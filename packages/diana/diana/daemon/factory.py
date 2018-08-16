# Pattern objects can be instantiated through a factory, however, the factory
# has to import relevant class types into "globals"

from ..apis import Orthanc, Redis, DicomFile, Splunk
from .watcher import ObservableOrthancProxy, ObservableOrthanc, ObservableDicomFile

def factory(**pattern):
    class_name = pattern.get('class')
    del(pattern['class'])
    _cls = globals()[class_name]
    return _cls(**pattern)
