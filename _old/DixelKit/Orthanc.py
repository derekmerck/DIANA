from requests import session, ConnectionError
import logging
from pprint import pformat
import json

class Orthanc(object):

    def __init__(self, host, port, user, password):
        self.addr = "http://{host}:{port}".format(host=host, port=port)
        self.session = session()
        self.session.auth = (user, password)

        self.logger = logging.getLogger("Orthanc")

        peers = self.session.get("{0}/peers".format(self.addr))
        self.logger.debug(peers.json())

    def send_item(self, peer, id):
        url = "{0}/peers/{1}/store".format(self.addr, peer)
        self.session.post(url, data=id)

    def query_remote(self, remote, level="studies", query=None, retrieve=False):
        data = {'Level': level,
                'Query': query}

        url = '{0}/modalities/{1}/query'.format(self.addr, remote)

        self.logger.debug(url)
        self.logger.debug(json.dumps(data))

        headers={"Accept-Encoding": "identity",
                 "Accept": "application/json"}

        try:
            r = self.session.post(url, json={}, headers=headers)
        except ConnectionError as e:
            self.logger.error(e)
            self.logger.error(e.request.headers)
            self.logger.error(e.request.body)



        qid = r.json()["ID"]

        url = '{0}/queries/{1}/answers'.format(self.addr, qid)
        r = self.session.get(url)
        answers = r.json()

        for a in answers:
            url = '{0}/queries/{1}/answers/{2}/content'.format(self.addr, qid, a)
            r = self.session.get(url)

            logging.debug(r.json())

        return r

def test_orthanc_rqr(source, remote, _qdict={}):

    qdict = {'PatientID': '',
             'StudyInstanceUID': '',
             'StudyDate': '',
             'StudyTime': '',
             'AccessionNumber': '',
             'ModalitiesInStudy': 'CT'}
    qdict.update(_qdict)

    q = source.query_remote(remote, query=qdict)

if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)
