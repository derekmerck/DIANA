Build a Python3 JetsonConda distro
==================================

.. code:: bash

   docker build -t jc-build-im . \
   && docker run --name jc-build -d jc-build-im \
   && docker cp jc-build:/JetsonConda-0.2.4-Linux-aarch64.sh . \
   && docker stop jc-build \
   && docker rm jc-build
