import logging
import requests
import json
from posixpath import join as urljoin
from urlparse import urlparse
import pickle
import os
from bs4 import BeautifulSoup


def load_pickle(f, default=None):
    if os.path.exists(f):
        return pickle.load(open(f, "rb"))
    else:
        return default


def save_pickle(f, data):
    pickle.dump(data, open(f, "wb"))


class SessionWrapper(requests.Session):

    cookie_jars_pickle = 'tmp_session_cookies.p'
    cookie_jars = load_pickle(cookie_jars_pickle, {})

    # Cookie jar for sharing proxy credentials

    def __init__(self, **kwargs):
        super(SessionWrapper, self).__init__()

        self.address = kwargs.get('address')
        self.auth = (kwargs.get('user'), kwargs.get('pword'))

        if self.address:
            self.hostname = urlparse(self.address).hostname
            self.port = urlparse(self.address).port
        else:
            self.hostname = None
            self.port = None

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info('Created session wrapper for %s' % self.hostname)

    def format_url(self, *url):
        # Simple join, but can override in derived classes and still use 'do_' macros
        url = urljoin(self.address, *url)
        return url

    def do_return(self, r):
        # Return dict if possible, but content otherwise (for image data)
        # self.logger.info(r.headers.get('content-type'))
        if r.status_code is not 200:
            self.logger.warn('REST interface returned error %s', r.status_code)
            ret = r.content
            msg = ret
        elif r.headers.get('content-type') == 'application/json':
            try:
                ret = r.json()
                if len(ret) < 50:
                    msg = ret
                else:
                    msg = 'a long json declaration'
            except ValueError:
                ret = r.content
                msg = 'a bad json declaration'
        else:
            ret = r.content
            msg = 'Non-json data'
        self.logger.debug('Returning %s', msg)
        return ret

    def do_delete(self, *url, **kwargs):
        params = kwargs.get('params')
        headers = kwargs.get('headers')
        url = self.format_url(*url)
        self.logger.debug('Deleting url: %s' % url)
        r = self.delete(url, params=params, headers=headers)
        return self.do_return(r)

    def do_get(self, *url, **kwargs):
        params = kwargs.get('params')
        headers = kwargs.get('headers')
        url = self.format_url(*url)
        self.logger.debug('Getting url: %s' % url)
        r = self.get(url, params=params, headers=headers)
        return self.do_return(r)

    def do_put(self, *url, **kwargs):
        params = kwargs.get('params')
        headers = kwargs.get('headers')
        data = kwargs.get('data')
        if type(data) is dict:
            headers.update({'content-type': 'application/json'})
            data = json.dumps(data)
        url = self.format_url(*url)
        self.logger.debug('Putting url: %s' % url)
        r = self.put(url, params=params, headers=headers, data=data)
        return self.do_return(r)

    def do_post(self, *url, **kwargs):
        params = kwargs.get('params', {})
        headers = kwargs.get('headers', {})
        data = kwargs.get('data')
        if type(data) is dict:
            headers.update({'content-type': 'application/json'})
            data = json.dumps(data)
            self.logger.info(data)
        url = self.format_url(*url)
        self.logger.debug('Posting to url: %s w params: %s' % (url, params))
        r = self.post(url, params=params, headers=headers, data=data)
        return self.do_return(r)

    def disable_verification(self):
        requests.packages.urllib3.disable_warnings()
        self.verify = False


class JuniperSessionWrapper(SessionWrapper):
    # Init and url construction for Juniper vpn connections

    def __init__(self, **kwargs):
        super(JuniperSessionWrapper, self).__init__(**kwargs)

        self.j_address = kwargs.get('j_address')
        self.j_user = kwargs.get('j_user')
        self.j_pword = kwargs.get('j_pword')

        self.disable_verification()

        # Check to see if credentials are registered
        self.credentials_ok = False
        if self.cookie_jars.get(self.j_address):
            # Set cookies
            self.cookies.update(self.cookie_jars.get(self.j_address))

            # See if the credentials are still any good
            url = urljoin(self.j_address, 'dana/home/index.cgi')
            r = self.get(url)
            # If this fails, eventually it will redirect to /dana-na/auth/url_default/welcome.cgi?p=forced-off
            if 'welcome.cgi' in r.url:
                self.cookie_jars[self.j_address] = None
            else:
                self.credentials_ok = True

        if not self.credentials_ok:
            # Submit login credentials
            url = urljoin(self.j_address, 'dana-na/auth/url_default/login.cgi')
            data = {'tz_value': '-300', 'realm': 'Users', 'username': self.j_user, 'password': self.j_pword}
            r = self.post(url, data=data)

            # Get the DSIDFormDataStr and respond to the request to start a new session
            h = BeautifulSoup(r.content, 'html.parser')
            dsid_field = h.find(id='DSIDFormDataStr')
            self.logger.debug('DSID %s' % dsid_field)
            data = {dsid_field['name']: dsid_field['value'], 'btnContinue': 'Continue%20the%20session'}
            self.post(url, data=data)
            # Now you are logged in and session cookies are saved for future requests.

            # Stash the session cookies for other juniper sessions to the same proxy address
            self.cookie_jars[self.j_address] = self.cookies
            save_pickle(self.cookie_jars_pickle, self.cookie_jars)

    def format_url(self, *url):
        #   https://{proxy_hostname}/{path},DanaInfo={target_hostname},Port={port}+{query_params}
        #   https://remote.vpn.com/path,DanaInfo=hostname+?query
        #   https://remote.vpn.com/path,DanaInfo=hostname,Port=8042+?query

        path = urljoin(*url)
        # Empty strings are apparently considered 'falsy'
        if self.port:
            url = '{0}/{3}/,DanaInfo={1},Port={2}+'.format(self.j_address, self.hostname, self.port, path)
        else:
            url = '{0}/{3}/,DanaInfo={1}+'.format(self.j_address, self.hostname, self.port, path)
        return url


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    pass
