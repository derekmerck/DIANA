Remote Embedded DIANA Setup
===========================

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Setup a multi-arch `DIANA <https://github.com/derekmerck/diana>`__
DICOM-handler service on embedded systems.

Use It
------

.. code:: bash

   $ docker-compose up

When using Resin.io devices in “local mode” for development and testing,
you can also `direct the device’s Docker daemon
remotely <https://github.com/resin-io-playground/resinos-compose>`__.

.. code:: bash

   $ DOCKER_API_VERSION=1.22 DOCKER_HOST=tcp://device_ip:2375 docker-compose up -d

Docker Image Dependencies
-------------------------

-  `redis <https://hub.docker.com/_/redis/>`__
-  `derekmerck/orthanc <https://github.com/derekmerck/orthanc-xarch>`__
   – Suggested to use pre-threading Orthanc-1.3.2 tag until
   `orthanc97 <https://bitbucket.org/sjodogne/orthanc/issues/97/intermittent-peer-to-peer-send-failures-w>`__
   is addressed
-  `derekmerck/diana <https://github.com/derekmerck/diana-xarch>`__
-  `derekmerck/diana-learn <https://github.com/derekmerck/diana-xarch>`__

``diana-learn`` includes tensorflow and Keras, and is used for machine
learning configurations.

Supported Architectures
-----------------------

Tested on ``amd64`` virtual machines and ``arm32v7`` `Raspberry
Pi <https://www.raspberrypi.org>`__. Can be compiled for ``aarch64``,
but currently untested.

Dependencies are are all multi-architecture, so the image name alone is
typically sufficient to find the correct image when pushing to a range
of devices. When uploading via `Resin.io <https://resin.io>`__ for
Raspberry Pi, though, you need to add explicit “arm32v7” tags. Their
builder is ``aarch64`` and will look for an “arm64v8” tag by preference,
rather than the base image target architecture, as it should.

License
-------

MIT
