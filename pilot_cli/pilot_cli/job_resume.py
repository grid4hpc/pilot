# -*- encoding: utf-8 -*-

import sys
import uuid

from pilot_cli.common import exit_codes
from pilot_cli.api import setup_app, json_dumps

def main():
    options, args, _, svc = setup_app(
        usage = "%prog [options] URI ...",
        description = """
        Pause a running job. All running tasks will continue execution, no
        new tasks will be started until the job is resumed.
        """,
        argstest = lambda args: len(args) == 1,
        logname = "pilot-job-pause")

    job_uri = args[0]
    request = { "operation": { "op": "start",
                               "id": str(uuid.uuid4()) } }
    svc.put(job_uri, json_dumps(request))

    if not options.quiet:
        print "Sent a request to resume execution of job %s" % job_uri

    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
