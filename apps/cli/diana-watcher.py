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
    group.add_argument("-c", "--config", default=None,
                       help="Config file containing config dict" )
    group.add_argument("-e", "--env", default=None,
                       help="Environment var containing json config dict")
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
        "testfire": True
    }

    # opts = parse_args()

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

    config = yaml.load(config_yml)

    if opts.get('genconf'):
        print( json.dumps(config, separators=[',',':']) )
        exit()

    source = factory( **config['source']['pattern'] )

    if config.get('force_config'):
        update_config(**config.get('force_config'))


    dest = factory( **config['dest']['pattern'] )
    watcher = DianaWatcher()

    # Do not do a deep index (no pull), just anonymize results by line and put in index
    watcher.routes = {
        (source, DianaEventType.NEW_MATCH):
            partial(watcher.index_by_proxy, dest=dest,
                                            retrieve=False,
                                            anonymize=True)
        }

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


