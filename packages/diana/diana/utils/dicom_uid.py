import datetime
from enum import Enum
import attr
from diana.utils.orthanc_id import orthanc_hash
import hashlib

def hash2int(h, digits):
    return int(h.hexdigest(), 16) % (10 ** digits)

def hash_str(s, digits=2):
    return str( hash2int(hashlib.sha1(str(s).encode("UTF8")), digits) )

class SuffixStyle(Enum):
    HIERARCHICAL = 1
    OID32 = 2
    RANDOM = 3

@attr.s
class DicomUIDMint(object):

    # RIH 3d Lab prefix within the medicalconnections.co.uk namespace
    prefix = "1.2.826.0.1.3680043.10.43"
    """
    1 - iso
    2 - ansi
    840 - us
    0.1.3680043.10.43 - sub-organization within medicalconnections.co.uk
    
    A 25 character prefix leaves 39 digits and stops available (64 chars max)
    """

    app_id = attr.ib(converter=hash_str, default="dicom")
    suffix_style = attr.ib( default=SuffixStyle.HIERARCHICAL )

    def hierarchical_suffix(self, PatientID: str, StudyInstanceUID: str,
                            SeriesInstanceUID=None, SOPInstanceUID=None):

        """
        A hierarchical asset uid has the form:

          `prefix.app.patient.study.series.instance`

        Where
          - prefix = 25 digits                              25
          - app = stop + 2 digits                       3 = 28
          - pt, study = stop + 12 digits each          26 = 54
          - series, instance = stop + 4 digits each (optional)
                                                       10 = 64
        Total length is 64
        """

        entries = []

        entries.append( hash_str(PatientID, 12) )
        entries.append( hash_str(StudyInstanceUID, 12) )

        if SeriesInstanceUID:
            entries.append( hash_str(SeriesInstanceUID, 4) )

            if SOPInstanceUID:
                entries.append( hash_str(SOPInstanceUID, 4) )

        return ".".join(entries)


    def random_suffix(self):
        """
        Uses app_id and current time to create a 4-segment suffix
        with the oid32 algorithm
        """
        seed1 = datetime.datetime.now()
        seed2 = self.app_id

        return self.oid32_suffix( seed1, seed2 )


    def oid32_suffix(self, PatientID: str, StudyInstanceUID: str,
                     SeriesInstanceUID=None, SOPInstanceUID=None):

        """
        A 32-byte orthanc_id asset uid has the form:

          `prefix.app.segment.segment.segment.segment`

        Where
          - prefix = 25 digits                              25
          - app = stop + 2 digits                       3 = 28
                                                       10 = 64
        Total length is 64
        """

        h = orthanc_hash(str(PatientID), str(StudyInstanceUID),
                         str(SeriesInstanceUID), str(SOPInstanceUID))
        s = str( hash2int( h, 32 ) )
        return '.'.join(s[i:i + 8] for i in range(0, len(s), 8))


    def uid(self, PatientID: str=None, StudyInstanceUID: str=None,
            SeriesInstanceUID=None, SOPInstanceUID=None,
            suffix_style=None):
        """
        app fields immediately following prefix with 2 digits are
        asset or common uids (pt, st, ser, inst).

        asset_uid takes up to 4 parameters (pt, st, ser, inst) that
        will be converted to strings and hashed.

        Non-asset uids will have app fields >2 digits.
        """

        suffix_style = suffix_style or self.suffix_style

        if suffix_style == SuffixStyle.HIERARCHICAL:
            suffix = self.hierarchical_suffix(PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID)
        elif suffix_style == SuffixStyle.OID32:
            suffix = self.oid32_suffix(PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID)
        elif suffix_style == SuffixStyle.RANDOM:
            suffix = self.random_suffix()
        else:
            raise TypeError("Unknown suffix style {}".format( suffix_style ))

        return "{}.{}.{}".format(DicomUIDMint.prefix, self.app_id, suffix)


def test_uid():

    umint = DicomUIDMint()
    s = umint.uid("patient", "study", "series", "instance")
    assert( s=="1.2.826.0.1.3680043.10.43.62.7834598798.958245076358.6951.1763" )

    umint = DicomUIDMint("Diana")
    s = umint.uid("patient", "study", "series", "instance")
    assert( s=="1.2.826.0.1.3680043.10.43.1.7834598798.958245076358.6951.1763" )

    umint = DicomUIDMint(suffix_style=SuffixStyle.OID32)
    s = umint.uid("patient", "study", "series", "instance")
    assert( s=="1.2.826.0.1.3680043.10.43.62.13853529.81072496.95419199.52800319" )

    umint = DicomUIDMint()
    s = umint.uid(123, True, Exception, DicomUIDMint)
    assert( s=="1.2.826.0.1.3680043.10.43.62.537183137519.769778132498.1158.9415" )

    umint = DicomUIDMint("Diana")
    s = umint.uid(123, True, Exception, DicomUIDMint, suffix_style=SuffixStyle.OID32)
    assert( s=="1.2.826.0.1.3680043.10.43.1.77849330.34713634.41174466.78080272" )

    umint = DicomUIDMint(suffix_style=SuffixStyle.RANDOM)
    s = umint.uid()
    t = umint.uid()
    assert( s != t )

if __name__ == "__main__":

    test_uid()



