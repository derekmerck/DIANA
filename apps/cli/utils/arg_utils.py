from argparse import ArgumentParser
import os, json, yaml, logging, re
from glob import glob
from pprint import pformat


def add_service_opts(parser: ArgumentParser):
    parser.add_argument("-s", "--services_file",
                    help="Service configuration yaml file")
    parser.add_argument("-S", "--services_env",
                    help="Service configuration environment var in yaml format")
    parser.add_argument("--services_dir",
                    help="Directory containing service configuration files in yaml format")
    parser.add_argument("--dump", action="store_true",
                    help="Dump configuration as yaml and json")


def get_services(opts):

    services = {}
    if opts.get('services_file'):
        with open(opts.get('services_file')) as f:
            print(f.read())
            ff = os.path.expandvars(f.read())
            print(ff)
            services.update(yaml.safe_load(ff))
    if opts.get('services_env'):
        ff = os.path.expandvars(os.environ.get(opts.get('services_env')))
        services.update(yaml.safe_load(ff))
    if opts.get('services_dir'):
        logging.debug(glob(os.path.join(opts.get('services_dir'), "*.yml")))
        fps = glob(os.path.join(opts.get('services_dir'), "*.yml"))
        for fp in fps:
            logging.debug(fp)
            with open(fp) as f:
                ff = os.path.expandvars(f.read())
                services.update(yaml.safe_load(ff))

    logging.debug(pformat(services))

    return services

def dump_config(opts, key='services'):
    # dump services for use as env
    print("YAML:")
    print(opts[key])
    print("JSON:")
    print(json.dumps(opts[key], separators=[',', ':']))