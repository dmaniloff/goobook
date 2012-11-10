#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# vim: fileencoding=UTF-8 filetype=python ff=unix et ts=4 sw=4 sts=4 tw=120
# author: Christer Sjöholm -- hcs AT furuvik DOT net

from __future__ import absolute_import

import argparse
import gdata.client
import gdata.service
import goobook.config
import logging
import pkg_resources
import sys
import xml.etree.ElementTree as ElementTree

from goobook.goobook import GooBook, Cache, GoogleContacts

log = logging.getLogger(__name__)

CONFIG_FILE = '~/.goobookrc'

def main():
    parser = argparse.ArgumentParser(description='Search you Google contacts from mutt or the command-line.')
    parser.add_argument('-c', '--config', help='Specify alternative configuration file.', metavar="FILE")
    parser.add_argument('-v', '--verbose', dest="logging_level", action='store_const',
            const=logging.INFO, help='Be verbose about what is going on (stderr).')
    parser.add_argument('-V', '--version',
            action='version',
            version='%%(prog)s %s' % pkg_resources.get_distribution("goobook").version,
            help="Print version and exit")
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

    parser_query_details = subparsers.add_parser('dquery',
            description='Search contacts using query (regex) and print out all info.')
    parser_query_details.add_argument('query', help='regex to search for.')
    parser_query_details.set_defaults(func=do_query_details)

    parser_reload = subparsers.add_parser('reload',
            description='Force reload of the cache.')
    parser_reload.set_defaults(func=do_reload)

    args = [arg.decode(goobook.config.ENCODING) for arg in sys.argv[1:]]
    args = parser.parse_args(args)

    logging.basicConfig(level=args.logging_level)

    try:
        if args.func == do_config_template:
            config = None
        else:
            config = goobook.config.read_config(args.config)
        args.func(config, args)
    except goobook.config.ConfigError, err:
        sys.exit(u'Configuration error: ' + unicode(err))
    except gdata.service.BadAuthentication, err:
        sys.exit(err) # Incorrect username or password

##############################################################################
# sub commands

def do_add(config, args):
    goobk = GooBook(config)
    if args.name and args.email:
        goobk.add_mail_contact(args.name, args.email)
    else:
        goobk.add_email_from(sys.stdin)

def do_config_template(config, args):
    print goobook.config.TEMPLATE

def do_dump_contacts(config, args):
    goco = GoogleContacts(config)
    print ElementTree.tostring(goco.fetch_contacts(), 'UTF-8')

def do_dump_groups(config, args):
    goco = GoogleContacts(config)
    print ElementTree.tostring(goco.fetch_contact_groups() , 'UTF-8')

def do_query(config, args):
    goobk = GooBook(config)
    goobk.query(args.query)

def do_query_details(config, args):
    goobk = GooBook(config)
    goobk.query_details(args.query)

def do_reload(config, args):
    cache = Cache(config)
    cache.load(force_update=True)

if __name__ == '__main__':
    main()
