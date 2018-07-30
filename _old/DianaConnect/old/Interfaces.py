import logging
logger = logging.getLogger('Tithonus.Interfaces')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

import requests
from posixpath import join as urljoin
import json

from old.DataTypes import *
from old.Utilities import *

class RepoInterface(object):

    @staticmethod
    def get_interface_for_config(interface_name, _config):
        config = _config[interface_name]
        if config['type'] == 'xnat':
            return XNATRepoInterface(config['address'], config['user'], config['pword'])
        elif config['type'] == 'orthanc':
            return OrthancRepoInterface(config['address'], config.get('user'), config.get('pword'), config.get('aetitle'))
        elif config['type'] == 'orthanc':
            # TODO: prevent accidental infinite recursion
            proxy = RepoInterface.get_interface_for_config(config['proxy_name'], _config)
            return DICOMRepoInterface(config['aetitle'], proxy)
        else:
            logger.warn("Unknown repo type in config")

    def __init__(self):
        pass

    def study_from_id(self, study_id):
        raise NotImplementedError

    def upload_study_archive(self, study):
        """Wrapper for upload study data with file handling"""
        data = None
        if os.path.isdir(study.local_file):
            logger.info('Uploading image folder %s', study.local_file)
            data = zipdir(study.local_file)
        elif os.path.isfile(study.local_file):
            logger.info('Uploading image archive %s', study.local_file)
            f = open(study.local_file, 'rb')
            data = f.read()
        self.upload_study_data(study, data)

    def upload_study_data(self, study, data):
        raise NotImplementedError

    def download_study_archive(self, study, fno=None):
        """Wrapper for upload study data with file handling"""
        study.data = self.download_study_data(study)
        if fno is not None:
            f = open(fno + '.zip', 'wb')
            f.write(study.data)
            f.close()

    def download_study_data(self, study):
        raise NotImplementedError

    def find_studies(self, query):
        raise NotImplementedError

    def studies(self):
        raise NotImplementedError

    def get_study(self, study_id):
        """This gets the study handle and meta data, not the image files"""
        raise NotImplementedError

    def delete_study(self, study_id):
        raise NotImplementedError

    def anonymize_study(self, study_id):
        raise NotImplementedError


class XNATRepoInterface(RepoInterface):

    var_dict = {'study_type': 'xnat:mrSessionData/fields/field[name=study_type]/field'}

    def __init__(self, address, user, pword):
        super(XNATRepoInterface, self).__init__()
        self.address = address
        self.auth = (user, pword)

    def studies(self):
        logger.info('xnat.get url: %s' % self.address+'/data/experiments')
        r = requests.get(self.address+'/data/experiments',
                         auth=self.auth)
        logger.info('xnat.get status: %d' % r.status_code)
        logger.info(r.json())
        # Find all of the data labels
        results = r.json().get('ResultSet').get('Result')
        _studies = [Study(result['ID'], giri=result['label']) for result in results]
        return _studies

    def set_study_attribute(self, study, key):
        logger.info('Submitting http put for custom var')

        value = study.__dict__[key]
        params = {self.var_dict[key]: value}
        s = urljoin(self.address, 'data/archive',
                    'projects', study.subject.project.project_id,
                    'subjects', study.subject.subject_id,
                    'experiments', study.study_id)
        r = requests.put(s, params=params, auth=self.auth)

        logger.info('xnat set attribute status: %d' % r.status_code)
        logger.info(r.text)

    def upload_study_data(self, study, data):
        """See <https://wiki.xnat.org/display/XKB/Uploading+Zip+Archives+to+XNAT>"""

        logger.info('Submitting http post for upload')
        params = {'overwrite': 'delete',
                  'project': study.subject.project.project_id,
                  'subject': study.subject.subject_id,
                  'session': study.study_id}
        headers = {'content-type': 'application/zip'}
        r = requests.post(self.address+'/data/services/import?format=html',
                          headers=headers,
                          params=params,
                          data=data,
                          auth=self.auth
                          )

        logger.info('xnat upload status: %d' % r.status_code)
        logger.info(r.text)

    def delete_study(self, study):
        # Unfortunately need the project for a delete, but perhaps easier with a 'root' proj
        # TODO: Test xnat delete
        params = {'remove_files': 'true'}
        s = urljoin(self.address, 'data/archive/',
                    'projects', study.subject.project.project_id,
                    'subjects', study.subject.subject_id,
                    'experiments', study.study_id)
        r = requests.delete(s, params=params, auth=self.auth)

        logger.info('xnat delete status: %d' % r.status_code)
        logger.info(r.text)


