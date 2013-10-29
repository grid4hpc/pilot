# -*- encoding: utf-8 -*-

import signal
import tempfile
import types
from eventlet.green import os
from eventlet.green.subprocess import Popen, PIPE
from tempfile import mktemp
import uuid, random
from cStringIO import StringIO

from pilot.lib import etree, tools, urlparse
import pilot.spooler


GLOBUSRUN_WS = "/usr/bin/pyglobusrun-ws"
WSRF_QUERY = "/usr/bin/pywsrf-query"
GLOBUS_CREDENTIAL_REFRESH = "/usr/bin/pyglobus-credential-refresh"

JOB_STATE_NS = "http://www.globus.org/namespaces/2008/03/gram/job/types"
BF2_NS = "http://docs.oasis-open.org/wsrf/bf-2"


class GlobusError(ValueError):
    pass

class ProxyExpiredError(GlobusError):
    pass

class TimeoutError(GlobusError):
    pass

class State(object):
    """Represent state of Globus' job."""

    pilot_task_state = dict(
        # globus state -> pilot state
        unsubmitted=u"pending",
        stagein=u"running",
        pending=u"running",
        active=u"running",
        suspended=u"running",
        stageout=u"running",
        cleanup=u"running",
        done=u"finished",
        userterminatedone=u"aborted", # same as jobrunner
        failed=u"aborted",
        userterminatefailed=u"aborted"
        )

    def __init__(self, et):
        """
        @param et: etree.ElementTree
        """
        self.et = et
        self.state = None
        self.cause = None
        self.exit_code = None
        self.parse()

    @classmethod
    def from_string(cls, xml_string):
        return cls(etree.fromstring(xml_string))

    def parse(self):
        state = self.et.find('.//{%s}state' % JOB_STATE_NS)
        if state is not None:
            self.state = state.text.lower()
            
        if self.state in [u'failed', u'userterminatedone']:
            self.cause = [e.text for e in self.et.findall('.//{%s}Description' % BF2_NS)]

        if self.state == u'done':
            self.exit_code = int(self.et.findall('.//{%s}exitCode' % JOB_STATE_NS)[0].text)      

    @property
    def pilot_state(self):
        return self.pilot_task_state[self.state]

    def __repr__(self):
        return "<globus.State(%s, %s)>" % (repr(self.state), repr(self.exit_code))
        

def prepare_proxy(proxy):
    filename = mktemp()
    fd = open(filename, 'w')
    fd.write(proxy)
    fd.close()
    os.chmod(filename, 0600)
    return filename

def job_submit(rsl, args, proxy=None):
    cmd = [GLOBUSRUN_WS, ]
    cmd.extend(args)
    rslfile = mktemp()
    fd = open(rslfile, "w")
    fd.write(rsl)
    fd.close()
    cmd.extend(['-f', rslfile])

    proxy_filename = None
    env = dict(os.environ)
    if proxy:
        proxy_filename = prepare_proxy(proxy)
        env['X509_USER_PROXY'] = proxy_filename

    pid = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, close_fds=True)
    (epr, err) = tools.communicate_with_timeout(pid, timeout=pilot.spooler.config['job_submit_timeout'])

    if proxy_filename:
        os.unlink(proxy_filename)

    os.unlink(rslfile)

    if epr is None:
        if pid.poll() is None:
            os.kill(pid.pid, signal.SIGKILL)
        raise TimeoutError('globusrun-ws timed out after %s seconds' % pilot.spooler.config['job_submit_timeout'])

    if pid.returncode != 0:
        raise GlobusError(err)

    return epr

def job_kill(epr, proxy=None):
    cmd = [GLOBUSRUN_WS, '-kill', '-host-authz', '-quiet', '-job-epr-file']
    eprfile = mktemp()
    fd = open(eprfile, "w")
    fd.write(epr)
    fd.close()
    cmd.append(eprfile)

    proxy_filename = None
    env = dict(os.environ)
    if proxy:
        proxy_filename = prepare_proxy(proxy)
        env['X509_USER_PROXY'] = proxy_filename

    pid = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, close_fds=True)
    (_, err) = tools.communicate_with_timeout(pid, timeout=pilot.spooler.config['job_kill_timeout'])

    if proxy_filename:
        os.unlink(proxy_filename)

    os.unlink(eprfile)

    if pid.poll() is None:
        os.kill(pid.pid, signal.SIGKILL)
        raise TimeoutError('globusrun-ws timed out after %s seconds' % pilot.spooler.config['job_kill_timeout'])

    if pid.returncode != 0:
        raise GlobusError("RC: %d, %s" % (pid.returncode, err))

