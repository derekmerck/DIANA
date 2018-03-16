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

    DB_SELECTION = 14
    DCM_DIR = "/Users/derek/Desktop/Christianson/00"
    R = RedisCache(db=DB_SELECTION, clear=True)
    orthanc = Orthanc(host="trusty64", port=8142, user="orthanc", password="0rthanC!", clear=True)
    assert(orthanc.size()==0)

    T0 = upload_dicom_dir(dcm_dir=DCM_DIR, dest=orthanc, cache=R, compress=False)

    orthanc.clear()
    R.clear()

    T1 = upload_dicom_dir(dcm_dir=DCM_DIR, dest=orthanc, cache=R, compress=True)

    assert(T0[3] < T1[3])
    assert(T1[4] < T0[4])


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    # test_upload_dicom_dir_w_compression()

    INVENTORY_DIR         = False
    REFACTOR_FILES_TO_ANS = False
    UPLOAD_ANS            = True

    dcm_dir = "/Users/derek/Desktop/Christianson"

    db_files = 14
    R = RedisCache(db=db_files, clear=INVENTORY_DIR)

    db_accessions = 13
    Q = RedisCache(db=db_accessions, clear=REFACTOR_FILES_TO_ANS)

    orthanc = Orthanc(host="trusty64", port=8142, user="orthanc", password="0rthanC!", clear=UPLOAD_ANS)

    if INVENTORY_DIR:
        logging.info("Inventorying DICOM dir")
        dicom_dir_inventory(dcm_dir, R)

    if REFACTOR_FILES_TO_ANS:
        logging.info("Refactoring files to accession numbers")
        for k in R.keys():
            v = R.get(k)
            fp = k
            accession_num = v['AccessionNumber']
            Q.lpush(accession_num, fp)

    def upload_accession(dest, accession_number, accession_cache, file_cache, compress=False, lazy=True):

        # All members of this accession
        fns = accession_cache.lget(accession_number)

        logging.debug(fns)

        # Create a worklist
        worklist = set()
        for fp in fns:
            # fp = os.path.join(dcm_dir, fn[0:2], fn[2:4], fn)
            logging.debug(fp)
            d = Dixel(key=fp, cache=file_cache)
            worklist.add(d)
            logging.debug(pformat(d.data))

        dest.add_all(worklist, compress=compress, lazy=True)

    if UPLOAD_ANS:
        upload_accession(orthanc, 'X001650710', Q, R)
        upload_accession(orthanc, 'A2954207', Q, R)




