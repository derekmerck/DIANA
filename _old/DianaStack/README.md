# DIANA-services

Derek Merck <derek_merck@brown.edu>
Rhode Island Hospital
Summer 2016

Uses Ansible to configure and spin up a Docker-based open-source<sup><a name="^splunk_ref">[1](#^splunk)</a></sup> medical imaging informatics platform.  Originally developed to support the RIH Clinical Imaging Research Repository (CIRR).


## All-in-One Services

- Clinical/PHI Facing Receiver - [Orthanc] on 4280 (HTTP/REST), 4243 (DICOM)
- Research/Anonymized Facing Repository - [XNAT] 1.6.5 on 5280 (HTTP/REST), 5242 (DICOM)
- Database - [Postgresql] 9.5 on 1432 (SQL)
- Log Monitoring - [Splunk] Lite on 1580 (HTTP/REST), 1514 (syslog)


## Routing Services

- Clinical/PHI Facing Forwarder - [Orthanc] on 4280 (HTTP/REST), 4243 (DICOM) with autoforwarding
- Multiplexing Router (single send -> multiple forwarding queues) - [Orthanc] on configurable ports

[Splunk]:http://www.splunk.com
[Postgresql]:http://www.postgresql.org
[Orthanc]:http://www.orthanc-server.com
[XNAT]:http://www.xnat.org
[Tithonus]:https://github.com/derekmerck/Tithonus


## Dependencies

- [Docker] for service virtualization on host nodes
- [Python] 2.7, [Ansible], [jinja2] for orchestration on control nodes

[Docker]:http://www.docker.com
[docker-compose]:https://docs.docker.com/compose/
[Python]:http://www.python.org
[pyyaml]:http://pyyaml.org
[jinja2]:http://jinja.pocoo.org
[ansible]:http://www.ansible.com


## Usage

Setup a clinical PACS (orthanc) and research PACS (xnat) along with postgres and splunk on a single machine.

```bash
$ ansible-playbook -i hosts -v all_in_one_archive.yml
```

The all-in-one server can become somewhat slow to ingest data (5+ images/sec), so we also use an optional receiver queue to accept incoming data and forward it along.  Keeping this queue empty results in approximately 40+ images/sec ingestion.  Moreover, it can be configured to route to multiple different archives.

```bash
$ ansible-playbook -i hosts -v dicom_router.yml
```


## Configuration

_Warning_: once data has been ingested, be _very_ careful about rebuilding the containers or changing configs, which can trigger rebuilds in the containers and drop data volumes or databases.  An additional "ALLOW_CLEAN" variable flag serves as a protection against this.<sup><a name="^database_ref">[2](#^database)</a></sup>

Override any credentials and service settings by including them in a `secrets.yml` file.

If `./pkg/xnat-1.6.5.tar.gz` exists, it will use that to build XNAT from source instead of downloading the tarball from the NRG.


### Administration

By default, the Splunk container monitors the Orthanc and XNAT log files.  These logs are also exposed on the host in `\var\log\orthanc` and `\var\log\xnat` by default.


## Troubleshooting

If using [Vagrant] with [VirtualBox], the Maven build for XNAT requires a lot of memory, so you may need to bump the VM RAM up from the default to 2GB.

Also, be sure to use the Docker provisioner.

```yml
config.vm.provider "virtualbox" do |vb|
   vb.memory = "2048"
end
config.vm.provision "docker`
```

[vagrant]: http://www.vagrantup.com
[virtualbox]: https://www.virtualbox.org

To get a multiplexing router to work on RedHat/CENTos run this to enable inter-container communication:

`$ sudo iptables -I INPUT 4 -i docker0 -j ACCEPT`

See <https://github.com/docker/docker/issues/10450> for discussion.  Alternatively, we could manually link the containers when they are instantiated.


### Tuning Postgresql

See <http://pgtune.leopard.in.ua> for simple config tool.  For our servers w 200GB of RAM I used the following:

```
max_connections = 200
shared_buffers = 25GB
effective_cache_size = 75GB
work_mem = 128MB
maintenance_work_mem = 2GB
min_wal_size = 1GB
max_wal_size = 2GB
checkpoint_completion_target = 0.7
wal_buffers = 16MB
default_statistics_target = 100
```

Although it didn't seem to make much of a difference in performance.

## Acknowledgements

Uses Docker images from:

- [jodogne/orthanc](https://github.com/jodogne/OrthancDocker)
- [chaseglove/xnat](https://github.com/chaselgrove/xnat-docker)
- [outcoldman/splunk](https://github.com/outcoldman/docker-splunk)


## License

MIT

---

<a name="^splunk">1</a>: Splunk is not open source, but Splunk Lite will work for this volume of logs and it _is_ free.  Replace it with your open-source syslog server of choice if necessary.[:arrow_heading_up:](#^splunk_ref)

<a name="^database">2</a>: Orthanc will happily use an existing database, or create a new one if necessary.  However, XNAT _requires_ that the database and image store volume be initialized during build, so the database may be dropped if Ansible decides to rebuild the XNAT container.[:arrow_heading_up:](#^database_ref)

