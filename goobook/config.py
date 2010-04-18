#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# vim: fileencoding=UTF-8 filetype=python ff=unix et ts=4 sw=4 sts=4 tw=120
# author: Christer Sjöholm -- hcs AT furuvik DOT net

from __future__ import absolute_import

import ConfigParser
import getpass
import logging
import os
import subprocess
import sys

from hcs_utils.storage import Storage
from netrc import netrc
from os.path import realpath, expanduser

log = logging.getLogger(__name__)

def read_config(config_file):
    '''Reads the ~/.goobookrc and ~/.netrc.
    returns the configuration as a dictionary.

    '''
    config = Storage({ # Default values
        'email': '',
        'password': '',
        'cache_filename': '~/.goobook_cache',
        'cache_expiry_hours': '24',
        })
    config_file = os.path.expanduser(config_file)
    if os.path.lexists(config_file) or os.path.lexists(config_file + '.gpg'):
        try:
            parser = ConfigParser.SafeConfigParser()
            if os.path.lexists(config_file):
                log.info('Reading config: %s', config_file)
                f = open(config_file)
            else:
                log.info('Reading config: %s', config_file + '.gpg')
                sp = subprocess.Popen(['gpg', '--no-tty', '-q', '-d', config_file + ".gpg"], stdout=subprocess.PIPE)
                f = sp.stdout
            parser.readfp(f)
            config.get_dict().update(dict(parser.items('DEFAULT', raw=True)))
        except (IOError, ConfigParser.ParsingError), e:
            print >> sys.stderr, "Failed to read configuration %s\n%s" % (config_file, e)
            sys.exit(1)
    if not config.email or not config.password:
        netrc_file = os.path.expanduser('~/.netrc')
        if os.path.exists(netrc_file):
            log.info('email or password missing from config, checking .netrc')
            auth = netrc(netrc_file).authenticators('google.com')
            if auth:
                login = auth[0]
                password = auth[2]
                if not config.email:
                    config.email = login
                if not config.password:
                    config.password = password
            else:
                log.info('No match in .netrc')

    #replace password field with a function.
    if config.password == 'prompt':
        config.password = getpass.getpass
    else:
        password = config.password
        config.password = lambda: password

    # Ensure paths are fully expanded
    config.cache_filename = realpath(expanduser(config.cache_filename))
    log.debug(config)
    return config
