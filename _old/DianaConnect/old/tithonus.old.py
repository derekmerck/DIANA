"""
Tithonus

Gatekeeper script for mirroring deidentified and reformatted medical images
(Named after _P. Tithonus_, the Gatekeeper butterfly)

[Derek Merck](derek_merck@brown.edu)
Spring 2015

<https://github.com/derekmerck/Tithonus>

Dependencies: requests, yaml, GID_Mint

See README.md for usage, notes, and license info.
"""

import logging
import argparse
import json
import sys
import os
import requests
import yaml
sys.path.append('../GID_Mint')
import GID_Mint

__package__ = "Tithonus"
__description__ = "Gatekeeper script for mirroring deidentified and reformatted medical images"
__url__ = "https://github.com/derekmerck/GID_Mint"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '0', '2')
__version__ = '.'.join(__version_info__)

logger = logging.getLogger(__package__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.info('version %s' % __version__)

class Study():
    """
    This is a container class for study or experiment data that facilitates communication
    between Orthanc and XNAT space.
    """

    def __init__(self, id, accession=None, giri=None, pname=None, dob=None,
                 gsid=None, mdname='', data=None, anonymized=False, institution='',
                 parent_pid=''):

        self.id = id                # uri/id relative to storage device
        self.parent_pid = parent_pid

        self.accession = accession  # PHI
        self.pname = pname          # PHI
        self.dob = dob              # PHI
        self.mdname = mdname        # PHI

        self.institution = institution

        self.anonymized = anonymized  # Flag for pre-anonymized image data

        self.giri = giri            # Anon
        self.gsid = gsid            # Anon
        self.ppname = ''
        self.pdob = ''
        self.pmdname = ''

        self.data = data

        if giri is None:
            if self.anonymized:
                self.giri = self.accession
            else:
                self.giri = GID_Mint.get_gid({'institution': self.institution, 'record_id': self.accession})

        if gsid is None and pname is not None and not self.anonymized:
            # Placeholder values for deidentification
            self.gsid = GID_Mint.get_gid({'pname': self.pname, 'dob': self.dob})
            self.ppname = GID_Mint.get_pname_for_gid({'gid': self.gsid})
            self.pdob = GID_Mint.get_pdob_for_dob_and_gid({'dob': self.dob, 'gid': self.gsid})
            mdgid = GID_Mint.get_gid({'gid': self.mdname})
            self.pmdname = GID_Mint.get_pmdname_for_gid({'gid': mdgid})

    def __str__(self):
        return "{0}({1}/{2})".format(self.id, self.giri, self.accession)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, Study):
            return self.giri == other.giri
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        # If two studies hash to the same value they are the same
        return hash(self.giri)
#        return hash(self.__repr__())

    def __cmp__(self, other):
        return self.giri < other.giri

class XNATInterface():

    def __init__(self, location):
        self.address = location[0]
        self.auth = (location[1],location[2])
        logger.info([self.address, self.auth])

    def delete_study(self, project, study):
        # Unfortunately need the project for a delete, but perhaps easier with a 'root' proj
        # TODO: Test xnat delete
        r = requests.delete(self.address + '/data/archive/projects/' + project + '/subjects/'
                            + study.gsid + '/experiments/' + study.id + '?remove_files=true',
                            auth=self.auth
                            )
        logger.info('xnat.delete status: %d' % r.status_code)
        logger.info(r.text)

    def upload_archive(self, project, study, fn=None):
        """See <https://wiki.xnat.org/display/XKB/Uploading+Zip+Archives+to+XNAT>"""

        logger.info('Sending %s to xnat', study.giri)

        params = {'project': project,
                  'subject': study.gsid,
                  'session': study.giri}

        files = None
        data = None
        if fn is not None:
            files = {'image_archive': open(fn, 'rb')}
        else:
            data = study.data

        headers = { 'content-type' : 'application/zip' }
        r = requests.post(self.address+'/data/services/import?format=html',
                          headers=headers,
                          params=params,
                          files=files,
                          data=data,
                          auth=self.auth
                          )

        logger.info('xnat.submit status: %d' % r.status_code)
        logger.info(r.text)

    def share_study(self, study, project):
        # TODO: Share subject to appropriate projects (possibly using reason for exam from Montage)
        pass

    def studies(self, which=None):
        logger.info('xnat.get url: %s' % self.address+'/data/experiments')
        r = requests.get(self.address+'/data/experiments',
                         auth=self.auth)
        logger.info('xnat.get status: %d' % r.status_code)
        logger.info(r.json())
        # Find all of the data labels
        results = r.json().get('ResultSet').get('Result')
        _studies = [Study(result['ID'], giri=result['label']) for result in results]
        return _studies


