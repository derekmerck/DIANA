import os, re, random, logging
from dateutil import parser as dateparser
from datetime import timedelta, datetime
from hashlib import sha256
from base64 import b32encode
from .mint import GuidMint

DEFAULT_NAMEBANK = "US_CENSUS"


class NameBank (object):
    """
    NameBanks should contain gender specific surnames
    and a single list of family names
    """

    def __init__(self, source=DEFAULT_NAMEBANK):
        super(NameBank, self).__init__()
        self.mnames = []
        self.fnames = []
        self.lnames = []

        if source == "US_CENSUS":
            self.set_from_census()

    def set_from_census(self):

        # Someday: Should weight these as well to match census distribution...

        with open("{0}/us_census/dist.male.first.txt".format(os.path.dirname(__file__))) as f:
            lines = f.readlines()
            for line in lines:
                words = line.split(" ")
                self.mnames.append(words[0])

        with open("{0}/us_census/dist.female.first.txt".format(os.path.dirname(__file__))) as f:
            lines = f.readlines()
            for line in lines:
                words = line.split(" ")
                self.fnames.append(words[0])

        with open("{0}/us_census/dist.all.last.txt".format(os.path.dirname(__file__))) as f:
            lines = f.readlines()
            for line in lines:
                words = line.split(" ")
                self.lnames.append(words[0])

    def get_name(self, seed, initials=None, gender=None):

        random.seed(seed)

        if not initials:
            initials = []
            initials[0] = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            initials[1] = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            initials[2] = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        fam_names = [x for x in self.lnames if x.startswith(initials[0])]

        if gender == "M":
            sur_names = self.mnames
        elif gender== "F":
            sur_names = self.fnames
        else:
            sur_names = self.mnames+self.fnames

        sur_names = [x for x in sur_names if x.startswith(initials[1])]

        fam_name = random.choice(fam_names)
        sur_name = random.choice(sur_names)
        middle_init = initials[2]

        return (fam_name, sur_name, middle_init)


class PseudoMint(GuidMint):
    """
    Mint that returns a complete identity, including a pseudonym based on the
    subject GUID and the US Census NameBank
    """

    def __init__(self,
                 name_source=DEFAULT_NAMEBANK,
                 name_format="DICOM",
                 **kwargs):
        self.name_bank = NameBank(name_source)
        self.name_format = name_format
        super(PseudoMint, self).__init__(**kwargs)

    def mint_guid(self, value, *args, **kwargs):

        value = value.lower()
        value = re.sub(r'\W+', '', value)
        value = list(value)
        value.sort()
        value = "".join(value)

        candidate = b32encode( self.hash(value) ).decode('utf8')
        while not re.match(u"^[A-Z]{3}", candidate ):
            candidate = b32encode( self.hash(candidate) ).decode('utf8')
        candidate = candidate[:self.hash_prefix_length].strip("=")
        return candidate

    def pseudonym(self, guid, gender=None):

        names = self.name_bank.get_name(guid, initials=guid, gender=gender)
        return names
        # return "^".join(names)

    def pseudo_identity(self, name, dob, gender=None, age=None, ref_date=None, format=None):

        if not isinstance(dob, datetime):
            try:
                dob = dateparser.parse(dob)
                dob_str = str(dob.date())
            except:
                dob_str = "U"
        else:
            dob_str = str(dob.date())

        if not gender:
            gender = "U"

        key = "|".join([name, dob_str, gender])

        guid = self.mint_guid(key)

        pnym = self.pseudonym(guid, gender)

        pdob = self.pseudodob(guid, dob=dob)

        return (guid, pnym, pdob)

        # guid = self.mint_guid(key)
        #
        # if self.name_format == "DICOM":
        #     pnym = "^".join(pnym)
        #     pnym = pnym.upper()
        # else:
        #     pnym = "{}, {} {}".format( *pnym )

        # # TODO: This is not repeatable b/c it depends on now(), which changes
        # if not dob and (age and ref_date):
        #     ddob = dateparser(ref_date)-timedelta(days=age*365.25)
        #     dob = str(ddob.date())
        #
        # # TODO: Handle cases where middle initial is missing, or names are in non-DICOM format?
        # name = name.upper()
        #
        # value = "|".join([name, str(dob), str(gender)])
        #
        # return GUIDMint.pseudo_identity(self, value, gender=gender, dob=dob)
        #

def test_pmint():

    M = PseudoMint()

    guid = M.mint_guid("MERCK^DEREK^L|1971-06-09|M")
    print(guid)

    pnym = M.pseudonym(guid, "M")
    print(pnym)

    pdob = M.pseudodob(guid, "19710609")
    print(pdob)

    pseudo_id = M.pseudo_identity("Merck, Derek L", dob="1971", gender="M")
    print(pseudo_id)

    pseudo_id = M.pseudo_identity("derek l MERCK", dob="june 9, 1971", gender="M")
    print(pseudo_id)

    pdob = M.pseudodob(guid, age="47")
    print(pdob)

    pdob = M.pseudodob(guid, age="29", ref_date="2000")
    print(pdob)


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_pmint()

