#!/usr/bin/env python
from distutils.core import setup

setup(name='DIANA',
      version='1.0',
      description='DICOM Analytics and Archive',
      author='Derek Merck',
      author_email='derek_merck@brown.edu',
      url='https://www.github.com/derekmerck/DIANA',
      packages=['DianaConnect', 'DianaFE', 'DianaStack', 'DixelKit', 'GUIDMint'],
     )