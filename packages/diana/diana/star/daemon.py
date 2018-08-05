from .app import app
from celery import chain
from ..apis import Orthanc, Splunk
from ..utils.dicom import DicomLevel
from .tasks import do

# Divide these up into 2 parts, discovery, which is part of the beat, and copy, which is distributed/multiplexed in the beat

@app.task(name="index_series")
def index_series( archive, index, timerange=("-10m","now"), **kwargs ):

    archive = Orthanc(archive)
    index = Splunk(index)

    worklist = archive.find(
        { "timerange": timerange,
          "level": DicomLevel.SERIES
        }
    )

    splunk_index = "DicomSeries"
    available = index.find(
        { "timerange": timerange,
          "level": DicomLevel.SERIES,  # Returns Dx of this type
          "index": splunk_index,
          "host": archive.location
        }
    )

    copy = chain( do("get", view="tags", pattern="archive") |
                  do("put", index=splunk_index, host=archive.location, pattern=index) )

    new_items = worklist - available
    for item in new_items:
        copy(item)


@app.task
def index_dose_reports( archive, index, timerange=("-10m", "now"), **kwargs ):

    archive = Orthanc(archive)
    index = Splunk(index)

    worklist = index.find(
        {   "timerange": timerange,
            "index": "DicomSeries",
            "level": DicomLevel.SERIES,  # Returns Dx at this level
            "host": archive.location,
            "query": "Modality=SR and SeriesDescription=*DOSE*"
        }
    )

    splunk_index = "DoseReports"
    available = index.find(
        {   "timerange": timerange,
            "index": splunk_index,
            "level": DicomLevel.SERIES,  # Returns Dx at this level
            "host": archive.location,
            "q": "Modality=SR and SeriesDescription=*DOSE*"
        }
    )

    copy = chain( do("get", view="instance_tags", pattern=archive) |
                  do("put", index=splunk_index, host=archive.location, pattern=index) )

    new_items = worklist - available
    for item in new_items:
        copy(item)


@app.task(name="index_remote")
def index_remote( proxy, remote_aet, index, dcm_query=None, splunk_query=None, timerange=("-10m", "now"), **kwargs ):

    proxy = Orthanc(proxy)
    index = Splunk(index)

    worklist = proxy.remote_find(
        {"timerange": timerange,
         "level": DicomLevel.SERIES,
         "query": dcm_query
         },
        remote_aet
    )

    splunk_proxy_name = "{}modalities/{}".format( proxy.location, remote_aet )
    splunk_index = "RemoteSeries"
    available = index.find(
        { "timerange": timerange,
          "level": DicomLevel.SERIES,  # Returns Dx of this type
          "index": splunk_index,
          "host": splunk_proxy_name,
          "query": splunk_query
        }
    )

    copy = chain( do("get", view="instance_tags", pattern=proxy) |
                  do("put", index=splunk_index, host=splunk_proxy_name, pattern=index) )

    new_items = worklist - available
    for item in new_items:
        copy(item)

@app.task(name="route")
def route( source, dest, **kwargs ):

    source = Orthanc(source)

    current = 0
    done = False

    while not done:
        changes = source.changes( since=current, limit=10 )
        ret = source.requester.do_get('changes', params={ "since": current, "limit": 10 })

        for change in ret['Changes']:
            # We are only interested interested in the arrival of new instances
            if change['ChangeType'] == 'NewInstance':

                do(change['ID'], "send", peer=dest, level=DicomLevel.INSTANCES, remove=True, pattern=source)

                # source.send( change['ID'], dest, level=DicomLevel.INSTANCES ).get()
                # source.remove( change['ID'], level=DicomLevel.INSTANCES )

        current = ret['Last']
        done = ret['Done']

    source.clear( desc="exports" )
    source.clear( desc="changes" )




