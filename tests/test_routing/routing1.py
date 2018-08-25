# Copy into {{ CONFIG_DIR }}/diana/routing/{{ orthanc_container_name}}.yml.
# DianaWatcher merges the routing tables and starts and monitors all observers.

from functools import partial
from diana.daemon import DianaEventType, DianaWatcher, ObservableOrthanc, ObservableDicomFile

orthanc_archive = ObservableOrthanc()
orthanc_queue   = ObservableOrthanc()
dcm_file        = ObservableDicomFile( location = '/tmp' )

routing = {

    (dcm_file, DianaEventType.INSTANCE_ADDED):
        partial(DianaWatcher.move, dest=orthanc_queue, remove=True),

    (dcm_file, DianaEventType.STUDY_ADDED):
        partial(DianaWatcher.unpack_and_put, dest=orthanc_queue, remove=True),

    (orthanc_queue, DianaEventType.INSTANCE_ADDED):
        partial(DianaWatcher.anonymize_and_move, dest=orthanc_queue, remove=True),

}