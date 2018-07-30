# Heavily modified from Orthanc/scripts/Replicate.py

import base64
import httplib2
import json
import re
import sys
import logging
import argparse

import requests
from posixpath import join as urljoin
from urlparse import urlsplit


class REST(requests.Session):

    def __init__(self, address):

        super(REST, self).__init__()

        self.address = address
        p = urlsplit(self.address)
        self.scheme = p.scheme
        self.hostname = p.hostname
        self.port = p.port
        self.path = p.path
        self.auth = (p.username, p.password)

        self.logger = logging.getLogger("{0}:{1} API".format(self.hostname, self.port))
        self.logger.info('Created session wrapper for %s' % address)

    def get_url(self, *loc):
        return urljoin("{0}://{1}:{2}".format(self.scheme, self.hostname, self.port), self.path, *loc)

    def do_return(self, r):
        # Return dict if possible, but content otherwise (for image data)
        if r.status_code is not 200:
            self.logger.warn('REST interface returned error %s', r.status_code)
            return r.content

        if r.headers.get('content-type') == 'application/json':
            try:
                ret = r.json()
            except ValueError:
                self.logger.warn('REST interface returned malformed json')
                ret = r.content
        else:
            ret = r.content
        return ret

    def do_get(self, loc):
        self.logger.debug(self.get_url(loc))
        r = self.get(self.get_url(loc), headers=self.headers)
        return self.do_return(r)

    def do_post(self, loc, data, headers=None):
        if type(data) is dict:
            headers={'content-type': 'application/json'}
            data = json.dumps(data)
        r = self.post(self.get_url(loc), data=data, headers=headers)
        return self.do_return(r)



URL_REGEX = re.compile('(http|https)://((.+?):(.+?)@|)(.*)')

def CreateHeaders(parsedUrl):
    headers = {}
    username = parsedUrl.group(3)
    password = parsedUrl.group(4)

    if username != None and password != None:
        # This is a custom reimplementation of the
        # "Http.add_credentials()" method for Basic HTTP Access
        # Authentication (for some weird reason, this method does not
        # always work)
        # http://en.wikipedia.org/wiki/Basic_access_authentication
        headers['authorization'] = 'Basic ' + base64.b64encode(username + ':' + password)

    return headers


def GetBaseUrl(parsedUrl):
    return '%s://%s' % (parsedUrl.group(1), parsedUrl.group(5))


def DoGetString(url):
    global URL_REGEX
    parsedUrl = URL_REGEX.match(url)
    headers = CreateHeaders(parsedUrl)

    h = httplib2.Http()
    resp, content = h.request(GetBaseUrl(parsedUrl), 'GET', headers=headers)

    if resp.status == 200:
        return content
    else:
        raise Exception('Unable to contact Orthanc at: ' + url)


def DoPostDicom(url, body):
    global URL_REGEX
    parsedUrl = URL_REGEX.match(url)
    headers = CreateHeaders(parsedUrl)
    headers['content-type'] = 'application/dicom'

    h = httplib2.Http()
    resp, content = h.request(GetBaseUrl(parsedUrl), 'POST',
                              body=body,
                              headers=headers)

    if resp.status != 200:
        raise Exception('Unable to contact Orthanc at: ' + url)


def _DecodeJson(s):
    if (sys.version_info >= (3, 0)):
        return json.loads(s.decode())
    else:
        return json.loads(s)


def DoGetJson(url):
    return _DecodeJson(DoGetString(url))


def CopyTags(src, index):

    # This is required to decode structured report data (dose) from Orthanc
    def ParseStructuredReport(tags):
        parsed_tags = tags
        return parsed_tags

    def SendTagsToSplunk(tags):
        pass

    pass


def copy_instances(src, dest, instances):

    for instance in instances:
        dicom = src.do_get('instances/{0}/file'.format(instance))
        headers = {'content-type': 'application/dicom'}
        dest.do_post('instances', data=dicom, headers=headers)


def copy_studies(src, dest, _studies):

    def copy_study(src, dest, study):
        logging.debug('Sending study %s...' % study)
        for instance in src.do_get('studies/{0}/instances'.format(study)):
            dicom = src.do_get('instances/{0}/file'.format(instance['ID']))
            headers = {'content-type': 'application/dicom'}
            dest.do_post('instances', data=dicom, headers=headers)

    dest_studies = dest.do_get('studies')
    # Ignore studies that already exist at target
    studies = set(_studies) - set(dest_studies)

    logging.debug(studies)
    logging.debug('Found {0} new studies out of {1}'.format(len(studies), len(_studies)))

    for study in studies:
        copy_study(src, dest, study)


def ConditionalCopyStudies(src, dest, index, filter):

    def FilterStudies(index, filter):
        pass

    studies = FilterStudies(index, filter)
    copy_studies(src, dest, studies)


def CopyInstances(args):
    src = REST(args.src)
    dest = REST(args.dest)
    src_instances = src.do_get('instances')
    dest_instances = dest.do_get('instances')
    instances = set(src_instances) - set(dest_instances)
    logging.debug('Found {0} new instances out of {1}'.format(len(instances), len(src_instances)))
    copy_instances(src, dest, instances)


def CopyStudies(args):

    src = REST(args.src)
    dest = REST(args.dest)
    studies = src.do_get('studies')
    logging.debug(studies)
    copy_studies(src, dest, studies)


def parse_args(args):

    # create the top-level parser
    parser = argparse.ArgumentParser(prog='DianaMonitor')
    subparsers = parser.add_subparsers()

    parser_a = subparsers.add_parser('copy_instances',
                                     help='Copy non-redundant images from one Orthanc to another')
    parser_a.add_argument('--src')
    parser_a.add_argument('--dest')
    parser_a.add_argument('--deidentify', action="store_true")
    parser_a.set_defaults(func=CopyInstances)

    parser_b = subparsers.add_parser('copy_tags',
                                     help='Copy non-redundant tags from one Orthanc instance to an index')
    parser_b.add_argument('--src')
    parser_b.add_argument('--index')
    parser_b.set_defaults(func=CopyTags)

    parser_c = subparsers.add_parser('conditional_copy_studies',
                                     help='Copy non-redundant images one Orthanc to another using an index filter')
    parser_c.add_argument('--src')
    parser_c.add_argument('--dest')
    parser_c.add_argument('--index')
    parser_c.add_argument('--filter')
    parser_c.add_argument('--deidentify', action="store_true")
    parser_c.set_defaults(func=ConditionalCopyStudies)

    return parser.parse_args(args)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    args = parse_args(['copy_instances',
                       '--src',  'http://orthanc:orthanc@localhost:8042',
                       '--dest', 'http://orthanc:orthanc@localhost:8043'])

    logging.debug(args)
    args.func(args)
