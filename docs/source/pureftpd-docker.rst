Ansible Role for PureFTPd in Docker
===================================

`Build
Status <https://travis-ci.org/derekmerck/ansible-pureftpd-docker>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Configure and run a
`Pure-FTPd <https://www.pureftpd.org/project/pure-ftpd>`__ server in a
Docker container.

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
-  `pexpect <https://pexpect.readthedocs.io>`__

Role Variables
--------------

Docker Image and Tag
~~~~~~~~~~~~~~~~~~~~

Always uses the hardened
`stilliard/docker-pure-ftpd <https://github.com/stilliard/docker-pure-ftpd>`__
image.

Docker Container Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   pftp_container_name:   "pftp"
   pftp_use_data_container: True
   pftp_data_dir:         "/data/ftp"
   pftp_port:             21
   pftp_public_host:      192.168.10.33  # TODO: Should be fqdn

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   pftp_service_user:     "pftp"
   pftp_service_password: "passw0rd!"

Example Playbook
----------------

.. code:: yaml

   - hosts: ftp_server
     roles:
        - derekmerck.pureftpd_docker

License
-------

MIT
