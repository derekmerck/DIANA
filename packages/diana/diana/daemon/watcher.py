"""
Subclassed Watcher implementing common DIANA workflows
"""

import logging, zipfile, os, time
from enum import Enum
from datetime import timedelta
from hashlib import md5
from functools import partial
import attr
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from diana.apis import Orthanc, DicomFile, Splunk, Dixel
from diana.utils import Watcher, ObservableMixin, DatetimeInterval2 as DatetimeInterval
from diana.utils.dicom import dicom_strftime2, DicomFormatError
from diana.utils.dicom import DicomUIDMint, SuffixStyle, DicomLevel


class DianaEventType(Enum):

    INSTANCE_ADDED = "instance_added"  # dcm file or orthanc instance
    SERIES_ADDED = "series_added"      # orthanc series
    STUDY_ADDED = "study_added"        # zip file or orthanc study
    NEW_MATCH =  "new_match"           # Dose report or other queried item match
    ALERT = "alert"                    # mention item in warning log


@attr.s
class DianaWatcher(Watcher):

    @classmethod
    def move(cls, event, dest, remove=False):
        item = event.event_data
        source = event.event_source
        logging.debug("Moving {}".format(item))

        try:
            item = source.get(item, view="file")
            if remove:
                source.remove(item)
            return dest.put(item)
        except DicomFormatError as e:
            logging.error(e)

    # TODO: Annotate with "anonymized_from" meta for alerts
    @classmethod
    def anonymize_and_move(cls, event, dest, remove=False):
        oid = event.event_data
        source = event.event_source

        item = source.get(oid, level=DicomLevel.INSTANCES)  # Get tags
        item = source.anonymize(item, remove=remove)        # Returns dixel with file

        logging.debug("Anonymizing and moving {}".format(item))

        return dest.put(item)

    @classmethod
    def index_series(cls, event, dest,
                     token=None,
                     index=None):
        oid = event.event_data
        source = event.event_source
        item = source.get(oid, level=DicomLevel.SERIES, view="tags")

        logging.debug("Indexing {}".format(item))
        logging.debug("Dest: {}".format(dest))

        return dest.put(item, token=token, index=index, host=event.event_source.location)

    @classmethod
    def index_by_proxy(cls, event, dest,
                       anonymize=False,
                       retrieve=False,
                       token=None,
                       index=None):

        item = event.event_data  # This should be a Dixel if a proxied return
        source = event.event_source

        # self.logger.debug("Received event with {} from {}".format(item, source))

        if retrieve:
            item = source.find(item, retrieve=True)
            item = source.get(item, view="tags")
            source.remove(item)

        if anonymize:

            logging.debug(item)
            # TODO: Should jitter datetime if it is important
            item.meta['AccessionNumber'] = md5(item.meta['AccessionNumber'].encode('UTF8')).hexdigest()
            item.meta['PatientID']       = md5(item.meta['PatientID'].encode('UTF8')).hexdigest()
            item.meta['StudyInstanceUID']= DicomUIDMint().uid(suffix_style=SuffixStyle.RANDOM)

        return dest.put(item, token=token, index=index, host=event.event_source.location)

    @classmethod
    def unpack_and_put(cls, event, dest, remove=False):
        item_fp = event.event_data

        logging.debug("Unzipping {}".format(item_fp))

        try:
            with zipfile.ZipFile(item_fp) as z:
                for member in z.infolist():
                    # if not os.path.isdir(filename):
                    # read the file
                    with z.open(member) as f:
                        logging.debug("Uploading {}".format(member))
                        item = Dixel(file=f)
                        dest.put(item)
            if remove:
                os.remove(item_fp)
        except zipfile.BadZipFile as e:
            logging.error(e)



@attr.s(hash=False)
class ObservableOrthanc(ObservableMixin, Orthanc):
    current_change = attr.ib( init=False, default=0 )

    def changes(self):
        event_queue = []
        done = False

        while not done:
            r = self.gateway.changes(current=self.current_change)
            for change in r['Changes']:
                if change['ChangeType'] == 'NewInstance':
                    oid = change['ID']
                    event_queue.append( (DianaEventType.INSTANCE_ADDED, oid) )
                elif change['ChangeType'] == 'StableSeries':
                    oid = change['ID']
                    event_queue.append((DianaEventType.SERIES_ADDED, oid))
                elif change['ChangeType'] == 'StableStudy':
                    oid = change['ID']
                    event_queue.append((DianaEventType.STUDY_ADDED, oid))
                else:
                    pass
                    # self.logger.debug("Found unhandled change type: {}".format( change['ChangeType']))
            self.current_change = r['Last']
            done = r['Done']

        if event_queue:
            self.logger.debug("Found {} Orthanc changes for {}".format( len( event_queue ), self.location))
            return event_queue

            # TODO: Unclear if we need to clear changes, or when we need to do this
            # source.clear("changes")
            # source.clear("exports")

