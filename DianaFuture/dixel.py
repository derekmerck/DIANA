import dcache
import dicom
from PIL import Image as PILImage
import StringIO
from aenum import Enum, auto
import logging
import os
import subprocess
from pprint import pformat
import binascii
from hashlib import sha1
from dateutil import parser

def normalize_date(date_str):
    return parser.parse(date_str)

"""
Patients are identified as the SHA-1 hash of their PatientID tag (0010,0020).
Studies are identified as the SHA-1 hash of the concatenation of their PatientID tag (0010,0020) and their StudyInstanceUID tag (0020,000d).
Series are identified as the SHA-1 hash of the concatenation of their PatientID tag (0010,0020), their StudyInstanceUID tag (0020,000d) and their SeriesInstanceUID tag (0020,000e).
Instances are identified as the SHA-1 hash of the concatenation of their PatientID tag (0010,0020), their StudyInstanceUID tag (0020,000d), their SeriesInstanceUID tag (0020,000e), and their SOPInstanceUID tag (0008,0018).
  -- http://book.orthanc-server.com/faq/orthanc-ids.html
"""
def orthanc_id(PatientID, StudyInstanceUID, SeriesInstanceUID=None, SOPInstanceUID=None):
    if not SeriesInstanceUID:
        s = "|".join([PatientID, StudyInstanceUID])
    elif not SOPInstanceUID:
        s = "|".join([PatientID, StudyInstanceUID, SeriesInstanceUID])
    else:
        s = "|".join([PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID])
    h = sha1(s)
    d = h.hexdigest()
    return '-'.join(d[i:i+8] for i in range(0, len(d), 8))


def test_hashing():

    ptid=   '80'
    stuid=  '14409.67140509640117601730783110182492517466'
    seruid= '14409.180696748118693976707516603316459807766'
    instuid='14409.251659350131093564476016562599266393167'
    id = orthanc_id(ptid, stuid, seruid, instuid)
    correct=  "c3a46d9f-20409d48-aee91522-34e3e1e9-958f34b2"
    assert( id==correct )


class DLVL(Enum):
    """
    Enumerated DICOM service levels
    """
    INSTANCES = auto()
    SERIES = auto()
    STUDIES = auto()
    PATIENTS = auto()

    def child(self):
        if self==DLVL.STUDIES:
            return DLVL.SERIES
        elif self==DLVL.SERIES:
            return DLVL.INSTANCES
        else:
            logging.warn("Bad child request for {}".format(self))

    def __str__(self):
        return '{0}'.format(self.name.lower())


