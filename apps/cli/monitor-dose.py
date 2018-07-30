#! python3
"""
monitor-dose
Merck, Summer 2018

Wrapper to configure and run a DoseReportHarvester daemon.

$ python3 dose-monitor -q "gepacs" -j "dose_reports"

"""

import logging, yaml
from argparse import ArgumentParser
from diana.apis import Orthanc, Splunk
from diana.daemon import DoseReportHarvester

def parse_args():

    p = ArgumentParser("monitor-dose")

    p.add_argument("-p", "--proxy",        default="proxy")
    p.add_argument("-q", "--proxy_domain", help="Orthanc remote aet")

    p.add_argument("-i", "--index",        default="splunk")
    p.add_argument("-j", "--index_domain", help="Splunk index name")
    p.add_argument("-h", "--index_hec",    default="diana",
                                           help="Splunk HEC token name")

    p.add_argument("-b", "--start",        default="now")
    p.add_argument("-c", "--increment",    default="-10m")

    p.add_argument("-r", "--repeat_while", default=False,
                                           help="False for one-shot, True for continuous")
    p.add_argument("-w", "--wait",         default=False,
                                           help="Wait for start + increment rather than scanning backwards")

    p.add_argument("-s", "--secrets",      default="secrets.yml")

    opts = p.parse_args()
    return opts


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    opts = parse_args()

    start = opts.start
    incr = opts.incr
    proxy_name = opts.proxy
    proxy_domain = opts.proxy_domain
    index_name = opts.index
    index_domain = opts.index_domain
    index_hec = opts.index_hec
    repeat_while = opts.repeat_while
    secrets_fn = opts.secrets

    with open(secrets_fn, 'r') as f:
        secrets = yaml.safe_load(f)

    proxy = Orthanc(**secrets[proxy_name])
    index = Splunk(**secrets[index_name])

    # TODO: Need to add a harvester with a delay that resets its time interval relative to now

    H = DoseReportHarvester(source=proxy, source_domain=proxy_domain,
                  dest=index, dest_domain=index_domain, dest_hec=index_hec,
                  start=start, incr=incr,
                  repeat_while=repeat_while)

    H.run()