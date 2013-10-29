# -*- encoding: utf-8 -*-

from zope.interface import implements
from pilot.api import *

import logging
import time

from pilot.lib import etree
from pilot.spooler import globus
from pilot.spooler.gridnnn import GridnnnResource
from pilot.spooler.infosys2 import Infosys2InfoProvider, StaticInfosys2InfoProvider

from ngrid import pwc, infosys


config = {
    'reg_url': None,
    'mds_url': None,
    'infosys2_url': None,
    'infosys2_file': None,
    'mds_ttl': "600",
    'infosys2_ttl': "600",    
}

def load(config):
    if config['reg_url'] is not None:
        raise RuntimeError("RegSVC infoprovider is not supported yet")

    infoprovider = None

    if config['mds_url'] is not None:
        infoprovider = MDSInfoProvider(mds_url=config['mds_url'],
                                       ttl=int(config['mds_ttl']))
    elif config['infosys2_url'] is not None:
        infoprovider = Infosys2InfoProvider(infosys2_url=config['infosys2_url'],
                                            ttl=int(config['infosys2_ttl']))
    elif config['infosys2_file'] is not None:
        infoprovider = StaticInfosys2InfoProvider(filename=config['infosys2_file'])

    if infoprovider is None:
        raise RuntimeError("Missing configuration parameters for realm gws")

    return infoprovider, GT4TaskExecutor()
    

class MDSInfoProvider(object):
    implements(ICachingResourceEnumerator, IHTTPConsumer)

    def __init__(self,
                 mds_url="https://cis.ngrid.ru:8443/wsrf/services/DefaultIndexService",
                 ttl=600):
        u"""
        Параметры:

        mds_url: url WS-MDS Index
        ttl: время кеширования информации о ресурсах
        """
        self.fetch_url = None
        self.timeout = None
        self.last_update = 0
        
        self.ttl = ttl
        self.mds_url = mds_url

        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        self._resources = []

    # IResouceEnumerator

    def enumerate(self):
        return self._resources

    # ICachingResourceEnumerator

    def stale(self):
        if time.time() - self.last_update > self.ttl:
            return True
        return False

    def refresh(self):        
        try:
            self.log.debug("refresh started")
            qrp = pwc.ResourceProperties(self._https_send_request)
            now = time.time()
            self.log.debug("querying MDS Index service at %s", self.mds_url)
            mds_info = qrp.query(self.mds_url)

            resources, errors = infosys.chew_mds(etree.ElementTree(mds_info))
            for error in errors:
                self.log.warning("MDS Error: %s", error)

            self.last_update = now
            self._resources = [GridnnnResource(data) for data in resources.itervalues()]
        finally:
            self.log.debug("refresh finished")

    # other methods

    def _https_send_request(self, url, request):
        IHTTPConsumer.validateInvariants(self)
        return self.fetch_url(url, "POST", body=request, timeout=self.timeout)[:2]


class GT4SubmissionParameters(object):
    implements(ISubmissionParameters)

    def __init__(self, description, arguments, uuid):
        self.description = description
        self.arguments = arguments
        self.id = uuid

    def __str__(self):
        return "RSL: %s, submission_parameters: %s" % (self.description, " ".join(self.arguments))

class GT4TaskState(object):
    implements(ITaskState)

    def __init__(self, state, reason=None, exit_code=None):
        self.state = state
        self.reason = reason
        self.exit_code = exit_code

    @classmethod
    def from_gstate(klass, gstate):
        if gstate.state == u"done":
            return GT4TaskState("finished", exit_code=gstate.exit_code)
        elif gstate.state in (u"failed", u"userterminatedone",
                              u"userterminatefailed"):
            return GT4TaskState("aborted", reason=gstate.cause)
        else:
            return GT4TaskState("running")

class GT4TaskExecutor(object):
    implements(ITaskExecutor)

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        

    def get_submission_parameters(self, task_definition, resource):
        rsl = globus.RSL(task_definition, {},
                         {'hostname': resource.hostname,
                          'queue': resource.queue,
                          'lrms_type': resource.lrms,
                          })
        return GT4SubmissionParameters(str(rsl),
                                       rsl.globusrun_args, rsl.submission_uuid)

    def submit(self, params, proxy):
        try:
            epr = globus.job_submit(params.description, params.arguments, proxy)
            return str(epr)
        except globus.TimeoutError, exc:
            raise TimeoutTaskExecutorError(str(exc))
        except globus.GlobusError, exc:
            if "InvalidProxyException" in str(exc):
                raise FatalTaskExecutorError("Proxy error: %s" % str(exc))
            raise NonFatalTaskExecutorError("Globus error: %s" % str(exc))

    def kill(self, epr, proxy):
        try:
            globus.job_kill(epr, proxy)
        except globus.TimeoutError, exc:
            raise TimeoutTaskExecutorError(str(exc))
        except globus.GlobusError, exc:
            if "InvalidProxyException" in str(exc):
                raise FatalTaskExecutorError("Proxy error: %s" % str(exc))
            raise NonFatalTaskExecutorError("Globus error: %s" % str(exc))

    def status(self, epr, proxy):
        try:
            return GT4TaskState.from_gstate(globus.job_status(epr, proxy))
        except globus.TimeoutError, exc:
            raise TimeoutTaskExecutorError(str(exc))
        except globus.GlobusError, exc:
            raise FatalTaskExecutorError(str(exc))
