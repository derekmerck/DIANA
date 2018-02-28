"""fix_splunk_json.py
Merck, Winter 2018

Splunk exports deformed JSON.  This script goes thorugh each line, grabs the _raw field,
converts it back into Python data structures and redumps whatever it can.
"""

import json
import pprint
import argparse

def parse_args():

    p = argparse.ArgumentParser()
    p.add_argument('source')
    opts = p.parse_args()
    return opts

if __name__ == "__main__":

    opts = parse_args()

    # Extract and reformat raw JSON from Splunk dump
    with file(opts.source) as fp:
        l = fp.readline()
        t = []
        while l:
            s = json.loads(l)
            try:
                ss = json.loads(s["result"]["_raw"])
                # pprint.pprint(ss)
                t.append(ss)
            except:
                # Occassionally malformed raw?
                pass
            l = fp.readline()

    import os
    outfile = os.path.splitext(opts.source)[0]+"_fixed.json"

    with file(outfile, 'w') as fp:
        json.dump(t, fp)