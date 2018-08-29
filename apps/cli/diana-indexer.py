#! python3
"""
index-it.py
Derek Merck, Summer 2018

Wrapper command-line tool for pre-index caching and restoring.

$ python3 index-it.py --location /my_path --redis_service my_redis -s secrets.yml

$ python3 index-it.py -l /my_path -r my_redis -s secrets.yml restore --an abcxyz123 -d orthanc

`secrets.yml` must have a section called "my_redis" with keys suitable for creating
a Redis instance.

No python3 on a system that needs reindexed?  Docker to the rescue...

$ docker run -v /orthanc/db:/orthanc/db -it derekmerck/diana:amd64 /bin/bash
# scp server:/secrets.yml .
# python3 apps/cli/index-it.py -l /orthanc/db -r redis -s /secrets.yml index -w orthanc
...

"""

from argparse import ArgumentParser
import yaml, logging
from diana.apis import Orthanc
from diana.daemon import FileIndexer

def parse_args(args=None):

    p = ArgumentParser("DIANA-Indexer")
    p.add_argument("-l", "--location",      default="")
    p.add_argument("-r", "--redis_service", default="redis")
    p.add_argument("-s", "--secrets",       default="secrets.yml")

    subs = p.add_subparsers(dest="command")

    r = subs.add_parser("index")
    r.add_argument("-w", "--walk_type",      default="unstructured", choices=["unstructured", "orthanc"])
    r.add_argument("-c", "--clear_cache",    default="false")
    r.add_argument("-p", "--relpath",        default=None)
    r.add_argument("-R", "--rex",            default=r"*.dcm")

    r = subs.add_parser("restore")
    r.add_argument("-a", "--accession_number",      default="")
    r.add_argument("-d", "--destination_service",   default="orthanc")

    opts = p.parse_args(args)
    return opts


def test_opts():
    opts = parse_args(
        '--location /Users/derek/data/DICOM -s secrets/lifespan_services.yml index -w orthanc -p Christianson'.split())

    print(opts)

    opts = parse_args(
        '--location /Users/derek/data/DICOM -s secrets/lifespan_services.yml restore --accession_number 4758606 -d proxy0'.split())

    print(opts)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    if opts.command == "index":
        with open(opts.secrets) as f:
            services = yaml.safe_load(f)
        redis_conf = services['redis']

        x = FileIndexer(location=opts.location, redis_conf=redis_conf)

        if opts.clear_cache:
            x.cache.clear()

        if opts.walk_type == "orthanc":
            x.run_orthanc(relpath=opts.relpath)
        else:
            x.run(relpath=opts.relpath, rex=opts.rex)

    elif opts.command == "restore":
        with open(opts.secrets) as f:
            services = yaml.safe_load(f)
        redis_conf = services[opts.redis_service]
        orthanc_conf = services[opts.destination_service]

        x = FileIndexer(location=opts.location, redis_conf=redis_conf)
        orthanc = Orthanc(**orthanc_conf)
        x.put_accession(accession_number=opts.accession_number, dest=orthanc)


    else:

        print("Valid commands are index or restore, see help for more info")
