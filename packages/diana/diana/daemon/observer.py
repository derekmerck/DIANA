import os, logging, uuid, zipfile, time
from typing import Callable, Collection
import attr
from watchdog.observers import Observer as wdObserver
from watchdog.events import FileSystemEventHandler as wdHandler
from diana.apis import DicomFile, Orthanc, Dixel
from diana.utils import Event, DicomLevel, Pattern


@attr.s
class Observer(object):

    def watch(self, source, handler, condition):
        while True:
            items = source.changes(condition)  # Basically "find recent"
            if items:
                handler.handle_items(items)

    def review(self, source, handler, condition, timekeeper):
        for time_interval in timekeeper:
            items = source.find(condition, time_interval)
            if items:
                handler.handle_items(items)



# Discovers individual items in real time
@attr.s
class Curator(object):
    source = attr.ib( type=Pattern )

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

