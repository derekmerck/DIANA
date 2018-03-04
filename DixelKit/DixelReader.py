import io
import os
import csv
import re
from pprint import pformat
import logging
import yaml
from DixelKit.Dixel import Dixel, DicomLevel

KeyPattern = re.compile(r"^(?P<level>\w)-?(?P<tag>[^:]+)?:(?P<key>.*)(?P<ref>/*)?$")

def tokenize_key(k):
    if k.endswith('*'):
        k = k[:-1]
    match = KeyPattern.match(k)
    if not match:
        return None
    tokens = { "level": match.group('level'),
               "key": match.group('key'),
               "tag": match.group('tag'),
               "ref": match.group("ref") is not None
            }
    return tokens


def stringify_key_toks(t, tags=False):
    key = "{}{}:{}{}".format(t['level'],
                             '' if t['tag'] is None or not tags else t['tag'],
                             t['key'],
                             '' if t['ref'] is None or not tags else "*")
    return key


key_str = """
patients:
  id:
    orthanc:  PatientID
    anon:     SubjectID
    flat:     MRN
    flat:     Medical Record Number
  age:
    orthanc:  PatientAge
    anon:     SubjectAge
  sex:
    orthanc:  PatientSex
    anon:     SubjectSex
  dob:
    orthanc:  PatientBirthDate
    anon:     SubjectBirthDate
  name:
    orthanc:  PatientName
    anon:     SubjectName
  first_name:
    montage:  Patient First Name
  last_name:
    montage:  Patient Last Name
    
studies:
  id:
    orthanc:  AccessionNumber
    montage:  Accession Number
    anon:     StudyID
  uid:
    orthanc:  StudyInstanceUID
  date:
    orthanc:  StudyDate
  time:
    orthanc:  StudyTime
  desc:
    orthanc:  StudyDescription
  report:
    montage:  Report Text
    anon:     StudyReport
  radiologist:
    montage:  Signing Physician
    anon:     StudyPhysician
  dose:
    orthanc:  X-Ray Radiation Dose
  file:
    orthanc:  ArchiveFile
  rpd:
    orthanc:  StudyType
  body_part:
    orthanc:  BodyPart
    
series:
  num:
    orthanc:  SeriesNumber
  uid:
    orthanc:  SeriesInstanceUID
  desc:
    orthanc:  SeriesDescription
  uuid:
    orthanc:  SeriesUID
  type:
    orthanc:  SeriesType  # spiral, axial, stationary
  file:
    orthanc:  ArchiveFile

instances:
  uid:
    orthanc:  SOPInstanceUID
  compressed:
    orthanc:  Compressed
  file:
    orthanc:  DicomFile
"""
key_map = yaml.load(key_str)
invkey_map = {}
for k, v in key_map.iteritems():
    level = DicomLevel.abrv(k)
    if not level:
        continue
    for kk, vv in v.iteritems():
        for kkk, vvv in vv.iteritems():
            invkey_map[vvv] = "{}:{}".format(level, kk)

class MetaTranslator(object):

    @classmethod
    def cardinal_meta(cls, meta):
        ret = {}
        for k, v in meta.iteritems():
            new_k = invkey_map.get(k, k)
            ret[new_k] = v
        return ret

    @classmethod
    def cardinal_items(cls, items):
        ret = []
        for meta in items:
            ret.append(cls.cardinal_meta(meta))
        return ret


    @classmethod
    def translate_meta(cls, meta, target="orthanc"):
        ret = {}
        for k, v in meta.iteritems():
            if v=='?':
                continue
            t = tokenize_key(k)
            logging.debug(t)
            if not t:
                ret[k] = v
                continue
            level = str(DicomLevel.of(t['level']))
            new_k = key_map[level][t['key']].get(target, k)
            ret[new_k] = v
        return ret

    @classmethod
    def translate_items(cls, items, target="orthanc"):
        ret = []
        for meta in items:
            ret.append(cls.translate_meta(meta, target))
        return ret


class DixelReader(object):

    def __init__(self, fn, root_dir=None):
        self.fn = fn
        if root_dir:
            self.fp = os.path.join(root_dir, fn)
        else:
            self.fp = fn


    @classmethod
    def parse_item(cls, item):
        # Determine what sort of a dixel this is, return id and level
        keys = item.keys()

        unique_keys = [k[0:-1] for k in item.keys() if k.endswith("*")]

        logging.debug(pformat(item))
        logging.debug(pformat(keys))
        logging.debug(pformat(unique_keys))

        all_keys = []
        for k in unique_keys:
            tokens = tokenize_key(k)
            if tokens:
                logging.debug(tokens)
                all_keys.append(tokens)

        # Figure out how many sub-items to parse from this item

        p_tags = [t for t in all_keys if t['level'] == 'p']
        s_tags = [t for t in all_keys if t['level'] == 's']
        r_tags = [t for t in all_keys if t['level'] == 'r']
        i_tags = [t for t in all_keys if t['level'] == 'i']

        from itertools import product
        unique_key_sets = list(product(s_tags, r_tags))
        logging.debug(len(unique_key_sets))
        logging.debug(unique_key_sets)

        subitems = []

        for uks in unique_key_sets:
            logging.debug(uks)
            id = []
            for uk in uks:
                key = stringify_key_toks(uk, tags=True)
                id.append(item[key])
            logging.debug(id)

            logging.debug('Make subitem')
            subitem = {'id': id}
            for k, v in item.iteritems():
                tokens = tokenize_key(k)
                # logging.debug(tokens)
                # logging.debug(uks)
                k_ = stringify_key_toks(tokens, tags=False)
                if tokens['level'] not in [uk['level'] for uk in uks]:
                    # No info, keep it
                    subitem[k_] = v
                    logging.debug('No rule: ' + k)
                else:
                    for uk in uks:
                        if (uk['level'], uk['tag']) == (tokens['level'], tokens['tag']):
                            subitem[k_] = v
                            logging.debug("Found key: {}".format(k))

            tags = []
            for k in subitem.keys():
                if k.endswith('tags'):
                    v = subitem[k]
                    tags_ = v.split(",")
                    for tag in tags_:
                        tags.append(tag)
                    del (subitem[k])
            if tags:
                subitem['tags'] = tags

            # logging.debug(subitem)
            subitems.append(subitem)

        return subitems

    def read_csv(self):

        with open(self.fp, 'rU') as f:
            items = csv.DictReader(f)

            worklist = []
            for item in items:
                subitems = DixelReader.parse_item(item)
                worklist = worklist + subitems

            return worklist


def test_reader_f2():

    dixel_str = \
u"""p:id,p:tags,s:id*,s:uid,r0:num*,r0:tags,r0:desc,r0:uid,r1:num*,r1:tags,r1:desc,r1:uid
200YYYYXXXX,ncrs,ANAN1490,UID.UID.UID.UID.1.1,6,ax,example,UID.UID.UID.UID.1.1,604,crn,?,?
200YYYYZZZZ,ncrs,ANAN1490,UID.UID.UID.UID.2.1,3,ax,example,UID.UID.UID.UID.2.2,crn,?,?
"""
    items = csv.DictReader(io.StringIO(dixel_str))
    logging.debug(items)
    worklist = []
    for item in items:
        logging.debug(item)
        subitems = DixelReader.parse_item(item)
        worklist = worklist + subitems

    logging.debug(pformat(worklist))

    worklist = MetaTranslator.translate_items(worklist)
    logging.debug(pformat(worklist))

    assert( worklist[0]['PatientID'].startswith('200Y') )
    assert( 'ncrs' in worklist[0]['tags'])

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
