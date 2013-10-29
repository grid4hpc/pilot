import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from cStringIO import StringIO

from pilot.lib import etree

from pilot.lib.base import BaseController
from pilot.lib.helpers import url

log = logging.getLogger(__name__)

APP_NS = 'http://www.w3.org/2007/app'
ATOM_NS = 'http://www.w3.org/2005/Atom'

class AtompubController(BaseController):

    def index(self):
        srv = etree.Element(etree.QName(APP_NS, 'service'))
        ws = etree.SubElement(srv, etree.QName(APP_NS, 'workspace'))
        etree.SubElement(ws, etree.QName(ATOM_NS, 'title')).text = 'Pilot Service'
        coll = etree.SubElement(ws, etree.QName(APP_NS, 'collection'))
        coll.set('href', url('jobs'))
        etree.SubElement(coll, etree.QName(ATOM_NS, 'title')).text = 'Jobs Service'
        etree.SubElement(coll, etree.QName(APP_NS, 'accept')).text = 'application/json'
        coll = etree.SubElement(ws, etree.QName(APP_NS, 'collection'))
        coll.set('href', url('job_policy'))
        etree.SubElement(coll, etree.QName(ATOM_NS, 'title')).text = 'Jobs Policy'
        coll = etree.SubElement(ws, etree.QName(APP_NS, 'collection'))
        coll.set('href', url('version'))
        etree.SubElement(coll, etree.QName(ATOM_NS, 'title')).text = 'Service Version'

        buf = StringIO()
        if 'accept' in request.headers and 'application/xml' in request.headers['accept']:
            response.headers['content-type'] = 'application/xml'
            buf.write('<?xml-stylesheet type="text/xsl" href="/atompub.xsl"?>\n')
        else:
            response.headers['content-type'] = 'application/atomsvc+xml'
        etree.ElementTree(srv).write(buf)
        return buf.getvalue()
