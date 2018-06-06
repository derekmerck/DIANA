from Interface import Interface
from Polynym import DicomSeries, DicomStudy, DicomSubject
import logging
import pprint
import pydicom


class XNATInterface(Interface):

    var_dict = {'study_type': 'xnat:mrSessionData/fields/field[name=study_type]/field'}

    def __init__(self, **kwargs):
        super(XNATInterface, self).__init__(**kwargs)

        # Intialize the XNAT session
        jsession_key = self.session.do_post('data/JSESSION')
        self.session.headers.update({'JSESSIONID': jsession_key})
        self.session.params.update({'format': 'json'})

    def __del__(self):
        # Close the XNAT session cleanly
        self.session.do_delete('data/JSESSION')

    # TODO: XNAT build series, studies, and subjects correctly
    def series_from_id(self, series_id):
        return DicomSeries(series_id=series_id, anonymized=True)

    def study_from_id(self, study_id, project_id=None):
        return DicomStudy(study_id=study_id, anonymized=True)

    def subject_from_id(self, subject_id, project_id=None):

        r = self.do_get('data/archive/projects', project_id, 'subjects', subject_id)
        subject_info = r.get('items')[0].get('data_fields')

        _subject_id = subject_info.get('ID')
        subject_name = subject_info.get('label')

        # self.logger.info(pprint.pprint(r))

        return DicomSubject(subject_id=_subject_id,
                            subject_name=subject_name,
                            project_id=project_id,
                            anonymized=True)

    def all_studies(self):
        resp = self.do_get('data/experiments')
        # Find all of the data labels
        results = resp.get('ResultSet').get('Result')
        for result in results:
            DicomStudy(study_id=result['ID'])
        count = resp.get('ResultSet').get('totalRecords')
        return count

    def upload_data(self, item):
        # See <https://wiki.xnat.org/display/XKB/Uploading+Zip+Archives+to+XNAT>

        if isinstance(item, DicomStudy) or isinstance(item, DicomSeries):
            params = {'overwrite': 'delete',
                      'project': item.subject.project_id}

            # dest = '/archive/projects/%s/subjects/%s/experiments/%s' % (item.subject.project_id, item.subject.subject_id, item.study_id)
            # params.update({'dest': dest})

            if item.subject.get('subject_id'):
                params.update({'subject': item.subject.subject_id})
            if item.get('study_id'):
                params.update({'session': item.study_id})

            headers = {'content-type': 'application/zip'}
            self.do_post('data/services/import', params=params, headers=headers, data=item.data)
        else:
            self.logger.warn('XNATInterface can only upload study items')

        # TODO: Need to check for upload errors when a duplicate study is pushed.

    def delete(self, worklist):
        # Unfortunately need the project for a delete, but perhaps easier with a 'root' project?

        if not isinstance(worklist, list):
            worklist = [worklist]

        for item in worklist:
            params = {'remove_files': 'true'}
            self.do_delete('data/archive/projects', item.subject.project_id,
                           'subjects', item.subject.subject_id[self],
                           'experiments', item.study_id[self],
                           params=params)

    def upload_archive(self, item, fn, **kwargs):
        # Note that we need _at least_ the project_id or it will go into the prearchive
        if item is None:
            # Make up a dummy study from the kwargs
            item = DicomStudy(**kwargs)

        self.logger.debug(item)
        super(XNATInterface, self).upload_archive(item, fn)

    # XNAT specific

    def set_study_attribute(self, study, key):
        value = study.__dict__[key]
        params = {self.var_dict[key]: value}
        self.do_put('data/archive/projects', study.subject.project_id,
                    'subjects', study.subject.subject_id[self],
                    'experiments', study.study_id[self],
                    params=params)

def xnat_bulk_edit():
    # Example of bulk editing from spreadsheet

    logger = logging.getLogger(xnat_bulk_edit.__name__)

    from tithonus import read_yaml
    repos = read_yaml('repos.yaml')

    source = Interface.factory('xnat-dev', repos)

    import csv
    with open('/Users/derek/Desktop/protect3d.variables.csv', 'rbU') as csvfile:
        propreader = csv.reader(csvfile)
        propreader.next()
        for row in propreader:
            logger.info(', '.join(row))
            subject_id = row[0]
            new_subject_id = '{num:04d}'.format(num=int(subject_id))
            logger.info(new_subject_id)

            params = {'gender': row[1],
                      #'age': row[2],
                      'src': row[3],
                      'label': new_subject_id}
            source.do_put('data/archive/projects/protect3d/subjects', subject_id, params=params)


