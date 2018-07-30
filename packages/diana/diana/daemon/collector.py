import logging
from typing import Collection, Union
import attr
from diana.apis import Dixel, Orthanc, OrthancPeer, DicomFile, Splunk
from diana.utils import Pattern


@attr.s
class Surveyor(object):
    source = attr.ib( type=Pattern )
    source_domain = attr.ib( type=str, default=None )
    dest = attr.ib( type=Pattern, default=None )
    dest_domain = attr.ib( type=str, default=None )

    def find_items(self, source_query, dest_query=None) -> Collection:

        candidates = self.source.find_items(source_query)

        if self.index and dest_query:
            discovered = self.dest.find_items(dest_query)
            return candidates - discovered
        else:
            return candidates


@attr.s
class Porter(object):
    source = attr.ib( type=Pattern )
    source_domain = attr.ib( type=str, default=None )
    dest = attr.ib( type=Pattern )
    dest_domain = attr.ib( type=str, default=None )
    dest_hec = attr.ib( type=str, default=None )
    clean = attr.ib( default=True )
    anonymize = attr.ib( type=bool )

    # Somehow self and dest need to embed all their local info like domain, hec, etc., so this can
    # be templated.

    def move_item2(self, d: Dixel):

        try:
            self.dest.check(d)
        except:
            raise Exception("Item already present in dest")

        try:
            self.source.check(d, True)  # calls retrieve if proxied
        except:
            raise Exception("Item not present in source")

        if type(self.source) == Orthanc and self.anonymize:
            try:
                e = self.source.anonymize(d)
                if self.clean:
                    self.source.remove(d)
                d = e
            except:
                raise Exception("Item could not be deidentified")

        try:
            if type(self.dest) == DicomFile or type(self.dest) == Orthanc:
                view = "file"
            elif type(self.dest) == Splunk:
                view = "tags"
            else:
                view = "meta"

            d = self.source.get(d, view=view)
            if self.clean:
                self.source.remove(d)
        except:
            raise Exception("Can not get item from source")

        try:
            self.dest.put(d)
        except:
            raise Exception("Can not put item in dest")


    def move_item(self, d: Dixel):

        # If already dealt with, ignore it
        if self.dest.check(d):
            logging.warning("Skipping {} - already present in dest".format(d))
            return

        # If this is a proxied source, need to retrieve it first
        if self.source_domain:

            if not d.meta.get("StudyInstanceUID"):
                logging.warning("Skipping {} - apparently unfindable".format(d))
                return

            e = self.source.find_item(d, domain=self.source_domain, retrieve=True)
            if not e:
                logging.warning("Skipping {} - could not retrieve".format(d))
                return

        # If anonymization requested
        if self.anonymize:

            try:
                e = self.source.anonymize(d)
            except:
                logging.warning("Skipping {} - could not anonymize (bad UID?)".format(d))
                return False

            if self.clean:
                self.source.remove(d)
            d = e

        # If this is a File or Orthanc dest, need to get file
        if type(self.dest) == DicomFile or type(self.dest) == Orthanc:
            self.source.get(d, view="archive")
            self.dest.put(d)

        # If this is a Splunk dest, need to get meta
        elif type(self.dest) == Splunk:
            self.source.get(d, view="meta")
            self.dest.put(d, domain=self.dest_domain, hec=self.dest_hec)

        # If this is an OrthancPeer, nothing to get, just need oid
        else:
            self.dest.put(d)

        if self.clean:
            self.source.remove(d)

    def move_items(self, worklist: Collection):

        for d in worklist:
            self.move_item(d)


@attr.s
class Collector(object):
    source = attr.ib( type=Pattern )
    source_domain = attr.ib( type=str, default=None )
    dest = attr.ib( type=Pattern )
    dest_domain = attr.ib( type=str, default=None )
    dest_hec = attr.ib( type=str, default=None )

    anonymize = attr.ib( default=True )
    clean     = attr.ib( default=True )

    surveyor = attr.ib( factory=Surveyor(source, source_domain, dest, dest_domain) )
    dest_porter = attr.ib( factory=Porter(source=source, dest=dest,
                                          dest_domain=dest_domain, dest_hec=dest_hec,
                                          anonymize=anonymize, clean=clean) )

    def collect_items(self, source_query, index_query):

        w = self.surveyor.find_items(source_query, index_query)
        self.porter.move_items(w)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    # ------------------------------------------
    # Inventory a proxied DICOM node
    # ------------------------------------------

    proxy = Orthanc("http://locahost:8042")
    proxied_aet = "pacs"

    s = Surveyor(proxy, proxied_aet)
    w = s.find_items(source_query={"StudyDate": "01012018"})

    # ------------------------------------------
    # Lazy inventory (only new items)
    # ------------------------------------------

    splunk = Splunk("http://localhost:8000")
    splunk_kwargs = {
        "index": "dicom",
        "hec": None
    }

    t = Surveyor(proxy, source_domain=proxied_aet, dest=splunk, dest_domain=None)
    w = s.find_items(source_query={"StudyDate": "01012018"},
                     dest_query={"index={self.index} | table AccessionNumber "})

    # ------------------------------------------
    # Move the worklist from the proxy to disk
    # ------------------------------------------

    files = DicomFile("/data/files", explode=(1,1))

    p = Porter( proxy, source_domain=proxied_aet, dest=files, anonymize=True )
    p.move_items(w)

    # ------------------------------------------
    # Move worklist from the proxy to a peer
    # ------------------------------------------

    archive = OrthancPeer( proxy, "archive" )

    p = Porter( proxy, source_domain=proxied_aet, dest=archive, anonymize=True )
    p.move_items(w)

    # ------------------------------------------
    # Lazy inventory to Splunk
    # ------------------------------------------

    c = Collector(source=proxy, source_domain=proxied_aet,
                  dest=splunk, dest_domain=None, dest_hec=None,
                  anonymize=False )

    c.collect_items(source_query={"StudyDate": "01012018"},
                    index_query={"index={self.index} | table AccessionNumber "})
