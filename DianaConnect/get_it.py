"""get_it.py
Merck
Winter 2018

Command-line tool for Orthanc proxy download:
> python get_it.py -AccessionNumber XYZ -PatientID 123 -p proxy -s secrets.yml

secrets.yml must have a section like services[proxy] suitable for creating an Orthanc
"""

from DixelKit.Dixel import *
from DixelKit.Orthanc import OrthancProxy
import logging
import yaml
from argparse import ArgumentParser


def get_it(PatientID, AccessionNumber, proxy):
    meta = {
        'PatientID': PatientID,
        'AccessionNumber': AccessionNumber
    }
    d = Dixel(AccessionNumber, meta=meta, level=DicomLevel.SERIES)
    proxy.get(d, retrieve=True)


def parse_args():
    p = ArgumentParser()
    p.add_argument("-p", "--PatientID", required=True)
    p.add_argument("-a", "--AccessionNumber", required=True)
    p.add_argument("-s", "--secrets", default="secrets.yml")
    p.add_argument("-p", "--proxy", default="deathstar")

    opts = p.parse_args()
    return opts


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    opts = parse_args()

    with open(opts.secrets, 'r') as f:
        secrets = yaml.load(f)
    proxy = OrthancProxy(**secrets['services'][opts.proxy])

    get_it(opts.PatientID, opts.AccessionNumber, proxy)


