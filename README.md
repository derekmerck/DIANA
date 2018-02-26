# DICOM Analytics and Archive (DIANA)

Derek Merck <derek_merck@brown.edu>  
Winter 2018

<https://www.github.com/derekmerck/DIANA>

# Includes

- DIANA-stack - Ansible service configuration
- DIANA-connect - Connectivity scripts and monitors
- DIANA-frontend - DIANA front end interface for trial data management
- DixelKit - DICOM element ("dixel") interconnectivity library
- GUIDMint - Clever anonymization rules for deidentification

# Dependencies

- Python 2.7
- Many extensions


## Overview

Hospital picture archive and communications systems (PACS) are not well suited for "big data" analysis.  It is difficult to identify and extract datasets in bulk, and moreover, high resolution data is often not even stored in the clinical systems.

**DIANA** is a [DICOM][] imaging informatics platform that can be attached to the clinical systems with a very small footprint, and then tuned to support a range of tasks from high-resolution image archival to cohort discovery to radiation dose monitoring.

It is similar to [XNAT][] in providing DICOM services, image data indexing, REST endpoints for scripting, and user access control.  It is dissimilar in that it is not a monolithic codebase, but an amalgamation of free and free and open source (FOSS) systems.  Indeed, XNAT can be setup as a component of DIANA.

[DICOM]: http://dicom.nema.org
[XNAT]:  http://www.xnat.org


## Components


### DIANA-services
Ansible scripts for reproducible configurations

* DICOM image archives and routing (Orthanc)
* data index and forwarding (Splunk)


### DIANA-apps
Splunk apps and dashboards for informatics and data review

* `status` (services introspection)
* [`rad_rx`](/apps/rad_rx) (DICOM SRDR)
* `workload` (hl7)


### DIANA-connect
Python gateway API's for scripting indexing or data transfer jobs.

* `update_index`
* `pacs_crawler`
* `montage_crawler`
* `find_studies` (identify image populations)
* `get_studies` (build secondary image registries)


### muDIANA
Extensions supporting high-throughput microscopy data and image analytics and archive

* Monitoring for Phenix Opera logs
* Read spreadsheets of data properties
* Post-processing including ROI cropping and 3D CLAHE
* Use disk compressed storage b/c of all the zeros
* get_samples Find sample cores in each well, extract ROI on pull



### Quick Start

Setup an image archive and a Splunk index.

```
$ ...
```


```


# diana-utils

## DIANA Connect and Monitor (d-mon)

## DIANA Trial Front End (d-tfe)

Provides a very simple front end html framework for listing available trial resources.

Built dynamically from a `services.yml` document.

## GUID-Mint (guid-mint)

## License

MIT

---

** GDCM has no rpm available for RedHat 6, but can be compiled 
following <http://gdcm.sourceforge.net/wiki/index.php/Compilation> and
<https://raw.githubusercontent.com/malaterre/GDCM/master/INSTALL.txt>

```bash
$ yum install cmake3 g++
$ git clone https://github.com/malaterre/GDCM
$ cd GDCM
$ mkdir build
$ cd build
$ cmake3 -D GDCM_BUILD_APPLICATIONS=true ..
$ make
$ make install
```

