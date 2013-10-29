#!/usr/bin/env python

import os, sys, xmlrpclib, getpass

def odd(seq):
    for i, elem in enumerate(seq):
        if i % 2 == 1:
            yield elem

def even(seq):
    for i, elem in enumerate(seq):
        if i % 2 == 0:
            yield elem

def main():
    password = getpass.getpass()
    server = xmlrpclib.ServerProxy("https://shamardin:%s@www.ngrid.ru/trac/login/xmlrpc" % password)

    args = sys.argv[1:]
    if len(args) % 2 != 0 or len(args) == 0:
        print "Usage: %s PageName filename.rst [PageName2 filename2.rst ...]" % sys.argv[0]
        sys.exit(1)

    pages = dict(zip(even(args), odd(args)))
    for page in pages:
        fd = open(pages[page], "r")
        pages[page] = fd.read()
        fd.close()

    for page, content in pages.iteritems():
        print "updating", page
        server.wiki.putPage(page, "{{{\n#!rst\n" + content + "\n}}}\n", {"comment": "automatic update"})

    sys.exit(0)

if __name__ == '__main__':
    main()
