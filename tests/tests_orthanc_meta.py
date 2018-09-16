import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from diana.apis import Orthanc, orthanc_meta_extras, DicomFile, Dixel

def test_encoding():

    meta = {
        'PatientID':       "123456",
        'PatientName':     "DOE^JOHN^B",
        'PatientBirthDate': (datetime.now() - timedelta(days=20*365)).isoformat(),
        'PatientSex':      "M",
        'AccessionNumber': "ABCDEFG",
        'StudyDescription': "Medical imaging study",
        'StudyDateTime':    datetime.now().isoformat(),
        'Institution':      "Medical center"
    }

    item = Dixel(meta=meta)

    fkey = Fernet.generate_key()
    item.encode_data_sig(fkey)

    assert( item.meta.get('DataSignature') != meta )

    round_trip = item.decode_data_sig(fkey)

    assert( round_trip.items() <= meta.items() )


def test_api():
    """
    Requires additional UserData definitions in orthanc.json, use testing docker-compose dicom service

    $ docker-compose -f docker-compose/docker-compose.yml dicom start
    $ python3 orthanc_meta_extras.py

    """

    orthanc = Orthanc()
    orthanc.clear()
    d = DicomFile(location='resources/ab_ct').get('IM66', view='file')
    logging.debug(d.meta)
    d.set_metadata(submitting_site="MY_SITE")
    orthanc.put(d)
    e = orthanc.anonymize(d)

    assert e.meta.get('SubmittingSite') == "MY_SITE"
    assert e.meta.get('PartialPatientID') == "7275"

    fkey = Fernet.generate_key()
    orthanc.clear()
    d = DicomFile(location='resources/ab_ct').get('IM66', view='file')
    logging.debug(d.meta)
    d.set_metadata(submitting_site="MY_SITE", fkey=fkey)
    orthanc.put(d)
    e = orthanc.anonymize(d)

    assert e.meta.get('SubmittingSite') == "MY_SITE"
    assert e.meta.get('PartialPatientID') == "7275"

    out = e.decode_data_sig(fkey)
    assert out['PatientName'] == d.meta['PatientName']
    assert out['PatientID'] == d.meta['PatientID']



if __name__ == "__main__":


    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)

    test_encoding()
    test_api()