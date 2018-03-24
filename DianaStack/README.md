# The DIANA Service Stack

Derek Merck <derek_merck@brown.edu>  
Brown University and Rhode Island Hospital  
Winter 2018

<https://www.github.com/derekmerck/DIANA/tree/master/DianaStack> 


## Overview

The Diana Service Stack is a collection of Ansible roles and playbooks to create reproducible system architectures.  Most roles are implemented as docker containers.  Cornerstone roles include [orthanc][] (or [osimis]) for DICOM storage and Splunk Lite for data indexing and discovery.

The Diana Service Stack can be configured into various different assemblies according to need and resources. Example playbooks for Rhode Island Hospital's Clinical Imaging Research Registry (CIRR) and for the Clinical Trial Central Imaging Archive (CTCIA) are provided in the `examples` directory.


## Dependencies

### Python Package Requirements

- [Python][] 2.7.11+ for scripting
- [Ansible][] for service orchestration
- [pyyaml][]
- [jinja2][]

### External Requirements

- [Docker][] for service virtualization
- [Orthanc][] for DICOM storage and bridging DICOM to REST
- [Postgresql][] 9.5+ for scalable Orthanc backend
- [Splunk][] 6.6+ for data indexing

[Docker]:http://www.docker.com
[Orthanc]: https://orthanc.chu.ulg.ac.be
[Splunk]: https://www.splunk.com
[Postgresql]:http://www.postgresql.org
[Orthanc]:http://www.orthanc-server.com
[Python]:http://www.python.org
[pyyaml]:http://pyyaml.org
[jinja2]:http://jinja.pocoo.org
[ansible]:http://www.ansible.com


## Use Cases

### DICOM VNA and Router

1. Create an index role
2. Create a db role
3. Create n+m DICOM repo roles
   - n archive workers
   - m queues, muxes
4. Create an http reverse proxy role for archive workers
5. Create a monitor role: repo inventories -> index
6. Install the `diana_monitor` dashboards

Make a `splunkbase` folder in the `splunk` role and download and add any Splunkbase extensions that you need.  They will be automatically installed on the indexer instance.

In particular, the Diana Splunk Apps use:

- [hl7 Extension](https://splunkbase.splunk.com/app/3283/)
- [REST Modular Input](https://splunkbase.splunk.com/app/1546/)
- [Website Performance Monitor]()

Creating the index first allows the system to ship component logs directly to the index

### REST Head Uploads

Max file size is set to 8MB in `nginx`.  Most CTs are only .5MB, but some long scouts for panscans may be 4+MB uncompressed.


### PACS Crawling

1. Create an index role
2. Create a DICOM repo role
3. Register the repo with the PACS as a valid query source
4. Create a monitor role: proxied inventories -> index
6. Install the `diana_monitor` dashboards


### DIANA for Dose Management

1. Create an index role
2. Create a DICOM repo role
3. Create a monitor role: repo inventory/dose -> index
4. Point modality dose reports to the dose repo
5. Install the `dose_rx` dashboards


#### Reconciling Missing Data on Dose Reports

Occassionally the EHR will be unavailable to automatically assign accession numbers or protocols as the studies are performed.  For example, we recently lost LifeChart for 4 hours, and ended up with about 40 studies that had absent or hand-input improper accession numbers assigned.  Because the index assumes the accession numbers are correct, this can lead to missing studies in the summary information.

Reconciling this is somewhat complicated, but can be scripted.

index = Splunk gateway
dicom_node = Orthanc with structured dose reports
remote_bridge = Orthanc with access to the PACS where the updated accession numbers live


1. Extract the Study Instance UID of the bad reports from Splunk

```python
study_ids = index.DoQuery( "index=dose_reports | ..."" )
```

2. Ask the PACS for the updated accession numbers for those StudyInstanceUIDs.
```python
for study_id in study_ids:
  accessions.append( proxy.DoRemoteQuery( {"StudyInstanceUID": study_id} ) )
```

3. Modify each report in the DICOM node
```
For study_id, accession_num in zip( study_ids, accessions ):
  dicom_node.modify( {"StudyInstanceUID": study_id}, {"AccessionNumber": accession_num} )
```

4. Drop the bad reports from the indices
```
index.DoQuery( "index=dicom_series | ... | del" )
index.DoQuery( "index=dose_reports | ... | del" )
```

5. Re-index the modified files and update the dose registry
```
index.UpdateSeries( dicom_node )
index.UpdateDoseRegistry( dicom_node )
```


## HL7 Dashboards

1. Create an index role with a `mount_pt` directory
2. Point the HL7 feeds to log to flat text in `mount_pt`
3. Install the `hl7_flow` dashboards

## Notes

#### ssh-agent in Pycharm

Set agent a regular terminal, then share it with `eval`.

```
$ ssh-agent
$ agent-add
> [prompt for password]
$ eval `(ssh-agent)`
```

## License

MIT
