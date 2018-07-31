DIANA Testing
======================

Merck, Summer 2018

Configuration
----------------------

There are two preconfigured service test benches.

**dev-local** is statically configured with [docker-compose][] (suitable for [Travis CI][])

```bash
$ cd test
$ docker-compose -f dev-local.compose.yml
$ pytest --services test/dev_local_services
```


**dev** is dynamically configured with [Ansible][], and is intended to more closely simulate a distributed production environment using [Vagrant][].
   
```bash
$ cd ~/testing/vagrant
$ vagrant up
$ cd ~/stack
$ ansible-playbook diana-play.yml -i test/dev_testbench.yml
$ pytest --services test/dev_services
```


Tests
----------------------

Diana+ tests are run in two passes, first using the standard scripting API, and again as asynchronously scheduled tasks managed through a [celery][] broker.

- `test_orthanc_api.py`:  `get`, `put`, `remove`, `find`, `send`, `inventory`
- `test_dicom_file_api.py`:  `get`, `put-file`, `put-image`, `remove`
- `test_collector_daemon.py`: `watch-ftp`, `watch-orthanc`'


[docker-compose]:
[Travis CI]:
[Ansible]:
[Vagrant]:
