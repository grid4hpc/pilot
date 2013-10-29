# -*- encoding: utf-8 -*-

import os, sys, logging, socket, time
from cStringIO import StringIO
from ConfigParser import SafeConfigParser
from paste import httpserver

from M2Crypto import SSL, X509, threading as m2_threading

from pilot.lib import certlib; certlib.monkey()
import meminfo

log = logging.getLogger(__name__)

class AccessLog(object):
    # LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
    log_format = '%(host)s - - %(asctime)s "%(request)s" %(status)s %(response_size)s "%(referer)s" "%(user_agent)s"'
    datefmt = "[%d/%b/%Y:%H:%M:%S %z]"
    def __init__(self):
        self.log = logging.getLogger('access_log')

    def __call__(self, host='-', request='-', status='200', response_size='-',
                 referer='-', user_agent='-'):
        asctime = time.strftime(self.datefmt)
        status = str(status)
        self.log.info(self.log_format % locals())

access_log = AccessLog()    


# pylint: disable-msg=W0221
class DefaultConfigParser(SafeConfigParser):
    def get(self, section, option, *args):
        if (not self.has_option(section, option)) and len(args) > 0:
            return args[0]
        else:
            return SafeConfigParser.get(self, section, option)

    def getint(self, section, option, default=None):
        if not self.has_option(section, option) and default is not None:
            return default
        else:
            return SafeConfigParser.getint(self, section, option)

    def getboolean(self, section, option, default=None):
        if not self.has_option(section, option) and default is not None:
            return default
        else:
            return SafeConfigParser.getboolean(self, section, option)

    def getfloat(self, section, option, default=None):
        if not self.has_option(section, option) and default is not None:
            return default
        else:
            return SafeConfigParser.getfloat(self, section, option)

class M2SecureHTTPServer(httpserver.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass,
                 ssl_context=None, request_queue_size=None,
                 ssl_certificate=None):
        # This overrides the implementation of __init__ in python's
        # SocketServer.TCPServer (which BaseHTTPServer.HTTPServer
        # does not override, thankfully).
        httpserver.HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        self.ssl_context = ssl_context
        self.ssl_certificate = ssl_certificate
        self.static_ssl_environ = {}
        self.stack_cache = dict()
        if ssl_context:
            assert ssl_certificate
            m2_threading.init()
            self.socket = SSL.Connection(ssl_context, self.socket)
            self.ssl_context.set_verify(SSL.verify_peer | SSL.verify_fail_if_no_peer_cert,
                                        20, self.verify_callback)
            # pylint: disable-msg=W0511
            # XXX: better to use X509_VERIFY_PARAM_set_flags on ctx->param
            os.environ['OPENSSL_ALLOW_PROXY_CERTS'] = '1'

            ssl_environ = {
                "wsgi.url_scheme": "https",
                "HTTPS": "on",
                "SSL_SERVER_M_VERSION": ssl_certificate.get_version(),
                "SSL_SERVER_M_SERIAL": ssl_certificate.get_serial_number(),
                "SSL_SERVER_V_START": ssl_certificate.get_not_before().get_datetime().strftime("%c %Z"),
                "SSL_SERVER_V_END": ssl_certificate.get_not_after().get_datetime().strftime("%c %Z")
                }

            for prefix, dn in [("I", ssl_certificate.get_issuer()),
                               ("S", ssl_certificate.get_subject())]:
                wsgikey = 'SSL_SERVER_%s_DN' % prefix
                ssl_environ[wsgikey] = str(dn)

                for name_entry in dn:
                    wsgikey = 'SSL_SERVER_%s_DN_%s' % (prefix,
                                                       name_entry.get_object().get_sn())
                    ssl_environ[wsgikey] = name_entry.get_data().as_text()
            self.static_ssl_environ.update(ssl_environ)
            
        self.server_bind()
        if request_queue_size:
            self.socket.listen(request_queue_size)
        self.server_activate()

    def verify_callback(self, ok, store):
        current_chain = store.get1_chain()
        dn = str(current_chain.pystack[0].get_subject())
        self.stack_cache[dn] = current_chain
        return ok

    def get_request(self):
        class SecureConnection(object):
            def __init__(self, conn, static_environ, peer_stack):
                self.__conn = conn
                self.__static_environ = static_environ
                self.__peer_stack = peer_stack

            def get_static_environ(self):
                return self.__static_environ

            def get_peer_stack(self):
                return self.__peer_stack

            def __getattr__(self, attrib):
                if hasattr(self.__conn, attrib):
                    return getattr(self.__conn, attrib)
                else:
                    return getattr(self.__conn.socket, attrib)
        (conn, info) = self.socket.accept()
        if self.ssl_context:
            peer = conn.get_peer_cert()
            if peer:
                stack = self.stack_cache.get(str(peer.get_subject()), None)
            else:
                stack = None
            conn = SecureConnection(conn, self.static_ssl_environ, stack)
        return (conn, info)        
    

