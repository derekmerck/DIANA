# <https://docs.google.com/spreadsheets/d/1muKHMIb9Br-59wfaQbDeLzAfKYsoWfDSXSmyt6P4EM8/pubhtml?gid=525933398&single=true>

import logging
import os
from Interface import Interface
from Polynym import DicomSeries, DicomStudy, DicomSubject


class OrthancInterface(Interface):

    def __init__(self, **kwargs):
        super(OrthancInterface, self).__init__(**kwargs)

    # Derived Class Implementations
    def series_from_id(self, series_id):
        # Check if series is already in interface
        if self.series.get(series_id):
            return self.series.get(series_id)

        # Assemble the study data
        series_info = self.do_get('series', series_id)
        series_tags = self.do_get('series', series_id, 'shared-tags')

        if series_tags.get('0012,0062').get('Value') == "YES":
            anonymized = True
        else:
            anonymized = False

        # Get study
        study = self.study_from_id(series_info['ParentStudy'])

        # Assemble the series data
        series = DicomSeries(series_id=series_info['MainDicomTags'].get('SeriesInstanceUID', 'No ID'),
                             anonymized=anonymized,
                             study=study)
        series['series_id', self] = series_id

        # Add series to the interface
        self.series[series_id] = series
        return series

    def study_from_id(self, study_id):
        # Check if study is already in interface
        if self.studies.get(study_id):
            return self.studies.get(study_id)

        # Assemble the study data
        study_info = self.do_get('studies', study_id)
        study_tags = self.do_get('studies', study_id, 'shared-tags')

        if study_tags.get('0012,0062',{}).get('Value') == "YES":
            anonymized = True
        else:
            anonymized = False

        # self.logger.info('Tags: %s' % study_tags['0012,0062']['Value'])

        # Get subject
        subject = self.subject_from_id(study_info['ParentPatient'])

        # Assemble the study data
        study = DicomStudy(study_id=study_info['MainDicomTags'].get('AccessionNumber', 'No ID'),
                           anonymized=anonymized,
                           subject=subject)
        study['study_id', self] = study_id

        self.studies[study_id] = study
        return study

    def subject_from_id(self, subject_id):
        # Check if study is already in interface
        if self.subjects.get(subject_id):
            return self.subjects.get(subject_id)

        # Assemble the subject data
        subject_info = self.do_get('patients', subject_id)
        subject_tags = self.do_get('patients', subject_id, 'shared-tags')

        # Check deidentification status
        if subject_tags.get('0012,0062',{}).get('Value') == "YES":
            anonymized = True
        else:
            anonymized = False

        subject = DicomSubject(subject_id=subject_info['MainDicomTags'].get('PatientID', 'No ID'),
                               subject_name=subject_info['MainDicomTags'].get('PatientName', 'No Name'),
                               subject_dob=subject_info['MainDicomTags'].get('PatientBirthDate', 'No Date'),
                               anonymized=anonymized)
        subject['subject_id', self] = subject_id

        # Add subject to the interface
        self.subjects[subject_id] = subject
        return subject

    def find(self, level, query, source=None):
        if isinstance(source, Interface):
            source_name = source.name
        else:
            source_name = source

        if level.lower() == 'subject' or level.lower() == 'patient':
            level_name = 'Patient'
        elif level.lower() == 'study':
            level_name = 'Study'
        elif level.lower() == 'series':
            level_name = 'Series'
        else:
            self.logger.warn('No level associated with %s ' % level)
            level_name = None

        data = {'Level': level_name, 'Query': query}
        worklist = []

        if source:
            # Checking a different modality
            resp_id = self.do_post('modalities', source_name, 'query', data=data).get('ID')

            answers = self.do_get('queries', resp_id, 'answers')
            for a in answers:
                # Add to available studies, flag as present on source
                item_data = self.do_get('queries', resp_id, 'answers', a, 'content?simplify')
                item = None
                if level == 'subject':
                    item = DicomSubject(subject_id=item_data.get('PatientID'),
                                        subject_name=item_data.get('PatientName'))
                    item['subject_id', source] = (resp_id, a)
                if level == 'study':
                    subject = DicomSubject(subject_id=item_data.get('PatientID'),
                                           subject_name=item_data.get('PatientName'))
                    item = DicomStudy(study_id=item_data['AccessionNumber'], subject=subject)
                    item['study_id', source] = (resp_id, a)
                elif level == 'series':
                    subject = DicomSubject(subject_id=item_data.get('PatientID'),
                                           subject_name=item_data.get('PatientName'))
                    study = DicomStudy(accession_number=item_data['AccessionNumber'], subject=subject)
                    item = DicomSeries(series_id=item_data['SeriesInstanceUID'], study=study)
                    item['series_id', source] = (resp_id, a)
                    # item.study = study
                worklist.append(item)
        else:
            # Add to available studies
            item = None
            item_data = self.do_post('tools/find', data=data)
            self.logger.debug('Local find: %s' % item_data)
            if level == 'study':
                item = self.study_from_id(item_data[0])
                item['study_id', self] = item_data[0]
            elif level == 'series':
                item = self.series_from_id(item_data[0])
                item['series_id', self] = item_data[0]
            worklist.append(item)

        return worklist

    def delete(self, worklist):
        if not isinstance(worklist, list):
            worklist = [worklist]

        for item in worklist:
            if isinstance(item, DicomStudy):
                self.do_delete('studies', item['study_id', self])
                self.studies[item.study_id] = None
                # TODO: Should delete series as well
            elif isinstance(item, DicomSeries):
                self.do_delete('series', item['series_id', self])
                self.series[item.series_id] = None
            elif isinstance(item, DicomSubject):
                self.do_delete('patients', item['subject_id', self])
                self.subjects[item.subject_id] = None
                # TODO: Should delete studies and series as well
            else:
                self.logger.warn('Unknown Dicom item requested for delete')

    def send(self, item, target):
        raise NotImplementedError

    def retrieve(self, item, source):
        # Retrieving from DICOM modality or Orthanc peer
        if isinstance(item, DicomStudy):
            self.do_post('queries', item.get(('study_id', source))[0],  # id, source = (q,a)
                         'answers', item.get(('study_id', source))[1],
                         'retrieve', data=self.aetitle)
            self.logger.debug('Study id: %s' % item.study_id)
            return self.find('study', {'StudyInstanceID': item.study_id, 'PatientID': item.subject.subject_id})
        elif isinstance(item, DicomSeries):
            self.do_post('queries', item.get(('series_id', source))[0],
                         'answers', item.get(('series_id', source))[1],
                         'retrieve', data=self.aetitle)
            self.logger.debug('Series id: %s' % item.series_id)
            return self.find('series', {'SeriesInstanceUID': item.series_id, 'PatientID': item.subject.subject_id})
        else:
            self.logger.warn('Unknown item type requested for retreive')

    def download_data(self, item):

        if isinstance(item, DicomStudy):
            item.data = self.do_get('studies', item.get(('study_id', self)), 'archive')
        elif isinstance(item, DicomSeries):
            item.data = self.do_get('series', item.get(('series_id', self)), 'archive')
        else:
            self.logger.warn('Unknown item type requested for download')

    def upload_data(self, study):
        # TODO: Implement Orthanc.upload_data
        raise NotImplementedError

    def all_studies(self):
        # Reset study index
        self.studies = {}
        study_ids = self.do_get('studies')
        for study_id in study_ids:
            self.study_from_id(study_id)

    def all_subjects(self):
        # Reset subjects index
        self.subjects = {}
        subject_ids = self.do_get('patients')
        for subject_id in subject_ids:
            self.subject_from_id(subject_id)

    # Orthanc ONLY functions

    def anonymize(self, study):

        rule_author = "RIH 3D Lab"
        rule_name = "General DICOM Deidentification Rules"
        rule_version = "v1.0"

        anon_script = {
            "Replace": {
                "0010-0010": study.subject.subject_name.a,  # PatientsName
                "0010-0020": study.subject.subject_id.a,    # PatientID
                "0010-0030": study.subject.subject_dob.a,   # PatientsBirthDate
                "0008-0050": study.study_id.a,              # AccessionNumber
                "0012-0062": "YES",                         # Deidentified
                "0010-0021": rule_author,                   # Issuer of Patient ID
                "0012-0063": "{0} {1} {2}".format(rule_author, rule_name, rule_version)  # Deidentification method
                },
            "Keep": [
                "0008-0080",                                # InstitutionName
                "0010-0040",                                # PatientsSex
                "0010-1010",                                # PatientsAge
                "StudyDescription",
                "SeriesDescription"],
            "KeepPrivateTags": None
            }

        anon_study_id = self.do_post('studies', study.study_id[self], 'anonymize', data=anon_script)['ID']
        # Can unlink original data
        study.study_id[self, 'original'] = study.study_id[self]
        study.study_id[self] = anon_study_id

