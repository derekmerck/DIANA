import requests
import urlparse
import logging
from pprint import pformat
from dixel import DLVL
import json


class Requester(object):

    def __init__(self, host, port, auth):

        self.base_url = "http://{}:{}".format(host, port)
        self.auth = auth

    def do_get(self, url, headers=None, params=None):
        url = urlparse.urljoin(self.base_url, url)
        r = requests.get(url, params=params, headers=headers, auth=self.auth)

        logging.debug(r.headers)
        if not r.status_code == 200:
            raise requests.ConnectionError
        elif r.headers.get('content-type').find('application/json')>=0:
            return r.json()
        else:
            return r.content

    def do_post(self, url, data=None, json=None, headers=None):
        url = urlparse.urljoin(self.base_url, url)
        r = requests.post(url, data=data, json=json, headers=headers, auth=self.auth)
        if not r.status_code == 200:
            raise requests.ConnectionError
        else:
            return r.json()

    def do_delete(self, url):
        url = urlparse.urljoin(self.base_url, url)
        r = requests.delete(url, auth=self.auth)
        if not r.status_code == 200:
            raise requests.ConnectionError
        else:
            return r.json()


# Implements a set-type interface for dixels with "add", "remove", "get", "__contains__"
class Orthanc(Requester):

    def __init__(self, host="localhost", port=8042, user=None, password=None, clear=False,
                 remote_names=None, **kwargs):
        self.logger = logging.getLogger("Orthanc<{}:{}>".format(host, port))
        super(Orthanc, self).__init__(host, port, (user, password))
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
                url = '{}/tags'.format(url)
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

    def anonymize(self, dixel, replacement_dict=None):

        url = "{}/{}/anonymize".format(dixel.dlvl, dixel.oid())

        replacement_json = json.dumps(replacement_dict)
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
                        'SeriesNumber',
                        'NumberOfSeriesRelatedInstances']

        keys[DLVL.INSTANCES] = keys[DLVL.SERIES] + ['SOPInstanceUID']

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
                r = self.do_post(url, data=self.remote_names[remote_aet])
                return r

        return ret