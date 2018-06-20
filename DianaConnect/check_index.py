
from Splunk import Splunk
from argparse import ArgumentParser
import yaml
import logging

def check_index(index, q, output_mode="json"):
    ret = index.oneshot(q, output_mode=output_mode)
    return ret


def parse_args():
    p = ArgumentParser()
    p.add_argument("-q", "--query", required=True)
    p.add_argument("-s", "--secrets", default="secrets.yml")
    p.add_argument("-i", "--index", default="splunk")
    p.add_argument("-o", "--output", choices=["csv", "json"], default="json")

    opts = p.parse_args()
    return opts


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()
    q = opts.q
    index_name = opts.index
    secrets_fn = opts.secrets
    output = opts.output

    with open(secrets_fn, 'r') as f:
        secrets = yaml.load(f)

    index = Splunk(**secrets['services'][index_name])
    check_index(index, q, output_mode=output)
