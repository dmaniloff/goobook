#!/usr/bin/env python
import gdata.contacts.service
from optparse import OptionParser
import sys
import os
parser = OptionParser()
parser.add_option("-A", "--add-address", action="store_false",
        help="Modo de parseo de mensajes para agregar direcciones")


if len(sys.argv) < 2:
    sys.exit(0)


client = gdata.contacts.service.ContactsService()
client.ClientLogin('cjbarroso@gmail.com', '57z!bW*-jsH9')
cadBusq = sys.argv[1]
query = gdata.contacts.service.ContactsQuery()
query.max_results='9999'
feed = client.GetContactsFeed(query.ToUri())
agenda = []
for e in feed.entry:
    # checkeos y resumenes
    for i in e.email:
        if e.title.text:
            agenda.append("%s\t%s"%(e.title.text,i.address))
        else:
            agenda.append("%s\t%s"%(i.address,i.address))


if agenda:
    for e in agenda:
        if cadBusq in e:
            print e
else:
    print "No Encontrado"