def job_status(epr, proxy=None):
    cmd = [WSRF_QUERY, ]
    eprfile = mktemp()
    cmd.extend(['-e', eprfile])
    fd = open(eprfile, "w")
    fd.write(epr)
    fd.close()

    proxy_filename = None
    env = dict(os.environ)
    if proxy:
        proxy_filename = prepare_proxy(proxy)
        env['X509_USER_PROXY'] = proxy_filename

    pid = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, close_fds=True)
    (xml, err) = tools.communicate_with_timeout(pid, timeout=pilot.spooler.config['job_query_timeout'])

    if proxy_filename:
        os.unlink(proxy_filename)

    os.unlink(eprfile)

    if xml is None:
        if pid.poll() is None:
            os.kill(pid.pid, signal.SIGKILL)
        raise TimeoutError('wsrf-query timed out after %s seconds' % pilot.spooler.config['job_query_timeout'])

    if pid.returncode == 2:
        raise ProxyExpiredError(err)
    elif pid.returncode != 0:
        raise GlobusError("Exit Code %d, %s" % (pid.returncode, err))

    gstate = State(etree.fromstring(xml))
    if gstate.state is None:
        raise GlobusError("state element not present in wsrf-query response")
    return gstate


def wsrf_query_epr(epr, proxy=None):
    epr_file = tempfile.NamedTemporaryFile()
    epr_file.write(epr)
    epr_file.flush()

    env = os.environ.copy()
    if proxy is not None:
        proxy_file = tempfile.NamedTemporaryFile()
        proxy_file.write(proxy)
        proxy_file.flush()
        env["X509_USER_PROXY"] = proxy_file.name

    proc = Popen([WSRF_QUERY, "-e", epr_file.name], env=env,
                stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    (out, err) = tools.communicate_with_timeout(proc, timeout=pilot.spooler.config['job_query_timeout'])

    if out is None:
        if proc.poll() is None:
            os.kill(proc.pid, signal.SIGKILL)
        raise TimeoutError("wsrf-query timed out after %s seconds" % pilot.spooler.config['job_query_timeout'])

    if proc.returncode == 2:
        raise ProxyExpiredError(err)
    elif proc.returncode != 0:
        raise GlobusError("Exit Code %d, %s" % (proc.returncode, err))

    return etree.parse(StringIO(out))

def credential_refresh(epr, proxy):
    epr_file = tempfile.NamedTemporaryFile()
    epr_file.write(epr)
    epr_file.flush()

    proxy_file = tempfile.NamedTemporaryFile()
    proxy_file.write(proxy)
    proxy_file.flush()

    env = os.environ.copy()
    env["X509_USER_PROXY"] = proxy_file.name
    proc = Popen([GLOBUS_CREDENTIAL_REFRESH, "-e", epr_file.name,
                  "-x", proxy_file.name], env=env,
                 stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    (out, err) = tools.communicate_with_timeout(proc, timeout=pilot.spooler.config['job_submit_timeout'])

    if out is None:
        if proc.poll() is None:
            os.kill(proc.pid, signal.SIGKILL)
        raise TimeoutError("globus-credential-refresh timed out after %s seconds" % pilot.spooler.config['job_submit_timeout'])

    if proc.returncode == 2:
        raise ProxyExpiredError(err)
    elif proc.returncode != 0:
        raise GlobusError("Exit Code %d, %s" % (proc.returncode, err))

    return True

def _build_transfer(src, dst, attempts=None):
    elt = etree.Element('transfer')
    etree.SubElement(elt, 'sourceUrl').text = src
    etree.SubElement(elt, 'destinationUrl').text = dst
    if attempts:
        etree.SubElement(elt, 'maxAttempts').text = unicode(attempts)
    return elt


def make_extensions(ext, root):
    for attr in ext:
        val = ext[attr]
        if type(val) in types.StringTypes:
            etree.SubElement(root, attr).text = val
        elif type(val) is list:
            for elt in val:
                if type(elt) in types.StringTypes:
                    etree.SubElement(root, attr).text = elt
                elif type(elt) is dict:
                    make_extensions(elt, etree.SubElement(root, attr))
                else:
                    print type(val)
        elif type(val) is dict:
            make_extensions(val, etree.SubElement(root, attr))
    return root

# pylint: disable-msg=R0902
class RSL(object):
    _notification_consumer_url = None
    def __init__(self, task, job, target):
        u"""Построить rsl и т.п. для задачи task для запуска ее на ws-gram GRAM.

        @param task: задача (в виде JSONTask)
        @param job: задание (в виде JSONJob)
        @param gram: resources.GRAM"""
        self.task = task
        self.job = job
        self.target = target
        self.et = None
        self.storage_base = None
        self.jobid = unicode(uuid.uuid4())
        self.pid = random.randint(1, 32767)
        self.globusrun_args = []

        self.build_rsl()
        self.build_globusrun_args()

    @property
    def submission_id(self):
        return unicode(u'uuid:%s' % (self.jobid,))

    @property
    def submission_uuid(self):
        return self.jobid

    @classmethod
    def set_notification_consumer_url(cls, url):
        cls._notification_consumer_url = url

    # pylint: disable-msg=R0912
    def build_rsl(self):
        self.storage_base = self.task.get('default_storage_base',
                                          self.job.get('default_storage_base', None))

        stdin_local_filename = "${GLOBUS_SCRATCH_DIR}/%s/in.%d" % (self.jobid, self.pid)
        stdout_local_filename = "${GLOBUS_SCRATCH_DIR}/%s/out.%d" % (self.jobid, self.pid)
        stderr_local_filename = "${GLOBUS_SCRATCH_DIR}/%s/err.%d" % (self.jobid, self.pid)
        transfer_attempts = int(self.task.get('max_transfer_attempts',
                                              self.job.get('max_transfer_attempts', '5')))

        job = etree.Element('job')
        self.et = etree.ElementTree(job)

        etree.SubElement(job, 'executable').text = self.task['executable']
        etree.SubElement(job, 'directory').text = "${GLOBUS_SCRATCH_DIR}/%s/" % self.jobid

        for argument in self.task.get('arguments', []):
            etree.SubElement(job, 'argument').text = argument

        for k in self.task.get('environment', {}):
            elt = etree.SubElement(job, 'environment')
            etree.SubElement(elt, 'name').text = unicode(k)
            etree.SubElement(elt, 'value').text = unicode(self.task['environment'][k])

        stagein = etree.Element('fileStageIn')
        if 'stdout' in self.task or \
               'stderr' in self.task or \
               'output_files' in self.task:
            stageout = etree.Element('fileStageOut')
        else:
            stageout = None
        cleanup = etree.Element('fileCleanUp')

        stagein.append(_build_transfer(
            "gsiftp://%s/etc/profile.d/" % self.target['hostname'],
            "file:///${GLOBUS_SCRATCH_DIR}/%s/" % self.jobid,
            transfer_attempts))
        etree.SubElement(etree.SubElement(cleanup, 'deletion'), 'file').text = \
            "file:///${GLOBUS_SCRATCH_DIR}/%s/" % self.jobid
        if 'stdin' in self.task:
            etree.SubElement(job, 'stdin').text = stdin_local_filename
            remote_url = self._build_url(self.task['stdin'])
            stagein.append(_build_transfer(
                remote_url,
                "file:///%s" % stdin_local_filename, transfer_attempts))

        if 'stdout' in self.task:
            etree.SubElement(job, 'stdout').text = stdout_local_filename
            remote_url = self._build_url(self.task['stdout'])
            stageout.append(_build_transfer(
                "file:///%s" % stdout_local_filename,
                remote_url, transfer_attempts))

        if 'stderr' in self.task:
            etree.SubElement(job, 'stderr').text = stderr_local_filename
            remote_url = self._build_url(self.task['stderr'])
            stageout.append(_build_transfer(
                "file:///%s" % stderr_local_filename,
                remote_url, transfer_attempts))

        if 'count' in self.task:
            etree.SubElement(job, 'count').text = unicode(self.task['count'])

        if int(self.task.get('count', '1')) > 1:
            etree.SubElement(job, 'jobType').text = u'mpi'
        else:
            etree.SubElement(job, 'jobType').text = u'single'

        if 'extensions' in self.task and len(self.task['extensions']) > 0:
            extensions = etree.SubElement(job, 'extensions')
            make_extensions(self.task['extensions'], extensions)

        if self.target['queue'] is not None:
            etree.SubElement(job, 'queue').text = self.target['queue']

        for filename in self.task.get('input_files', {}):
            remote_url = self._build_url(self.task['input_files'][filename])
            local_path = os.path.normpath(
                "${GLOBUS_SCRATCH_DIR}/%s/%s" % (self.jobid, filename))
            if filename.endswith(os.path.sep):
                local_path += os.path.sep
            stagein.append(_build_transfer(
                remote_url, "file:///%s" % local_path, transfer_attempts))

        for filename in self.task.get('output_files', {}):
            remote_url = self._build_url(self.task['output_files'][filename])
            local_path = os.path.normpath(
                "${GLOBUS_SCRATCH_DIR}/%s/%s" % (self.jobid, filename))
            if filename.endswith(os.path.sep):
                local_path += os.path.sep
            stageout.append(_build_transfer(
                "file:///%s" % local_path, remote_url, transfer_attempts))

        for elt in [stagein, stageout, cleanup]:
            if elt:
                job.append(elt)

    def _build_url(self, path_or_url):
        storage_base = self.storage_base
        netloc = urlparse.urlparse(path_or_url)[1]
        if netloc != '':
            return path_or_url
        elif storage_base is None:
            raise ValueError("cannot convert %s to url without storage base" % path_or_url)
        else:
            return urlparse.urljoin(storage_base, path_or_url)

    def __str__(self):
        if self.et:
            buf = StringIO()
            buf.write('<?xml version="1.0" encoding="UTF-8"?>')
            self.et.write(buf, encoding='utf-8')
            return buf.getvalue()
        else:
            return "<job />"

    def __repr__(self):
        return "<RSL>"

    def build_globusrun_args(self):
        # FIXME: termination time should be set to
        # proxy cert lifetime + 24 hours and updated after each
        # myproxy cert renewal
        self.globusrun_args = [
            '-submit', '-batch', '-factory', self.target['hostname'],
            '-factory-type', self.target['lrms_type'],
            '-submission-id', str(self.submission_id),
            '-staging-delegate', '-termination', '+720:00',
            ]
        # NOTE: non-standard command-line argument for globusrun-ws
        if self._notification_consumer_url is not None:
            self.globusrun_args += [
                '--meta-pilot-notification-consumer-url', self._notification_consumer_url]
