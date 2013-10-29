# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr

from pilot.spooler import jobs, operations, queues, tasks, config

import mock, pdb

def reset():
    tasks.starters = {}
    config["task_starters"] = 100

@mock.patch('eventlet.spawn')
def test_task_loop_simple(spawn):
    reset()
    empty_db()
    job = create_job()
    task = job.tasks[0]

    operations.loop()
    jobs.loop()

    spawn.return_value = 42

    assert task.runnable
    assert task.state.s == u"new"
    assert not spawn.called
    assert len(tasks.starters) == 0
    tasks.loop()
    assert spawn.called
    assert spawn.call_count == 1
    args = spawn.call_args[0]
    assert args[0] == tasks.start
    assert args[1] == task
    assert not task.runnable
    assert task.id in tasks.starters
    assert tasks.starters[task.id] == spawn.return_value
    assert task.state.s == u"starting"

    N = 3
    test_jobs = [create_job() for i in xrange(0, N)]
    test_tasks = [job.tasks[0] for job in test_jobs]
    operations.loop()
    jobs.loop()

    tasks.loop()
    assert spawn.call_count == N+1, spawn.call_count
    assert len(tasks.starters) == N+1
    found = list(test_tasks)
    for args, kwargs in spawn.call_args_list[1:]:
        assert args[1] in found        
        found.pop(found.index(args[1]))
    assert len(found) == 0

@mock.patch('eventlet.spawn')
def test_task_loop_overflow(spawn):
    N = 3
    reset()
    empty_db()
    config["task_starters"] = N-1
    test_jobs = [create_job() for i in xrange(0, N)]
    test_tasks = [job.tasks[0] for job in test_jobs]
    operations.loop()
    jobs.loop()

    def runnable_count(test_tasks):
        return len([task for task in test_tasks if task.runnable])

    assert runnable_count(test_tasks) == N, runnable_count(test_tasks)

    spawn.return_value = 42

    tasks.loop()
    assert spawn.call_count == N-1, spawn.call_count
    assert runnable_count(test_tasks) == 1
    tasks.starters.popitem()
    tasks.loop()
    assert spawn.call_count == N, spawn.call_count
    assert runnable_count(test_tasks) == 0

@mock.patch('eventlet.spawn')
def test_task_reset(spawn):
    reset()
    empty_db()
    job = create_job()
    task = job.tasks[0]
    
    operations.loop()
    jobs.loop()
    tasks.loop()
    assert task.state.s == u"starting"
    assert not task.runnable

    reset()
    tasks.reset_tasks()
    assert task.runnable
    assert task.state.s == u"pending"

    tasks.loop()
    assert not task.runnable
    assert task.state.s == u"starting"
