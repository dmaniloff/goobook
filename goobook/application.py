#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# vim: fileencoding=UTF-8 filetype=python ff=unix et ts=4 sw=4 sts=4 tw=120
# author: Christer Sjöholm -- hcs AT furuvik DOT net

from __future__ import absolute_import

import gdata.client
import goobook.config
import locale
import logging
import optparse
import sys
import xml.etree.ElementTree as ElementTree

from goobook.goobook import GooBook, Cache

log = logging.getLogger(__name__)

CONFIG_FILE = '~/.goobookrc'
CONFIG_TEMPLATE = '''\
# "#" or ";" at the start of a line makes it a comment.
[DEFAULT]
# If not given here, email and password is taken from .netrc using
# machine google.com
;email: user@gmail.com
;password: top secret
# The following are optional, defaults are shown
;cache_filename: ~/.goobook_cache
;cache_expiry_hours: 24
'''

ENCODING = locale.getpreferredencoding()

def main():
    class MyParser(optparse.OptionParser):
        def format_epilog(self, formatter):
            return self.epilog
    usage = 'usage: %prog [options] <command> [<arg>]'
    description = 'Search you Google contacts from mutt or the command-line.'
    epilog = '''\
Commands:
  add              Add the senders address to contacts, reads a mail from STDIN.
  reload           Force reload of the cache.
  query <query>    Search contacts using query (regex).
  config-template  Prints a template for .goobookrc to STDOUT

'''
    parser = MyParser(usage=usage, description=description, epilog=epilog)
    parser.set_defaults(config_file=CONFIG_FILE)
    parser.add_option("-c", "--config", dest="config_file",
                    help="Specify alternative configuration file.", metavar="FILE")
    parser.add_option("-v", "--verbose", dest="logging_level", default=logging.ERROR,
                    help="Specify alternative configuration file.",
                    action='store_const', const=logging.INFO)
    parser.add_option("-d", "--debug", dest="logging_level",
                    help="Specify alternative configuration file.",
                    action='store_const', const=logging.DEBUG)
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        sys.exit(1)
    logging.basicConfig(level=options.logging_level)
    config = goobook.config. read_config(options.config_file)
    try:
        cmd = args.pop(0)
        if cmd == "query":
            if len(args) != 1:
                parser.error("incorrect number of arguments")
            goobk = GooBook(config)
            goobk.query(args[0].decode(ENCODING))
        elif cmd == "add":
            if len(args) == 0:
                goobk = GooBook(config)
                goobk.add_email_from(sys.stdin)
            elif len(args) == 2:
                goobk = GooBook(config)
                goobk.add_mail_contact(args[0], args[1])
        elif cmd == "reload":
            cache = Cache(config)
            cache.load(force_update=True)
        elif cmd == "dump_contacts":
            cache = Cache(config)
            cache.load()
            print ElementTree.tostring(cache.contacts, 'UTF-8')
        elif cmd == "dump_groups":
            cache = Cache(config)
            cache.load()
            print ElementTree.tostring(cache.groups, 'UTF-8')
        elif cmd == "config-template":
            print CONFIG_TEMPLATE
        else:
            parser.error('Command not recognized: %s' % cmd)
    except gdata.client.BadAuthentication, e:
        print >> sys.stderr, e # Incorrect username or password
        sys.exit(1)

if __name__ == '__main__':
    main()
