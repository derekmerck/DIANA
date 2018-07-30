"""
Diana Harvester (Monitor service)
Merck, Summer 2018

Monitor any Diana service on a time interval. Subclass with
new `discover` and `handle` functions to customize it for a
particular class.  See `harvest_dose.py` for an example.

TODO: Collect := at interval: Survey(source, q, dest, q) -> worklist; Transport(source, dest, worklist)

"""

import logging
import attr
from ..utils import DatetimeInterval


@attr.s
class Harvester(object):
    source = attr.ib(  )
    dest = attr.ib( )

    source_domain = attr.ib( type=str, default=None )
    dest_domain = attr.ib( type=str, default=None )
    dest_hec = attr.ib( type=str, default=None )

    start = attr.ib(default=None)
    incr  = attr.ib(default=None)
    end   = attr.ib(default=None)
    time_window = attr.ib( init=False, type=DatetimeInterval )

    repeat_while = attr.ib( default=True )  # stop condition, true = once

    @time_window.default
    def set_dtinterval(self):
        return DatetimeInterval(self.start, incr=self.incr, end=self.end)

    def run(self):

        while self.repeat_while:
            self.collect()
            self.time_window.next()

    def collect(self):

        recent = self.discover_recent()

        if not recent:
            logging.debug("No recent items, nothing to do")
            return

        indexed = self.discover_indexed()

        if not indexed:
            logging.debug("No items indexed, need to collect {} recent items".format(len(recent)))
            new_items = recent
            self.handle_worklist(new_items)
            return

        logging.debug("COMPARE==============================")
        logging.debug( [x.AccessionNumber for x in recent] )
        logging.debug( [y.AccessionNumber for y in indexed] )
        logging.debug("=============================/COMPARE")

        new_items = set( x for x in recent if x.meta["AccessionNumber"] not in
                         [y.meta['AccessionNumber'] for y in indexed])

        if not new_items:
            logging .debug("No new items, nothing to do")
            return

        logging.debug("Need to collect {} new items".format(len(new_items)))
        self.handle_worklist(new_items)

    def discover_recent(self):
        raise NotImplementedError

    def discover_indexed(self):
        raise NotImplementedError

    def handle_worklist(self, worklist):
        raise NotImplementedError
