import json, logging
from datetime import datetime, timedelta
from hashlib import md5
from cryptography.fernet import Fernet
from requests import ConnectionError
from diana.apis import Orthanc, Dixel
from diana.utils.dicom import dicom_patient_initials, DicomLevel
from diana.utils import SmartJSONEncoder, stringify

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
    # # Some core metadata of interest
    # "ReceptionDate",
    # "AnonymizedFrom",
    # "RemoteAet",
    # "CalledAet",

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

    logging.debug("Setting dixel metadata")

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
    self.meta['TrueStudyDate'] =       self.meta.get('StudyDateTime') or "Unknown"
    self.meta['PartialPatientName'] =  dicom_patient_initials(self.meta.get('PatientName')) or "Unknown"
    self.meta['PartialPatientID'] =    get_end( self.meta.get('PatientID') ) or "Unknown"
    self.meta['PartialAccessionNumber'] = get_end(self.meta.get('AccessionNumber')) or "Unknown"

    if fkey:
        encode_data_sig(self, fkey)

    logging.debug(self.meta)

    # Todo: This should also propogate metadata up to series/study level


def encode_data_sig(self: Dixel, fkey):
    # Embedded data is adequate to create the study-level shams
    data = {
        'PatientID':        self.meta.get('PatientID')        or "Unknown",
        'PatientName':      self.meta.get('PatientName')      or "Unknown",
        'PatientBirthDate': self.meta.get('PatientBirthDate') or "Unknown",
        'PatientSex':       self.meta.get('PatientSex')       or "U",
        'AccessionNumber':  self.meta.get('AccessionNumber')  or "Unknown",
        'StudyDescription': self.meta.get('StudyDescription') or "Unknown",
        'StudyDateTime':    self.meta.get('StudyDateTime')    or "Unknown",
        'Institution':      self.meta.get('Institution')      or "Unknown"
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

    logging.info(content)
    res = json.loads(content)
    return res


# Write values from dixel into Orthanc metadata
def put_metadata(self: Orthanc, item: Dixel):
    self.logger.debug("Putting meta data keys")

    for k in SUPPORTED_METADATA:
        if item.meta.get( k ):
            self.gateway.put_metadata(item.oid(), item.level, k, stringify( item.meta.get( k ) ))

    if item.level == DicomLevel.INSTANCES or item.level == DicomLevel.SERIES:
        parent = self.get_parent(item)
        parent.copy_metadata(item)
        self.put_metadata(parent)


# Read values from Orthanc and update dixel
def get_metadata(self: Orthanc, item: Dixel) -> Dixel:
    self.logger.debug("Checking for metadata keys")

    for k in SUPPORTED_METADATA:
        try:
            result = self.gateway.get_metadata(item.oid(), item.level, k)
        except ConnectionError as e:
            # Nothing there, just skip it
            result = None
        except Exception as e:
            self.logger.error(e)
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

