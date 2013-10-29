# -*- encoding: utf-8 -*-

import sys, datetime, pprint, time

from pilot_cli import api
from pilot_cli.api import setup_app
from pilot_cli.common import exit_codes

def main():
    options, args, log, svc = setup_app(
        usage = "%prog [options] count ...",
        description = """
        Try to burn server with requests.
        """,
        argstest = lambda args: len(args) == 1,
        logname = 'exhaust')

    count = int(args[0])
    start = time.time()
    for i in xrange(0, count):
        svc.server_version()
    end = time.time()
    print "Sent %d requests in %.3f seconds (%.3f req/second)" % (
        count, end-start, count/(end-start))
    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
