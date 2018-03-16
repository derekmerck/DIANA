"""
Dictionary caching class

Variables beginning with a leading underscore are reserved for class attributes, i.e., "_key"
"""

import redis
import csv
import pickle
import logging
import os
from pprint import pformat


class DictCache(object):
    """
    Persistent dict caching
    """
    def delete(self, key, *args, **kwargs):
        raise NotImplementedError

    def get(self, key, *args, **kwargs):
        raise NotImplementedError

    def put(self, key, data, *args, **kwargs):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError

    def values(self):
        raise NotImplementedError

    def kvs(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __nonzero__(self):
        """Exists, even if nothing in it"""
        return True


class FileDictCache(DictCache):

    def __init__(self, fp, load_fn, save_fn, autosave=True, clear=False):
        super(FileDictCache, self).__init__()
        self.fp = fp
        self.logger = logging.getLogger("{}<{}>".format(self.__class__.__name__, fp))
        self.cache = {}
        self.autosave = autosave
        self.save_fn = save_fn
        if clear:
            self.clear()
        if os.path.exists(self.fp):
            load_fn()
        else:
            self.logger.warn("No existing cache at {}".format(fp))

    def clear(self):
        if os.path.exists(self.fp):
            os.remove(self.fp)

    def delete(self, key, **kwargs):
        if key in self.cache.keys():
            del(self.cache[key])
        if self.autosave:
            self.save_fn()

    def get(self, key, **kwargs):
        if key in self.cache.keys():
            return self.cache[key]
        else:
            self.logger.warn('Nothing set for key {}'.format(key))

    def put(self, key, data, force=False, **kwargs):
        if key in self.cache.keys() and not force:
            self.logger.warn("key {} already exists, use 'force' to overwrite".format(key))
            return
        if len(data) == 0:
            self.delete(key)
            return
        self.cache[key] = data
        if self.autosave:
            self.save_fn()

    def keys(self):
        return self.cache.keys()

    def values(self):
        return self.cache.values()

    def __len__(self):
        return len(self.cache.keys())


class CSVCache(FileDictCache):

    def __init__(self, fp, key_field='_key', fieldnames=None, clear=False, autosave=True, remap_fn=None):
        self.fieldnames = fieldnames
        self.key_field = key_field
        self.remap_fn = remap_fn # CSV caches from Montage or Copath will have non-normalized dixels in them
        super(CSVCache, self).__init__(fp, self.load_csv, self.save_csv, clear=clear, autosave=autosave)

    def load_csv(self):

        self.logger.debug("Reading cache")
        with open(self.fp, 'rU') as f:
            reader = csv.DictReader(f)
            self.fieldnames = reader.fieldnames
            for item in reader:

                # Trim unset fields out
                data = {}
                for k, v in item.iteritems():
                    if v and k != '_key':
                        data[k] = v

                if self.remap_fn:
                    data = self.remap_fn(key=None, data=data)

                # After remapping
                key = data.get(self.key_field)
                self.cache[key] = data


    def save_csv(self, fieldnames=None, extras='ignore'):

        if len(self.cache) == 0:
            return

        # convert cache into list of dicts w keys
        items = []
        for key, v in self.cache.iteritems():
            item = dict(v)
            if not item.get(self.key_field):
                item[self.key_field] = key
            items.append(item)

        # Use explicit fieldnames if present
        if not fieldnames and self.fieldnames:
            # Otherwise use reader provided fieldnames
            fieldnames = self.fieldnames
        elif not fieldnames and not self.fieldnames:
            # Otherwise use all fieldnames (assuming no reader)
            fieldnames = set()
            for item in items:
                for key in item.keys():
                    fieldnames.add(key)
            fieldnames = sorted(list(fieldnames))

        with open(self.fp, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction=extras)
            writer.writeheader()
            writer.writerows(items)


class PickleCache(FileDictCache):

    def __init__(self, fp, clear=False, autosave=True):
        super(PickleCache, self).__init__(fp, self.load_pickle, self.save_pickle, clear=clear, autosave=autosave)

    def load_pickle(self):
        with open(self.fp, 'rb') as f:
            self.cache = pickle.load(f)

    def save_pickle(self):
        with open(self.fp, 'wb') as f:
            pickle.dump(self.cache, f)


class RedisCache(DictCache):

    def __init__(self, host='localhost', port=6379, password=None, db=0, clear=False):
        self.logger = logging.getLogger("{}<db:{}>".format(self.__class__.__name__, db))
        super(RedisCache, self).__init__()
        self.redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db)
        if clear:
            self.clear()

    def clear(self):
        self.redis.flushdb()

    def delete(self, key, **kwargs):
        self.redis.delete(key)

    def get(self, key, **kwargs):
        if self.redis.exists(key):
            return self.redis.hgetall(key)
        else:
            pass

    def put(self, key, data, force=False, **kwargs):
        if self.redis.exists(key) and not force:
            self.logger.warn("Key {} already exists, use 'force' to overwrite".format(key))
            return
        self.delete(key)
        if len(data) > 0:
            self.redis.hmset(key, data)

    def keys(self, pattern="*"):
        return self.redis.keys(pattern)

    def values(self):
        ret = []
        for k in self.keys():
            ret.append(self.get(k))

    @property
    def cache(self):
        ret = {}
        for k in self.keys():
            ret[k] = self.get(k)
        return ret

    def __len__(self):
        return len(self.keys())


