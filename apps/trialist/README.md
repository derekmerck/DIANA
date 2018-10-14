DIANA Trialist Web App
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
- markdown
- [pyyaml][]
- [jinja2][]

[Python]: http://www.python.org
[Flask]: http://flask.pocoo.org
[Flask-HTTPAuth]: https://github.com/miguelgrinberg/Flask-HTTPAuth
[pyyaml]: http://pyyaml.org
[jinja2]: http://jinja.pocoo.org


## Usage

```bash
$ export FLASK_APP=trialist.py
$ export TRIALIST_CONFIG=../examples/central_imaging/trials.yml
$ python -m flask run
```