class WSGIServerBase(M2SecureHTTPServer):
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None,
                 request_queue_size=None, ssl_certificate=None):
        M2SecureHTTPServer.__init__(self, server_address,
                                    RequestHandlerClass, ssl_context,
                                    request_queue_size=request_queue_size,
                                    ssl_certificate=ssl_certificate)
        self.wsgi_application = wsgi_application
        self.wsgi_socket_timeout = None

    def get_request(self):
        # If there is a socket_timeout, set it on the accepted
        try:
            (conn,info) = M2SecureHTTPServer.get_request(self)
        except SSL.SSLError, exc:
            log.error("Ignoring SSL error: %s", exc)
            raise socket.error("SSL: %s" % str(exc))
        if self.wsgi_socket_timeout:
            conn.settimeout(self.wsgi_socket_timeout)
        return (conn, info)

class WSGIThreadPoolServer(httpserver.ThreadPoolMixIn, WSGIServerBase):
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None, ssl_certificate=None,
                 nworkers=10, daemon_threads=True,
                 threadpool_options=None, request_queue_size=None):
        WSGIServerBase.__init__(self, wsgi_application, server_address,
                                RequestHandlerClass, ssl_context, ssl_certificate=ssl_certificate,
                                request_queue_size=request_queue_size)
        if threadpool_options is None:
            threadpool_options = {}
        httpserver.ThreadPoolMixIn.__init__(self, nworkers, daemon_threads,
                                            **threadpool_options)


class WSGIServer(httpserver.ThreadingMixIn, WSGIServerBase):
    daemon_threads = False


class WSGIAbort(RuntimeError): pass

class WSGIHandler(httpserver.WSGIHandler):
    def log_request(self, code='-', size='-'):
        # headers may be missing if the request was not parsed.
        headers = getattr(self, 'headers', {})
        access_log(host=self.client_address[0], request=self.requestline,
                   status=code, response_size=size, referer=headers.get('Referer' '-'),
                   user_agent=headers.get('User-Agent', '-'))

    def log_message(self, format, *args):
        log.error("%s - - [%s] %s\n" % (
            self.address_string(),
            self.log_date_time_string(),
            format%args))

    def wsgi_execute(self, environ=None):
        """
        Invoke the server's ``wsgi_application``.
        """

        try:
            self.wsgi_setup(environ)
        except WSGIAbort, exc:
            self.wsgi_start_response(exc[0], [('Content-Type', 'text/plain'),
                                              ('Content-Length', str(len(exc[1])))])
            self.wsgi_write_chunk(exc[1])
            return

        try:
            result = self.server.wsgi_application(self.wsgi_environ,
                                                  self.wsgi_start_response)
            try:
                for chunk in result:
                    self.wsgi_write_chunk(chunk)
                if not self.wsgi_headers_sent:
                    self.wsgi_write_chunk('')
            finally:
                if hasattr(result,'close'):
                    result.close()
                result = None
        except socket.error, exce:
            self.wsgi_connection_drop(exce, environ)
            return
        except:
            if not self.wsgi_headers_sent:
                error_msg = "Internal Server Error\n"
                self.wsgi_curr_headers = (
                    '500 Internal Server Error',
                    [('Content-type', 'text/plain'),
                     ('Content-length', str(len(error_msg)))])
                self.wsgi_write_chunk("Internal Server Error\n")
            raise        

    def wsgi_setup(self, environ=None):
        httpserver.WSGIHandler.wsgi_setup(self, environ)
        self.wsgi_environ.update(self.connection.get_static_environ())
        
        cert = self.connection.get_peer_cert()
        stack = self.connection.get_peer_stack()
        ssl_context = self.connection.ctx
        ssl_environ = {
            'x509_client_cert': cert,
            'x509_client_stack': stack,
        }
        if cert:
            ssl_environ['SSL_CLIENT_CERT'] = cert.as_pem()

        te = self.headers.get('Transfer-Encoding', None)
        if te:
            if te == 'chunked':
                cl = 0
                data = StringIO()
                rfile = self.wsgi_environ['wsgi.input']
                while(True):
                    line = rfile.readline().strip().split(';', 1)
                    chunk_size = int(line[0], 16)
                    if chunk_size <= 0:
                        break
                    cl += chunk_size
                    data.write(rfile.read(chunk_size))
                    crlf = rfile.read(2)
                    if crlf != '\r\n':
                        raise WSGIAbort('400 Bad Request', "Bad transfer encoding (expected '\\r\\n', got %r)" % crlf)
                data.seek(0)
                self.wsgi_environ["wsgi.input"] = data
                self.wsgi_environ["CONTENT_LENGTH"] = str(cl) or ""
            else:
                raise WSGIAbort('501 Unimplemented', "Don't know what to do with Transfer-Encoding: %s" % te)
                
        self.wsgi_environ.update(ssl_environ)

    def handle(self):
        try:
            httpserver.WSGIHandler.handle(self)
        except SSL.SSLError, exc:
            self.log_message("ignoring ssl error: %s" % str(exc))


