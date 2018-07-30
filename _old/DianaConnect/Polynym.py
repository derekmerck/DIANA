# Polynym extends `dict` to provide a set of ids for different contexts
# Alternate id's can be automatically generated with context_map_rules
#
# Dicom hierarchical node types are derived with pseudoanonymization rules
# and parent/child relationships

import hashlib
import logging
import GID_Mint


class Polynym(dict):

    @staticmethod
    def identity_rule(s):
        return s

    @staticmethod
    def md5_rule(s):
        return hashlib.md5(s).hexdigest()

    def __init__(self, **kwargs):
        super(Polynym, self).__init__(**kwargs)
        self.context_maps = {}
        # if self['anonymized']:
        #     # Set all mappings to identity
        #     self['override_rule'] = Polynym2.identity_rule

    @property
    def anonymized(self):
        return self.get('anonymized', False)

    def add_map(self, source, target, rule):
        if self.context_maps.get(source):
            self.context_maps[source].update({target: rule})
        else:
            self.context_maps[source] = {target: rule}
        self.apply_rules()

    def apply_rules(self):
        for source, mapping in self.context_maps.iteritems():
            for target, rule in mapping.iteritems():
                value = self.get(source)
                if value:
                    dict.__setitem__(self, target, rule(value))

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.apply_rules()

    def __cmp__(self, other):
        # Polynyms are considered equivalent if they share _hashed_id_ (same value and rule)
        if self.get('hashed_id') == other.get('hashed_id'):
            return True
        else:
            return False


class HierarchicalPolynym(Polynym):

    def __init__(self, **kwargs):
        super(HierarchicalPolynym, self).__init__(**kwargs)
        self.parent = kwargs.get('parent')
        self.children = kwargs.get('children', [])
        self.data = kwargs.get('data')


class DicomSeries(HierarchicalPolynym):

    relevant_keys = ['series_id', 'anonymized']

    def __init__(self, **kwargs):
        filtered_kwargs = {k: v for (k, v) in kwargs.iteritems() if k in self.relevant_keys}
        super(DicomSeries, self).__init__(**filtered_kwargs)
        self.parent = kwargs.get('study', DicomStudy(**kwargs))
        self.study.children.append(self)

    @property
    def series_id(self):
        return self.get('series_id')

    @property
    def study(self):
        return self.parent

    @study.setter
    def study(self, value):
        self.parent = value

    @property
    def subject(self):
        return self.study.subject

    @subject.setter
    def subject(self, value):
        self.parent.parent = value


class DicomStudy(HierarchicalPolynym):

    relevant_keys = ['study_id', 'accession_number', 'anonymized']

    def hashed_accession_rule(self, _id):
        return GID_Mint.get_gid({'accession_number': _id})
        # return Polynym2.md5_rule(id)

    def __init__(self, **kwargs):
        filtered_kwargs = {k: v for (k, v) in kwargs.iteritems() if k in self.relevant_keys}
        super(DicomStudy, self).__init__(**filtered_kwargs)

        if self.anonymized:
            self.add_map('accession_number', 'hashed_id', Polynym.identity_rule)
        else:
            self.add_map('accession_number', 'hashed_id', self.hashed_accession_rule)
        self.apply_rules()
        self.parent = kwargs.get('subject', DicomSubject(**kwargs))
        self.subject.children.append(self)

    @property
    def study_id(self):
        return self.get('study_id')

    @property
    def subject(self):
        return self.parent

    @subject.setter
    def subject(self, value):
        self.parent = value

    @property
    def hashed_id(self):
        return self.get('hashed_id')


class DicomSubject(HierarchicalPolynym):

    relevant_keys = ['subject_id', 'subject_name', 'dob', 'yob', 'gender', 'project_id', 'anonymized']

    def hashed_subject_id_rule(self, subject_name):
        return GID_Mint.get_gid({'pname': subject_name})

    def pseudo_subject_name_rule(self, dummy):
        # Requires hashed_id is already set
        if not self.get('hashed_id'):
            self['hashed_id'] = self.hashed_subject_id_rule(self['subject_name'])
        return GID_Mint.get_pname_for_gid({'gid': self['hashed_id']})

    def pseudo_subject_dob_rule(self, dob):
        # Requires hashed_id is already set
        if not self.get('hashed_id'):
            self['hashed_id'] = self.hashed_subject_id_rule(self['subject_name'])
        return GID_Mint.get_pdob_for_dob_and_gid({'gid': self['hashed_id'], 'dob': dob})

    def __init__(self, **kwargs):
        filtered_kwargs = {k: v for (k, v) in kwargs.iteritems() if k in self.relevant_keys}
        super(DicomSubject, self).__init__(**filtered_kwargs)

        # XNAT subjects are associated with research projects
        # (and diferent projects may have different anonymization rules)
        self.project_id = kwargs.get('project_id', 'root')

        if self.anonymized:
            self.add_map('subject_name', 'pseudonym',  Polynym.identity_rule)
            self.add_map('subject_id',   'hashed_id',  Polynym.identity_rule)
            self.add_map('dob',          'pseudo_dob', Polynym.identity_rule)
        else:
            self.add_map('subject_name', 'hashed_id',  self.hashed_subject_id_rule)
            self.add_map('hashed_id',    'pseudonym',  self.pseudo_subject_name_rule)
            self.add_map('dob',          'pseudo_dob', self.pseudo_subject_dob_rule)
        self.apply_rules()

    @property
    def subject_id(self):
        return self.get('subject_id')

    @property
    def pseudonym(self):
        return self.get('pseudonym')


def test_polynym2():

    logger = logging.getLogger('Polynym2')

    p = Polynym()
    p.add_map(('test', 0),    ('test1', 1), Polynym.md5_rule)
    p.add_map(('test', 0),    ('test2', 2), Polynym.md5_rule)
    p.add_map( 'test_single',  'test_copy', Polynym.identity_rule)

    p['test', 0]     = 'TEST_VALUE1'
    p['test_single'] = 'TEST_VALUE2'

    assert(p['test1', 1] == 'd0ddaea916cb15a6f0a675a1d2e53029')
    assert(p['test2', 2] == 'd0ddaea916cb15a6f0a675a1d2e53029')
    assert(p['test_copy'] == 'TEST_VALUE2')

    logger.info(p)


def test_dicom_nodes():

    logger = logging.getLogger('DICOM/Polynym')

    t = DicomSubject(subject_name='Merck PhD^Derek', dob='19710101')
    # logger.debug(t)
    assert(t.pseudonym == 'Fortinbras^Quickly^S^King^IV')

    u = DicomStudy(accession_number='12345678', subject_name='Merck PhD^Derek', dob='19710101')
    # logger.debug(u)
    # logger.debug(u.subject)
    assert(u.hashed_id == '554XZAIY6AW7W')
    assert(u.subject.pseudonym == 'Fortinbras^Quickly^S^King^IV')

    v = DicomSeries(series_id='XYZ', accession_number='12345678', subject_name='Merck PhD^Derek', dob='19710101')

    logger.debug(v)
    logger.debug(v.study)
    logger.debug(v.subject)

    assert(v.series_id == 'XYZ')
    assert(v.study.hashed_id == '554XZAIY6AW7W')
    assert(v.subject.pseudonym == 'Fortinbras^Quickly^S^King^IV')

    logger.debug(v.subject.children[0].children[0])
    assert(v.subject.children[0].children[0].series_id == 'XYZ')


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    test_polynym2()
    test_dicom_nodes()
