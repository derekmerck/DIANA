DICOM Analytics and Archive (DIANA)
===================================

| Derek Merck derek_merck@brown.edu
| Brown University and Rhode Island Hospital
| Winter 2018

| Source: https://www.github.com/derekmerck/DIANA
| Documentation: https://diana.readthedocs.io

Overview
--------

Hospital picture archive and communications systems (PACS) are not well
suited for "big data" analysis. It is difficult to identify and extract
datasets in bulk, and moreover, high resolution data is often not even
stored in the clinical systems.

**DIANA** is a `DICOM <http://dicom.nema.org>`__ imaging informatics
platform that can be attached to the clinical systems with a very small
footprint, and then tuned to support a range of tasks from
high-resolution image archival to cohort discovery to radiation dose
monitoring.

It is similar to `XNAT <http://www.xnat.org>`__ in providing DICOM
services, image data indexing, REST endpoints for scripting, and user
access control. It is dissimilar in that it is not a monolithic
codebase, but an amalgamation of free and free and open source (FOSS)
systems. Indeed, XNAT can be setup as a component of DIANA.

Dependencies
------------

-  Python 2.7
-  Many extensions, see individual packages

Components
----------

DIANA-stack
~~~~~~~~~~~

Ansible scripts for flexible, reproducible DICOM service configurations.

-  DICOM image archives and routing (Orthanc)
-  Data indexing and forwarding (Splunk)

DIANA-connect
~~~~~~~~~~~~~

Python scripts for data monitoring and transfer jobs.

-  Update data indices with DICOM tag information
-  Monitor available studies in PACS
-  Build secondary image registries
-  Identify image populations
-  Automatic deidentification

DIANA-frontend
~~~~~~~~~~~~~~

A simple, dynanmically configured DIANA front-end html interface for
accessing available imaging trial resources.

Reference implementation at http://www.centralimaging.com/

DIANA-splunk
~~~~~~~~~~~~

Splunk apps and dashboards for informatics and data review

-  DIANA-status: DIANA services introspection
-  RadRx: DICOM structured dose record monitoring
-  RadFlow: hl7 feed analysis and radiologist workload balancing
-  RadClf: Radiology report NLP classification

DixelKit
~~~~~~~~

DICOM element ("dixel") wrapper classes for for
`Orthanc <https://orthanc.chu.ulg.ac.be>`__,
`Montage <https://www.nuance.com/healthcare/medical-imaging/mpower-clinical-analytics.html>`__,
`Splunk <https://www.splunk.com>`__, and files on disk.

GUIDMint
~~~~~~~~

Flexible, reproducible anonymization and hashing schemes and canonical
ID server.

muDIANA
~~~~~~~

(Planned) Extensions supporting high-throughput microscopy data and
image analytics and archive

-  Monitoring for microscopy use logs
-  Post-processing including ROI cropping and 3D CLAHE

License
-------

MIT
