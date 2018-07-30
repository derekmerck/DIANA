from requests import session
import logging
from pprint import pformat

class Montage(object):

    def __init__(self, host, user, password, port=80):
        self.addr = "http://{host}:{port}/api/v1".format(host=host, port=port)
        self.session = session()
        self.session.auth = (user, password)

        self.logger = logging.getLogger("Montage")

        indices = self.session.get("{0}/index".format(self.addr))
        self.logger.debug(indices.json())


    def query(self, qdict, index="rad"):

        url = "{0}/index/{1}/search".format(self.addr, index)
        r = self.session.get(url, params=qdict)

        self.logger.debug(pformat(r))
        return r.json()["objects"]


def test_montage(source):
    qdict = {"q": "cta",
             "modality": 4,
             "exam_type": [8683, 7713, 8766],
             "start_date": "2016-11-17",
             "end_date": "2016-11-19"}
    r = source.query(qdict)
    logging.debug(pformat(r))

    AN = r[0]["accession_number"]          # AccessionNumber
    mid = r[0]["id"]                       # Montage ID
    Report = r[0]['text']                  # Report text
    exam_type = r[0]['exam_type']['code']  # IMG code
