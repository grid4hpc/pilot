# -*- encoding: utf-8 -*-

import os, sys, logging, socket, time
from cStringIO import StringIO
from ConfigParser import SafeConfigParser
from paste import httpserver

from M2Crypto import SSL, X509, threading as m2_threading

from pilot.lib import certlib; certlib.monkey()
import meminfo
from . import serving

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
    ctx.set_verify(SSL.verify_peer | SSL.verify_fail_if_no_peer_cert, 20)    
    ctx.set_cipher_list("ALL:NULL:eNULL")
    os.environ['OPENSSL_ALLOW_PROXY_CERTS'] = '1'

    setup_logging(conf)
    try:
        serving.run_simple(bindaddr, port, application, ssl_context=ctx,
                           use_reloader=False, use_debugger=True)
    except Exception, exc:
        print exc
        raise

def main():
    from optparse import OptionParser
    
    parser = OptionParser(usage="%prog [options...]")
    parser.description = """Run the pilot httpd service."""
    parser.add_option('-c', '--config', dest='config',
                 help="specify config file (default: %default)", default="pilot.ini")
    options, _ = parser.parse_args()

    start(options.config)
