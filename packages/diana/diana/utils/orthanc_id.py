from hashlib import sha1

def orthanc_hash(PatientID: str, StudyInstanceUID: str, SeriesInstanceUID=None, SOPInstanceUID=None) -> sha1:
    if not SeriesInstanceUID:
        s = "|".join([PatientID, StudyInstanceUID])
    elif not SOPInstanceUID:
        s = "|".join([PatientID, StudyInstanceUID, SeriesInstanceUID])
    else:
        s = "|".join([PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID])
    return sha1(s.encode("UTF8"))


def orthanc_id(PatientID: str, StudyInstanceUID: str, SeriesInstanceUID=None, SOPInstanceUID=None) -> str:
    h = orthanc_hash(PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID)
    d = h.hexdigest()
    return '-'.join(d[i:i+8] for i in range(0, len(d), 8))
