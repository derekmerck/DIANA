from argparse import ArgumentParser
import os, json, yaml

def add_service_opts(parser: ArgumentParser):
    parser.add_argument("-s", "--services_config",
                    help="Service configuration yaml file")
    parser.add_argument("-S", "--services_env",
                    help="Service configuration environment var in yaml format")
    parser.add_argument("--dump", action="store_true",
                    help="Dump configuration as yaml and json")

def get_services(opts):
    services = {}
    if opts.get('services_config'):
        with open(opts.get('services_config')) as f:
            services.update(yaml.safe_load(f))
    if opts.get('services_env'):
        services.update(yaml.safe_load(os.environ.get(opts.get('services_env'))))

    return services

def dump_service_config(opts):
    # dump services for use as env
    print("YAML:")
    print(opts['services'])
    print("JSON:")
    print(json.dumps(opts['services'], separators=[',', ':']))
    exit()