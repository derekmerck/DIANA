
# Splunk exports deformed JSON.  This script goes thorugh each line, grabs the _raw field,
# converts it back into Python data structures and redumps whatever it can.

import json
import pprint

# Extract and reformat raw JSON from Splunk dump
with file("/Users/Derek/Downloads/xa_dose_reports.json") as fp:
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

with file("/Users/Derek/Desktop/xa_dose_reports_fixed.json", 'w') as fp:
    json.dump(t, fp)