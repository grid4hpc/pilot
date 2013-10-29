# -*- encoding: utf-8 -*-

from zope.interface import implements
from pilot.api import *

import cPickle as pickle
import json
import logging
import re
import signal
import sys
import uuid
from urlparse import urlparse, urljoin
from eventlet.green import os, time
from eventlet.green.subprocess import Popen, PIPE

from pilot.spooler import gridmap
from pilot_cli import proxylib

config = { }

def load(config):
    return InfoProvider(), Executor()

class InfoProvider(object):
    implements(IResourceEnumerator)

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))

    def enumerate(self):
        return [LocalResource()]
        

class LocalResource(object):
    implements(IResource)

    def __init__(self):
        self.hostname = "localhost"
        self.port = None
        self.lrms = "localexec"
        self.queue = None
        self.version = "0.1"
        self.config = LocalResourceConfig()
        self.software = []
        self.state = LocalResourceState(self.config)

    def access_allowed(self, fqans):
        return True


class LocalResourceConfig(object):
    implements(IResourceConfiguration)

    def __init__(self):
        uname = os.uname()
        cpuinfo = [l.strip().split(':') for l in open("/proc/cpuinfo").readlines()]
        cpuinfo = [[v.strip() for v in l] for l in cpuinfo if len(l) > 1]
        meminfo = [l.strip().split() for l in open("/proc/meminfo")]
        meminfo = dict([(m[0].strip(':'), m[1:]) for m in meminfo])
        self.os_name = uname[0]
        self.os_version = uname[2].split('-')[0]
        self.os_release = uname[2].split('-')[1]
        self.platform = uname[4]
        self.smp_size = len([attr for attr in cpuinfo if attr[0]=='processor'])
        self.cpu_hz = int(float([attr for attr in cpuinfo \
                                 if attr[0] == 'cpu MHz'][0][1]))
        self.cpu_instruction_set = self.platform
        self.cpu_model = ' '.join(
            [attr for attr in cpuinfo if attr[0] == 'model name'][0][1].split())
        self.ram_size = int(meminfo['MemTotal'][0])/1024
        self.virtual_size = (int(meminfo['MemTotal'][0]) + \
                             int(meminfo['SwapTotal'][0])) / 1024
        self.physical_slots = 1
        self.physical_cpus = len(
            set([attr[1] for attr in cpuinfo if attr[0] == 'physical id']))
        self.logical_cpus = self.smp_size

class LocalResourceState(object):
    implements(IResourceState)

    def __init__(self, config):
        self.total_cpus = config.logical_cpus
        self.free_cpus = self.total_cpus
        self.running_jobs = 0
        self.total_jobs = 0
        self.waiting_jobs = 0
        self.enabled = True

def _init_urlparse():
    from urlparse import uses_relative, uses_netloc, uses_params, uses_fragment
    for scheme in ('gsiftp', ):
        for prop in uses_relative, uses_netloc, uses_params, uses_fragment:
            if scheme not in prop:
                prop.insert(0, scheme)
                
_init_urlparse()

def expand_path(task, path):
    netloc = urlparse(path)[1]
    if netloc != '':
        return path
    elif 'default_storage_base' in task:
        return urljoin(task['default_storage_base'], path)
    else:
        raise FatalTaskExecutorError("cannot expand %s to url without default_storage_base" % path)

def staging_info(task):
    stage_in = {}
    stage_out = {}
    streams = {}
    if 'stdin' in task:
        streams['stdin'] = uuid.uuid4().hex
        stage_in[streams['stdin']] = expand_path(task, task['stdin'])
    for stream in ('stdout', 'stderr'):
        if stream in task:
            streams[stream] = uuid.uuid4().hex
            stage_out[streams[stream]] = expand_path(task, task[stream])

    for local, remote in task.get('input_files', {}).iteritems():
        stage_in[local.lstrip('/')] = expand_path(task, remote)
        
    for local, remote in task.get('output_files', {}).iteritems():
        stage_out[local.lstrip('/')] = expand_path(task, remote)

    return stage_in, stage_out, streams

