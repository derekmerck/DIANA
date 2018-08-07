"""
Subclassed Watcher implementing a number of common Diana workflows
"""

import logging, zipfile, os, time
from enum import Enum, auto
import attr
from diana.apis import Orthanc, DicomFile, Splunk, Dixel
from diana.utils import Watcher, ObservableMixin, DatetimeInterval2 as DatetimeInterval
from diana.utils.dicom.dicom_strings import dicom_strftime2


class DianaEventType(Enum):

    INSTANCE_ADDED = auto()  # dcm file or orthanc instance
    SERIES_ADDED = auto()    # orthanc series
    STUDY_ADDED = auto()     # zip file or orthanc study

    NEW_MATCH = auto()       # Dose report or other queried item match

    ALERT = auto()           # mention item in warning log


@attr.s
class DianaWatcher(Watcher):

    def move(self, event, dest, remove=False):
        item = event.data
        source = event.source

        item = source.get(item, view="file")
        if remove:
            source.remove(item)
        return dest.put(item)

    def anonymize_and_move(self, event, dest, remove=False):
        item = event.data
        source = event.source

        item = source.anonymize(item, remove=remove)
        item = source.get(item, view="file")
        item = dest.put(item)
        source.remove(item)  # Never need to keep anon
        return item

    def index(self, event, dest):
        item = event.data
        source = event.source

        item = source.get(item, view="tags")
        return dest.put(item)

    def index_by_proxy(self, event, dest):
        item = event.data
        source = event.source

        item = source.find(item, retrieve=True)
        item = source.get(item, view="tags")
        source.remove(item)
        return dest.put(item)

    def unpack_and_put(self, event, dest, remove=False):
        item_fp = event.data

        self.logger.debug("Unzipping {}".format(item_fp))
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


@attr.s(hash=False)
class ObservableOrthanc(ObservableMixin, Orthanc):

    def changes(self):
        event_queue = []
        event_queue.append( (DianaEventType.STUDY_ADDED, 100) )
        event_queue.append( (DianaEventType.STUDY_ADDED, "barbar") )
        event_queue.append( (DianaEventType.INSTANCE_ADDED, 100) )
        event_queue.append( (DianaEventType.INSTANCE_ADDED, "barbar") )
        return event_queue

@attr.s(hash=False)
class ObservableOrthancProxy(ObservableMixin, Orthanc):
    changes_query = attr.ib( factory=dict )
    domain = attr.ib( default='' )

    def changes(self):

        def set_study_dt(q):
            interval = DatetimeInterval(*q['StudyDateTimeInterval'])

            d, t0 = dicom_strftime2(interval.earliest)
            _, t1 = dicom_strftime2(interval.latest)

            q['StudyDate'] = d
            q['StudyTime'] = "{}-{}".format(t0, t1)
            del (q['StudyDateTimeInterval'])

            return q

        q = set_study_dt(self.changes_query)


@attr.s(hash=False)
class ObservableDicomFile(ObservableMixin, DicomFile):

    def changes(self):
        pass

    def poll_events(self):

        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileSystemEvent

        @attr.s(hash=False)
        class WatchdogEventReceiver(FileSystemEventHandler):
            source = attr.ib()

            def on_any_event(self, wd_event: FileSystemEvent):

                if wd_event.is_directory:
                    return

                event_data = wd_event.src_path
                event_type = None

                if wd_event.event_type == "added" and event_data.endswith(".dcm"):
                    event_type = DianaEventType.INSTANCE_ADDED
                elif wd_event.event_type == "added" and event_data.endswith(".zip"):
                    event_type = DianaEventType.STUDY_ADDED

                if event_type:
                    event = self.source.gen_event(event_type=event_type, event_data=event_data)
                    # self.logger.debug('Adding to event queue')
                    self.source.put(event)

        observer = Observer()
        receiver = WatchdogEventReceiver(source=self)

        observer.schedule(receiver, self.location, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(2)
        except:
            observer.stop()
            self.logger.warning("Stopped polling file system for changes")
        observer.join()


if __name__ == "__main__":

    from datetime import datetime, timedelta
    from diana.utils import Event
    from diana.utils.dicom import DicomLevel

    logging.basicConfig(level=logging.DEBUG)

    dcm_file =        ObservableDicomFile( location="/Users/derek/Desktop/dcm" )
    orthanc_queue =   ObservableOrthanc()
    orthanc_archive = ObservableOrthanc( port=8043 )

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
        (orthanc_archive, DianaEventType.STUDY_ADDED):  partial(watcher.index,
                                                                dest=splunk),
        (orthanc_proxy, DianaEventType.NEW_MATCH):      partial(watcher.index_by_proxy,
                                                                dest=splunk),
        (orthanc_proxy, DianaEventType.ALERT):          logging.warning
    }

    watcher.fire( Event( DianaEventType.ALERT, "foo", event_source=orthanc_proxy ))

    watcher.run()
