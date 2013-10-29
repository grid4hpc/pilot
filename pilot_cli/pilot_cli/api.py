# -*- encoding: utf-8 -*-

import codecs
import datetime
import inspect
import getpass
import httplib
import logging
from optparse import OptionGroup
import os
import posix
import pytz
import re
import signal
import socket
import sys
import time
import traceback
from urlparse import urljoin

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

try:
    import json
except ImportError:
    import simplejson as json

from M2Crypto import SSL, RSA, EVP, BIO, X509

import common
from common import exit_codes
from httplib2m2 import Http, HttpLib2ErrorWithResponse
import proxylib

log = logging.getLogger("pilot_cli.api")
_date_iso_fmt_re = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{2,6})?Z$')

def isoformat(dts):
    """Отформатировать дату/время с точностью до микросекунд по ISO 8601,
       если в дате присутствует tzinfo, то предварительно перевести дату в UTC.

       @param dts: объект datetime
    """
    if dts.tzinfo:
        rc = dts.astimezone(pytz.utc).isoformat()[:-6]
    else:
        rc = dts.isoformat()
    if dts.microsecond == 0:
        rc += ".000000"
    return rc + "Z"

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo is None:
                args = list(time.gmtime(time.mktime(obj.timetuple())))[:6]
                args.append(obj.microsecond)
                args.append(pytz.utc)
                # pylint: disable-msg=W0142
                fixed_dt = datetime.datetime(*args)
                return isoformat(fixed_dt)
            else:
                return isoformat(obj)
        else:
            return json.JSONEncoder.default(self, obj)

def json_dumps(*args, **kwargs):
    kwargs['cls'] = JSONEncoder
    kwargs.setdefault('ensure_ascii', False)
    return json.dumps(*args, **kwargs)

def convert_dates(obj, converted=None):
    if converted is None:
        converted = []
    if id(obj) in converted:
        return
    converted.append(id(obj))

    if type(obj) is dict:
        keys = obj.keys()
    elif type(obj) is list:
        keys = range(0, len(obj))
    else:
        return
    for key in keys:
        if key not in ['ts', 'server_time', 'created', 'expires', 'modified']:
            pass
        value = obj[key]
        if type(value) is dict:
            convert_dates(value, converted)
        elif type(value) is list:
            for item in value:
                convert_dates(item)
        elif type(value) is str or type(value) is unicode:
            if _date_iso_fmt_re.match(value):
                args = list(time.strptime(value[:19], '%Y-%m-%dT%H:%M:%S')[0:6])
                if '.' in value and len(value) > 26:
                    micro = int(value[20:26])
                else:
                    micro = 0
                args.extend([micro, pytz.utc])
                # pylint: disable-msg=W0142
                obj[key] = datetime.datetime(*args)
            

def json_loads(*args, **kwargs):
    result = json.loads(*args, **kwargs)
    convert_dates(result)
    return result

def handle_http_errors((response, content), uri):
    if response.status == 401:
        errmsg("You have no access to resource %s", uri)
        log.debug("HTTP Error %d: %s", response.status, content.strip())
        sys.exit(exit_codes.access_denied)
    elif response.status == 404:
        msg = "The specified URI (%s) could not be found" % uri
        if 'x-pilot-error-message' in response:
            msg += ": " + response['x-pilot-error-message']
        else:
            msg += ":\n" + content.strip()
        errmsg(msg)
        log.debug("HTTP Error %d: %s", response.status, content.strip())
        sys.exit(exit_codes.not_found)
    elif response.status == 408:
        errmsg("HTTP Error 408: Request timed out")
        log.debug("HTTP Error %d: %s", response.status, content.strip())
        sys.exit(exit_codes.request_timed_out)
    elif 500 <= response.status < 600:
        errmsg("Server Error %d: %s", response.status, content.strip())
        log.debug("HTTP Error %d: %s", response.status, content.strip())
        sys.exit(exit_codes.internal_server_error)
    elif 400 <= response.status < 500:
        errmsg("Request Error: %s (HTTP status code %d)", content.strip(), response.status)
        log.debug("HTTP Error %d: %s", response.status, content.strip())
        sys.exit(exit_codes.bad_usage)

    return response, content


class PilotError(RuntimeError):
    """
    Базовый класс для всех ошибок PilotService
    """
    pass

class UnsupportedProtocolError(PilotError):
    pass

