import requests
from requests import ConnectionError
from hashlib import sha1
from pprint import pformat
from Dixel import *
from DixelStorage import *
import DixelTools
from Splunk import Splunk
import json


class Orthanc(HTTPDixelStorage):

    def __init__(self,
                 host,
                 port=8042,
                 user=None,
                 password=None,
                 cache_policy=CachePolicy.NONE,
                 prefer_compressed=False,
                 peer_name=None,
                 **kwargs):
        # self.session = requests.session()
        super(Orthanc, self).__init__()

        # Setup session
        if user and password:
            self.session.auth = (user, password)
        self.url = "http://{host}:{port}".format(host=host, port=port)

        # Local properties
        self.prefer_compressed = prefer_compressed
        self.peer_name = peer_name
        # cache_pik = "{0}.pik".format(
        #         sha1("{0}:{1}@{2}".format(
        #         user, password, self.url)).hexdigest()[0:8])
        # cache_pik = cache_pik, cache_policy = cache_policy

    # def do_get(self, url, headers=None, params=None):
    #     try:
    #         r = self.session.get(url, headers=headers, params=params)
    #     except requests.exceptions.ConnectionError as e:
    #         logging.error(e.request.headers)
    #         logging.error(e.request.body)
    #
    #     return r
    #
    # def do_post(self, url, data=None, json=None, headers=None):
    #     try:
    #         r = self.session.post(url, data=data, json=json, headers=headers)
    #     except requests.exceptions.ConnectionError as e:
    #         logging.error(e.request.headers)
    #         logging.error(e.request.body)
    #     return r
    #
    # def do_delete(self, url, headers=None):
    #     try:
    #         r = self.session.delete(url, headers=headers)
    #     except requests.exceptions.ConnectionError as e:
    #         logging.error(e.request.headers)
    #         logging.error(e.request.body)
    #     return r

    def statistics(self):
        url = "{0}/statistics".format(self.url)
        r = self.do_get(url)
        return r.json()

    def get(self, dixel, **kwargs):

        if dixel.level is DicomLevel.INSTANCES:
            url = '{0}/{1}/{2}/file'.format(self.url, str(dixel.level), dixel.id)
        else:
            url = '{0}/{1}/{2}/archive'.format(self.url, str(dixel.level), dixel.id)

        r = self.do_get(url)
        # r = self.session.get(url)
        if r.status_code == 200:
            dixel.data['archive'] = r.content
        else:
            self.logger.warning('Could not get {0}!'.format(dixel))

    def put(self, dixel):
        if dixel.level != DicomLevel.INSTANCES:
            raise NotImplementedError("Orthanc can only 'put' dixel instances")

        headers = {'content-type': 'application/dicom'}
        url = "{0}/instances/".format(self.url)
        r = self.do_post(url, data=dixel.data['file'], headers=headers)
        # r = self.session.post(url, data=dixel.data['file'], headers=headers)

        if r.status_code == 200:
            self.logger.debug('Added {0} successfully!'.format(dixel))
        else:
            self.logger.warning('Could not add {0}!'.format(dixel))

        self.logger.debug(pformat(r.json()))

    def delete(self, dixel):
        url = "{}/{}/{}".format(self.url, str(dixel.level), dixel.id)

        # r = self.session.delete(url)
        r = self.do_delete(url)
        if r.status_code == 200:
            self.logger.debug('Removed {0} successfully!'.format(dixel))
        else:
            self.logger.warning('Could not delete {0}!'.format(dixel))


    def update(self, dixel, **kwargs):

        meta = dixel.meta.copy()

        if dixel.level != DicomLevel.SERIES:
            url = "{}/{}/{}/tags?simplify".format(self.url, str(dixel.level), dixel.id)
        else:
            url = "{}/{}/{}/shared-tags?simplify".format(self.url, str(dixel.level), dixel.id)
	    
        # r = self.session.get(url)
        r = self.do_get(url)

        if r.status_code != 200:
            return dixel

        tags = r.json()
        tags = DixelTools.simplify_tags(tags)

        meta.update(tags)

        # Check anon status
        url = "{}/{}/{}/metadata".format(self.url, str(dixel.level), dixel.id)
        r = self.do_get(url)
        # try:
        #     r = self.session.get(url)
        # except requests.exceptions.ConnectionError:
        #     logging.warn(r.content)

        items = r.json()
        if "AnonymizedFrom" in items:
            meta['Anonymized'] = True

        if dixel.level == "instance":
            url = "{}/{}/{}/metadata/TransferSyntaxUID".format(self.url, str(dixel.level), dixel.id)
            # r = self.session.get(url)
            r = self.do_get(url)
            meta['TransferSyntaxUID'] = r.json()

            url = "{}/{}/{}/metadata/SopClassUid".format(self.url, str(dixel.level), dixel.id)
            # r = self.session.get(url)
            r = self.do_get(url)
            meta['SOPClassUID'] = DixelTools.DICOM_SOPS.get(r.json(), r.json())  # Text or return val

        return Dixel(dixel.id, meta=meta, level=dixel.level)


    def copy(self, dixel, dest):
        # May have various tasks to do, like anonymize or compress

        if type(dest) == Orthanc:
            # Use push-to-peer
            url = "{0}/peers/{1}/store".format(self.url, dest.peer_name)
            # self.session.post(url, data=dixel.id)

            r = self.do_post(url, data=dixel.id)
            # r = requests.post(url, auth=self.session.auth, data=dixel.id)
            self.logger.debug(r.content)

        elif type(dest) == Splunk:
            dixel = self.update(dixel)  # Add available data and meta data, parse
            dest.put(dixel)

        else:
            raise NotImplementedError(
                "{} doesn't know how to put dixel {} into {}".format(
                    self.__class__.__name__,
                    dixel.level,
                    dest.__class__.__name__))

    def initialize_inventory(self):
        res = set()
        url = "{0}/instances".format(self.url)
        r = self.do_get(url)
        r = self.session.get(url)
        for item in r.json():
            res.add(Dixel(id=item, level=DicomLevel.INSTANCES))

        # self.logger.debug(res)

        return res

    @property
    def series(self):
        return self.check_cache('series')

    def initialize_series(self):
        res = set()
        r = self.do_get("{0}/series".format(self.url)).json()
        for item in r:
            res.add(Dixel(id=item, level=DicomLevel.SERIES))
        return res

    @property
    def studies(self):
        return self.check_cache('studies')

    def initialize_studies(self):
        res = set()
        r = self.do_get("{0}/studies".format(self.url)).json()
        for item in r:
            res.add(Dixel(id=item, level=DicomLevel.SERIES))
        return res

    def exists(self, dixel):
        url = "{}/{}/{}".format(self.url,
                                str(dixel.level),
                                dixel.id)
        r = self.do_get(url)
        # r = self.session.get(url)
        if r.status_code == 200:
            return True
        else:
            return False

    def anonymize(self, dixel, replacement_dict=None):

        url = "{}/{}/{}/anonymize".format(self.url,
                                str(dixel.level),
                                dixel.id)

        replacement_json = json.dumps(replacement_dict)
        logging.debug(replacement_json)

        headers = {'content-type': 'application/json'}
        r = self.do_post(url, data=replacement_json, headers=headers)
        # r = requests.post()
        self.logger.debug(r.content)

        if r.status_code == 200:
            self.logger.debug('Anonymized {0} successfully!'.format(dixel))
            e = Dixel(id=r.json()['ID'], level=dixel.level)
            return e

        else:
            self.logger.warning('Could not anonymize {0}!'.format(dixel))


