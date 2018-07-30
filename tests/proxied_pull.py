
service_cfg = "secrets/lifespan_services.yml"

import logging, yaml
from celery import chain
from diana.star.apis import Orthanc, DicomFile, Dixel
from diana.star.tasks import do
from diana.utils import DicomLevel

# local
def pull_and_send(item: Dixel, source: Orthanc, dest: str):

    item = source.find_item( item, retrieve=True )
    item = source.anonymize( item, remove=True )
    source.send( item, peer=dest )

# star chain
def pull_and_send_star(item, source, dest):

    f = chain( do.s( item, "find_item", pattern=source.pattern, retrieve=True ) |
           do.s( "anonymize", pattern=source.pattern, remove=True ) |
           do.s( "send", pattern=source.pattern, peer=dest ) )
    return f


def pull_and_save(item: Dixel, source: Orthanc, dest: DicomFile):

    item = source.find_item(item, retrieve=True)
    item = source.anonymize(item, remove=True)
    item = source.get(item, level=item.level, view="file")
    dest.put( item )

def pull_and_save_star(item: Dixel, source: Orthanc, dest: DicomFile):

    f = chain( do.s( item, "find_item", pattern=source.pattern, retrieve=True ) |
           do.s( "anonymize", pattern=source.pattern, remove=True ) |
           do.s( "get", pattern=source.pattern, view="file" ) |
           do.s( "put", pattern=dest ) )
    return f




