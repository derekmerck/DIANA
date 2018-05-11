#! /usr/bin/python
"""
get_it.py

Merck
Winter 2018

Command-line tool for Orthanc proxy retrieve.

Usage:

```bash
> python get_it.py -patient_id 123 -accession_number XYZ -series_number 1 -p proxy -s secrets.yml
```

`secrets.yml` must have a section like services[proxy] suitable for creating an Orthanc
"""

from DixelKit.Dixel import *
from DixelKit.Orthanc import OrthancProxy
import logging
import yaml
from argparse import ArgumentParser


def get_it(proxy, patient_id, accession_number, series_number=''):
    meta = {
        'PatientID': patient_id,
        'AccessionNumber': accession_number,
        'SeriesNumber': series_number
    }
    d = Dixel(accession_number, meta=meta, level=DicomLevel.SERIES)
    proxy.get(d, retrieve=True)


def parse_args():
    p = ArgumentParser()
    p.add_argument("-p", "--patient_id", required=True)
    p.add_argument("-a", "--accession_number", required=True)
    p.add_argument("-r", "--series_number")
    p.add_argument("-s", "--secrets", default="./secrets.yml")
    p.add_argument("-o", "--proxy",   default="deathstar")

    opts = p.parse_args()
    return opts


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    opts = parse_args()

    with open(opts.secrets, 'r') as f:
        secrets = yaml.load(f)
    proxy = OrthancProxy(**secrets['lifespan'][opts.proxy])

    get_it(proxy, opts.patient_id, opts.accession_number, opts.series_number)