class PilotService(object):
    def __init__(self, baseurl, ssl_ctx, retries=1):
        """
        baseurl - корневой URL для всех запросов pilot
        ssl_ctx - инициализированный SSL.Context со всеми сертификатами и т.п.
        retries - количество попыток повторения запроса, в случае сбоя
        """
        self.baseurl = baseurl
        self.retries = retries
        self._cli_version = None

        http = Http()
        http.add_ssl_context(ssl_ctx)
        http.follow_all_redirects = True
        
        self.http = http

    def do_request(self, request):
        try:
            self.validate_response(data, headers)
            return data, headers
        except IOError, e:
            print >> sys.stderr, str(e)
            sys.exit(exit_codes.content_error)

    def request(self, relpath, method="GET", data=None, mimetype="application/json", headers=None):
        uri = urljoin(self.baseurl, relpath)
        if not uri.startswith('http'):
            log.debug("Bad request URI: %s", uri)
            errmsg("Pilot server address is not specified. Either set PILOT_SERVER environment variable or use --url option.")
            sys.exit(exit_codes.server_unspecified)

        send_headers = {}
        if headers:
            send_headers.update(headers)
        send_headers.update({"user-agent": "pilot_cli-%s" % self.cli_version(),
                             "connection": "close"})
        if data:
            if isinstance(data, unicode):
                data = data.encode("utf-8")
            send_headers.update({"content-type": mimetype,
                                 "content-length": str(len(data)),
                                 "content-md5": md5(data).digest().encode("base64")})
        else:
            send_headers["content-length"] = "0"

        try:
            log.debug("Sending %s to %s", method, uri)
            attempt = 0
            while attempt < self.retries:
                try:
                    attempt += 1
                    response, content = self.http.request(uri, method, body=data, headers=send_headers)
                    break
                except httplib.BadStatusLine:
                    log.debug("Attempt %d failed", attempt)
                    if attempt < self.retries:
                        continue
                    else:
                        raise
            log.debug("Response literal contents:\n%s", content)

            errors = []
            if ('content-length' in response) and (len(content) != int(response['content-length'])):
                errors.append("Conent-Length does not match response length.")
            if ('content-md5' in response) and (md5(content).digest() != response['content-md5'].decode('base64')):
                errors.append("Content-MD5 does not match response checksum.")

            if len(errors) > 0:
                errmsg("Server response contains errors:")
                for error in errors:
                    errmsg(" * %s", error)
                sys.exit(exit_codes.content_error)                
                
            return response, content
        except SSL.Checker.SSLVerificationError, exc:
            errmsg("SSL Verification Error: %s", str(exc))
            sys.exit(exit_codes.bad_certificate)
        except SSL.SSLError, exc:
            errmsg("SSL Error: %s", str(exc))
            sys.exit(exit_codes.ssl_error)
        except socket.timeout, exc:
            errmsg("Socket timeout: %s (%d)", exc.args[1], exc.args[0])
            sys.exit(exit_codes.connection_timed_out)            
        except socket.error, exc:
            errmsg("Socket error: %s (%d)", exc.args[1], exc.args[0])
            sys.exit(exit_codes.connection_error)
        except HttpLib2ErrorWithResponse, exc:
            errmsg("Error getting response from server: %s", str(exc))
            sys.exit(exit_codes.content_error)
        except SystemExit, exc:
            raise
        except Exception, exc:
            errmsg("Unknown error while making HTTP request: %s (type: %s)", str(exc), type(exc).__name__)
            log.debug("Uncaught exception:\n%s", traceback.format_exc())
            sys.exit(exit_codes.content_error)

    def get(self, relpath, headers=None):
        return handle_http_errors(self.request(relpath, headers=headers), relpath)

    def delete(self, relpath):
        return handle_http_errors(self.request(relpath, method="DELETE"), relpath)

    def post(self, relpath, data, mimetype="application/json"):
        return handle_http_errors(self.request(relpath, method="POST", data=data, mimetype=mimetype), relpath)

    def put(self, relpath, data, mimetype="application/json"):
        return handle_http_errors(self.request(relpath, method="PUT", data=data, mimetype=mimetype), relpath)

    def server_version(self):
        return self.get("/version")[1]

    def cli_version(self):
        if not self._cli_version:
            try:
                from pkg_resources import get_distribution
                self._cli_version = get_distribution('pilot_cli').version
            except ImportError:
                self._cli_version = 'UNKNOWN'
        return self._cli_version

    def refresh_delegation(self, delegation_id, proxy_filename):
        response, content = self.request("/delegations/%s" % delegation_id)
        if response.status == 404:
            self.update_delegation(delegation_id)
            next_expiration = None
        else:
            info = json_loads(content)
            next_expiration = info.get("next_expiration")

        key, chain = proxylib.load_proxy(open(proxy_filename).read())
        # M2Crypto 0.16 does NOT provide any functions to read time value, except string value :(
        # so instead:
        # proxy_expiration = chain[0].get_not_after().get_datetime()
        # we have this shit:
        proxy_expiration = datetime.datetime.fromtimestamp(
            time.mktime(time.strptime(str(chain[0].get_not_after()),
                                      "%b %d %H:%M:%S %Y %Z")), pytz.UTC)
        
        if (next_expiration is None) or (proxy_expiration > next_expiration):
            self.renew_delegation(delegation_id, key, chain)

    def update_delegation(self, delegation_id, renewable=False,
                          myproxy_server=None, credname=None):
        data = {"renewable": renewable,
                "myproxy_server": myproxy_server,
                "credname": credname}
        response, content = self.request("/delegations/%s" % delegation_id,
                                         method="PUT", data=json_dumps(data))
        if response.status >= 400:
            if response.status == 404:
                raise UnsupportedProtocolError("Delegation creation is not supported.")
            raise PilotError("Failed to create delegation %s: %s (%d)" % (
                delegation_id, content, response.status))

    def renew_delegation(self, delegation_id, key, chain):
        response, content = self.request("/delegations/%s/pubkey" % delegation_id,
                                         headers={"accept": "application/x-pkcs1+pem"})
        if response.status != 200:
            raise PilotError("Failed to fetch delegation renew public key for delegation %s" % delegation_id)
        new_key = RSA.load_pub_key_bio(BIO.MemoryBuffer(content))
        new_pkey = EVP.PKey()
        new_pkey.assign_rsa(new_key)
        new_proxy = proxylib.generate_proxycert(new_pkey, chain[0], key, full=True)

        new_stack = X509.X509_Stack()
        new_stack.push(new_proxy)
        for cert in chain:
            new_stack.push(cert)
        response, content = self.request("/delegations/%s/renew" % delegation_id, method="PUT",
                                         data=new_stack.as_der(),
                                         mimetype="application/x-pkix-chain+der")
        if response.status != 204:
            raise PilotError("Failed to update delegation %s: %s" % (delegation_id, content))

