# Bridge between Orthanc gateway and Splunk

import os
import sys
print os.getcwd()

sys.path.append(os.getcwd())

import logging
import yaml
from connect.Gateway import *
from pprint import pformat

logging.basicConfig(level=logging.DEBUG)

with open('secrets.yaml') as f:
    credentials = yaml.load(f)
import argparse

def parse_args():

    # create the top-level parser
    parser = argparse.ArgumentParser(prog='ask_orthanc')
    parser.add_argument('ID')
    return parser.parse_args()

def ask_orthanc(orthanc, qlevel, ID, dtype):
    orthanc.level = qlevel
    r = orthanc.GetItem(ID, dtype=dtype)
    logging.debug(pformat(r))
    return r

if __name__=="__main__":
    opts = parse_args()
    orthanc0 = OrthancGateway(address=credentials['orthanc0_address'])

    # opts.ID = "f1791473-8a5c07ad-c2a01863-5506f3c5-92ffd5a1"

    opts.ID = "3f5b89c0-04c749cb-19927fcc-d8e93159-25eb429c"
    opts.ID = "ae41ffb4-297f51ae-1c83ec22-fb2ab348-d0613a2a"
    
    r = ask_orthanc(orthanc0, 'series', opts.ID, 'info')
    instance = r['Instances'][0]
    r = ask_orthanc(orthanc0, 'instances', instance, 'tags')

    cfov = None
    if r.get('ReconstructionTargetCenterPatient'):
        cfov = r.get('ReconstructionTargetCenterPatient')
    elif r.get('RACoordOfTargetReconCentre'):
        cfov = r.get('RACoordOfTargetReconCentre').split("\\")

    AccessionNumber = r.get("AccessionNumber")

logging.debug("Accession {0}: {1}".format(AccessionNumber, cfov))
