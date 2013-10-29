# -*- encoding: utf-8 -*-

import sys
import uuid

from pilot_cli.formats import job_from_file, add_software
from pilot_cli.common import exit_codes
from pilot_cli.api import errmsg, setup_app, json_dumps, json_loads, PilotError, UnsupportedProtocolError

def main():
    options, args, log, svc = setup_app(
        usage="%prog [options] job_definition.js ...",
        description = """
    Submit a job to Pilot service and output a job URI.
    """,
        argstest=lambda args: len(args) == 1,
        logname="pilot-job-submit")

    try:
        definition = job_from_file(args[0])
        if options.software:
            add_software(definition, options.software)
    except IOError, exc:
        errmsg("Could not read file %s: %s", exc.filename, exc.strerror)
        sys.exit(exit_codes.file_error)
    except ValueError, exc:
        errmsg("Job parsing error: %s", str(exc))
        sys.exit(exit_codes.parsing_error)

    try:
        svc.refresh_delegation(options.delegation_id, options.proxy)
        use_delegations = True
    except UnsupportedProtocolError, exc:
        use_delegations = False        
    except PilotError, exc:
        errmsg("Failed to refresh delegation: %s" % str(exc))
        sys.exit(exit_codes.delegation_error)

    log.debug("job definition (raw):\n%s", definition)
    if use_delegations:
        request = {
            "definition": definition,
            "delegation_id": options.delegation_id,
        }
        response, content = svc.post("/jobs", json_dumps(request))
    else:
        try:
            request = {
                "definition": definition,
                "proxy": open(options.proxy, "rb").read()
            }
        except IOError, exc:
            errmsg("Failed to load proxy certificate %s: %s", options.proxy, str(exc))
            sys.exit(exit_codes.proxy_error)
        response, content = svc.post("/jobs/", json_dumps(request))

    try:
        job_uri = response['location']
    except KeyError, exc:
        job_uri = json_loads(content)[0]['uri']

    log.debug("New job URI: %s", job_uri)

    request = { "operation": { "op": "start",
                               "id": str(uuid.uuid4()) } }
    response, content = svc.put(job_uri, json_dumps(request))

    if not options.quiet:
        print "Job was successfully submitted to Pilot service."
        print "Job URI:\n"
        print "    %s\n" % job_uri
    else:
        print job_uri
    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
