
from typing import Mapping
import attr
from ..utils import Pattern, gateway
from . import Dixel
from ..utils.dicom import DicomLevel
from . import RadiologyReport


@attr.s(hash=False)
class Montage(Pattern):
    host = attr.ib( default="localhost" )
    port = attr.ib( default="80" )
    path = attr.ib( default="api/v1" )
    user = attr.ib( default="montage" )
    password = attr.ib( default="montage" )
    gateway = attr.ib( init=False )

    domains = attr.ib( factory=dict )  # Mapping of domain name -> retreive destination names

    @gateway.default
    def connect(self):
        return gateway.Montage(host=self.host, port=self.port, path=self.path,
                               user=self.user, password=self.password)

    def __attrs_post_init__(self):
        indices = self.gateway.get("index")
        self.logger.debug(indices)

    @property
    def location(self):
        return self.gateway._url()

    def find(self, query: Mapping, index="rad"):
        r = self.gateway.find(query=query, index=index)

        ret = set()
        for item in r["objects"]:

            meta = {
                "AccessionNumber": item["accession_number"],
                "MontageID": item["id"],
                "ExamType": item['exam_type']['code'] }

            ret.add(Dixel(meta=meta, report=item['text'], level=DicomLevel.STUDIES))
        return ret



def test_montage(source):

    import logging
    from pprint import pformat

    logging.basicConfig(level=logging.DEBUG)
    qdict = {"q": "cta",
             "modality": 4,
             "exam_type": [8683, 7713, 8766],
             "start_date": "2016-11-17",
             "end_date": "2016-11-19"}
    worklist = source.find(qdict)
    logging.debug(pformat(worklist))
