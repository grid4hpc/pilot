# -*- encoding: utf-8 -*-

import eventlet
import logging
from operator import itemgetter
import sqlalchemy as sa
import time

from pilot import model
from pilot.api import *
from pilot.model.meta import Session
from pilot.spooler import config, exec_pool, grid

from loops import forever
import queues
import tasks

log = logging.getLogger(__name__)
heartbeat = logging.getLogger(u"heartbeat." + __name__)


running = {}


@forever
def loop():
    """
    Основной цикл опроса состояния
    """
    if len(running) == 0:
        sleep()
        return
    
    time_sorted = sorted(running.iteritems(), key=itemgetter(1))
    now = time.time()
    oldest = time_sorted[0]
    delta = now - oldest[1]
    if delta > config.wsn_poll_period:
        running.pop(oldest[0])
        poll_task(oldest[0])
    else:
        sleep(config.wsn_poll_period - delta)
        return

    timeout = 86400
    if len(time_sorted) > 1:
        next_oldest = time_sorted[1]
        delta = now - next_oldest[1]
        timeout = max(0, config.wsn_poll_period - delta)
    sleep(1)
    

def sleep(timeout=1):
    """
    Ничего не делать в течение какого-то времени, или пока нас не дернут.
    """
    try:
        task_id = queues.task_poll.get(True, timeout)
        now = time.time()
        running[task_id] = now
        while not queues.task_poll.empty():
            running[queues.task_poll.get()] = now
    except eventlet.queue.Empty:
        pass


def poll_task(task_id):
    log.debug(u"task_%d: polling status", task_id)
    task = Session.query(model.Task).filter_by(id=task_id).first()
    
    if task is None:
        log.debug(u"task_%d: not found in database", task_id)
        return
    
    if task.state.s != u"running":
        log.debug(u"%s (task_%d): already in %s state", task.logname(),
                  task_id, task.state.s)
        return

    try:
        realm = task.native_type
        state = exec_pool.spawn(grid.executor(realm).status,
                                str(task.native_id), task.job.proxy).wait()
        tasks.update_state(task, state)
        running[task_id] = time.time()        
    except TimeoutTaskExecutorError, exc:
        log.warn(u"%s: TimeoutTaskExecutorError while checking task state: %s",
                 task.logname(), str(exc))
    except TaskExecutorError, exc:
        log.warn(u"%s: aborting due to TaskExecutorError: %s", task.logname(),
                 str(exc))
        tasks.abort(task, u"TaskExecutorError while checking task state: %s" % \
                    str(exc))
    except grid.RealmNotFoundError, exc:
        log.warn(u"%s: RealmNotFoundError: %s", task.logname, str(exc))
        tasks.abort(task, u"RealmNotFoundError: %s" % str(exc))
    
def refresh():
    """
    Обновить набор запущенных задач из базы данных
    """
    now = time.time()
    tasks = Session.query(model.Task) \
            .join((model.TaskState, model.Task.state_id == model.TaskState.id), model.Task.job) \
            .filter(sa.and_(model.TaskState.s == u"running", model.Job.deleted == False))
    running.clear()
    for task in tasks:
        running[task.id] = now
    log.debug("refresh: running tasks: %d", len(running))
