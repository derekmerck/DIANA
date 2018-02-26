import logging
from pprint import pformat
from DixelKit.DixelStorage import CachePolicy
from DixelKit.FileStorage import FileStorage
from DixelKit.Orthanc import Orthanc, OrthancProxy
from DixelKit.Montage import Montage
from DixelKit.Splunk import Splunk
from DixelKit import DixelTools

def test_indexer():

    orthanc = Orthanc('localhost', 8042)
    splunk = Splunk('localhost', 8089, 'admin', 'changeme')
    orthanc.copy_inventory(splunk, lazy=True)


def test_mirror():

    # Caches inventory by default
    file_dir = FileStorage("/users/derek/Desktop/Protect3/80", cache_policy=CachePolicy.USE_CACHE)
    assert( len(file_dir.inventory) == 119 )

    # No caching by default
    orthanc = Orthanc('localhost', 8042)

    orthanc.delete_inventory()
    assert( len(orthanc.inventory) == 0 )
    s = orthanc.statistics()
    logging.debug(pformat(s))
    assert( s["TotalDiskSizeMB"] == 0 )

    # Size should be 0

    # Upload whatever is missing
    copied = file_dir.copy_inventory(orthanc)
    logging.debug(copied)
    assert( copied == 119 )
    s = orthanc.statistics()
    logging.debug(pformat(s))
    assert( s["TotalDiskSizeMB"] > 60 )

    # Size should be about 65MB

    # Upload whatever is missing
    copied = file_dir.copy_inventory(orthanc, lazy=True)
    logging.debug(copied)
    assert( copied == 0 )
    s = orthanc.statistics()
    logging.debug(pformat(s))

    # Set this orthanc to prefer compressed data
    orthanc.prefer_compressed = True
    orthanc.delete_inventory()
    assert( len(orthanc.inventory) == 0 )
    s = orthanc.statistics()
    logging.debug(pformat(s))

    # Size should be 0

    # Upload whatever is missing
    copied = file_dir.copy_inventory(orthanc)
    logging.debug(copied)
    assert( copied == 119 )
    s = orthanc.statistics()
    logging.debug(pformat(s))
    assert( s["TotalDiskSizeMB"] < 20 )

    # Size should be less than uncompressed (65)

    # Confirm compressed has same id as uncompressed
    orthanc.prefer_compressed = False
    copied = file_dir.copy_inventory(orthanc, lazy=True)
    logging.debug(copied)
    assert( copied == 0 )
    s = orthanc.statistics()
    logging.debug(pformat(s))


    # At this point, the original attachment is MOOT, I believe


def test_pacs_lookup():

    splunk = Splunk()
    archive = Orthanc()
    proxy = OrthancProxy('localhost', 8042, remote="remote_aet")
    dest = Orthanc('localhost', 8042)
    montage = Montage()

    # No AccessionNumber yet, so we have to uniquify by mrn+time
    worklist = DixelTools.load_csv(csv_file="/Users/derek/Desktop/elvos3.csv",
                                   secondary_id="Treatment Time")

    splunk.update_worklist(worklist)       # Find indexed studies on source, update id's
    archive.copy_worklist(dest, worklist)

    proxy.update_worklist(worklist)        # Find other studies on PACS, update id's
    proxy.copy_worklist(worklist, dest)

    # worklist.update(montage)

    DixelTools.save_csv(csv_file="/Users/derek/Desktop/elvos3-out.csv")


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)

    test_mirror()
    # test_pacs_lookup()
