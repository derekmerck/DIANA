# DICOM Analytics and Archive (DIANA)

Derek Merck <derek_merck@brown.edu>  
Brown University and Rhode Island Hospital  
Winter 2018

<https://www.github.com/derekmerck/DIANA>

## Includes

- DIANA-stack - Flexible Ansible service configuration
- DIANA-connect - Connectivity and monitoring scripts
- DIANA-frontend - Simple DIANA front end interface for trial data management
- DixelKit - DICOM element ("dixel") service interface library (Orthanc, Montage, Splunk)
- GUIDMint - Clever anonymization and hashing rules for subject deidentification
- RadRX - Splunk app for CT dose monitoring

## Dependencies

- Python 2.7
- Many extensions


## Overview

Hospital picture archive and communications systems (PACS) are not well suited for "big data" analysis.  It is difficult to identify and extract datasets in bulk, and moreover, high resolution data is often not even stored in the clinical systems.

**DIANA** is a [DICOM][] imaging informatics platform that can be attached to the clinical systems with a very small footprint, and then tuned to support a range of tasks from high-resolution image archival to cohort discovery to radiation dose monitoring.

It is similar to [XNAT][] in providing DICOM services, image data indexing, REST endpoints for scripting, and user access control.  It is dissimilar in that it is not a monolithic codebase, but an amalgamation of free and free and open source (FOSS) systems.  Indeed, XNAT can be setup as a component of DIANA.

[DICOM]: http://dicom.nema.org
[XNAT]:  http://www.xnat.org


## Components


### DIANA-stack
Ansible scripts for reproducible configurations

* DICOM image archives and routing (Orthanc)
* data index and forwarding (Splunk)


### DIANA-connect
Python gateway API's for scripting indexing or data transfer jobs.

* `update_index`
* `pacs_crawler`
* `montage_crawler`
* `find_studies` (identify image populations)
* `get_studies` (build secondary image registries)


### DIANA-frontend

Provides a very simple front end html framework for listing available trial resources.

Built dynamically from a `services.yml` document.


### DIANA-splunk
Splunk apps and dashboards for informatics and data review

* DIANA-status (DIANA services introspection)
* [rad_rx](/apps/rad_rx) (DICOM SRDR)
* workload (hl7)


### DixelKit

Tools for working with arbitrary representations of DICOM objects (level, tags, file data)


### GUIDMint


### muDIANA
Extensions supporting high-throughput microscopy data and image analytics and archive

* Monitoring for Phenix Opera logs
* Read spreadsheets of data properties
* Post-processing including ROI cropping and 3D CLAHE
* Use disk compressed storage b/c of all the zeros
* get_samples Find sample cores in each well, extract ROI on pull


## License

MIT

