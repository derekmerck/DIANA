import os
import sys
print os.getcwd()

sys.path.append(os.getcwd())

import logging
import yaml
import datetime as dt
from hashlib import sha1, md5
from connect.Gateway import *

logging.basicConfig(level=logging.DEBUG)

with open('secrets.yaml') as f:
    credentials = yaml.load(f)

orthanc0 = OrthancGateway(address=credentials['orthanc0_address'])
orthanc1 = OrthancGateway(address=credentials['orthanc1_address'])
pacs_proxy = OrthancGateway(address=credentials['pacs_proxy_address'])
splunk = SplunkGateway(address=credentials['splunk_address'],
                       hec_address=credentials['hec_address'])

remote = 'gepacs'         # Remote modality name in orthanc0
remote1 = 'anon_archive'  # orthanc1's peer name in orthanc0


# Setup anonymization function
def anonymizer(d):
    r = {'Replace': {
            'PatientName': md5(d['PatientID']),
            'PatientID': md5(d['PatientID']),
            'AccessionNumber': md5(d['AccessionNumber']) },
         'Keep': ['StudyDescription', 'SeriesDescription', 'ContrastBolusAgent', 'StationName']
        }
    return r


# Read accession numbers
fn = "accession_numbers.txt"
with open(fn) as f:
    content = f.readlines()
content = [x.strip() for x in content]

accessions = content
logging.info(accessions)

for accession_number in accessions:

    # Retrieve from remote
    pacs_proxy.level = 'studies'
    q = pacs_proxy.QueryRemote(remote, query={'AccessionNumber': accession_number})
    logging.debug(pprint.pformat(q))

    a = pacs_proxy.session.do_get('queries/{0}/answers/0/content?simplify'.format(q['ID']))
    logging.debug(pprint.pformat(a))

    pid = a['PatientID']
    stuid = a['StudyInstanceUID']
    t = sha1(pid + '|' + stuid).hexdigest()
    id = u'-'.join([t[n:n + 8] for n in range(0,40,8)])

    r = pacs_proxy.session.do_post('queries/{0}/answers/0/retrieve'.format(q['ID']), 'DEATHSTAR')
    logging.debug(pprint.pformat(r))

    s = pacs_proxy.GetItem(id)
    logging.debug(pprint.pformat(s))

    # Anonymize it
    t = pacs_proxy.session.do_post('studies/{0}/anonymize'.format(id), anonymizer(s))
    logging.debug(pprint.pformat(t))

    id_anon = t['ID']
    pname_anon = md5(s['PatientID']).hexdigest()

    # Send it to the anonymized peer
    t = pacs_proxy.session.do_post('peers/{0}/store'.format(remote1), id_anon)

    # # Download it locally
    # data = pacs_proxy.session.do_get('studies/{0}/archive'.format(id_anon))
    # fn = '/Users/derek/Desktop/peco/{0}.zip'.format(pname_anon[0:8])
    #
    # f = open(fn, 'wb')
    # f.write(data)
    # f.close()

    # # Delete everything from source
    pacs_proxy.DeleteItem(id)
    pacs_proxy.DeleteItem(id_anon)

# splunk.index_names['series'] = 'air1'
# UpdateSeriesIndex(orthanc1,splunk)

