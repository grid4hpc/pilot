# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr
from nose.tools import assert_raises

from pilot.spooler import jobs, operations, tasks, globus, wsgi

import mock, pdb
from cStringIO import StringIO
import cPickle as pickle

fake_resources = [("tb01.ngrid.ru", "test", "pbs")]

from test_tasks_state import fake_state_xml

def test_wsn_bad_method_path():
    environ = { 'REQUEST_METHOD': 'GET' }
    response = [None]
    def start_response(status, headers):
        response[0] = (status, headers)

    result = ''.join(list(tasks.wsgi_wsn_notification(environ, start_response)))
    assert response[0][0].startswith('405 ')
    assert result.startswith('405 ')

    environ['REQUEST_METHOD'] = "POST"
    assert_raises(wsgi.Error404, tasks.wsgi_wsn_notification, environ, start_response)

    environ['PATH_INFO'] = '/blah/'
    environ['wsgi.input'] = StringIO()
    assert_raises(wsgi.HttpError, tasks.wsgi_wsn_notification, environ, start_response)

    environ['wsgi.input'] = StringIO(pickle.dumps(globus.State.from_string(fake_state_xml(u"failed"))))
    assert_raises(wsgi.Error404, tasks.wsgi_wsn_notification, environ, start_response)
    
@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_wsn_good(generate_rsl, globus_job_submit, matchmake, spawn):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    matchmake.return_value = fake_resources
    globus_job_submit.return_value = u"<epr/>"
    thread = mock.Mock()
    spawn.return_value = thread
    generate_rsl.return_value = fake_rsl
    
    operations.loop()
    jobs.loop()
    tasks.loop()
    tasks.start(task)

    assert task.state.s == u"running"

    environ = { 'REQUEST_METHOD': 'POST',
                'PATH_INFO': '/%s/' % task.submission_uuid,
                'wsgi.input': StringIO(pickle.dumps(globus.State.from_string(fake_state_xml(u"failed"))))
                }
    response = [None]
    def start_response(status, headers):
        response[0] = (status, headers)

    result = ''.join(list(tasks.wsgi_wsn_notification(environ, start_response)))
    assert response[0][0].startswith('204 '), response[0][0]
    assert task.state.s == u"aborted"