class LocalSubmissionParameters(object):
    implements(ISubmissionParameters)

    def __init__(self, task, resource):
        p = {
            'env': task.get('environment', {}),
            'executable': task['executable'],
            'args': [task['executable']] + task.get('arguments', []),
            }

        p["in"], p["out"], p["streams"] = staging_info(task)
        self.description = pickle.dumps(p)
        self.arguments = []

def map_user(proxy):
    key, proxy = proxylib.load_proxy(proxy)
    mapping = gridmap.get_mapping(proxy)
    if gridmap.is_pool(mapping):
        account = gridmap.allocate_pool_account(mapping, proxy)
        if account is None:
            raise FatalTaskExecutorError("Could not allocate from pool %s" % mapping)
        return account
    else:
        return mapping

class TaskState(object):
    implements(ITaskState)

    def __init__(self, state, reason=None, exit_code=None):
        self.state = state
        self.reason = reason
        self.exit_code = exit_code    

PILOT_STAGER = os.path.join(os.path.split(os.path.abspath(sys.argv[0]))[0], "pilot-stager")

def run_stager(params):
    params["puid"] = os.geteuid()
    pid = Popen(["sudo", "-n", "-u", params["user"], PILOT_STAGER],
                stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    stdout, stderr = pid.communicate(json.dumps(params))
    result = json.loads(stdout)
    return result

class Executor(object):
    implements(ITaskExecutor)

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
    
    def get_submission_parameters(self, task_definition, resource):
        return LocalSubmissionParameters(task_definition, resource)

    def submit(self, params, proxy):
        p = pickle.loads(params.description)
        user = map_user(proxy)
        staging = {"proxy": proxy,
                   "user": user,
                   "in": p["in"].items()}
        result = run_stager(staging)
        scratch = result["scratch"]
        if len(result["errors"]) > 0:
            raise FatalTaskExecutorError("Stage in failed: %s" % repr(result["errors"]))

        stdin = p["streams"].get("stdin", "/dev/null")
        stdout = p["streams"].get("stdout", "/dev/null")
        stderr = p["streams"].get("stderr", "/dev/null")
        cmd = " ".join(re.escape(x) for x in p["args"])
        parg = ["sudo", "-n", "-u", user, "--",
                "sh", "-c", "cd %s ; umask 0077 ; %s < %s > %s 2>%s" % (scratch, cmd, stdin, stdout, stderr)]
        self.log.debug("popen: %s", parg)
        pid = Popen(parg,
                    stdin=open("/dev/null", "rb"),
                    stdout=open("/dev/null", "wb"),
                    stderr=open("/dev/null", "wb"),
                    close_fds=True)
        stageout = {"user": user,
                    "scratch": scratch,
                    "out": p["out"].items()}
        return pickle.dumps((pid.pid, stageout))

    def status(self, taskid, proxy):
        pid, staging = pickle.loads(taskid)
        try:
            pid, status = os.waitpid(pid, os.WNOHANG)
            if pid != 0:
                if os.WIFEXITED(status):
                    staging["proxy"] = proxy
                    result = run_stager(staging)
                    if len(result["errors"]) > 0:
                        raise FatalTaskExecutorError("Stage out failed: %s" % repr(result["errors"]))
                    
                    return TaskState("finished",
                                     exit_code=os.WEXITSTATUS(status),
                                     reason="status=%d" % status)
                else:
                    return TaskState("aborted",
                                     exit_code=os.WEXITSTATUS(status),
                                     reason="waitpid returned %d" % status)
            else:
                return TaskState("running")
        except OSError, exc:
            if exc.errno == 10:
                return TaskState("aborted",
                                 exit_code=255,
                                 reason="Child process not found")
            else:
                return TaskState("aborted",
                                 exit_code=255,
                                 reason=str(exc))

    def kill(self, taskid, proxy):
        pid, staging = pickle.loads(taskid)
        pid = Popen(["sudo", "-n", "-u", staging["user"],
                     "kill", "-9", "-%d" % pid],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
        pid.communicate(None)
