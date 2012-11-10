# vim: fileencoding=UTF-8 filetype=python ff=unix expandtab sw=4 sts=4 tw=120
# maintainer: Christer Sjöholm -- goobook AT furuvik DOT net
# authors: Marcus Nitzschke -- marcus.nitzschke AT gmx DOT com
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

import codecs
import email.parser
import email.header
import gdata.service
import itertools
import logging
import os
import pickle
import re
import sys
import time
import xml.etree.ElementTree as ET

from hcs_utils.storage import Storage

log = logging.getLogger(__name__)

CACHE_FORMAT_VERSION = '3.2'
G_MAX_SRESULTS = 9999 # Maximum number of entries to ask google for.
GDATA_VERSION = '3'
ATOM_NS = '{http://www.w3.org/2005/Atom}'
G_NS = '{http://schemas.google.com/g/2005}'
GC_NS = '{http://schemas.google.com/contact/2008}'

class GooBook(object):
    '''This class can't be used as a library as it looks now, it uses sys.stdin
       print, sys.exit() and getpass().'''
    def __init__ (self, config):
        self.__config = config
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
                groups = set(self.cache.get_group(gid).title for gid in contact.groups)
                groups = groups.difference(('System Group: My Contacts',))
                groups_str = ', '.join(('"' + g + '"' for g in groups))
                for (emailaddr, kind) in emailaddrs:
                    title = contact.title or contact.nickname or emailaddr
                    extra_str =  kind
                    if groups_str:
                        extra_str = extra_str + ' groups: ' + groups_str
                    print (u'\t'.join((emailaddr, title, extra_str))).encode(self.__config.encoding, errors='replace')
        for group in matching_groups:
            emails = ['%s <%s>' % (c.title, c.emails[0][0]) for c in group.contacts if c.emails]
            emails = ', '.join(emails)
            if not emails:
                continue
            print (u'%s\t%s (group)' % (emails, group.title)).encode(self.__config.encoding, errors='replace')

    def query_details(self, query):
        """
        Method for querying the contacts and printing
        a detailed view.
        """

        out = codecs.getwriter(self.__config.encoding)(sys.stdout, errors='replace')

        #query contacts
        matching_contacts = sorted(self.__query_contacts(query), key=lambda c: c.title)
        #query groups
        matching_groups = sorted(self.__query_groups(query), key=lambda g: g.title)
        for group in matching_groups:
            matching_contacts += group.contacts

        for contact in matching_contacts:
            print >> out, "-------------------------"
            print >> out, contact.title
            if contact.birthday:
                print >> out, "Birthday: ", contact.birthday
            if contact.phonenumbers:
                print >> out, "Phone:"
                for (number, kind) in contact.phonenumbers:
                    print >> out, "\t", number, " (" + kind + ")"
            if contact.emails:
                print >> out, "EMail:"
                emailaddrs = sorted(contact.emails)
                for (emailaddr, kind) in emailaddrs:
                    print >> out, "\t", emailaddr, " (" + kind + ")"
            if contact.im:
                print >> out, "IM:"
                for (nick, protocol) in contact.im:
                    print >> out, "\t", nick, " (", protocol, ")"
            if contact.addresses:
                print >> out, "Address:"
                for (address, kind) in contact.addresses:
                    lines = address.splitlines()
                    lines[0] = '%s ( %s )' %  (lines[0], kind)
                    print >> out, "\t" + '\n\t'.join(lines)
            if contact.groups:
                print >> out, "Groups:"
                groups = set(self.cache.get_group(gid).title for gid in contact.groups)
                groups = groups.difference(('System Group: My Contacts',))
                groups_str = '\n\t'.join(groups)
                print >> out, "\t" + groups_str


    def __query_contacts(self, query):
        match = re.compile(query, re.I).search # create a match function
        for contact in self.cache.contacts:
            if self.__config.filter_groupless_contacts and not contact.groups:
                continue # Skip contacts without groups
            if any(itertools.imap(match,
                [contact.title, contact.nickname] + [unicode(number) for (number, kind) in contact.phonenumbers])):
                yield contact
            else:
                matching_addrs = [(email, kind) for (email, kind) in contact.emails if match(email)]
                if matching_addrs:
                    contact.emails = matching_addrs # only show matching
                    yield contact

    def __query_groups(self, query):
        match = re.compile(query, re.I).search # create a match function
        for group in self.cache.groups:
            # Collect all values to match against
            all_values = (group.title,)
            if any(itertools.imap(match, all_values)):
                group.contacts = list(self.__get_group_contacts(group.id))
                yield group

    def __get_group_contacts(self, group_id):
        for contact in self.cache.contacts:
            if group_id in contact.groups:
                yield contact

    def add_mail_contact(self, name, mailaddr):
        entry = ET.Element(ATOM_NS + 'entry')
        ET.SubElement(entry, ATOM_NS + 'category', scheme='http://schemas.google.com/g/2005#kind',
                term='http://schemas.google.com/contact/2008#contact')
        fullname_e = ET.Element(G_NS + 'fullName')
        fullname_e.text = name
        ET.SubElement(entry, G_NS + 'name').append(fullname_e)
        ET.SubElement(entry, G_NS + 'email', rel='http://schemas.google.com/g/2005#other', primary='true',
                address=mailaddr)

        group_id = self.cache.get_group_by_title('System Group: My Contacts').id
        ET.SubElement(entry, GC_NS + 'groupMembershipInfo', deleted='false',
                href=group_id)

        gcont = GoogleContacts(self.__config)
        log.debug('Going to create contact name: %s email: %s' % (name, mailaddr))
        gcont.create_contact(entry)
        log.info('Created contact name: %s email: %s' % (name, mailaddr))

    def add_email_from(self, lines):
        """Add an address from From: field of a mail.
        This assumes a single mail file is supplied through.

        Args:
          lines: A generator of lines, usually a open file.

        """

        parser = email.parser.HeaderParser()
        headers = parser.parse(lines)
        if 'From' not in headers:
            print "Not a valid mail file!"
            sys.exit(2)

        (name, mailaddr) = email.utils.parseaddr(headers['From'])
        if not name:
            name = mailaddr
        else:
            # This decodes headers like "=?iso-8859-1?q?p=F6stal?="
            values = email.header.decode_header(name)
            if len(values) == 0:
                # Can't this be possible?
                name = mailaddr
            else:
                # There should be only one element anyway
                (name, encoding) = values[0]

                if encoding is not None:
                    name = name.decode(encoding)

        self.add_mail_contact(name, mailaddr)

