Ansible Role for Queued Orthancs in Docker
==========================================

| Derek Merck
| derek_merck@brown.edu
| Rhode Island Hospital and Brown University
| Providence, RI

Configure and run a queued orthanc arrangement where the primary archive
is fed by an anonymization and compression queue.

For directed anonymization, with GUID assignment, use a DIANA-Watcher
route. Additional DIANA-Watcher routes may be configured to move
incoming files onto the queue as well.

Dependencies
------------

Galaxy Roles
~~~~~~~~~~~~

-  ``derekmerck.orthanc-docker``
-  ``derekmerck.diana-docker``
-  ``matic-insurance.docker-postgres``

Local Node
~~~~~~~~~~

Because this service is composed of multiple roles, it is easiest to
organize the configurations in their own namespaces (as sub-keys). To
support this mechanism, passed in var are merged over defaults as the
first task. Pass in overrides as ``qorth_queue`` and
``qorth_destination``.

Remote Node
~~~~~~~~~~~

-  `Docker <https://www.docker.com>`__
-  `docker-py <https://docker-py.readthedocs.io>`__

Role Variables
--------------

Configure with two separate variables, ``qorth_queue`` and
``quorth_destination``, each appropriate for instantiating a
``derekmerck.orthanc.docker`` role.

The ``qorth_service`` var sets the base name for the service.

.. code:: yaml

   qorth_service: "dicom"

New orthanc role variable declarations with nested vars:

.. code:: yaml

   qorth_queue:
     orthanc_ports:
       api:                   42001
       dicom:                 42000
     orthanc_volumes:
       data:                  "{{ data_dir }}/{{ container_name }}"
       config:                "{{ config_dir }}/{{ container_name }}"

New queue-specific routing configuration vars:

.. code:: yaml

   qorth_queue:
     diana_routing_dir:       None
     ftpd_incoming_dir:       None

Setting ``diana_routing_dir`` will add a DIANA dependency and create a
baseline routing table to forward imaging between the queue and
destination nodes. If ``ftpd_incoming_dir`` is also set, a route from
incoming to the orthanc queue will also be created.

Example Playbook
----------------

Simple forwarding via lua scripts:

.. code:: yaml

   - hosts: dicom_node
     vars:
       data_dir: "/data"
       config_dir: "/config"
       
     roles:
       - name: Setup queued orthanc
         role: derekmerck.queued-orthanc
         vars:
           qorth_service: my_archive
           
             qorth_queue:
               orthanc_ports:
                 dicom: 42000
                 api:   42001
               orthanc_anonymize: True
               orthanc_compress: False
               
             qorth_destination:
               orthanc_ports:
                 api:   42002
               orthanc_users: "{{ lookup('file', my_auth.yml ) | from_yaml | select( qorth_service ) }}"

If using forwarding with compression, use the ``derekmerck/orthanc``
docker image, which comes with ``libgdcm`` pre-installed.

.. code:: yaml

             qorth_queue:
               orthanc_docker_image: derekmerck/orthanc
               orthanc_docker_tag: or321
               orthanc_anonymize: True
               orthanc_compress:  True

Forwarding with a DIANA-Watcher routing table.

.. code:: yaml

           ...
           qorth_service: my_archive
             qorth_queue:
               diana_routing_dir: "{{ config_dir }}/diana/routes"
               ftpd_incoming_dir: "{{ data_dir }}/ftpd/my_archive"
           ...

Using the ``orthanc/osimis`` docker image for the archive provides an
anonymized data review interface. Alternatively, a separate Osimis
container can be attached to the same postgres backend tables and file
store.

.. code:: yaml

           ...
           qorth_service: my_archive
             qorth_destination:
               orthanc_docker_image: osimis/orthanc
           ...

License
-------

MIT
