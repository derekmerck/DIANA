import os, logging, uuid, zipfile, time
from typing import Callable, Collection
import attr
from watchdog.observers import Observer as wdObserver
from watchdog.events import FileSystemEventHandler as wdHandler
from ..apis import DicomFile, Orthanc, Dixel, Redis
from ..utils import Event, Pattern, dtinterval
from ..utils.dicom import DicomLevel

# - Every five minutes
#
# - Run a PACS query
#
# - If there are responses
#
# - Collect each study
# - handle it (anonymize, classify, parse)
#
# - route it to destinations
#   - index
#   - other pacs
#   - anon -> research archive


# -> simplify <-

# watch directory
#   -> new file
#     -> unzip if zip
#     -> for item in folders
#        -> if dicom
#            -> anon if needed
#            -> send it to dest

# watch orthanc
#   -> new file
#     -> anonymize if needed
#     -> send it to dest
#     -> delete it

from enum import Enum, auto
from datetime import datetime
import attr

class DiscoveryType(Enum):
    DOSE_RECORD: auto()
    DIXEL_MATCH: auto()


@attr.s
class Discovery(object):
    discovery_type = attr.ib( type=Enum )
    discovery_time = attr.ib( type=datetime )
    discovery_source = attr.ib()
    discovery_id = attr.ib()

    item_time = attr.ib( type=datetime )
    item_id = attr.ib()



@attr.s
class Observer(object):
    source = attr.ib( type=Observable )
    handlers = attr.ib( factory=list )

    # Keep up in real time
    def watch(self, handlers: list, condition):
        while True:
            items = self.source.changes(condition)  # Basically "find recent"
            if items:
                for handler in handlers:
                    handler.handle_items(items)

    # scheduled or historical review
    def review(self, handlers: list, condition, timekeeper: dtinterval):
        for time_interval in timekeeper:
            items = self.source.find(condition, time_interval)
            if items:
                for handler in handlers:
                    handler.handle_items(items)

# queue = Orthanc()
# archive = Orthanc()
# splunk = Splunk
#
# observer = Observer(source)
# observer.add_handler( condition, Router(dest=archive) )
#
#


# - each time dtinterval
#   - check each source
#     -for each item
#       - run each handler for that source


@attr.s
class Observer(object):
    source = attr.ib( type=Observable )

    # Keep up in real time
    def watch(self, handlers: list, condition):
        while True:
            items = self.source.changes(condition)  # Basically "find recent"
            if items:
                for handler in handlers:
                    handler.handle_items(items)

    # scheduled or historical review
    def review(self, handlers: list, condition, timekeeper: dtinterval):
        for time_interval in timekeeper:
            items = self.source.find(condition, time_interval)
            if items:
                for handler in handlers:
                    handler.handle_items(items)



# Discovers individual items in real time
@attr.s
class Curator(object):

    observers = attr.ib( init=False, factory=dict )

    def add_observer(self, source):
        self.observers['source'] = {}

    def add_handler_for_observer(self):
        pass


    handlers = attr.ib( factory=list )
    observer = attr.ib( factory=Observer )

    timekeeper = attr.ib( default=None )  # start, stop, increment

    def watch(self):
        self.observer.watch(self.source, self)  # triggers porter callback handle_item

    def review(self, discovered:Pattern = None):
        self.observer.review(self.source, self, self.timekeeper, discovered)  # triggers porter callback handle_items

    def handle_item(self, item):
        for handler in self.handlers:
            item = handler(item)

    def handle_items(self, worklist: Collection):
        for item in worklist:
            self.handle_item(item)

    def register_retrieve_anon_and_send(self, dest):
        self.handlers.append( self.source.find, retrieve=True )
        self.handlers.append( self.source.anonymize, remove=True )
        self.handlers.append( self.source.send, dest=dest, remove=True )

    def register_anon_and_save(self, dest):
        self.handlers.append( self.source.get, view="file" )
        self.handlers.append( dest.put )
        self.handlers.append( dest.anonymize, remove=True )

    def register_index(self, discovered):
        self.handlers.append( self.source.get )
        self.handlers.append( discovered.put )





if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    source = DicomFile("/data/incoming/ftp")
    dest = Orthanc()
    observer = Observer()

    curator = Curator( source=source, observer=observer )
    curator.register_anon_and_save( dest )

    curator.watch()



exit()



@attr.s(hash=False)
class Watcher(object):
    uid = attr.ib( factory=uuid.uuid4 )
    logger = attr.ib( init=False )

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    # Dereferencer for testing
    def fire(self, event_type, data):
        event = getattr(self, event_type)
        if event:
            event.fire(data)

    def run(self):
        raise NotImplementedError


@attr.s(hash=True)
class FileWatcher(Watcher, wdHandler):
    location = attr.ib( type=str, default=None )
    observer = attr.ib( factory=wdObserver )
    # Event queues
    file_added   = attr.ib( factory=Event )
    file_changed = attr.ib( factory=Event )
    file_removed = attr.ib( factory=Event )

    def run(self):

        self.observer.schedule(self, self.location, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Error")

        self.observer.join()

    def on_any_event(self, event):
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Take any action here when a file is first created.
            print("Received created event - %s." % event.src_path)
            self.file_added(event.src_path)

        elif event.event_type == 'modified':
            # Taken any action here when a file is modified.
            print("Received modified event - %s." % event.src_path)
            self.file_changed(event.src_path)