def errmsg(*args, **kwargs):
    if len(args) == 1:
        msg = args[0]
    elif len(kwargs) != 0:
        msg = args[0] % kwargs
    else:
        msg = args[0] % args[1:]

    print >> sys.stderr, msg


def sigalrm_handler(sig, stack):
    errmsg("Operation timed out.")
    sys.exit(exit_codes.command_timed_out)

def askpass(prompt, options):
    if not options.userkey_password:
        if options.quiet:
            prompt = ""
        else:
            prompt = "Password for %s: " % options.userkey

        if posix.isatty(sys.stdin.fileno()):
            password = getpass.getpass(prompt)
        else:
            if prompt != "":
                sys.stdout.write(prompt)
                sys.stdout.flush()
            password = raw_input()

        options.userkey_password = password
        
    return options.userkey_password

def build_ssl_ctx(options):
    log.debug("creating SSL Context")
    ssl_ctx = SSL.Context("tlsv1")

    ssl_ctx.load_verify_locations(capath=options.capath)
    ssl_ctx.set_verify(SSL.verify_peer, 10)

    try:
        if options.use_proxy:
            ssl_ctx.load_cert_chain(options.proxy, options.proxy,
                                    lambda prompt: askpass(prompt, options))
        else:
            ssl_ctx.load_cert(options.usercert, options.userkey,
                              lambda prompt: askpass(prompt, options))
    except SSL.SSLError, exc:
        errmsg("Failed to load certificate: %s", str(exc))
        sys.exit(exit_codes.proxy_error)

    return ssl_ctx

def setup_encoding(encoding):
    need_setup = False
    if sys.stdout.encoding is None:
        need_setup = True
    else:
        if codecs.lookup(sys.stdout.encoding) != codecs.lookup(encoding):
            need_setup = True

    if need_setup:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout)
        sys.stderr = codecs.getwriter(encoding)(sys.stderr)
        sys.stdin = codecs.getreader(encoding)(sys.stdin)


class ExceptionHandler(object):
    def __init__(self):
        self.original_hook = sys.excepthook
        sys.excepthook = self.handle_exception

    def handle_exception(self, tipe, value, traceback):
        if issubclass(tipe, UnicodeError):
            print >> sys.stderr, "%s was unable to output some of the characters. Please specify --encoding option which supports a broader character set (UTF-8 is recommended)." % os.path.basename(sys.argv[0])
        else:
            self.original_hook(tipe, value, traceback)        

def setup_app(usage="%prog [options] ...",
              description=None,
              argstest=lambda args: len(args) == 0,
              logname='app',
              extra_options=None):
    u"""Функция, выполняющая основные настройки cli-приложения

    @param usage: строка использования для OptionParser
    @param description: описание приложения
    @param argstest: функция, проверяющая правильность неименованных аргументов
    @param logname: имя программы для сообщений в log
    """
    parser = common.default_option_parser()
    parser.usage = usage
    parser.description = description and re.sub(r"\s+", " ", description)
    if extra_options is not None:
        group = OptionGroup(parser, parser.expand_prog_name("%prog options"))
        extra_options(group)
        parser.add_option_group(group)
    (options, args) = parser.parse_args()

    setup_encoding(options.io_encoding)
    ExceptionHandler()

    if options.help_exit_codes:
        common.print_exit_codes()
        sys.exit(exit_codes.success)

    if len(inspect.getargspec(argstest)[0]) == 1:
        args_valid = argstest(args)
    else:
        args_valid = argstest(args, options)
    
    if not args_valid:
        parser.print_help()
        sys.exit(exit_codes.bad_usage)
        
    common.setup_logging(options)
    common.finalize_options(options)

    service = PilotService(options.pilot_url, build_ssl_ctx(options),
                           options.retries)

    if options.timeout is not None:
        signal.signal(signal.SIGALRM, sigalrm_handler)
        signal.alarm(options.timeout)

    return (options, args, logging.getLogger(logname), service)