def test_orthanc_juniper():

    logger = logging.getLogger(orthanc_tests2.__name__)
    from tithonus import read_yaml

    repos = read_yaml('repos.yaml')
    source = Interface.factory('deathstar+lsmaster', repos)

    source.all_studies()

def orthanc_tests2():

    logger = logging.getLogger(orthanc_tests2.__name__)

    # REST Interface Orthanc
    source = OrthancInterface(address="http://localhost:8043", aetitle='3DLAB-DEV1')

    if False:
        source.all_subjects()

        for item in source.subjects.values():
            source.delete(item)

        source.all_studies()
        assert source.studies == {}

        # Test find in other repo
        item = source.find('study', {'PatientName': 'ZNE*'}, '3dlab-dev0')[0]
        logger.debug(item)

        assert item.subject.subject_id == u'ZA4VSDAUSJQA6'

        source.retrieve(item, '3dlab-dev0')
        # Have to wait for a while for it to show up...

    source.all_studies()

    logger.debug(source.studies)
    assert '163acdef-fe16e651-3f35f584-68c2103f-59cdd09d' in source.studies.keys()

    logger.debug(source.subjects)
    assert 'be8f2869-69326801-e0800ffb-f4a9f179-ad110c47' in source.subjects.keys()

    # Test find in this repo
    item = source.find('study', {'PatientName': 'ZNE*'})[0]
    logger.debug(item.subject)
    assert item.subject.subject_id == u'ZA4VSDAUSJQA6'

    # Test Orthanc Download
    if True:
        source.download_archive(item, 'orthanc_tmp_archive')
        assert os.path.getsize('orthanc_tmp_archive.zip') > 35000000
        os.remove('orthanc_tmp_archive.zip')

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_orthanc_juniper()
#    orthanc_tests2()
