# Pattern objects can be instantiated through a factory, however, the factory
# has to import relevant class types into "globals"

from . import Orthanc, Redis, DicomFile, Splunk


def factory(**pattern):
    class_name = pattern.get('class')
    del(pattern['class'])
    _cls = globals()[class_name]
    return _cls(**pattern)
