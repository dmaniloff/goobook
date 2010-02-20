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
import sys
import os
import re
import time
import ConfigParser
from netrc import netrc
from os.path import realpath, expanduser
from gdata.contacts.client import ContactsClient, ContactsQuery
from gdata.contacts.data import ContactEntry
from gdata.data import Email, Name, FullName

#from gdata.contacts.service import ContactsService, ContactsQuery
#import atom

CONFIG_PATH = '~/.goobookrc'
CONFIG_EXAMPLE = '''[DEFAULT]
#If not given here, email and password is taken from .netrc using host=google.com
email: user@gmail.com
password: top secret
#The following are optional, defaults are shown
;max_results: 9999
;cache_filename: ~/.goobook_cache
;cache_expiry_hours: 24
'''

class GooBook(object):
    '''This class can't be used as a library as it looks now, it uses sys.stdin
       print and sys.exit().'''
    def __init__ (self, config):
        self.email = config.get('DEFAULT', 'email')
        self.password = config.get('DEFAULT', 'password')
        self.max_results = config.get('DEFAULT', 'max_results')
        self.cache_filename = config.get('DEFAULT', 'cache_filename')
        self.cache_filename = realpath(expanduser(self.cache_filename))
        self.cache_expiry_hours = config.get('DEFAULT', 'cache_expiry_hours')
        self.contacts = [] #[{fieldname: value}]

    def __get_client(self):
        if not self.email or not self.password:
            auth = netrc().authenticators('google.com')
            if auth:
                (login, account, password) = auth
                if not self.email:
                    self.email = login
                if not self.password:
                    self.password = password
        if not self.email or not self.password:
            print >> sys.stderr, "Missing email or password"
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
            if 'email' in contact and contact['email'].strip():
                emailaddrs = sorted(contact['email'].split(','))
                for email in emailaddrs:
                    print "%s\t%s" % (email, contact['name'])

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
        print 'Created contact:', name, mailaddr

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
        with codecs.open(self.filename, encoding=locale.getpreferredencoding()) as inp:
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
        with codecs.open(self.filename, 'w', encoding=locale.getpreferredencoding()) as out:
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

def usage():
    print """\
Usage: goobook.py <command> [<arg>]
Commands:
   reload
   query <name>
   add <mail.at.stdin>\
"""
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        usage()
    config_defaults = {
        'email': '',
        'password': '',
        'max_results': '9999',
        'cache_filename': '~/.goobook_cache',
        'cache_expiry_hours': '24',
        }
    config = ConfigParser.SafeConfigParser(defaults=config_defaults)
    try:
        config.readfp(open(os.path.expanduser(CONFIG_PATH)))
    except (IOError, ConfigParser.ParsingError):
        print >> sys.stderr, "Failed to read %s\n\nExample:\n\n%s" % (
            CONFIG_PATH, CONFIG_EXAMPLE)
        sys.exit(1)
    goobk = GooBook(config)
    if sys.argv[1] == "query":
        if len(sys.argv) < 3:
            usage()
        goobk.query(sys.argv[2])
    elif sys.argv[1] == "add":
        goobk.add()
    elif sys.argv[1] == "reload":
        goobk.fetch()
        goobk.store()
    else:
        usage()

if __name__ == '__main__':
    main()
