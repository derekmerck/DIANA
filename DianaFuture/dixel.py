import dcache
import dicom
from aenum import Enum, auto
import logging

class DLVL(Enum):
    """
    Enumerated DICOM service levels
    """
    INSTANCES = auto()
    SERIES = auto()
    STUDIES = auto()
    PATIENTS = auto()


class Dixel(dcache.Persistent):

    @classmethod
    def read_dcm(cls, dcm_fp):
        logging.debug("Reading DCM file")
        tags = dicom.read_file(dcm_fp, stop_before_pixels=True)
        data = {'PatientID': tags[0x0010, 0x0020].value,
                'StudyInstanceUID': tags[0x0020, 0x000d].value,
                'SeriesInstanceUID': tags[0x0020, 0x000e].value,
                'SOPInstanceUID': tags[0x0008, 0x0018].value,
                'TransferSyntaxUID': tags.file_meta.TransferSyntaxUID,
                'MediaStorage': tags.file_meta.MediaStorageSOPClassUID,
                'AccessionNumber': tags[0x0008, 0x0050].value,
                'HasPixels': 'PixelData' in tags,
                'FilePath': dcm_fp}
        return data


    @classmethod
    def check_orthanc(cls, oid, orthanc):
        pass


    def __init__(self, key, data=None, cache=None, init_fn=None, dlvl=DLVL.STUDIES):
        self.dlvl = dlvl
        super(Dixel, self).__init__(key, data, cache, init_fn)



if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    R = dcache.RedisCache(db=15, clear=True)

    dcm_fp = "/Users/derek/Desktop/Protect3/37/20000101-CT/Series-1/14409.254617228500857193993507647715712518182"
    d = Dixel(dcm_fp, cache=R, dlvl=DLVL.INSTANCES, init_fn=Dixel.read_dcm)
    # With init function on key
    logging.debug(d.data)
    d.data['exists'] = True
    d.persist()

    Q = dcache.RedisCache(db=15)
    e = Dixel(dcm_fp, cache=Q, dlvl=DLVL.INSTANCES, init_fn=Dixel.read_dcm)
    logging.debug(e.data)

    # Read montage dixels
    M = dcache.CSVCache(fp="/Users/derek/Desktop/test_3.csv",
                        id_field="Accession Number")
    for item in M.cache.itervalues():
        # logging.debug(item)
        f = Dixel(item["Accession Number"], data=item, cache=R, dlvl=DLVL.STUDIES)
        f.data['Important thing'] = "Important data"
        f.persist()

    for item in M.cache.itervalues():
        f = Dixel(item["Accession Number"], cache=R, dlvl=DLVL.STUDIES)
        logging.debug(f.data)

    # f = Dixel(oid, cache=Q,
    #           init_fn=Dixel.check_orthanc, init_args=[orthanc, DLVL.SERIES])
