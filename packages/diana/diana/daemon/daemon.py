from ..utils import DicomLevel


def index_series( archive, index, timerange=("-10m","now") ):

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
          "host": archive.host
        }
    )

    new_items = worklist - available
    copy_items(new_items, archive, index, splunk_index=splunk_index)


def index_dose_reports( archive, index, timerange=("-10m", "now") ):

    worklist = index.find(
        {   "timerange": timerange,
            "index": "DicomSeries",
            "level": DicomLevel.SERIES,  # Returns Dx at this level
            "host": archive.location,
            "Modality": "SR",
            "SeriesDescription": "*DOSE*"
        }
    )

    splunk_index = "DoseReports"
    available = index.find(
        { "timerange": timerange,
          "level": DicomLevel.SERIES,  # Returns Dx of this type
          "index": splunk_index,
          "host": archive.host
        }
    )


    new_items = worklist - available
    copy_items(new_items, archive, index, splunk_index=splunk_index)


def index_remote_series( proxy, remote_aet, index, dcm_query=None, splunk_query=None, timerange=("-10m", "now") ):

    worklist = proxy.remote_find(
        {"timerange": timerange,
         "level": DicomLevel.SERIES,
         "query": dcm_query
         },
        remote_aet
    )

    splunk_index = "RemoteSeries"
    available = index.find(
        { "timerange": timerange,
          "level": DicomLevel.SERIES,  # Returns Dx of this type
          "index": "{}-{}".format(remote_aet, proxy.host),
          "host": proxy.host,
          "splunk_query": splunk_query
          }
    )

    new_items = worklist - available
    copy_items(new_items, proxy, index, splunk_index=splunk_index)


def route( source, dest, **kwargs ):

    current = 0
    done = False

    while not done:
        changes = source.changes( since=current, limit=10 )
        ret = source.requester.do_get('changes', params={ "since": current, "limit": 10 })

        for change in ret['Changes']:
            # We are only interested interested in the arrival of new instances
            if change['ChangeType'] == 'NewInstance':
                source.send( change['ID'], dest, level=DicomLevel.INSTANCES ).get()
                source.remove( change['ID'], level=DicomLevel.INSTANCES )

        current = ret['Last']
        done = ret['Done']

    source.changes( clear=True )
    source.exports( clear=True )




