#! /usr/bin/python

import logging
from hashlib import md5
from pprint import pformat
import argparse
import time
import collections
import json
from datetime import datetime

# Make sure to install these packages in env
import requests
import yaml

# Make sure to include this in distribution
from StructuredTags import simplify_tags


def handle_study(s, task):

    url = "{0}/studies/{1}/shared-tags?simplify".format(task.source, s)
    r = requests.get(url, auth=task.auth)
    info = r.json()
    # logging.debug(pformat(info))

    t = None  # Deidentified study id, s is presumed to have PHI

    if task.anonymize:

        deidentified = False
        if info.get("PatientIdentityRemoved")=="Yes" or \
           info["PatientName"].startswith(task.anon_prefix):

            deidentified = True
            logging.debug("{0} is already deidentified".format(info['PatientName']))
            t = s
            s = None

        if not deidentified:
            # Deidentify
            anon = anonymizer(info, task.anon_prefix)
            logging.debug(json.dumps(anon))
            url = "{0}/studies/{1}/anonymize".format(task.source, s)
            r = requests.post(url, data=json.dumps(anon), auth=task.auth, headers={'content-type': 'application/json'})

            # Get anon id back
            info = r.json()
            logging.debug(pformat(info))
            t = info['ID']

    # TODO: First check w dest about current held items/force
    if task.dest:
        if task.anonymize:
            data = t
        else:
            data = s
        url = "{0}/peers/{1}/store".format(task.source, task.dest)
        r = requests.post(url, data=data, auth=task.auth, headers={'content-type': 'application/text'})

    # TODO: First check w dest about currently held items/force
    if task.indexer_dest:
        if task.anonymize:
            item = t
        else:
            item = s

        # Get all series in item
        url = '{0}/studies/{1}'.format(task.source, item)
        r = requests.get(url, auth=task.auth)
        series = r.json()['Series']

        for ss in series:
            url = '{0}/series/{1}/shared-tags?simplify'.format(task.source, ss)
            r = requests.get(url, auth=task.auth)
            tags = r.json()
            # # Don't really need to do this at series level...
            data = simplify_tags(tags)

            logging.debug(pformat(tags))

            url = "services/collector/event"
            r = task.indexer_gateway.post(url, tags, source=task.source, dest=task.indexer_dest)

    if task.delete_anon and t:
        # Delete deidentified data from source
        url = "{0}/studies/{1}".format(task.source, t)
        r = requests.delete(url, auth=task.auth)

    if task.delete_phi and s:
        # Delete PHI data from source
        url = "{0}/studies/{1}".format(task.source, s)
        r = requests.delete(url, auth=task.auth)


def continuous():

    for task in tasks:

        # logging.debug(task)

        # Deidentify and move a few _recent_ studies to dest
        url = "{0}/changes".format(task.source)
        r = requests.get(url,
                         params = {'since': task.current,
                                   'limit': 100},
                         auth=task.auth)
        q = r.json()
        # logging.debug(pformat(q))

        for change in q['Changes']:
            if change['ChangeType'] == 'StableStudy':
                handle_study(change['ID'], task)

        task.current = q['Last']

        if q['Done']:
            logging.debug('Everything has been processed up to {0}: Waiting...'.format(task.current))


def one_shot():
    # For one-shots, we should confirm that the data is not
    # already on the dest/index_dest

    logging.debug('Starting one shot processing')

    for task in tasks:

        # Build a worklist
        url = "{0}/studies".format(task.source)
        r = requests.get(url, auth=task.auth)
        studies = r.json()

        logging.debug(studies)

        for s in studies:
            handle_study(s, task)


# Simple default anonymization function

def anonymizer(d, anon_prefix=None):
    r = {'Replace': {
            'PatientName':      anon_prefix + md5(d['PatientID']).hexdigest()[0:8],
            'PatientID':        md5(d['PatientID']).hexdigest(),
            'AccessionNumber':  md5(d['AccessionNumber']).hexdigest()
         },
         'Keep': ['StudyDescription', 'SeriesDescription', 'StudyDate'],
         # Need 'Force' to change PatientID
         'Force': True
        }
    return r


# Helper classes for REST API and Tasks

class Gateway(object):

    def __init__(self, addr, auth):
        self.addr = addr
        self.auth = auth

    # implement get/put/delete/post wrapper

    def post(self, url, data, headers=None, **kwargs):

        if not headers:
            headers = {}

        # Encodes datetime and hashes
        class SafeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                if hasattr(obj, 'hexdigest'):
                    return obj.hexdigest()
                return json.JSONEncoder.default(self, obj)

        if type(data) is dict or type(data) is collections.OrderedDict:
            headers.update({'content-type': 'application/json'})
            data = json.dumps(data, cls=SafeEncoder)
        elif isinstance(data, str):
            headers.update({'content-type': 'text/plain'})

        r = requests.post(url, data=data, headers=headers)
        return r

    def get(self, url, params=None, headers=None, **kwargs):
        if not headers:
            headers = {}
        if not params:
            params = {}
        r = requests.get(url, params=params, headers=headers, auth=self.auth)
        return r


