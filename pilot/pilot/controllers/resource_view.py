import logging, pickle, pprint

from paste.util import mimeparse

from pylons import request, response, session, config, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from pilot.lib.base import BaseController, render, render_data, render_json
from pilot.lib import resources

log = logging.getLogger(__name__)

class ResourceViewController(BaseController):
    def index(self):
        try:
            res = resources.list_resources()
            for resource in res.itervalues():
                try:
                    resource.acls = resource.get_acls()
                except AttributeError:
                    resource.acls = []
            formats = ('text/plain', 'text/html')
            format = mimeparse.best_match(formats,
                                          request.headers.get('Accept', '*/*'))
            if (format == ''):
                format = formats[0]
            if (format == 'text/plain'):
                return render_data((pprint.pformat(res) + '\n'))
            elif (format == 'text/html'):
                return render('/resource_view/index.html', {'res': res})
        except resources.ResourcesError, exc:
            abort(503)

    def index2(self):
        try:
            res = resources.list_resources()
            for realm, host, port, lrms, queue in res.iterkeys():
                yield resources.resource_name(realm, host, port, lrms, queue) + "\n"
        except resources.ResourcesError, exc:
            abort(503)
                           
