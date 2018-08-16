"""
Subclassed Watcher implementing a number of common Diana workflows
"""

import logging, zipfile, os, time
from enum import Enum, auto
from datetime import timedelta
from hashlib import md5
import attr
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from diana.apis import Orthanc, DicomFile, Splunk, Dixel
from diana.utils import Watcher, ObservableMixin, DatetimeInterval2 as DatetimeInterval
from diana.utils.dicom import dicom_strftime2, DicomFormatError
from diana.utils.dicom import DicomUIDMint, DicomLevel


class DianaEventType(Enum):

    INSTANCE_ADDED = auto()  # dcm file or orthanc instance
    SERIES_ADDED = auto()    # orthanc series
    STUDY_ADDED = auto()     # zip file or orthanc study
    NEW_MATCH = auto()       # Dose report or other queried item match
    ALERT = auto()           # mention item in warning log


@attr.s
class DianaWatcher(Watcher):

    def move(self, event, dest, remove=False):
        self.logger.debug("Moving item")
        item = event.event_data
        source = event.event_source

        try:
            item = source.get(item, view="file")
            if remove:
                source.remove(item)
            return dest.put(item)
        except DicomFormatError as e:
            self.logger.error(e)

    # TODO: Annotate with "anonymized_from" meta for alerts
    def anonymize_and_move(self, event, dest, remove=False):
        oid = event.event_data
        source = event.event_source

        item = source.get(oid, level=DicomLevel.INSTANCES)  # Get tags
        # if item.meta.get('AnonymizedFrom'):
        #     source.remove(item)
        item = source.anonymize(item, remove=remove)
        # item = source.get(item, view="file")
        item = dest.put(item)
        return item

    def index(self, event, dest):
        item = event.event_data
        source = event.event_source

        item = source.get(item, view="tags")
        return dest.put(item)

    def index_by_proxy(self, event, dest,
                       anonymize=False,
                       retrieve=False,
                       token=None,
                       index=None):

        item = event.event_data  # This should be a Dixel if a proxied return
        source = event.event_source

        if retrieve:
            item = source.find(item, retrieve=True)
            item = source.get(item, view="tags")
            source.remove(item)

        if anonymize:

            self.logger.debug(item)

            item.meta['AccessionNumber'] = md5(item.meta['AccessionNumber'].encode('UTF8')).hexdigest()
            item.meta['PatientID']       = md5(item.meta['PatientID'].encode('UTF8')).hexdigest()
            item.meta['StudyInstanceUID']= DicomUIDMint().random_suffix()

        return dest.put(item, token=token, index=index, host=event.event_source.location)

    def unpack_and_put(self, event, dest, remove=False):
        item_fp = event.event_data

        self.logger.debug("Unzipping {}".format(item_fp))

        try:
            with zipfile.ZipFile(item_fp) as z:
                for filename in z.namelist():
                    if not os.path.isdir(filename):
                        # read the file
                        with z.open(filename) as f:
                            self.logger.debug("Uploading {}".format(filename))
                            item = Dixel(file=f)
                            dest.send(item)
            if remove:
                os.remove(item_fp)
        except zipfile.BadZipFile as e:
            self.logger.error(e)



@attr.s(hash=False)
class ObservableOrthanc(ObservableMixin, Orthanc):
    current_change = attr.ib( init=False, default=0 )

    def changes(self):
        event_queue = []

        current = 0
        done = False

        while not done:
            r = self.gateway.changes(current=self.current_change)
            for change in r['Changes']:
                # We are only interested interested in the arrival of new instances
                if change['ChangeType'] == 'NewInstance':
                    oid = change['ID']
                    event_queue.append( (DianaEventType.INSTANCE_ADDED, oid) )
            self.current_change = r['Last']
            done = r['Done']

        if event_queue:
            self.logger.debug("Found {} Orthanc changes".format( len( event_queue )))
            return event_queue

            # TODO: Unclear if we need to do this, or where we need to do this
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
        return DatetimeInterval(timedelta(seconds=self.query_discovery_period))

    def changes(self):
        q = {}
        d, t0 = dicom_strftime2(self.dt_interval.earliest)
        _, t1 = dicom_strftime2(self.dt_interval.latest)
        next( self.dt_interval )
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
                elif wd_event.event_type == "created":
                    self.logger.debug("Found a possible dcm instance")
                    event_type = DianaEventType.INSTANCE_ADDED

                if event_type:
                    event = self.source.gen_event(event_type=event_type, event_data=event_data)
                    self.source.events.put(event)

                self.logger.debug('Rejecting non-creation event {}'.format(wd_event))

        observer = Observer()
        receiver = WatchdogEventReceiver(source=self)

        observer.schedule(receiver, self.location, recursive=True)
        observer.start()


if __name__ == "__main__":

    from datetime import datetime, timedelta
    from diana.utils import Event

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

    dcm_file =        ObservableDicomFile( location="/Users/derek/Desktop/dcm" )
    orthanc_queue =   ObservableOrthanc( password="passw0rd!" )

    logging.debug(orthanc_queue)
    logging.debug( orthanc_queue.info() )

    orthanc_archive = ObservableOrthanc( port=8043, password="passw0rd!")

    find_dose_reports = {
        'level': DicomLevel.SERIES,
        'StudyDateTimeInterval': (timedelta(minutes=-15),),
        'Modality': "SR",
        'SeriesDescription': "*DOSE*"
    }
    orthanc_proxy =   ObservableOrthancProxy( port=8044, domain="gepacs", changes_query=find_dose_reports )

    splunk = Splunk()

    watcher = DianaWatcher()
    from functools import partial
    watcher.routes = {
        (dcm_file,      DianaEventType.INSTANCE_ADDED): partial(watcher.move,
                                                                dest=orthanc_queue, remove=True),
        (dcm_file,      DianaEventType.STUDY_ADDED):    partial(watcher.unpack_and_put,
                                                                dest=orthanc_queue, remove=True),
        (orthanc_queue, DianaEventType.INSTANCE_ADDED): partial(watcher.anonymize_and_move,
                                                                dest=orthanc_archive, remove=True),
        # (orthanc_archive, DianaEventType.STUDY_ADDED):  partial(watcher.index,
        #                                                         dest=splunk),
        # (orthanc_proxy, DianaEventType.NEW_MATCH):      partial(watcher.index_by_proxy,
        #                                                         dest=splunk),
        (orthanc_proxy, DianaEventType.ALERT):          logging.warning
    }

    watcher.fire( Event( DianaEventType.ALERT, "foo", event_source=orthanc_proxy ))

    watcher.run()
