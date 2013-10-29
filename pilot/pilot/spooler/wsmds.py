# -*- encoding: utf-8 -*-

import logging
import socket
import time
import types
import uuid

from cStringIO import StringIO
from distutils.version import LooseVersion

if not hasattr(socket, "_GLOBAL_DEFAULT_TIMEOUT"):
    socket._GLOBAL_DEFAULT_TIMEOUT = object()

from M2Crypto import SSL

import eventlet
import eventlet.tpool
from eventlet.green import time, socket, threading
from eventlet.green.subprocess import Popen, PIPE

from ngrid import pwc, infosys
from pilot.spooler import config
from pilot_cli.httplib2m2 import Http
from pilot.lib import json, etree

_pilot_testbed_mds_url = 'https://gr4.phys.spbu.ru:8443/wsrf/services/DefaultIndexService'

log = logging.getLogger(__name__)


class SSLFetcher(object):
    def __init__(self, cert, key, cafile=None, capath=None, timeout=None):
        ssl_ctx = SSL.Context("sslv23")
        ssl_ctx.load_cert(cert, key)
        ssl_ctx.load_verify_locations(cafile=cafile, capath=capath)
        ssl_ctx.set_verify(SSL.verify_peer, 10)

        http = Http(timeout=timeout)
        http.add_ssl_context(ssl_ctx)
        http.follow_all_redirects = True
        http.force_exception_to_status_code = True
        
        self.ssl_ctx = ssl_ctx
        self.http = http

    def fetch_url(self, url, method="GET", body=None, timeout=None):
        self.http.timeout = timeout
        response, content = self.http.request(url, method, body,
                                              headers={'User-Agent': 'pilot-spooler'})
        return content, response.status

class RegMDSInfoProvider(object):
    def __init__(self, reg_url, production_only=False):
        self.reg_url = reg_url
        self.__resources = {}
        self.production_only = production_only
        self.query_pool = eventlet.GreenPool(size=15)
        self.cache = {}
        self.cache_ttl = 60*20
        self.last_update = 0
        self.ttl = 600
        self.connection_timeout = config.matchmaker_connection_timeout
        self.fetcher = SSLFetcher(config.common_ssl_certificate, config.common_ssl_privatekey, capath=config.common_ssl_capath)

    def https_send_request(self, url, request):
        return eventlet.tpool.execute(self.fetcher.fetch_url, url, "POST", body=request, timeout=self.connection_timeout)

    @property
    def resources(self):
        if time.time() - self.last_update > self.ttl:
            self.refresh()
        return self.__resources

    def refresh(self):
        log.debug("refresh started")
        result, code = self.fetcher.fetch_url(self.reg_url, timeout = self.connection_timeout)

        if code >= 400:
            log.error("Registration Service Refresh failed: %d (%s)", code, result)
            return

        try:
            data = json.loads(result)
        except ValueError, exc:
            log.critical("Failed to decode registration service answer: %s", result)
            return
        
        sites_to_refresh = []
        for site in data:
            include = True
            if self.production_only:
                if site.get('state', 'unknown').lower() != 'certified':
                    include = False
            if site.get('status', 'unknown').lower() not in ('working', 'testing'):
                include = False

            if not include:
                continue

            mds_epr = site.get('epr_mds', None)
            if mds_epr is None:
                continue
            sites_to_refresh.append(mds_epr)

        qrp = pwc.ResourceProperties(self.https_send_request)
        def get_new_data(url):
            try:
                return url, qrp.query(url)
            except Exception, exc:
                log.debug("update of %s failed: %s", url, str(exc))
                return url, None

        now = time.time()
        for url, data in self.query_pool.imap(get_new_data, sites_to_refresh):
            if data is None:
                continue
            self.cache[url] = {'et': data, 'ts': now}
            log.debug("updated info for %s", url)

        for url in list(self.cache):
            if (now - self.cache[url]['ts']) > self.cache_ttl:
                log.debug("info for %s has expired", url)
                self.cache.pop(url)

        root = etree.Element("mds")
        for url, data in self.cache.iteritems():
            root.append(data['et'])
        final_tree = etree.ElementTree(root)

        resources, errors = infosys.chew_mds(final_tree)
        for error in errors:
            log.debug("MDS Error: %s", error)

        self.__resources = resources
        self.last_update = now

class MDSInfoProvider(object):
    def __init__(self, mds_url):
        self.mds_url = mds_url
        self.__resources = {}
        self.cache = {}
        self.cache_ttl = 60*20
        self.last_update = 0
        self.ttl = 600
        self.connection_timeout = config.matchmaker_connection_timeout
        self.fetcher = SSLFetcher(config.common_ssl_certificate, config.common_ssl_privatekey, capath=config.common_ssl_capath)

    def https_send_request(self, url, request):
        return eventlet.tpool.execute(self.fetcher.fetch_url, url, "POST", body=request, timeout=self.connection_timeout)

    @property
    def resources(self):
        if time.time() - self.last_update > self.ttl:
            self.refresh()
        return self.__resources

    def refresh(self):
        log.debug("refresh started")
        qrp = pwc.ResourceProperties(self.https_send_request)
        now = time.time()
        log.info("querying MDS Index service at %s", self.mds_url)
        mds_info = qrp.query(self.mds_url)

        resources, errors = infosys.chew_mds(etree.ElementTree(mds_info))
        for error in errors:
            log.debug("MDS Error: %s", error)

        self.__resources = resources
        self.last_update = now
