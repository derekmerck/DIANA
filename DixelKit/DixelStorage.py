import pickle
import os
import logging
import requests
from aenum import IntEnum


# Set this to something else to store cache files elsewhere
TMP_CACHE_DIR = "/tmp"


class CachePolicy(IntEnum):
    NONE = 0
    USE_CACHE = 1
    CLEAR_AND_USE_CACHE = 2


# TODO: Could just make this a subclass of DixelTools.Caching
class DixelStorage(object):
    """
    An abstract API representing a collection of Dixels on disk, in Orthanc,
    on a PACS, in Splunk, etc...

    Should implement CRUD (create, read, update, delete) interface:
    -     put(dixel)     -- create/insert/add item to inventory
    - d = get(dixel)     -- read/return a specific item from inventory by (predixel)
                            (same as update?) can populate meta.data['archive'] or ['file']
    -     delete(dixel)  -- remove a specific item from inventory
    -     copy(dixel, dest) -- copy a specific item from inventory to a destination storage
    - d = update(dixel)  -- update a (predixel) with data or meta from inventory -- same as get?

    Includes optional disk caching (pickling) for expensive-to-compute inventories

    Because dixels are hashable and dixel worklists are sets, it is straightforward to implement
    lazy updates by differencing inventories.
    """

    def __init__(self,
                 cache_pik=None,
                 cache_policy=CachePolicy.NONE):
        self.logger = logging.getLogger()
        self.cache = {}
        self.cache_policy = cache_policy
        if cache_pik:
            self.cache_pik = os.path.join(TMP_CACHE_DIR, cache_pik)
        if cache_pik and cache_policy == CachePolicy.CLEAR_AND_USE_CACHE:
            if os.path.exists(self.cache_pik):
                os.remove(self.cache_pik)

    # Abstract methods -- implement these to extend
    def put(self, dixel):
        raise NotImplementedError

    def get(self, dixel, **kwargs):
        raise NotImplementedError

    def delete(self, dixel):
        raise NotImplementedError

    def copy(self, dixel, destination):
        raise NotImplementedError

    def update(self, dixel, **kwargs):
        raise NotImplementedError

    # Anything that you want to cache can be accessed with a "var" property
    # and an "initialize_var()" method that _returns_ an appropriate value
    @property
    def inventory(self):
        return self.check_cache('inventory')

    def initialize_inventory(self):
        # Return the completed inventory
        raise NotImplementedError

    # Generic functions
    def check_cache(self, item):

        # Uninitialized cache
        if not self.cache:
            self.load_cache()

        # Uninitialized item
        if not self.cache.get(item):
            self.cache[item] = self.initialize_cache(item)
            self.save_cache()

        return self.cache.get(item)

    def initialize_cache(self, item):
        method_name = 'initialize_{0}'.format(item)
        # self.logger.debug('Calling method {}'.format(method_name))
        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise NotImplementedError(
                "Class `{}` does not implement `{}`".format(self.__class__.__name__, method_name))
        return method()

    # File inventories in particular can be expensive to compute
    def save_cache(self):
        if self.cache_policy > 0 and self.cache_pik:
            with open(self.cache_pik, 'wb') as f:
                pickle.dump(self.cache, f)

    def load_cache(self):
        if self.cache_policy != CachePolicy.NONE and \
                self.cache_pik and \
                os.path.exists(self.cache_pik):
            with open(self.cache_pik, 'rb') as f:
                self.cache = pickle.load(f)

    def view_inventory(self):
        logging.info(sorted(self.inventory))

    def delete_inventory(self):
        worklist = self.inventory
        self.delete_worklist(worklist)
        self.cache['inventory'] = None

    def copy_inventory(self, dest, lazy=False):
        worklist = self.inventory
        return self.copy_worklist(dest, worklist, lazy)

    def get_worklist(self, worklist, lazy=False, **kwargs):

        for dixel in worklist:
            if lazy:
                if dixel in self.inventory:
                    return

            self.get(dixel, **kwargs)

    def delete_worklist(self, worklist):
        for dixel in worklist:
            self.delete(dixel)

    def copy_worklist(self, dest, worklist, lazy=False):

        if lazy:
            # logging.debug("All src:  {0} dixels\n   {1}".format(len(worklist), sorted(worklist)))
            # logging.debug("All dest: {0} dixels\n   {1}".format(
            #     len(dest.inventory), sorted(dest.inventory)))
            worklist = worklist - dest.inventory
            # logging.debug("Lazy:     {0} dixels\n   {1}".format(len(worklist), sorted(worklist)))

        count = 0
        for dixel in worklist:
            count = count + 1
            self.copy(dixel, dest)

        return count

    def update_worklist(self, worklist, **kwargs):
        res = set()
        for dixel in worklist:
            u = self.update(dixel, **kwargs)
            if u:
                res.add(u)
        return res


class HTTPDixelStorage(DixelStorage):

    def __init__(self, **kwargs):
        self.session = requests.session()
        self.url = None
        super(HTTPDixelStorage, self).__init__(kwargs)

    def do_get(self, url, headers=None, params=None):
        r = requests.Response()
        r.status_code = 499
        try:
            r = self.session.get(url, headers=headers, params=params)
            r = requests.get(url, headers=headers, params=params, auth=self.session.auth)
        except requests.exceptions.ConnectionError as e:
            logging.error(e.message)
            logging.error(e.request.url)
            logging.error(e.request.headers)
            logging.error(e.request.body)
            logging.error(e.response)
            if e.response:
                r = e.response
        return r

    def do_post(self, url, data=None, json=None, headers=None):
        r = requests.Response()
        r.status_code = 499
        try:
            # r = self.session.post(url, data=data, json=json, headers=headers)
            r = requests.post(url, data=data, json=json, headers=headers, auth=self.session.auth)
        except requests.exceptions.ConnectionError as e:
            logging.error(e.message)
            logging.error(e.request.url)
            logging.error(e.request.headers)
            logging.error(e.request.body)
            logging.error(e.response)
            if e.response:
                r = e.response
        return r

    def do_delete(self, url, headers=None):
        r = requests.Response()
        r.status_code = 499
        try:
            r = self.session.delete(url, headers=headers)
        except requests.exceptions.ConnectionError as e:
            logging.error(e.message)
            logging.error(e.request.url)
            logging.error(e.request.headers)
            logging.error(e.request.body)
            logging.error(e.response)
            if e.response:
                r = e.response
        return r