# -*- encoding: utf-8 -*-

import eventlet
from M2Crypto import SSL
from pilot_cli.httplib2m2 import Http

class SSLFetcher(object):
    def __init__(self,
                 cert="/etc/grid-security/hostcert.pem",
                 key="/etc/grid-security/hostkey.pem",
                 cafile=None,
                 capath="/etc/grid-security/certificates",
                 timeout=None):
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

    def fetch_url(self, url, method="GET", body=None, extra_headers={}, timeout=None):
        self.http.timeout = timeout
        headers = {'User-Agent': 'pilot-spooler'}
        headers.update(extra_headers)
        response, content = self.http.request(url, method, body,
                                              headers=headers)
        return content, response.status, dict(response)

class EventletFetcher(object):
    def __init__(self, fetcher):
        self.fetcher = fetcher

    def fetch_url(self, *args, **kwargs):
        return eventlet.tpool.execute(self.fetcher.fetch_url, *args, **kwargs)
