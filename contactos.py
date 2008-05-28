#!/usr/bin/env python
import sys
import os
import re
import pickle
from datetime import datetime

from gdata.contacts.service import ContactsService, ContactsQuery


class GooBook(object):
    def __init__ (self, username, password, max_results, cache_filename):
        self.username = username
        self.password = password
        self.max_results = max_results
        self.cache_filename = cache_filename

    def query(self, query):
        """
        Do the query, and print it out in 
        """
        match = re.compile(query, re.I).search
        feed = self.load()
        for entry in feed.entry:
            name = entry.title.text or ''
            name_matches = match(name)
            for email in entry.email:
                address = email.address
                primary = email.primary
                if (name_matches and primary == 'true') \
                        or (not name_matches and match(address)):
                    print "%s\t%s" % (name or address, address)
            
    def load(self):
        """
        Load the cached addressbook feed, or fetch it (again) if it is
        old or missing or invalid or anyting
        """
        try:
            picklefile = file(self.cache_filename, 'rb')
        except IOError:
            # we should probably catch picke errors too...
            feed = self.fetch()
            self.store(feed)
        else:
            stamp, feed = pickle.load(picklefile)
            if (datetime.now() - stamp).days:
                feed = self.fetch()
                self.store(feed)
        return feed

    def fetch(self):
        """
        Actually go out on the wire and fetch the addressbook. 
        """
        client = ContactsService()
        client.ClientLogin(self.username, self.password)
        query = ContactsQuery()
        query.max_results = self.max_results
        feed = client.GetContactsFeed(query.ToUri())
        return feed

    def store(self, adbk):
        """
        Pickle the addressbook and a timestamp
        """
        picklefile = file(self.cache_filename, 'wb')
        stamp = datetime.now()
        pickle.dump((stamp, adbk), picklefile)
        

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    
    try:
        from settings import USERNAME, PASSWORD, MAX_RESULTS, CACHE_FILENAME
    except ImportError:
        raise RuntimeError("Please create a valid settings.py"
                           " (look at settings_example.py for inspiration)")
    else:
        CACHE_FILENAME = os.path.realpath(os.path.expanduser(CACHE_FILENAME))

    goobk = GooBook(USERNAME, PASSWORD, MAX_RESULTS, CACHE_FILENAME)
    goobk.query(sys.argv[1])
