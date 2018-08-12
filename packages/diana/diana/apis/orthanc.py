# DICOM node or proxy


"""
Orthanc sekrit keys:

config:

"Dictionary" : {
    # LO - long string (64 chars)
 	# ST - short text (1024 chars)

    "abcd,1003" : [ "ST", "DataSignature",    1, 1, "RIH3D Private Data" ],
    "abcd,1005" : [ "LO", "KeySignature",     1, 1, "RIH3D Private Data"],
    "abcd,1007" : [ "LO", "SignatureVersion", 1, 1, "RIH3D Private Data"]

},

stash:

data = {
    'PatientID':        "1234abcdefg",
    'PatientName':      "MERCK^DEREK^L",
    'PatientBirthDate': datetime.now().date(),
    'AccessionNumber':  "abc1234567",
    'StudyDescription': "blah blah",
    'StudyDateTime':    datetime.now(),
    'Institution':      "Some Hospital"
}

f = Fernet(key)
token = f.encrypt(json.dumps(data))

d.tags['DataSignature'] = token
d.tags['KeySignature'] = md5(key)
d.tags['SignatureVersion'] = diana.__version__

"""

import datetime
from pprint import pformat
from typing import Mapping, Callable, Union
import attr
from requests import ConnectionError
from ..utils import Pattern, gateway
from ..utils.dicom import DicomLevel, dicom_clean_tags, dicom_strfdate, dicom_strpdate, dicom_strpdtime
from .dixel import Dixel


def apply_tag_map(map, meta):
    for k,v in map['Replace']:
        meta[k] = v
    return meta


def simple_sham_map(meta):
    map = {
        'Replace': {
            'PatientName': meta['ShamName'],
            'PatientID': meta['ShamID'],
            'PatientBirthDate': dicom_strfdate( meta['ShamDoB'] ) if isinstance(meta["ShamDoB"], datetime.date) else meta["ShamDoB"],
            'AccessionNumber': meta['ShamAccession'].hexdigest() if hasattr( meta["ShamAccession"], "hexdigest") else meta["ShamAccession"],
            'StudyInstanceUID': meta['ShamStudyUID'],
        },
        'Keep': ['PatientSex', 'StudyDescription', 'SeriesDescription', 'StudyDate'],
        'Force': True
    }
    if meta.get('ShamSeriesUID'):
        map['Replace']['SeriesInstanceUID'] = meta.get('ShamSeriesUID')

    return map

