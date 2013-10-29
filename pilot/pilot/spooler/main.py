# -*- encoding: utf-8 -*-

import atexit
import logging, optparse, sys
from StringIO import StringIO
from ConfigParser import SafeConfigParser, NoOptionError
import socket
import eventlet
import eventlet.wsgi
from eventlet.green import time, os, httplib

import signal
from pilot.spooler import config, globus, write_traceback, wsgi

import sqlalchemy as sa
from pilot import model
from pilot.lib import meminfo, resources
from pilot.spooler.matchmaker import Matchmaker
import pilot.spooler

from pilot.spooler import operations, jobs, tasks, tasks_poller, delegations, grid
from pilot.spooler.loops import forever

from M2Crypto import X509


log = logging.getLogger(__name__)


def setup_logging():
    u"""
    Настроить logging согласно конфигурации
    @return: None
    """
    levelmap = {
        0: logging.FATAL,
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
        }
    level = levelmap.get(config.debug_level, logging.ERROR)
    logging.root.setLevel(level)

    for logger in (logging.FileHandler(config.logfile, encoding='utf-8'),
                   logging.StreamHandler()):
        logger.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'))
        logger.setLevel(level)
        logging.root.addHandler(logger)

    class StreamInterceptor(object):
        def __init__(self, logname='error_log'):
            self.log = logging.getLogger(logname)
            
        def write(self, message):
            msg = message.strip("\n")
            if len(msg) > 0:
                self.log.error('%s', msg)

        def flush(self):
            pass

    if not config.debug_mode:
        sys.stdout = StreamInterceptor('stdout')
        sys.stderr = StreamInterceptor('stderr')

def parse_cmdline():
    """
    Parse command line for pilot-spooler
    """
    parser = optparse.OptionParser(usage="%prog [options] ...")
    parser.add_option('-c', type='string', metavar='FILE',
                      help='Configuration file to use (default: %default)',
                      dest='configfile', default='pilot.ini')
    parser.add_option('-d', type='int', metavar='LEVEL',
                      help='Debug level. Available levels are: fatals (0), errors (1), warnings (2), info messages (3), debug messages (4). Default: use value from config file, 1 if unset.',
                      dest='debug_level', default=None)
    parser.add_option('-l', type='string', metavar='FILE',
                      help='Log messages to FILE.',
                      dest='logfile')
    parser.add_option("--link-tasks", action="store_true", dest="link_tasks",
                      help="Recreate task links in the database and exit. Required if you are upgrading a non-empty database and passed version 18.")

    group = optparse.OptionGroup(parser, "Debug options")
    group.add_option('--interactive', action='store_true',
                     help='Connect to the database and run interactive debug session. Requires ipython.', dest='ipython')
    group.add_option('--simulate', action='store_true',
                     help='Run jobrunner in simulation mode',
                     dest='simulate')
    group.add_option('--singlestep', action='store_true',
                     help='Run one mainloop cycle and exit.',
                     dest='singlestep')
    parser.add_option_group(group)

    options, args = parser.parse_args()
    if len(args) != 0:
        parser.print_help()
        sys.exit(0)

    if options.simulate or options.singlestep or options.ipython or options.link_tasks:
        options.debug_mode = True
        options.logfile = None
    else:
        options.debug_mode = False

    for attr in ('configfile', 'logfile'):
        val = getattr(options, attr)
        if val:
            setattr(options, attr, os.path.abspath(val))

    pilot.spooler.load_config_file(options.configfile)
    pilot.spooler.update_config_from_options(options)
    pilot.spooler.config.link_tasks = options.link_tasks

def create_session():
    engine = sa.engine_from_config(config, 'pilot_database.')
    model.init_model(engine)
    return model.meta.Session


