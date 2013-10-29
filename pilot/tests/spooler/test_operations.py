# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session

from pilot.spooler import jobs, operations, queues

def test_operations_start():
    job = empty_db_and_create_job()
    assert job.state.s == u"new"
    assert job.operations[0].completed is None
    operations.loop()
    assert job.operations[0].completed is not None

def test_operations_fail_start_from_running():
    job = empty_db_and_create_job()
    job.state.s = u"running"
    Session.flush()
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[0].success == False

def test_operations_fail_other():
    job = empty_db_and_create_job()
    job.operations.append(model.JobOperation(u'start', u'2'))
    assert job.state.s == u"new"
    assert job.operations[0].completed is None
    assert job.operations[1].completed is None
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[1].completed is not None
    assert job.operations[0].success == False
    assert job.operations[1].success == True   

def test_operations_fail_pause_from_new():
    job = empty_db_and_create_job()
    job.operations[0].op = u"pause"
    Session.flush()
    assert job.state.s == u"new"
    assert job.operations[0].completed is None
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[0].success == False

def test_operations_pause_from_running():
    job = empty_db_and_create_job()
    job.state.s = u"running"
    job.operations[0].op = u"pause"
    Session.flush()
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[0].success == True

def test_operations_abort_from_running():
    job = empty_db_and_create_job()
    job.state.s = u"running"
    job.operations[0].op = u"abort"
    Session.flush()
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[0].success == True

def test_operations_fail_abort_from_new():
    job = empty_db_and_create_job()
    job.operations[0].op = u"abort"
    Session.flush()
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[0].success == False

def test_operations_fail_unknown():
    job = empty_db_and_create_job()
    job.operations[0].op = u"blargh"
    Session.flush()
    operations.loop()
    assert job.operations[0].completed is not None
    assert job.operations[0].success == False

def test_operations_trigger():
    environ = { 'REQUEST_METHOD': 'GET' }
    response = [None]
    def start_response(status, headers):
        response[0] = (status, headers)

    result = ''.join(list(operations.trigger(environ, start_response)))
    assert result.startswith('405 ')
    assert response[0][0].startswith('405 ')

    environ['REQUEST_METHOD'] = 'POST'
    assert queues.operation.qsize() == 0
    result = ''.join(list(operations.trigger(environ, start_response)))
    assert queues.operation.qsize() == 1
    assert response[0][0].startswith('204 ')

    operations.loop()
    assert queues.operation.qsize() == 0
    operations.trigger(environ, start_response)
    operations.trigger(environ, start_response)
    operations.trigger(environ, start_response)
    assert queues.operation.qsize() == 3
    operations.loop()
    assert queues.operation.qsize() == 0    
