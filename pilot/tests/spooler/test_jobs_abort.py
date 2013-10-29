# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session

from pilot.spooler import jobs, operations, queues, tasks, globus
from nose.plugins.attrib import attr

import mock, pdb

fake_resources = [("tb01.ngrid.ru", "test", "pbs")]

def test_job_simple_abort():
    job = empty_db_and_create_job()
    task = job.tasks[0]

    operations.loop()
    jobs.loop()

    assert task.runnable

    reason = u"test abort"
    jobs.abort(job, reason)
    jobs.loop()

    assert job.state.s == u"aborted"
    assert job.state.info == reason
    assert last_log().event == u"job_aborted"
    assert not task.runnable


@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.globus.job_kill")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_job_abort_running_tasks(generate_rsl, globus_job_kill, globus_job_submit, matchmake, spawn):
    job = empty_db_and_create_ab_job()
    task_a = job.tasks[0]
    task_b = job.tasks[1]

    generate_rsl.return_value = fake_rsl

    matchmake.return_value = fake_resources
    globus_job_submit.return_value = u"<epr/>"
    thread = mock.Mock()
    spawn.return_value = thread
    
    operations.loop()
    jobs.loop()
    tasks.loop()
    tasks.start(task_a)

    assert task_a.state.s == u"running"
    assert task_b.state.s == u"new"
    assert job.state.s == u"running"

    jobs.abort(job, u"must terminate")
    assert task_a.state.s == u"aborted", task_a
    assert task_b.state.s == u"new"
    assert job.state.s == u"aborted"


@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.globus.job_kill")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_job_abort_running_starting_tasks(generate_rsl, globus_job_kill, globus_job_submit, matchmake, spawn):
    job = empty_db_and_create_diamond_job()
    task_a = job.tasks[0]
    task_b1 = job.tasks[1]
    task_c = job.tasks[3]

    matchmake.return_value = fake_resources
    globus_job_submit.return_value = u"<epr/>"
    thread = mock.Mock()
    spawn.return_value = thread

    generate_rsl.return_value = fake_rsl
    
    operations.loop()
    jobs.loop()
    tasks.loop()
    tasks.start(task_a)
    tasks.finish(task_a, 0)

    jobs.loop()

    assert job.state.s == u"running"
    assert task_b1.runnable
    assert task_c.runnable

    tasks.loop()
    tasks.start(task_b1)
    assert task_b1.state.s == u"running"
    assert task_c.state.s == u"starting"
    assert job.state.s == u"running"

    jobs.abort(job, u"must terminate")
    assert task_b1.state.s == u"aborted"
    assert task_c.state.s == u"aborted", task_c
    assert job.state.s == u"aborted"

    assert thread.kill.call_count == 1

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.globus.job_kill")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_job_abort_running_starting_tasks_with_exception(generate_rsl, globus_job_kill, globus_job_submit, matchmake, spawn):
    job = empty_db_and_create_diamond_job()
    task_a = job.tasks[0]
    task_b1 = job.tasks[1]
    task_c = job.tasks[3]

    matchmake.return_value = fake_resources
    globus_job_submit.return_value = u"<epr/>"
    thread = mock.Mock()
    spawn.return_value = thread
    thread.kill.side_effect = RuntimeError("blargh!")

    generate_rsl.return_value = fake_rsl
    
    operations.loop()
    jobs.loop()
    tasks.loop()
    tasks.start(task_a)
    tasks.finish(task_a, 0)

    jobs.loop()

    assert job.state.s == u"running"
    assert task_b1.runnable
    assert task_c.runnable

    tasks.loop()
    tasks.start(task_b1)
    assert task_b1.state.s == u"running"
    assert task_c.state.s == u"starting"
    assert job.state.s == u"running"

    jobs.abort(job, u"must terminate")
    assert task_b1.state.s == u"aborted"
    assert task_c.state.s == u"aborted", task_c
    assert job.state.s == u"aborted"

    assert thread.kill.call_count == 1
