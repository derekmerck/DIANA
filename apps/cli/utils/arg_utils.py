from argparse import ArgumentParser
import os, json, yaml, logging, re
from glob import glob

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
            path_matcher = re.compile(r'\$\{([^}^{]+)\}')

            # variable expansion -- see https://stackoverflow.com/a/52412796
            def path_constructor(loader, node):
                ''' Extract the matched value, expand env variable, and replace the match '''
                value = node.value
                match = path_matcher.match(value)
                env_var = match.group()[2:-1]
                return os.environ.get(env_var) + value[match.end():]

            yaml.add_implicit_resolver('!path', path_matcher)
            yaml.add_constructor('!path', path_constructor)

            services.update(yaml.safe_load(f))

    if opts.get('services_env'):
        services.update(yaml.safe_load(os.environ.get(opts.get('services_env'))))
    if opts.get('services_dir'):
        logging.debug(glob(os.path.join(opts.get('services_dir'), "*.yml")))
        fps = glob(os.path.join(opts.get('services_dir'), "*.yml"))
        for fp in fps:
            logging.debug(fp)
            with open(fp) as f:
                services.update(yaml.safe_load(f))

    return services

def dump_config(opts, key='services'):
    # dump services for use as env
    print("YAML:")
    print(opts[key])
    print("JSON:")
    print(json.dumps(opts[key], separators=[',', ':']))