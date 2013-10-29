# -*- encoding: utf-8 -*-

import sys
import datetime

from pilot_cli.api import setup_app, json_loads
from pilot_cli.common import exit_codes

def format_dates(o, seen=None):
    if seen is None:
        seen = set()
    if id(o) in seen:
        return
    seen.add(id(o))

    if isinstance(o, list):
        return [format_dates(element, seen) for element in o]
    elif isinstance(o, dict):
        return dict((k, format_dates(v, seen)) for k, v in o.iteritems())
    elif isinstance(o, datetime.datetime):
        return o.strftime("%c %Z")
    else:
        return o

def main():
    options, args, log, svc = setup_app(
        usage = "%prog [options] URI ...",
        description = """
        Get detailed information about the job, including all its status
        changes, pending operations, etc.
        """,
        argstest = lambda args: len(args) == 1,
        logname = "pilot-job-info")

    job_uri = args[0]
    _, content = svc.get(job_uri)
    info = json_loads(content)
    log.debug("job status (raw):\n%s", info)

    if options.json or options.quiet:
        sys.exit(exit_codes.success)

    info['state'].sort(lambda a, b: -cmp(a['ts'], b['ts']))
    info['operation'].sort(lambda a, b: -cmp(a['created'], b['created']))
    format_dates(info)

    tasks = {}
    if options.verbose:
        for task, task_uri in info['tasks'].iteritems():
            _, content = svc.get(task_uri)
            task_info = json_loads(content)
            task_info['state'].sort(lambda a, b: -cmp(a['ts'], b['ts']))
            format_dates(task_info)
            log.debug("task status (raw):\n%s", task_info)
            tasks[task] = task_info

    for key in ['server_time', 'created', 'modified', 'expires',
                'owner', 'vo', 'deleted']:
        print " * %s: %s" % (key, info.pop(key))
    for key in ['operation', 'state', 'tasks']:
        if key in info and len(info[key]) == 0:
            info.pop(key)
    if 'operation' in info:
        print " * operations:"
        for op in info['operation']:
            if 'completed' not in op:
                state = "pending since %s" % op['created']
            else:
                if op['success']:
                    state = 'done %s' % op['completed']
                else:
                    state = 'failed %s' % op['completed']
            print "   - %s (%s)" % (op['op'], state)
        info.pop('operation')
    if 'state' in info:
        print " * state history (newest first):"
        for st in info['state']:
            print '   - %s (%s)' % (st.pop('s'), st.pop('ts'))
            if len(st) > 0:
                for key in sorted(st.keys()):
                    print '     + %s: %s' % (key, st[key])
        info.pop('state')

    if 'tasks' in info:
        print " * tasks:"
        for task in sorted(info['tasks'].keys()):
            print '   - %s: %s' % (task, info['tasks'][task])
            if options.verbose:
                t = tasks[task]
                state = t['state'][0]
                s = state['s']
                if s == 'finished':
                    print '        %s (exit code %s) since %s' % (
                        s, t.get('exit_code', 'unknown'), state['ts'])
                elif s == 'running':
                    print '        %s (at %s) since %s' % (
                        s, state.get('info', 'unknown'), state['ts'])
                    if 'info' in state:
                        state.pop('info')
                else:
                    print '        %s since %s' % (s, state['ts'])
                state.pop('s')
                state.pop('ts')
                for key in sorted(state.keys()):
                    print '        + %s: %s' % (key, state[key])
        info.pop('tasks')


    for key in ['definition', 'server_policy_uri']:
        info.pop(key)
    if len(info.keys()) > 0:
        log.error("unused keys in response: %s", ', '.join(info.keys()))

    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