class Cache(object):
    def __init__(self, config):
        self.__config = config
        self.contacts = None # list of Storage
        self.groups = None # list of Storage

    def load(self, force_update=False):
        """Load the cached addressbook feed, or fetch it (again) if it is
        old or missing or invalid or anyting

        Args:
          force_update: force update of cache

        """
        cache = {}

        # if cache newer than cache_expiry_hours
        if not force_update and (os.path.exists(self.__config.cache_filename) and
                ((time.time() - os.path.getmtime(self.__config.cache_filename)) <
                    (int(self.__config.cache_expiry_hours) * 60 * 60))):
            try:
                log.debug('Loading cache: ' + self.__config.cache_filename)
                cache = pickle.load(open(self.__config.cache_filename, 'rb'))
                if cache.get('goobook_cache') != CACHE_FORMAT_VERSION:
                    log.info('Detected old cache format')
                    cache = None # Old cache format
            except StandardError, err:
                log.info('Failed to read the cache file: %s', err)
                raise
        if cache:
            self.contacts = cache.get('contacts')
            self.groups = cache.get('groups')
        else:
            self.update()
        if not self.contacts:
            raise Exception('Failed to find any contacts') # TODO

    def update(self):
        log.info('Retrieving contact data from Google.')
        gc = GoogleContacts(self.__config)
        self.contacts = list(self._parse_contacts(gc.fetch_contacts()))
        self.groups = list(self._parse_groups(gc.fetch_contact_groups()))
        self.save()

    def save(self):
        """Pickle the addressbook and a timestamp

        """
        if self.contacts: # never write a empty addressbook
            cache = {'contacts': self.contacts, 'groups': self.groups, 'goobook_cache': CACHE_FORMAT_VERSION}
            pickle.dump(cache, open(self.__config.cache_filename, 'wb'))

    def get_group(self, id_):
        for group in self.groups:
            if group.id == id_:
                return group
        raise KeyError('Group: ' + id_)

    def get_group_by_title(self, title):
        for group in self.groups:
            if group.title == title:
                return group
        raise KeyError('Group: ' + title)

    @staticmethod
    def _parse_contact(entry):
        '''Extracts interesting contact info from cache.'''
        contact = Storage()
        # ID
        contact.id = entry.findtext(ATOM_NS + 'id')
        # title
        contact.title = entry.findtext(ATOM_NS + 'title')
        # nickname
        contact.nickname = entry.findtext(GC_NS + 'nickname', default='')
        # emails
        contact.emails = []
        for ent in entry.findall(G_NS + 'email'):
            label = ent.get('label') or ent.get('rel').split('#')[-1]
            contact.emails.append((ent.get('address'), label))
        # groups
        contact.groups = [e.get('href') for e in entry.findall(GC_NS + 'groupMembershipInfo') if
            e.get('deleted') == 'false']
        # phone
        contact.phonenumbers = []
        for ent in entry.findall(G_NS + 'phoneNumber'):
            label = ent.get('label') or ent.get('rel').split('#')[-1]
            contact.phonenumbers.append((ent.text, label))
        # birthday
        contact.birthday = entry.find(GC_NS + 'birthday').get('when') if entry.findall(GC_NS + 'birthday') else None
        #address
        contact.addresses = []
        for address in entry.findall(G_NS + 'structuredPostalAddress'):
            label = address.get('label') or address.get('rel').split('#')[-1]
            contact.addresses.append((address.findtext(G_NS + 'formattedAddress'), label))
        # IM
        contact.im = []
        for ent in entry.findall(G_NS + 'im'):
            protocol = ent.get('protocol')
            # Default protocol is GOOGLE_TALK
            protocol = ent.get('protocol').split('#')[-1] if protocol else "GOOGLE_TALK"
            contact.im.append((ent.get('address'), protocol))

        log.debug('Parsed contact %s', contact)
        return contact

    @staticmethod
    def _parse_group(entry):
        '''Extracts interesting group info from cache.'''
        group = Storage()
        group.id = entry.findtext(ATOM_NS + 'id')
        group.title = entry.findtext(ATOM_NS + 'title')
        log.debug('Parsed group %s', group)
        return group

    def _parse_contacts(self, raw_contacts):
        for entry in raw_contacts.findall(ATOM_NS + 'entry'):
            yield self._parse_contact(entry)

    def _parse_groups(self, raw_groups):
        for entry in raw_groups.findall(ATOM_NS + 'entry'):
            yield self._parse_group(entry)


class GoogleContacts(object):

    def __init__(self, config):
        self.__email = config.email
        self.__client = self.__get_client(config.password())

    def __get_client(self, password):
        '''Login to Google and return a ContactsClient object.

        '''
        client = gdata.service.GDataService(additional_headers={'GData-Version': GDATA_VERSION})
        client.ssl = True # TODO verify that this works
        #client.debug = True
        client.ClientLogin(username=self.__email, password=password, service='cp', source='goobook')
        log.debug('Authenticated client')
        return client

    def _get(self, query):
        res = self.__client.Get(str(query), converter=ET.fromstring)
        #TODO check not failed
        return res

    def _post(self, data, query):
        '''data is a ElementTree'''
        data = ET.tostring(data)
        log.debug('POSTing to: %s\n%s', query, data)
        res = self.__client.Post(data, str(query))
        log.debug('POST returned: %s' , res)
        #res = self.__client.Post(data, str(query), converter=str)
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

    def create_contact(self, entry):
        query = gdata.service.Query('http://www.google.com/m8/feeds/contacts/default/full')
        self._post(entry, query)

