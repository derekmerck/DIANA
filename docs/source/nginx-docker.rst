Ansible Role for Nginx in Docker
================================

`Build Status <https://travis-ci.org/derekmerck/ansible-nginx-docker>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Configure and run a `Nginx <https://https://www.nginx.com>`__ web server
with reverse proxying in a Docker container.

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

Always uses the official `Nginx <https://hub.docker.com/_/nginx/>`__
image.

Set the Nginx version tag.

.. code:: yaml

   nginx_docker_image_tag:   "latest"

Docker Container Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always runs on ports 80 and 443 (if secured)

.. code:: yaml

   nginx_container_name:    "nginx"
   nginx_config_dir:        "/opt/{{ nginx_container_name }}"

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

See examples for format of upstream reverse proxies and security.

.. code:: yaml

   nginx_upstreams:         []
   nginx_security:          {}

Example Playbook
----------------

.. code:: yaml

   - hosts: web_server
     roles:
       - role: derekmerck.nginx_docker
         nginx_upstreams:
           - name: upstream
             path: /my_path    # No trailing slash, rewrite host -> host/my_path
             pool:
               - port: 5000
                 # host defaults to "localhost"
               - host: another_host
                 port: 80
         nginx_security:
           cert_dir:    "/opt/certs"
           common_name: "www.example.com"

License
-------

MIT
