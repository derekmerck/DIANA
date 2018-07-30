# Encodes datetime and hashes

import json
from datetime import datetime, date


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