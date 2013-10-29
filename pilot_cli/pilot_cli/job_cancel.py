# -*- encoding: utf-8 -*-

import sys

from pilot_cli.api import setup_app
from pilot_cli.common import exit_codes

def main():
    options, args, _, svc = setup_app(
        usage="%prog [options] URI ...",
        description = """
        Cancel a running job.
        """,
        argstest=lambda args: len(args) == 1,
        logname="pilot-job-cancel")

    job_uri = args[0]
    svc.delete(job_uri)

    if not options.quiet:
        print "Removed job %s" % job_uri

    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
