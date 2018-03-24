#!/usr/bin/env python
from distutils.core import setup

# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


setup(name='DIANA',
      version='1.0',
      description='DICOM Analytics and Archive',
      long_description=long_description,
      author='Derek Merck',
      author_email='derek_merck@brown.edu',
      url='https://www.github.com/derekmerck/DIANA',
      packages=['DianaConnect', 'DianaFE', 'DianaStack',
                'DianaSplunk', 'DixelKit', 'GUIDMint', 'DianaFuture'],
     )