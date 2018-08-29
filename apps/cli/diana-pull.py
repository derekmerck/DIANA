#! python3
"""
pull-it.py
Derek Merck, Winter 2018

Wrapper command-line tool for Orthanc proxy retrieve from modality.

$ python3 pull-it.py -accession XYZ -series "thin * brain -p my_proxy -d my_pacs -s secrets.yml

`secrets.yml` must have a section called "my_proxy" with keys suitable for creating
an Orthanc instance that knows about the remote "my_pacs".
"""

import logging, yaml
from argparse import ArgumentParser
from diana.apis import Orthanc, Dixel
from diana.utils.dicom import DicomLevel

def parse_args():

    parser = ArgumentParser("DIANA-Pull")
    parser.add_argument("-a", "--accession", required=True)
    parser.add_argument("-s", "--secrets", default="./secrets.yml")

    parser.add_argument("-p", "--proxy",   required=True)
    parser.add_argument("-q", "--domain",  default=None,
                                           help="Orthanc remote aet")
    parser.add_argument("-r", "--series",  default=None)

    opts = parser.parse_args()

    return opts


if __name__ == "__main__":

    opts = parse_args()

    logging.basicConfig(level=logging.DEBUG)

    with open(opts.secrets, "r") as f:
        services = yaml.safe_load(f)

    orthanc = Orthanc(**services[opts.proxy])

    if not opts.series:
        d = Dixel(meta={"AccessionNumber": opts.accession},
                  level=DicomLevel.STUDIES)

    else:
        d = Dixel(meta={"AccessionNumber": opts.accession,
                        "SeriesDescription": opts.series},
                  level=DicomLevel.SERIES)

    orthanc.find_item(d, domain=opts.domain, retrieve=True)
