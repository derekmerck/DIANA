"""
Generic Event Routing Framework

- Enumerate EventTypes
- Watched sources should implement the ObservableMixin.changes() interface and return a list of tuples (type, data)
- Configure a routing table as in the example, use functools.partial for complex handlers with multiple arguments.
- Call the Watcher with "run"

"""

# TODO: something similar but "reviewable" for historical data pulls

import logging, uuid, time
from enum import Enum, auto
from typing import Any, Tuple, List
from multiprocessing import Process, Queue
import attr


@attr.s
class Event(object):
    event_type = attr.ib( type=Enum )
    event_data: Any = attr.ib()
    event_source = attr.ib( default=None )  # Cannot pass these through mp queue, have to addend them later
    event_count = attr.ib( type=int, default=None )
    event_uid = attr.ib( init=False, factory=uuid.uuid4 )

    def __str__(self):
        return "{} : {} : {} : {} : {}".format(self.event_count,
                                          str(self.event_uid)[0:6],
                                          self.event_source.__class__.__name__ or "None",
                                          self.event_type,
                                          self.event_data)


@attr.s(hash=False)
class ObservableMixin(object):
    event_count = attr.ib( init=False, default=0 )
    logger = attr.ib(factory=logging.getLogger)
    events = attr.ib(factory=Queue)

    def changes(self) -> List[Tuple[Enum, Any]]:
        raise NotImplementedError

    def poll_events(self):

        def poll():
            while True:
                new_events = self.changes()
                if new_events:
                    for event_type, event_data in new_events:
                        # logging.debug(change)
                        event = self.gen_event(event_type=event_type, event_data=event_data)
                        # self.logger.debug('Adding to event queue')
                        self.events.put(event)
                time.sleep(1.0)

        p = Process(target=poll)
        p.start()

    def gen_event( self, event_type: Enum, event_data: Any=None ):
        self.event_count += 1
        return Event(event_type=event_type, event_data=event_data, event_count=self.event_count)


@attr.s
class Watcher(object):
    routes = attr.ib( factory=dict ) # form = { [source, event_type]: partial(func, args), ... }
    logger = attr.ib()

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    def log_event(self, event):
        self.logger.debug(event)

    def fire(self, event):
        func = self.routes.get((event.event_source, event.event_type))
        if func:
            return func(event)

    def run(self):

        sources = []
        route_keys = self.routes.keys()
        for key in route_keys:
            if key[0] not in sources:
                sources.append(key[0])

        for source in sources:
            source.poll_events()

        while True:
            # self.logger.debug("Checking queues")
            for source in sources:
                while not source.events.empty():
                    event = source.events.get()
                    event.event_source = source
                    self.fire(event)
            time.sleep(1)

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    class EventType(Enum):
        ADDED = auto()
        CHANGED = auto()
        REMOVED = auto()

    @attr.s(hash=False)
    class MockObserver(ObservableMixin):
        start = attr.ib( factory=time.time )

        def changes(self):
            current = time.time()
            # self.logger.debug(current-self.start)

            if current-self.start > 8 and self.event_count < 4:
                return [self.sample_events.pop()]
            elif current-self.start > 6 and self.event_count < 3:
                return [self.sample_events.pop()]
            elif current-self.start > 4 and self.event_count < 2:
                return [self.sample_events.pop()]
            elif current-self.start > 2 and self.event_count < 1:
                return [self.sample_events.pop()]


    source1 = MockObserver()
    source1.sample_events = [
            (EventType.ADDED,   "foo" ),
            (EventType.ADDED,   "bar" ),
            (EventType.CHANGED, "foo" ),
            (EventType.REMOVED, "foo" ),
        ]

    source2 = MockObserver()
    source2.sample_events = [
            (EventType.ADDED,   "FOO" ),
            (EventType.ADDED,   "BAR" ),
            (EventType.CHANGED, "FOO" ),
            (EventType.REMOVED, "FOO" ),
        ]

    watcher = Watcher()

    watcher.routes = {
        (source1, EventType.ADDED):   watcher.log_event,
        (source1, EventType.CHANGED): watcher.log_event,
        (source2, EventType.ADDED):   watcher.log_event
    }

    watcher.fire( Event( EventType.ADDED, 'foo', source=source2 ))

    watcher.run()
