from DixelStorage import DixelStorage

from pprint import pformat
from splunklib import client, results
from datetime import datetime
import json

class Splunk(DixelStorage):

    def __init__(self, host, port, user, password):
        super(Splunk, self).__init__()

        # Create a Service instance and log in
        self.service = client.connect(
            host=host,
            port=port,
            username=user,
            password=password)

        # Print installed apps to the console to verify login
        for app in self.service.apps:
            self.logger.debug(app.name)

    def oneshot(self, q, output_mode="json", **kwargs):

        for key, value in kwargs.iteritems():
            if type(value) is datetime:
                kwargs[key] = value.isoformat()
            # self.logger.debug("{0}: {1}".format(key, value))

        r = self.service.jobs.oneshot(q, output_mode=output_mode, **kwargs)

        if output_mode == "json":
            data = json.loads(r.read())['results']
            self.logger.debug(pformat(data))
            return data

    def get_series(self, index, patient_id, desc, start, end):

        kwargs = {"earliest_time": start,
                  "latest_time": end}

        q = """search index="{index}" PatientID="{patient_id}" SeriesDescription="{desc}"| 
               fields _time AccessionNumber ID SeriesDescription | 
               fields - _*"""
        q = q.format(index=index, patient_id=patient_id, desc=desc)

        return self.oneshot(q, **kwargs)


def test_splunk(source):

    source.find_series("dicom_series", "*", "*brain*", "-1h", "now")
