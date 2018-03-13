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
    def delete(self, id, *args, **kwargs):
        raise NotImplementedError

    def get(self, id, *args, **kwargs):
        raise NotImplementedError

    def put(self, id, data, *args, **kwargs):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class FileDictCache(DictCache):

    def __init__(self, fp, load_fn, save_fn, clear=False):
        self.fp = fp
        self.cache = {}
        self.save_fn = save_fn
        if clear:
            self.clear()
        if os.path.exists(self.fp):
            load_fn()

    def clear(self):
        if os.path.exists(self.fp):
            os.remove(self.fp)

    def delete(self, id, **kwargs):
        if id in self.cache.keys():
            del(self.cache[id])
        self.save_fn()

    def get(self, id, **kwargs):
        if id in self.cache.keys():
            return self.cache[id]
        else:
            self.logger.warn('Nothing set for id {}'.format(id))

    def put(self, id, data, force=False,**kwargs):
        if id in self.cache.keys() and not force:
            self.logger.warn("Id {} already exists, use 'force' to overwrite".format(id))
            return
        if len(data) == 0:
            self.delete(id)
            return
        self.cache[id] = data
        self.save_fn()


class CSVCache(FileDictCache):

    def __init__(self, fp, id_field='_id', clear=False, fieldnames=None):
        self.fieldnames = fieldnames
        self.id_field = id_field
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Reading cache")
        super(CSVCache, self).__init__(fp, self.load_csv, self.save_csv, clear)

    def load_csv(self):

        # self.logger.debug("Loading {}".format(self.fp))

        with open(self.fp, 'rU') as f:
            reader = csv.DictReader(f)
            self.fieldnames = reader.fieldnames
            for item in reader:
                key = item.get(self.id_field)

                # Trim unset fields out
                data = {}
                for k, v in item.iteritems():
                    if v and k !=  "_id":
                        data[k] = v

                self.cache[key] = data


    def save_csv(self, fieldnames=None, extras='ignore'):

        if len(self.cache) == 0:
            return

        # convert cache into list of dicts w id
        items = []
        for key, v in self.cache.iteritems():
            item = dict(v)
            item[self.id_field] = key
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

    def __init__(self, fp, clear=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        super(PickleCache, self).__init__(fp, self.load_pickle, self.save_pickle, clear)

    def load_pickle(self):
        with open(self.fp, 'rb') as f:
            self.cache = pickle.load(f)

    def save_pickle(self):
        with open(self.fp, 'wb') as f:
            pickle.dump(self.cache, f)


class RedisCache(DictCache):

    def __init__(self, host='localhost', port=6379, password=None, db=0, clear=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db)
        if clear:
            self.redis.flushdb()

    def delete(self, id, **kwargs):
        self.redis.delete(id)

    def get(self, id, **kwargs):
        if self.redis.exists(id):
            return self.redis.hgetall(id)
        else:
            self.logger.warn('Nothing set for id {}'.format(id))

    def put(self, id, data, force=False, **kwargs):
        if self.redis.exists(id) and not force:
            self.logger.warn("Id {} already exists, use 'force' to overwrite".format(id))
            return
        self.delete(id)
        if len(data) > 0:
            self.redis.hmset(id, data)

class Persistent(object):

    def __init__(self, key, data=None, cache=None, init_fn=None, **kwargs):
        self.key = key
        self.data = data or {}
        self.cache = cache

        # Use data if provided
        if data:
            self.data = dict(data)
            self.persist()

        # Otherwise, try to load key
        if not data and self.cache:
            self.data = self.cache.get(self.key)

        # Otherwise, call the init_fn
        if not self.data:
            self.data = init_fn(self.key)
            self.persist()

    def persist(self, cache=None):
        # Accepts an alternate dcache to save to
        cache = cache or self.cache
        if not cache:
            return
        cache.put(self.key, self.data, force=True)


def test_persistence():

    R = RedisCache()
    Q = RedisCache()

    data = {"flag": "white",
            "dog":  "lab",
            "bird": "parrot"}

    p = Persistent("12345", data, R)
    q = Persistent("12345", dcache=Q)

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

    test_persistence()

    # test_redis()
    # test_csv()
    # test_pickle()