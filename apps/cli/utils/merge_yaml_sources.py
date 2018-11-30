import os, logging
from glob import glob
from pprint import pformat
import yaml
"""
Env var expansion and merge data from:
- input in yaml/json format
- input file or dir of files in yaml/json format
"""

def merge_yaml_sources(data=None, path=None):

    result = {}
    if data:
        data_exp = os.path.expandvars(data)
        result = yaml.safe_load(data_exp)

    if os.path.isfile(path):
        with open(path) as f:
            finput_exp = os.path.expandvars(f.read())
            result.update(yaml.safe_load(finput_exp))

    elif os.path.isdir(path):
        fps = glob(os.path.join(path, "*.yml"))
        for fp in fps:
            with open(fp) as f:
                finput_exp = os.path.expandvars(f.read())
                result.update(yaml.safe_load(finput_exp))

    logging.debug("Merged yaml maps")
    logging.debug("===================")
    logging.debug(pformat(result))

    return result