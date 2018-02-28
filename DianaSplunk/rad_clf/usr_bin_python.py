"""
Wrapper for running Splunk lookups using /usr/bin/python and locally managed packages

Roughly taken from:
<https://answers.splunk.com/answers/8/can-i-add-python-modules-to-the-splunk-environment.html>

Use in Splunk lookup as:
> usr_bin_python.py RADclf.py -s report radcat -pd {pkl_dir}
"""

import os
import subprocess
import sys

# Critical to dump the existing environment or it will try to attach to Splunk's
# sqlite and other broken packages.
del(os.environ['LD_LIBRARY_PATH'])
del(os.environ['PATH'])

_NEW_PYTHON_PATH = '/Users/derek/anaconda/bin/python'
# _NEW_PYTHON_PATH = '/usr/bin/python'
# _OLD_PYTHON_PATH = os.environ['PYTHONPATH']
os.environ['PYTHONPATH'] = _NEW_PYTHON_PATH

my_process = os.path.join(os.getcwd(), sys.argv[1])

p = subprocess.Popen([os.environ['PYTHONPATH'], my_process] + sys.argv[2:],
stdin=sys.stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = p.communicate()[0]

# Don't necessarily need this if stdout=sys.stdout, I think
print output