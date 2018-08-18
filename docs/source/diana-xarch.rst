DIANA xArch Docker Image
========================

`Build Status <https://travis-ci.org/derekmerck/docker-diana-xarch>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Build multi-arch
`DIANA <https://github.com/derekmerck/diana@diana-star>`__ and
DIANA-Learn Python Docker images for embedded systems.

Use It
------

.. code:: bash

   $ docker run derekmerck/diana:latest    # (amd64, arm32v7, arm64v8)
   $ docker run derekmerck/diana:learn     # (learn-amd64, learn-arm32v7, learn-arm64v8)
   $ docker run derekmerck/diana:movidius  # (movidius-arm32v7)

Build It
--------

This image uses system python and the ``resin/$ARCH-debian:stretch``
image. `Resin.io <http://resin.io>`__ base images include a
`QEMU <https://www.qemu.org>`__ cross-compiler to facilitate building
images for low-power single-board computers on more powerful
Intel-architecture desktops and servers.

``docker-compose.yml`` contains build descriptions for all relevant
architectures.

``amd64``
~~~~~~~~~

.. code:: bash

   $ docker-compose build diana-amd64

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

   $ docker-compose build diana-arm32v7 diana-movidius-arm32v7

The official ``arm32`` tensorflow wheels are available from pypi or as
`nightly build artifacts <http://ci.tensorflow.org/view/Nightly/>`__.
The wheel name for the python 3.4 build has to be manipuated to remove
the platform restriction tags in order to install on 3.5 or 3.6.

The `Intel Movidius <https://www.movidius.com>`__ NPU drivers from the
`NCSDK v2.0 <https://github.com/movidius/ncsdk>`__ are available in the
``diana:movidius`` tag. Only the toolkit itself is installed, tensorflow
is from pypi and `caffe <http://caffe.berkeleyvision.org>`__ must be
installed separately if needed.

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
   $ git clone http://github.com/derekmerck/diana-xarch@system_python
   $ cd orthanc-xarch
   $ docker-compose build diana-arm64v8
   $ docker-compose build diana-learn-arm64v8
   $ python3 manifest-it.py diana-xarch.manifest.yml

Although `Resin uses Packet ARM servers to compile arm32
images <https://resin.io/blog/docker-builds-on-arm-servers-youre-not-crazy-your-builds-really-are-5x-faster/>`__,
the available ThunderX does not implement the arm32 instruction set, so
it `cannot compile natively for the Raspberry
Pi <https://gitlab.com/gitlab-org/omnibus-gitlab/issues/2544>`__.

NVIDIA provides a recent `tensorflow wheel for their Jetson
TXs <https://devtalk.nvidia.com/default/topic/1031300/tensorflow-1-8-wheel-with-jetpack-3-2-/>`__.

Manifest It
-----------

After building new images, call ``manifest-it.py`` to push updated
images and build the Docker multi-architecture service mappings.

.. code:: bash

   $ python3 manifest-it diana-xarch.manifest.yml

License
-------

MIT
