import logging
from typing import Mapping

from datetime import datetime
import attr
from .dixel import Dixel
from ..utils import Pattern, DatetimeInterval, gateway
from ..utils.dicom import DicomLevel
# splunk-sdk is 2.7 only, so diana.utils.gateway provides a minimal query/put replacement

# Suppress insecure warning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@attr.s
class Splunk(Pattern):
    host = attr.ib( default="localhost" )
    port = attr.ib( default="8000" )
    user = attr.ib( default="splunk" )
    protocol = attr.ib( default="https" )
    password = attr.ib( default="admin" )
    hec_protocol = attr.ib( default="http" )
    hec_port = attr.ib( default="8088" )
    gateway = attr.ib( init=False )

    hec_tokens = attr.ib( factory=dict )  # Mapping of domain name -> token

    default_token = attr.ib( default=None )
    default_index = attr.ib( default='main' )

    @gateway.default
    def connect(self):

        # Create a Service instance and log in
        return gateway.Splunk(
            host=self.host,
            port=self.port,
            protocol = self.protocol,
            hec_port=self.hec_port,
            hec_protocol=self.hec_protocol,
            user=self.user,
            password=self.password
        )

    def add_hec_token(self, name: str, token: str):
        self.hec_tokens[name] = token

    def find_items(self,
            query: Mapping,
            time_interval: DatetimeInterval=None):

        results = self.gateway.find_events(query, time_interval)

        # logging.debug("Splunk query: {}".format(query))
        # logging.debug("Splunk results: {}".format(results))

        if results:
            worklist = set()
            for d in results:
                worklist.add( Dixel(meta=d, level=DicomLevel.of( d['level'] ) ) )

            # logging.debug(worklist)

            return worklist


    def put(self, item: Dixel, host: str, token: str, index: str=None ):

        if item.meta.get('InstanceCreationDateTime'):
            timestamp = item.meta.get('InstanceCreationDateTime')
        elif item.meta.get('StudyDateTime'):
            timestamp = item.meta.get('StudyDateTime')
        else:
            logging.warning("Failed to get inline 'DateTime', using now()")
            timestamp = datetime.now()

        event = item.meta

        event['level'] = str(item.level)
        event['oid'] = item.oid()

        if not token:
            token=self.default_token
        _token = self.hec_tokens.get(token)

        if not index:
            index=self.default_index

        # self.logger.debug(timestamp)
        # self.logger.debug(event)
        # self.logger.debug(index)
        # self.logger.debug(_token)

        _host = "{}@{}".format(host, self.hostname)

        # at $time $event was reported by $host for $index with credentials $auth
        self.gateway.put_event( timestamp=timestamp, event=event, host=_host, index=index, token=_token )

        # Real auth description
        # headers = {'Authorization': 'Splunk {0}'.format(self.hec_tok[hec])}
