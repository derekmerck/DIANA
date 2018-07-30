import logging
import os

from Interface import Interface


class DICOMInterface(Interface):

    def __init__(self, **kwargs):
        super(DICOMInterface, self).__init__(**kwargs)

    def find(self, level, question, source=None):
        return self.proxy.find(level, question, self)

    def download_data(self, item):
        self.proxy.copy(item, self, self.proxy)
        self.proxy.download_data(item)


def dicom_tests():

    logger = logging.getLogger(dicom_tests.__name__)

    # Test DICOM Instantiate
    from OrthancInterface import OrthancInterface
    proxy = OrthancInterface(address='http://localhost:8043', name='3dlab-dev1')
    source = DICOMInterface(proxy=proxy, name='3dlab-dev0+dcm')

    # Test DICOM Subject Query
    r = source.find('subject', {'PatientName': 'ZNE*'})[0]
    assert r.subject_id == 'ZA4VSDAUSJQA6'

    # Test DICOM Q/R/DL
    from tithonus import read_yaml
    repos = read_yaml('repos.yaml')

    source = Interface.factory('3dlab-dev0+dcm', repos)
    target = Interface.factory('3dlab-dev1', repos)

    w = source.find('series', {'SeriesInstanceUID': '1.2.840.113654.2.55.4303894980888172655039251025765147023'})[0]
    u = target.retrieve(w, source)[0]
    target.copy(u, target, 'nlst_tmp_archive')
    assert os.path.getsize('nlst_tmp_archive.zip') == 176070
    os.remove('nlst_tmp_archive.zip')

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    dicom_tests()
