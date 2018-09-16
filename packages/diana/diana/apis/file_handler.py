import os, time
from typing import Union, Sequence
import attr
from diana.apis import Dixel
from diana.utils import Pattern, gateway
from diana.utils.dicom import DicomLevel, dicom_strpdtime


@attr.s
class ReportFile(Pattern):
    location = attr.ib(default=None)
    gateway = attr.ib(init=False)

    @gateway.default
    def connect(self):
        return gateway.TextFile(location=self.location)

    def put(self, item: Dixel, path: str=None, explode: str=None, anonymize: bool=False) -> Dixel:
        fn = item.meta['FileName']

        if anonymize:
            data = item.report.anonymized()
        else:
            data = item.report.text

        if os.path.splitext(fn)[-1:] != ".txt":
            fn = fn + '.txt'

        self.gateway.write(fn, data, path=path, explode=explode )
        return item


@attr.s
class ImageFile(Pattern):
    location = attr.ib(default=None)
    gateway = attr.ib(init=False)

    @gateway.default
    def connect(self):
        return gateway.ImageFile(location=self.location)

    def put(self, item: Dixel, path: str = None, explode: str = None) -> Dixel:
        fn = item.meta['FileName']

        if os.path.splitext(fn)[-1:] != ".png" and \
                os.path.splitext(fn)[-1:] != ".jpg":
            fn = fn + '.png'

        data = item.get_pixels()

        self.gateway.write(fn, data, path=path, explode=explode)
        return item


@attr.s(hash=False)
class DicomFile(Pattern):
    location = attr.ib( default=None )
    gateway = attr.ib( init=False )

    @gateway.default
    def connect(self):
        return gateway.DicomFile(location=self.location)

    def check(self, item: Dixel, path: str=None, fn_from: str="FileName", explode: Sequence=None) -> bool:

        fn = item.meta.get(fn_from)
        if item.level == DicomLevel.INSTANCES and \
                os.path.splitext(fn)[-1:] != ".dcm":
            fn = fn + '.dcm'   # Single file
        if item.level < DicomLevel.INSTANCES and \
                os.path.splitext(fn)[-1:] != ".zip":
            fn = fn + '.zip'   # Archive format

        if not path:
            path = self.location

        return self.gateway.exists(fn, path=path, explode=explode)

    def put(self, item: Dixel, path: str=None, fn_from: str="FileName", explode: Sequence=None) -> Dixel:

        fn = item.meta.get(fn_from)
        if item.level == DicomLevel.INSTANCES and \
                os.path.splitext(fn)[-1:] != ".dcm":
            fn = fn + '.dcm'   # Single file
        if item.level < DicomLevel.INSTANCES and \
                os.path.splitext(fn)[-1:] != ".zip":
            fn = fn + '.zip'   # Archive format

        if not path:
            path = self.location

        data = item.file

        self.gateway.write(fn, data, path=path, explode=explode )
        return item

    def remove(self, item: Dixel, path: str=None):

        if type(item) == Dixel:
            fn = item.meta['FileName']
            path = item.meta['FilePath']
        else:
            fn = item

        return self.gateway.remove(fn, path=path)


    def get(self, item: Union[str, Dixel], path: str=None, view: str="tags") -> Dixel:
        # print("getting")

        # Get needs to accept oid's or items with oid's
        if type(item) == Dixel:
            fn = item.meta['FileName']
            path = item.meta['FilePath']
        else:
            fn = item

        dcm, fp = self.gateway.read(fn, path=path, pixels=(view=="pixels"))

        # Core data required for shamming
        _meta = {'PatientID': dcm[0x0010, 0x0020].value,
                 'PatientName': str( dcm[0x0010,0x0010].value ),
                 'PatientBirthDate': dcm[0x0010,0x0030].value,
                 'PatientSex': dcm[0x0010,0x0040].value,

                 'AccessionNumber': dcm[0x0008, 0x0050].value,
                 'StudyInstanceUID': dcm[0x0020, 0x000d].value,
                 'SeriesInstanceUID': dcm[0x0020, 0x000e].value,
                 'SOPInstanceUID': dcm[0x0008, 0x0018].value,

                 'StudyDate':  dcm[0x0008,0x0020].value,
                 'StudyTime': dcm[0x0008,0x0030].value,

                 'SeriesDescription': dcm[0x0008,0x103E].value,
                 'StudyDescription': dcm[0x0008,0x1030].value,
                 'InstanceNumber': dcm[0x0020,0x0013].value,

                 'TransferSyntaxUID': dcm.file_meta.TransferSyntaxUID,
                 'TransferSyntax': str(dcm.file_meta.TransferSyntaxUID),
                 'MediaStorage': str(dcm.file_meta.MediaStorageSOPClassUID),
                 'PhotometricInterpretation': dcm[0x0028, 0x0004].value,  #MONOCHROME, RGB etc.

                 'FileName': fn,
                 'FilePath': path,
                 'FullPath': fp }

        _meta['StudyDateTime'] = dicom_strpdtime(_meta['StudyDate'] + _meta['StudyTime'])

        _pixels = None
        if view=="pixels":
            _pixels = dcm.pixel_array

        _file = None
        if view=="file":
            with open(fp, 'rb') as f:
                _file = f.read()

        item = Dixel(level=DicomLevel.INSTANCES, meta=_meta, pixels=_pixels, file=_file)
        return item
