# -*- encoding: utf-8 -*-

import logging
import BaseHTTPServer
from M2Crypto import X509, EVP

from gridproxy import voms
from pilot.lib import certlib ; certlib.monkey()

from hashlib import sha1

log = logging.getLogger(__name__)

def testing_mode(environ):
    if environ['PATH_INFO'] == '/_test_vars':
        return True
    if ('paste.testing' in environ) and environ['paste.testing']:
        return True

class TestingEnviron(object):
    def __init__(self):
        self.environ = {}
        self.setup()

    def setup(self,
              dn='/C=RU/O=RDIG/OU=users/OU=sinp.msu.ru/CN=Test User',
              owner_hash='3ab5b9f8e522cf7375db9b6d7ac18d1fc629d565',
              vo='test',
              fqans=['/test']):
        self.environ['SSLAuthN.dn'] = dn
        self.environ['SSLAuthN.user'] = owner_hash
        self.environ['SSLAuthN.vo'] = vo
        self.environ['SSLAuthN.voms_fqans'] = fqans

    def update(self, environ):
        environ.update(self.environ)

__for_tests = TestingEnviron()
testing_environ = __for_tests.update
configure_testing_environ = __for_tests.setup

def noproxy_chain(stack):
    stk = X509.X509_Stack()
    proxy = True
    for cert in stack:
        if proxy and cert.is_proxy():
            continue
        else:
            proxy = False
        stk.push(cert)

    return stk

def combined_subject_hash(stack):
    md = EVP.MessageDigest('sha1')
    for cert in stack:
        md.update(cert.get_subject().as_der())
    return md.final().encode('hex')

def load_cert_info(environ):
    if 'x509_client_cert' in environ and 'x509_client_stack' in environ:
        cert = environ['x509_client_cert']
        stack = environ['x509_client_stack']
        if (cert is None) or (stack is None):
            raise RuntimeError("Could not get X509 certificate and chain from WSGI container")
    elif 'SSL_CLIENT_CERT' in environ:
        try:
            cert = X509.load_cert_string(environ['SSL_CLIENT_CERT'])
            stack = X509.X509_Stack()
            stack.push(cert)
            i = 0
            while True:
                k = 'SSL_CLIENT_CERT_CHAIN_%d' % i
                if k in environ:
                    stack.push(X509.load_cert_string(environ[k]))
                else:
                    break
                i += 1
            environ['x509_client_cert'] = cert
            environ['x509_client_stack'] = stack
        except (KeyError,), exc:
            raise RuntimeError("Could not get X509 certificate and chain from WSGI container: %s" % str(exc))
    
    chain = noproxy_chain(stack)
    environ['SSL_CLIENT_CERT'] = chain[0].as_pem()
    environ['SSLAuthN.dn'] = str(chain[0].get_subject())
    environ['SSLAuthN.user'] = combined_subject_hash(chain)

class TranscodingStartResponse(object):
    def __init__(self, start_response):
        self.start_response = start_response

    def __call__(self, status, headers, exc_info=None):
        if type(status) is unicode:
            status = status.encode('utf-8')
        h = []
        for k, v in headers:
            if type(k) is unicode:
                k = k.encode('utf-8')
            if type(v) is unicode:
                v = v.encode('utf-8')
            h.append((k, v))
        return self.start_response(status, h)

class SslVomsAuthNMiddleware(object):
    def __init__(self, app, voms_dir="/etc/grid-security/vomsdir", cert_dir="/etc/grid-security/certificates"):
        self.app = app
        self.voms_dir = voms_dir
        self.cert_dir = cert_dir

    def error(self, code, environ, start_response, extra_message=None):
        responses = BaseHTTPServer.BaseHTTPRequestHandler.responses[code]
        short_response = responses[0]
        long_response = "%d %s\n\n%s\n" % (code, responses[0], responses[1])
        if extra_message is not None:
            long_response += "\n"
            long_response += extra_message
            
        start_response('%d %s' % (code, short_response),
                       [("content-type", "text/plain"),
                        ("content-length", str(len(long_response)))])
        return long_response

    def check_voms(self, environ):
        cert = environ['x509_client_cert']
        stack = environ['x509_client_stack']
        voms_ac = voms.VOMS(self.voms_dir, self.cert_dir)

        try:
            voms_ac.from_x509_cert_chain(cert, stack)
            environ['SSLAuthN.voms_ac'] = voms_ac
            environ['SSLAuthN.vo'] = voms_ac.vo
            environ['SSLAuthN.voms_fqans'] = voms_ac.fqans
            environ['SSLAuthN.voms_error'] = None
            md = EVP.MessageDigest('sha1')
            md.update(voms_ac.server)
            md.update("\n")
            md.update(voms_ac.serverca)
            md.update("\n")
            for fqan in voms_ac.fqans:
                md.update(fqan)
                md.update("\n")            
            environ['SSLAuthN.identity'] = md.final().encode('hex')
        except voms.VOMSError, exc:
            if exc.name in ('none', 'noext', 'nodata'):
                environ['SSLAuthN.voms_ac'] = None
                environ['SSLAuthN.vo'] = None
                environ['SSLAuthN.voms_fqans'] = []
                environ['SSLAuthN.voms_error'] = exc
                environ['SSLAuthN.identity'] = None
            else:
                raise    

    def __call__(self, environ, start_response):
        if testing_mode(environ):
            testing_environ(environ)
        else:
            if environ.get('HTTPS', '0') not in ('1', 'on'):
                return self.error(401, environ, start_response)

            if ('x509_client_cert' in environ) and ('x509_client_stack' in environ):
                try:
                    load_cert_info(environ)
                    self.check_voms(environ)
                except RuntimeError, exc:
                    return self.error(401, environ, start_response, str(exc))
            elif 'SSL_CLIENT_CERT' in environ:
                try:
                    load_cert_info(environ)
                    self.check_voms(environ)
                except RuntimeError, exc:
                    return self.error(401, environ, start_response, str(exc))
                    
            elif 'GRST_CRED_0' in environ:
                fqans = environ['SSLAuthN.voms_fqans'] = []
                for i in xrange(100):
                    k = 'GRST_CRED_%d' % i
                    if k not in environ:
                        break
                    kind, notbefore, notafter, cc_delegation, dn = environ[k].split(' ', 4)
                    if kind == 'X509USER':
                        #environ['SSLAuthN.user'] = dn
                        #environ['SSLAuthN.identity'] = sha1(dn).hexdigest()
                        environ['SSLAuthN.dn'] = dn
                        environ['SSLAuthN.user'] = sha1(dn).hexdigest()
                    elif kind == 'VOMS':
                        fqans.append(dn)
                idd = sha1(environ['SSLAuthN.dn'])
                for fqan in fqans:
                    idd.update(fqan)
                environ['SSLAuthN.identity'] = idd.hexdigest()
                if len(fqans) > 0:
                    environ['SSLAuthN.vo'] = fqans[0].split('/')[1]
                else:
                    environ['SSLAuthN.vo'] = None
            else:
                return self.error(500, environ, start_response)

            log.debug("user=%s, identity=%s", environ['SSLAuthN.user'], environ['SSLAuthN.identity'])
            log.debug("dn=%s, vo=%s, fqans=%s", environ['SSLAuthN.dn'], environ['SSLAuthN.vo'], environ['SSLAuthN.voms_fqans'])
            # XXX: check active cipher and allow NULL ciphers only for WS-N
        return self.app(environ, TranscodingStartResponse(start_response))
