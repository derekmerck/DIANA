import logging, uuid
from typing import List, Any
import attr


@attr.s
class Event(object):
    event_type = attr.ib()
    data = attr.ib()
    source = attr.ib()
    eid = attr.ib(factory=uuid.uuid4)

    def __str__(self):
        return "{} : {} : {}".format(self.source, self.event_type, self.data)


@attr.s
class ObservableMixin(object):
    event_count = attr.ib( init=False, default=0 )

    def poll_changes(self, last_event: Event=None, *args, **kwargs) -> List[Event]:
        """
        last_event provides a reference for a changes_since() func
        Return a _list_ of events, even if only a singleton
        """
        raise NotImplementedError

    def gen_event(self, event_type: str, event_data: Any=None, eid: Any=None ):
        """
        eid is optional: if None, a uuid is created, if "next", a count is returned
        """
        if not eid or eid == "uuid":
            # Generate a hash id
            return Event(source=self, event_type=event_type, data=event_data, eid=uuid.uuid4())

        if eid == "next":
            self.event_count += 1
            return Event(source=self, event_type=event_type, data=event_data, eid=self.event_count)

        return Event(source=self, event_type=event_type, data=event_data, eid=eid)


@attr.s
class Watcher(object):

    source = attr.ib( type=ObservableMixin )
    handlers = attr.ib( factory=list )
    last_event = attr.ib( init=False, default=None, type=Event )
    logger = attr.ib( init=False )

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    def fire(self, event: Event):
        self.last_event = event
        for handle in self.handlers:
            handle(event)

    def run(self):
        while True:
            events = self.source.poll_changes(last_event=self.last_event)
            if events:
                for event in events:
                    self.fire(event)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    import time

    class MockFileObserver(ObservableMixin):

        def poll_changes(self, last_event=None, **kwargs):
            time.sleep(2)
            event_queue = []
            for i in range(3):
                event_queue.append( self.gen_event("file_changed", "foo", "next") )
            return event_queue

    def handler(event):
        logging.debug("{} : {}: {} : {}".format(event.eid,
                                        event.source.__class__.__name__,
                                        event.event_type,
                                        event.data))

    source = MockFileObserver()
    watcher = Watcher(source=source, handlers=[handler])
    watcher.run()