class Persistent(object):

    def __init__(self, key, data=None, cache=None, init_fn=None, remap_fn=None, **kwargs):
        self.key = key
        self.data = data or {}
        self.cache = cache

        # Use data if provided
        if data:
            # logging.debug("Setting data")
            self.data = dict(data)

        # Otherwise, try to load key
        if not data and self.cache:
            # logging.debug("Calling loader fn")
            self.data = self.cache.get(self.key)

        # Otherwise, call the init_fn
        if not self.data and init_fn:
            self.data = init_fn(key=self.key, data=self.data)

        # Call the data remapper if there is one
        if remap_fn:
            # logging.debug("Calling remapper fn")
            self.data = remap_fn(key=self.key, data=self.data)

        self.persist()

    def persist(self, cache=None):
        # Accepts an alternate dcache to save to
        cache = cache or self.cache
        if not cache:
            return
        # logging.debug("Putting {} in cache {}".format(self.key, cache))
        cache.put(self.key, self.data, force=True)


def test_persistence():

    R = RedisCache()
    Q = RedisCache()

    data = {"flag": "white",
            "dog":  "lab",
            "bird": "parrot"}

    p = Persistent("12345", data, R)
    q = Persistent("12345", cache=Q)

    logging.debug(p.data)
    logging.debug(q.data)

    assert(p.data == q.data)


def check_output(test_cache):
    test_cache.delete('foo')
    data = {'bird':   'flamingo',
            'mammal': "hipp",
            'fish':   "shark"}
    test_cache.put('foo', data)
    foo = test_cache.get('foo')
    assert(foo==data)

    test_cache.put('foo', {})
    foo = test_cache.get('foo')
    assert(foo==data)

    test_cache.put('foo', {}, force=True)
    foo = test_cache.get('foo')
    assert(foo==None)

    test_cache.put('foo', {'dog': 'lab'}, force=True)
    foo = test_cache.get('foo')
    assert(foo=={'dog': 'lab'})

    test_cache.put('bar', {'cat': 'lion', 'dog': 'poodle'}, force=True)
    bar = test_cache.get('bar')
    assert(bar=={'cat': 'lion',
                 'dog': 'poodle'})


def test_redis():

    R = RedisCache()
    check_output(R)


def test_csv():

    fp = "/tmp/test.csv"
    C = CSVCache(fp, clear=True)
    check_output(C)

    D = CSVCache(fp)

    foo = D.get('foo')
    logging.debug(foo)
    assert(foo=={'dog': 'lab'})

    bar = D.get('bar')
    assert(bar=={'cat': 'lion',
                 'dog': 'poodle'})


def test_pickle():

    fp = "/tmp/test.pkl"
    P = PickleCache(fp, clear=True)
    check_output(P)

    Q = PickleCache(fp)

    foo = Q.get('foo')
    assert(foo=={'dog': 'lab'})

    bar = Q.get('bar')
    assert(bar=={'cat': 'lion',
                 'dog': 'poodle'})


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    test_redis()
    test_csv()
    test_pickle()

    test_persistence()

