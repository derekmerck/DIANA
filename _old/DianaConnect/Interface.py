import logging
import zipfile
import os
import io

from SessionWrapper import SessionWrapper, JuniperSessionWrapper


class Interface(object):

    # -----------------------------
    # Available DicomData across all interfaces
    # -----------------------------

    available_series = {}
    available_studies = {}
    available_subjects = {}

    # -----------------------------
    # Public factory
    # -----------------------------

    @classmethod
    def factory(cls, name, _config):
        from OrthancInterface import OrthancInterface
        from XNATInterface import XNATInterface
        from DICOMInterface import DICOMInterface
        from MontageInterface import MontageInterface
        from TCIAInterface import TCIAInterface

        # Accepts a config dict and returns an interface
        config = _config[name]
        name = name.split('+')[0]
        if config['type'] == 'xnat':
            return XNATInterface(name=name, **config)
        elif config['type'] == 'orthanc':
            return OrthancInterface(name=name, **config)
        elif config['type'] == 'dicom':
            proxy = Interface.factory(config['proxy'], _config)
            return DICOMInterface(name=name, proxy=proxy, **_config)
        elif config['type'] == 'montage':
            return MontageInterface(name=name, **config)
        elif config['type'] == 'tcia':
            return TCIAInterface(name=name, **config)
        else:
            logger = logging.getLogger(Interface.factory.__name__)
            logger.warn("Unknown repo type '%s' in config", name)
            pass

    # -----------------------------
    # Baseclass __init__
    # -----------------------------

    def __init__(self, **kwargs):
        super(Interface, self).__init__()
        self.address = kwargs.get('address')
        self.aetitle = kwargs.get('aetitle')
        self.auth = (kwargs.get('user'), kwargs.get('pword'))
        self.name = kwargs.get('name', 'None')
        self.name = self.name.split('+')[0]
        self.api_key = kwargs.get('api_key')
        self.proxy = kwargs.get('proxy')
        self.j_proxy = kwargs.get('j_proxy')

        # Create a session/juniper session
        if self.j_proxy is None:
            self.session = SessionWrapper(**kwargs)
        else:
            self.session = JuniperSessionWrapper(**kwargs)

        # Should be "available studies" plus a registry of all studies somewhere else
        self.series = {}
        self.studies = {}
        self.subjects = {}

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info('Created interface')

    # -----------------------------
    # Abstract Public API:
    # - find
    # - send
    # - receive
    # - delete
    # -----------------------------

    def find(self, level, question, source=None):
        # Level is a HDN type: subject, studies, or series
        # Question is a dictionary of property names and values
        # by default, the source is _this_ interface,
        # returns a WORKLIST, a list of session, study, or subject items
        raise NotImplementedError

    def retrieve(self, item, source):
        raise NotImplementedError

    def send(self, item, target):
        raise NotImplementedError

    def delete(self, worklist):
        raise NotImplementedError

    # -----------------------------
    # Abstract Private/Hidden API:
    # - upload_data
    # - download_data
    # - subject_from_id
    # - study_from_id
    # - series_from_id
    # - all_studies (optional)
    # -----------------------------

    # Each interface needs to implement methods for moving data around
    def upload_data(self, item):
        raise NotImplementedError

    def download_data(self, item):
        raise NotImplementedError

    # Factories for HDN types
    def subject_from_id(self, subject_id):
        raise NotImplementedError

    def study_from_id(self, study_id):
        raise NotImplementedError

    def series_from_id(self, series_id):
        raise NotImplementedError

    # Optional but frequently useful shortcut
    def all_studies(self):
        raise NotImplementedError

    # -----------------------------
    # Baseclass Public API:
    # - copy
    # - move
    # - upload_archive
    # - download_archive
    # -----------------------------

    def copy(self, worklist, source, target, anonymize=False):
        # Sends data for items in WORKLIST from the source to the target
        # if the source is self and the target is a string/file, it downloads
        # if the source is a string/file and the target is self, it uploads
        # if the source is a DICOM node and the target is self, it retrieves

        # TODO: Create anonymized study if necessary and delete it when done

        if not isinstance(worklist, list):
            worklist = [worklist]

        for item in worklist:
            # Figure out case
            if isinstance(source, basestring) and (target is None or target is self):
                # It's probably a file being uploaded
                self.upload_archive(item, source)
            elif source is self and isinstance(target, basestring):
                # It's probably a file being downloaded
                self.download_archive(item, target)
            elif source is self:
                # Sending to DICOM modality or Orthanc peer
                self.send(item, target)
            elif target is self:
                self.retrieve(item, source)

    def move(self, worklist, source, target, anonymize=False):
        self.copy(worklist, source, target, anonymize)
        self.delete(worklist)

    def upload_archive(self, item, fn):
        if os.path.isdir(fn):
            self.logger.info('Uploading image folder %s', fn)
            item.data = self.zipdir(fn)
        elif os.path.isfile(fn):
            self.logger.info('Uploading image archive %s', fn)
            f = open(fn, 'rb')
            item.data = f.read()
            f.close()

        self.upload_data(item)

    def download_archive(self, item, fn):
        self.logger.info('Downloading image archive %s', fn)
        self.download_data(item)
        if fn is not None:
            f = open(fn + '.zip', 'wb')
            f.write(item.data)
            f.close()

    # -----------------------------
    # Private/Hidden Helpers
    # - do_get
    # - do_post
    # - do_put
    # - do_delete
    # - do_return
    # - zipdir
    # -----------------------------

    def do_return(self, r):
        return self.session.do_return(r)

    def do_delete(self, *url, **kwargs):
        return self.session.do_delete(*url, **kwargs)

    def do_get(self, *url, **kwargs):
        return self.session.do_get(*url, **kwargs)

    def do_put(self, *url, **kwargs):
        return self.session.do_put(*url, **kwargs)

    def do_post(self, *url, **kwargs):
        return self.session.do_post(*url, **kwargs)

    def zipdir(self, top, fno=None):

        file_like_object = io.BytesIO()
        if fno is None:
            self.logger.info('Creating in-memory zip')
            zipf = zipfile.ZipFile(file_like_object, 'w', zipfile.ZIP_DEFLATED)
        else:
            self.logger.info('Creating zip file')
            zipf = zipfile.ZipFile(fno, 'w', zipfile.ZIP_DEFLATED)

        for dirpath, dirnames, filenames in os.walk(top):
            for f in filenames:
                fn = os.path.join(dirpath, f)
                # self.logger.debug(fn)
                zipf.write(fn, os.path.relpath(fn, top))

        zipf.close()

        if fno is None:
            return file_like_object.getvalue()


def interface_tests():

    logger = logging.getLogger(interface_tests.__name__)

    # Test Interface Instatiate
    interface = Interface(address="http://localhost:8043")
    assert u'163acdef-fe16e651-3f35f584-68c2103f-59cdd09d' in interface.do_get('studies')

    # Test Interface Factory
    interface = Interface.factory('test', {'test': {'type': 'orthanc', 'address': 'http://localhost:8043'}})
    assert u'163acdef-fe16e651-3f35f584-68c2103f-59cdd09d' in interface.do_get('studies')


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    interface_tests()


