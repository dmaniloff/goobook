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

'''\
The idea is make an interface to google contacts that mimics the behaviour of
abook for mutt. It's developed in python and uses the fine
google data api (gdata).
'''

import email.header
import gdata.service
import itertools
import locale
import logging
import getpass
import sys
import os
import re
import time

try:
    import simplejson
    json = simplejson # this hushes pyflakes
except ImportError:
    import json

from gdata.contacts.client import ContactsClient, ContactsQuery
from gdata.contacts.data import ContactEntry
from gdata.data import Email, Name, FullName
from hcs_utils.memoize import memoize
from hcs_utils.storage import Storage
from hcs_utils.json import jget

log = logging.getLogger(__name__)

CACHE_FORMAT_VERSION = '1.2'
ENCODING = locale.getpreferredencoding()
G_MAX_SRESULTS = 9999 # Maximum number of entries to ask google for.

class GooBook(object):
    '''This class can't be used as a library as it looks now, it uses sys.stdin
       print, sys.exit() and getpass().'''
    def __init__ (self, config):
        self.cache = Cache(config)
        self.cache.load()

    def query(self, query):
        """Do the query, and print it out in

        """
        #query contacts
        matching_contacts = sorted(self.__query_contacts(query), key=lambda c: c.title)
        #query groups
        matching_groups = sorted(self.__query_groups(query), key=lambda g: g.title)
        # mutt's query_command expects the first line to be a message,
        # which it discards.
        print "\n",
        for contact in matching_contacts:
            if contact.emails:
                emailaddrs = sorted(contact.emails)
                for emailaddr in emailaddrs:
                    print (u'%s\t%s' % (emailaddr, contact.title)).encode(ENCODING)
        for group in matching_groups:
            emails = ['%s <%s>' % (c.title, c.emails[0]) for c in group.contacts if c.emails]
            emails = ', '.join(emails)
            if not emails:
                continue
            print (u'%s\t%s (group)' % (emails, group.title)).encode(ENCODING)

#    @property
#    def password(self):
#        if not self.config.password:
#            self.config.password = getpass.getpass()
#        return self.config.password

    @staticmethod
    def __parse_contact(entry):
        '''Extracts interesting contact info from cache.'''
        contact = Storage()
        contact.id = entry['id']['$t']
        contact.title = entry['title']['$t']
        contact.nickname = jget(entry, '', 'gContact$nickname', '$t')
        contact.emails = [e['address'] for e in entry.get('gd$email', [])]
        contact.groups = [e['href'] for e in entry.get('gContact$groupMembershipInfo', []) if e['deleted'] == 'false']
        log.debug('Parsed contact %s', contact)
        return contact

    @staticmethod
    def __parse_group(entry):
        '''Extracts interesting group info from cache.'''
        group = Storage()
        group.id = entry['id']['$t']
        group.title = entry['title']['$t']
        log.debug('Parsed group %s', group)
        return group

    def itercontacts(self):
        for entry in self.cache.contacts['feed']['entry']:
            yield self.__parse_contact(entry)

    def itergroups(self):
        for entry in self.cache.groups['feed']['entry']:
            yield self.__parse_group(entry)

    def __query_contacts(self, query):
        match = re.compile(query, re.I).search # create a match function
        for contact in self.itercontacts():
            # Collect all values to match against
            all_values = itertools.chain((contact.title, contact.nickname),
                                         contact.emails)
            if any(itertools.imap(match, all_values)):
                yield contact

    def __query_groups(self, query):
        match = re.compile(query, re.I).search # create a match function
        for group in self.itergroups():
            # Collect all values to match against
            all_values = (group.title,)
            if any(itertools.imap(match, all_values)):
                group.contacts = list(self.__get_group_contacts(group.id))
                yield group

    def __get_group_contacts(self, group_id):
        for contact in self.itercontacts():
            if group_id in contact.groups:
                yield contact

    def add(self, name, email): # TODO
        pass

    def add_email_from(self, lines):
        """Add an address from From: field of a mail.
        This assumes a single mail file is supplied through.

        Args:
          lines: A generator of lines, usually a open file.

        """
        from_line = ""
        for line in lines:
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
        self.add(name, mailaddr)

