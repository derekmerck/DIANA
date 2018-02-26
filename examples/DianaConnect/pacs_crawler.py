
import os
import sys
print os.getcwd()

sys.path.append(os.getcwd())

import logging
import yaml
import datetime as dt
from connect.Gateway import *
from connect.UpdateIndex import UpdateRemoteStudyIndex, UpdateRemoteSeriesIndex

logging.basicConfig(level=logging.DEBUG)

with open('secrets.yaml') as f:
    credentials = yaml.load(f)

orthanc0 = OrthancGateway(address=credentials['orthanc0_address'])
pacs_proxy = OrthancGateway(address=credentials['pacs_proxy_address'])
splunk = SplunkGateway(address=credentials['splunk_address'],
                       hec_address=credentials['hec_address'])

remote="gepacs"

def UpdateRSIOverRange(year, month, day, n_days, h_incr=3, modality="CT"):

    if h_incr >= 6:
        # It looks like q/r can only handle about a hundred returned answers at a time
        logging.warn("Don't set the hourly increment any higher than 6 -- that is close to the upper limit for a normal day")

    for _day in range(0, n_days):
        d = dt.datetime(year, month, day) + dt.timedelta(_day)
        # logging.debug('date: {year}{month:02d}{day:02d}'.format(year=year, month=d.month, day=d.day))
        for t in range(0, 24, h_incr):
            UpdateRemoteStudyIndex(pacs_proxy, remote, splunk,
                                    study_date='{year}{month:02d}{day:02d}'.format(year=d.year, month=d.month, day=d.day),
                                    study_time='{start:02d}0000-{end:02d}5959'.format(start=t, end=t + h_incr - 1),
                                    modality=modality
                                   )

# UpdateRSIOverRange(2017, 5, 1, 18, modality="CT")

UpdateRemoteSeriesIndex(pacs_proxy, 'riha', splunk, accession_number='51475723')

