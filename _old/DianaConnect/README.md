Tithonus
=============================

[Derek Merck](derek_merck@brown.edu)  
Spring 2015

## Overview

Gatekeeper script for mirroring deidentified and reformatted medical images from [Orthanc][] to [XNAT][] using their [RESTful][] interfaces.

(Named after [_P. Tithonus_, the Gatekeeper butterfly][tithonus])

[Orthanc]: http://www.orthanc-server.com
[XNAT]: http://www.xnat.org
[tithonus]: http://en.wikipedia.org/wiki/Gatekeeper_(butterfly)
[restful]: http://en.wikipedia.org/wiki/Representational_state_transfer

## Dependencies

- Python 2.7
- [PyYAML](http://pyyaml.org)
- [Requests](http://docs.python-requests.org/en/latest/)
- [BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/)
- [GID_Mint](https://github.com/derekmerck/GID_Mint)


## Usage

```
usage: tithonus.py [-h] [-s STUDY] [-c CONFIG] [--delete_phi]
                   [--delete_deidentified]
                   {find-study,move-study,copy-study,delete-study,mirror-repo}
                   source target

Tithonus Core

positional arguments:
  command                 {find, copy, move, remove, mirror, transfer}
  source                  Source/working image repository as ID in config or json (or 'local')
  target                  Target image repository as ID in config or json (or 'local')

optional arguments:
  -h, --help              Show this help message and exit
  -s STUDY, --study STUDY Study as ID in working repo or json
  -c CONFIG, --config CONFIG Repo config file path
  --delete_phi            Remove original data with PHI from local after anonymization
  --delete_deidentified   Remove deidentified data from local after download

usage:

find source           --input query/filter    --config file  --output worklist.csv   (run query)
copy source target    --input items/worklist  --config file  --anonymize             (delete anon if any)
move source target    --input items/worklist  --config file  --anonymize             (copy + delete phi + delete anon if any)
remove source target  --input items/worklist  --config file                          (delete)
mirror source target  --input query/filter    --config file  --anonymize             (find + copy)
forward source target --input query/filter    --config file  --anonymize             (find + move)
```

- `source/target` must be something that can create an interface (json, name in config, or `local`)
- `items` must be something that can create a worklist { 'level': 'study', 'ids_in_source' : [1,2,3,4] }, (json, csv)
- `query` must be something that can filter items in the source into a worklist { 'level': 'subject', 'PatientName': 'ZNE*' } (json)
- `config` is optional for creating interfaces by name


### Uploading Local Files

```bash
$ python tithonus.py copy local my_target -i my_dicom_dir -c my_config
```

### Anonymize and Transfer a Single Study

```bash
$ python tithonus.py copy my_source my_target -i {'study_id', 'ABCDEDFG'} -c my_repos.yaml --anonymize
```


### Mirroring

Mirror and anonymize a local Orthanc clinical archive to a remote XNAT database:

```bash
$ python tithonus.py mirror "[orthanc, http://localhost:8042, user, pword]" "[xnat, http://localhost:8080/xnat, user, pword]"
```

You can keep your image repository settings in a separate config file as well.

```bash
$ python tithonus.py my_orthanc my_xnat -c my_repos.yaml
```

With a `my_repos.yaml` in this format:

```yaml
my_xnat:
  type:    'xnat'
  address: 'http://localhost:8080/xnat'
  user:    'user_name'
  pword:   'password'
my_orthanc:
  type:    'orthanc'
  address: 'http://localhost:8042'
  user:    'user_name'
  pword:   'password'
my_dicom:
  type:    'dicom'
  aetitle: 'MYDICOM'
  proxy:   'my_orthanc'
```

## Unit Tests

Setup for easy use with Nose.

- Presumes a DICOM server running at <dcm://localhost:4042> (Orthanc will do)
- Presumes an Orthanc server running at <http://localhost:8043> (A second instance of Orthanc will do)
- Presumes an XNAT server running at <http://localhost:8080/xnat> (Docker?)
- Presumes a valid [TCIA][] API key is available in the environment variable `TCIA_API_KEY`

[TCIA]: http://www.cancerimagingarchive.com

## Resources

- Orthanc [REST 0.9.1 API](https://docs.google.com/spreadsheets/d/1muKHMIb9Br-59wfaQbDeLzAfKYsoWfDSXSmyt6P4EM8/pubhtml?gid=525933398&single=true)
- XNAT [zip upload](https://wiki.xnat.org/display/XKB/Uploading+Zip+Archives+to+XNAT)
- Juniper [login trickery](https://gist.github.com/oogali/778846)

## License

[MIT](http://opensource.org/licenses/mit-license.html)
