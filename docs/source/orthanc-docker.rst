Ansible Role for Orthanc in Docker
==================================

`Build
Status <https://travis-ci.org/derekmerck/ansible-orthanc-docker>`__

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Configure and run an `Orthanc <https://www.orthanc-server.com>`__ DICOM
node in a Docker container.

Dependencies
------------

Galaxy Roles
~~~~~~~~~~~~

-  `geerlingguy.docker <https://github.com/geerlingguy/ansible-role-docker>`__
   to setup the docker environment
-  `geerlingguy.pip <https://github.com/geerlingguy/ansible-role-pip>`__
   to install Python reqs
-  `matic-insurance.docker-postgres <https://github.com/matic-insurance/ansible-docker-postgres>`__
   to setup the postgres backend, if needed

Local Node
~~~~~~~~~~

-  Python Cryptography, if password secrets are encrypted

Remote Node
~~~~~~~~~~~

-  `Docker <https://www.docker.com>`__
-  `docker-py <https://docker-py.readthedocs.io>`__

Role Variables
--------------

Docker Image and Tag
~~~~~~~~~~~~~~~~~~~~

Select an Orthanc image and tag.

-  ``jodogne/orthanc`` is the official vanilla `Orthanc for
   Docker <http://book.orthanc-server.com/users/docker.html>`__ build
   maintained by Sébastien Jodogne
-  ``jodogne/orthanc-plugins`` is the official build supporting the
   Postgresql backend (uses PostgreSQL 10 – trusty has a problem with
   installing tools for 9.5)
-  ``osimis/orthanc`` is a third-party `Osimis for
   Docker <https://osimis.atlassian.net/wiki/spaces/OKB/pages/26738689/How+to+use+osimis+orthanc+Docker+images>`__
   spin with an excellent web viewer for review and annotation
-  ``derekmerck/orthanc`` is a third-party multi-architecture (amd64,
   arm32v7) bleeding-edge release spin from
   `diana-plus <https://github.com/derekmerck/diana_plus>`__

.. code:: yaml

   orthanc_docker_image:       "jodogne/orthanc"
   orthanc_docker_image_tag:   "latest"

Docker Container Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   orthanc_container_name:     "orthanc"
   orthanc_use_data_container: True
   orthanc_data_dir:           "/data/{{ orthanc_container_name }}"
   orthanc_config_dir:         "/opt/{{ orthanc_container_name }}"
   orthanc_api_port:           8042
   orthanc_dicom_port:         4242
   orthanc_container_timezone: "America/New_York"

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

Configure the service. These variables are used in the template config
file.

.. code:: yaml

   orthanc_title:              "Orthanc"
   orthanc_aet:                "ORTHANC"
   orthanc_user:               "orthanc"
   orthanc_password:           "passw0rd!"

Additional complex configuration items that are injected into
``orthanc.conf``. They must follow the appropriate format (see below)

.. code:: yaml

   orthanc_users:              {}
   orthanc_peers:              {}
   orthanc_modalities:         {}

Routing Configuration
~~~~~~~~~~~~~~~~~~~~~

Orthanc can be configured as a router by including a dictionary of
destinations (peer). While routing it can optionally anonymize and/or
compress data. See the role ``derekmerck/queued-orthanc`` for examples
of how to construct more flexible routing with a DIANA-Watcher service.

.. code:: yaml

   orthanc_anonymize:          False
   orthanc_compress:           False
   orthanc_destinations:       [{dest: peer or modality name, type: peer or dicom}, ..]

PostgreSQL Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   orthanc_pg_backend:         False
   orthanc_pg_user:            "{{ orthanc_user }}"
   orthanc_pg_password:        "{{ orthanc_password }}"
   orthanc_pg_database:        "{{ orthanc_container_name }}"
   orthanc_pg_host:             "postgres"
   orthanc_pg_port:             5432

Example Playbook
----------------

Run a single orthanc instance.

.. code:: yaml

   - hosts: dicom_node
     roles:
        - derekmerck.orthanc_docker

Run a single orthanc instance with some additional users and peers

.. code:: yaml

   - hosts: dicom_node
     roles:
       - name: derekmerck.orthanc_docker
         orthanc_users:
           user1: password        
           user2: passw0rd!        
         orthanc_peers:
           my_peer:       [ "http://127.0.0.1:8043/", "user1", "password" ]
           my_other_peer: [ "http://127.0.0.1:8043/", "user2", "passwOrd!"]
         orthanc_modalities:
           my_pacs:        ["MY_PACS", "192.168.1.1", 104 ]
           my_workstation: ["MY_WORKSTATION", "192.168.1.2", 104 ]

*Note: This is currently only working for user passwords.* Run a single
orthanc instance with additional users and peers using confidential
passwords (fernet encoded)

| \```yaml - hosts: dicom_node vars: fernet_key:
  ‘t8YHZXpNvk_OFPkvyWc2rDWUxp7qXY6tiHr10f_PG3Y=’ roles: - name:
  derekmerck.orthanc_docker orthanc_users: user1:
  “gAAAAABbcFt-3M4t288flnG2xY88xKPx4U1l1phZtv4hDpnjNx3Mq8s9MnY74dY6Ab35qp6voKAVGJ9BMT8wlthPY4COk16sIg==”
| user2:
  “gAAAAABbcFrtnhBWtrEC8QXvqByYsyEEqNKC2mP2joN4rcK58RNZIdKqMLErq-Lki6NhPSvpv_Y7fkYJRuaM4Gbt0QFFYZtZmQ==”
  orthanc_peers: my_peer: [ “http://127.0.0.1:8043/”, “user1”,
  “gAAAAABbcFt-3M4t288flnG2xY88xKPx4U1l1phZtv4hDpnjNx3Mq8s9MnY74dY6Ab35qp6voKAVGJ9BMT8wlthPY4COk16sIg==”
  ] my_other_peer: [ “http://127.0.0.1:8043/”, “user2”,
  “gAAAAABbcFrtnhBWtrEC8QXvqByYsyEEqNKC2mP2joN4rcK58RNZIdKqMLErq-Lki6NhPSvpv_Y7fkYJRuaM4Gbt0QFFYZtZmQ==”]

Run multiple instances against the same backend for load balancing.

.. code:: yaml

   - hosts: dicom_node
     tasks:
     - include_role:
         name: derekmerck.orthanc_docker
       vars:
         # Independent variables
         orthanc_api_port:        "804{{ item }}"
         orthanc_dicom_port:      "424{{ item }}"
         
         # Shared variables
         orthanc_data_dir:        "/data/orthanc"
         orthanc_docker_image:    "jodogne/orthanc-plugins"
         orthanc_pg_backend:      True
         orthanc_db_name:         "orthanc"
       with_sequence: count=3

Run a multiplexing forwarder with compression

.. code:: yaml

   - hosts: dicom_node
     roles:
       - name: derekmerck.orthanc_docker
         orthanc_peers:
           my_peer:       [ "http://127.0.0.1:8043/", "user1", "password" ]
         orthanc_modalities:
           my_workstation: ["MY_WORKSTATION", "192.168.1.2", 104 ]
         orthanc_destinations:
           - dest: my_peer
             type: peer
           - dest: my_workstation
             type: dicom
         orthanc_compression: True

License
-------

MIT
