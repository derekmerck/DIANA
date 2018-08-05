"""
Watcher has an observable **source** and multiple **handlers**

The observable source is called for **changes**, this may take a _since_ parameter and _blocking_


"""
import logging, zipfile, os
import attr
from diana.apis import Orthanc, DicomFile, Dixel
from diana.utils import Event, ObservableMixin, Watcher


@attr.s
class DixelHandler(object):
    # For sources -> anon queue

    dest = attr.ib( default=None )
    anonymize = attr.ib( default=False )
    remove = attr.ib( default=False )
    logger = attr.ib( init=False, factory=logging.getLogger )



    def unpack_and_put(self, event):

        item_fp = event.data
        source = event.source

        self.logger.debug("Unzipping {}".format(item_fp))
        with zipfile.ZipFile(item_fp) as z:
            for filename in z.namelist():
                if not os.path.isdir(filename):
                    # read the file
                    with z.open(filename) as f:
                        self.logger.debug("Uploading {}".format(filename))
                        item = Dixel(file=f)
                        self.dest.send(item)
        if self.remove:
            os.remove(item_fp)

    def get_and_put(self, event):

        item_id = event.data
        source = event.source

        if self.anonymize:
            item = source.anonymize(item_id, remove=self.remove)
            item = source.get(item, view="file")
        else:
            item = source.get(item_id, view="file")
            if self.remove:
                os.remove(item_id)

        self.dest.put(item)



@attr.s
# This should actually be a base file class or a mixin
class ObservableDicomFile(ObservableMixin, DicomFile):

    from watchdog.observers import Observer as wdObserver
    from watchdog.events import FileSystemEventHandler as wdHandler

    observer = attr.ib( factory=wdObserver )

    def poll_changes(self, *kwargs):
        # Don't need last event for watchdog monitoring

        self.observer.schedule(self, self.location, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Error")

        self.observer.join()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    import time

    class MockDicomFile(ObservableMixin, DicomFile):

        def poll_changes(self, last_event=None, **kwargs):
            event_queue = []
            for i in range(3):
                event_queue.append( self.gen_event("new_file", "foo", "next") )
            return event_queue

    class MockOrthanc(ObservableMixin, Orthanc):

        def poll_changes(self, last_event=None, **kwargs):
            event_queue = []
            for i in range(3):
                event_queue.append( self.gen_event("new_instance", "foo", "uuid") )
            return event_queue


    # Some test endpoints

    s1_f = MockDicomFile(location="/Users/derek/Desktop/dcm")
    s1_q = MockOrthanc()
    s1_o = MockOrthanc( port=8043 )
    s1_i = MockSplunk( domain = 's1')

    px_o = MockOrthanc( port=8044, proxy='gepacs' )
    px_i = MockSplunk( domain = 'px' )

    routes = {
        # [source, event]:      ['action', destination]
        [s1_f, 'new_file']:        [     'get_and_put', s1_q],
        [s1_f, 'new_archive']:     [  'unpack_and_put', s1_q],
        # [s1_q, 'new_instance']: ['anon_get_and_put', s1_o],
        [s1_q, 'new_instance']:    ['anon_get_and_put_and_put', s1_o, s1_i ],
        [px_o, 'new_dose_series']: ['pull_get_and_put', px_i ]
    }
