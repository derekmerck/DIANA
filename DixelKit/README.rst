DixelKit
========

| Derek Merck derek_merck@brown.edu
| Brown University and Rhode Island Hospital
| Winter 2018

https://www.github.com/derekmerck/DIANA/tree/master/DixelKit

Overview
--------

DICOM image objects may be represented in *many* different ways across
`DIANA <https//www.github.com/derekmerck/DIANA>`__): as ``.dcm`` files,
as URLs in `Orthanc <http://www.orthanc-server.com>`__, as tag data in
`Splunk <http://www.splunk.com>`__. A range of data and metadata,
including pixels, text reports, and procedure variables may be
associated with studies. And study data may be built-up incrementally
from multiple sources, creating incomplete DICOM-like structures.

DixelKit is a more generic and accessible toolkit for working with
collections of such medical imaging related data and metadata.

Dixel is a portmanteau for a "DICOM element" (or "DIANA element", a la
pixel or voxel.)

A DixelStorage is an inventory of dixels that supports CRUD access (put,
read/get/copy, update, delete). Implemented DixelStorages include:
``.dcm`` files, Orthanc (open source PACS), Splunk (meta data index),
and Montage (report text)

Dependencies
------------

Python package requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  `pydicom <http://pydicom.readthedocs.io/en/stable/getting_started.html>`__
-  `python-dateutil <https://dateutil.readthedocs.io/en/stable/>`__
-  `pyyaml <https://pyyaml.org>`__
-  `python-magic <https://github.com/ahupp/python-magic>`__
-  `requests <http://docs.python-requests.org/en/master/>`__
-  `splunk-sdk <http://dev.splunk.com/python>`__
-  `aenum <https://bitbucket.org/stoneleaf/aenum>`__
-  `beautifulsoup4 <https://www.crummy.com/software/BeautifulSoup/bs4/doc/>`__

External requirements
~~~~~~~~~~~~~~~~~~~~~

-  `Grassroots
   DICOM <http://gdcm.sourceforge.net/wiki/index.php/Main_Page>`__
   (``gdcm``) for DICOM file pixel compression

   -  ``$ brew install gdcm`` on OSX
   -  ``$ apt-get install libgcdm-tools`` on Debian^^

-  File magic (``libmagic``) for file typing

   -  ``$ brew install libmagic`` on OSX
   -  Typically pre-installed on Linux

Instalation
-----------

``$ git clone http://github.com/derekmerck/DIANA``

Usage
-----

See ``tests.py`` for more examples.

Lazy copy from FileStorage
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    >>> file_dir = FileStorage( 'my/dicom/dir' )
    >>> orthanc = Orthanc( 'localhost' )
    >>> count = file_dir.copy_inventory(orthanc)
    >>> assert( count > 0 )
    >>> count = file_dir.copy_inventory(orthanc, lazy=True)
    >>> assert( count == 0 )

JPG2K compression on copy from FileStorage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    >>> file_dir = FileStorage( 'my/dicom/dir' )
    >>> orthanc = Orthanc( 'localhost' )
    >>> file_dir.copy_inventory(orthanc)
    >>> size = orthanc.statistics()['DiskSizeMB']
    >>> orthanc.remove_inventory()
    >>> orthanc.prefer_compressed = True
    >>> file_dir.copy_inventory(orthanc)
    >>> size_z = orthanc.statistics()['DiskSizeMB']
    >>> assert( size_z < size )

Compression is performed only when the file: 1) has pixels (not a
structured report) and 2) the pixel dimensions are evenly divisible by
8. Otherwise the uncompressed data is loaded. This prevents ``gdcmconv``
from throwing an error when the transfer syntax cannot be changed.

**TODO**: This is not quite right: odd dimensions *can* be compressed,
so so we need to do some more analysis of when ``gdcmconv`` fails on
image data (ie, tilted gantry).

Lazy upload metadata to Splunk from Orthanc
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    >>> orthanc = Orthanc( 'localhost' )
    >>> splunk = Splunk( 'localhost', 8089, 'user', 'passw0rd' )
    >>> orthanc.copy_inventory( splunk, lazy=True )

Lookup Studies and Create a Research Archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    >>> csv_text = """
    PatientID, DateOfService, Procedure
    ABC,       01012000,      CT Angiogram"""
    >>> worklist = DixelUtils.load_csv(csv_text)
    >>> splunk.update(worklist)   # Get accession numbers, orthanc id's
    >>> montage.update(worklist)  # Add report text
    >>> DixelUtils.save_csv('my_project.csv')
    >>> orthanc.copy(worklist, Orthanc('my_project_host') )

Storage Instantiation with Secrets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    >>> secret_yaml="""
    host: localhost
    port: 8042
    user: username
    password: passw0rd
    """
    >>> credentials = yaml.load(secret_yaml)
    >>> orthanc = Orthanc(credentials)

--------------

^^ GDCM has no rpm available for RedHat 6, but can be compiled following
http://gdcm.sourceforge.net/wiki/index.php/Compilation and
https://raw.githubusercontent.com/malaterre/GDCM/master/INSTALL.txt

.. code:: bash

    $ yum install cmake3 g++
    $ git clone https://github.com/malaterre/GDCM
    $ cd GDCM
    $ mkdir build
    $ cd build
    $ cmake3 -D GDCM_BUILD_APPLICATIONS=true ..
    $ make
    $ make install
