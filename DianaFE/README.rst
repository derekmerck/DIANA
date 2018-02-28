DIANA-frontend
==============

| Derek Merck derek_merck@brown.edu
| Brown University and Rhode Island Hospital
| Winter 2018

https://www.github.com/derekmerck/DIANA/tree/master/DianaFE

Overview
--------

Flask server providing a simple, flexible front-end html framework for
listing available trial resources.

Dependencies
------------

-  `Python <http://www.python.org>`__ 2.7.11+
-  `Flask <http://flask.pocoo.org>`__
-  `Flask-HTTPAuth <https://github.com/miguelgrinberg/Flask-HTTPAuth>`__
-  flask\_restplus
-  markdown
-  `pyyaml <http://pyyaml.org>`__
-  `jinja2 <http://jinja.pocoo.org>`__
-  numpy
-  bokeh

Usage
-----

.. code:: bash

    $ cd DianaFE
    $ export FLASK_APP="DianaFE.py"
    $ export dfe_config="../examples/DianaFE/central_dfe_cfg.yml"
    $ python -m flask run

GUIDMint Integration
--------------------

The DianaFE app can host helper apps, including ``get-a-guid`` from
GUIDMint. This can be used as a cardinal study ID server.

.. code:: bash

    $ curl 'http://localhost:5000/guid/pseudonym/pseudo_id?name=MERCK^DEREK&gender=M&age=10'
    {"dob": "2007-09-16", "gender": "M", "guid": "YGN3N52VZZRYD3SU", "name": "YOUMANS^GUY^N"}
