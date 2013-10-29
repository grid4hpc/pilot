# -*- encoding: utf-8 -*-

from zope.interface import implements
from pilot.api import *

from pilot.spooler.realm.local import map_user, run_stager, staging_info

import cPickle as pickle
import logging
import re
import time

import eventlet
from eventlet.green import os
from eventlet.green.subprocess import Popen, PIPE
tempfile = eventlet.import_patched("tempfile")

from pilot.lib import tools, json

config = {
    "requires_x509": "no",
    "map_user": "yes",
    "map_sources": "gridmap, voms",
    "gridmap_file": "/etc/grid-security/grid-mapfile",
    "vomsmap_file": "/etc/grid-security/groupmapfile",
    "ban_file": None,
    "status_update_path": None,
    "taskid_interface": "arg",
    # commands
    "cmd_pilot2batch": None,
    "cmd_submit": None,
    "cmd_status": None,
    "cmd_status_callback": None,
    "cmd_kill": None,
    "timeout_pilot2batch": "15",
    "timeout_submit": "15",
    "timeout_status": "15",
    "timeout_status_callback": "15",
    "timeout_kill": "15",
    "extra_args_pilot2batch": "",
    "extra_args_submit": "",
    "extra_args_status": "",
    "extra_args_status_callback": "",
    "extra_args_kill": "",
}

def load(config):
    return InfoProvider(config), Executor(config)

class InfoProvider(object):
    implements(IResourceEnumerator)

    def __init__(self, config):
        self.resources = [LocalResource()]

    def enumerate(self):
        return self.resources

class LocalResource(object):
    implements(IResource)

    def __init__(self):
        self.hostname = "localhost"
        self.port = None
        self.lrms = "genbatch"
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
        self.os_name = "Unknown"
        self.os_version = "0"
        self.os_release = "0"
        self.platform = "Unknown"
        self.smp_size = 44444
        self.cpu_hz = 44444
        self.cpu_instruction_set = "Unknown"
        self.cpu_model = "Unknown"
        self.ram_size = 44444
        self.virtual_size = 44444
        self.physical_slots = 44444
        self.physical_cpus = 44444
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

class SubmissionParameters(object):
    implements(ISubmissionParameters)

    def __init__(self, description, args=[]):
        self.description = description
        self.arguments = args

def fail_on_bad_code(cmdname, code, err):
    if code < 0:
        raise NonFatalTaskExecutorError("%s command timed out or aborted" % cmdname)
    if code == 1:
        raise NonFatalTaskExecutorError("%s temporary failed: %s" % (cmdname, err))
    if code > 1:
        raise FatalTaskExecutorError("%s failed: %s" % (cmdname, err))

class Executor(object):
    implements(ITaskExecutor)

    def __init__(self, config):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        self.config = config

        self.log.info("called with configuration: %s", config)

        for cmd in ("pilot2batch", "submit", "kill"):
            k = "cmd_" + cmd
            if self.config[k] is None:
                raise RuntimeError("configuration key %s is missing" % k)

        if (self.config["cmd_status"] is None) and \
           (self.config["cmd_status_callback"] is None):
            raise RuntimeError("configuration keys cmd_status and cmd_status_callback are missing at the same time")

        if self.config["taskid_interface"] not in ("arg", "stdin"):
            raise RuntimeError("Unknown taskid_interface: %s" % self.config["taskid_interface"])

    def popen(self, cmdname, args=[], proxy=None, scratch=None):
        """
        Return a Popen object for the given command with extra supplied args
        """
        cmdpath = self.config["cmd_" + cmdname]
        if self.config["extra_args_" + cmdname] != "":
            args = self.config["extra_args_" + cmdname].split() + args
            
        px = None
        if proxy is not None and self.config["requires_x509"].lower() == "yes":
            px = tempfile.NamedTemporaryFile()
            px.write(proxy)
            px.flush()
            env = os.environ.copy()
            env["X509_USER_PROXY"] = px.name

        if scratch is None:
            cmd = [cmdpath] + args
        else:
            cmdline = " ".join(re.escape(x) for x in [cmdpath]+args)
            cmd = ["sh", "-c", '"cd %s ; %s"' % (scratch, cmdline)]
        pid = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
        pid.px = px # otherwise can self-destruct before the process is finished
        return pid

    def speak(self, cmdname, args=[], proxy=None, stdin=None, scratch=None):
        """
        Return a tuple of (exit_code, stdout, stderr) for the given command.
        If exit_code == -1 then the program timed out.
        """
        pid = self.popen(cmdname, args, proxy, scratch)
        timeout = float(self.config["timeout_" + cmdname])
        (out, err) = tools.communicate_with_timeout(pid, stdin, timeout)

        if out is None:
            if pid.poll() is None:
                os.kill(pid.pid, signal.SIGKILL)
            return -1, out, err

        return pid.returncode, out, err

    def get_submission_parameters(self, t, r):
        code, out, err = self.speak("pilot2batch", stdin=json.dumps(t))
        if code < 0:
            raise ValueError("pilot2batch failed")

        fake_params = SubmissionParameters(out, err.split("\x00"))
        p = {"params": fake_params}
        p["in"], p["out"], p["streams"] = staging_info(t)
        
        return SubmissionParameters(pickle.dumps(p), [])

    def submit(self, params, proxy):
        p = pickle.loads(params.description)
        params = p["params"]
        user = map_user(proxy)
        staging = {"proxy": proxy,
                   "user": user,
                   "in": p["in"].items()}
        result = run_stager(staging)
        scratch = result["scratch"]
        
        code, out, err = self.speak("submit", params.arguments,
                                    proxy, params.description, scratch=scratch)

        if err is not None and len(err) > 0:
            self.log.info("submit returned: %s", err)

        fail_on_bad_code("submit", code, err)            

        stageout = {"user": user,
                    "scratch": scratch,
                    "out": p["out"].items()}
        return pickle.dumps((out.strip(), stageout))

    def kill(self, jobid, proxy):
        jobid, staging = pickle.loads(jobid)
        if self.config["taskid_interface"] == "arg":
            code, out, err = self.speak("kill", [jobid], proxy)
        else:
            code, out, err = self.speak("kill", [], proxy, jobid)

        if err is not None and len(err) > 0:
            self.log.info("kill returned: %s", err)

    def status(self, jobid, proxy):
        jobid, staging = pickle.loads(jobid)
        if self.config["taskid_interface"] == "arg":
            code, out, err = self.speak("status", [jobid], proxy)
        else:
            code, out, err = self.speak("status", [], proxy, jobid)

        fail_on_bad_code("status", code, err)

        status, reason = out.split("\n", 1)
        if status == "FINISHED":
            staging["proxy"] = proxy
            result = run_stager(staging)
            if len(result["errors"]) > 0:
                raise FatalTaskExecutorError("Stage out failed: %s" % repr(result["errors"]))
            return TaskState("finished",
                             exit_code=int(err.split("\n", 1)[0]),
                             reason=reason)
        elif status == "ABORTED":
            return TaskState("aborted", reason=reason)
        else:
            return TaskState("running", reason=reason)

class TaskState(object):
    implements(ITaskState)

    def __init__(self, state, reason=None, exit_code=None):
        self.state = state
        self.reason = reason
        self.exit_code = exit_code
