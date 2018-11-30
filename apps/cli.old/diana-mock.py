# DIANA-Mock
# Merck, Fall 2017
#
# Simulate a real-time DICOM source generator
#
# $ dicom-mock -s _secrets/lifespan_services.yml scanner -d mock -m CT -r 60
# $ dicom-mock -S DIANA_SECRETS scanner -d mock -m CT -r 60
#
# Where secrets include an Orthanc destination named "mock"

import random, time, logging, os, json
from datetime import datetime, timedelta
from argparse import ArgumentParser
import yaml
import attr
from diana.apis import Orthanc
from diana.mock import MockStudy
from utils.arg_utils import *

def parse_args():

    p = ArgumentParser(prog="DIANA-Mock")
    p.add_argument("-n", "--name",           default="Mock scanner")
    p.add_argument("-m", "--modality",       default="CT", choices=["CT", "MR", "CR"]),
    p.add_argument("-r", "--rate",           default="10",
                                             help="Average generation rate in studies/hour")
    p.add_argument("-d", "--destination",    default="Destination service")

    add_service_opts(p)
    opts = vars( p.parse_args() )
    opts['services'] = get_services(opts)
    if opts['dump']:
        dump_config(opts, 'services')
        exit()

    return opts

@attr.s
class MockScanner(object):
    seed = attr.ib( default=None )
    name = attr.ib( type=str, default="Mock Scanner" )
    modality = attr.ib( type=str, default="CT" )
    rate = attr.ib( type=float, default=10, converter=float )

    @seed.validator
    def set_seed(self, attribute, value):
        if value:
            random.seed(value)

    def gen_study(self):
        s = MockStudy(seed=self.seed,
                      study_datetime=datetime.now(),
                      station_name = self.name,
                      modality=self.modality )
        return s

    def run(self, dest: Orthanc):

        while True:

            logging.info("Generating study")
            s = self.gen_study()

            for d in s.dixels():
                # logging.debug(d)
                d.gen_file()
                dest.put( d )

            ave_delay  = 60*60/self.rate
            this_delay = random.gauss(ave_delay, ave_delay*0.3)
            if this_delay < 0.1:
                this_delay = 0.1
            logging.info("Waiting {} secs".format(this_delay))
            time.sleep( this_delay )


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    opts = parse_args()
    services = opts['services']

    D = Orthanc(**services[opts.get('destination')])
    M = MockScanner(name = opts.get('name'),
                    modality = opts.get('modality'),
                    rate = opts.get('rate'))
    M.run(dest=D)