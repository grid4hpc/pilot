# -*- encoding: utf-8 -*-

"""The base Controller API

Provides the BaseController class for subclassing.
"""
from pylons.controllers import WSGIController
from pylons.templating import render_mako as render
from pylons import request, response, session, tmpl_context as c, config
from pylons.controllers.util import abort as pylons_abort
from pylons.controllers.util import redirect_to
from pylons.decorators.util import get_pylons

from pilot import model
from pilot.model import meta
from pilot.model.meta import Session
from pilot.lib import helpers as h
from pilot.lib import json

from decorator import decorator

import sqlalchemy as sa

import datetime, md5, base64

class BaseController(WSGIController):
    def __init__(self):
        WSGIController.__init__(self)
        self.cert_dn = None
        self.cert_vo = None
        self.cert_fqans = []
        self.fqans_string = ''
        self.cert_owner = None

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        dn = environ.get('SSLAuthN.dn', None)
        vo = environ.get('SSLAuthN.vo', None)
        self.cert_dn = dn and unicode(dn) or None
        self.cert_vo = vo and unicode(vo) or None
        self.cert_fqans = environ.get('SSLAuthN.voms_fqans', [])
        self.fqans_string = ':'.join(self.cert_fqans)
        self.cert_owner = environ.get('SSLAuthN.user', None)
        response.headers['X-Pilot-Version'] = config['version']
        try:
            # WSGIController.__call__ dispatches to the Controller method
            # the request is routed to. This routing information is
            # available in environ['pylons.routes_dict']
            return WSGIController.__call__(self, environ, start_response)
        finally:
            meta.Session.remove()

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return h.isots(obj)
        return json.JSONEncoder.default(self, obj)

def render_data(data, content_type='text/plain', code=200):
    if type(data) is unicode:
        data = data.encode('utf-8')
    elif data is None:
        data = ''
    cksum = md5.md5()
    if isinstance(data, unicode):
        data = data.encode('utf-8')
    cksum.update(data)
    response.headers['Content-Type'] = content_type
    response.headers['Content-Length'] = str(len(data))
    response.headers['Content-MD5'] = base64.b64encode(cksum.digest())
    response.status_int = code
    return data

def render_no_data():
    response.status_int = 204
    response.headers['Content-Length'] = 0
    response.headers['Content-MD5'] = '1B2M2Y8AsgTpgAmY7PhCfg=='
    response.headers.pop('Content-Type')
    return ''

def render_json(result, code=200):
    content_type = 'application/json'
    if 'user-agent' in request.headers and \
           'Mozilla' in request.headers['user-agent'] and \
           'application/json' not in request.headers.get('accept', ''):
        content_type = 'text/javascript'
    data = json.dumps(result, cls=Encoder, indent=2, ensure_ascii=False) + "\n"
    return render_data(data, content_type, code)

def expects_json(func, self, *args):
    """
    Декоратор для методов контроллеров, принимающих на вход
    JSON-объекты.  Метод должен иметь последним аргументом
    опциональный аргумент obj, который при вызове будет иметь значение
    разобранного JSON-объекта.
    """
    request = self._py_object.request
    try:
        obj = json.loads(request.body)
    except ValueError, exc:
        abort(400, 'Failed to load JSON object: %s' % str(exc))
    new_args = args[:-1] + (obj,)
    return func(self, *new_args)
expects_json = decorator(expects_json)

def abort(status_code=None, detail='', headers=None, comment=None):
    send_headers = {}
    if headers is not None:
        send_headers.update(headers)
    send_headers['x-pilot-error-message'] = detail
    pylons_abort(status_code, detail, send_headers, comment)

# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']
