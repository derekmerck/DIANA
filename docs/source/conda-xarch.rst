Conda xArch Docker Image
========================

`Build Status <https://travis-ci.org/derekmerck/docker-conda-xarch>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Build multi-arch Conda and Keras-TF Python Docker images for embedded
systems.

Conda on Arm
------------

The official arm32
`MiniConda <https://repo.continuum.io/miniconda/Miniconda-3.16.0-Linux-armv7l.sh>`__
is Python 2 from 2015. These images use
`BerryConda <https://github.com/jjhelmus/berryconda>`__ compiled by
jjhelmus. He also explains how to build a JetsonConda in the
`Conda/Constructor <https://github.com/conda/constructor>`__ repo.\*

   \*Need tdd ``libconda`` to the package manifest.

The official ``arm32`` tensorflow wheels are available as `nightly build
artifacts <http://ci.tensorflow.org/view/Nightly/>`__. The wheel name
for the python3 build has to be manipuated to remove the platform
restriction tags. NVIDIA provides a recent `tensorflow wheel for their
Jetson
TXs <https://devtalk.nvidia.com/default/topic/1031300/tensorflow-1-8-wheel-with-jetpack-3-2-/>`__.

Use It
------

.. code:: bash

   $ docker run derekmerck/conda:py2
   $ docker run derekmerck/keras-tf:py2

   $ docker run derekmerck/conda:latest
   $ docker run derekmerck/keras-tf:latest

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

   $ docker-compose build conda-py2-amd64 keras-tf-py2-amd64
   $ docker-compose build conda-py3-amd64 keras-tf-py3-amd64

Desktop computers/vms, `UP boards <http://www.up-board.org/upcore/>`__,
and the `Intel
NUC <https://www.intel.com/content/www/us/en/products/boards-kits/nuc.html>`__
are ``amd64`` devices. The appropriate image can be built and pushed
from `Travis CI <https://travis-ci.org>`__.

``arm32v7``
~~~~~~~~~~~

Most low-power single board computers such as the Raspberry Pi and
Beagleboard are ``arm32v7`` devices. Appropriate images can be
cross-compiled and pushed from Travis CI.

.. code:: bash

   $ docker-compose build conda-py2-arm32v7 keras-tf-py2-arm32v7
   $ docker-compose build conda-py3-arm32v7 keras-tf-py3-arm32v7

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
   $ git clone http://github.com/derekmerck/conda-xarch
   $ cd conda-xarch
   $ docker-compose build conda3-arm64v8

Although `Resin uses Packet ARM servers to compile arm32
images <https://resin.io/blog/docker-builds-on-arm-servers-youre-not-crazy-your-builds-really-are-5x-faster/>`__,
the available ThunderX does not implement the arm32 instruction set, so
it `cannot compile natively for the Raspberry
Pi <https://gitlab.com/gitlab-org/omnibus-gitlab/issues/2544>`__.

Manifest It
-----------

After building new images, call ``manifest-it.py`` to push updated
images and build the Docker multi-architecture service mappings.

.. code:: bash

   $ python3 manifest-it conda-xarch.manifest.yml

License
-------

MIT
