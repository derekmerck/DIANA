
import os
import sys
print os.getcwd()

sys.path.append(os.getcwd())

import logging
import yaml
from connect.Gateway import *
from connect.UpdateIndex import UpdatePatientDimensions

logging.basicConfig(level=logging.DEBUG)

with open('secrets.yaml') as f:
    credentials = yaml.load(f)

orthanc0 = OrthancGateway(address=credentials['orthanc0_address'])
splunk = SplunkGateway(address=credentials['splunk_address'],
                       hec_address=credentials['hec_address'])

UpdatePatientDimensions(orthanc0, splunk)