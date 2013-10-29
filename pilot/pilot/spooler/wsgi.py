# -*- encoding: utf-8 -*-

import traceback
from BaseHTTPServer import BaseHTTPRequestHandler

class HttpError(RuntimeError):
    def __init__(self, code, message=None):
        RuntimeError.__init__(self, message)
        self.code = code

class Error404(HttpError):
    def __init__(self, message=None):
        HttpError.__init__(self, 404, message)

class Router(object):
    def __init__(self):
        self.apps = {}
        self.debug = True

    def register(self, name, app):
        self.apps[name] = app

    def error404(self, environ, start_response):
        start_response('404 Not Found', [
            ('Content-type', 'text/plain')
            ])
        yield "Oops. This url is not found on this server:\n\n"
        yield environ['PATH_INFO']
        yield "\n"

    def error500(self, environ, start_response):
        start_response('500 Internal Server Error', [
            ('Content-type', 'text/plain')
            ])
        yield "Internal server error.\n"
        if self.debug:
            if 'exception_traceback' in environ:
                yield "\n\n"
                yield environ['exception_traceback']

    def error_generic(self, code, environ, start_response):
        message, extended = BaseHTTPRequestHandler.responses.get(code, ('Unknown error', 'Unknown error'))
        status_response = '%d %s' % (code, message)
        start_response(status_response, [('Content-type', 'text/plain')])
        yield extended
        yield "\n\nRequest: "
        yield environ.get('REQUEST_METHOD', '???')
        yield ' '
        yield environ.get('PATH_INFO', '')
        yield "\n"

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        path_parts = path_info.split('/')
        if len(path_parts) < 2 or path_parts[1] not in self.apps:
            return self.error404(environ, start_response)
        app = self.apps[path_parts[1]]
        new_path = '/' + '/'.join(path_parts[2:])
        new_env = dict(environ)
        new_env['PATH_INFO'] = new_path
        try:
            return app(new_env, start_response)
        except Error404:
            return self.error404(environ, start_response)
        except HttpError, exc:
            return self.error_generic(exc.code, environ, start_response)
        except Exception, exc:
            environ['exception_traceback'] = traceback.format_exc()
            return self.error500(environ, start_response)
