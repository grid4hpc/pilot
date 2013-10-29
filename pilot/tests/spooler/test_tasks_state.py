# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr

from pilot.spooler import jobs, operations, tasks, globus

import mock, pdb

fake_resources = [("tb01.ngrid.ru", "test", "pbs")]

def fake_state_xml(state, exit_code=0):
    return """
    <globus xmlns:js="http://www.globus.org/namespaces/2008/03/gram/job/types"
            xmlns:bf2="http://docs.oasis-open.org/wsrf/bf-2">
      <js:state>%(state)s</js:state>
      <js:exitCode>%(exit_code)d</js:exitCode>
      <bf2:Description>Fault description</bf2:Description>
    </globus>
    """ % dict(state=state, exit_code=exit_code)

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_update_state_failstate(generate_rsl, globus_job_submit, matchmake, spawn):
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

    new_state = globus.State.from_string(fake_state_xml("failed"))
    tasks.update_state(task, new_state)
    assert task.state.s == u"aborted"

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_update_state_failstate2(generate_rsl, globus_job_submit, matchmake, spawn):
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

    new_state = globus.State.from_string(fake_state_xml("userterminatedone"))
    tasks.update_state(task, new_state)
    assert task.state.s == u"aborted"
    new_state = globus.State.from_string(fake_state_xml("failed"))
    tasks.update_state(task, new_state)
    assert state_count(task, u"aborted") == 1

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_update_state_finished(generate_rsl, globus_job_submit, matchmake, spawn):
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

    new_state = globus.State.from_string(fake_state_xml("done", 42))
    tasks.update_state(task, new_state)
    assert task.state.s == u"finished"
    assert task.exit_code == 42

    tasks.update_state(task, new_state)
    assert task.state.s == u"finished"
    assert state_count(task, u"finished") == 1
    assert last_log().event == u"task_finished"

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_update_state_flips(generate_rsl, globus_job_submit, matchmake, spawn):
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

    new_state = globus.State.from_string(fake_state_xml("done", 42))
    tasks.update_state(task, new_state)
    assert task.state.s == u"finished"
    assert task.exit_code == 42

    new_state = globus.State.from_string(fake_state_xml("failed"))
    tasks.update_state(task, new_state)
    assert task.state.s == u"finished"
    assert state_count(task, u"finished") == 1
    assert state_count(task, u"aborted") == 0

@mock.patch("eventlet.spawn")
@mock.patch("pilot.spooler.tasks.matchmake")
@mock.patch("pilot.spooler.globus.job_submit")
@mock.patch("pilot.spooler.matchmaker.generate_rsl")
def test_task_update_state_flips2(generate_rsl, globus_job_submit, matchmake, spawn):
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

    new_state = globus.State.from_string(fake_state_xml("failed"))
    tasks.update_state(task, new_state)
    assert task.state.s == u"aborted"

    new_state = globus.State.from_string(fake_state_xml("done", 42))
    tasks.update_state(task, new_state)
    assert task.state.s == u"aborted"
    assert state_count(task, u"finished") == 0
    assert state_count(task, u"aborted") == 1
