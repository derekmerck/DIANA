"""
Prepare a DICOM tag set for ingestion into splunk:

- Standardize dates and times as datetime objects
- Identify a sensible creation datetime
- Flatten and simplify ContentSequences in the manner of Orthanc's 'simplify' parameter
- Add sensible defaults for missing station names and ctdi_vols in dose reports

"""

import logging, json, os
from ..smart_encode import SmartJSONEncoder
from .dicom_strings import dicom_strpdtime


def parse_timestamps(tags):

    # Convert DICOM Date/Times into ISO DateTimes
    try:
        t = dicom_strpdtime(tags['StudyDate'] + tags['StudyTime'])
        tags['StudyDateTime'] = t
    except KeyError:
        pass

    try:
        t = dicom_strpdtime(tags['SeriesDate'] + tags['SeriesTime'])
        tags['SeriesDateTime'] = t
    except KeyError:
        pass

    # Not all instances have ObservationDateTime
    try:
        t = dicom_strpdtime(tags['ObservationDateTime'])
        tags['ObservationDateTime'] = t
    except KeyError:
        pass

    # Not all instances have an InstanceCreationDate/Time
    try:
        t = dicom_strpdtime(tags['InstanceCreationDate'] + tags['InstanceCreationTime'])
        tags['InstanceCreationDateTime'] = t
    except KeyError:
        pass

    # We want to use InstanceCreationDate as the _time field, so create a sensible
    # value if it's missing
    if not tags.get('InstanceCreationDateTime'):
        if tags.get('SeriesDateTime'):
            tags['InstanceCreationDateTime'] = tags['SeriesDateTime']
        elif tags.get('StudyDateTime'):
            tags['InstanceCreationDateTime'] = tags['StudyDateTime']
        elif tags.get('ObservationDateTime'):
            tags['InstanceCreationDateTime'] = tags['ObservationDateTime']
        else:
            logger.warning('No creation date could be parsed from instance, series, study, or observation.')
            pass

    return tags

# This allows us to standardize how ctdi keys are included in dose reports.  They exist
# in Siemens reports, but are _not_ present on GE reports, which makes the data difficult
# to parse with Splunk
def normalize_ctdi_vol(tags):

    try:
        exposures = tags["X-Ray Radiation Dose Report"]["CT Acquisition"]

        for exposure in exposures:

            if "CT Dose" not in exposure:
                logger.debug("Normalizing missing CT Dose key")
                exposure["CT Dose"] = {'Mean CTDIvol': 0}
            else:
                # logger.debug("CT Dose key already exists!")
                pass

    except:
        pass

    return tags

# Make sure that a StationName is present or introduce a sensible alternative
def normalize_station_name(tags):

    if "StationName" not in tags:
        try:
            tags["StationName"] = tags["DeviceSerialNumber"]
        except:
            try:
                tags["StationName"] = tags["X-Ray Radiation Dose Report"]["Device Observer UID"]
            except:
                tags["StationName"] = "Unknown"
                logger.debug('No station name identifed')

    return tags


def simplify_content_sequence(tags):

    data = {}

    for item in tags["ContentSequence"]:

        # logger.debug('Item = ' + pformat(item))

        try:
            key = item['ConceptNameCodeSequence'][0]['CodeMeaning']
            type_ = item['ValueType']
            value = None
        except KeyError:
            logger.debug('No key or no type, returning')
            return

        if type_ == "TEXT":
            value = item['TextValue']
            # logger.debug('Found text value')

        elif type_ == "IMAGE":
            # "IMAGE" sometimes encodes a text UUID, sometimes a refsop
            try:
                value = item['TextValue']
            except KeyError:
                logger.debug('No text value for "IMAGE", returning')
                return

        elif type_ == "NUM":
            value = float(item['MeasuredValueSequence'][0]['NumericValue'])
            # logger.debug('Found numeric value')
        elif type_ == 'UIDREF':
            value = item['UID']
            # logger.debug('Found uid value')
        elif type_ == 'DATETIME':
            value = dicom_strpdtime(item['DateTime'])
            # logger.debug('Found date/time value')
        elif type_ == 'CODE':
            try:
                value = item['ConceptCodeSequence'][0]['CodeMeaning']
            except:
                value = "UNKNOWN"
            # logger.debug('Found coded value')
        elif type_ == "CONTAINER":
            value = simplify_content_sequence(item)
            # logger.debug('Found container - recursing')
        else:
            logger.debug("Unknown ValueType (" + item['ValueType'] + ")")

        if data.get(key):
            # logger.debug('Key already exists (' + key + ')')
            if isinstance(data.get(key), list):
                value = data[key] + [value]
                # logger.debug('Already a list, so appending')
            else:
                value = [data[key], value]
                # logger.debug('Creating a list from previous and current')

        data[key] = value

    return data

def simplify_structured_tags(tags):

    # Parse any structured data into simplified tag structure
    if tags.get('ConceptNameCodeSequence'):
        # There is structured data in here
        key = tags['ConceptNameCodeSequence'][0]['CodeMeaning']
        value = simplify_content_sequence(tags)

        t = dicom_strpdtime(tags['ContentDate'] + tags['ContentTime'])
        value['ContentDateTime'] = t

        del(tags['ConceptNameCodeSequence'])
        del(tags['ContentSequence'])
        del(tags['ContentDate'])
        del(tags['ContentTime'])

        tags[key] = value

    return tags


def dicom_clean_tags(tags):

    # Flatten content sequences
    tags = simplify_structured_tags(tags)

    # Convert timestamps to python datetimes
    tags = parse_timestamps(tags)

    # Deal with missing fields in ctdi_vol
    tags = normalize_ctdi_vol(tags)

    # Deal with unnamed stations
    tags = normalize_station_name(tags)

    # logger.info(pformat(tags))

    return tags

def test_simplify():

    dir = "tests/resources/dose"
    items = ["anon_dose"]

    for item in items:

        fn = "{}.json".format(item)
        fp = os.path.join(dir, fn)

        with open(fp) as f:
            tags = json.load(f)

        tags = dicom_clean_tags(tags)

        # Have to compare in dumped space b/c loader doesn't convert times back into times
        tag_str = json.dumps(tags, indent=3, cls=SmartJSONEncoder, sort_keys=True)

        fn = "{}.simple.json".format(item)
        fp = os.path.join(dir, fn)

        with open(fp) as f:
            simple_str = f.read()

        # print(tag_str)
        # print(simple_str)

        assert tag_str == simple_str

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_simplify()
