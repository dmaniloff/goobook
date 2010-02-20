#!/usr/bin/env python
# vim: fileencoding=UTF-8 filetype=python ff=unix expandtab sw=4 sts=4 tw=120
# author: Christer Sjöholm -- goobook AT furuvik DOT net

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup

setup(name='goobook',
      version = '1.0',
      description = 'Search your google contacts from mutt.',
      long_description=open('README.txt').read(),
      maintainer = u'Christer Sjöholm',
      maintainer_email = 'goobook@furuvik.net',
      url = 'http://goobook.googlecode.com/',
      classifiers = [f.strip() for f in """
        Development Status :: 5 - Production/Stable
        Environment :: Console
        Operating System :: OS Independent
        Programming Language :: Python
        Programming Language :: Python :: 2.6
        Intended Audience :: End Users/Desktop
        License :: OSI Approved :: GNU General Public License (GPL)
        Topic :: Communications :: Email :: Address Book
        """.splitlines() if f.strip()],
      license = 'GPLv3',
      install_requires = ['gdata>=2.0.7'],
      py_modules = ['goobook'],
      entry_points = {'console_scripts': [ 'goobook = goobook:main']}
     )

