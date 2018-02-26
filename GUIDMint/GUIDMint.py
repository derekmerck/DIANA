"""
GUIDMint

Hashes an alphanumeric guid from a given string value
Given a guid, gender (M/F/U), and name lists, returns a reproducible pseudonym
Given a dob (%Y-%m-%d), returns a reproducible pseudodob within 6 months of the original dob

If age is input, the dob is assumed to be (now - age*3655.25 days)
"""

import logging
from hashlib import sha256, md5
from base64 import b32encode
import re
import random
from datetime import datetime, timedelta
import os
from abc import abstractmethod

__version__ = "0.9.0"

DEFAULT_MAX_DATE_OFFSET = int(365/2)   # generated pseudodob is within 6 months
DEFAULT_NAMEBANK = "US_CENSUS"
DEFAULT_HASH_PREFIX_LENGTH = 16  # 8 = 64bits, -1 = entire value

class NameBank (object):
    # NameBanks should contain gender specific surnames
    # and a single list of family names

    def __init__(self, source=DEFAULT_NAMEBANK):
        super(NameBank, self).__init__()
        self.mnames = []
        self.fnames = []
        self.lnames = []

        if source == "US_CENSUS":
            self.set_from_census()

    def set_from_census(self):

        # Should weight these as well to match census distribution...

        with open("{0}/names/dist.male.first.txt".format(os.path.dirname(__file__))) as f:
            lines = f.readlines()
            for line in lines:
                words = line.split(" ")
                self.mnames.append(words[0])

        with open("{0}/names/dist.female.first.txt".format(os.path.dirname(__file__))) as f:
            lines = f.readlines()
            for line in lines:
                words = line.split(" ")
                self.fnames.append(words[0])

        with open("{0}/names/dist.all.last.txt".format(os.path.dirname(__file__))) as f:
            lines = f.readlines()
            for line in lines:
                words = line.split(" ")
                self.lnames.append(words[0])


class GUIDMint(object):

    def __init__(self,
                 max_date_offset = DEFAULT_MAX_DATE_OFFSET,
                 hash_prefix_length = DEFAULT_HASH_PREFIX_LENGTH,
                 **kwargs):
        self.__version__ = __version__
        self.max_date_offset = max_date_offset
        self.hash_prefix_length = hash_prefix_length
        self.logger = logging.getLogger(self.name())

    def name(self):
        return self.__class__.__name__

    @abstractmethod
    def mint_guid(self, value, *args, **kwargs):
        pass

    def pseudonym(self, guid, gender=None, *args, **kwargs):
        pass

    def pseudo_dob(self, guid, dob=None, age=None, *args, **kwargs):
        random.seed(guid)

        if not dob and not age:
            age = random.randint(19,65)

        if not dob and age:
            ddob = datetime.now()-timedelta(days=age*365.25)
            dob = str(ddob.date())

        d = datetime.strptime(dob, "%Y-%m-%d")
        r = random.randint(-self.max_date_offset,self.max_date_offset)
        rd = timedelta(days=r)

        return str((d+rd).date())

    def pseudo_identity(self, value, gender="U", dob=None, age=None, *args, **kwargs):

        g = self.mint_guid(value)
        n = self.pseudonym(g, gender)
        d = self.pseudo_dob(g, dob)

        self.logger.debug("guid:      {0}".format(g))
        self.logger.debug("pseudonym: {0}".format(n))
        self.logger.debug("pseudodob: {0}".format(d))

        return g, n, d

class MD5Mint(GUIDMint):

    def __init__(self, prefix="", **kwargs):
        self.prefix = prefix
        super(MD5Mint, self).__init__(**kwargs)

    def mint_guid(self, value, *args, **kwargs):
        # Accept any value and return md5 of it
        return md5(value.encode('utf-8')).hexdigest()[:self.hash_prefix_length]

    def pseudonym(self, guid, gender="U", dob=None, age=None, **kwargs):
        return self.prefix + guid


class PseudoMint(GUIDMint):

    def __init__(self,
                 name_source=DEFAULT_NAMEBANK,
                 name_format="DICOM",
                 **kwargs):
        self.name_bank = NameBank(name_source)
        self.name_format = name_format
        super(PseudoMint, self).__init__(**kwargs)

    def mint_guid(self, value, *args, **kwargs):

        candidate = b32encode(sha256(value.encode('utf-8')).digest())
        while not re.match(b"^[A-Z]{3}", candidate):
            candidate = b32encode(sha256(candidate).digest())

        candidate = candidate[:self.hash_prefix_length].decode().strip("=")
        return candidate

    def pseudonym(self, guid, gender="U", dob=None, age=None, *args, **kwargs):

        if self.name_format == "DICOM":
            i_fam = 0
            i_sur = 1
            i_mid = 2
        else:
            i_sur = 0
            i_mid = 1
            i_fam = 2

        fam_names = [x for x in self.name_bank.lnames if x.startswith(guid[i_fam])]

        if gender == "M":
            sur_names = self.name_bank.mnames
        elif gender== "F":
            sur_names = self.name_bank.fnames
        else:
            sur_names = self.name_bank.mnames+self.name_bank.fnames

        sur_names = [x for x in sur_names if x.startswith(guid[i_sur])]

        random.seed(guid)
        fam_name = random.choice(fam_names)
        sur_name = random.choice(sur_names)

        middle = guid[i_mid]

        if self.name_format == "DICOM":
            name = "^".join([fam_name, sur_name, middle])
        else:
            name = " ".join([sur_name, middle, fam_name])

        return name


    def pseudo_identity(self, name, gender="U", dob=None, age=None, *args, **kwargs):

        if not dob and age:
            ddob = datetime.now()-timedelta(days=age*365.25)
            dob = str(ddob.date())

        # TODO: Handle cases where middle initial is missing, or names are in non-DICOM format?
        name = name.upper()

        value = "|".join([name, str(dob), str(gender)])

        return GUIDMint.pseudo_identity(self, value, gender=gender, dob=dob)


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)

    md5_mint = MD5Mint()
    pseudo_mint = PseudoMint()

    name = "MERCK^DEREK^L"
    gender = "M"
    dob = "1971-06-06"

    md5_mint.pseudo_identity(name, gender=gender, dob=dob)
    pseudo_mint.pseudo_identity(name, gender=gender, dob=dob)

    name = "MERCK^LISA^H"
    gender = "F"
    dob = "1973-01-01"

    md5_mint.pseudo_identity(name, gender=gender, dob=dob)
    pseudo_mint.pseudo_identity(name, gender=gender, dob=dob)

    name = "PROTECT3-SU001"
    age = 65

    md5_mint.pseudo_identity(name, age=age)
    pseudo_mint.pseudo_identity(name, age=age)
