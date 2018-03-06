"""
A study level dixel may have report text associated with it.
"""

import os
import re
import logging

class Report(object):

    def __init__(self, text=None, dixel=None):
        if text:
            self.text = text
        elif dixel:
            self.text = dixel.meta['Report Text']
            extractions = self.extractions()
            for k,v in extractions.iteritems():
                dixel.meta[k]=v

    # Based on Lifespan/RIMI report template
    PHI_RE = re.compile(r'^.* MD.*$|^.*MRN.*$|^.*DOS.*$|^(?:.* )Dr.*$|^.* NP.*$|^.* RN.*$|^.* RA.*$|^.* PA.*$|^Report created.*$|^.*Signing Doctor.*$|^.*has reviewed.*$',re.M)
    FINDINGS_RE = re.compile(r'^.*discussed.*$|^.*nurse practitioner.*$|^.*physician assistant.*$|^.*virtual rad.*$', re.M | re.I)
    RADCAT_RE = re.compile(r'^.*RADCAT.*$', re.M)
    # https://stackoverflow.com/questions/16699007/regular-expression-to-match-standard-10-digit-phone-number
    PHONE_RE = re.compile(r'\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*', re.M)

    def anonymized(self):
        # Explicitly decode it
        raw_text = self.text.decode('utf-8', 'ignore')

        # Anonymize and blind to RADCAT
        anon_text = raw_text
        anon_text = Report.PHI_RE.sub(u"", anon_text, 0)
        anon_text = Report.FINDINGS_RE.sub(u"", anon_text, 0)
        anon_text = Report.RADCAT_RE.sub(u"", anon_text, 0)
        anon_text = Report.PHONE_RE.sub(u"(555) 555-5555 ", anon_text, 0)

        # if anon_text.lower().find('discussed')>0:
        #     logging.debug(anon_text)
        if anon_text.lower().find('oliver')>0:
            logging.debug(anon_text)

        try:
            anon_text = anon_text.encode("utf-8", errors='ignore')
        except UnicodeDecodeError:
            logging.error(anon_text)
            raise Exception('Cannot encode this report')

        return anon_text


    def write(self, save_dir, fn, anonymize=True, nesting=0):
        """
        File nesting may be 0, 1, 2 (Orthanc-style)
        """
        if not nesting:
            fp = save_dir
        elif nesting==1:
            fp = os.path.join(save_dir,
                                fn[0:2])
        elif nesting==2:
            fp = os.path.join(save_dir,
                                fn[0:2],
                                fn[2:4])
        else:
            raise ValueError('nesting param must be 0,1,2')

        if not os.path.exists(fp):
            os.makedirs(fp)
        fp = os.path.join(fp, fn)

        with open(fp, 'w') as f:
            if anonymize==True:
                text = self.anonymized()
            else:
                text = self.text
            f.write(text)

    def extractions(self):
        res = {}
        patterns = {
            'lungrads': 'Lung-RADS .*[Cc]ategory (\d)',
            'radcat': '(?i)RADCAT(?: Grade)?:? ?R?(\d)',
            'ctdi': 'CTDIvol = (\d*\.*\d*).*mGy',
            'dlp': 'DLP = (\d*\.*\d*).*mGy-cm',
            'lungrads_s': 'Lung-RADS .*[Cc]ategory \d-?([Ss])',
            'lungrads_c': 'Lung-RADS .*[Cc]ategory \d-?([Cc])',
            'current_smoker': '([Cc]urrent smoker)',
            'pack_years': '(\d+)[ -]pack[ -]year',
            'years_quit': 'quit(.*\d+) year[s?]'
        }

        for k, pattern in patterns.iteritems():
            match = re.findall(pattern, self.text)
            if match:
                # logging.debug('{}: {}'.format(k, max(match)))
                res[k] = max(match)
        return res


def test_report():
    with open('./tests/data/screening_rpt_anon.txt') as f:
        text = f.read()
    R = Report(text=text)

    # Extractions
    extractions = R.extractions()
    assert( extractions['radcat']=='4')
    assert( extractions['ctdi']=='2.72')

    # Saving
    save_dir = './tests'
    fn = "saved_report.txt"
    R.write(save_dir, fn, anonymize=True, nesting=1)
    tmp_fn = os.path.join(save_dir, 'sa', fn)
    assert( os.path.exists(tmp_fn) )

    with open(tmp_fn, 'r') as f:
        text = f.read()
        assert( text.find('Reading Resident MD: ABBBB CDDD, MD') < 0 )
        assert( text.find('Unchanged bilateral pulmonary nodules.') > 0 )

    # Clean up
    os.remove(tmp_fn)
    os.removedirs(os.path.join(save_dir, 'sa'))


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_report()