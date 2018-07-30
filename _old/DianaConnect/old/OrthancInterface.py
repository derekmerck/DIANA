
# <https://docs.google.com/spreadsheets/d/1muKHMIb9Br-59wfaQbDeLzAfKYsoWfDSXSmyt6P4EM8/pubhtml?gid=525933398&single=true>

from Interface import Interface
from DICOMInterface import DICOMInterface
from HierarchicalData import Series, Study, Subject
import logging
import os


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

        self.logger.debug(series_info)


        # Get study
        study = self.study_from_id(series_info['ParentStudy'])

        # Assemble the series data
        series = Series(series_id=series_info['MainDicomTags'].get('SeriesInstanceUID', 'No ID'), parent=study)
        series.series_id[self] = series_id

        self.series[series_id] = series

        return series

    def study_from_id(self, study_id, subject=None):
        # Check if study is already in interface
        if self.studies.get(study_id):
            return self.studies.get(study_id)

        # Assemble the study data
        study_info = self.do_get('studies', study_id)

        # Get subject
        subject = self.subject_from_id(study_info['ParentPatient'])

        # Assemble the study data
        study = Study(study_id=study_info['MainDicomTags'].get('AccessionNumber', 'No ID'), parent=subject)
        study.study_id[self] = study_id

        self.studies[study_id] = study

        # TODO: Need to grab institution, mdname, to deidentify correctly
        # InstitutionName = 0008,0080
        # ReferringPhysiciansName = 0008,0090

        return study

    def subject_from_id(self, subject_id):
        # Check if study is already in interface
        if self.subjects.get(subject_id):
            return self.subjects.get(subject_id)

        # Assemble the subject data
        subject_info = self.do_get('patients', subject_id)

        subject = Subject(subject_id=subject_info['MainDicomTags'].get('PatientID', 'No ID'),
                          subject_name=subject_info['MainDicomTags'].get('PatientName', 'No Name'),
                          subject_dob=subject_info['MainDicomTags'].get('PatientBirthDate', 'No Date'))
        subject.subject_id[self] = subject_id

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
                    item = Subject(item_data['PatientID'])
                    item.subject_id[source] = (resp_id, a)
                if level == 'study':
                    subject = Subject(item_data['PatientID'])
                    subject.subject_name.o = item_data.get('PatientName')
                    item = Study(item_data['AccessionNumber'])
                    item.study_id[source] = (resp_id, a)
                    item.subject = subject
                elif level == 'series':
                    # subject = Subject(item_data['PatientID'])
                    # subject.subject_name.o = item_data['PatientName']
                    # study = Study(item_data['AccessionNumber'])
                    # study.subject = subject
                    item = Series(item_data['SeriesInstanceUID'])
                    item.series_id[source] = (resp_id, a)
                    # item.study = study
                worklist.append(item)
        else:
            # Add to available studies
            item_data = self.do_post('tools/find', data=data)
            self.logger.debug(item_data)
            if level == 'study':
                item = self.study_from_id(item_data[0])
                item.study_id[self] = item_data[0]
            elif level == 'series':
                item = self.series_from_id(item_data[0])
                item.series_id[self] = item_data[0]
            worklist.append(item)

        return worklist

    def send(self, item, target):
        raise NotImplementedError

    def retreive(self, item, source):
        # Retreiving from DICOM modality or Orthanc peer
        if isinstance(source, DICOMInterface):
            # Copy from modality
            if isinstance(item, Study):
                self.do_post('queries', item.study_id.get(source)[0],
                             'answers', item.study_id.get(source)[1],
                             'retrieve', data=self.aetitle)
            elif isinstance(item, Series):
                self.do_post('queries', item.series_id.get(source)[0],
                             'answers', item.series_id.get(source)[1],
                             'retrieve', data=self.aetitle)
                self.logger.debug('ortho id %s' % item.series_id.o)
                return self.find('series', {'SeriesInstanceUID': item.series_id.o})
            else:
                self.logger.warn('Unknown item type')
        else:
            raise NotImplementedError

    def download_data(self, item):

        if isinstance(item, Study):
            item.data = self.do_get('studies', item.study_id.get(self), 'archive')
        elif isinstance(item, Series):
            item.data = self.do_get('series', item.series_id.get(self), 'archive')
        else:
            self.logger.warn('Unknown item type')

    def upload_data(self, study):
        # If there is study.data, send it.
        # If there is study.available_on_source, retreive it and create a new id
        pass

    def all_studies(self):
        study_ids = self.do_get('studies')
        self.studies = {study_id: self.study_from_id(study_id) for study_id in study_ids}

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
                "0012-0063": "{0} {1} {2}".format(rule_author, rule_name, rule_version) # Deidentification method
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


def orthanc_tests():

    #from nose.plugins.skip import SkipTest

    logger = logging.getLogger(orthanc_tests.__name__)

    # Test Orthanc Instantiate
    source = OrthancInterface(address="http://localhost:8042")
    source.all_studies()
    logger.debug(source.studies)
    assert '163acdef-fe16e651-3f35f584-68c2103f-59cdd09d' in source.studies.keys()

    # TODO: Test Orthanc Query -> Worklist

    # Test Orthanc Download
    if False:
        source.download_archive(source.studies.values()[0], 'orthanc_tmp_archive')
        assert os.path.getsize('orthanc_tmp_archive.zip') == 35884083
        os.remove('orthanc_tmp_archive.zip')

    # TODO: Test Orthanc Upload

    # TODO: Test Orthanc Delete

    # TODO: Test Orthanc Anonymize

    # Test Orthanc Query DICOM node -> Worklist
    source = OrthancInterface(address="http://localhost:8043")
    r = source.find('study', {'PatientName': 'ZNE*'}, '3dlab-dev0')[0]
    assert r.subject.subject_id.o == u'ZA4VSDAUSJQA6'

    # TODO: Test Orthanc Retreive from DICOM


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    orthanc_tests()
