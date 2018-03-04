
import os
import sys

import logging
import yaml
import datetime as dt
import math

from Orthanc import OrthancProxy
from Splunk import Splunk
from DianaConnect import get_it


def update_remote_study_index_over_time(proxy, index, start_dt, end_dt, incr, q=None):

    if math.abs(incr) >= 6:
        # It looks like q/r can only handle about a hundred returned answers at a time
        logging.warn("Don't set the hourly increment higher than 6, that is close to the upper limit on returned studies")

    if q==None:
        q = {'modality': 'CT'}

    start = start_dt
    while start > end_dt:

        # Determine study_date
        study_date = "{}-{}".format(dt.date(start), dt.date(start + incr))
        # Determine study_time
        study_time = "{}-{}".format(dt.time(start), dt.time(start + incr))

        q['study_date'] = study_date
        q['study_time'] = study_time

        results = proxy.search_remote(q)
        splunk.update(results)
        start = start+incr


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)

    with open('secrets.yaml') as f:
        secrets = yaml.load(f)

    # Remote for deathstar service is "GEPACS"
    deathstar  = OrthancProxy(**secrets['services']['deathstar'])
    splunk     = Splunk(**secrets['services']['splunk'])

    start_time = dt.now()
    end_time   = dt.date("01-01-2015")
    incr       = "-3h"

    update_remote_study_index_over_time(
        deathstar,
        splunk,
        start_time,
        end_time,
        incr
    )