class OrthancGateway(Gateway):

    def __init__(self, addr, user, password):
        auth = (user, password)
        super(OrthancGateway, self).__init__(addr, auth)


class SplunkGateway(Gateway):

    def __init__(self, addr, user=None, password=None, token=None):
        auth = (user, password)
        super(SplunkGateway, self).__init__(addr, auth)
        self.token = token

    def post(self, url, data, headers=None, source=None, dest=None, **kwargs):

        if not headers:
            headers = {}

        def epoch(dt):
            tt = dt.timetuple()
            return time.mktime(tt)

        url = '{0}/services/collector/event'.format(self.addr)

        data = collections.OrderedDict([('time', epoch(data['InstanceCreationDateTime'])),
                                        ('host', source),
                                        ('sourcetype', '_json'),
                                        ('index', dest),
                                        ('event', data)])

        headers.update({'Authorization': 'Splunk {0}'.format(self.token)})

        r = super(SplunkGateway,self).post(url, data, headers)
        return r


class Task(object):

    def __init__(self, d):
        self.source = d.get('source')
        self.auth =  (d.get('user', 'Orthanc'),
                      d.get('password'))
        self.dest =   d.get('dest')

        self.indexer = d.get('indexer')
        self.indexer_user = d.get('indexer_user'),
        self.indexer_password = d.get('indexer_password')
        self.indexer_token = d.get('indexer_token')
        self.indexer_dest = d.get('indexer_dest')

        self.anonymize = d.get('anonymize')
        self.anon_prefix = d.get('anon_prefix')
        self.delete_phi = d.get('delete_phi')
        self.delete_anon = d.get('delete_anon')

        self.current = 0

        self.source_gateway = OrthancGateway(addr=d.get('source'),
                                             user=d.get('user', 'Orthanc'),
                                             password=d.get('password'))

        self.indexer_gateway = SplunkGateway(addr=d.get('indexer'),
                                             user=d.get('indexer_user'),
                                             password=d.get('indexer_password'),
                                             token=d.get('indexer_token'))

    def __str__(self):
        return str( self.__dict__ )


# Setup Parsers

def parse_config(fn):

    tasks = []
    with open(fn) as f:
        config = yaml.load(f)
        for task in config['tasks']:
            tasks.append(Task(task))

    return tasks, config.get('delay')


def parse_args():

    parser = argparse.ArgumentParser(prog='d-mon')

    # In config, multiple tasks may be defined with these params
    parser.add_argument('--source',        help='Orthanc address - http://host:port/api')
    parser.add_argument('--user')
    parser.add_argument('--password')

    parser.add_argument('--indexer',       help='Splunk HEC address - http://host:port/api', default=None)
    parser.add_argument('--indexer_user',  default=None)
    parser.add_argument('--indexer_password', default=None)
    parser.add_argument('--indexer_token', help='Splunk HEC token', default=None)

    parser.add_argument('--dest',          help='Copy-to Orthanc peer name in source', default=None)
    parser.add_argument('--indexer_dest',  help='Index-to Splunk index name', default=None)

    parser.add_argument('--anonymize',     help='True/False (False)', default=None, action='store_true')
    parser.add_argument('--anon_prefix',   help="If anonymizing, optional prefix for new name (None)", default=None)

    parser.add_argument('--delete_phi',    help='True/False (False)', action='store_true')
    parser.add_argument('--delete_anon',   help='True/False (False)', action='store_true')

    # Only one delay and config allowed
    parser.add_argument('--delay',         help='-1 for one shot, otherwise seconds (2)', default=2)
    parser.add_argument('--config',        help='YML config file for multiple tasks (None)', default=None)

    return parser.parse_args()


# Command-line invocation

if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    # If a config file is given, register multiple tasks
    if opts.config:
        # Need to parse out multiple tasks

        tasks, c_delay = parse_config(opts.config)
        if c_delay:
            opts.delay = c_delay

    # Otherwise there is only one task to register
    else:
        tasks = [Task(opts)]

    for task in tasks:
        logging.debug(task)

    if opts.delay<0:
        # Single shot update
        one_shot()

    else:

        # Loop and monitor changes
        while True:
            continuous()
            time.sleep(opts.delay)