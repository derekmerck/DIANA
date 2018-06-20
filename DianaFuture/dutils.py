import logging
import os
from pprint import pformat
import hashlib
from dixel import Dixel, DLVL
from dcache import CSVCache
from GUIDMint import PseudoMint

def create_key_csv(cache, fp, fieldnames=None, key_field="AccessionNumber"):
    N = CSVCache(fp,
                 key_field=key_field,
                 autosave=False, clear=True)
    for k, v in cache.cache.iteritems():
        v_ = {}
        for kk, vv in v.iteritems():
            if not fieldnames or kk in fieldnames:
                v_[kk] = vv
        N.put(k, v_)
    N.save_fn()
    logging.debug("Saved {} entries".format(len(N)))


def copy_from_pacs(proxy, remote_aet, cache, save_dir, anon_map=None, lazy=True, clean_proxy=True, depth=0, dry_run=False):

    def dixel_save_dir(fn, save_dir, depth):
        fd = save_dir
        if depth:
            for de in range(depth):
                fd = os.path.join(fd, fn[de])
        return fd

    for key in cache.keys():
        d = Dixel(key=key, cache=cache)

        # An AnonID isn't usually going to be assigned until
        # there has been a DICOM UID lookup, so this is a
        # reasonable check for "record complete"
        if not d.data.get('AnonID'):
            logging.warn("No anon ID for MRN {}".format(d.data['PatientID']))
            d.data['status'] = "missing_info"
            continue

        if d.data.get('status', 'ready') != "ready":
            continue

        d.data['fn_base'] = d.data['AnonAccessionNum']
        fn = '{}.zip'.format(d.data['fn_base'])
        dsd = dixel_save_dir(fn, save_dir, depth)
        fp = os.path.join(dsd, fn)

        # Check if file already exists for lazy!
        if lazy and os.path.exists(fp):
            logging.debug('Skipping {}: already exists'.format(fn[0:7]))
            d.data['status'] = "done"
            continue

        # loc = d.data.get('RetrieveAETitle').lower()
        # if not proxy.remote_names.get(loc):
        #     logging.warn("Skipping {}: No retrieve loc provided".format(fn))
        #     continue

        if dry_run:
            logging.debug("Skipping {}: Dry-run, no retreive attempted".format(fn[0:7]))
            continue

        if not d in proxy:
            proxy.find(d, remote_aet, retrieve=True)

        if not d in proxy:
            logging.warn("Failed {}: Unsuccessful retrieval!".format(fn[0:7]))
            d.data['status'] = "unretrievable"
            d.persist()
            continue

        r = proxy.anonymize(d, replacement_map=anon_map)

        # logging.debug(r)

        d.data['AnonOID'] = r['ID']
        d.persist()

        # Need an oid and an anon name to save...
        e = Dixel(key=d.data['AnonOID'],
                  data={'OID': d.data['AnonOID'],
                        'fn_base': d.data['fn_base']},
                  dlvl=d.dlvl)
        file_data = proxy.get(e, get_type='file')

        e.write_file(file_data, save_dir=dsd)

        if clean_proxy:
            proxy.remove(d)
            proxy.remove(e)

        d.data['status'] = "done"
        logging.info("Grabbed {}".format(fn[0:7]))


def set_anon_ids(cache=None, mint=None, lazy=True, dixel=None):

    def set_anon_id(d):

        if lazy and not \
            (d.data.get('AnonID') and
             d.data.get('AnonName') and
             d.data.get('AnonDoB') ):

            name = d.data.get('PatientName')
            gender = d.data.get('PatientSex', 'U')
            dob = d.data.get('PatientBirthDate')

            if not name or not dob:
                logging.debug('Inadequate data to anonymize {}'.format(d.data.get('PatientID')))
                raise KeyError

            dob = "-".join([dob[:4],dob[4:6],dob[6:]])
            anon = mint.pseudo_identity(name=name, gender=gender, dob=dob)

            d.data['AnonID'] = anon[0]
            d.data['AnonName'] = anon[1]
            d.data['AnonDoB'] = anon[2]

            d.persist()

    if not mint:
        mint = PseudoMint()

    if dixel:
        set_anon_id(dixel)
        return

    if cache:

        for key in cache.keys():
            d = Dixel(key=key, cache=cache)
            set_anon_id(d)
        #
        # if lazy and not \
        #     (d.data.get('AnonID') and
        #      d.data.get('AnonName') and
        #      d.data.get('AnonDoB') ):
        #
        #     name = d.data.get('PatientName')
        #     gender = d.data.get('PatientSex', 'U')
        #     dob = d.data.get('PatientBirthDate')
        #
        #     if not name or not dob:
        #         logging.debug('Inadequate data to anonymize {}'.format(d.data.get('PatientID')))
        #         continue
        #
        #     dob = "-".join([dob[:4],dob[4:6],dob[6:]])
        #     anon = mint.pseudo_identity(name=name, gender=gender, dob=dob)
        #
        #     d.data['AnonID'] = anon[0]
        #     d.data['AnonName'] = anon[1]
        #     d.data['AnonDoB'] = anon[2]
        #
        #     d.persist()