@attr.s(hash=False)
class Orthanc(Pattern):
    host = attr.ib( default="localhost" )
    port = attr.ib( default="8042" )
    path = attr.ib( default=None )
    user = attr.ib( default="orthanc" )
    password = attr.ib( default="orthanc" )
    gateway = attr.ib( init=False )

    domains = attr.ib( factory=dict )  # Mapping of domain name -> retreive destination names

    @gateway.default
    def connect(self):
        return gateway.Orthanc(host=self.host, port=self.port, path=self.path,
                               user=self.user, password=self.password)

    @property
    def location(self):
        return self.gateway._url()

    def add_domain(self, domain: str, retrieve_dest: str=None ):
        self.domains[domain] = retrieve_dest

    def get(self, item: Union[str, Dixel], level: DicomLevel=DicomLevel.STUDIES, view: str="tags") -> Dixel:

        # Get needs to accept oid's or items with oid's
        if type(item) == Dixel:
            oid = item.oid()
            level = item.level
            meta = item.meta
        elif type(item) == str:
            oid = item
            meta = {'oid': oid}
        else:
            raise ValueError("Can not get type {}!".format(type(item)))

        self.logger.debug("{}: getting {}".format(self.__class__.__name__, oid))

        if view=="instance_tags":
            result = self.get(oid, level, view="meta")

            oid = result['Instances'][0]
            view = "tags"
            level = DicomLevel.INSTANCES
            # Now get tags as normal

        # print(oid)
        result = self.gateway.get_item(oid, level, view=view)
        if view == "tags":
            # We can clean tags and assemble a dixel
            result = dicom_clean_tags(result)
            item = Dixel(meta=result, level=level)
            return item
        elif view == "file" or \
             view == "archive":
            # We can assemble a dixel with a file
            item = Dixel(meta=meta, file=result, level=level)
            return item
        else:
            # Return the meta info or binary data
            return result

    def put(self, item: Dixel):
        self.logger.debug("{}: putting {}".format(self.__class__.__name__, item.uid))

        if item.level != DicomLevel.INSTANCES:
            self.logger.warning("Can only 'put' Dicom instances.")
            raise ValueError
        if not item.file:
            self.logger.warning("Can only 'put' file data.")
            raise KeyError
        result = self.gateway.put_item(item.file)

        if not result:  # Success!
            return item
        else:
            return result

    # Handlers

    def check(self, item: Dixel) -> bool:
        # self.logger.debug(item.level)
        try:
            res = self.gateway.get_item(item.oid(), item.level)
            # self.logger.debug("Found phi")
            return True
        except ConnectionError:
            try:
                res = self.gateway.get_item(item.sham_oid(), item.level)
                # self.logger.debug("Found anonymized")
                return True
            except ConnectionError:
                # self.logger.debug("Could not find {} or {}".format(item.oid(), item.sham_oid()))
                return False

    def anonymize(self, item: Dixel, replacement_map: Callable[[dict],dict]=simple_sham_map, remove: bool=False) -> Dixel:

        if not item.meta.get('ShamID'):
            item.set_shams()

        replacement_dict = replacement_map(item.meta)
        result = self.gateway.anonymize_item(item.oid(), item.level, replacement_dict=replacement_dict)
        # self.logger.debug(result)
        if remove:
            self.remove(item)
        # self.logger.debug(result)
        if result:
            if item.level == DicomLevel.INSTANCES:
                return Dixel( item.sham_oid(), file=result, level=DicomLevel.INSTANCES )
            else:
                return self.get( result['ID'], level=item.level )

    def remove(self, item: Dixel):
        oid = item.oid()
        level = item.level
        return self.gateway.delete_item(oid, level)

    def find_item(self, item: Dixel, domain: str="local", retrieve: bool=False):
        """
        Have some information about a dixel, want to find the STUID, SERUID, INSTUID
        """

        # self.logger.debug("Finding {}".format(item.oid()))

        def find_item_query(item):
            # Usually want to mask the dixel data to just AccessionNumber to isolate a study, or
            # AccessionNumber and SeriesDescription to isolate a series, if possible

            q = {}
            keys = {}

            # All levels have these
            keys[DicomLevel.STUDIES] = ['PatientID',
                                        'PatientName',
                                        'PatientBirthDate',
                                        'PatientSex',
                                        'StudyInstanceUID',
                                        'StudyDate',
                                        'StudyTime',
                                        'AccessionNumber']

            # Series level has these
            keys[DicomLevel.SERIES] = keys[DicomLevel.STUDIES] + \
                                      ['SeriesInstanceUID',
                                       'SeriesDescription',
                                       'ProtocolName',
                                       'SeriesNumber',
                                       'NumberOfSeriesRelatedInstances',
                                       'Modality']

            # For instance level, use the minimum
            keys[DicomLevel.INSTANCES] = ['SOPInstanceUID', 'SeriesInstanceUID']

            def add_key(q, key, dixel):
                q[key] = dixel.meta.get(key, '')
                return q

            for k in keys[item.level]:
                q = add_key(q, k, item)

            if item.level == DicomLevel.STUDIES and item.meta.get('Modality'):
                q['ModalitiesInStudy'] = item.meta.get('Modality')

            return q

        q = find_item_query(item)
        # self.logger.debug(q)

        result = self.find(q, item.level, domain, retrieve=retrieve)

        if result:
            # self.logger.debug(result)
            return item.update(result.pop())


    def find(self, q: Mapping, level: DicomLevel, domain: str, retrieve: bool=False):

        query = {'Level': str(level),
                 'Query': q}

        if retrieve:
            retrieve_dest = self.domains[domain]
        else:
            retrieve_dest = None

        results = self.gateway.find(query, domain, retrieve_dest)

        if results:
            worklist = set()
            for d in results:
                d['StudyDateTime'] = dicom_strpdtime(d['StudyDate'] + d['StudyTime'])
                d['PatientBirthDate'] = dicom_strpdate(d['PatientBirthDate'])
                # self.logger.debug(pformat(d))
                worklist.add( Dixel(meta=d, level=level ) )

            return worklist

    def send(self, item: Dixel, peer_dest: str=None, modality_dest: str=None):
        if modality_dest:
            return self.gateway.send_item(item.oid(), dest=modality_dest, dest_type="modalities")
        if peer_dest:
            return self.gateway.send_item(item.oid(), dest=peer_dest, dest_type="peers")

    def clear(self, desc: str="all"):
        if desc == "all" or desc == "studies":
            self.inventory['studies'] = self.gateway.get("studies")
            for oid in self.inventory['studies']:
                self.gateway.delete_item(oid, DicomLevel.STUDIES)
        elif desc == "exports":
            self.gateway.do_delete("exports")
        elif desc == "changes":
            self.gateway.do_delete("changes")
        else:
            raise NotImplementedError

    def info(self):
        return self.gateway.statistics()

    @property
    def instances(self):
        oids = self.gateway.get("instances")
        for oid in oids:
            yield Dixel(meta={'oid': oid}, level=DicomLevel.INSTANCES)


    @property
    def series(self):
        oids = self.gateway.get("series")
        for oid in oids:
            yield Dixel(meta={'oid': oid}, level=DicomLevel.SERIES)

    @property
    def studies(self):
        oids = self.gateway.get("studies")
        for oid in oids:
            yield Dixel(meta={'oid': oid}, level=DicomLevel.STUDIES)

#
# @attr.s
# class OrthancPeer(Pattern):
#     # An Orthanc peer is a way to reverse peer.put(item) to source.send(item, peer) for templating
#     source = attr.ib( type=Orthanc, default=None )
#     peer_name = attr.ib( type=str, default=None )
#
#     def put(self, item):
#         self.source.send(item, peer=self.peer_name)

