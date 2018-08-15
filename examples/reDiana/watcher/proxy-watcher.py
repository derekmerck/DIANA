"""
Remotely-configurable proxy-watcher
"""

import os, logging
from datetime import timedelta, datetime
from diana.apis import Splunk, Dixel
from diana.daemon import DianaWatcher, ObservableOrthanc, ObservableOrthancProxy, DianaEventType
from diana.utils.dicom import DicomLevel, dicom_strftime2, DicomUIDMint, SuffixStyle
from diana.utils import Event


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

# DEFFAULT DEV CONFIGURATION -- SET THROUGH RESIN IN PROD
# IN MANY CASES DEFAULT IS FINE IF USING STD CONFIG, MARKED SHOULD BE DISTINCT

default_host = "172.17.0.1"

# app level
orthanc_host             = os.environ.get('ORTHANC_HOST', default_host )
orthanc_port             = os.environ.get('ORTHANC_PORT', "8042")
orthanc_user             = os.environ.get('ORTHANC_USER', "orthanc")
orthanc_password         = os.environ.get('ORTHANC_PASSWORD', "passw0rd!")         # **

splunk_host              = os.environ.get('SPLUNK_HOST',  default_host)            # **

logging.debug(splunk_host)

splunk_hec_port          = os.environ.get('SPLUNK_HEC_PORT', "8088")

# service level (useful to orthancs, not watchers)
orthanc_query_domain     = os.environ.get('ORTHANC_DOMAIN', "modality")

# service level (useful to watchers, not to orthancs)
splunk_watcher_index     = os.environ.get('SPLUNK_WATCHER_INDEX', "imaging")        # **
splunk_watcher_tok       = os.environ.get('SPLUNK_WATCHER_TOK', "INVALID_TOKEN")    # **

# device level (specific to each device/site watcher)
orthanc_query_study_desc = os.environ.get('ORTHANC_STUDY_DESC', "*")                # **
orthanc_discovery_period_len = os.environ.get('ORTHANC_DISCOVERY_PERIOD', 300)
orthanc_polling_interval = os.environ.get('ORTHANC_POLLING_INTERVAL', 120)

# device level (specific to each device/orthanc)
# orthanc_modality_host    = os.environ.get('ORTHANC_MODALITY_HOST', default_host )  # **
# orthanc_modality_port    = os.environ.get('ORTHANC_MODALITY_PORT', "4242" )        # **
# orthanc_modality_aet     = os.environ.get('ORTHANC_MODALITY_AET',  "ORTHANC" )     # **
#
# orthanc_modality         = {'modality': [orthanc_modality_host,
#                                          orthanc_modality_port,
#                                          orthanc_modality_aet]}


# Need additional device-level data for orthanc modalities self config

changes_query = {
    'ModalitiesInStudy': '',
    'StudyDescription': '*'  #orthanc_query_study_desc
}

orthanc_proxy = ObservableOrthancProxy(
    host = orthanc_host,
    port = orthanc_port,
    user = orthanc_user,
    password = orthanc_password,
    changes_query = changes_query,
    default_domain = orthanc_query_domain,
    default_query_level = DicomLevel.STUDIES,
    discovery_period=-300,     # Look back 5 mins
    polling_interval=90        # check every 90 secs
)

splunk = Splunk(
    host=splunk_host,
    hec_port=splunk_hec_port,
    hec_tokens={"watcher": splunk_watcher_tok},
    default_index=splunk_watcher_index,
    default_token='watcher'
)

watcher = DianaWatcher()
from functools import partial

# Do not do a deep index (no pull), just anonymize results by line and put in index
watcher.routes = {
    (orthanc_proxy, DianaEventType.NEW_MATCH):
        partial(watcher.index_by_proxy, dest=splunk,
                                        token='watcher',
                                        retrieve=False,
                                        anonymize=True)
}

watcher.fire(Event(DianaEventType.NEW_MATCH,
                   Dixel(meta={
                        "AccessionNumber": "123",
                        "PatientID": "abc",
                        "StudyDate": dicom_strftime2( datetime.now() )[0],
                        'StudyTime': dicom_strftime2( datetime.now() )[1],
                        'StudyDescription': "My study",
                        'StudyInstanceUID': DicomUIDMint().uid(suffix_style=SuffixStyle.RANDOM)},
                         ),
                   event_source=orthanc_proxy))

watcher.run()