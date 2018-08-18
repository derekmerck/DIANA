Get-a-GUID Web App
==================

Overview
--------

Python library and Flask REST api to generate 1-way hashes for study
ids, pseudonyms, and approximate-birth-date for globally consistent
identifiers in study anonymization.

A reference web implementation of the most recent master branch is
available at `http://get-a-guid.zmø.biz <http://get-a-guid.zmø.biz>`__.

Dependencies
------------

-  Python 3.6
-  guidmint
-  `Flask <http://flask.pocoo.org>`__
-  markdown

Usage
-----

Local Server Instance
~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   $ python get_a_guid.py &  
     * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)  
   $ curl "localhost:5000/guid/pseudonym/pseudo_id?value=MERCK^DEREK^L"
   {"dob": "1968-07-25", "gender": "U", "guid": "AYJOAUVBBT54F6TP", "name": "ANDRONIS^YEVETTE^J"}

Implementing as a Public Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a `Heroku <http://www.heroku.com>`__ server instance:

.. code:: bash

   $ heroku create
   $ git push heroku master
   $ heroku ps:scale web=1
   $ curl "http://get-a-guid.herokuapp.com/pseudonym/pseudo_id?name=MERCK^DEREK^L"
   {"dob": "1968-07-25", "gender": "U", "guid": "AYJOAUVBBT54F6TP", "name": "ANDRONIS^YEVETTE^J"} 

Single dyno Heroku instances are free to run, but can take a minute to
startup after they fall asleep.

To create a `Dokku <http://dokku.viewdocs.io/dokku/>`__ server instance:

.. code:: bash

   $ git clone https://github.com/derekmerck/DIANA
   $ cd DIANA
   $ git add remote dokku dokku@xn--zm-mka.biz:get-a-guid
   $ git subtree push --prefix GUIDMint dokku master
   $ curl "http://get-a-guid.xn--zm-mka.biz/pseudonym/pseudo_id?name=MERCK^DEREK^L"
   {"dob": "1968-07-25", "gender": "U", "guid": "AYJOAUVBBT54F6TP", "name": "ANDRONIS^YEVETTE^J"} 

Acknowledgements
----------------

-  Thanks for the `Heroku <http://www.heroku.com>`__ Flask tutorials at
   http://virantha.com/2013/11/14/starting-a-simple-flask-app-with-heroku/
   and
   http://stackoverflow.com/questions/17260338/deploying-flask-with-heroku
   and http://www.moreiscode.com/dokku-error/
-  GitHub markdown css from
   https://github.com/sindresorhus/github-markdown-css

License
-------

`MIT <http://opensource.org/licenses/mit-license.html>`__
