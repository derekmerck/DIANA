"""
Tithonus Setup
Merck, Spring 2015

[Derek Merck](derek_merck@brown.edu)
Spring 2015

<https://github.com/derekmerck/Tithonus>

Dependencies: requests, PyYAML

See README.md for usage, notes, and license info.

## Distribution to a pypi server:

```
$ pandoc --from=markdown --to=rst --output=README.rst README.md
$ python setup.py sdist
$ python setup.py register [-r https://testpypi.python.org/pypi]
$ python setup.py sdist upload  [-r https://testpypi.python.org/pypi]
```
"""

import os
from setuptools import setup
import tithonus


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

# README.md is preferred
long_desc = read('README.md')
# pypi requires a README.rst, so we create one with pandoc and include it in the source distribution
if os.path.exists('README.rst'):
    long_desc = read('README.rst')

setup(
    name=tithonus.__package__,
    description=tithonus.__description__,
    author=tithonus.__author__,
    author_email=tithonus.__email__,
    version=tithonus.__version__,
    long_description=long_desc,
    url=tithonus.__url__,
    license=tithonus.__license__,
    py_modules=["tithonus", "Interface", "Polynym"],
    include_package_data=True,
    zip_safe=True,
    install_requires=['requests', 'PyYAML', 'beautifulsoup4'],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Healthcare Industry',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Medical Science Apps.'
    ]
)