# -*- encoding: utf-8 -*-

import sys

from pilot_cli.api import setup_app, json_loads
from pilot_cli.common import exit_codes

def main():
    options, _, _, svc = setup_app(
        description = """Cancel all owned jobs. This command marks
        all jobs as deleted, which causes them to abort after some
        short time. The job URIs will still be valid until they are
        grabage collected by pilot service.""",
        argstest = lambda args: len(args) == 0,
        logname="pilot-cancel-my-jobs")

    _, content = svc.get("/jobs")
    for job in json_loads(content):
        uri = job['uri']
        svc.delete(uri)
        if not options.quiet:
            print "Removed job %s" % uri

    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
