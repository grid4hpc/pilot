# -*- encoding: utf-8 -*-

import random
import types
from cStringIO import StringIO

from M2Crypto import RSA, SSL, X509

import eventlet
from eventlet.green import os, httplib, socket
from eventlet.green.subprocess import Popen, PIPE
tempfile = eventlet.import_patched("tempfile")

from pilot.lib import tools, urlparse
import pilot.spooler

from pilot_cli import proxylib

def quote(s):
    """return a GRAM5 string, quoted and escaped if needed"""
    forbidden_chars = "+&|()=<>!\"'^#$"
    should_quote = False
    for c in forbidden_chars:
        if c in s:
            should_quote = True
            break

    if should_quote:
        return '"' + s.replace('"', '""') + '"'
    else:
        return s


def from_dict(rsl, trusted_attrs=[]):
    """Convert a dictionary-like structure into GRAM5 RSL.

    @param rsl: a dictionary to be converted to RSL. Key values may be
    either strings, dictionaries mapping strings to strings, or lists
    of strings.

    @param trusted_attrs: a list of attributes which values will not
    be quoted.
    """
    elements = []
    for k, v in rsl.iteritems():
        if k in trusted_attrs:
            q = lambda x: x
        else:
            q = quote
        if isinstance(v, types.StringTypes):
            elements.append("(%s=%s)" % (q(k), q(v)))
        elif isinstance(v, types.ListType):
            parts = ["%s" % q(e) for e in v]
            elements.append("(%s=%s)" % (q(k), " ".join(parts)))
        elif isinstance(v, types.DictType):
            parts = ["(%s %s)" % (q(k2), q(v2)) \
                     for k2, v2 in v.iteritems()]
            elements.append("(%s=%s)" % (k, " ".join(parts)))
    return "&" + "".join(elements)


def transfer_url(x, base):
    netloc = urlparse.urlparse(x)[1]
    if netloc != "":
        return x
    elif base is None:
        raise ValueError("cannot convert %s to url without storage base" % x)
    else:
        return urlparse.urljoin(base, x)


def rsl(task, target):
    u"""Построить GRAM5 RSL для задачи task задания job для запуска ее на GRAM5 target

    @param task: задача (в виде JSONTask)
    @param job: задание (в виде JSONJob)
    @param gram: resources.GRAM
    """

    pid = random.randint(1, 1000000000)
    base = task.get("default_storage_base", None)

    rsl = {"scratch_dir": "$(HOME)",
           "directory": "$(SCRATCH_DIRECTORY)",
           "executable": task["executable"],
           "file_stage_in": {},
           "file_stage_out": {},
           }
    if "arguments" in task:
        rsl["arguments"] = task["arguments"]
    if "environment" in task:
        rsl["environment"] = task["environment"]

    if "stdin" in task:
        f = "stdin.%d" % pid
        rsl["stdin"] = f
        rsl["file_stage_in"][transfer_url(task["stdin"], base)] = f
    for s in ("stdout", "stderr"):
        if s in task:
            f = "%s.%d" % (s, pid)
            rsl[s] = f
            rsl["file_stage_out"][f] = transfer_url(task[s], base)

    if "count" in task:
        rsl["host_count"] = str(task["count"])
        if task["count"] > 1:
            rsl["job_type"] = "mpi"
        else:
            rsl["job_type"] = "single"

    # XXX: handle extensions here!

    if target.get('queue', None) is not None:
        rsl["queue"] = target['queue']

    for filename, x in task.get('input_files', {}).iteritems():
        if "/" in filename:
            raise ValueError("Staging with directories is not supported for GRAM5")
        rsl["file_stage_in"][transfer_url(x, base)] = filename

    for filename, x in task.get('output_files', {}):
        if "/" in filename:
            raise ValueError("Staging with directories is not supported for GRAM5")
        rsl["file_stage_out"][filename] = transfer_url(x, base)

    if len(rsl["file_stage_in"]) == 0:
        rsl.pop("file_stage_in")
    if len(rsl["file_stage_out"]) == 0:
        rsl.pop("file_stage_out")
    return from_dict(rsl, ["directory", "scratch_dir"])
            