#    def add(self):
#        """Add an address from From: field of a mail.
#        This assumes a single mail file is supplied through stdin.
#
#        """
#        from_line = ""
#        for line in sys.stdin:
#            if line.startswith("From: "):
#                from_line = line
#                break
#        if from_line == "":
#            print "Not a valid mail file!"
#            sys.exit(2)
#        #Parse From: line
#        #Take care of non ascii header
#        from_line = unicode(email.header.make_header(email.header.decode_header(from_line)))
#        #Parse the From line
#        (name, mailaddr) = email.utils.parseaddr(from_line)
#        if not name:
#            name = mailaddr
#        #save to contacts
#        client = self.__get_client()
#        new_contact = ContactEntry(name=Name(full_name=FullName(text=name)))
#        new_contact.email.append(Email(address=mailaddr, rel='http://schemas.google.com/g/2005#home', primary='true'))
#        client.create_contact(new_contact)
#        print 'Created contact:', name.encode(ENCODING), mailaddr.encode(ENCODING)


class Cache(object):
    def __init__(self, config):
        self.__config = config
        self.contacts = {}
        self.groups = {}

    def load(self, force_update=False):
        """Load the cached addressbook feed, or fetch it (again) if it is
        old or missing or invalid or anyting

        Args:
          force_update: force update of cache

        """
        cache = None

        # if cache newer than cache_expiry_hours
        if not force_update and (os.path.exists(self.__config.cache_filename) and
                ((time.time() - os.path.getmtime(self.__config.cache_filename)) <
                    (self.__config.cache_expiry_hours * 60 * 60))):
            try:
                cache = json.load(open(self.__config.cache_filename))
                if cache.get('goobook_cache') != CACHE_FORMAT_VERSION:
                    cache = None # Old cache format
            except ValueError:
                pass # Failed to read JSON file.
        if cache:
            self.contacts = cache.get('contacts')
            self.groups = cache.get('groups')
        else:
            gc = GoogleContacts(self.__config.email, self.__config.password)
            self.contacts = gc.fetch_contacts()
            self.groups = gc.fetch_contact_groups()
            self.save()
        if not self.contacts:
            raise Exception('Failed to find any contacts') # TODO

    def save(self):
        """Pickle the addressbook and a timestamp

        """
        if self.contacts: # never write a empty addressbook
            cache = {'contacts': self.contacts, 'groups': self.groups, 'goobook_cache': CACHE_FORMAT_VERSION}
            json.dump(cache, open(self.__config.cache_filename, 'w'), indent=2)

class GoogleContacts(object):

    def __init__(self, email, password):
        self.__email = email
        self.__client = self.__get_client(password)

    def __get_client(self, password):
        '''Login to Google and return a ContactsClient object.

        '''
        if not self.__email or not password:
            print >> sys.stderr, "ERROR: Missing email or password"
            sys.exit(1) #TODO
        client = gdata.service.GDataService(additional_headers={'GData-Version': '3'})
        client.ssl = True # TODO verify that this works
        client.ClientLogin(username=self.__email, password=password, service='cp', source='goobook')
        return client

    def _get(self, query):
        query.alt = 'json'
        client = self.__client
        json_str = client.Get(str(query), converter=str)
        res = json.loads(json_str)
        #TODO check not failed
        return res

    def fetch_contacts(self):
        query = gdata.service.Query('http://www.google.com/m8/feeds/contacts/default/full')
        query.max_results = G_MAX_SRESULTS
        res = self._get(query)
        return res

    def fetch_contact_groups(self):
        query = gdata.service.Query('http://www.google.com/m8/feeds/groups/default/full')
        query.max_results = G_MAX_SRESULTS
        res = self._get(query)
        return res
