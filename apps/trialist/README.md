DIANA Trialists Front-End Web App
=================================

Derek Merck <derek_merck@brown.edu>  
Brown University and Rhode Island Hospital  
Winter 2018

<https://www.github.com/derekmerck/DIANA/>


## Overview

Flask server providing a simple, flexible front-end html framework for listing available trial resources.


## Dependencies

- [Python][] 3.6+
- [Flask][]
- [Flask-HTTPAuth][]
- flask_restplus
- markdown
- [pyyaml][]
- [jinja2][]
- numpy
- bokeh

[Python]: http://www.python.org
[Flask]: http://flask.pocoo.org
[Flask-HTTPAuth]: https://github.com/miguelgrinberg/Flask-HTTPAuth
[pyyaml]: http://pyyaml.org
[jinja2]: http://jinja.pocoo.org


## Usage

```bash
$ cd DianaFE
$ export FLASK_APP="DianaFE.py"
$ export dfe_config="../examples/central_imaging/trials.yml"
$ python -m flask run
```

See <../examples/central_imaging/trials.yml> for a configuration reference.


## GUIDMint Integration

The Trialist app can host helper apps, including `get-a-guid` from GUIDMint.  This can be used as a cardinal study ID server.

```bash
$ curl 'http://localhost:5000/guid/pseudonym/pseudo_id?name=MERCK^DEREK&gender=M&age=10'
{"dob": "2007-09-16", "gender": "M", "guid": "YGN3N52VZZRYD3SU", "name": "YOUMANS^GUY^N"}
```
