from hashlib import sha1
import csv
import os
import re
import logging
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser
from bs4 import BeautifulSoup   # For report anonymization
import pickle
from Dixel import *
from pprint import pformat

from StructuredTags import simplify_tags

DICOM_SOPS = {
    '1.2.840.10008.5.1.4.1.1.2':     'CT Image Storage',
    '1.2.840.10008.5.1.4.1.1.88.22': 'Enhanced SR',
    '1.2.840.10008.5.1.4.1.1.88.67': 'X-Ray Radiation Dose SR',             # Can't compress
    '1.2.840.10008.5.1.4.1.1.7':     'Secondary Capture Image Storage'      # Can't compress
}

DICOM_TRANSFERSYNTAX_UID = {
    '1.2.840.10008.1.2':	        'Implicit VR Endian: Default Transfer Syntax for DICOM',
    '1.2.840.10008.1.2.1':	        'Explicit VR Little Endian',
    '1.2.840.10008.1.2.1.99':	    'Deflated Explicit VR Little Endian',
    '1.2.840.10008.1.2.2':	        'Explicit VR Big Endian',
    '1.2.840.10008.1.2.4.90':       'JPEG 2000 Image Compression (Lossless Only)'
}


def load_csv(csv_file, secondary_id=None):
    with open(csv_file, 'rU') as f:
        items = csv.DictReader(f)
        s = set()
        for item in items:
            # Need to create a unique identifier without having tags
            #   1. Use OID if available
            id = item.get('OID')
            #   2. Use AN if available
            if not id:
                id = item.get('AccessionNumber')
            #   3. If no AN, try PatientID + secondary_id (ie, Treatment Time)

            if not id and item.get('Accession Number'):
                id = item.get('Accession Number')
                item['AccessionNumber'] = item.get('Accession Number')
                del(item['Accession Number'])

            if not id:
                if not secondary_id:
                    raise ValueError("Needs AccessionNumber or MRN+Ref")
                id = item.get('PatientID') + item.get(secondary_id)

            if not item.get('PatientID'):
                item['PatientID'] = item.get('Patient MRN')
                del(item['Patient MRN'])

            # logging.debug(pformat(item))

            d = Dixel(id, level=DicomLevel.STUDIES, meta=item)
            s.add(d)
        return s, items.fieldnames

def save_csv(csv_file, worklist, _fieldnames=None):

    with open(csv_file, "w") as fp:

        fieldnames=_fieldnames or []
        for item in worklist:
            for k in item.meta.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        writer = csv.DictWriter(fp,
                                fieldnames=fieldnames,
                                extrasaction='ignore')
        writer.writeheader()

        for item in worklist:
            # Unicode!
            meta = {k: u"{}".format(v).encode("utf-8", errors='ignore') for k, v in item.meta.iteritems()}

            # meta = {k: unicode(v, errors='ignore').encode("utf-8", errors='ignore') for k, v in item.meta.iteritems()}
            writer.writerow(meta)


def report_extractions(dixel):

    raw_text = dixel.meta['Report Text']

    def find_it(k, expr):
        match = re.findall(expr, raw_text)
        if match:
            # logging.debug('{}: {}'.format(k, max(match)))
            dixel.meta[k] = max(match)

    extractions = {
        'lungrads':   'Lung-RADS .*[Cc]ategory (\d)',
        'radcat':     'RADCAT ?(\d)',
        'ctdi':       'CTDIvol = (\d*\.*\d*).*mGy',
        'dlp':        'DLP = (\d*\.*\d*).*mGy-cm',
        'lungrads_s': 'Lung-RADS .*[Cc]ategory \d-?([Ss])',
        'lungrads_c': 'Lung-RADS .*[Cc]ategory \d-?([Cc])',
        'current_smoker': '([Cc]urrent smoker)',
        'pack_years': '(\d+)[ -]pack[ -]year',
        'years_quit': 'quit(.*\d+) year[s?]'
    }

    for k, v in extractions.iteritems():
        find_it(k, v)

    return dixel


