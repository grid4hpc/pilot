# -*- encoding: utf-8 -*-

import sys
import types

from pilot_cli.formats import job_from_file, add_software
from pilot_cli.common import exit_codes
from pilot_cli.api import errmsg, setup_app, json_dumps, json_loads, PilotError, UnsupportedProtocolError

def gram_contact(resource):
    contact = resource['host']
    if resource.get('port', None):
        contact += ':%s' % resource['port']
    contact += '/%(lrms_type)s-%(queue)s' % resource
    return contact

def main():
    options, args, log, svc = setup_app(
        usage="%prog [options] job_definition.js ...",
        description = """
    Matchmake a job using a pilot service and output if the job is
    runnable and all matching resources for all tasks.    
    """,
        argstest=lambda args: len(args) == 1,
        logname="pilot-job-matchmake")

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

    job_id = job_uri.strip("/").split("/")[-1]
    try:
        response, content = svc.get('/v2/jobs/%s/resources' % job_id)
        if options.json:
            print content
            sys.exit(exit_codes.success)

        info = json_loads(content)

        if options.quiet:
            if info['runnable']:
                print 'runnable: true'
            else:
                print 'runnable: false'
            for task in info['resources']:
                line = '%s: ' % task['task_id']
                line += ', '.join(gram_contact(resource) for resource in task['resources'])
                print line
            sys.exit(exit_codes.success)

        if info['runnable']:
            print "Job can be executed."
        else:
            print "Job cannot be executed."
        print
        for task in info['resources']:
            print "Task %s:" % task['task_id']
            if len(task['resources']) != 0:
                for resource in task['resources']:
                    if type(resource) not in types.StringTypes:
                        print " * %s" % gram_contact(resource)
                    else:
                        print " * %s" % resource
            else:
                print " - No compatible resources"
        sys.exit(exit_codes.success)
    finally:
        svc.delete(job_uri)


if __name__ == '__main__':
    main()
