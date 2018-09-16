import json
from datetime import datetime, timedelta
from hashlib import md5
from cryptography.fernet import Fernet
from requests import ConnectionError
from . import Orthanc, Dixel
from diana.utils.dicom import dicom_patient_initials
from diana.utils import SmartJSONEncoder

"""
Could also use Orthanc sekrit keys:

config:

"Dictionary" : {
    # LO - long string (64 chars)
 	# ST - short text (1024 chars)

    "abcd,1003" : [ "ST", "DataSignature",    1, 1, "RIH3D Private Data" ],
    "abcd,1005" : [ "LO", "KeySignature",     1, 1, "RIH3D Private Data"],

},
"""

SUPPORTED_METADATA = [
    # Some core metadata of interest
    "ReceptionDate",
    "AnonymizedFrom",
    "RemoteAet",
    "CalledAet",

    # User Configured
    "SubmittingSite",
    "SubmissionDate",
    "SubmissionMechanism",  # file upload, dicom aets, or web UI
    "TrueStudyDate",        # saved from prior to anonymization
    "PartialPatientName",
    "PartialPatientID",
    "PartialAccessionNumber",
    "DataSignature",
    "KeySignature"
]

def copy_metadata(self: Dixel, other: Dixel):
    for k in SUPPORTED_METADATA:
        if other.meta.get( k ):
            self.meta[k] = other.meta.get( k )

def set_metadata(self: Dixel,
                 submitting_site: str = None,
                 submission_mechanism: str = None,
                 submission_date: datetime = None,
                 fkey = None):

    def get_end(item: str) -> str:
        if not item:
            return ""
        if len(item) < 5:
            return item
        return item[-4:]

    # Check for RemoteAet, CalledAet
    self.meta['SubmittingSite'] =      submitting_site or "Unknown"
    self.meta['SubmissionDate'] =      submission_date or datetime.now()
    self.meta['SubmissionMechanism'] = submission_mechanism or "Unknown"
    self.meta['TrueStudyDate'] =       self.meta['StudyDateTime'] or "Unknown"
    self.meta['PartialPatientName'] =  dicom_patient_initials(self.meta['PatientName']) or "Unknown"
    self.meta['PartialPatientID'] =    get_end( self.meta['PatientID'] ) or "Unknown"
    self.meta['PartialAccessionNumber'] = get_end(self.meta['AccessionNumber']) or "Unknown"

    if fkey:
        encode_data_sig(self, fkey)

    # Todo: This should also propogate metadata up to series/study level


def encode_data_sig(self: Dixel, fkey):
    data = {
        'PatientID': self.meta['PatientID'],
        'PatientName': self.meta['PatientName'],
        'PatientBirthDate': self.meta['PatientBirthDate'],
        'AccessionNumber': self.meta['AccessionNumber'],
        'StudyDescription': self.meta['StudyDescription'],
        'StudyDateTime': self.meta['StudyDateTime'],
        'Institution': self.meta['Institution']
    }

    f = Fernet(fkey)
    token = f.encrypt(json.dumps(data, cls=SmartJSONEncoder).encode('utf8'))
    self.meta['DataSignature'] = token
    self.meta['KeySignature'] = md5(fkey).hexdigest()

def decode_data_sig(self: Dixel, fkey):

    if md5(fkey).hexdigest() != self.meta['KeySignature']:
        raise ValueError("Wrong key")

    f = Fernet(fkey)
    token = self.meta['DataSignature']
    content = f.decrypt(token)

    print(content)
    res = json.loads(content)
    return res


# Write values from dixel into Orthanc metadata
def put_metadata(self: Orthanc, item: Dixel):

    for k in SUPPORTED_METADATA:
        if item.meta.get( k ):
            self.gateway.put_metadata(item.oid, item.level, k, item.meta.get( k ))


# Read values from Orthanc and update dixel
def get_metadata(self: Orthanc, item: Dixel) -> Dixel:

    for k in SUPPORTED_METADATA:
        self.logger.debug(k)
        try:
            result = self.gateway.put_metadata(item.oid, item.level, k)
            self.logger.debug(result)
        except ConnectionError as e:
            self.logger.warning(e)
            result = None
        if result:
            item.meta[k] = result
    return item


# Monkey-patch
Dixel.set_metadata = set_metadata
Dixel.copy_metadata = copy_metadata
Dixel.encode_data_sig = encode_data_sig
Dixel.decode_data_sig = decode_data_sig

Orthanc.put_metadata = put_metadata
Orthanc.get_metadata = get_metadata


def test_encoding():

    meta = {
        'PatientID': "123456",
        'PatientName': "DOE^JOHN^B",
        'PatientBirthDate': (datetime.now() - timedelta(days=20*365)).isoformat(),
        'AccessionNumber': "ABCDEFG",
        'StudyDescription': "Medical imaging study",
        'StudyDateTime': datetime.now().isoformat(),
        'Institution': "Medical center"
    }

    item = Dixel(meta=meta)

    fkey = Fernet.generate_key()
    encode_data_sig(item, fkey)

    assert( item.meta.get('DataSignature') != meta )

    round_trip = decode_data_sig(item, fkey)

    assert( round_trip.items() <= meta.items() )
