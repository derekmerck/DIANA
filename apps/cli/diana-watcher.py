"""
Remotely-configurable DIANA-watcher
Derek Merck, Summer 2018

Can also reconfigure a local orthanc instance with a shared config file to add local destinations.
"""

import os, logging, json, yaml
from functools import partial
from argparse import ArgumentParser
from datetime import datetime
from diana.daemon import DianaWatcher, DianaEventType
from diana.daemon.watcher import set_proxied_index_route, set_upload_files_route,\
                                 set_anon_and_forward_route, set_index_tags_route
from diana.daemon.factory import factory
from diana.utils import merge_dicts_by_glob

#config_yml = \
"""
# DIANA-Watcher config

source:
  pattern:
    class: ObservableOrthancProxy
    host: trusty64
    port: 42001
    
    query_dict:
      ModalitiesInStudy: ''
      StudyDescription:  '*'
    query_domain: mypacs
    query_level: 1                   # Studies
    query_discovery_period: -300     # Look back 5 mins

    polling_interval: 120            # Check every 2 mins

dest:
  pattern:
    class: Splunk
    host: trusty64

    default_index: watcher
    default_token: watcher
    hec_tokens: 
      watcher: 65d4ab0a-9a00-4fa2-b150-8343f0d168da
      
# If the watcher container shares the orthanc container
force_config:
  fp: /etc/orthanc/orthanc.json
  updates:
    modalities:
      mypacs: ['pacs_ip', 'pacs_port', 'pacs_aet']
  post_config_action:
    object: source
    method: reset  # Hot restart orthanc with new config
"""

#
# def do_updates(updates):
#
#     def do_update(fp, updates, post_config_action=None):
#         logging.debug(fp)
#         logging.debug(updates)
#         logging.debug(post_config_action)
#         # try:
#         old_conf = {}
#         if os.path.exists(fp):
#             with open(fp) as f:
#                 old_conf = json.load(f)
#         new_conf = {**old_conf, **updates}
#         logging.debug(new_conf)
#
#         if old_conf != new_conf:
#             # changes were made
#             with open(fp, 'w') as f:
#                 json.dump(new_conf, f)
#             # if post_config_action:
#             #     # ie, restart Orthanc
#             #     globals()[post_config_action['object']].__getattr__(post_config_action['method'])()
#         # except Exception:
#         #     logging.error("Failed to install requested configuration updates.")
#
#         logging.debug(globals())
#
#         logging.debug(locals())
#
#     for update in updates:
#         do_update(**update)

def get_route(route_name, source_name, dest_name):
    # Named DIANA routes

    source_kwargs = services.get(source_name)
    dest_kwargs = services.get(dest_name)

    if route_name == "proxied_index":
        route = set_proxied_index_route(source_kwargs, dest_kwargs)

    elif route_name == "upload_file":
        route = set_upload_files_route(source_kwargs, dest_kwargs)

    elif route_name == "anon_and_forward":
        route = set_anon_and_forward_route(source_kwargs, dest_kwargs)

    elif route_name == "index_tags":
        route = set_index_tags_route(source_kwargs, dest_kwargs)

    else:
        raise ValueError('No loader for {}'.format(route_name))

    return route


def parse_args():

    p = ArgumentParser(prog="DIANA-Watcher")

    p.add_argument("-s", "--services_config",
                   help="Service configuration yaml file")
    p.add_argument("-S", "--services_env",
                   help="Service configuration environment var in yaml format")

    p.add_argument("-r", "--route", nargs=3,
                   help="Single route configuration as 3-tuple 'route source dest'")
    p.add_argument("-c", "--routes_config",
                   help="Multiple-route configuration file in yaml format [[route, source, dest],...]")
    p.add_argument("-C", "--routes_env",
                   help="Multiple-route configuration environment var in yaml format [[route, source, dest],...]")

    # p.add_argument("-u", "--updates_config",
    #                help="Updates file for an available config file in yaml format")
    # p.add_argument("-U", "--updates_env",
    #                help="Updates environment var for an available config file in yaml format")

    p.add_argument("-d", "--dump",
                   help="Dump yaml and json strings for the current configuration and exit",
                   action="store_true")

    return vars( p.parse_args() )


