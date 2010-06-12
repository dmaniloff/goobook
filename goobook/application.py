#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# vim: fileencoding=UTF-8 filetype=python ff=unix et ts=4 sw=4 sts=4 tw=120
# author: Christer Sjöholm -- hcs AT furuvik DOT net

from __future__ import absolute_import

import argparse
import gdata.client
import goobook.config
import locale
import logging
import sys
import xml.etree.ElementTree as ElementTree

from goobook.goobook import GooBook, Cache, GoogleContacts

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
    parser = argparse.ArgumentParser(description='Search you Google contacts from mutt or the command-line.')
    parser.add_argument('-c', '--config', help='Specify alternative configuration file.', metavar="FILE")
    parser.add_argument('-v', '--verbose', dest="logging_level", action='store_const',
            const=logging.INFO, help='Be verbose about what is going on (stderr).')
    parser.add_argument('-d', '--debug', dest="logging_level", action='store_const',
            const=logging.DEBUG, help='Output debug info (stderr).')
    parser.set_defaults(config=CONFIG_FILE, logging_level=logging.ERROR)

    subparsers = parser.add_subparsers()

    parser_add = subparsers.add_parser('add',
            description='Create new contact, if name and email is not given the'
                        ' sender of a mail read from stdin will be used.')
    parser_add.add_argument('name', nargs='?', metavar='NAME',
            help='Name to use.')
    parser_add.add_argument('email', nargs='?', metavar='EMAIL',
            help='E-mail to use.')
    parser_add.set_defaults(func=do_add)

    parser_config_template = subparsers.add_parser('config-template',
            description='Prints a template for .goobookrc to stdout')
    parser_config_template.set_defaults(func=do_config_template)

    parser_dump_contacts = subparsers.add_parser('dump_contacts',
            description='Dump contacts as XML.')
    parser_dump_contacts.set_defaults(func=do_dump_contacts)

    parser_dump_groups = subparsers.add_parser('dump_groups',
            description='Dump groups as XML.')
    parser_dump_groups.set_defaults(func=do_dump_groups)

    parser_query = subparsers.add_parser('query',
            description='Search contacts using query (regex).')
    parser_query.add_argument('query', help='regex to search for.', metavar='QUERY')
    parser_query.set_defaults(func=do_query)

    parser_reload = subparsers.add_parser('reload',
            description='Force reload of the cache.')
    parser_reload.set_defaults(func=do_reload)

    args = [arg.decode(ENCODING) for arg in sys.argv[1:]]
    args = parser.parse_args(args)

    logging.basicConfig(level=args.logging_level)

    try:
        config = goobook.config. read_config(args.config)
    except goobook.config.ConfigError, err:
        sys.exit(err)

    try:
        args.func(config, args)
    except gdata.client.BadAuthentication, e:
        print >> sys.stderr, e # Incorrect username or password
        sys.exit(1)

##############################################################################
# sub commands

def do_add(config, args):
    goobk = GooBook(config)
    if args.name and args.email:
        goobk.add_mail_contact(args.name, args.email)
    else:
        goobk.add_email_from(sys.stdin)

def do_config_template(config, args):
    print CONFIG_TEMPLATE

def do_dump_contacts(config, args):
    goco = GoogleContacts(config)
    print ElementTree.tostring(goco.fetch_contacts(), 'UTF-8')

def do_dump_groups(config, args):
    goco = GoogleContacts(config)
    print ElementTree.tostring(goco.fetch_contact_groups() , 'UTF-8')

def do_query(config, args):
    goobk = GooBook(config)
    goobk.query(args.query)

def do_reload(config, args):
    cache = Cache(config)
    cache.load(force_update=True)

if __name__ == '__main__':
    main()
