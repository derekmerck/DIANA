import requests
import urlparse
import logging
from pprint import pformat
from dixel import DLVL
import json
import hashlib
import yaml
import re
from datetime import timedelta
from dateutil import parser as dateutil_parser


class Requester(object):

    def __init__(self, host, port, auth, path=''):

        self.base_url = "http://{}:{}".format(host, port)
        self.path = path
        self.auth = auth

    def do_get(self, url, headers=None, params=None):
        url = "/".join([self.path, url])
        url = urlparse.urljoin(self.base_url, url)
        logging.debug(url)
        r = requests.get(url, params=params, headers=headers, auth=self.auth)

        logging.debug(r.headers)
        if not r.status_code == 200:
            raise requests.ConnectionError
        elif r.headers.get('content-type').find('application/json')>=0:
            return r.json()
        else:
            return r.content

    def do_post(self, url, data=None, json=None, headers=None):
        url = "/".join([self.path, url])
        url = urlparse.urljoin(self.base_url, url)
        r = requests.post(url, data=data, json=json, headers=headers, auth=self.auth)
        if not r.status_code == 200:
            raise requests.ConnectionError
        else:
            return r.json()

    def do_delete(self, url):
        url = "/".join([self.path, url])
        url = urlparse.urljoin(self.base_url, url)
        r = requests.delete(url, auth=self.auth)
        if not r.status_code == 200:
            raise requests.ConnectionError
        else:
            return r.json()


class Montage(Requester):

    def __init__(self, host, port=80, user=None, password=None, index="rad", **kwargs):
        self.logger = logging.getLogger("Montage<{}:{}>".format(host, port))
        super(Montage, self).__init__(host, port, (user, password), "api/v1")
        self.do_get('')
        self.path = "/".join([self.path, 'index', index])
        self.do_get('')


    def do_query(self, qdict):
        r = self.do_get("search", params=qdict)
        return r["objects"]

    def find(self, dixel, **kwargs):

        def daterange(s_ref, s_delta, s_delta2=None):

            def mk_delta(s):
                m = re.search('^(?P<op>(\+|\-))(?P<count>\d+)(?P<units>(s|m|h|d|w))$', s)
                val = int(m.groupdict()['op'] + m.groupdict()['count'])
                if m.groupdict()['units'] == 's':
                    td = timedelta(seconds=val)
                elif m.groupdict()['units'] == 'm':
                    td = timedelta(minutes=val)
                elif m.groupdict()['units'] == 'h':
                    td = timedelta(hours=val)
                elif m.groupdict()['units'] == 'd':
                    td = timedelta(days=val)
                elif m.groupdict()['units'] == 'w':
                    td = timedelta(weeks=val)
                else:
                    raise ()

                return td

            # TODO: does this work with "now"?
            ref = dateutil_parser.parse(s_ref)
            delta = mk_delta(s_delta)

            if s_delta2:
                delta2 = mk_delta(s_delta2)
            else:
                delta2 = - delta

            earliest = ref + delta
            latest = ref + delta2

            return earliest, latest

        qdict = {}

        if dixel.data.get('PatientID'):
            qdict['patient_mrn'] = dixel.data['PatientID']
        if dixel.data.get('AccessionNumber'):
            qdict['accession_number'] = dixel.data['AccessionNumber']
        if dixel.data.get('RefDate') and dixel.data.get('time_delta'):
            (start_date, end_date) = daterange(dixel.data.get('RefDate'), dixel.data.get('time_delta'))
            qdict['start_date'] = start_date
            qdict['end_date']   = end_date

        for k, v in kwargs.iteritems():
            qdict[k] = v

                 # : "2016-11-17",
                 # "end_date": "2016-11-19"

        return self.do_query(qdict)


