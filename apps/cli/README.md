DIANA CLI
================

Derek Merck  
<derek_merck@brown.edu>  
Rhode Island Hospital and Brown University  
Providence, RI  
 
## `check-it.py`

Wrapper command-line tool for Splunk query.

```
> python3 check-it.py --query "index=dose_report" -e "-1d" -l now -i my_splunk -s secrets.yml
```

`secrets.yml` must have a section called "my_splunk" with keys suitable for creating
an Splunk instance that can accept the query.


## `dcm2im.py`

Wrapper command-line tool to convert pixels from a DICOM format file or directory
into a standard image format (png, jpg).

```
> python dcm2py.py -i im000001.dcm
```

## `index-it.py`

Wrapper command-line tool for pre-index caching and restoring.

```
$ python3 index-it.py --location /my_path --redis_service my_redis -s secrets.yml

$ python3 index-it.py -l /my_path -r my_redis -s secrets.yml restore --an abcxyz123 -d orthanc
```

`secrets.yml` must have a section called "my_redis" with keys suitable for creating
a Redis instance.

No python3 on a system that needs reindexed?  Docker to the rescue...

```
$ docker run -v /orthanc/db:/orthanc/db -it derekmerck/diana-worker /bin/bash
# scp server:/secrets.yml .
# python3 apps/cli/index-it.py -l /orthanc/db -r redis -s secrets.yml index -w orthanc
```

## `monitor-dose.py`

monitor-dose
Merck, Summer 2018

Wrapper to configure and run a DoseReportHarvester daemon.

```
$ python3 dose-monitor -q "gepacs" -j "dose_reports"
```


## `pull-it.py`

Wrapper command-line tool for Orthanc proxy retrieve from modality.

```
> python3 pull-it.py -accession XYZ -series "thin * brain -p my_proxy -d my_pacs -s secrets.yml
```

`secrets.yml` must have a section called "my_proxy" with keys suitable for creating
an Orthanc instance that knows about the remote "my_pacs".