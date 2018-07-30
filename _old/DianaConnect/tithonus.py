'''
In progress...

Tithonus

Gatekeeper script for mirroring deidentified and reformatted medical images
(Named after _P. Tithonus_, the Gatekeeper butterfly)

[Derek Merck](derek_merck@brown.edu)
Spring 2015

<https://github.com/derekmerck/Tithonus>

Dependencies: requests, PyYAML, beautifulsoup4, GID_Mint

See README.md for usage, notes, and license info.
'''

import logging
import argparse
import os
import yaml

__package__ = "tithonus"
__description__ = "Gatekeeper script for mirroring deidentified and reformatted medical images"
__url__ = "https://github.com/derekmerck/Tithonus"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '2', '3')
__version__ = '.'.join(__version_info__)
logger = logging.getLogger('Tithonus CLI')

from Interface import Interface


# Effectively reduces the problem to implementing a generic query, copy, and delete for each interface
def find(source, query):
    return source.find(query['level'], query['Query'])


def copy(source, target, worklist, anonymize=False):
    if isinstance(source, basestring):
        # It's a local file being uploaded
        target.copy(worklist, source, target, anonymize)
    else:
        source.copy(worklist, source, target, anonymize)


def delete(source, worklist):
    source.delete(worklist)


def move(source, target, worklist, anonymize=False ):
    copy(source, target, worklist, anonymize)
    delete(source, worklist)


def mirror(source, target, query, anonymize=False):
    worklist = find(source, query)
    copy(source, target, worklist, anonymize)


def transfer(source, target, query, anonymize=False):
    worklist = find(source, query)
    move(source, target, worklist, anonymize)


def read_yaml(fn):
    with open(fn, 'r') as f:
        y = yaml.load(f)
        f.close()
        return y


def get_args():
    """Setup args and usage"""
    parser = argparse.ArgumentParser(description='Tithonus Core')

    parser.add_argument('command',
                        choices=['find', 'copy', 'delete', 'move', 'mirror', 'transfer'])
    parser.add_argument('source',
                        help='Source/working image repository as json or ID in config')
    parser.add_argument('target',
                        help='Target image repository as json or as ID in config')
    parser.add_argument('-i', '--input',
                        help='Worklist of items to process or query/filter as json, yaml, or csv file')
    parser.add_argument('-o', '--outfile',
                        help='File for output worklist from "find" function')
    parser.add_argument('-a', '--anonymize',
                        help='Anonymize patients and studies before copy/move (if source is orthanc-type)',
                        action='store_true',
                        default='False')
    parser.add_argument('-c', '--config',
                        help='Image repository configuration file',
                        default='./repo.yaml')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    p = parser.parse_args()

    p.config = 'repo.yaml'
    logger.info('Reading %s' % p.config)
    if os.path.isfile(p.config):
        p.y = read_yaml(p.config)
        logger.info('Read config: \n', p.y)

    return p

from nose.plugins.skip import SkipTest

def test_dicom_download_production():
    # Example of how to download a worklist of series.
    #
    # Format worklist like this:
    #
    # SeriesInstanceUIDs:
    #   - x.y.zzz.wwwwww.u.ttt.s.aaaaaaaaaaa....
    #   - x.y.zzz.wwwwww.u.ttt.s.aaaaaaaaaab....
    #
    # Can search for "Series/Study/PatientInstanceUID", "AccessionNumber", "PatientName" or "PatientID"

    raise SkipTest

    repos = read_yaml('repos.yaml')

    source = Interface.factory('gepacs', repos)
    target = Interface.factory('deathstar', repos)

    # worklist_config = read_yaml('series_worklist.yaml')['SeriesInstanceUIDs']
    #
    # for entry in worklist_config:
#    w = source.find('study', {'AccessionNumber': 'R13851441'})[0]
    u = target.find('study', {'AccessionNumber': 'R13851441'})[0]
    #u = target.retreive(w, source)[0]
    target.copy(u, target, '/Users/derek/Desktop/%s_archive' % u.study_id.o)



def test_dicom_download_dev():

    # Test DICOM Download (also in DICOMInterface)

    repos = read_yaml('repos.yaml')

    source = Interface.factory('3dlab-dev0+dcm', repos)
    target = Interface.factory('3dlab-dev1', repos)

    w = source.find('series', {'SeriesInstanceUID': '1.2.840.113654.2.55.4303894980888172655039251025765147023'})
    u = target.retrieve(w[0], source)
    target.copy(u[0], target, 'nlst_tmp_archive')
    assert os.path.getsize('nlst_tmp_archive.zip') == 176070
    os.remove('nlst_tmp_archive.zip')


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_dicom_download_dev()
    exit()

    args = get_args()

    input_data = """
1234abcdXXY:
  project_id: protect3d
  subject_id: my_patient100
  study_id:   my_study-ABCD
  study_type: baseline_minus_10
  local_file: /Users/derek/Desktop/xnat_test/sample1
"""

    command = args.get('command')
    input = yaml.load(input_data)
    worklist = input
    query = input
    anonymize = args.anonymize
    output = args.get('output')

    source = None
    if args.get('source'):
        source_config = args.config[args.get('source')]
        source_config['name'] = args.get('source')
        source = Interface.factory(source_config)

    target = None
    if args.get('target'):
        target_config = args.config[args.get('target')]
        target_config['name'] = args.get('target')
        target = Interface.factory(target_config)

    if command == 'find':
        query = args.input
        find(source, query)
    elif command == 'copy':
        copy(source, target, worklist, anonymize)
    elif command == 'delete':
        delete(source, worklist)
    elif command == 'move':
        move(source, target, worklist, anonymize)
    elif command == 'mirror':
        mirror(source, target, query, anonymize)
    elif command == 'transfer':
        transfer(source, target, query, anonymize)
    else:
        logger.error('Command %s not available')
        raise NotImplementedError
