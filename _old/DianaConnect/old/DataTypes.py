import logging
logger = logging.getLogger('Tithonus.DataTypes')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class Project(object):

    def __init__(self, project_id):
        self.project_id = project_id


class Subject(object):

    def __init__(self, subject_id, project=None, anonymized=False):
        self.project = project
        self.subject_id = subject_id  # Required

        self.name = ''
        self.dob = ''

        # May be different per context, do we need to keep track separately?
        # Seems like we _only_ care about the anonymized part
        self.anon_subject_id = ''
        self.anon_subject_name = ''
        self.anon_dob = ''

        self.anonymized = anonymized
        if self.anonymized:
            self.anon_subject_id = self.subject_id
            self.anon_subject_name = self.anon_subject_name
            self.anon_dob = self.anon_dob
        else:
            self.anonymize()

        self.site_id = ''  # For multi-center data

    def anonymize(self):
        pass

    # Need to override __equals__ so anonymized and PHI versions are considered to be the same


class Study(object):

    @staticmethod
    def get_study_for_config(study_id, _config):
        # TODO: Need some error checking
        config = _config[study_id]
        project = Project(config['project_id'])
        subject = Subject(config['subject_id'], project)
        study = Study(study_id, subject)
        study.local_file = config['local_file']
        study.study_type = config['study_type']
        return study

    def __init__(self, study_id,
                 subject=None,
                 subject_name=None,
                 subject_id=None,
                 subject_dob=None,
                 anonymized=False,
                 study_type=None,
                 physician=None,
                 institution=None,
                 other_ids=None,
                 local_file=None):

        self.study_id = study_id
        # Should check to see if this is a subject or a subject config

        if subject is None:
            self.subject = Subject(subject_id)
        else:
            self.subject = subject

        self.anonymized = anonymized
        self.physician = physician
        self.study_type = study_type  # Maps to visit_type in XNAT, useful for serial or ordered studies
        self.institution = institution  # Maps to site_id in XNAT
        self.local_file = local_file

        self.anon_study_id = None
        self.anon_physician = None

        self.data = None

        # Indexed as repo:number...
        self.other_ids = other_ids

        if self.anonymized:
            self.anon_study_id = self.study_id
            self.anon_physician = self.physician
        else:
            self.anonymize()

    def anonymize(self):

        # if self.anon_study_id is None:
        #     if self.anonymized:
        #         self.anon_study_id = self.study_id
        #     else:
        #         self.giri = GID_Mint.get_gid({'institution': self.institution, 'record_id': self.accession})
        #
        # if gsid is None and pname is not None and not self.anonymized:
        #     # Placeholder values for deidentification
        #     self.gsid = GID_Mint.get_gid({'pname': self.pname, 'dob': self.dob})
        #     self.ppname = GID_Mint.get_pname_for_gid({'gid': self.gsid})
        #     self.pdob = GID_Mint.get_pdob_for_dob_and_gid({'dob': self.dob, 'gid': self.gsid})
        #     mdgid = GID_Mint.get_gid({'gid': self.mdname})
        #     self.pmdname = GID_Mint.get_pmdname_for_gid({'gid': mdgid})

        pass

    def __str__(self):
        # TODO: Fix this
        return "{0}({1})".format(self.study_id, self.subject.subject_id)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, Study):
            return self.anon_study_id == other.anon_study_id
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.anon_study_id)

    def __cmp__(self, other):
        return self.anon_study_id < other.anon_study_id
