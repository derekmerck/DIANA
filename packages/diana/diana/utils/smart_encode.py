# Encodes datetime and hashes

import json, re, logging
from datetime import datetime, date
from jsmin import jsmin


def stringify(obj):
    if isinstance(obj, datetime) or isinstance(obj, date):
        return obj.isoformat()

    if hasattr(obj, 'hexdigest'):
        return obj.hexdigest()


class SmartJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        out = stringify(obj)
        if out:
            return out

        return json.JSONEncoder.default(self, obj)


def update_json_file(fp, data, dryrun=False):

    with open(fp, 'r') as f:
        content = f.read()

    new_content = update_json(content, data)

    if content != new_content:
        changed = True
        logging.debug("Updating json content")
        logging.debug(new_content)

        if not dryrun:
            with open(fp, 'w') as f:
                f.write(new_content)
    else:
        changed = False
        logging.debug("No changes to write")

    return changed, new_content


def update_json(content, data):
    # Handles dicts, strings, ints, bools

    for key, value in data.items():

        pattern = None
        old_value = None
        new_value = None
        new_str = None

        # Merge if its a group
        if isinstance(value, dict):

            pattern = r"\"{key}\" : (\{{.*?\}})".format(key=key)
            # logging.debug(pattern)
            match = re.search(pattern, content, re.DOTALL)

            old_str = match.group(1)
            # logging.debug("Found {}".format(old_str))

            # Strip comments
            clean_str = jsmin(old_str)
            old_value = json.loads(clean_str)
            new_value = {**old_value, **value}
            new_str = "\"{key}\" : {value}".format(
                key=key,
                value=json.dumps(new_value)
            )

        elif isinstance(value, str):

            pattern = r"\"{key}\" : (\".*?\")".format(key=key)
            # logging.debug(pattern)
            match = re.search(pattern, content, re.DOTALL)

            old_str = match.group(1)
            old_value = old_str
            new_value = value
            new_str = "\"{key}\" : \"{value}\"".format(
                key=key,
                value=new_value
            )

        elif isinstance(value, bool):

            pattern = r"\"{key}\" : ((true)|(false))".format(key=key)
            # logging.debug(pattern)
            match = re.search(pattern, content, re.DOTALL)

            old_str = match.group(1)
            old_value = old_str
            new_value = value
            new_str = "\"{key}\" : {value}".format(
                key=key,
                value=str(new_value).lower()
            )

        elif isinstance(value, int):

            pattern = r"\"{key}\" : (\d*)".format(key=key)
            # logging.debug(pattern)
            match = re.search(pattern, content, re.DOTALL)

            old_str = match.group(1)
            old_value = old_str
            new_value = value
            new_str = "\"{key}\" : {value}".format(
                key=key,
                value=str(new_value).lower()
            )

        else:
            raise TypeError("Do not know how to edit in json value of type {}".format(type(value)))

        if old_value != new_value:
                content = re.sub(pattern, new_str, content, flags=re.DOTALL)
                # logging.debug(content)

    return content


def test_update_json_file():

    fp0 = "tests/resources/configs/orthanc-src.json"
    fp1 = "tests/resources/configs/orthanc-updated.json"

    data = {
        'Name': "Baz",
        'DicomAet': 'BAZ',
        'RegisteredUsers': {'foo': 'bar'},
        'DicomModalities': {'spam': ['SPAM', 'locahost', 9999]},
        'SslEnabled': True,
        'DicomPort': 11112
    }

    chg0, content0 = update_json_file(fp0, data, dryrun=True)
    chg1, content1 = update_json_file(fp1, data, dryrun=True)

    assert chg0
    assert not chg1
    assert content0 == content1


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_update_json_file()
