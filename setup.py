#!/usr/bin/env python
# vim: fileencoding=UTF-8 filetype=python ff=unix expandtab sw=4 sts=4 tw=120
# author: Christer Sjöholm -- goobook AT furuvik DOT net

import os

from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
NEWS = open(os.path.join(here, 'CHANGES.txt')).read()

class UltraMagicString(object):
    ''' Stolen from http://stackoverflow.com/questions/1162338/whats-the-right-way-to-use-unicode-metadata-in-setup-py

    Catch-22:
    - if I return Unicode, python setup.py --long-description as well
      as python setup.py upload fail with a UnicodeEncodeError
    - if I return UTF-8 string, python setup.py sdist register
      fails with an UnicodeDecodeError
    '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __unicode__(self):
        return self.value.decode('UTF-8')

    def __add__(self, other):
        return UltraMagicString(self.value + str(other))

    def split(self, *args, **kw):
        return self.value.split(*args, **kw)

setup(name='goobook',
      version = '1.4',
      description = 'Search your google contacts from the command-line or mutt.',
      long_description=UltraMagicString(README + '\n\n' + NEWS),
      maintainer = UltraMagicString('Christer Sjöholm'),
      maintainer_email = 'goobook@furuvik.net',
      url = 'http://goobook.googlecode.com/',
      download_url = 'http://pypi.python.org/pypi/goobook',
      classifiers = [f.strip() for f in """
        Development Status :: 5 - Production/Stable
        Environment :: Console
        Operating System :: OS Independent
        Programming Language :: Python
        Programming Language :: Python :: 2.6
        Programming Language :: Python :: 2.7
        Intended Audience :: End Users/Desktop
        License :: OSI Approved :: GNU General Public License (GPL)
        Topic :: Communications :: Email :: Address Book
        """.splitlines() if f.strip()],
      license = 'GPLv3',
      install_requires = [
          'argparse>=1.1',
          'distribute',
          'gdata>=2.0.7',
          'hcs_utils==1.1.1',
          'simplejson>=2.1.0',
          'keyring>=0.2'],
      packages = find_packages(),
      entry_points = {'console_scripts': [ 'goobook = goobook.application:main']}
     )

