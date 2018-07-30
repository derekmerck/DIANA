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
from dateutil import parser as dateparser
from datetime import datetime, timedelta, date
import os
from abc import abstractmethod

DEFAULT_MAX_DATE_OFFSET = int(365/2)   # generated pseudodob is within 6 months
DEFAULT_HASH_PREFIX_LENGTH = 16  # 8 = 64bits, -1 = entire value

class GUIDMint(object):
    """
    Abstract= base class for guid mints.
    """

    def __init__(self,
                 max_date_offset = DEFAULT_MAX_DATE_OFFSET,
                 hash_prefix_length = DEFAULT_HASH_PREFIX_LENGTH,
                 **kwargs):
        self.max_date_offset = max_date_offset
        self.hash_prefix_length = hash_prefix_length
        self.logger = logging.getLogger(self.name())

    def name(self):
        return self.__class__.__name__

    @abstractmethod
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


