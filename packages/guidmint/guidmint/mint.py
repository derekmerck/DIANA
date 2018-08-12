"""
Hashes an alphanumeric guid from a given string value

* Given a guid, gender (M/F/U), and name lists -> returns a reproducible pseudonym
* Given a guid, and dob (%Y-%m-%d) -> returns a reproducible pseudodob within 6 months of the original dob
* Given a guid, and age (delta Y) -> pseudodob of guid, (now - age*365.25 days); it is NOT reproducible b/c it depends on now


pseudonym for id

pseudodob for id, dob OR age + studydate

id from key

key from name, gender=U, dob OR age + studydate
key from mrn
key from


"""

import logging

import random
from datetime import datetime, timedelta, date
from hashlib import sha256
from cryptography.fernet import Fernet
from base64 import b32encode, b32decode, b64encode, b64decode
from dateutil import parser as dateparser
import os
import attr

DEFAULT_MAX_DATE_OFFSET = int(365/2)   # generated pseudodob is within 6 months
DEFAULT_HASH_PREFIX_LENGTH = 16  # 8 = 64bits, -1 = entire value

@attr.s
class GuidMint(object):
    """
    Abstract= base class for guid mints.
    """

    max_date_offset = attr.ib( default=DEFAULT_MAX_DATE_OFFSET )
    hash_prefix_length = attr.ib( default=DEFAULT_HASH_PREFIX_LENGTH )
    logger = attr.ib( factory=logging.getLogger )
    fernet_key = attr.ib( default=None, convert=Fernet )

    def hash(self, value):
        return sha256(value.encode('utf-8'))

    def encrypt(self, value):
        if self.fernet_key:
            return self.fernet_key.encrypt( value.encode('utf-8') )
        raise KeyError("No fernet key for encrypting")

    def decrypt(self, token):
        if self.fernet_key:
            return self.fernet_key.decrypt(token)
        raise KeyError("No fernet key for encrypting")

    def name(self):
        return self.__class__.__name__

    def guid(self, value: str, *args, **kwargs):
        raise NotImplementedError

    def pseudodob(self, guid, dob=None, age=None, ref_date=None, *args, **kwargs) -> datetime:
        random.seed(guid)

        if not dob:
            if not age:
                age = random.randint(19,65)

            age = int(age)

            if not ref_date:
                logging.warning("Generating unrepeatable pseudodob using 'now' as the age reference date")
                ref_date = datetime.now()
            elif type(ref_date) != datetime:
                ref_date = dateparser.parse(ref_date)

            dob = ref_date-timedelta(days=age*365.25)

        elif not isinstance(dob, datetime) and not isinstance(dob, date):

            logging.error(type(dob))

            dob = dateparser.parse(dob)

        r = random.randint(-self.max_date_offset, self.max_date_offset)
        rd = timedelta(days=r)

        return (dob+rd)

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    fernet_key = b'guidmint-guidmint-guidmint-guidmint-guidmin='
    # fernet_key = b'9jgCMWN3JaWEY5O5V93TNXWMfxmcFyAPUVoG2CJ79Lk='

    fernet_key_sig = b64encode( sha256( b64decode( fernet_key ) ).digest()  )
    logging.debug( fernet_key_sig )

    mint = GuidMint(fernet_key=fernet_key)

    data = {
        'PatientName':      "MERCK^DEREK^L",
        'PatientID':        "1234abcdefg",
        'PatientBirthDate': datetime.now().date(),
        'AccessionNumber':  "abc1234567",
        'StudyDescription': "blah blah",
        'StudyDateTime':    datetime.now(),
        'Institution':      "Some Hospital"
    }

    import json
    from diana.utils import SmartJSONEncoder
    from pprint import pformat

    data = json.dumps( data, cls=SmartJSONEncoder)

    tok = mint.encrypt( json.dumps( data ) )

    logging.debug(tok)
    logging.debug(len(tok))
    val = json.loads( mint.decrypt( tok ) )

    val2 = Fernet(fernet_key_sig).decrypt(tok)

    logging.debug(pformat(data))

    logging.debug(tok)
    logging.debug(val)
    logging.debug(val2)

    def gender_check(value):
        if value.upper().startswith("M"):
            return "M"
        elif value.upper().startswith("F"):
            return "F"
        else:
            return "U"

    @attr.s
    class PseudoIdentity():

        name = attr.ib( type=str )
        study_datetime = attr.ib( type=datetime, default=datetime.now(), convert=dateparser.parse)

        age = attr.ib( type=int, default=0 )
        birthdate = attr.ib( type=datetime, convert=dateparser.parse )

        @birthdate.default
        def guess_birthdate(self):
            if not self.age:
                random.seed(self.name)
                self.age = random.randint(40,80)

            offset = timedelta( days=self.age*365 )
            return self.study_datetime - offset

        gender = attr.ib(default="U", convert=gender_check)

        study_description = attr.ib( default=None)
        institution = attr.ib( default=None )

        def name_token(self):
            # remove non-letters, sort alphabetically, all upper
            pass

        def dob_token(self):
            # %YY%mm%dd 6-char format
            pass

        def gender_token(self):
            return self.gender()

        def serialize_knowns(self):

            return {
                'PatientName': self.name
            }

        def encode(self, key):
            f = Fernet(key)
            token = f.encrypt( self.serialize_knowns() )


        # PseudoPatientID     = attr.ib()
        # PseudoPatientName   = attr.ib()
        # PseudoBirthDate     = attr.ib()
        # PseudoAccessionNum  = attr.ib()
        # PseudoStudyDateTime = attr.ib()
        #
        # DataSignature = attr.ib()
        # KeySignature = attr.ib()
        # SignatureVersion = attr.ib()

    # if no birthdate and no age - chose a random age 30-80 based on name
    # if no birthdate but age - chose randomly based on age and name
    # if no gender - use unknown

    # if no accession num, use StudyUID

    # new id = hash( patient name, birthdate, gender )
    # new accession num = hash( accession num )
    # new StudyDateTime = old StudyDateTime.jitter secs( random( new id, new accession number )  )
    # new SeriesDateTime = old StudyDateTime.jitter secs( random( new id, new accession number )  )
    # new InstanceCreationDateTime

    # return data sig
    # return key sig
    # return algorithm version
