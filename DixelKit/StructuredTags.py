import logging
# import requests
import json
from datetime import datetime
from pprint import pprint, pformat


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


# DICOM Date/Time format
def get_datetime(s):
    try:
        # GE Scanner aggregated dt format
        ts = datetime.strptime(s, "%Y%m%d%H%M%S")
    except ValueError:

        try:
            # Siemens scanners use a slightly different aggregated format with fractional seconds
            ts = datetime.strptime(s, "%Y%m%d%H%M%S.%f")

        except ValueError:
            logging.debug("Can't parse date time string: {0}".format(s))
            ts = datetime.now()

    return ts


def simplify_structured_tags(tags):

    data = {}

    for item in tags["ContentSequence"]:

        # logging.debug('Item = ' + pformat(item))

        try:
            key = item['ConceptNameCodeSequence'][0]['CodeMeaning']
            type_ = item['ValueType']
            value = None
        except KeyError:
            logging.debug('No key or no type, returning')
            return

        if type_ == "TEXT":
            value = item['TextValue']
            # logging.debug('Found text value')

        elif type_ == "IMAGE":
            # "IMAGE" sometimes encodes a text UUID, sometimes a refsop
            try:
                value = item['TextValue']
            except KeyError:
                logging.debug('No text value for "IMAGE", returning')
                return

        elif type_ == "NUM":
            value = float(item['MeasuredValueSequence'][0]['NumericValue'])
            # logging.debug('Found numeric value')
        elif type_ == 'UIDREF':
            value = item['UID']
            # logging.debug('Found uid value')
        elif type_ == 'DATETIME':
            value = get_datetime(item['DateTime'])
            # logging.debug('Found date/time value')
        elif type_ == 'CODE':
            try:
                value = item['ConceptCodeSequence'][0]['CodeMeaning']
            except:
                value = "UNKNOWN"
            # logging.debug('Found coded value')
        elif type_ == "CONTAINER":
            value = simplify_structured_tags(item)
            # logging.debug('Found container - recursing')
        else:
            logging.debug("Unknown ValueType (" + item['ValueType'] + ")")

        if data.get(key):
            # logging.debug('Key already exists (' + key + ')')
            if isinstance(data.get(key), list):
                value = data[key] + [value]
                # logging.debug('Already a list, so appending')
            else:
                value = [data[key], value]
                # logging.debug('Creating a list from previous and current')

        data[key] = value

    return data


def simplify_tags(tags):

    # Parse any structured data into simplified tag structure
    if tags.get('ConceptNameCodeSequence'):
        # There is structured data in here
        key = tags['ConceptNameCodeSequence'][0]['CodeMeaning']
        value = simplify_structured_tags(tags)

        t = get_datetime(tags['ContentDate'] + tags['ContentTime'])
        value['ContentDateTime'] = t

        del(tags['ConceptNameCodeSequence'])
        del(tags['ContentSequence'])
        del(tags['ContentDate'])
        del(tags['ContentTime'])

        tags[key] = value

    # Convert DICOM DateTimes into ISO DateTimes
    try:
        t = get_datetime(tags['StudyDate'] + tags['StudyTime'])
        tags['StudyDateTime'] = t
    except KeyError:
        pass

    try:
        t = get_datetime(tags['SeriesDate'] + tags['SeriesTime'])
        tags['SeriesDateTime'] = t
    except KeyError:
        pass

    # Not all instances have ObservationDateTime
    try:
        t = get_datetime(tags['ObservationDateTime'])
        tags['ObservationDateTime'] = t
    except KeyError:
        pass

    # Not all instances have an InstanceCreationDate
    try:
        t = get_datetime(tags['InstanceCreationDate'] + tags['InstanceCreationTime'])
        tags['InstanceCreationDateTime'] = t
    except KeyError:
        pass

    # We want to use InstanceCreationDate as the _time field, so put a sensible value in if it's missing
    if not tags.get('InstanceCreationDateTime'):
        if tags.get('SeriesDateTime'):
            tags['InstanceCreationDateTime'] = tags['SeriesDateTime']
        elif tags.get('StudyDateTime'):
            tags['InstanceCreationDateTime'] = tags['StudyDateTime']
        elif tags.get('ObservationDateTime'):
            tags['InstanceCreationDateTime'] = tags['ObservationDateTime']
        else:
            logging.warn('No creation date could be parsed from instance, series, study, or observation.')
            pass

    # logging.info(pformat(tags))

    return tags


# This allows us to standardize how ctdi keys are included in dose reports, they exist in Siemens reports
# but are _not_ present on GE machines, which makes the data difficult to parse with Splunk
def normalize_ctdi_tags(tags):

    try:
        exposures = tags["X-Ray Radiation Dose Report"]["CT Acquisition"]

        for exposure in exposures:

            if "CT Dose" not in exposure:
                logging.debug("Normalizing missing CT Dose key")
                exposure["CT Dose"] = {'Mean CTDIvol': 0}
            else:
                # logging.debug("CT Dose key already exists!")
                pass

    except:
        pass

    # Make sure that a StationName is present
    if "StationName" not in tags:
        try:
            tags["StationName"] = tags["DeviceSerialNumber"]
        except:
            try:
                tags["StationName"] = tags["X-Ray Radiation Dose Report"]["Device Observer UID"]
            except:
                logging.debug('No station name identifed')

    return tags


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    items = ["vir_tags2"]

    for item in items:

        with open('/Users/derek/Desktop/{0}.json'.format(item)) as f:
            tags = json.load(f)

        tags = simplify_tags(tags)
        tags = normalize_ctdi_tags(tags)

        with open('/Users/derek/Desktop/{0}-simple.json'.format(item), 'w') as f:
            json.dump(tags, f, indent=3, cls=DateTimeEncoder, sort_keys=True)