# Implements a set-type interface for dixels with "add", "remove", "get", "__contains__"
class Orthanc(Requester):

    @classmethod
    def simple_anon_map(cls, dixel):
        return {
            'Replace': {
                'PatientName': dixel.data['AnonName'],
                'PatientID': dixel.data['AnonID'],
                'PatientBirthDate': dixel.data['AnonDoB'].replace('-', ''),
                'AccessionNumber': hashlib.md5(dixel.data['AccessionNumber']).hexdigest(),
            },
            'Keep': ['PatientSex', 'StudyDescription', 'SeriesDescription'],
            'Force': True
        }

    def __init__(self, host="localhost", port=8042, user=None, password=None, path='',
                 clear=False, remote_names=None, **kwargs):
        self.logger = logging.getLogger("Orthanc<{}:{}>".format(host, port))
        super(Orthanc, self).__init__(host, port, (user, password), path=path)
        if clear:
            self.clear()
        self.remote_names = remote_names

    def add(self, dixel, lazy=True, force=False, compress=False):
        # TODO: Should be "compressed", "uncompressed", "as_is" (default)

        if not dixel.dlvl == DLVL.INSTANCES:
            self.logger.warn("Can only 'put' instances")

        if force:
            self.remove(dixel)

        if not lazy or dixel not in self:
            data = dixel.read_file(compress)
            if data:
                # logging.debug("Putting")
                headers = {'content-type': 'application/dicom'}
                url = "instances"
                try:
                    r = self.do_post(url, data=data, headers=headers)
                except:
                    self.logger.error("Failed to post {}".format(dixel.oid()))
                    r = -1
                return r

            else:
                self.logger.warn("No data for {}".format(dixel))

    def get(self, dixel, get_type='tags'):

        url = '{}/{}'.format(str(dixel.dlvl), dixel.oid())

        if get_type == 'tags':
            if dixel.dlvl is DLVL.INSTANCES:
                url = '{}/tags?simplify'.format(url)
            else:
                url = '{}/shared-tags?simplify'.format(url)
            # TODO: Check compression, etc.
        elif get_type == "file":
            if dixel.dlvl is DLVL.INSTANCES:
                url = '{}/file'.format(url)
            else:
                url = '{}/archive'.format(url)
        else:
            self.logger.warn("Unknown 'get_type': {}".format(get_type))

        return self.do_get(url)

    def remove(self, dixel):
        url = '{}/{}'.format(str(dixel.dlvl), dixel.oid())
        return self.do_delete(url)

    def __contains__(self, dixel):

        if dixel.dlvl == DLVL.STUDIES:
            inv = self.do_get("studies")
        elif dixel.dlvl == DLVL.SERIES:
            inv = self.do_get("series")
        elif dixel.dlvl == DLVL.INSTANCES:
            inv = self.do_get("instances")
        else:
            self.logger.warn("Can only '__contain__' study, series, instance dixels")
            return

        return dixel.oid() in inv

    def clear(self):
        inv = self.do_get("studies")
        logging.debug(inv)
        for i in inv:
            url = "studies/{}".format(i)
            logging.debug(url)
            self.do_delete(url)

    def statistics(self):
        return self.do_get("statistics")

    def size(self, unit="MB"):
        stats = self.statistics()
        if unit == "MB":
            return float(stats['TotalDiskSizeMB'])
        elif unit == "TB":
            return float(stats['TotalDiskSizeMB'])/1000.0
        else:
            self.logger.warn("Unknown unit type {}".format(unit))

    def add_all(self, worklist, lazy=True, compress=True):
        # logging.debug(pformat(inventory))
        for d in worklist:
            self.add(d, lazy, compress)

    def anonymize(self, dixel, replacement_map=None):

        url = "{}/{}/anonymize".format(dixel.dlvl, dixel.oid())

        if not replacement_map:
            replacement_map = self.simple_anon_map

        replacement_json = json.dumps(replacement_map(dixel))
        # logging.debug(replacement_json)

        headers = {'content-type': 'application/json'}
        r = self.do_post(url, data=replacement_json, headers=headers)

        if not r:
            self.logger.warning('Could not anonymize {0}!'.format(dixel))
        else:
            return r


    def find(self, dixel, remote_aet, retrieve=False):
        # Have some information about the dixel, want to find the STUID, SERUID, INSTUID
        # Returns a _list_ of dictionaries with matches

        q = {}
        keys = {}

        # All levels have these
        keys[DLVL.STUDIES] = ['PatientID',
                        'PatientName',
                        'PatientBirthDate',
                        'PatientSex',
                        'StudyInstanceUID',
                        'StudyDate',
                        'StudyTime',
                        'AccessionNumber']

        keys[DLVL.SERIES] = keys[DLVL.STUDIES] + ['SeriesInstanceUID',
                        'SeriesDescription',
                        'ProtocolName',
                        'SeriesNumber',
                        'NumberOfSeriesRelatedInstances']

        # Minimal, we are going to want to retreive this
        keys[DLVL.INSTANCES] = ['SOPInstanceUID','SeriesInstanceUID']
        if dixel.data.get('SOPInstanceUID'):
            keys[DLVL.INSTANCES] = ['SOPInstanceUID']

        def add_key(q, key, dixel):
            q[key] = dixel.data.get(key, '')
            return q

        for k in keys[dixel.dlvl]:
            q = add_key(q, k, dixel)

        # logging.debug(pformat(q))


        # if dixel.dlvl == DLVL.STUDIES and qdict.get('Modality'):
        #     _qdict['ModalitiesInStudy'] = qdict.get('Modality')
        #     del (qdict['Modality'])

        data = {'Level': str(dixel.dlvl),
                'Query': q}

        url = '/modalities/{}/query'.format(remote_aet)
        headers = {"Accept-Encoding": "identity",
                   "Accept": "application/json"}

        r = self.do_post(url, json=data, headers=headers)
        if not r:
            logging.warn("No reply from orthanc lookup")
            return

        qid = r["ID"]
        url = 'queries/{}/answers'.format(qid)
        r = self.do_get(url)

        if not r:
            logging.warn("No answers from orthanc lookup")
            return

        answers = r
        ret = []
        for aid in answers:
            url = 'queries/{}/answers/{}/content?simplify'.format(qid, aid)
            r = self.do_get(url)
            if not r:
                logging.warn("Bad answer from orthanc lookup")
                return

            ret.append(r)

            if retrieve:
                # Just grab the first one and return
                url = 'queries/{}/answers/{}/retrieve'.format(qid, aid)
                rr = self.do_post(url, data=self.remote_names[remote_aet])
                logging.debug(rr)

        return ret



import pytest
@pytest.fixture
def report_db():
    logging.basicConfig(level=logging.DEBUG)
    with open("secrets.yml", 'r') as f:
        secrets = yaml.load(f)

    return Montage(**secrets['services']['prod']['montage'])

def test_montage(report_db):

    qdict = {"q": "cta",
             "modality": 4,
             "exam_type": [8683, 7713, 8766],
             "start_date": "2016-11-17",
             "end_date": "2016-11-19"}

    r = report_db.query(qdict)
    logging.debug(pformat(r))


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_montage(report_db())