from collections import deque

@attr.s(hash=False)
class ObservableOrthancProxy(ObservableMixin, Orthanc):
    query_dict = attr.ib( factory=dict )
    query_domain = attr.ib( default=None )
    query_level = attr.ib( default=DicomLevel.STUDIES )
    discovery_queue_len = attr.ib( default=200 )
    query_discovery_period = attr.ib( default=300, convert=int )

    # Keep last n accession numbers in memory
    discovery_queue = attr.ib(init=False)
    dt_interval = attr.ib(init=False, type=DatetimeInterval)

    @discovery_queue.default
    def create_discovery_queue(self):
        return deque(maxlen=self.discovery_queue_len)

    @dt_interval.default
    def set_dt_interval(self):
        return DatetimeInterval(timedelta(seconds=-self.query_discovery_period))

    def changes(self):
        q = {}

        if False:
            # Deep review loop
            next(self.dt_interval)
        else:
            # Always use current as latest in dt inverval
            self.dt_interval = self.set_dt_interval()

        d, t0 = dicom_strftime2(self.dt_interval.earliest)
        _, t1 = dicom_strftime2(self.dt_interval.latest)
        q['StudyDate'] = d
        q['StudyTime'] = "{}-{}".format(t0, t1)
        q.update( self.query_dict )

        response = self.find(q, level=DicomLevel.STUDIES, domain=self.query_domain)

        event_queue = []

        for item in response:
            if item.meta['AccessionNumber'] in self.discovery_queue:
                # logging.debug("Skipping old item")
                continue
            else:
                # logging.debug("Adding new item")
                # logging.debug(item)
                self.discovery_queue.append(item.meta['AccessionNumber'])
                event_queue.append( (DianaEventType.NEW_MATCH, item) )

        if event_queue:
            self.logger.debug("Found {} matches on {}".format( len( event_queue ), self.query_domain))
            return event_queue


@attr.s(hash=False)
class ObservableDicomFile(ObservableMixin, DicomFile):

    # This one is not a simple changes fix, uses alternate polling system
    def changes(self):
        pass

    def poll_events(self):

        @attr.s(hash=False)
        class WatchdogEventReceiver(FileSystemEventHandler):
            source = attr.ib()
            logger = attr.ib( factory=logging.getLogger )

            def on_any_event(self, wd_event: FileSystemEvent):

                self.logger.debug(wd_event)

                if wd_event.is_directory:
                    return

                event_data = wd_event.src_path
                event_type = None

                if wd_event.event_type == "created" and event_data.endswith(".zip"):
                    self.logger.debug("Found a zipped archive")
                    event_type = DianaEventType.STUDY_ADDED
                    sleep_time = 1.0

                elif wd_event.event_type == "created":
                    self.logger.debug("Found a possible dcm instance")
                    event_type = DianaEventType.INSTANCE_ADDED
                    sleep_time = 0.2

                if event_type:

                    # Need to poll for a while until it's finished
                    size = os.stat(event_data).st_size
                    prev_size = size - 1
                    while size > prev_size:
                        time.sleep(sleep_time)  # No change in this long
                        prev_size = size
                        size = os.stat(event_data).st_size
                    self.logger.debug("Final file size: {}".format(size))

                    event = self.source.gen_event(event_type=event_type, event_data=event_data)
                    self.source.events.put(event)

                self.logger.debug('Rejecting non-creation event {}'.format(wd_event))

        observer = Observer()
        receiver = WatchdogEventReceiver(source=self)

        observer.schedule(receiver, self.location, recursive=True)
        observer.start()


