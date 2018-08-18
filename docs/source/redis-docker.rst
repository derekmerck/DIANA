Ansible Role for Redis in Docker
================================

`Build Status <https://travis-ci.org/derekmerck/ansible-redis-docker>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Configure and run a `Redis <https://redis.io>`__ kv-store in a Docker
container.

Dependencies
------------

Galaxy Roles
~~~~~~~~~~~~

-  `geerlingguy.docker <https://github.com/geerlingguy/ansible-role-docker>`__
   to setup the docker environment
-  `geerlingguy.pip <https://github.com/geerlingguy/ansible-role-pip>`__
   to install Python reqs

Remote Node
~~~~~~~~~~~

-  `Docker <https://www.docker.com>`__
-  `docker-py <https://docker-py.readthedocs.io>`__

Role Variables
--------------

Docker Image and Tag
~~~~~~~~~~~~~~~~~~~~

Always uses the official `Redis <https://hub.docker.com/_/redis/>`__
image.

Set the Redis version tag.

.. code:: yaml

   redis_docker_image_tag:   "latest"

Docker Container Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   redis_container_name:     "redis"
   redis_port:               6379

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   redis_password:            "passw0rd!"

Example Playbook
----------------

.. code:: yaml

   - hosts: redis_server
     roles:
        - derekmerck.redis_docker

License
-------

MIT
