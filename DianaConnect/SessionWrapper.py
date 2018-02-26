import logging
import requests
import json
from posixpath import join as urljoin
from urlparse import urlsplit
from datetime import datetime
import collections
from hashlib import sha256

# from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter

class Session(requests.Session):

    def __init__(self, address):

        super(Session, self).__init__()

        self.address = address
        p = urlsplit(self.address)
        self.scheme = p.scheme
        self.hostname = p.hostname
        self.port = p.port
        self.path = p.path

        if p.username == "Splunk":
            self.headers = {'Authorization': 'Splunk {0}'.format(p.password)}
        else:
            self.auth = (p.username, p.password)

        self.logger = logging.getLogger("{0}:{1} API".format(self.hostname, self.port))
        self.logger.info('Created a session wrapper for %s' % address)

        self.mount('http://', HTTPAdapter(max_retries=5))

    def get_url(self, *loc):
        return urljoin("{0}://{1}:{2}".format(self.scheme, self.hostname, self.port), self.path, *loc)

    def do_return(self, r):

        # Return dict if possible, but content otherwise (for image data)
        if r.status_code is not 200 and r.status_code is not 201:
            self.logger.warn('Session returned error %s', r.status_code)
            return r

        if r.headers.get('content-type').startswith('application/json'):
            try:
                ret = r.json()
            except ValueError:
                self.logger.warn('Session returned malformed json')
                ret = r.content
        else:
            ret = r.content
        return ret

    def do_get(self, loc, params={}):
        # self.logger.debug(self.get_url(loc))
        r = self.get(self.get_url(loc), headers=self.headers, verify=False, params=params)
        return self.do_return(r)

    def do_delete(self, loc, params={}):
        r = self.delete(self.get_url(loc), headers=self.headers, verify=False, params=params)
        return self.do_return(r)

    def do_put(self, loc, data, headers={}):
        pass

    def do_post(self, loc, data, headers={}):

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                if hasattr(obj, 'hexdigest'):
                    return obj.hexdigest()
                return json.JSONEncoder.default(self, obj)

        if type(data) is dict or type(data) is collections.OrderedDict:
            headers.update({'content-type': 'application/json'})
            data = json.dumps(data, cls=DateTimeEncoder)
        elif isinstance(data, str):
            headers.update({'content-type': 'text/plain'})

        r = self.post(self.get_url(loc), data=data, headers=headers, verify=False)

        return self.do_return(r)
