# -*- encoding: utf-8 -*-

import sys

from pilot.lib import certlib ; certlib.monkey()
from pilot_cli import proxylib

key, chain = proxylib.load_proxy(open(sys.argv[1]).read())
for n, cert in enumerate(chain):
    print "Cert #%d: %s" % (n+1, cert.get_subject())
    if str(cert.get_subject()).endswith("CN=Lev Shamardin"):
        print "Skipping"
        continue
    print "Issuer: %s" % (cert.get_issuer())
    for i in xrange(0, cert.get_ext_count()):
        ext = cert.get_ext_at(i)
        name = ext.get_name()
        if name == "UNDEF":
            name = ext.get_object().get_oid()        
        print " *", i, name, ext.get_value()
