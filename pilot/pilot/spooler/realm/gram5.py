# -*- encoding: utf-8 -*-

from zope.interface import implements
from pilot.api import *

import logging
import time

from pilot.spooler import gram5
from pilot.spooler.gridnnn import GridnnnResource
from pilot.spooler.infosys2 import Infosys2InfoProvider, StaticInfosys2InfoProvider


config = {
    'infosys2_url': None,
    'infosys2_file': None,
    'infosys2_ttl': "600",    
}

def load(config):
    infoprovider = None

    if config['infosys2_url'] is not None:
        infoprovider = Infosys2InfoProvider(infosys2_url=config['infosys2_url'],
                                            ttl=int(config['infosys2_ttl']))
    if config['infosys2_file'] is not None:
        infoprovider = StaticInfosys2InfoProvider(filename=config['infosys2_file'])

    if infoprovider is None:
        raise RuntimeError("Missing configuration parameters for realm gram5")

    return InfosysWrapper(infoprovider), Gram5TaskExecutor()
    

class InfosysWrapper:
    def __init__(self, infosys):
        self.infosys = infosys

    def __getattr__(self, attr):
        return getattr(self.infosys, attr)

    def refresh(self):
        self.infosys.refresh()
        for r in self._resources:
            r.port = 2119

class Gram5SubmissionParameters(object):
    implements(ISubmissionParameters)

    def __init__(self, rsl, resource):
        self.rsl = rsl
        self.resource = resource

    def as_dict(self):
        return {'RSL': self.rsl, 'Resource': self.resource}

    def __str__(self):
        return "Resource: %s, RSL: %s" % (self.resource, self.rsl)

class Gram5TaskState(object):
    implements(ITaskState)

    def __init__(self, state, reason=None, exit_code=None):
        self.state = state
        self.reason = reason
        self.exit_code = exit_code

    @classmethod
    def from_string(klass, state):
        if state == "DONE":
            return Gram5TaskState("finished", exit_code=0)
        elif state == "FAILED":
            return Gram5TaskState("aborted", reason="Unknown")
        else:
            return Gram5TaskState("running")

class Gram5TaskExecutor(object):
    implements(ITaskExecutor)

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        

    def get_submission_parameters(self, t, r):
        rsl = gram5.rsl(t, {'hostname': r.hostname,
                            'queue': r.queue,
                            'lrms_type': r.lrms,
                            })
        resource = "%s:%s/jobmanager-%s" % (r.hostname, r.port, r.lrms)
        return Gram5SubmissionParameters(rsl, resource)

    def submit(self, params, proxy):
        try:
            joburl = gram5.submit2(params.rsl, params.resource, proxy)
            return joburl
        except RuntimeError, exc:
            if "Error with GSI credential" in exc:
                raise FatalTaskExecutorError("Credentials error: %s" % str(exc))
            raise NonFatalTaskExecutorError("Globus error: %s" % str(exc))

    def kill(self, epr, proxy):
        raise NotImplementedError

    def status(self, url, proxy):        
        try:
            return Gram5TaskState.from_string(gram5.status2(url, proxy))
        except RuntimeError, exc:
            if str(exc) == "globusrun timed out":
                raise TimeoutTaskExecutorError(str(exc))
            else:
                raise FatalTaskExecutorError(str(exc))
