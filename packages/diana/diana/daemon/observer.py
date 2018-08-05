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



from datetime import datetime, timedelta
from diana.utils import DatetimeInterval2


class Observable(object):

    def changes(self, condition, since: datetime ):
        raise NotImplemented

    def find(self, condition, timeinterval: DatetimeInterval2):
        raise NotImplemented


class Handler(object):

    def handle(self, item, source, dest=None):
        raise NotImplemented

@attr.s
class Observer(object):
    condition = attr.ib()
    source = attr.ib( type=Observable )
    delay = attr.ib(  default=timedelta(seconds=300) )  # Every 5 mins by default
    schedule = attr.ib(  init=False, type=dtinterval )

    @schedule.init
    def set_schedule(self):
        return DatetimeInterval2(begin=datetime.now(), incr=self.delay)

    def update(self):
        if datetime.now() < self.schedule.end:
            return
        new_items = self.source.changes( self.condition, since=self.schedule.begin )
        next(self.schedule)
        return new_items


@attr.s
class Reviewer(object):
    condition = attr.ib()
    source = attr.ib( type=Observable )
    schedule = attr.ib( type=dtinterval )

    def update(self):
        new_items = self.source.find( self.condition, timeinterval=self.schedule )
        next( self.schedule )
        return new_items

@attr.s
class Sender(object):
    dest=attr.ib()

    def pull_anonymize_and_send(self, _item, source):
        item = source.find(_item)
        item = source.anonymize(item)
        item = source.send(item, self.dest)

    def send(self, _item, source):
        item = source.get(_item)
        self.dest.put(item)

    def record_discovery(self, _item, source):
        # Create an event record
        discovery_record = {
            "site": source.name,
            "discovery_time": datetime.now(),
            "item_time": item.get('_time'),
            "study_desc": item.get('StudyDescription'),
        }
        self.dest.put(discovery_record)

    # def handle_star(self, _item, source):
    #     # make chain
    #     chain( source.get(_item), dest.put() )


@attr.s
class CollectionChannel(object):
    observers = attr.ib( factory=list )
    handlers  = attr.ib( factory=list )

    # Call this as a scheduled task
    def update(self):
        for o in self.observers:
            new_items = o()

            for item in new_items:
                for h in self.handlers:
                    h(item, observer.source)

    # Call this for an independent thread
    def run(self):
        self.update()
        time.sleep(1)


# Collection of channels
@attr.s
class Collector(object):
    channels = attr.ib( init=False, factory=list )

    def run(self):
        for c in self.channels:
            c.update()

        time.sleep(1)


# EXAMPLE

# Endpoints
orthanc = Orthanc()
redis = Redis()

# Observer
obs = Observer(condition="new_instance", source=orthanc)

# Handler
p = Sender(dest=redis)

channel = CollectionChannel(observers=[obs.update], handlers=[p.send])

channel.run()








items = []
dest = Pattern
observer = Observable

items = observer.changes()
if items:
    for item in items:
        if item not in dest:

            # Create an event record
            item['meta'] = {
                "site": "Here",
                "discovery_time": datetime.datetime.now(),
                "item_time": item.get('_time'),
                "study_desc": item.get('StudyDescription'),
            }

            dest.put(item)









@attr.s
class ConditionalHandler(object):
    condition = attr.ib()
    handler = attr.ib()

    # def test(self, ):
    #     if condition:
    #         handler


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


@attr.s(hash=True)
class OrthancWatcher(Watcher):
    orthanc = attr.ib( type=Orthanc, default=None )

    # Event queues
    instance_added   = attr.ib( factory=Event )
    instance_removed = attr.ib( factory=Event )
    study_added   = attr.ib( factory=Event )
    study_removed = attr.ib( factory=Event )

    def run(self):
        # get changes

        # emit some events

        # delete changes
        pass


@attr.s(hash=True)
class Handler(object):
    logger  = attr.ib( init=False )
    watcher = attr.ib( type=Watcher )

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    def handle(self, data):
        raise NotImplementedError


@attr.s(hash=True)
class ArchiveHandler(Handler):
    dest = attr.ib( type=Orthanc )

    def __attrs_post_init__(self):
        self.watcher.file_added += self.handle

    def handle(self, file):

        if os.path.splitext(file)[1] != ".zip":
            return

        # unzip file
        self.logger.debug("Unzipping {}".format(file))

        return

        with zipfile.ZipFile(file) as z:
            for filename in z.namelist():
                if not os.path.isdir(filename):
                    # read the file
                    with z.open(filename) as f:
                        self.logger.debug("Uploading {}".format(filename))
                        self.dest.put(data=f)
        os.remove(file)


@attr.s(hash=True)
class OrthancRouter(Handler):
    dest = attr.ib( type=Orthanc )

    def __attrs_post_init__(self):
        self.watcher.instance_added += self.handle

    def handle(self, oid):

        self.logger.debug("Transferring {}".format(oid))
        self.watcher.source.send(Dixel(meta={"oid": oid}, level=DicomLevel.INSTANCES))


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    fw = FileWatcher(location="/Users/derek/tmp")
    orthanc0 = Orthanc()

    unzipper = ArchiveHandler(fw, orthanc0)

    orthanc1 = Orthanc()
    ow = OrthancWatcher(orthanc0)

    router = OrthancRouter(ow, orthanc1 )

    # ---------

    source_path = "foo.dcm"
    logging.debug("Added {}".format(source_path))
    fw.fire("file_added", source_path)

    source_path = "foo.zip"
    logging.debug("Added {}".format(source_path))
    fw.fire("file_added", source_path)

    logging.debug("Removed {}".format(source_path))
    fw.fire("file_removed", source_path)

    oid = "abcdefg"
    logging.debug("Instance arrived {}".format(oid))
    ow.fire("instance_added", oid)

    logging.debug("Instance removed {}".format(oid))
    ow.fire("instance_removed", oid)


    fw.run()

