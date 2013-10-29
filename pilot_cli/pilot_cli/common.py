# -*- encoding: utf-8 -*-

import logging
import optparse
import os

from pilot_cli.ext import enum
import proxylib

def default_option_parser():
    u"""
    Возвращает OptionParser, содержащий опции, общие для всех
    программ: proxy, output, verbose, debug, log

    @rtype:  OptionParser
    @return: OptionParser instance
    """
    try:
        from pkg_resources import get_distribution
        pkg_version = get_distribution('pilot_cli').version
    except ImportError:
        pkg_version = 'UNKNOWN'
    parser = optparse.OptionParser(usage="%prog [options] ...", version="%prog " + pkg_version)
    parser.add_option("--help-exit-codes", action="store_true",
                      help="Display help on CLI utilities exit codes",
                      dest="help_exit_codes")
    
    group = optparse.OptionGroup(parser, 'Security options')
    group.add_option("-c", "--cert", "--usercert", metavar="FILE",
                     help="User certificate filename (default: %default)",
                     dest="usercert", default=os.path.expanduser("~/.globus/usercert.pem"))
    group.add_option("-k", "--key", "--userkey", metavar="FILE",
                     help="User certificate key filename (default: %default)",
                     dest="userkey", default=os.path.expanduser("~/.globus/userkey.pem"))
    group.add_option("-p", "--password", "--userkeypass", metavar="XXX",
                     help="Password for user key (default: read from stdin)",
                     dest="userkey_password", default=None)
    group.add_option("-P", "--proxy", metavar="FILE",
                     help="Proxy certificate chain filename (default: %default)",
                     dest="proxy", default=proxylib.get_proxy_filename())
    group.add_option("--noproxy", action="store_false",
                     help="Do not use proxy certificate, use user certificate instead (default: use proxy certificate).",
                     dest="use_proxy", default=True)
    group.add_option("--capath", "-C", metavar="PATH",
                     help="Path to CA certificates, CRLs and signing policies (default: %default)",
                     dest="capath", default="/etc/grid-security/certificates")
    parser.add_option_group(group)
    
    group = optparse.OptionGroup(parser, "Common options")
    group.add_option("-u", "--url", metavar='URL',
                     help="Pilot server to use if not obvious from other arguments. May be specified as a full URL or just a host/host:port combination. (default: $PILOT_SERVER)",
		     dest="pilot_url", default=os.environ.get("PILOT_SERVER", None))
    group.add_option("-D", "--delegation", metavar="NAME",
                     help="Delegation to use (default: \"%default\").",
                     dest="delegation_id", default="default")
    group.add_option("-t", "--timeout", metavar="SECONDS", type="int",
                     help="Command execution timeout, in seconds (default: infinite)",
                     dest="timeout", default=None)
    group.add_option("-j", "--json", action="store_true",
                     help="JSON output. Forces --quiet (default: off)",
                     dest="json")
    group.add_option("-q", "--quiet", action="store_true",
                     help="Do not output any information intended for human beings. (default: off)",
                     dest="quiet")
    group.add_option("-v", "--verbose", action="store_true",
                     help="Be more verbose about what's going on (default: off)",
                     dest="verbose")
    group.add_option("-d", "--debug", type="int", metavar="N",
                     help="Debug level. Available levels are: fatals (0), errors (1), warnings (2), info messages (3), debug messages (4). Default: %default",
                      dest="debug_level", default=1)
    group.add_option("-r", "--retry", type="int", metavar="N",
                     help="Number of request retries in case of network failures. Default: %default",
                     dest="retries", default=3)
    group.add_option("--log", metavar='FILE',
                     help="Output debug information to file instead of stderr.",
                     dest="debug_filename")
    group.add_option("--encoding", metavar="ENC",
                     help="Input/Output encoding to use (default: %default)",
                     dest="io_encoding", default="UTF-8")
    group.add_option("--software", metavar="SW",
                     help="Add these software requirements to the job. "
                     "Requirements for specific package is added only if "
                     "requirements for this package are missing in job "
                     "definition.")    
    parser.add_option_group(group)

    return parser

def finalize_options(options):
    if options.json:
        options.quiet = True
    if options.verbose:
        options.quiet = False

    if not options.pilot_url.startswith("https://"):
        if ":" in options.pilot_url:
            options.pilot_url = "https://%s/" % options.pilot_url.strip("/")
        else:
            options.pilot_url = "https://%s:5053/" % options.pilot_url.strip("/")
                      
def setup_logging(options):
    u"""
    Настроить logging согласно опциям
    @param options: опции, возвращенные OptionParser
    @return: None
    """
    if options.debug_filename:
        logger = logging.FileHandler(options.debug_filename, encoding='utf-8')
    else:
        logger = logging.StreamHandler()

    logger.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'))

    levelmap = {
        0: logging.FATAL,
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
        }
    level = levelmap.get(options.debug_level, logging.ERROR)
    logger.setLevel(level)
    logging.root.setLevel(level)
    logging.root.addHandler(logger)

class NamedInteger(int):
    def set_name(self, name):
        self.name = name

    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return 'None'

def exit_code_value(self, i, key):
    if key == 'success':
        code = NamedInteger(0)
    else:
        code = NamedInteger(i+100)
    code.set_name(key)
    return code

exit_codes = enum.Enum('success', 'submission_failed', 'bad_usage', 'not_found',
                       'access_denied', 'bad_certificate', 'connection_error',
                       'proxy_error', 'ssl_error', 'content_error',
                       'parsing_error', 'file_error', 'internal_server_error',
                       'request_timed_out', 'connection_timed_out',
                       'server_unspecified', 'command_timed_out', 'delegation_error',
                       value_type = exit_code_value)

exit_codes_descriptions = {
    exit_codes.success: "Operation completed successfully",
    exit_codes.submission_failed: "Job submission failed with HTTP error code 4xx",
    exit_codes.bad_usage: "Command has received invalid set of arguments",
    exit_codes.not_found: "The specified URI could not be found.",
    exit_codes.access_denied: "No access to resource (HTTP 401)",
    exit_codes.ssl_error: "Peer certificate validation error",
    exit_codes.connection_error: "Socket error (connection error)",
    exit_codes.parsing_error: "Job or task parsing error",
    exit_codes.file_error: "File not found or could not be read",
    exit_codes.internal_server_error: "HTTP error 500 from server",
    exit_codes.proxy_error: "Failed to load (proxy) certificate",
    exit_codes.content_error: "Network problem: failed to read data from server",
    exit_codes.request_timed_out: 'HTTP Error 408: Request timed out',
    exit_codes.connection_timed_out: 'Connection timed out',
    exit_codes.server_unspecified: 'Pilot server URL is not specified',
    exit_codes.command_timed_out: 'Command execution timed out',
    exit_codes.delegation_error: "Error while delegating proxy certificate",
    }

def print_exit_codes():
    print "Used exit codes:\n"
    print "Code  Short name            Description"
    print "----  --------------------  -----------"
    for exit_code in exit_codes:
        description = exit_codes_descriptions.get(exit_code, "")
        print "%4d  %-20s  %s" % (exit_code, str(exit_code), description)