class Dixel(dcache.Persistent):

    @classmethod
    def read_dcm(cls, key, data):

        def is_dicom(fp):

            with open(fp, 'rb') as f:
                f.seek(0x80)
                header = f.read(4)
                magic = binascii.hexlify(header)
                if magic == "4449434d":
                    # logging.debug("{} is dcm".format(fp))
                    return True
            # logging.debug("{} is NOT dcm".format(fp))
            return False

        dcm_fp = key
        if not is_dicom(dcm_fp):
            raise Exception("Not a DCM file: {}".format(dcm_fp))
        # logging.debug("Reading DCM file")
        tags = dicom.read_file(dcm_fp, stop_before_pixels=True)
        # Don't want to save complex data types in cache
        _data = {'PatientID':        tags[0x0010, 0x0020].value,
                'AccessionNumber':   tags[0x0008, 0x0050].value,
                'StudyInstanceUID':  tags[0x0020, 0x000d].value,
                'SeriesInstanceUID': tags[0x0020, 0x000e].value,
                'SOPInstanceUID':    tags[0x0008, 0x0018].value,
                'TransferSyntaxUID': tags.file_meta.TransferSyntaxUID,
                'TransferSyntax':    str(tags.file_meta.TransferSyntaxUID),
                'MediaStorage':      str(tags.file_meta.MediaStorageSOPClassUID),
                'FilePath':          dcm_fp}
        return _data

    @classmethod
    def remap_montage_keys(cls, key, data):
        _data = {'PatientID':         data.get("Patient MRN"),
                'PatientFirstName':   data.get("Patient First Name"),
                'PatientLastName':    data.get("Patient Last Name"),
                'AccessionNumber':    data.get("Accession Number"),
                'OrderCode':          data.get("Exam Code"),
                'PatientStatus':      data.get("Patient Status"),
                'ReportText':         data.get("Report Text"),
                'ReferringPhysicianName': data.get('Ordered By'),
                'Organization':       data.get('Organization'),
                'StudyDescription':   data.get('Exam Description'),
                'PatientSex':         data.get('Patient Sex'),
                'PatientAge':         data.get('Patient Age')
                 }
        if data.get('Exam Completed Date'):
            _data['StudyDate']=       normalize_date(data["Exam Completed Date"])
        if data.get('radcat'):
            _data['Radcat'] =         data.get("radcat")
        if data.get('CancerStatus'):
            _data['CancerStatus'] = data.get("CancerStatus")

        # Preserve any reserved keys
        for k in data.keys():
            if k.startswith('_'):
                _data[k] = data[k]

        return _data

    @classmethod
    def remap_copath_keys(cls, key, data):

        _data = {
                'PatientFirstName':   data.get("FIRST"),
                'PatientLastName':    data.get("LAST"),
                'PathologyCase':      data.get("CASE"),
                'PathologyDate':      normalize_date(data["SIGNOUT DATE"])}
        if data.get('CancerStatus'):
            _data['CancerStatus'] =   data.get("CancerStatus")

        # Preserve any reserved keys
        for k in data.keys():
            if k.startswith('_'):
                _data[k] = data[k]

        return _data

    def __init__(self, key, data=None, cache=None, init_fn=None, remap_fn=None, dlvl=DLVL.STUDIES, ro=False):
        super(Dixel, self).__init__(key, data=data, cache=cache, init_fn=init_fn, remap_fn=remap_fn, ro=ro)
        if not self.data.get('_dlvl'):
            self.dlvl = dlvl
        self.persist()
        self.logger = logging.getLogger("Dixel<{}>".format(key))

    @property
    def dlvl(self):
        return DLVL[self.data['_dlvl'].upper()]

    @dlvl.setter
    def dlvl(self, value):
        self.data['_dlvl'] = str(value)

    def write_image(self, file_data, save_dir=None):

        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)

        file_like = StringIO.StringIO(file_data)
        ds = dicom.read_file(file_like)

        if ds.Modality != "US":
            logging.warn("Skipping non-ultrasound data")
            return

        try:
            pixels = ds.pixel_array
            if ds[0x0028, 0x0004].value == "RGB":
                pixels = pixels.reshape([pixels.shape[1], pixels.shape[2], 3])
        except NotImplementedError:
            logging.warn("Skipping bogus data format")
            return

        try:
            im = PILImage.fromarray(pixels)
            fn = self.oid() + '.png'  # Single file
            fp = os.path.join( save_dir, fn )

            if ds.Modality == "US":
                # Crop out annotations
                w, h = im.size
                im = im.crop((150, 100, w - 100, h - 100))

            im.save(fp)
        except TypeError:
            logging.warn("PIL can not handle images of type {}, falling back to DCM".format(ds[0x0028, 0x0004].value))
            self.data['PatientID'] = self.oid()
            self.write_file(file_data, save_dir)

    def write_file(self, file_data, save_dir=None):
        save_dir = save_dir or os.path.split( self.data.get('FilePath') )[0]

        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)

        if self.dlvl == DLVL.INSTANCES:
            fn = self.data['PatientID'] + '.dcm'  # Single file
        else:
            fn = self.data['PatientID'] + '.zip'  # Archive format
        fp = os.path.join(save_dir, fn)
        with open(fp, 'wb') as f:
            f.write(file_data)

    def read_file(self, compress=False):

        fp = self.data.get('FilePath')

        if self.dlvl != DLVL.INSTANCES:
            self.logger.warn("Can only return file for instance level")
            return

        elif not fp:
            self.logger.warn("Can only return file for instances with a 'FilePath' data element")
            return

        elif compress:
            if "VR" in self.data['TransferSyntax'] and \
                "SR" not in self.data['MediaStorage'] and \
                "Secondary" not in self.data['MediaStorage'] and \
                "Raw" not in self.data['MediaStorage']:

                # Compress w gdcm
                fn = os.path.split(fp)[-1]
                self.logger.debug('Compressing {}'.format(fn))

                fpz = os.path.join("/tmp", "{}.compressed".format(fn))
                ret_code = subprocess.call(['gdcmconv', '-U', '--j2k', fp, fpz])

                if ret_code != 0:
                    # TODO: Capture these for analysis
                    self.logger.warn("Bad exit code ({}) from gdcmconv".format(ret_code))
                    return

                with open(fpz, "rb") as f:
                    ret = f.read()
                os.remove(fpz)
                return ret

            else:
                self.logger.debug(pformat(self.data))
                self.logger.warn("Dixel is not JPG2K compressable - returning uncompressed file")

        with open(fp) as f:
            return f.read()

    def oid(self, dlvl=None):
        # This is not a property because a dixel can generate the OID for any higher level
        # - instances can return instance(default), series, study
        # - series can return series (default), study
        # - studies can return study (default)

        if not dlvl and self.data.get('OID'):
            return self.data.get('OID')

        dlvl = dlvl or self.dlvl

        if dlvl == DLVL.STUDIES:
            return orthanc_id(self.data["PatientID"],
                              self.data["StudyInstanceUID"])
        elif dlvl == DLVL.SERIES:
            return orthanc_id(self.data["PatientID"],
                              self.data["StudyInstanceUID"],
                              self.data["SeriesInstanceUID"])
        elif dlvl == DLVL.INSTANCES:
            return orthanc_id(self.data["PatientID"],
                              self.data["StudyInstanceUID"],
                              self.data["SeriesInstanceUID"],
                              self.data["SOPInstanceUID"])


def test_dixel_caching():

    R = dcache.RedisCache(db=15)
    Q = dcache.RedisCache(db=15)

    dcm_fp = "../tests/data/ct_scout_01.dcm"
    d = Dixel(dcm_fp, cache=R, dlvl=DLVL.INSTANCES, init_fn=Dixel.read_dcm)
    e = Dixel(dcm_fp, cache=Q)

    # logging.debug(d.data)
    # logging.debug(e.data)

    assert(d.data == e.data)



if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    # Read montage dixels
    M = dcache.CSVCache(fp="/Users/derek/Desktop/test_3.csv",
                        key_field="Accession Number")

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