def bulk_age_deduction():

    logger = logging.getLogger(test_xnat.__name__)

    from tithonus import read_yaml
    repos = read_yaml('repos.yaml')

    source = Interface.factory('xnat-dev', repos)

    s = source.subject_from_id('UOCA0008A', project_id='ava')
    r = source.do_get('data/services/dicomdump?src=/archive/projects', s.project_id, 'subjects', s.subject_id, 'experiments', 'UOCA0008A&field=PatientAge', params={'field1': 'PatientAge', 'field': 'StudyDate'})


def bulk_upload():

    logger = logging.getLogger(test_xnat.__name__)

    from tithonus import read_yaml
    repos = read_yaml('repos.yaml')

    source = Interface.factory('xnat-dev', repos)

    from glob import glob
    worklist = glob('/Users/derek/Data/hydrocephalus_dicom/*.zip')

    for fn in worklist[1:]:
        source.upload_archive(None, fn, project_id='ava')

import re
import dicom
from glob import glob
from datetime import datetime


def deduce_yob(date_str, age_str, fmt='%Y%m%d'):
    logger = logging.getLogger(deduce_yob.__name__)
    age = int(re.search(r'\d+', age_str).group())
    date = datetime.strptime(date_str, fmt).date()
    return date.year-age


def bulk_folder_upload():

    logger = logging.getLogger(bulk_folder_upload.__name__)

    from tithonus import read_yaml
    repos = read_yaml('repos.yaml')

    source = Interface.factory('xnat-dev', repos)

    source.all_studies()

    base_dir = '/Users/derek/Data/ATACH_I'
    subject_worklist = glob('%s/*' % base_dir)
    logger.info(subject_worklist)

    i = 0

    for subject_dir in subject_worklist:
        subsubject_worklist = glob('%s/*' % subject_dir)
        for subsubject_dir in subsubject_worklist:
            study_worklist = glob('%s/*' % subsubject_dir)
            #logger.info(study_worklist)
            for study_dir in study_worklist:

                i = i+1

                #logger.info(study_dir)
                if 'scene' in study_dir.lower(): continue

                # get a dcm file to figure out the subject name, study id, and session type...
                session_worklist = glob('%s/*' % study_dir)
                session_dir = session_worklist[0]
                instance_worklist = glob('%s/*' % session_dir)
                instance_file = instance_worklist[0]

                ds = pydicom.read_file(instance_file)

                #logger.info(ds)

                orig_subject_id = ds.PatientID
                num = int(re.search(r'\d+', orig_subject_id).group())
                suffix_res = re.search(r'[A-Za-z]+', orig_subject_id)

                if suffix_res:
                    suffix = suffix_res.group().upper()
                    if suffix == 'TIER':
                        # Special case for silly ATACH mis-labelling
                        if orig_subject_id.endswith('1'):
                            suffix = 'T1'
                        elif orig_subject_id.endswith('2'):
                            num = 172
                            suffix = 'T2'
                else:
                    suffix = ''

                subject_id = '{num:04d}{suffix}'.format(num=int(num), suffix=str(suffix))

                study_id = ds.AccessionNumber

                study_date_str = ds.StudyDate
                age_str = ds.get('PatientsAge')

                if study_date_str and age_str:
                    yob = deduce_yob(study_date_str, age_str)
                else:
                    yob = None

                logger.info('%s : %s : %s' % (subject_id, study_id, yob))

                if i<=1:
                    continue

                # source.upload_archive(None, study_dir, project_id='atach3d', study_id=study_id, subject_id=subject_id)
                source.upload_archive(None, 'tmp.zip', project_id='atach3d', study_id=study_id, subject_id=subject_id)
                if yob:
                    source.do_put('data/archive/projects/atach3d/subjects', subject_id, params={'yob': yob})


    # TODO: Need to consider 'asserts' for xnat testing

    s = source.subject_from_id('my_patient2', 'mtp01')
    source.do_get('data/archive/projects/mtp01/subjects/my_patient2', params={'format': 'json', 'yob': '1971'})

    t = DicomStudy(subject_id='my_patient3',
                   project_id='mtp01')
    source.upload_archive(t, 'tcia_tmp_archive1.zip')

    logger.info(s)

    # Need to test:
    # 1. xnat-dev is up
    # 2. mtp01 is empty
    # 3. can upload a study to mtp01 w correct subject name, study name, etc.
    # 4. can download the study from mtp01
    pass

import requests

def test_xnat():

    logger = logging.getLogger(bulk_folder_upload.__name__)

    from tithonus import read_yaml
    repos = read_yaml('repos.yaml')

    source = Interface.factory('xnat-dev', repos)

    count = source.all_studies()

    slack_addr = repos['rih3dlab']['address']

    payload = {"text": "<http://xnat-dev.cloudapp.net:8080/xnat|xnat> currently contains {0} studies.".format(count)}
    requests.post(slack_addr, json=payload)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_xnat()
    #bulk_age_deduction()