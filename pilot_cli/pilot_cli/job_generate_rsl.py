# -*- encoding: utf-8 -*-

import sys

from pilot_cli.formats import job_from_file, add_software
from pilot_cli.common import exit_codes
from pilot_cli.api import errmsg, setup_app, json_dumps, json_loads

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

    svc.refresh_delegation(options.delegation_id, options.proxy)

    log.debug("job definition (raw):\n%s", definition)
    request = {
        "definition": definition,
        "delegation_id": options.delegation_id,
    }

    response, content = svc.post("/jobs", json_dumps(request))
    try:
        job_uri = response['location']
    except KeyError, exc:
        job_uri = json_loads(content)[0]['uri']

    job_id = job_uri.strip("/").split("/")[-1]
    try:
        response, content = svc.get('/v2/jobs/%s/RSL' % job_id)
        if options.json:
            print content
            sys.exit(exit_codes.success)

        info = json_loads(content)
        output = []
        for task_id in sorted(info.keys()):
            task_lines = []
            task_lines.append("Task: %s" % task_id)                
            if info[task_id]['RSL'] is None:
                task_lines.append("No compatible resources")
            else:
                if "RSL" in info[task_id]:
                    task_lines.append("RSL:")
                    task_lines.append(info[task_id]['RSL'])
                if "submission_args" in info[task_id]:
                    task_lines.append("Submission command:")
                    task_lines.append("pyglobusrun-ws %s" % info[task_id]['submission_args'])
                if "Resource" in info[task_id]:
                    task_lines.append("Resource contact: %s" % info[task_id]["Resource"])
            output.append("\n".join(task_lines) + "\n")
        print ('='*75 + "\n").join(output)

        sys.exit(exit_codes.success)
    finally:
        svc.delete(job_uri)

if __name__ == '__main__':
    main()
