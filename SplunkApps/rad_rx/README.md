# ![logo](static/appIconAlt_2x.png) Rad Rx

Derek Merck <derek_merck@brown.edu>, Brown University and Rhode Island Hospital  
Scott Collins, Rhode Island Hospital  
Karen Laurie, The Miriam Hospital  

<https://github.com/derekmerck/DIANA/tree/master/apps/rad_rx>


## Overview

**Rad Rx** is a [Splunk][] app that provides dashboards for radiation dose monitoring from DICOM
structured reports and a simple incident ticketing system.

It is intended to be used with [DIANA-connect][], a set of python scripts that can monitor an installation of Jodogne's [Orthanc][] and copy [DICOM][] structured report tags to a Splunk index.

[Orthanc]: https://orthanc.chu.ulg.ac.be
[DICOM]: http://dicom.nema.org
[Splunk]: https://www.splunk.com
[DIANA-connect]: https://github.com/derekmerck/DIANA/tree/master/connect


## Dependencies

- Splunk 6.6


## Setup

1. Setup a Splunk instance.  (I prefer to use the [Splunk Docker container](https://hub.docker.com/r/splunk/splunk/) for quick deployments.)
2. Create indices for `dose_reports` and `dose_incidents`
3. Create a `device_map.csv` file and an `rpd_map.csv` (procedure names) file (refer to RIH the maps in [lookups](lookups/))
4. Login to the Splunk server and install the dose app from github and copy your lookups to `local`

```
$ clone https://github.com/derekmerck/DIANA.git
$ ln -s /opt/Splunk/etc/apps/rad_rx DIANA/apps/rad_rx
$ cp my_device_map.csv DIANA/apps/rad_rx/local/lookups/device_map.csv
$ cp my_rpd_map.csv DIANA/apps/rad_rx/local/lookups/rpd_map.csv
```

4. Refresh Splunk <http://splunkhost:8000/debug/refresh>

You can add data to the system either manually, by importing JSON dose reports (or minimally formatted csv files), or via a scripted pull from a DICOM archive.