# def test_anon_queue_routing(watcher:DianaWatcher):
#     logging.debug("Setting up anon queue route")
#
#     dcm_file =        ObservableDicomFile( location="/Users/derek/Desktop/dcm" )
#     orthanc_queue =   ObservableOrthanc( password="passw0rd!" )
#
#     logging.debug(orthanc_queue)
#     logging.debug( orthanc_queue.info() )
#
#     orthanc_archive = ObservableOrthanc( port=8043, password="passw0rd!")
#
#     find_dose_reports = {
#         'level': DicomLevel.SERIES,
#         'StudyDateTimeInterval': (timedelta(minutes=-15),),
#         'Modality': "SR",
#         'SeriesDescription': "*DOSE*"
#     }
#     orthanc_proxy =   ObservableOrthancProxy( port=8044, domain="gepacs", changes_query=find_dose_reports )
#
#     splunk = Splunk()
#
#     watcher.routes = {
#         (dcm_file,      DianaEventType.INSTANCE_ADDED): partial(watcher.move,
#                                                                 dest=orthanc_queue, remove=True),
#         (dcm_file,      DianaEventType.STUDY_ADDED):    partial(watcher.unpack_and_put,
#                                                                 dest=orthanc_queue, remove=True),
#         (orthanc_queue, DianaEventType.INSTANCE_ADDED): partial(watcher.anonymize_and_move,
#                                                                 dest=orthanc_archive, remove=True),
#         # (orthanc_archive, DianaEventType.STUDY_ADDED):  partial(watcher.index,
#         #                                                         dest=splunk),
#         # (orthanc_proxy, DianaEventType.NEW_MATCH):      partial(watcher.index_by_proxy,
#         #                                                         dest=splunk),
#         (orthanc_proxy, DianaEventType.ALERT):          logging.warning
#     }
#
#     # watcher.fire( Event( DianaEventType.ALERT, "foo", event_source=orthanc_proxy ))


def test_proxied_indexer_route():
    """
    Use with examples/mockPACS configuration

    # proxy must know about PACS modality and how it is named by PACS
    # pacs must know about proxy name/addr and have permissions
    """

    # These are just complex service definitions (set w --service -source -dest)
    orthanc = ObservableOrthancProxy(
                        host="trusty64",
                        port=8999,
                        password="passw0rd!",
                        domains={"mock": "WATCHER"},
                        query_domain="mock",
                        query_level=DicomLevel.STUDIES,
                        query_dict={'ModalitiesInStudy': "",
                                    'StudyDescription': ""},
                        query_discovery_period=300,  # Check last 5 mins
                        polling_interval=120)  # Every 2 mins

    splunk = Splunk(    host="trusty64",
                        default_index="remotes",
                        default_token="remotes_tok",
                        hec_tokens={"remotes_tok": "1b67778c-0b1d-4df9-8142-5c726e74b053"})

    return set_proxied_index_route(orthanc, splunk)


def set_upload_files_route(source, dest) -> dict:
    # Common routing option -- set with -r "upload_files"
    logging.debug("Setting up upload files route")


    # Cast to objects
    if type(source) == dict:
        source = ObservableDicomFile(**source)
    if type(dest) == dict:
        dest = Orthanc(**dest)

    routes = {
        (source,      DianaEventType.INSTANCE_ADDED): partial(DianaWatcher.move,
                                                                dest=dest, remove=True),
        (source,      DianaEventType.STUDY_ADDED):    partial(DianaWatcher.unpack_and_put,
                                                                dest=dest, remove=True)
    }
    return routes


def set_anon_and_forward_route(source, dest) -> dict:
    logging.debug("Setting up anon and forward route")

    # Cast to objects
    if type(source) == dict:
        source = ObservableOrthanc(**source)
    if type(dest) == dict:
        dest = Orthanc(**dest)

    routes = {
        (source,  DianaEventType.INSTANCE_ADDED): partial(DianaWatcher.anonymize_and_move,
                                                            dest=dest, remove=True)
    }

    return routes

def set_index_tags_route(source, dest) -> dict:
    logging.debug("Setting up index tags route")

    # Cast to objects
    if type(source) == dict:
        source = ObservableOrthanc(**source)
    if type(dest) == dict:
        dest = Splunk(**dest)

    routes = {
        (source, DianaEventType.SERIES_ADDED): partial(DianaWatcher.index_series,
                                                    dest=dest )
    }

    return routes


def set_proxied_index_route(source, dest) -> dict:
    logging.debug("Setting up proxied index route")

    # Cast to objects
    if type(source) == dict:
        source = ObservableOrthancProxy(**source)
    if type(dest) == dict:
        dest = Splunk(**dest)

    routes = {
        (source, DianaEventType.NEW_MATCH): partial(DianaWatcher.index_by_proxy,
                                                    dest=dest,
                                                    anonymize=True)
    }

    return routes


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

    # Create watcher
    watcher = DianaWatcher()

    # Set with --routing "proxied_indexer"
    routes = test_proxied_indexer_route()

    # Merge routes by whatever mechanism
    watcher.add_routes(routes)
    watcher.run()
