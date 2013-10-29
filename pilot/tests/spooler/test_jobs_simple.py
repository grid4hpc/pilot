# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session

from pilot.spooler import jobs, operations, queues

def test_job_simple():
    job = empty_db_and_create_job()
    task = job.tasks[0]
    assert task.runnable == False
    assert job.state.s == u"new"
    operations.loop()
    assert job.state.s == u"starting"

    jobs.loop()
    assert job.state.s == u"running"
    assert task.runnable == True
    assert last_log().event == u"job_started"

    jobs.loop()
    assert job.state.s == u"running"

    task.runnable = False
    task.add_state(u"running")
    jobs.loop()
    assert job.state.s == u"running"

    task.runnable = False
    task.add_state(u"finished")
    jobs.loop()
    assert job.state.s == u"finished"
    assert last_log().event == u"job_finished"

def test_job_simple_aborted():
    job = empty_db_and_create_job()
    task = job.tasks[0]
    operations.loop()
    jobs.loop()

    task.runnable = False
    task.add_state(u"aborted")
    jobs.loop()
    assert job.state.s == u"aborted"
    assert u"0 tasks" in job.state.info
    assert last_log().event == u"job_aborted"

def test_job_ab_success():
    job = empty_db_and_create_ab_job()
    assert len(job.tasks) == 2
    task_a = job.tasks[0]
    task_b = job.tasks[1]
    
    assert task_a.runnable == False
    assert task_b.runnable == False
    operations.loop()
    jobs.loop()
    assert job.state.s == u"running"
    assert last_log().event == u"job_started"
    assert task_a.runnable == True
    assert task_b.runnable == False

    task_a.runnable = False
    task_a.add_state(u"finished")
    jobs.loop()
    assert job.state.s == u"running"
    assert task_a.runnable == False
    assert task_b.runnable == True

    task_b.runnable = False
    task_b.add_state(u"finished")
    jobs.loop()
    assert job.state.s == u"finished"
    assert last_log().event == u"job_finished"

def test_job_ab_fail():
    job = empty_db_and_create_ab_job()
    task_a = job.tasks[0]
    task_b = job.tasks[1]
    
    operations.loop()
    jobs.loop()

    task_a.runnable = False
    task_a.add_state(u"aborted")
    jobs.loop()
    assert job.state.s == u"aborted"
    assert u"0 tasks" in job.state.info
    assert last_log().event == u"job_aborted"

def test_job_ab_partial():
    job = empty_db_and_create_ab_job()
    task_a = job.tasks[0]
    task_b = job.tasks[1]
    
    operations.loop()
    jobs.loop()

    task_a.runnable = False
    task_a.add_state(u"finished")
    jobs.loop()
    
    task_b.runnable = False
    task_b.add_state(u"aborted")
    jobs.loop()
    assert job.state.s == u"partial"
    assert u"1 of 2 tasks" in job.state.info
    assert last_log().event == u"job_aborted"

def test_job_diamond_success():
    def complete_runnable_tasks(job):
        for task in job.tasks:
            if task.runnable:
                task.runnable = False
                st = task.add_state(u"finished")
                task.exit_code = 0
                
    job = empty_db_and_create_diamond_job()
    assert len(job.tasks) == 5
    
    operations.loop()
    jobs.loop()

    complete_runnable_tasks(job)
    jobs.loop()
    Session.refresh(job)
    assert job.state.s == u"running"

    complete_runnable_tasks(job)
    jobs.loop()
    Session.refresh(job)
    assert job.state.s == u"running"

    complete_runnable_tasks(job)
    jobs.loop()
    Session.refresh(job)
    assert job.state.s == u"running"

    complete_runnable_tasks(job)
    jobs.loop()
    assert job.state.s == u"finished"
    assert last_log().event == u"job_finished"
    
def test_job_diamond_partial():
    def complete_runnable_tasks(job):
        for task in job.tasks:
            if task.runnable:
                task.runnable = False
                st = task.add_state(u"finished")
                task.exit_code = 0
                
    job = empty_db_and_create_diamond_job()
    
    operations.loop()
    jobs.loop()

    complete_runnable_tasks(job)
    jobs.loop()
    Session.refresh(job)
    assert job.state.s == u"running"

    complete_runnable_tasks(job)
    job.tasks[3].add_state(u"aborted")
    jobs.loop()
    Session.refresh(job)
    assert job.state.s == u"running"

    complete_runnable_tasks(job)
    jobs.loop()
    assert job.state.s == u"partial"
    assert u"3 of 5 tasks" in job.state.info
    assert last_log().event == u"job_aborted"