def setup_logging(conf):
    levelmap = {
        0: logging.FATAL,
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
        }
    level = levelmap.get(conf.getint('httpd', 'debug_level', 4), logging.ERROR)
    logging.root.setLevel(logging.DEBUG)
    
    access_log = logging.getLogger('access_log')
    access_log_filename = conf.get('httpd', 'access_log', None)
    if access_log_filename:
        handler = logging.FileHandler(access_log_filename, encoding='utf-8')
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.INFO)
        access_log.addHandler(handler)

    class AccessLogFilter(object):
        def filter(self, record):
            if record.name == 'access_log':
                return False
            return True

    error_log_filename = conf.get('httpd', 'error_log', None)
    error_format = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                                     datefmt='%a %b %d %H:%M:%S %Y')
    if sys.stdout.isatty():
        # при запуске в терминале дублировать лог в него, включая access_log
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(error_format)
        handler.setLevel(level)
        logging.root.addHandler(handler)
        
    if error_log_filename:
        handler = logging.FileHandler(error_log_filename, encoding='utf-8')
        handler.setFormatter(error_format)
        handler.setLevel(level)
        handler.addFilter(AccessLogFilter())
        logging.root.addHandler(handler)

    class StdoutInterceptor(object):
        def __init__(self, logname='error_log'):
            self.log = logging.getLogger(logname)
            
        def write(self, message):
            msg = message.strip("\n")
            if len(msg) > 0:
                self.log.error('%s', msg)

    sys.stdout = StdoutInterceptor('stdout')
    sys.stderr = StdoutInterceptor('stderr')
        
# pylint: disable-msg=R0914
def start(configfile=None):
    """Subscribe all engine plugins and start the engine."""

    conf = DefaultConfigParser()
    conf.read(configfile)

    conf.defaults()['here'] = os.path.abspath(os.path.dirname(configfile))

    port = conf.getint('httpd', 'port', 5053)
    bindaddr = conf.get('httpd', 'host', '0.0.0.0')

    from paste.deploy import loadapp
    application = loadapp('config:' + os.path.abspath(configfile))

    ssl_cert_location = conf.get('common', 'ssl_certificate', '/etc/grid-security/containercert.pem')
    ssl_key_location = conf.get('common', 'ssl_privatekey', '/etc/grid-security/containerkey.pem')
    try:
        ssl_certificate = X509.load_cert(ssl_cert_location)
    except Exception, exc:
        log.error("Failed to load certificate: %s" % str(exc))
        sys.exit(1)
    ctx = SSL.Context('sslv23')
    ctx.set_session_id_ctx("pilot-xxx")
    try:
        ctx.load_cert(ssl_cert_location, ssl_key_location)
    except Exception, exc:
        log.error("Failed to load key: %s" % str(exc))
        sys.exit(1)
    ctx.load_verify_locations(
        cafile=conf.get('common', 'ssl_cafile', None),
        capath=conf.get('common', 'ssl_capath', '/etc/grid-security/certificates'))
    ctx.set_cipher_list("ALL:NULL:eNULL")

    server_address = (bindaddr, port)
    handler = WSGIHandler
    handler.server_version = "PilotWSGIServer (based on %s)" % handler.server_version
    handler.protocol_version = "HTTP/1.0"

    setup_logging(conf)
    #server = WSGIThreadPoolServer(application, server_address, handler,
    #                              ssl_context=ctx, ssl_certificate=ssl_certificate,
    #                              request_queue_size=9, nworkers=10)
    server = WSGIServer(application, server_address, handler,
                        ssl_context=ctx, ssl_certificate=ssl_certificate,
                        request_queue_size=100)
    server.daemon_threads = True
    server.wsgi_socket_timeout = 3
    try:
        print "serving on %s://%s:%s" % ('https', bindaddr, port)
        server.serve_forever()
    except KeyboardInterrupt:
        pass

def main():
    from optparse import OptionParser
    
    parser = OptionParser(usage="%prog [options...]")
    parser.description = """Run the pilot httpd service."""
    parser.add_option('-c', '--config', dest='config',
                 help="specify config file (default: %default)", default="pilot.ini")
    options, _ = parser.parse_args()

    start(options.config)