class OrthancProxy(Orthanc):

    def __init__(self, *args, **kwargs):
        self.remote_aet = kwargs.get('remote_aet', None)
        super(OrthancProxy, self).__init__(*args, **kwargs)

    def get(self, dixel, **kwargs):

        def find_series(dixel):
            # Return an individual qid, aid

            dicom_level = "series"

            def qdict(dixel):
                qdict = {'PatientID': dixel.meta['PatientID'],
                         'StudyInstanceUID': '',
                         'SeriesInstanceUID': dixel.meta.get('SeriesInstanceUID', ''),
                         'SeriesDescription': '',
                         'SeriesNumber': '',
                         'StudyDate': '',
                         'StudyTime': '',
                         'AccessionNumber': dixel.meta['AccessionNumber']}
                # if dixel.level == DicomLevel.STUDIES:
                #     qdict['ModalitiesInStudy'] = 'CT'
                qdict.update(kwargs.get('qdict', {}))
                return qdict

            query = qdict(dixel)

            data = {'Level': dicom_level,
                    'Query': query}

            self.logger.debug(pformat(data))

            url = '{0}/modalities/{1}/query'.format(self.url, self.remote_aet)
            self.logger.debug(url)

            headers = {"Accept-Encoding": "identity",
                       "Accept": "application/json"}

            r = self.do_post(url, json=data, headers=headers)
            if r.status_code == 200:
                dixel.meta['QID'] = r.json()["ID"]

            # # Does not like session.post for some reason!
            # try:
            #     # r = self.session.post(url, json=data, headers=headers)
            #     r = requests.post(url, json=data, headers=headers, auth=self.session.auth)
            #     self.logger.debug(r.headers)
            #     self.logger.debug(r.content)
            #     dixel.meta['QID'] = r.json()["ID"]
            # except ConnectionError as e:
            #     self.logger.error(e)
            #     self.logger.error(e.request.headers)
            #     self.logger.error(e.request.body)

            url = '{0}/queries/{1}/answers'.format(self.url, dixel.meta['QID'])
            r = self.do_get(url)

            answers = r.json()

            if len(answers)>1:
                self.logger.warn('Retrieve too many candidate responses, using LAST')

            for aid in answers:
                url = '{0}/queries/{1}/answers/{2}/content?simplify'.format(self.url, dixel.meta['QID'], aid)
                # r = self.session.get(url)
                r = self.do_get(url)

                tags = r.json()

                suffix = kwargs.get('suffix', '')
                if suffix:
                    tmp = {}
                    for k,v in tags.iteritems():
                        tmp[k+suffix] = v
                    tags = tmp

                logging.debug(pformat(tags))

                dixel.meta.update(tags)
                dixel.meta['AID'] = aid
                dixel.meta['OID'] = DixelTools.orthanc_id(dixel.meta['PatientID'],
                                            dixel.meta['StudyInstanceUID'+suffix],
                                            dixel.meta['SeriesInstanceUID'+suffix])

                # A proper series level ID
                dixel.id = dixel.meta['OID']

            return dixel

        def retrieve_series(dixel):
            oid = DixelTools.orthanc_id(dixel.meta['PatientID'],
                                  dixel.meta['StudyInstanceUID'],
                                  dixel.meta['SeriesInstanceUID'])
            dixel.meta['oid'] = oid
            dixel.id = oid

            dixel.level = DicomLevel.SERIES

            self.logger.debug('Expecting oid: {}'.format(oid))

            if self.exists(dixel): return

            url = "{}/queries/{}/answers/{}/retrieve".format(
                self.url,
                dixel.meta['QID'],
                dixel.meta['AID'])
            r = requests.post(url, auth=self.session.auth, data="DEATHSTAR")
            self.logger.debug(r.content)

            if not self.exists(dixel):
                raise Exception("Failed to c-move dixel w accession {}".format(dixel.meta['AccessionNumber']))

            return dixel

        # Check and see if you already have it in inventory
        if self.exists(dixel):
            return Orthanc.update(self, dixel)

        # if not dixel.meta.get('QID') or not dixel.meta.get('AID'):
        dixel = find_series(dixel)

        if kwargs.get('retrieve'):
            dixel = retrieve_series(dixel)

        return dixel

    # def copy(self, dixel, dest):
    #     # Must _retrieve_ first
    #     #self.get(dixel, retrieve=True, lazy=True)
    #     Orthanc.copy(self, dixel, dest)
    #     #self.delete(dixel)

    def update(self, dixel, **kwargs):

        if dixel.meta.get('AccessionNumber') and\
                not dixel.meta.get("RetrieveAETitle"):
            # run a PACS search for this study
            d = self.get(dixel, **kwargs)
        else:
            d = Orthanc.update(self, dixel, **kwargs)

        return d



