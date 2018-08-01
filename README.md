DICOM Analytics and Archive (DIANA)
=====================================

Derek Merck <derek_merck@brown.edu>  
Brown University and Rhode Island Hospital  
Winter 2018

Source: <https://www.github.com/derekmerck/DIANA>  
Documentation: <https://diana.readthedocs.io>


Dependencies
------------------

- Python 3.6
- Many [Python packages](packages/diana/requirements.txt)
- Many Ansible roles
- Many Docker containers


Overview
----------------

Hospital picture archive and communications systems (PACS) are not well suited for "big data" analysis.  It is difficult to identify and extract datasets in bulk, and moreover, high resolution data is often not even stored in the clinical systems.

**DIANA** is a [DICOM][] imaging informatics platform that can be attached to the clinical systems with a very small footprint, and then tuned to support a range of tasks from high-resolution image archival to cohort discovery to radiation dose monitoring.  It provides DICOM services, image data indexing, REST endpoints for scripting, and user access control through an amalgamation of free and free and open source (FOSS) systems.

[DICOM]: http://www.dicomstandard.org/


Installation
------------------

From pypi

```bash
pip3 install diana_plus
```

From source

```bash
$ git clone https://www.github.com/derekmerck/DIANA
$ pip install -e DIANA/packages/guidmint DIANA/packages/diana_plus
```


Organization
------------------

### diana package

- [utils](packages/diana/diana/utils) contains generic code with no references to diana-dixels or endpoints.
- [apis](packages/diana/diana/apis) contains get/put/handle functions for diana-dixels ("DICOM elements") and enpoints including [Orthanc][], [Montage][], [Splunk][], and files on disk.
- [daemon](packages/diana/diana/daemon) contains higher level tasks that compose multiple apis, like file and PACS monitoring, building secondary registries, and automatic deidentification and routing
- [star](packages/diana/diana/star) overloads apis with a celery-friendly wrapper function (something like `do-star(object, func, item)`)
  
[Orthanc]: https://orthanc.chu.ulg.ac.be
[Splunk]: https://www.splunk.com
[Montage]: https://www.nuance.com/healthcare/medical-imaging/mpower-clinical-analytics.html

  
### guidmint package

- [guidmint](packages/guidmint/guidmint) implements "mints" for flexible, reproducible anonymization, hashing schemes, and generating repeatable global uids and sham names/dobs

Can also be installed independly with `pip3 install guidmint`


### halibut package

- [halibut](packages/halibut/halibut) utility code for running Keras MobileNet classifiers on DICOM images (contributed by Ian Pan), additional requirements: [scipy][] and [keras][]

[scipy]: https://www.scipy.org
[keras]: https://keras.io


### apps

- [cli](apps/cli) contains command-line interface wrappers for common diana functions such as querying endpoints and saving images

- [diana-worker](apps/diana-worker) creates a diana+ celery worker ("diana*")

- [get-a-guid](apps/get-a-guid) is a REST API for `guidmint`

- [radcatr](apps/radcatr) is a simple TKL UI for basic report review and annotation

- study-manager is a simple, dynanmically configured DIANA front-end web portal for uploading and accessing available imaging resources from multiple trials and studiers.  A reference implementation is at <http://www.central-imaging.com/>.

- splunk-apps are apps and dashboards for informatics and data review:
   * DIANA-status: DIANA services introspection
   * RadRx: DICOM structured dose record monitoring
   * RadFlow: hl7 feed analysis and radiologist workload balancing
   * RadClf: Radiology report NLP classification
   
  
### tests

- [resources](tests/resources) includes some simple, anonymized DICOM files are included to test apis for upload, download,
caching, etc.
- [bench](tests/bench) provides a dev configuraqtion for testing with vagrant
- [unit](tests/unit) collection of short function verfications

See [tests/README.md]


The DIANA Service Stack
-----------------------

A simple DIANA stack requires two basic services:

- An Orthanc DICOM node for storing, pulling, proxying DICOM data
- A Splunk database for indexing available data

Additional services can be added:

- File handlers for reading/writing DCM, png, text, and csv files
- Persistent (Redis, csv) or in-memory caches for worklist
- Report handlers for extracting and anonymizing report data
- AI handlers for image analysis

A set of distributed "star" apis shadow the vanilla api names for building workflows with the celery async manager.  In this case, two additional services are required:

- A Redis messenger
- One or more "diana-workers" attached to various queues depending on their hardware (file or report access, machine learning hardware, proxying ip)

A basic stack can be configured with [Ansible][] using [Vagrant][] and the `testbench_playbook.yml` inventory.  

[Ansible]: https://www.ansible.com
[Vagrant]: https://www.vagrantup.com


### Ansible Roles

The `cirr_playbook.yml` is used with a private inventory to setup the Lifespan CIRR.
The `central_im_playbook.yml` is used to configure the Central Imaging archive.

Several roles for containerized services are available on [Ansible-Galaxy][] for these playbooks.

- [`derekmerck.diana-docker`](https://github.com/derekmerck/ansible-diana-docker)
- [`derekmerck.nginx-docker`](https://github.com/derekmerck/ansible-nginx-docker)
- [`derekmerck.orthanc-docker`](https://github.com/derekmerck/ansible-orthanc-docker)
- [`derekmerck.pureftpd-docker`](https://github.com/derekmerck/ansible-pureftpd-docker)
- [`derekmerck.redis-docker`](https://github.com/derekmerck/ansible-redis-docker)
- [`derekmerck.snappass-docker`](https://github.com/derekmerck/ansible-snappass-docker)
- [`derekmerck.splunk-docker`](https://github.com/derekmerck/ansible-splunk-docker)

[Ansible-Galaxy]: https://galaxy.ansible.com
  
### Docker xArch Images

[reDiana][] is a `docker-compose` file for setting up a Remote Embedded DIANA instance on a single-board computer, such as a Raspberry Pi.  It is particularly designed to be controlled through the [Resin.io][] IoT platform.

[reDiana]: https://github.com/derekmerck/reDiana
[resin.io]: https://resin.io

Several multi-architecture Docker images are available on [Docker Hub][] for these roles and compositions.

- [`derekmerck/orthanc`](https://github.com/derekmerck/docker-orthanc-xarch)
- [`derekmerck/conda`](https://github.com/derekmerck/docker-conda-xarch) and `derekmerck/keras-tf`
- [`derekmerck/diana`](https://github.com/derekmerck/docker-diana-xarch) and `derekmerck/diana-learn` (includes Halibut)

These containers are built for both `amd64` and `arm32v7` architectures on [travis-ci][] as part of testing, so they are always available from docker hub.
  
[Docker Hub]: https://hub.docker.io
[travis-ci]: https://travis-ci.org


Future Work
---------------

### muDIANA

(Planned) Extensions supporting high-throughput 3D microscopy data and image analytics and archive

- Monitoring for microscopy use logs
- Post-processing including ROI cropping and 3D CLAHE


License
---------------

[MIT](http://opensource.org/licenses/mit-license.html)
