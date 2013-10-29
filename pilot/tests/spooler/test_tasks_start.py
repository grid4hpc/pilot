# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr

from pilot.spooler import jobs, operations, queues, tasks, config, globus

import mock, pdb

fake_resources = [("tb01.ngrid.ru", "test", "pbs")]
    
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_start(generate_rsl, globus_job_submit, matchmake):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    matchmake.return_value = fake_resources
    globus_job_submit.return_value = "<epr/>"
    generate_rsl.return_value = fake_rsl
    
    task.add_state(u"starting")
    tasks.start(task)

    assert task.id not in tasks.starters
    assert globus_job_submit.call_count == 1
    assert matchmake.call_count == 1
    assert last_log().event == u"task_started"
    assert last_log().info["hostname"] == fake_resources[0][0]
    assert task.state.s == u"running"
    assert str(task.native_id) == str(globus_job_submit.return_value)
    assert task.native_type == u"globus-epr"
    assert last_log().task_id == job.tasks[0].name

@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
def test_task_start_no_resources(globus_job_submit, matchmake):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    matchmake.return_value = []
    globus_job_submit.return_value = u"<epr/>"
    
    task.add_state(u"starting")
    tasks.start(task)

    assert task.id not in tasks.starters
    assert globus_job_submit.call_count == 0
    assert matchmake.call_count == 1
    assert last_log().event == u"task_aborted"
    assert task.state.s == u"aborted"
    assert "No compatible resources" in task.state.info


@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_start_failing_globus(generate_rsl, globus_job_submit, matchmake):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    matchmake.return_value = fake_resources
    globus_job_submit.return_value = u"<epr/>"
    globus_job_submit.side_effect = globus.TimeoutError()
    generate_rsl.return_value = fake_rsl
    
    task.add_state(u"starting")
    tasks.start(task)

    assert task.id not in tasks.starters
    assert globus_job_submit.call_count > 1
    assert last_log().event == u"task_aborted"
    assert task.state.s == u"aborted"
    assert "all compatible resources" in task.state.info
    assert last_log().task_id == job.tasks[0].name

@mock.patch("pilot.spooler.tasks.matchmake")
def test_task_start_bad_proxy(matchmake):
    empty_db()
    job = create_job(proxy=test_user_bad_proxy)
    task = job.tasks[0]

    matchmake.return_value = fake_resources
    
    task.add_state(u"starting")
    tasks.start(task)

    assert task.id not in tasks.starters
    assert last_log().event == u"task_aborted"
    assert task.state.s == u"aborted"
    assert ("Error loading VOMS attributes" in task.state.info) or \
           ("task submission failed:" in task.state.info)


@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_start_failing_RSL(generate_rsl, matchmake):
    empty_db()
    job = create_job()
    task = job.tasks[0]

    matchmake.return_value = fake_resources
    generate_rsl.side_effect = ValueError("blargh!")
    
    task.add_state(u"starting")
    tasks.start(task)

    assert task.id not in tasks.starters
    assert last_log().event == u"task_aborted"
    assert task.state.s == u"aborted"
    assert "cannot build rsl" in task.state.info

