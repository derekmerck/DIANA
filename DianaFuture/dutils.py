from dcache import RedisCache, PickleCache
from dixel import Dixel, DLVL
from dapi import Orthanc
import os
import logging
from pprint import pformat
from pytictoc import TicToc

"""
Each of the CIRR's 256 1st level subfolders has about 60GB of data in it...
"""


def dicom_dir_inventory(dcm_dir, cache):
    worklist = set()
    n = 0
    for root, dirs, files in os.walk(dcm_dir, topdown=True):
        for name in files:
            # Ignore junk files
            if name.startswith("."):
                continue
            n = n+1
            fp = os.path.join(root, name)
            logging.debug(fp)
            #ETAFF
            try:
                # Create an instance dixel with a fp key
                d = Dixel(fp, cache=cache, init_fn=Dixel.read_dcm, dlvl=DLVL.INSTANCES)
                worklist.add(d)
            except Exception, e:
                logging.error(e.message)
                pass

    return worklist, n



def upload_dicom_dir(dcm_dir, dest, cache=None, compress=False):

    logging.info("-----------------------------------")
    logging.info("Starting clock for upload_dicom_dir")

    t = TicToc()
    t.tic()
    logging.info("Inventorying DICOM dir")
    worklist, n_items = dicom_dir_inventory(dcm_dir, cache)
    worklist_time = t.tocvalue(restart=True)

    logging.info("Uploading instances")
    initial_size = dest.size()
    dest.add_all(worklist, compress=compress, lazy=True)
    upload_time = t.tocvalue()
    final_size = dest.size()

    dcm_items = len(worklist)
    inventory_time = round(worklist_time, 2)
    upload_time = round(upload_time, 2)
    upload_mb = final_size-initial_size

    logging.info("-----------------------------------")
    logging.info("Found {} DCM items (of {})".format(dcm_items, n_items))
    logging.info("Inventory time: {} secs".format(inventory_time))
    logging.info("Upload time: {} secs".format(upload_time))
    logging.info("Uploaded MB: {}".format(upload_mb))
    logging.info("-----------------------------------")

    return dcm_items, n_items, inventory_time, upload_time, upload_mb


def test_upload_dicom_dir_w_compression():

    DCM_DIR = "/Users/derek/Desktop/Christianson/00"
    R = RedisCache(db=15, clear=True)
    orthanc = Orthanc(host="trusty64", port=8142, user="orthanc", password="0rthanC!", clear=True)
    assert(orthanc.size()==0)

    T0 = upload_dicom_dir(dcm_dir=DCM_DIR, dest=orthanc, cache=R, compress=False)

    orthanc.clear()
    R.clear()

    T1 = upload_dicom_dir(dcm_dir=DCM_DIR, dest=orthanc, cache=R, compress=True)

    assert(T0[3] < T1[3])
    assert(T1[4] < T0[4])


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    test_upload_dicom_dir_w_compression()



