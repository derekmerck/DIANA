#!/usr/bin/env python
'''
In progress...

Tithonus

Gatekeeper script for mirroring deidentified and reformatted medical images
(Named after _P. Tithonus_, the Gatekeeper butterfly)

[Derek Merck](derek_merck@brown.edu)
Spring 2015

<https://github.com/derekmerck/Tithonus>

Dependencies: requests, yaml, GID_Mint

See README.md for usage, notes, and license info.
'''

import argparse

import yaml

from old.Interfaces import *

__package__ = "Tithonus"
__description__ = "Gatekeeper script for mirroring deidentified and reformatted medical images"
__url__ = "https://github.com/derekmerck/Tithonus"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '1', '2')
__version__ = '.'.join(__version_info__)

logger = logging.getLogger(__package__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.info('version %s' % __version__)


def find_study(source_name, study_id):
    pass


def delete_study(source_name, study_id):
    pass


def copy_study(source_name, target_name, study_id):

    study = Study.get_study_for_config(study_id, study_config)
    if source_name == "local":
        # Create objects
        target = RepoInterface.get_interface_for_config(target_name, repos_config)

        # Upload and set custom variables
        target.upload_study_archive(study)
        target.set_study_attribute(study, 'study_type')

    elif target_name == "local":
        # Create objects
        source = RepoInterface.get_interface_for_config(source_name, repos_config)
        source.download_study_archive(study)


def mirror_repo(source_name, target_name):

    source = RepoInterface.get_interface_for_config(source_name, repos_config)
    target = RepoInterface.get_interface_for_config(target_name, repos_config)

    worklist = source.studies()
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
    remote_studies = target.studies()
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
        anon_study = source.anonymize(study)
        upload_worklist.append(anon_study)
        # TODO: Delete PHI if necessary
        # Can delete original file now (unless flagged)
        if opts.delete_phi:
            # local.delete(study)
            pass

    logger.info('Final upload worklist: ' + str(upload_worklist))

    for study in upload_worklist:
        study.data = source.download_study_data(study)
        target.upload_study_data('root', study)

        # TODO: Decide whether to share this study to specific subprojects (stroke, ablation)
        # Possibly based on querying reason for exam from Montage?
        # remote.share_study(anon_study)

        # TODO: Delete anonymized if necessary
        # Can delete anonymized file now (unless flagged)
        if opts.delete_deidentified:
            # local.delete(study)
            pass

def get_args():
    """Setup args and usage"""
    parser = argparse.ArgumentParser(description='Tithonus Core')
    parser.add_argument('function',
                        choices=['find-study', 'move-study', 'copy-study', 'delete-study', 'mirror-repo'])
    parser.add_argument('source',
                        help='Source/working image repository as ID in config or json')
    parser.add_argument('target',
                        help='Target image repository as ID in config or json')
    parser.add_argument('-s', '--study',
                        help='Study as ID in working repo or json')
    parser.add_argument('-c', '--config',
                        help='Repo config file path',
                        default='./repos.yaml')
    # parser.add_argument('--delete_phi',
    #                     help='Remove original data with PHI from local after anonymization',
    #                     action='store_true',
    #                     default=False)
    # parser.add_argument('--delete_deidentified',
    #                     help='Remove deidentified data from local after download',
    #                     action='store_true',
    #                     default=False)
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')


    p = parser.parse_args()

    if os.path.isfile(p.config):
        f = open(p.config, 'r')
        y = yaml.load(f)
        print y
        p.local = y['local']
        p.remote = y['remote']
        f.close()

    return p



f = open('repos.yaml', 'r')
repos_config = yaml.load(f)
f.close()

studies_json = '{"1234abcdXX":{"subject_id": "my_patient9a", "project_id": "protect3d", "study_type": "baseline-ABC", "local_file": "/Users/derek/Desktop/xnat_test/sample1"}}'
studies_yaml = """
1234abcdXXY:
  subject_id: my_patient10
  project_id: protect3d
  study_type: baseline-ABCD
  local_file: /Users/derek/Desktop/xnat_test/sample1
"""
study_config = yaml.load(studies_yaml)
opts = None

def clear_queries(interface):
    pass
    # for q in DoGet(_REMOTE, '/queries'):
    #     DoDelete(_REMOTE, '/queries/%s' % q)

def query(interface, aetitle=None, subject_id=None, subject_name=None, study_date=None, study_description=None, accession_number=None ):

    # See <https://bitbucket.org/sjodogne/orthanc-tests/src/e07deb07289db660bac3bc6421a769264ca9929f/Tests/Tests.py?at=default#Tests.py-1428>

    # Formulate the query
    q={}
    if subject_id:
        q['PatientID'] = subject_id
    if subject_name:
        q['PatientName'] = subject_name
    if study_date:
        q['StudyDate'] = study_date
    if study_description:
        q['StudyDescription'] = study_description
    if accession_number:
        q['AccessionNumber'] = accession_number
    # TODO: Should be able to do imaging 'modality' too

    data = json.dumps({'Level': 'Study', 'Query': q})

    if aetitle:
        s = urljoin(interface.address, 'modalities', aetitle, 'query')
        r = requests.post(s, data=data, auth=interface.auth)
        logger.info(r.status_code)
        qid = r.json()['ID']
        logger.info('qid: ' + qid)
        return qid
    else:
        s = urljoin(interface.address, 'tools/find')
        r = requests.post(s, data=data, auth=interface.auth)
        logger.info(r.status_code)
        sids = r.json()
        logger.info(sids)
        return sids

def view_query_results(proxy_interface, qid, which):

    r = requests.get(proxy_interface.address + '/queries', auth=('derek','3dlab'))
    logger.info(r.request)
    logger.info(r.status_code)
    logger.info(r.text)

    r = requests.get(proxy_interface.address + '/queries/%s/answers' % qid)
    logger.info(r.status_code)
    logger.info(r.text)

    r = requests.get(proxy_interface.address + '/queries/%s/answers/%s/content?simplify' % (qid,which))
    logger.info(r.status_code)
    logger.info(r.text)


def retrieve_query_results(proxy_interface, qid, which):

    r = requests.post(proxy_interface.address + '/queries/%s/answers/%s/retrieve' % (qid, which), data=proxy_interface.aetitle)
    logger.info(r.status_code)
    logger.info(r.text)


if __name__ == "__main__":

    # DICOM Server
    source_name = "deathstar"
    source0 = RepoInterface.get_interface_for_config(source_name, repos_config)
    logger.info('Studies on ' + source_name + ' : ' + '%s' % source0.studies())

    # # Orthanc REST proxy
    # source_name = "3dlab-dev1"
    # source1 = RepoInterface.get_interface_for_config(source_name, repos_config)
    #
#    qid = query(source0, aetitle='GEPACS', subject_name='DOE^JOHN*')
#     qid = 'C94BF2FF-7276-4539-A12E-037A75B68426'
#     view_query_results(source0, qid, 0)
#     retrieve_query_results(source0, qid, 0)

    sids = query(source0, subject_name='DOE^JOHN*')
    logger.info(sids[0])
    study = source0.study_from_id(sids[0])
    source0.download_study_archive(study, 'my_archive')

    exit()

    opts = get_args()

    # Get this from command line
    function = "copy-study"
    source_name = "local"
    target_name = "lunney@xnat-dev"
    study_id = "1234abcdXXY"

    if function == "find-study":
        find_study(source_name, study_id)
    if function == "copy-study":
        copy_study(source_name, target_name, study_id)
    elif function == "delete-study":
        delete_study(source_name, study_id)
    elif function == "move-study":
        copy_study(source_name, target_name, study_id)
        delete_study(source_name, study_id)
    elif function == "mirror-repo":
        mirror_repo(source_name, target_name)
    else:
        logger.warn("Unknown function request")