# Output all report data
def save_text_corpus(out_dir, worklist, num_subdirs=0):

    for item in worklist:

        if not item.meta.get('categories'):
            logging.warn('Skipping {} bc no categories'.format(item))
            continue

        # Clean up the report and anonymize

        # Sometimes montage uses html syntax
        # soup = BeautifulSoup(item.meta['Report Text'], "html.parser")
        # raw_text = soup.get_text()

        # Make it unicode explicitly
        raw_text = item.meta['Report Text'].decode('utf-8', 'ignore')

        # Anonymize and blind to RADCAT
        # 'Oliver' is unfortunately all over and not always flagged correctly as NP
        anon_text = re.sub(u"(^.* MD.*$|^.*MRN.*$|^.*DOS.*$|^.*RADCAT.*$|^.* Dr.*$|^.* NP.*$|^.* RN.*$|^.* RA.*$|^.*Oliver.*$|^Report created.*$)",
                    u"", raw_text, 0, re.M)

        try:
            anon_text = anon_text.encode("utf-8", errors='ignore')
        except UnicodeDecodeError:
            logging.error(anon_text)
            raise Exception('Cannot encode this report')

        # Each dixel report gets a file name with annotations for modality,
        # body part, and finding
        # out_dir/<study_oid>_study_region_finding.txt

        study_oid = orthanc_id(
            item.meta['PatientID'],
            item.meta['AccessionNumber'])
        suffix = "_".join(str(x) for x in item.meta['categories'])
        fn = study_oid + "+" + suffix + ".txt"

        if num_subdirs==0:
            path = out_dir
        elif num_subdirs==1:
            path = os.path.join(out_dir,
                                study_oid[0:2])
        elif num_subdirs==2:
            path = os.path.join(out_dir,
                                study_oid[0:2],
                                study_oid[2:4])

        if not os.path.exists(path):
            os.makedirs(path)
        full_path = os.path.join(path, fn)

        with open(full_path, 'w') as f:
            f.write(anon_text)


"""
Patients are identified as the SHA-1 hash of their PatientID tag (0010,0020).
Studies are identified as the SHA-1 hash of the concatenation of their PatientID tag (0010,0020) and their StudyInstanceUID tag (0020,000d).
Series are identified as the SHA-1 hash of the concatenation of their PatientID tag (0010,0020), their StudyInstanceUID tag (0020,000d) and their SeriesInstanceUID tag (0020,000e).
Instances are identified as the SHA-1 hash of the concatenation of their PatientID tag (0010,0020), their StudyInstanceUID tag (0020,000d), their SeriesInstanceUID tag (0020,000e), and their SOPInstanceUID tag (0008,0018).
  -- http://book.orthanc-server.com/faq/orthanc-ids.html
"""

def orthanc_id(PatientID, StudyInstanceUID, SeriesInstanceUID=None, SOPInstanceUID=None):
    if not SeriesInstanceUID:
        s = "|".join([PatientID, StudyInstanceUID])
    elif not SOPInstanceUID:
        s = "|".join([PatientID, StudyInstanceUID, SeriesInstanceUID])
    else:
        s = "|".join([PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID])

    h = sha1(s)
    d = h.hexdigest()
    return '-'.join(d[i:i+8] for i in range(0, len(d), 8))

# Accept a reference time and a +/i delta time str in the format "+/-#[s|m|h|d|w]"
# returns a datetime range (earliest, latest)
# ie, daterange("now", "1d")
def daterange(s_ref, s_delta, s_delta2=None):

    def mk_delta(s):
        m = re.search('^(?P<op>(\+|\-))(?P<count>\d+)(?P<units>(s|m|h|d|w))$', s)
        val = int(m.groupdict()['op'] + m.groupdict()['count'])
        if m.groupdict()['units'] == 's':
            td = timedelta(seconds=val)
        elif m.groupdict()['units'] == 'm':
            td = timedelta(minutes=val)
        elif m.groupdict()['units'] == 'h':
            td = timedelta(hours=val)
        elif m.groupdict()['units'] == 'd':
            td = timedelta(days=val)
        elif m.groupdict()['units'] == 'w':
            td = timedelta(weeks=val)
        else:
            raise()

        return td

    # TODO: does this work with "now"?
    ref = dateutil_parser.parse(s_ref)
    delta = mk_delta(s_delta)

    if s_delta2:
        delta2 = mk_delta(s_delta2)
    else:
        delta2 = - delta

    earliest = ref + delta
    latest = ref + delta2

    return earliest, latest

class Caching(object):

    @classmethod
    def pkl(cls, o, fn):
        logging.debug("Saving object")
        with open(fn, 'wb') as f:
            pickle.dump(o, f, -1)

    @classmethod
    def unpkl(cls, fn):
        logging.debug("Loading object")
        with open(fn, 'rb') as f:
            o = pickle.load(f)
            return o

    PICKLE_DIR = '.'

    def __init__(self, pkl, init_func=None, *init_args):
        self._init_func = init_func
        self._pkl = os.path.join(Caching.PICKLE_DIR, "{}.pkl".format(pkl))
        self._data = None
        self._init_args = init_args

    @property
    def data(self):
        if not self._data:
            try:
                self._data = self.unpkl(self._pkl)
            except:
                self._data = self._init_func(*self._init_args)
                self.pkl(self._data, self._pkl)
        return self._data


def test_hashing():

    ptid=   '80'
    stuid=  '14409.67140509640117601730783110182492517466'
    seruid= '14409.180696748118693976707516603316459807766'
    instuid='14409.251659350131093564476016562599266393167'
    id = orthanc_id(ptid, stuid, seruid, instuid)
    correct=  "c3a46d9f-20409d48-aee91522-34e3e1e9-958f34b2"
    assert( id==correct )


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_hashing()