# -*- encoding: utf-8 -*-

import re
import sys

__all__ = ['proc_stat', 'proc_status']

_pstat_parts = [
    ('pid', int),
    ('comm', str),
    ('state', str),
    ('ppid', int),
    ('pgrp', int),
    ('session', int),
    ('tty_nr', int),
    ('tpgid', int),
    ('flags', int),
    ('minflt', int),
    ('cminflt', int),
    ('majflt', int),
    ('cmajflt', int),
    ('utime', int),
    ('stime', int),
    ('cutime', int),
    ('cstime', int),
    ('priority', int),
    ('nice', int),
    ('num_threads', int),
    ('itrealvalue', int),
    ('starttime', int),
    ('vsize', int),
    ('rss', int),
    ('rsslim', int),
    ('startcode', int),
    ('endcode', int),
    ('startstack', int),
    ('kstkesp', int),
    ('kstkeip', int),
    ('signal', int),
    ('blocked', int),
    ('sigignore', int),
    ('sigcatch', int),
    ('wchan', int),
    ('nswap', int),
    ('cnswap', int),
    ('exit_signal', int),
    ('processor', int),
    ('rt_priority', int),
    ('policy', int),
    ('delayacct_blkio_ticks', int),
    ('guest_time', int),
    ('cguest_time', int),
]

number = re.compile(r'^\d+$')
many_numbers = re.compile(r'^((\d+)(\s*))+$')
whitespace = re.compile(r'\s+')

if sys.platform == 'linux2':
    def proc_stat(pid=None):
        if pid is not None:
            path='/proc/%d/stat' % pid
        else:
            path='/proc/self/stat'
        line = open(path, 'r').read()
        line.strip()

        res = {}
        for i, elt in enumerate(line.split()):
            part = _pstat_parts[i]
            res[part[0]] = part[1](elt)

        return res

    def proc_status(pid=None):
        if pid is not None:
            path='/proc/%d/status' % pid
        else:
            path='/proc/self/status'

        result = {}        
        for line in open(path, 'rt'):
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            field = parts[0].strip()
            value = parts[1].strip()
            if field.startswith('Vm'):
                result[field] = int(value[:-3]) * 1024
            else:
                if field[:3] in ('Sig', 'Cap') or \
                   field[:5] in ('Cpus_', 'Mems_'):
                    result[field] = value
                elif number.match(value):
                    result[field] = int(value)
                elif many_numbers.match(value):
                    result[field] = [int(n) for n in whitespace.split(value)]
                else:
                    result[field] = value
        return result
else:
    def proc_stat(pid=None):
        raise NotImplementedError("No implementation for this platform.")

    def proc_status(pid=None):
        raise NotImplementedError("No implementation for this platform.")

