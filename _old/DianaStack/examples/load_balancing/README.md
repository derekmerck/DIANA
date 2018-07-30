

# Setting up a REST Load Balancer

This is intended to work with a DICOM bridge.  DICOM load balancing is hard/unknown, so the idea is to convert the DICOM requests into HTTP peering REST requests and load balance that with an nginx reverse proxy.  

Note particularly that you should _definitely_ use a recent build of Orthanc Docker for this, as otherwise the `asserts` will eventually cause all instances but one to fail. 

## Setting load balancing up on a running system:

### 1. Shutdown `archive-forwarder` to freeze the database

```
cirr2$ docker stop archive-forwarder
```

### 2. Create workers

No need to expose ports.  Restart on failure sometimes useful if the database is in a possibly inconsistent state on first startup.

```
$ docker run --name orthanc0 -d --link db:postgres -v /research/orthanc-connect/orthanc.json:/etc/orthanc/orthanc.json:ro -v /research/orthanc-archive/db:/var/lib/orthanc/db:rw jodogne/orthanc-plugins
$ docker run --name orthanc1 -d --link db:postgres -v /research/orthanc-connect/orthanc.json:/etc/orthanc/orthanc.json:ro -v /research/orthanc-archive/db:/var/lib/orthanc/db:rw jodogne/orthanc-plugins
$ docker run --name orthanc2 -d --link db:postgres -v /research/orthanc-connect/orthanc.json:/etc/orthanc/orthanc.json:ro -v /research/orthanc-archive/db:/var/lib/orthanc/db:rw jodogne/orthanc-plugins
```

### 3. Restart `archive-forwarder`

```
cirr2$ docker start archive-forwarder
```

### 4. Create `/research/config/rest-head.conf`

```
events {
  worker_connections  1024;
}

http {
  upstream orthanc {
    server orthanc0:8042;
    server orthanc1:8042;
    server orthanc2:8042;
  }

  server {
    listen 8042;
    location / {
      proxy_pass http://orthanc;
    }
  }
}
```

### 5. Create the REST-Head

```
$ docker run --name rest-head -d --link orthanc0 --link orthanc1 --link orthanc2 -p 4288:8042 -v /research/config/rest-head.conf:/etc/nginx/nginx.conf:ro nginx
```

### 6. Test the REST-Head


### 7. Switch the `archive-router` to point to `rest-head`

Edit `cirr2:/var/lib/orthanc/archive-router/orthanc.json` to put the `cirr1` peer on port 4288.



Finally, you should be able to add more workers by turning off the REST-Head, starting up the workers, editing the conf file, and restarting the REST-Head.