Orthanc xArch Docker Image
==========================

`Build Status <https://travis-ci.org/derekmerck/docker-orthanc-xarch>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Build multi-arch `Orthanc <https://www.orthanc-server.com>`__ DICOM-node
Docker images for embedded systems. Includes ``libgdcm`` for plug-ins.

Use It
------

.. code:: bash

   $ docker run derekmerck/orthanc:latest

Build It
--------

This image is based on the ``resin/$ARCH-debian:stretch`` image.
`Resin.io <http://resin.io>`__ base images include a
`QEMU <https://www.qemu.org>`__ cross-compiler to facilitate building
images for low-power single-board computers on more powerful
Intel-architecture desktops and servers.

``docker-compose.yml`` contains build descriptions for all relevant
architectures.

``amd64``
~~~~~~~~~

.. code:: bash

   $ docker-compose build orthanc-amd64

Desktop computers/vms, `UP boards <http://www.up-board.org/upcore/>`__,
and the `Intel
NUC <https://www.intel.com/content/www/us/en/products/boards-kits/nuc.html>`__
are ``amd64`` devices. The appropriate image can be built and pushed
from `Travis CI <https://travis-ci.org>`__.

``arm32v7``
~~~~~~~~~~~

Most low-power single board computers such as the Raspberry Pi and
Beagleboard are ``arm32v7`` devices. Cross-compiling the appropriate
image takes too long on Travis CI, so it currently has to be tediously
cross-compiled and pushed locally.

.. code:: bash

   $ docker-compose build orthanc-arm32v7

Build Orthanc 1.3.2 (pre-threading)

.. code:: bash

   $ ORX_TAG="or132" ORX_BRANCH="Orthanc-1.3.2" docker-compose build orthanc-arm32v7

``arm64v8``
~~~~~~~~~~~

The `NVIDIA Jetson
TX2 <https://developer.nvidia.com/embedded/buy/jetson-tx2>`__ uses a
Tegra ``arm64v8`` cpu. The appropriate image can be built natively and
pushed from `Packet.io <https://packet.io>`__, using a brief tenancy on
a bare-metal Cavium ThunderX ARMv8 server.

.. code:: bash

   $ apt update && apt upgrade
   $ curl -fsSL get.docker.com -o get-docker.sh
   $ sh get-docker.sh 
   $ docker run hello-world
   $ apt install git python-pip
   $ pip install docker-compose
   $ git clone http://github.com/derekmerck/orthanc-xarch
   $ cd orthanc-xarch
   $ docker-compose build orthanc-arm64v8

Although `Resin uses Packet ARM servers to compile arm32
images <https://resin.io/blog/docker-builds-on-arm-servers-youre-not-crazy-your-builds-really-are-5x-faster/>`__,
the ThunderX does not implement the arm32 instruction set, so it `cannot
compile natively for the Raspberry
Pi <https://gitlab.com/gitlab-org/omnibus-gitlab/issues/2544>`__.

Manifest It
-----------

After building new images, call ``manifest-it.py`` to push updated
images and build the Docker multi-architecture service mappings.

.. code:: bash

   $ python3 manifest-it orthanc-xarch.manifest.yml

License
-------

MIT
