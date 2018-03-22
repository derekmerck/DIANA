import logging
import os
from pprint import pformat
from dixel import Dixel, DLVL
from dcache import CSVCache
from GUIDMint import PseudoMint

def create_key_csv(cache, fp):
    N = CSVCache(fp,
                 key_field="AccessionNumber",
                 autosave=False, clear=True)
    for k in cache.keys():
        d = Dixel(key=k, cache=cache)
        # logging.debug(d.data)
        N.put(k, d.data)
    N.save_fn()
    logging.debug("Saved {} entries".format(len(N)))


def copy_from_pacs(proxy, remote_aet, cache, save_dir, anon_map=None, lazy=True, clean_proxy=True):

    for key in R.keys():
        d = Dixel(key=key, cache=cache)

        if not d.data.get('AnonID'):
            logging.warn("No anon ID for MRN {}".format(d.data['PatientID']))
            continue

        fp = os.path.join(save_dir, d.data['AnonID'] + '.zip')

        # Check if file already exists for lazy!
        if lazy and os.path.exists(fp):
            logging.debug('{} already exists -- skipping'.format(d.data['AnonID'] + '.zip'))
            continue

        if not d in proxy:
            proxy.find(d, remote_aet, retrieve=True)

        if not d in proxy:
            logging.warn("{} was not retrieved successfully!".format(d.data["AccessionNumber"]))
            continue

        r = proxy.anonymize(d, replacement_map=anon_map)

        logging.debug(r)

        d.data['AnonOID'] = r['ID']
        d.persist()

        # Need an oid and an anon namne to save...
        e = Dixel(key=d.data['AnonOID'],
                  data={'OID': d.data['AnonOID'],
                        'PatientID': d.data['AnonID']},
                  dlvl=d.dlvl)
        file_data = proxy.get(e, get_type='file')
        e.write_file(file_data, save_dir=save_dir)

        if clean_proxy:
            proxy.remove(d)
            proxy.remove(e)


def set_anon_ids(cache, mint=None, lazy=True):

    if not mint:
        mint = PseudoMint()

    for key in cache.keys():
        d = Dixel(key=key, cache=cache)

        if lazy and not \
            (d.data.get('AnonID') and
             d.data.get('AnonName') and
             d.data.get('AnonDoB') ):

            name = d.data.get('PatientName')
            gender = d.data.get('PatientSex', 'U')
            dob = d.data.get('PatientBirthDate')

            if not name or not dob:
                logging.debug('Inadequate data to anonymize {}'.format(d.data.get('PatientID')))
                continue

            dob = "-".join([dob[:4],dob[4:6],dob[6:]])
            anon = mint.pseudo_identity(name=name, gender=gender, dob=dob)

            d.data['AnonID'] = anon[0]
            d.data['AnonName'] = anon[1]
            d.data['AnonDoB'] = anon[2]

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

        ret = proxy.find(d, remote_aet, retrieve=retrieve)
        if ret:
            # Take the first entry in ret and update the STUID/SERUID/INSTUID so we can retrieve
            d.data['StudyInstanceUID'] = ret[0].get("StudyInstanceUID")
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