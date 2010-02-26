#!/usr/bin/env python2
# vim: fileencoding=UTF-8 filetype=python ff=unix expandtab sw=4 sts=4 tw=120
# maintainer: Christer Sjöholm -- goobook AT furuvik DOT net
#
# Copyright (C) 2009  Carlos José Barroso
# Copyright (C) 2010  Christer Sjöholm
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
The idea is make an interface to google contacts that mimics the behaviour of
abook for mutt. It's developed in python and uses the fine
google data api (gdata).
'''

import codecs
import email.header
import locale
import optparse
import sys
import os
import re
import time
import ConfigParser
from netrc import netrc
from os.path import realpath, expanduser

import gdata
from gdata.contacts.client import ContactsClient, ContactsQuery
from gdata.contacts.data import ContactEntry
from gdata.data import Email, Name, FullName

#from gdata.contacts.service import ContactsService, ContactsQuery
#import atom

CONFIG_FILE = '~/.goobookrc'
CONFIG_EXAMPLE = '''[DEFAULT]
# If not given here, email and password is taken from .netrc using
# machine google.com
email: user@gmail.com
password: top secret
# The following are optional, defaults are shown
;max_results: 9999
;cache_filename: ~/.goobook_cache
;cache_expiry_hours: 24
'''

ENCODING = locale.getpreferredencoding()

class GooBook(object):
    '''This class can't be used as a library as it looks now, it uses sys.stdin
       print and sys.exit().'''
    def __init__ (self, config):
        self.email = config['email']
        self.password = config['password']
        self.max_results = config['max_results']
        self.cache_filename = config['cache_filename']
        self.cache_filename = realpath(expanduser(self.cache_filename))
        self.cache_expiry_hours = config['cache_expiry_hours']
        self.contacts = [] #[{fieldname: value}]

    def __get_client(self):
        '''Login to Google and return a ContactsClient object.
        '''
        if not self.email or not self.password:
            print >> sys.stderr, "ERROR: Missing email or password"
            sys.exit(1)
        client = ContactsClient()
        client.ssl = True
        client.ClientLogin(email=self.email, password=self.password, service='cp', source='goobook')
        return client

    def query(self, query):
        """
        Do the query, and print it out in
        """
        self.load()
        match = re.compile(query, re.I).search
        result = []
        for contact in self.contacts:
            for value in contact.itervalues():
                if value and match(value):
                    result.append(contact)
                    break

        #sort contacts
        result.sort(key=lambda c: c['name'])

        # mutt's query_command expects the first line to be a message,
        # which it discards.
        print "\n",
        for contact in result:
            name = contact['name'].encode(ENCODING)
            if 'email' in contact and contact['email'].strip():
                emailaddrs = sorted(contact['email'].split(','))
                for email in emailaddrs:
                    email = email.encode(ENCODING)
                    print "%s\t%s" % (email, name)

    def load(self):
        """
        Load the cached addressbook feed, or fetch it (again) if it is
        old or missing or invalid or anyting
        """
        try:
            abook = AbookDatabase(self.cache_filename)
            self.contacts = list(abook.get_contacts())
        except (IOError, AbookError):
            self.fetch()
            self.store()
        else:
            # if cache older than cache_expiry_hours
            if ((time.time() - os.path.getmtime(self.cache_filename)) >
                (self.cache_expiry_hours * 60 *60)):
                self.fetch()
                self.store()


    def fetch(self):
        """
        Actually go out on the wire and fetch the addressbook.

        """

        client = self.__get_client()
        query = ContactsQuery(max_results=self.max_results)
        contacts_ = client.get_contacts(query=query)
        contacts = []
        for ent in contacts_.entry:
            contact = {}
            contact['name'] = ent.title.text
            emails = [email.address for email in ent.email]
            contact['email'] = ','.join(emails)
            if ent.nickname:
                contact['nick'] = ent.nickname.text
            contacts.append(contact)
        self.contacts = contacts

    def store(self):
        """
        Pickle the addressbook and a timestamp
        """
        if self.contacts: # never store a empty addressbook
            abook = AbookDatabase(self.cache_filename)
            abook.write_contacts(self.contacts)

    def add(self):
        """
        Add an address from From: field of a mail.
        This assumes a single mail file is supplied through stdin.
        """

        from_line = ""
        for line in sys.stdin:
            if line.startswith("From: "):
                from_line = line
                break
        if from_line == "":
            print "Not a valid mail file!"
            sys.exit(2)
        #Parse From: line
        #Take care of non ascii header
        from_line = unicode(email.header.make_header(email.header.decode_header(from_line)))
        #Parse the From line
        (name, mailaddr) = email.utils.parseaddr(from_line)
        if not name:
            name = mailaddr
        #save to contacts
        client = self.__get_client()
        new_contact = ContactEntry(name=Name(full_name=FullName(text=name)))
        new_contact.email.append(Email(address=mailaddr, rel='http://schemas.google.com/g/2005#home', primary='true'))
        client.create_contact(new_contact)
        print 'Created contact:', name.encode(ENCODING), mailaddr.encode(ENCODING)

class AbookDatabase(object):
    '''Parse and generate Abook compatible addressbook files.

    abooks implementation can be seen here:
    http://abook.cvs.sourceforge.net/viewvc/abook/abook/database.c
    '''

    def __init__(self, filename):
        self.filename = filename

    def get_contacts(self):
        '''yields a {fieldname: value} for each contact. '''
        for (name, sect) in self.read().iteritems():
            if name != 'format':
                yield sect

    def read(self):
        ''' read the abook file and return a list of its sections.
            [{section: {fieldname: value}}]'''
        sections = {}# {sectionname: {fieldname: value}}
        with codecs.open(self.filename, encoding=ENCODING) as inp:
            section = None
            for line in inp:
                line = line.strip()
                if not line or line[0] == '#':
                    pass
                elif line[0] == '[':
                    sectionname = line.strip('[]')
                    if sectionname in sections:
                        raise AbookError('ERROR parsing %s, duplicate '
                            'section: %s' % (self.filename, sectionname))
                    sections[sectionname] = section = {}
                elif section == None:
                    raise AbookError('ERROR parsing %s, no section '
                            'header.' % self.filename)
                elif '=' in line:
                    (name, value) = line.split('=', 1)
                    if name in section:
                        raise AbookError('ERROR parsing %s, duplicate '
                            'field: %s' % (self.filename, name))
                    section[name] = value
                else:
                    raise AbookError('Failed to parse line in %s: %s' %
                                           (self.filename, repr(line)))
        return sections

    def write_contacts(self, contacts):
        '''Write the list of contacts [{fieldname: value}] to disk'''
        sections = {}
        for (i, contact) in enumerate(contacts):
            sections[i] = contact
        self.write(sections)

    def write(self, sections):
        '''sections is a {sectionname: {fieldname: value}}'''
        with codecs.open(self.filename, 'w', encoding=ENCODING) as out:
            out.write('[format]\n'
                      'program=goobook\n'
                      'version=2.0.0\n\n')
            for (sectionname, section) in sections.iteritems():
                out.write('[%s]\n' % sectionname)
                for (name, value) in section.iteritems():
                    out.write('%s=%s\n' % (name, value))
                out.write('\n')

class AbookError(Exception):
    '''Exception thrown when failing to parse a abook file.'''
    pass

def read_config(config_file):
    ''' Reads the ~/.goobookrc and ~/.netrc.
        returns the configuration as a dictionary.
    '''
    config = { # Default values
        'email': '',
        'password': '',
        'max_results': '9999',
        'cache_filename': '~/.goobook_cache',
        'cache_expiry_hours': '24',
        }
    if os.path.lexists(config_file):
        try:
            parser = ConfigParser.SafeConfigParser()
            parser.readfp(open(os.path.expanduser(config_file)))
            config.update(dict(parser.items('DEFAULT', raw=True)))
        except (IOError, ConfigParser.ParsingError):
            print >> sys.stderr, "Failed to read %s\n\nExample:\n\n%s" % (
                config_file, CONFIG_EXAMPLE)
            sys.exit(1)
    if not config.get('email') or not config.get('password'):
        auth = netrc().authenticators('google.com')
        if auth:
            login = auth[0]
            password = auth[2]
            if not config.get('email'):
                config['email'] = login
            if not config.get('password'):
                config['password'] = password
    return config


def main():

    class MyParser(optparse.OptionParser):
        def format_epilog(self, formatter):
            return self.epilog
    usage = 'usage: %prog [options] <command> [<arg>]'
    description = 'Search you Google contacts from mutt or the command-line.'
    epilog = '''\
Commands:
  add <mail.at.stdin>
  reload
  query <name>

'''
    parser = MyParser(usage=usage, description=description, epilog=epilog)
    parser.set_defaults(config_file=CONFIG_FILE)
    parser.add_option("-c", "--config", dest="config_file",
                    help="Specify alternative configuration file.", metavar="FILE")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        sys.exit(1)
    config = read_config(options.config_file)
    goobk = GooBook(config)
    try:
        cmd = args.pop(0)
        if cmd == "query":
            if len(args) != 1:
                parser.error("incorrect number of arguments")
            goobk.query(args[0].decode(ENCODING))
        elif cmd == "add":
            goobk.add()
        elif cmd == "reload":
            goobk.fetch()
            goobk.store()
        else:
            parser.error('Command not recognized: %s' % cmd)
    except gdata.client.BadAuthentication, e:
        print >> sys.stderr, e # Incorrect username or password
        sys.exit(1)

if __name__ == '__main__':
    main()