class OrthancInterface():

    def __init__(self, location):
        self.address = location[0]
        self.auth = (location[1],location[2])
        logger.info([self.address, self.auth])

    def anonymize(self, study):

        rule_author = "RIH 3D Lab"
        rule_name = "General DICOM Deidentification Rules"
        rule_version = "v1.0"

        anon_script = {
            "Replace": {
                "0010-0010": study.ppname, # PatientsName
                "0010-0020": study.gsid,   # PatientID
                "0008-0050": study.giri,   # AccessionNumber
                "0010-0030": study.pdob,   # PatientsBirthDate
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

        headers = { 'content-type' : 'application/json' }
        r = requests.post(self.address+'/studies/' + study.id +'/anonymize',
                          data=json.dumps(anon_script),
                          auth=self.auth,
                          headers=headers
                          )
        logger.info('orthanc.get status: %d' % r.status_code)
        logger.info(r.json())

        anon_study =self.study_from_id(r.json()['ID'])
        return anon_study

    def delete(self, *args):

        # TODO: Create delete curl for dp/dd flags
        pass

    def download_archive(self, study, fnb=None):
        logger.info('Downloading %s', self.address+'/studies/' + study.id + '/archive')
        r = requests.get(self.address+'/studies/' + study.id + '/archive',
                         auth=self.auth
                         )
        logger.info('orthanc.dl status: %d' % r.status_code)
        data = r.content
        if fnb is not None:
            f = open(os.path.join('/tmp', fnb + '.zip'), 'wb')
            f.write(data)
            f.close()
        return data

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

        return Study(study_info['ID'],
                     parent_pid=study_info['ParentPatient'],
                     accession=study_info['MainDicomTags']['AccessionNumber'],
                     pname=patient_info['MainDicomTags']['PatientName'],
                     dob=patient_info['MainDicomTags']['PatientBirthDate'],
                     institution="Rhode Island Hospital",
                     anonymized='AnonymizedFrom' in study_info
                     )

    def studies(self, which=None):

        r = requests.get(self.address+'/studies',
                         auth=self.auth
                         )
        logger.info('orthanc.get status: %d' % r.status_code)
        study_ids = r.json()
        logger.info(study_ids)

        _studies = [self.study_from_id(study_id) for study_id in study_ids]
        return _studies



def get_args():
    """Setup args and usage"""
    parser = argparse.ArgumentParser(description='Tithonus Core')
    parser.add_argument('-r', '--remote',
                        help='Remote mirror (XNAT) [address, (user, pword)]',
                        nargs=3,
                        metavar=('RADDR', 'RUSER', 'RPWORD'),
                        default=['http://localhost:8080/xnat', 'user', 'pword'])
    parser.add_argument('-l', '--local',
                        help='Local (Orthanc) [address, user, pword]}',
                        nargs=3,
                        metavar=('LADDR', 'LUSER', 'LPWORD'),
                        default=['http://localhost:8042', 'user', 'pword'])
    parser.add_argument('-c', '--config',
                        help='Config file path',
                        default='./config.yaml')
    parser.add_argument('-dp', '--delete_phi',
                        help='Remove original data with PHI from local after anonymization',
                        action='store_true',
                        default=False)
    parser.add_argument('-dd', '--delete_deidentified',
                        help='Remove deidentified data from local after mirror',
                        action='store_true',
                        default=False)
    p = parser.parse_args()

    if os.path.isfile(p.config):
        f = open(p.config, 'r')
        y = yaml.load(f)
        print y
        p.local = y['local']
        p.remote = y['remote']
        f.close()

    return p


if __name__ == "__main__":

    args_dict = get_args()
    logger.info(args_dict)

    remote = XNATInterface(args_dict.remote)
    local = OrthancInterface(args_dict.local)

    worklist = local.studies()
    logger.info("Candidate local worklist:" + str(worklist))
    """"
    Case 1:  Not anonymized yet, not pushed   -> Create anonymized child, push child
    Case 2:  Is anonymized, not pushed        -> Push
    Case 3:  Has anonymized child, not pushed -> Push child
    Case 4:  Not anonymized yet, pushed       -> Remove from worklist
    Case 5:  Is anonymized, pushed            -> Remove from worklist
    Case 6:  Has anonymized child, pushed     -> Remove from worklist
    """""

    # Deal with cases 4-6 by removing studies that are already on the remote server,
    # but keep duplicate locals, so can not use 'set'
    remote_studies = remote.studies()
    logger.info("Available remote_studies" + str(remote_studies))
    worklist = [study for study in worklist if study not in remote_studies]
    logger.info("Candidate local worklist minus remotes:" + str(worklist))

    # Create a worklist of studies that are ready to go to the mirror
    upload_worklist = [study for study in worklist if study.anonymized]
    logger.info('Initial upload worklist: ' + str(upload_worklist))

    # The anonymization worklist is everything that is not in the upload_worklist
    anonymization_worklist = [study for study in worklist if study not in upload_worklist]
    logger.info('Initial anonymization worklist: ' + str(anonymization_worklist))

    for study in anonymization_worklist:
        anon_study = local.anonymize(study)
        upload_worklist.append(anon_study)
        # TODO: Delete PHI if necessary
        # Can delete original file now (unless flagged)
        if args_dict.delete_phi:
            # local.delete(study)
            pass

    logger.info('Final upload worklist: ' + str(upload_worklist))

    for study in upload_worklist:
        study.data = local.download_archive(study)
        remote.upload_archive('root', study)

        # TODO: Decide whether to share this study to specific subprojects (stroke, ablation)
        # Possibly based on querying reason for exam from Montage?
        # remote.share_study(anon_study)

        # TODO: Delete anonymized if necessary
        # Can delete anonymized file now (unless flagged)
        if args_dict.delete_deidentified:
            # local.delete(study)
            pass

