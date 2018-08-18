Ansible Role for DIANA in Docker
================================

`Build Status <https://travis-ci.org/derekmerck/ansible-diana-docker>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Configure and run a `DIANA <https://github.com/derekmerck/DIANA>`__
DICOM handler node in a Docker container.

Dependencies
------------

Galaxy Roles
~~~~~~~~~~~~

-  `geerlingguy.docker <https://github.com/geerlingguy/ansible-role-docker>`__
   to setup the docker environment
-  `geerlingguy.pip <https://github.com/geerlingguy/ansible-role-pip>`__
   to install Python reqs
-  `derekmerck.redis-docker <https://github.com/derekmerck/ansible-redis-docker>`__
   for Redis backend

Remote Node
~~~~~~~~~~~

-  `Docker <https://www.docker.com>`__
-  `docker-py <https://docker-py.readthedocs.io>`__

Role Variables
--------------

Docker Image and Tag
~~~~~~~~~~~~~~~~~~~~

Use the ``derekmerck/diana-learn`` image for classification.

.. code:: yaml

   diana_docker_image:         derekmerck/diana

Docker Container Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   diana_container_name:        diana-worker

Redis Backend Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   diana_redis_container_name:  redis
   diana_redis_host:            "{{ dockerhost_ip }}"
   diana_redis_port:            6379
   diana_redis_password:        "passw0rd!"
   diana_broker_db:             1
   diana_result_db:             2

Example Playbook
----------------

.. code:: yaml

   - hosts: diana_worker
     roles:
        - derekmerck.diana_docker

License
-------

MIT
