# -*- encoding: utf-8 -*-

import sys

from pilot_cli.common import exit_codes
from pilot_cli.api import setup_app, isoformat, json_loads

def main():
    options, args, log, svc = setup_app(
        usage = "%prog [options] URI ...",
        description = """
        Get a status information for the job
        """,
        argstest = lambda args: len(args) == 1,
        logname = "pilot-job-status")

    job_uri = args[0]
    _, content = svc.get(job_uri)
    info = json_loads(content)
    log.debug("job status (raw):\n%s", info)

    states = info['state']
    states.sort(lambda a, b: -cmp(a['ts'], b['ts']))
    state = states[0]

    if options.json:
        print content
        sys.exit(exit_codes.success)

    if options.quiet:
        print '%s %s' % (state['s'], isoformat(state['ts']))
        sys.exit(exit_codes.success)

    if options.verbose:
        print "Job state information for %s:" % job_uri
        for s in states:
            print " * %-15s (%s)" % (s['s'], s['ts'].strftime('%c %Z'))
            if 'info' in s:
                print "   %s" % s['info']
    else:
        result = 'Job %s is %s since %s' % (job_uri, state['s'],
                                            state['ts'].strftime('%c %Z'))
        if 'info' in state:
            result += ' (%s)' % state['info']
        result += '.'
        print result

    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
