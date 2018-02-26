
import os
import sys
print os.getcwd()

sys.path.append(os.getcwd())

import logging
import yaml
from connect.Gateway import *
from connect.UpdateIndex import UpdateSeriesIndex, UpdateDoseReports, UpdatePatientDimensions

logging.basicConfig(level=logging.DEBUG)

with open('secrets.yaml') as f:
    credentials = yaml.load(f)

orthanc0 = OrthancGateway(address=credentials['orthanc0_address'])
splunk = SplunkGateway(address=credentials['splunk_address'],
                       hec_address=credentials['hec_address'])

# Update the series index
UpdateSeriesIndex(orthanc0, splunk)

# Update the dose reports

# Use a different database
splunk.index_names['dose'] = 'dose_reports1'

UpdateDoseReports(orthanc0, splunk)

# Update patient dimensions for SSDE
UpdatePatientDimensions(orthanc0, splunk)

# Update the PACS index from the last hour
# ...
