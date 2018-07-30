# DICOM Analytics and Archive

Derek Merck <derek_merck@brown.edu>  
Brown University and Rhode Island Hospital  
Winter 2018

Source: <https://www.github.com/derekmerck/diana>  
Documentation: <https://diana.readthedocs.io>  


## Overview

Hospital picture archive and communications systems (PACS) are not well suited for "big data" analysis.  It is difficult to identify and extract datasets in bulk, and moreover, high resolution data is often not even stored in the clinical systems.

**diana** is a [DICOM][] imaging informatics platform that can be attached to the clinical systems with a very small footprint, and then tuned to support a range of tasks from high-resolution image archival to cohort discovery to radiation dose monitoring.

**diana-star** is a celery queuing system with a diana api.  This provides a backbone for distributed task management.  The "star" suffix is in honor of the historical side-note of Matlab's Star-P parallel computing library.


## Dependencies

- Python 3.6
- Many Python packages