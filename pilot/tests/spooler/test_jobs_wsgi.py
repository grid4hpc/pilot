# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr
from nose.tools import assert_raises

from pilot.spooler import jobs, wsgi

import mock, pdb
from cStringIO import StringIO
import cPickle as pickle

def test_delete_bad_method_path():
    environ = { 'REQUEST_METHOD': 'GET' }
    response = [None]
    def start_response(status, headers):
        response[0] = (status, headers)

    assert_raises(wsgi.HttpError, jobs.wsgi_delete, environ, start_response)

    environ['REQUEST_METHOD'] = "DELETE"
    assert_raises(wsgi.Error404, jobs.wsgi_delete, environ, start_response)

    environ['PATH_INFO'] = '/blah/'
    assert_raises(wsgi.Error404, jobs.wsgi_delete, environ, start_response)

    environ['PATH_INFO'] = '/'
    assert_raises(wsgi.Error404, jobs.wsgi_delete, environ, start_response)

@mock.patch('pilot.spooler.jobs.abort')
def test_wsgi_good(jobs_abort):
    job = create_job()
    environ = { 'REQUEST_METHOD': 'DELETE',
                'PATH_INFO': '/%s/' % job.jid }
    response = [None]
    def start_response(status, headers):
        response[0] = (status, headers)

    assert job.state.s == u"new"
    result = ''.join(list(jobs.wsgi_delete(environ, start_response)))
    assert response[0][0].startswith('204 ')
    assert job.deleted
    assert job.state.s == u"new"
    assert jobs_abort.call_count == 0

    job = create_job()
    environ = { 'REQUEST_METHOD': 'DELETE',
                'PATH_INFO': '/%s/' % job.jid }
    response = [None]
    def start_response(status, headers):
        response[0] = (status, headers)

    job.add_state(u"running")
    assert job.state.s == u"new"
    result = ''.join(list(jobs.wsgi_delete(environ, start_response)))
    assert response[0][0].startswith('204 ')
    assert job.deleted
    assert jobs_abort.call_count == 1
