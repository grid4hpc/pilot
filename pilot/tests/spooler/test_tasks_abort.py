# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr

from pilot.spooler import jobs, operations, queues, tasks, config, globus

import mock, pdb

fake_resources = [("tb01.ngrid.ru", "test", "pbs")]

@mock.patch("eventlet.spawn")
def test_task_abort_during_start_nokill(spawn):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    thread = mock.Mock()
    spawn.return_value = thread

    operations.loop()
    jobs.loop()
    tasks.loop()

    assert task.id in tasks.starters
    tasks.abort(task, u"test", dont_kill=True)
    assert thread.kill.call_count == 0
    assert last_log().event == u"task_aborted"
    Session.refresh(task)
    assert state_count(task, u"aborted") == 1

@mock.patch("eventlet.spawn")
def test_task_abort_during_start(spawn):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    thread = mock.Mock()
    spawn.return_value = thread

    operations.loop()
    jobs.loop()
    tasks.loop()

    assert task.id in tasks.starters
    tasks.abort(task, u"test")
    assert thread.kill.call_count == 1
    assert state_count(task, u"aborted") == 1

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.globus.job_kill")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_abort_running(generate_rsl, globus_job_kill, globus_job_submit, matchmake, spawn):
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
    tasks.abort(task, u"test")
    assert globus_job_kill.call_count > 0
    assert state_count(task, u"aborted") == 1

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_kill")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.tasks.log")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_abort_running_kill_fails_generic(generate_rsl, log, globus_job_submit, globus_job_kill, matchmake, spawn):
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
    globus_job_kill.side_effect = RuntimeError("blargh!")
    tasks.abort(task, u"test")
    last_log_call = log.critical.call_args_list[-1]
    assert "unexptected exception during globus.job_kill" in last_log_call[0][0]
    assert state_count(task, u"aborted") == 1

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.tasks.log")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_abort_running_kill_fails(generate_rsl, log, globus_job_submit, matchmake, spawn):
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
    tasks.abort(task, u"test")
    last_log_call = log.warn.call_args_list[-1]
    assert "error killing globus job" in last_log_call[0][0]
    assert state_count(task, u"aborted") == 1
    
@mock.patch("eventlet.spawn")
def test_task_abort_not_twice(spawn):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    thread = mock.Mock()
    spawn.return_value = thread

    operations.loop()
    jobs.loop()
    tasks.loop()

    assert task.id in tasks.starters
    tasks.abort(task, u"test")
    tasks.abort(task, u"test")
    assert state_count(task, u"aborted") == 1
