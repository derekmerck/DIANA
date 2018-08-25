DICOM Analytics and Archive (DIANA)
===================================

| Derek Merck derek_merck@brown.edu
| Brown University and Rhode Island Hospital
| Winter 2018

| Source: https://www.github.com/derekmerck/DIANA
| Documentation: https://diana.readthedocs.io

Dependencies
------------

-  Python 3.6
-  Many `Python packages <conda_env.yml>`__
-  Many `Ansible roles <#ansible-roles>`__
-  Many `Docker containers <#docker-images>`__

Overview
--------

Hospital picture archive and communications systems (PACS) are not well
suited for “big data” analysis. It is difficult to identify and extract
datasets in bulk, and moreover, high resolution data is often not even
stored in the clinical systems.

**DIANA** is a `DICOM <http://www.dicomstandard.org/>`__ imaging
informatics platform that can be attached to the clinical systems with a
very small footprint, and then tuned to support a range of tasks from
high-resolution image archival to cohort discovery to radiation dose
monitoring. It provides DICOM services, image data indexing, REST
endpoints for scripting, and user access control through an amalgamation
of free and free and open source (FOSS) systems.

Installation
------------

From pypi:

.. code:: bash

   pip3 install diana_plus

From source:

.. code:: bash

   $ git clone https://www.github.com/derekmerck/DIANA
   $ pip install -e DIANA/packages/guidmint DIANA/packages/diana

Organization
------------

diana package
~~~~~~~~~~~~~

-  `utils <packages/diana/diana/utils>`__ contains generic code with no
   references to diana-dixels or endpoints.
-  `apis <packages/diana/diana/apis>`__ contains get/put/handle
   functions for diana-dixels (“DICOM elements”) and enpoints including
   `Orthanc <https://orthanc.chu.ulg.ac.be>`__,
   `Montage <https://www.nuance.com/healthcare/medical-imaging/mpower-clinical-analytics.html>`__,
   `Splunk <https://www.splunk.com>`__, and files on disk.
-  `daemon <packages/diana/diana/daemon>`__ contains higher level tasks
   that compose multiple apis, like file and PACS monitoring, building
   secondary registries, and automatic deidentification and routing
-  `star <packages/diana/diana/star>`__ overloads apis with a
   celery-friendly wrapper function (something like
   ``do-star(object, func, item)``)

guidmint package
~~~~~~~~~~~~~~~~

-  `guidmint <packages/guidmint>`__ implements “mints” for flexible,
   reproducible anonymization, hashing schemes, and generating
   repeatable global uids and sham names/dobs

Can also be installed independently with ``pip3 install guidmint``

halibut package
~~~~~~~~~~~~~~~

-  `halibut <packages/halibut>`__ utility code for running Keras
   MobileNet classifiers on DICOM images (contributed by Ian Pan),
   additional requirements: `scipy <https://www.scipy.org>`__ and
   `keras <https://keras.io>`__

apps
~~~~

-  `cli <apps/cli>`__ contains command-line interface wrappers for
   common diana functions such as querying endpoints and saving images

-  `diana-worker <apps/diana-worker>`__ creates a diana+ celery worker
   ("diana*")

-  `get-a-guid <apps/get-a-guid>`__ is a REST API for ``guidmint``

-  `radcatr <apps/radcatr>`__ is a simple TKL UI for basic report review
   and annotation

-  study-manager is a simple, dynanmically configured DIANA front-end
   web portal for uploading and accessing available imaging resources
   from multiple trials and studiers. A reference implementation is at
   http://www.central-imaging.com/.

-  splunk-apps are apps and dashboards for informatics and data review:

   -  DIANA-status: DIANA services introspection
   -  RadRx: DICOM structured dose record monitoring
   -  RadFlow: hl7 feed analysis and radiologist workload balancing
   -  RadClf: Radiology report NLP classification

tests
~~~~~

-  `resources <tests/resources>`__ includes some simple, anonymized
   DICOM files are included to test apis for upload, download, caching,
   etc.
-  `bench <tests/bench>`__ provides a dev configuraqtion for testing
   with vagrant
-  `unit <tests/unit>`__ collection of short function verfications

See `tests <tests>`__

The DIANA Service Stack
-----------------------

A simple DIANA stack requires two basic services:

-  An Orthanc DICOM node for storing, pulling, proxying DICOM data
-  A Splunk database for indexing available data

Additional services can be added:

-  File handlers for reading/writing DCM, png, text, and csv files
-  Persistent (Redis, csv) or in-memory caches for worklist
-  Report handlers for extracting and anonymizing report data
-  AI handlers for image analysis

A set of distributed “star” apis shadow the vanilla api names for
building workflows with the celery async manager. In this case, two
additional services are required:

-  A Redis messenger
-  One or more “diana-workers” attached to various queues depending on
   their hardware (file or report access, machine learning hardware,
   proxying ip)

A basic stack can be configured with
`Ansible <https://www.ansible.com>`__ using
`Vagrant <https://www.vagrantup.com>`__ and the
``testbench_playbook.yml`` inventory.

Ansible Roles
~~~~~~~~~~~~~

The ``cirr_playbook.yml`` is used with a private inventory to setup the
Lifespan CIRR. The ``central_im_playbook.yml`` is used to configure the
Central Imaging archive.

Several roles for containerized services are available on
`Ansible-Galaxy <https://galaxy.ansible.com>`__ for these playbooks.

-  ```derekmerck.diana-docker`` <https://github.com/derekmerck/ansible-diana-docker>`__
-  ```derekmerck.nginx-docker`` <https://github.com/derekmerck/ansible-nginx-docker>`__
-  ```derekmerck.orthanc-docker`` <https://github.com/derekmerck/ansible-orthanc-docker>`__
-  ```derekmerck.pureftpd-docker`` <https://github.com/derekmerck/ansible-pureftpd-docker>`__
-  ```derekmerck.redis-docker`` <https://github.com/derekmerck/ansible-redis-docker>`__
-  ```derekmerck.snappass-docker`` <https://github.com/derekmerck/ansible-snappass-docker>`__
-  ```derekmerck.splunk-docker`` <https://github.com/derekmerck/ansible-splunk-docker>`__

Docker Images
~~~~~~~~~~~~~

`reDiana <https://github.com/derekmerck/reDiana>`__ is a
``docker-compose`` file for setting up a Remote Embedded DIANA instance
on a single-board computer, such as a Raspberry Pi. It is particularly
designed to be controlled through the `Resin.io <https://resin.io>`__
IoT platform.

Several multi-architecture Docker images are available on `Docker
Hub <https://hub.docker.io>`__ for these roles and compositions.

-  ```derekmerck/orthanc`` <https://github.com/derekmerck/docker-orthanc-xarch>`__
-  ```derekmerck/conda`` <https://github.com/derekmerck/docker-conda-xarch>`__
   and ``derekmerck/keras-tf``
-  ```derekmerck/diana`` <https://github.com/derekmerck/docker-diana-xarch>`__
   and ``derekmerck/diana-learn`` (includes Halibut)

These containers are built for both ``amd64`` and ``arm32v7``
architectures on `travis-ci <https://travis-ci.org>`__ as part of
testing, so they are always available from docker hub.

Future Work
-----------

muDIANA
~~~~~~~

(Planned) Extensions supporting high-throughput 3D microscopy data and
image analytics and archive

-  Monitoring for microscopy use logs
-  Post-processing including ROI cropping and 3D CLAHE

License
-------

`MIT <http://opensource.org/licenses/mit-license.html>`__