if __name__ == "__main__":

    # Reduce junk output
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

    opts = parse_args()

    # opts = {
    #     "services": "/Users/derek/dev/DIANA/examples/mockPACS/dev_watcher_services.yml",
    #     "route": ['proxied_index', 'orthanc_proxy', 'splunk'],
    #     "dump": False
    # }

    # logging.debug(opts)

    watcher = DianaWatcher()

    services = {}
    if opts.get('services_config'):
        with open( opts.get('services') ) as f:
            services.update( yaml.safe_load(f) )
    if opts.get('services_env'):
        services.update( yaml.safe_load( os.environ.get(opts.get('services_env'))) )

    # updates = []
    # if opts.get('updates'):
    #     with open( opts.get('updates') ) as f:
    #         updates += yaml.safe_load(f)
    # if opts.get('updates_env'):
    #     updates += yaml.safe_load( os.environ.get(opts.get('updates_env')))
    #
    # updates= [{
    #         'fp': "/Users/derek/Desktop/hello.json",
    #         'updates': {'second_field': [1,2,3]},
    #         'post_config_action': {'object': 'source', 'method':'reset'}
    #         }]
    #
    # if updates:
    #     do_updates(updates)

    if opts.get('dump'):
        # dump services for use as env
        print("YAML:")
        print(services)
        print("JSON:")
        print(json.dumps(services, separators=[',', ':']))
        exit()

    routes = {}
    if opts.get('route'):
        # Single route by name
        route = get_route(*opts.get('route'))
        routes.update( route )

    if opts.get('routes_config'):
        # multiple routes by name
        with open( opts.get('routes_config') ) as f:
            routes_config = yaml.safe_load(f)
            for route_conf in routes_config:
                route = get_route(*route_conf)
                routes.update(route)

    if opts.get('routes_config_env'):
        routes_config = yaml.safe_load( os.environ.get(opts.get('routes_config_var')))
        for route_conf in routes_config:
            route = get_route(*route_conf)
            routes.update(route)

    if not routes:
        raise ValueError("No routes indicated, nothing to do.")

    watcher.add_routes(routes)
    watcher.run()

    exit()





    # config = yaml.load(config_yml)

    # opts = parse_args()

    routes = {}

    if opts.get('env') or opts.get('config'):

        if opts.get('config_env'):
            config_json = os.environ.get(opts.get('config_env'))
            config = yaml.load(config_json)
        elif opts.get('config'):
            fp = opts.get('config')
            with open(fp) as f:
                if fp.endswith('.json'):
                    config = json.load(f)
                elif fp.endswith('.yml') or fp.endswith('.yaml'):
                    config = yaml.safe_load(f)
                else:
                    raise TypeError("Unknown conf file type")

        source = factory(**config['source']['pattern'])
        dest = factory(**config['dest']['pattern'])

        # Do not do a deep index (no pull), just anonymize results by line and put in index
        routes[(source, DianaEventType.NEW_MATCH)]: \
                partial(DianaWatcher.index_by_proxy, dest=dest,
                                                retrieve=False,
                                                anonymize=True)

    if opts.get('dir'):
        expr = os.path.join(opts.get('dir'), "*.py")
        routes = merge_dicts_by_glob( expr, 'routing')
        # logging.debug(routes)

    watcher = DianaWatcher()
    watcher.routes = routes

    logging.debug( watcher.routes )

    if opts.get('testfire'):

        from diana.apis import Dixel
        from diana.utils.dicom import DicomUIDMint, SuffixStyle
        from diana.utils import Event

        watcher.fire(Event(DianaEventType.NEW_MATCH,
                           Dixel(meta={
                                "AccessionNumber": "TEST-FIRE",
                                "PatientID": "My Subject",
                                "StudyDateTime": datetime.now(),
                                'StudyDescription': "My Study",
                                'StudyInstanceUID': DicomUIDMint().uid(suffix_style=SuffixStyle.RANDOM)},
                                 ),
                           event_source=source))

    else:
        watcher.run()


