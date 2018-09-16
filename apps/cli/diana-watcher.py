"""
Remotely-configurable DIANA-watcher
Derek Merck, Summer 2018

Can also reconfigure a local orthanc instance with a shared config file to add local destinations.
"""

from diana.daemon import DianaWatcher
from diana.daemon.watcher import set_proxied_index_route, set_upload_files_route,\
                                 set_anon_and_forward_route, set_index_tags_route
from utils.arg_utils import *


def get_route(name, src, dest):
    # Named DIANA routes

    source_kwargs = services.get(src)
    dest_kwargs = services.get(dest)

    if name == "proxied_index":
        route = set_proxied_index_route(source_kwargs, dest_kwargs)

    elif name == "upload_file":
        route = set_upload_files_route(source_kwargs, dest_kwargs)

    elif name == "anon_and_forward":
        route = set_anon_and_forward_route(source_kwargs, dest_kwargs)

    elif name == "index_tags":
        route = set_index_tags_route(source_kwargs, dest_kwargs)

    else:
        raise ValueError('No loader for route "{}"'.format(name))

    return route


def parse_args():

    def add_routing_opts(p):
        p.add_argument("-r", "--route", nargs=3,
                       help="Single route configuration as 3-tuple 'route source dest'")

        p.add_argument("-c", "--routes_file",
                       help="Multi-route configuration file in yaml format [{name: route, src: source, dest: dest],...]")
        p.add_argument("-C", "--routes_env",
                       help="Multi-route configuration environment var in yaml format [{name: route, src: source, dest: dest],...]")
        p.add_argument("--routes_dir",
                       help="Directory with multiple multi-route config files in yaml format [{name: route, src: source, dest: dest],...]")
        return p

    def get_routes(opts):
        routes = []
        if opts.get('route'):
            # Single route by name
            name, src, dest = opts.get("route")
            routes.append({'name': name, 'src': src, 'dest': dest})

        if opts.get('routes_file'):
            # multiple routes by name
            with open(opts.get('routes_file')) as f:
                routes_config = yaml.safe_load(f)
                for route_conf in routes_config:
                    routes.append( route_conf )

        if opts.get('routes_env'):
            routes_config = yaml.safe_load(os.environ.get(opts.get('routes_env')))
            for route_conf in routes_config:
                routes.append(route_conf)

        if opts.get('routes_dir'):
            fps = glob("{}/*.yml".format(opts.get('routes_dir')))
            logging.debug(fps)
            for fp in fps:
                with open(fp) as f:
                    routes_config = yaml.safe_load(f)
                    for route_conf in routes_config:
                        routes.append(route_conf)

        return routes

    p = ArgumentParser(prog="DIANA-Watcher")
    add_service_opts(p)
    add_routing_opts(p)
    opts = vars( p.parse_args() )
    opts['services'] = get_services(opts)
    opts['routes']   = get_routes(opts)
    if opts['dump']:
        dump_config(opts, 'services')
        dump_config(opts, 'routes')
        exit()

    return opts


if __name__ == "__main__":

    # Reduce junk output
    logging.basicConfig(level=logging.DEBUG)
    # logging.getLogger("requests").setLevel(logging.WARNING)
    # logging.getLogger("urllib3").setLevel(logging.WARNING)
    # logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

    opts = parse_args()
    watcher = DianaWatcher()

    services = opts.get('services')
    routes = opts.get('routes')

    if not services:
        raise ValueError("No services defined, nothing to do.")
    if not routes:
        raise ValueError("No routes defined, nothing to do.")

    # Convert route definitions into object-anchored routes
    expanded_routes = {}
    for route_def in routes:
        expanded_route = get_route(**route_def)
        expanded_routes.update( expanded_route )

    watcher.add_routes(expanded_routes)
    watcher.run()

