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
from diana.daemon.factory import factory
from diana.utils import merge_dicts_by_glob

config_yml = \
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


def update_config(fp, updates, post_config_action=None):
    try:
        with open(fp) as f:
            old_conf = json.load(f)
            new_conf = { **old_conf, **updates }
            if old_conf != new_conf:
                # changes were made
                json.dump(new_conf, fp)
                if post_config_action:
                    globals()[post_config_action['object']].__getattr__(post_config_action['method'])()
    except Exception:
        logging.error("Failed to install requested configuration updates.")


def parse_args():

    p = ArgumentParser(prog="DIANA-Watcher")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--dir", default=None,
                       help="Routing directory with python modules")
    group.add_argument("-c", "--config", default=None,
                       help="Config file containing single-route indexer config dict as json or yaml" )
    group.add_argument("-e", "--env", default=None,
                       help="Environment var containing single-route indexer json config dict")
    p.add_argument("-t", "--testfire",
                   help="Test fire an event and exit", action="store_true")
    p.add_argument("-g", "--genconf",
                   help="Generate a conf string from current configuration and exit",
                   action="store_true")

    return p.parse_args()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

    opts = {
        "dir": "/Users/derek/dev/DIANA/tests/test_routing"
    }

    # config = yaml.load(config_yml)

    # opts = parse_args()

    routes = {}

    if opts.get('env') or opts.get('config'):

        if opts.get('env'):
            config_json = os.environ.get('env')
            config = json.loads(config_json)
        elif opts.get('config'):
            fp = opts.get('config')
            with open(fp) as f:
                if fp.endswith('.json'):
                    config = json.load(f)
                elif fp.endswith('.yml') or fp.endswith('.yaml'):
                    config = yaml.safe_load(f)
                else:
                    raise TypeError("Unknown conf file type")

        if opts.get('genconf'):
            # dump sources, dests, and force config
            print(json.dumps(config, separators=[',', ':']))
            exit()

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

