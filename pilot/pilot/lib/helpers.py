# -*- encoding: utf-8 -*-

"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
# Import helpers as desired, or define your own, ie:
#from webhelpers.html.tags import checkbox, password

from decorator import decorator
from pylons import url as p_url, config
from M2Crypto import Rand
import urlparse

from pilot_cli import httplib2m2


__all__ = ['url', 'isots', 'Http', 'SpoolerHttp', 'trace', 'trace_method']

def url(*args, **kwargs):
    kwargs['qualified'] = True
    return p_url(*args, **kwargs)


def isots(timestamp):
    return timestamp.isoformat()[:26] + 'Z'


class Http(httplib2m2.Http):
    def __init__(self, timeout=2):
        httplib2m2.Http.__init__(self, timeout=timeout)
        self.force_exception_to_status_code = True

    def request(self, uri, method="GET", body=None, headers=None, redirections=5, connection_type=None):
        if headers is None:
            headers = {}
        headers['User-Agent'] = 'pilot-httpd'
        
        return httplib2m2.Http.request(self, uri, method, body, headers, redirections, connection_type)


class SpoolerHttp(Http):
    def __init__(self, timeout=2):
        Http.__init__(self, timeout=timeout)
        self.base_uri = 'http://localhost:%d' % config['matchmaker_port']

    def request(self, rel_uri, method="GET", body=None, headers=None, redirections=5, connection_type=None):
        uri = urlparse.urljoin(self.base_uri, rel_uri)
        return Http.request(self, uri, method, body, headers, redirections, connection_type)

def _trace(f, *args, **kw):
    print "trace: calling %s with args %s, %s" % (f.__name__, args, kw)
    rv = f(*args, **kw)
    print "trace: call to %s finished, return value: %s" % (f.__name__, rv)
    return rv

def trace(f):
    return decorator(_trace, f)

def _trace_method(f, *args, **kw):
    self = args[0]
    name = '.'.join((self.__class__.__module__,
                     self.__class__.__name__,
                     f.__name__))
    print "trace_method: calling %s with args %s, %s" % (name, args[1:], kw)
    rv = f(*args, **kw)
    print "trace_method: call to %s finished, return value: %s" % (name, rv)
    return rv

def trace_method(f):
    return decorator(_trace_method, f)
