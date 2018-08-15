"""
Reads dixel meta and reports from or writes to a csv file
"""

from csv import DictReader, DictWriter
from typing import Union, Mapping
from dateutil import parser as dtparser
import attr
from ..utils import Pattern
from ..utils.smart_encode import stringify
from ..utils.dicom import DicomLevel, dicom_strpdate
from .dixel import Dixel
import os

from pprint import pprint, pformat

# Doesn't really need to be patternable
@attr.s
class MetaCache(Pattern):
    location = attr.ib( default=None )
    cache = attr.ib( init=False, factory=dict )
    key_field = attr.ib( default="AccessionNumber" )

    montage_keymap = {
        "Accession Number": "AccessionNumber",
        "Patient MRN":  "PatientID",
        "Patient First Name": 'PatientFirstName',
        "Patient Last Name": 'PatientLastName',

        'Patient Sex': 'PatientSex',
        'Patient Age': 'PatientAge',

        'Exam Completed Date': "StudyDate",
        'Organization': 'Organization',
        "Exam Code": "OrderCode",
        'Exam Description': 'StudyDescription',
        "Patient Status": "PatientStatus",
        'Ordered By': 'ReferringPhysicianName',

        "Report Text": "_report"
    }

    def did(self, meta):
        level = meta["_level"]

        try:
            if level == DicomLevel.STUDIES:
                return meta[self.key_field]

            elif level == DicomLevel.SERIES:
                return meta[self.key_field], meta['SeriesDescription']

            elif level == DicomLevel.INSTANCES:
                return meta[self.key_field], meta['SeriesDescription'], meta['InstanceNumber']

        except KeyError:
            self.logger.error("Could not find key {}".format( self.key_field) )
            self.logger.error("keys: {}".format(meta.keys()))
            return None


    def get(self, item: Union[Dixel, str], **kwargs):

        # Get needs to accept oid's or items with oid's
        if type(item) == Dixel:
            id = item.uid
        elif type(item) == str or type(item) == tuple:
            id = item
        else:
            raise ValueError("Can not get type {}!".format(type(item)))

        meta = self.cache.get( id )
        # self.logger.debug(meta)
        if type( meta.get("_level") ) == DicomLevel:
            level = meta.get("_level")
        else:
            level = DicomLevel.of( meta.get("_level" ) )
            meta['_level'] = level

        report = meta.get('_report')
        uid    = meta.get('_uid')

        item = Dixel( uid=uid, meta=meta, level=level, report=report )
        return item

    def remove(self, item: Union[Dixel, str] ):

        if type(item) == Dixel:
            id = item.id
        elif type(item) == str:
            id = item
        else:
            raise ValueError("Can not remove type {}!".format(type(item)))

        if self.cache.get(id):
            del( self.cache[id] )

    def put(self, item, **kwargs):
        meta = item.meta
        meta['_level'] = item.level
        if item.report:
            meta['_report'] = item.report
        self.cache[self.did(meta)] = meta

    def load(self, fp: str=None, level=DicomLevel.STUDIES, keymap: Mapping=None):
        self.logger.debug("loading {}".format(os.path.split(fp)[-1]))
        fp = fp or self.location

        def remap_keys(item):
            ret = {}
            # Only take kv's that are in the remapper
            for k, v in keymap.items():
                vv = item.get(k)
                if vv:
                    ret[v] = vv
            return ret

        # This encoding seems to fix a lot of Montage read errors
        # - https://stackoverflow.com/questions/33819557/unicodedecodeerror-utf-8-codec-while-reading-a-csv-file
        with open(fp, encoding="cp1252") as f:
        # with open(fp, encoding="UTF8") as f:
            reader = DictReader(f)

            for item in reader:
                if keymap:
                    item = remap_keys(item)
                if not item.get("_level"):
                    item["_level"] = level
                else:
                    item["_level"] = DicomLevel.of(item.get("_level"))

                for k, v in item.items():
                    # if this k is a "date", normalize it
                    if v and \
                            (k.lower().find("date") >= 0 or \
                            k.lower().find("dob") >= 0 ):
                        try:
                            # self.logger.debug(v)
                            item[k] = dtparser.parse(v)
                        except ValueError:
                            try:
                                item[k] = dicom_strpdate(v)
                            except:
                                raise ValueError("No date can be parsed from {}".format(v))

                # self.logger.debug( pformat( dict(item) ))

                self.cache[self.did(item)] = dict(item)


    def dump(self, fp=None, fieldnames=None, extra_fieldnames=[]):
        self.logger.debug("dumping")
        fp = fp or self.location
        fieldnames = fieldnames or \
                     list( self.cache.values().__iter__().__next__().keys() )
        for field in extra_fieldnames:
            if field not in fieldnames:
                fieldnames.append(field)
        if "_report" not in fieldnames:
            fieldnames.append("_report")
        if "_level" not in fieldnames:
            fieldnames.append("_level")

        # print(fieldnames)

        with open(fp, "w") as f:
            writer = DictWriter(f, fieldnames)
            writer.writeheader()
            for k, v in self.cache.items():
                w = {}
                for kk, vv in v.items():
                    # self.logger.debug(fieldnames)
                    # self.logger.debug(kk)
                    # self.logger.debug(vv)
                    if kk in fieldnames:
                        # self.logger.debug("valid field")
                        out = stringify(vv)
                        if out:
                            # self.logger.debug("Using out {}".format(out))
                            w[kk] = out
                        else:
                            # self.logger.debug("Using native {}".format(vv))
                            w[kk] = vv

                writer.writerow(w)

    def __len__(self):
        return len(self.cache.keys())

    def __iter__(self):
        # self.logger.debug("Setting iterator = cache.keys()")
        self.iterator = iter(self.cache.keys())
        # self.logger.debug(self.cache.keys())
        return self

    def __next__(self):
        # self.logger.debug("Getting")
        return self.get(next(self.iterator))

    def __contains__(self, other):
        # self.logger.debug(self.did(other.meta))
        # self.logger.debug(self.cache.keys())

        return self.did(other.meta) in self.cache.keys()