def submit(rsl, resource, proxy):
    px = tempfile.NamedTemporaryFile()
    px.write(proxy)
    px.flush()

    jobfile = tempfile.NamedTemporaryFile()
    jobfile.write(rsl)
    jobfile.flush()

    env = os.environ.copy()
    env["X509_USER_PROXY"] = px.name

    cmd = ["globusrun", "-fast-batch", "-batch", "-quiet",
           "-file", jobfile.name, "-resource", resource]
    pid = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, close_fds=True)

    (out, err) = tools.communicate_with_timeout(pid, timeout=pilot.spooler.config['job_submit_timeout'])

    if out is None:
        if pid.poll() is None:
            os.kill(pid.pid, signal.SIGKILL)
        raise RuntimeError("globusrun timed out")

    if pid.returncode != 0:
        raise RuntimeError("globusrun failed: " + err)

    return out.strip()

PENDING = 1
ACTIVE = 2
FAILED = 4
DONE = 8
SUSPENDED = 16
UNSUBMITTED = 32
STAGE_IN = 64
STAGE_OUT = 128

CALLBACK_URL = "https://example.com/"

def submit2(rsl, resource, proxy):
    ctx = build_proxy_context(proxy, pilot.spooler.config["common_ssl_capath"])
    sock = SSL.Connection(ctx)
    hostpair, jobmanager = resource.split("/", 1)
    hostport = hostpair.split(":", 1)
    if len(hostport) == 2:
        sock.connect((hostport[0], int(hostport[1])))
    else:
        sock.connect((hostport[0], 2119))
    sock.settimeout(pilot.spooler.config['job_submit_timeout'])
    sock = GSIClientSocket(sock, proxy)
    try:
        code, headers, response = talk_to_gatekeeper(
            sock, hostport[0], "/" + jobmanager,
            ["protocol-version: 2", "job-state-mask: %d" % 0xfffff,
             "callback-url: %s" % CALLBACK_URL,
             'rsl: "' + rsl.replace('"', r'\"').replace("\n", " ") + '"'])
    except socket.timeout:
        raise RuntimeError("gatekeeper timed out")

    if code != '200':
        raise RuntimeError("gatekeeper failed: " + " ".join(response.split()))

    for line in response.split("\r\n"):
        if line.startswith("job-manager-url:"):
            return line.split(" ", 1)[1]

    raise RuntimeError("gatekeeper returned malformed response: " + " ".join(response.split()))

def status(url, proxy):
    """Return GRAM5 job state. Possible states:

    PENDING
    ACTIVE
    FAILED
    SUSPENDED
    DONE
    UNSUBMITTED
    STAGE_IN
    STAGE_OUT

    """
    px = tempfile.NamedTemporaryFile()
    px.write(proxy)
    px.flush()

    env = os.environ.copy()
    env["X509_USER_PROXY"] = px.name

    cmd = ["globusrun", "-fast-batch", "-batch", "-quiet", "-status", url]
    pid = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, close_fds=True)

    (out, err) = tools.communicate_with_timeout(pid, timeout=pilot.spooler.config['job_submit_timeout'])

    if out is None:
        if pid.poll() is None:
            os.kill(pid.pid, signal.SIGKILL)
        raise RuntimeError("globusrun timed out")

    if pid.returncode != 0:
        raise RuntimeError("globusrun failed: " + err)

    return out.strip()

def status2(url, proxy):
    _, hostport, _, _, _, _ = urlparse.urlparse(url)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if ":" not in hostport:
        raise ValueError("invalid job url: %s" % url)
    try:
        host, port = hostport.split(":", 1)
        print (host, int(port))
        sock.connect((host, int(port)))
        sock.close()
        return "PENDING"
    except socket.error, exc:
        if "ECONNREFUSED" in str(exc):
            return "DONE"
        else:
            raise "Unknown failure querying job status: %s" % str(exc)

def build_proxy_context(proxy, capath):
    """
    Build an SSL.Context for GSI authentication using given proxy
    """

    ctx = SSL.Context("sslv3")
    ctx.load_verify_locations(capath=capath)
    px = tempfile.NamedTemporaryFile()
    px.write(proxy)
    px.flush()
    ctx.load_cert_chain(px.name, px.name, lambda prompt: "")

    return ctx

