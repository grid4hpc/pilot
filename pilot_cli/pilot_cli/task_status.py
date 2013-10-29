# -*- encoding: utf-8 -*-

import sys

from pilot_cli.api import setup_app, isoformat, json_loads
from pilot_cli.common import exit_codes

def main():
    options, args, log, svc = setup_app(
        usage = "%prog [options] URI ...",
        description = """
        Get a status information for the task of the job.
        """,
        argstest = lambda args: len(args) == 1,
        logname = "pilot-task-status")

    task_uri = args[0]
    _, content = svc.get(task_uri)
    info = json_loads(content)
    log.debug("task status (raw):\n%s", info)

    states = info['state']
    states.sort(lambda a, b: -cmp(a['ts'], b['ts']))
    state = states[0]

    if options.json:
        print content
        sys.exit(exit_codes.success)

    exit_code = info.get('exit_code', None)
    if options.quiet:
        msg = state['s']
        if exit_code is not None:
            msg += '(%s)' % exit_code
        print '%s %s' % (msg, isoformat(state['ts']))
        sys.exit(exit_codes.success)
        
    if options.verbose:
        print "Task state information for %s:" % task_uri
        for s in states:
            print " * %-15s (%s)" % (s['s'], s['ts'].strftime('%c %Z'))
            if 'info' in s:
                print "   %s" % s['info']
            if s['s'] == 'finished' and exit_code is not None:
                print "   exit code: %s" % exit_code
    else:
        msg = state['s']
        if exit_code is not None:
            msg += ' (exit code %s)' % exit_code
        result = 'Task %s is %s since %s' % (task_uri, msg,
                                             state['ts'].strftime('%c %Z'))
        if 'info' in state:
            result += ' (%s)' % state['info']
        result += '.'
        print result
    
    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
