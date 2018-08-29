#! python3
"""
DIANA-lookup.py
Derek Merck, Summer 2018

Wrapper command-line tool for Splunk query.

$ python3 DIANA-lookup.py --query "index=dose_report" -e "-1d" -l now -i my_splunk -s secrets.yml

`secrets.yml` must have a section called "my_splunk" with keys suitable for creating
an Splunk instance that can accept the query.
"""

import yaml, logging
from argparse import ArgumentParser
from diana.apis import Splunk
from diana.utils import DatetimeInterval


def parse_args():
    p = ArgumentParser("DIANA-lookup")
    p.add_argument("-q", "--query",    required=True)
    p.add_argument("-e", "--earliest", default="-1d")
    p.add_argument("-l", "--latest",   default="now")
    p.add_argument("-i", "--index",    default="splunk")
    p.add_argument("-s", "--secrets",  default="secrets.yml")

    opts = p.parse_args()
    return opts


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()
    q = opts.q
    earliest = opts.earliest
    latest = opts.latest
    index_name = opts.index
    secrets_fn = opts.secrets

    with open(secrets_fn, 'r') as f:
        secrets = yaml.load(f)

    index = Splunk(**secrets[index_name])

    result = index.find_items(q, DatetimeInterval( earliest, latest ))

    print(result)