def configure_globus():    
    if 'globusrun_ws' in config:
        globus.GLOBUSRUN_WS = config.globusrun_ws
    if 'wsrf_query' in config:
        globus.WSRF_QUERY = config.wsrf_query

    certfiles = (config.common_ssl_certificate,)

    cert = None
    for filename in certfiles:
        try:
            cert = open(filename, 'r').read()
            break
        except IOError:
            pass

    if cert is None:
        log.fatal("Cannot read certificate from known locations (%s)", ', '.join(certfiles))
        sys.exit(1)

    x509 = X509.load_cert_string(cert)
    subject = x509.get_subject()
    if 'CN' not in subject.nid:
        log.fatal("No CN field in certificate subject")
        sys.exit(1)

    cn = subject.get_entries_by_nid(subject.nid['CN'])[0].get_data().as_text()
    hostname = cn.split('/')[-1]

    consumer_url = 'https://%s:%d/gram-state-notification/' % (hostname, config.httpd_port)

    log.debug("Setting notification consumer url to %s", consumer_url)
    globus.RSL.set_notification_consumer_url(consumer_url)
    pilot.spooler.wsn_enabled = True


def sighandler(signal, stack):
    log.info("Got signal %d, terminating" % signal)
    sys.exit(0)

def link_tasks():
    Session = model.meta.Session
    from pilot.model import tools
    jobs = Session.query(model.Job)
    count = jobs.count()
    for i, job in enumerate(jobs):
        print "Processing job %d/%d" % (i+1, count)
        for msg in tools.setup_task_links(job, True):
            print msg


def start_ipython():
    import IPython.ipapi
    from pilot.model.meta import Session
    env = globals()
    env['Session'] = Session
    sys.argv = sys.argv[:1]
    IPython.ipapi.launch_new_instance(env)


hb_log = logging.getLogger('memory')
@forever
def mem_heartbeat():
    info = meminfo.proc_status()
    hb_log.debug("VM: %d kB/%d kB peak, RSS: %d kB/%d kB peak" % (
        info['VmSize']/1024, info['VmPeak']/1024,
        info['VmRSS']/1024, info['VmHWM']/1024))
    eventlet.sleep(config['memory_heartbeat'])
    

def main():
    """pilot-spooler main funcion"""

    profile_filename = os.environ.get("PILOT_SPOOLER_PROFILE")
    if profile_filename is not None:
        import hotshot
        profiler = hotshot.Profile(profile_filename)
        atexit.register(profiler.stop)
        log.debug("Starting profiler, output to %s", profile_filename)
        profiler.start()        
    
    parse_cmdline()
    setup_logging()

    configure_globus()

    signal.signal(signal.SIGTERM, sighandler)
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGHUP, sighandler)

    create_session()
    grid.configure()

    # try to connect to database to detect db connection errors
    try:
        model.meta.Session.execute("SELECT 1").fetchall()
    except sa.exc.OperationalError, exc:
        log.fatal("Cannot connect to database: %s", unicode(exc))
        sys.exit(1)

    if config.link_tasks:
        link_tasks()
        sys.exit(0)

    if config.debug_mode:
        start_ipython()
        sys.exit(0)

    pilot.spooler.matchmaker_port = config.matchmaker_port
    resources.config['capath'] = config.common_ssl_capath
    resources.config['voms_dir'] = config.common_voms_dir
    resources.config['baseurl'] = "http://localhost:%d/" % \
                                  config.matchmaker_port
    resources.config['httplib'] = httplib

    tasks.reset_tasks()
    tasks_poller.refresh()

    def http_server():
        try:
            sock = eventlet.listen(('127.0.0.1', pilot.spooler.matchmaker_port))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            atexit.register(sock.close)
        except Exception, exc:
            log.critical("Failed to create a web server socket: %s", str(exc))
            os.kill(0, signal.SIGTERM)
        app = wsgi.Router()
        app.register('matchmaker', Matchmaker())
        app.register('wsn_task_callback', tasks.wsgi_wsn_notification)
        app.register('job_trigger', operations.trigger)
        app.register('job_delete', jobs.wsgi_delete)
        log.debug("starting wsgi server")
        eventlet.wsgi.server(sock, app, keepalive=False)
        log.critical("WSGI Server crashed (?)")

    # import yappi
    # yappi.start()

    eventlet.spawn_n(mem_heartbeat)
    eventlet.spawn_n(http_server)
    eventlet.spawn_n(operations.loop)
    eventlet.spawn_n(jobs.loop)
    eventlet.spawn_n(jobs.garbage_collector)
    eventlet.spawn_n(tasks.loop)
    eventlet.spawn_n(tasks_poller.loop)
    eventlet.spawn_n(delegations.loop)
    while True:
        eventlet.sleep(10)
        # yappi.print_stats(yappi.SORTTYPE_TTOTAL, limit=10)
