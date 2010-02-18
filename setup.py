#!/usr/bin/env python
# vim: fileencoding=UTF-8 filetype=python ff=unix expandtab sw=4 sts=4 tw=120
# author: Christer Sjöholm -- goobook AT furuvik DOT net

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup

setup(name='goobook',
      version = '0.9.0',
      description = 'Search your google contacts from mutt.',
      maintainer = 'Christer Sjöholm',
      maintainer_email = 'goobook@furuvik.net',
      url = 'http://goobook.googlecode.com/',
      classifiers = ['Development Status :: 4 - Beta',
                     'Operating System :: OS Independent',
                     'Environment :: Console',
                     'Intended Audience :: End Users/Desktop',
                     'License :: OSI Approved :: GNU General Public License (GPL)',
                     'Programming Language :: Python',
                     'Programming Language :: Python :: 2.6',
                     'Topic :: Communications :: Email :: Address Book',
                    ],
      license = 'GPLv3',
      requires = ['gdata (>=2.0.7)'],
      py_modules = ['goobook'],
      entry_points = {'console_scripts': [ 'goobook = goobook:main']}
     )