class OrthancRepoInterface(RepoInterface):
    # <https://docs.google.com/spreadsheets/d/1muKHMIb9Br-59wfaQbDeLzAfKYsoWfDSXSmyt6P4EM8/pubhtml?gid=525933398&single=true>

    def __init__(self, address, user, pword, aetitle=None):
        super(OrthancRepoInterface, self).__init__()
        self.address = address
        self.auth = (user, pword)
        self.aetitle = aetitle

    def study_from_id(self, study_id):

        r = requests.get(self.address+'/studies/'+study_id,
                         auth=self.auth
                         )
        logger.info('orthanc.get status: %d' % r.status_code)

        # Could do this too...  Maybe _need_ to do it this way...
        # curl http://localhost:8042/instances/e668dcbf-8829a100-c0bd203b-41e404d9-c533f3d4/simplified-tags

        study_info = r.json()
        logger.info(study_info)

        r = requests.get(self.address+'/patients/'+study_info['ParentPatient'],
                         auth=self.auth
                         )
        patient_info = r.json()
        logger.info(patient_info)

        # TODO: Need to grab institution, mdname, to deidentify correctly
        # InstitutionName = 0008,0080
        # ReferringPhysiciansName = 0008,0090

        return Study(study_info['MainDicomTags']['AccessionNumber'],
                     subject_id=patient_info['MainDicomTags']['PatientID'],
                     subject_name=patient_info['MainDicomTags']['PatientName'],
                     subject_dob=patient_info['MainDicomTags']['PatientBirthDate'],
                     other_ids={self: study_id},
                     institution="Rhode Island Hospital",
                     anonymized='AnonymizedFrom' in study_info
                     )

    def studies(self):

        r = requests.get(self.address+'/studies',
                         auth=self.auth
                         )
        logger.info('orthanc get studies status: %d' % r.status_code)
        study_ids = r.json()
        logger.info(study_ids)

        _studies = [self.study_from_id(study_id) for study_id in study_ids]
        return _studies

    def find_studies(self, query):
        params = {'query': query}
        s = urljoin(self.address, 'find')
        r = requests.put(s, params=params, auth=self.auth)
        logger.info('orthanc find studies: %d' % r.status_code)
        return r.content

    def proxy_find_studies(self, query, modality):
        params = {'query': query}
        s = urljoin(self.address, 'modality', modality, 'query')
        r = requests.put(s, params=params, auth=self.auth)
        logger.info('orthanc proxy-find studies: %d' % r.status_code)
        return r.content

    def download_study_data(self, study):
        logger.info('Downloading %s', self.address+'/studies/' + study.study_id + '/archive')
        r = requests.get(self.address+'/studies/' + study.other_ids[self] + '/archive',
                         auth=self.auth
                         )
        logger.info('orthanc dl status: %d' % r.status_code)
        data = r.content
        return data

    def anonymize(self, study):

        rule_author = "RIH 3D Lab"
        rule_name = "General DICOM Deidentification Rules"
        rule_version = "v1.0"

        anon_script = {
            "Replace": {
                "0010-0010": study.subject.anon_subject_name, # PatientsName
                "0010-0020": study.subject.anon_subject_id,   # PatientID
                "0010-0030": study.subject.anon_dob,          # PatientsBirthDate
                "0008-0050": study.anon_study_id,             # AccessionNumber
                "0012-0062": "YES",        # Deidentified
                "0010-0021": rule_author,  # Issuer of Patient ID
                "0012-0063": "{0} {1} {2}".format(rule_author, rule_name, rule_version) # Deidentification method
                },
            "Keep": [
                "0008-0080",                # InstitutionName
                "0010-0040",                # PatientsSex
                "0010-1010",                # PatientsAge
                "StudyDescription",
                "SeriesDescription"],
            "KeepPrivateTags": None
            }

        headers = {'content-type' : 'application/json'}
        s = urljoin(self.address, 'studies', study.study_id, 'anonymize')
        r = requests.delete(s, data=json.dumps(anon_script), headers=headers, auth=self.auth)

        logger.info('orthanc anonymize status: %d' % r.status_code)
        logger.info(r.json())

        # Use this value as study.anon_study_id?
        # anon_study =self.study_from_id(r.json()['ID'])
        # return anon_study


class DICOMRepoInterface(RepoInterface):

    def __init__(self, aetitle, proxy):
        super(DICOMRepoInterface, self).__init__()
        self.aetitle = aetitle
        self.proxy = proxy

    def find_study(self, study):
        self.proxy.proxy_find_study(self.aetitle, study)

    def download_study_data(self, study):
        # DL to proxy, then grab data
        self.proxy.proxy_get_study(self.aetitle, study)
        data = self.proxy.download_study_data
        return data


class TCIARepoInterface(RepoInterface):

    def __init__(self, address, api_key):
        super(TCIARepoInterface, self).__init__()
        self.address = address
        self.api_key = api_key

    def get_study(self, study_id):
        pass

#