def lookup_accessions(cache, report_db, lazy=True):
    # Use a proxy and a condition (time) to identify study_level accession nums/stuids

    for key in cache.keys():
        d = Dixel(key=key, cache=cache)

        if d.dlvl != DLVL.STUDIES:
            logging.debug("Can only lookup AccessionNumber for study level dixels, skipping MRN {}".format(d.data['PatientID']))
            continue

        if lazy and d.data.get('AccessionNumber'):
            logging.debug("Already have AccessionNumber info for {}, skipping.".format(d.data['AccessionNumber']))
            continue

        report_db.find(d, time_delta="-1d")
        d.persist()


def lookup_uids(cache, proxy, remote_aet, retrieve=False, lazy=True):
    # Use a proxy to lookup StudyUID, SeriesUID, and SOPInstanceUID data
    for key in cache.keys():
        d = Dixel(key=key, cache=cache)

        if lazy and not retrieve and \
                (d.dlvl == DLVL.STUDIES and d.data.get('StudyInstanceUID')) or \
                (d.dlvl == DLVL.SERIES and d.data.get('StudyInstanceUID') and
                                        d.data.get('SeriesInstanceUID')) or \
                (d.dlvl == DLVL.INSTANCES and d.data.get('StudyInstanceUID') and
                                        d.data.get('SeriesInstanceUID') and
                                        d.data.get('SOPInstanceUID')):
            logging.debug("Already have UID info for {}, skipping.".format(d.data['AccessionNumber']))
            continue

        # retrieve = True
        # logging.debug(d.data['PatientLastName'])
        d.data['PatientID'] = ""

        ret = proxy.find(d, remote_aet, retrieve=retrieve)
        if ret:
            # Take the first entry in ret and update the STUID/SERUID/INSTUID so we can retrieve
            if not d.data.get("AccessionNumber"):
                d.data['AccessionNumber'] = ret[0].get("AccessionNumber")
            d.data['StudyInstanceUID'] = ret[0].get("StudyInstanceUID")
            d.data['PatientID'] = ret[0].get("PatientID")
            d.data['PatientName'] = ret[0].get("PatientName")
            d.data['PatientBirthDate'] = ret[0].get("PatientBirthDate")
            d.data['PatientSex'] = ret[0].get("PatientSex")
            if d.dlvl == DLVL.SERIES or d.dlvl == DLVL.INSTANCES:
                d.data['SeriesInstanceUID'] = ret[0].get("SeriesInstanceUID")
            if d.dlvl == DLVL.SERIES:
                d.data['SeriesDescription'] = ret[0].get("SeriesDescription")
                d.data['SeriesNumber'] = ret[0].get("SeriesNumber")
                d.data['SeriesNumInstances'] = ret[0].get('NumberOfSeriesRelatedInstances')
            if d.dlvl == DLVL.INSTANCES:
                d.data['SOPInstanceUID'] = ret[0].get("SOPInstanceUID")

            d.persist()
        else:
            logging.warning("No answers for {}".format(d.data["AccessionNumber"]))


def lookup_child_uids(cache, c_cache, child_qs, proxy, remote_aet):
    # Use a proxy to lookup child StudyUID, SeriesUID, and SOPInstanceUID data
    for key in cache.keys():
        d = Dixel(key=key, cache=cache)

        if d.dlvl == DLVL.SERIES:
            logging.info("Already found a series for this dixel, skipping")
            continue

        for q in child_qs:
            qkey = "{}-{}".format(key, str(hash(pformat(q)))[-4:])

            data = dict(d.data)
            data.update(q)

            # logging.debug(pformat(data))
            e = Dixel(key=qkey, data=data, cache=c_cache)
            # Can't put this in init() for some reason
            e.dlvl = d.dlvl.child()

            ret = proxy.find(e, remote_aet)
            if ret:

                # logging.debug(pformat(ret[0]))

                e.data['StudyInstanceUID'] = ret[0].get("StudyInstanceUID")
                e.data['PatientName'] = ret[0].get("PatientName")
                e.data['PatientBirthDate'] = ret[0].get("PatientBirthDate")
                e.data['PatientSex'] = ret[0].get("PatientSex")
                if e.dlvl == DLVL.SERIES or e.dlvl == DLVL.INSTANCES:
                    e.data['SeriesInstanceUID'] = ret[0].get("SeriesInstanceUID")
                if e.dlvl == DLVL.SERIES:
                    e.data['SeriesDescription'] = ret[0].get("SeriesDescription")
                    e.data['SeriesNumber'] = ret[0].get("SeriesNumber")
                    e.data['SeriesNumInstances'] = ret[0].get('NumberOfSeriesRelatedInstances')
                if e.dlvl == DLVL.INSTANCES:
                    e.data['SOPInstanceUID'] = ret[0].get("SOPInstanceUID")

                e.persist()