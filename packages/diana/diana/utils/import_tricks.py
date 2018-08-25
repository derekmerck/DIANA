import importlib.util
import os.path
from glob import glob
from pprint import pprint


def import_by_fn(fn):
    m_name = os.path.splitext( os.path.basename(fn) )[0]
    spec = importlib.util.spec_from_file_location(m_name, fn)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def import_by_glob(expr):
    fns = glob(expr)
    res={}
    for fn in fns:
        m = import_by_fn(fn)
        res[m.__name__] = m
    return res


def pluck_by_attr(objs, attr_name):

    res = []
    for o in objs.values():
        a = getattr(o, attr_name)
        res.append(a)
    return res


def flatten_array_of_dicts(dicts):
     res = {}
     for d in dicts:
         res.update(d)
     return res


def merge_dicts_by_glob(expr, attr_name):
    modules = import_by_glob(expr)
    all_routing = pluck_by_attr(modules, attr_name)
    res = flatten_array_of_dicts(all_routing)
    return res


if __name__ == "__main__":

    expr = "/Users/derek/dev/DIANA/tests/test_routing/*.py"
    attr_name = 'routing'
    pprint(merge_dicts_by_glob(expr, attr_name))