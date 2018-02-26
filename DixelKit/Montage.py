import requests
from pprint import pformat
from Dixel import *
from DixelStorage import *
import DixelTools


class Montage(DixelStorage):

    def __init__(self, host, port=80, user=None, password=None):

        self.session = requests.session()
        if user and password:
            self.session.auth = (user, password)
        self.url = "http://{host}:{port}/api/v1".format(host=host, port=port)
        super(Montage, self).__init__()

        indices = self.session.get("{0}/index".format(self.url))
        self.logger.debug(indices.json())

    def query(self, qdict, index="rad"):
        url = "{0}/index/{1}/search".format(self.url, index)
        r = self.session.get(url, params=qdict)

        # self.logger.debug(pformat(r))
        return r.json()["objects"]

    # Assumes an AccessionNumber or PatientID and ReferenceTime field
    # Finds a MID (MontageID) if possible and fills in other patient and report data
    def update(self, dixel, time_delta=0, **kwargs):

        # if dixel.meta['mid']:
        #     # Already looked this exam up
        #     return dixel

        qdict = kwargs.get('qdict', {})

        PatientID = dixel.meta['PatientID']
        earliest, latest = DixelTools.daterange(dixel.meta['ReferenceTime'], time_delta)
        AccessionNumber = None

        q = PatientID
        if dixel.meta.get("AccessionNumber"):
            AccessionNumber = dixel.meta["AccessionNumber"]
            q = q + "+" + AccessionNumber

        qdict["q"] = q
        qdict["start_date"] = earliest
        qdict["end_date"] = latest

        r = self.query(qdict)

        # Got some hits
        if r:

            self.logger.debug(pformat(r))
            data = None

            if AccessionNumber:
                # Check and see if there is a match in r
                found = False
                for r_item in r:
                    if r_item["accession_number"] == AccessionNumber:
                        # Use this data
                        data = r_item
                        found = True
                        break
                if found == False:
                    self.logger.warning(
                        "Can't find Accession {0} in results!".format(AccessionNumber))
                    return dixel
            else:
                # If there is no AN, just use the first study returned
                data = r[0]

            # TODO: Should really take extractions as an argument
            # dmap = kwargs.get('dmap', {})
            #
            # for k, v in dmap:
            #     dixel.meta[k]

            suffix = kwargs.get('suffix', '')

            dixel.meta["Age"]             = data["patient_age"]
            dixel.meta["First Name"]      = data["patient_first_name"].capitalize()
            dixel.meta["Last Name"]       = data["patient_last_name"].capitalize()

            dixel.meta["AccessionNumber"+suffix] = data["accession_number"]
            dixel.meta["MID"+suffix]             = data["id"]                  # Montage ID
            dixel.meta["Report"+suffix]          = data['text']                # Report text
            dixel.meta["ExamCode"+suffix]        = data['exam_type']['code']   # IMG code

            # Try to find exam completed time
            for event in data['events']:
                if event['event_type'] == 5:
                    dixel.meta["ExamCompleted"+suffix] = event['date']

            return Dixel(id=dixel.meta["AccessionNumber"+suffix],
                         meta=dixel.meta,
                         level=DicomLevel.STUDIES)

        # No results
        else:
            return dixel


    def make_worklist(self, qdict):
        # Return a set of predixel results
        r = self.query(qdict)
        logging.debug(pformat(r))

        res = set()

        for item in r:

            meta = {
                'AccessionNumber': item[0]["accession_number"],
                'PatientID'      : item[0]["id"],                # Montage ID
                'ReportText'     : item[0]['text'],
                'ExamType'       : item[0]['exam_type']['code']  # IMG code
            }
            res.add(
                Dixel( id=meta['AccessionNumber'], meta=meta, level=DicomLevel.STUDIES )
            )

        return res

def test_montage():

    montage = Montage('montage', 80, 'm_user', 'passw0rd')

    qdict = { "q":          "cta",
              "modality":   4,
              "exam_type":  [8683, 7713, 8766],
              "start_date": "2016-11-17",
              "end_date":   "2016-11-19"}

    worklist = montage.make_worklist(qdict)