def asn1_sequence_length(bytes):
    """
    return a length of an ASN1 sequence in bytes or -1 if not an ASN1 sequence
    """
    if len(bytes) < 2:
        return -1
    if ord(bytes[0]) != 0x30:
        return -1
    length = ord(bytes[1])
    if length > 127:
        length_bytes = length & 0x7F
        if len(bytes) < 2+length_bytes:
            return -1
        length = 0
        for i in xrange(length_bytes):
            length = (length << 8) | ord(bytes[2+i])
        length = length+length_bytes

    return length+2

class GSIClientSocket:
    """
    Wrapper class for GSI for sockets.
    """

    def __init__(self, sock, delegate=None):
        """
        Return a wrapped GSI Client Socket.

        @param sock: socket to wrap. Socket should be blocking with
        timeouts configured and handled by the caller.        
        @param delegate: a proxy certificate to be used for delegation
        or None if no delegation should be done.

        Reference document: OGF GFD-I.078
        """
        self.sock = sock
        if delegate is None:
            self.key = None
            self.chain = None
        else:
            self.key, self.chain = proxylib.load_proxy(delegate)
        self.context_established = False

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def write(self, data):
        if self.context_established:
            return self.sock.write(data)

        if self.key is None:
            self.context_established = True
            self.sock.write("0"+data)
        else:
            # Now here goes something really weird. If there is NO
            # delegation after the context establishment phase
            # (previous if clause), any cipher suite works. If there
            # is a delegation after context establishment, it fails
            # with any cipher suite except NULL cipher.
            #
            # This is probably a bug in globus GSI implementation.
            if not str(self.sock.get_cipher()).startswith("NULL"):
                self.sock.set_cipher_list("NULL-SHA")
                self.sock.renegotiate()
            self.sock.write("D")
            request = ""
            while True:
                request += self.sock.read(100*1024)
                if asn1_sequence_length(request) == len(request):
                    break
                if len(request) > 100*1024:
                    raise IOError("GSI context error: no cert request in delegation phase")
            try:
                request = X509.load_request_der_string(request)
            except X509.X509Error:
                return IOError("GSI context error: bad certificate request received from server")
            proxy = proxylib.generate_proxycert(request.get_pubkey(),
                                                self.chain[0], self.key,
                                                globus_bug=False)
            self.sock.write(proxy.as_der())

            # Even more strange is the fact that switching back to a
            # strong cipher after delegation does NOT work also. So
            # these lines are commented out:
            #
            # self.sock.set_cipher_list("ALL:!LOW:!SSLv2")
            # self.sock.renegotiate()
            self.context_established = True
            self.sock.write(data)

    send = sendall = write

def talk_to_gatekeeper(socket, server, path, content):
    """
    Talk to a GRAM5 gatekeeper.

    @param socket: a socket (or SSL.Connection). Must be in blocking
    mode. Timeouts are to be handled by the caller.
    @param server:  server host name
    @param path: URI path
    @param content: list of lines to be sent to server
    """
    body = "\r\n".join(content) + "\r\n"
    header_lines = ["POST %s HTTP/1.1" % path,
                    "Host: %s" % server,
                    "Content-Type: application/x-globus-gram",
                    "Content-Length: %d" % len(body),
                    ]
    header = "\r\n".join(header_lines) + "\r\n\r\n"

    socket.send(header)
    socket.send(body)

    reply = ""

    # wait for complete response header
    while True:
        data = socket.recv(1)
        if data == "":
            raise IOError("Gatekeeper did not return a complete header.")
        reply += data
        if "\r\n\r\n" in reply:
            break

    first, rest = reply.split("\r\n", 1)
    version, status, reason = first.strip().split(None, 2)
    msg = httplib.HTTPMessage(StringIO(rest))

    if status != "200":
        return status, msg, ""

    if msg.getheader("Content-Length") is None:
        raise IOError("Gatekeeper returned a malformed response.")

    content_length = int(msg.getheader("Content-Length"))
    response = ""
    while len(response) < content_length:
        data = socket.recv(content_length - len(response))
        if data == "":
            raise IOError("Gatekeeper did not return a complete message body.")
        response += data

    return status, msg, response
