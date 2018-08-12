import logging, hashlib, datetime
import attr
from dateutil import parser as dtparser
from .report import RadiologyReport
from ..utils import Pattern, orthanc_id
from ..utils.dicom import DicomLevel, dicom_strfdate, dicom_strfname, DicomUIDMint
from guidmint import PseudoMint


@attr.s(cmp=False, hash=None)
class Dixel(Pattern):
    level = attr.ib(default=DicomLevel.STUDIES)
    meta  = attr.ib(factory=dict)
    pixels = attr.ib(default=None)
    file  = attr.ib(default=None)
    report = attr.ib(default=None, type=RadiologyReport, converter=RadiologyReport)

    # Can't pickle a logger without dill, so Dixels don't need one
    logger = attr.ib(init=False, default=None)

    def __hash__(self):

        # Not always the best idea, can't series or instances into a set if the AN is identical
        if self.level == DicomLevel.STUDIES:
            try:
                return hash(self.AccessionNumber)
            except:
                pass

        return Pattern.__hash__(self)

    def update(self, other):
        if self.level != other.level:
            raise ValueError("Wrong dixel levels to update!")

        updatable = ["PatientID", "PatientName", "PatientBirthDate",
                     "StudyInstanceUID", "AccessionNumber", "StudyDateTime",
                     "SeriesInstanceUID", "SeriesNumber",
                     "SOPInstanceUID", ]

        for k in updatable:
            v = other.meta.get(k)
            if v:
                # logging.debug("Found an update {}:{}".format(k,v))
                if k.lower().find("date") >= 0 and \
                        type(v) != datetime.datetime and \
                        type(v) != datetime.date:
                    v = dtparser.parse(v)
                self.meta[k] = v

        return self

    @property
    def AccessionNumber(self):
        return self.meta['AccessionNumber']

    def oid(self, level: DicomLevel=None):

        # Stashed, may not be computable
        if not level and self.meta.get('oid'):
            return self.meta['oid']

        # Can compute any parent oid
        level = level or self.level

        if level == DicomLevel.PATIENTS:
            return orthanc_id(self.meta['PatientID'])
        elif level == DicomLevel.STUDIES:
            return orthanc_id(self.meta['PatientID'], self.meta['StudyInstanceUID'])
        elif level == DicomLevel.SERIES:
            return orthanc_id(self.meta['PatientID'], self.meta['StudyInstanceUID'],
                              self.meta['SeriesInstanceUID'])
        elif level == DicomLevel.INSTANCES:
            return orthanc_id(self.meta['PatientID'], self.meta['StudyInstanceUID'],
                              self.meta['SeriesInstanceUID'], self.meta['SOPInstanceUID'])
        else:
            raise ValueError("No such DICOM level: {}".format(level))

    def sham_oid(self):

        if self.level == DicomLevel.STUDIES:
            return orthanc_id(self.meta['ShamID'], self.meta['ShamStudyUID'])
        elif self.level == DicomLevel.SERIES:
            return orthanc_id(self.meta['ShamID'], self.meta['ShamStudyUID'], self.meta['ShamSeriesUID'])
        elif self.level == DicomLevel.INSTANCES:
            return orthanc_id(self.meta['ShamID'], self.meta['ShamStudyUID'], self.meta['ShamSeriesUID'], self.meta['ShamInstanceUID'])

        raise TypeError("Cannot create sham oid from meta")

    def get_pixels(self):
        if self.meta['PhotometricInterpretation'] == "RGB":
            pixels = self.pixels.reshape([self.pixels.shape[1], self.pixels.shape[2], 3])
        else:
            pixels = self.pixels

        return pixels

    def set_shams(self, id_mint: PseudoMint=None, dicom_mint: DicomUIDMint=None):

        id_mint = id_mint or PseudoMint()
        dicom_mint = dicom_mint or DicomUIDMint("Diana")

        sham_identity = id_mint.pseudo_identity(self.meta['PatientName'],
                                                self.meta['PatientBirthDate'],
                                                self.meta['PatientSex'])

        self.meta['ShamAccession'] = hashlib.md5(self.meta['AccessionNumber'].encode("UTF8"))
        self.meta['ShamID']        = sham_identity[0]
        self.meta['ShamName']      = dicom_strfname( sham_identity[1] )
        self.meta['ShamDoB']       = dicom_strfdate( sham_identity[2] )
        self.meta['ShamStudyUID']  = dicom_mint.uid(self.meta['PatientID'],
                                                    self.meta['AccessionNumber'])

        if self.level == DicomLevel.SERIES or self.level == DicomLevel.INSTANCES:
            self.meta['ShamSeriesUID'] = dicom_mint.uid(self.meta['PatientID'],
                                                        self.meta['AccessionNumber'],
                                                        self.meta['SeriesDescription'])

        if self.level == DicomLevel.INSTANCES:
            self.meta['ShamInstanceUID'] = dicom_mint.uid(self.meta['PatientID'],
                                                        self.meta['AccessionNumber'],
                                                        self.meta['SeriesDescription'],
                                                        self.meta['InstanceNumber'])

        return self
