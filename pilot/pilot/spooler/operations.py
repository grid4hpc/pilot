# -*- encoding: utf-8 -*-

import datetime
import eventlet
import logging

from pilot import model
from pilot.spooler import config
from pilot.model.meta import Session

from loops import forever
import queues


log = logging.getLogger(__name__)
heartbeat = logging.getLogger(u"heartbeat." + __name__)

@forever
def loop():
    """
    Основной цикл обработки операций
    """
    heartbeat.debug("start")
    pending_operations = Session.query(model.JobOperation) \
                         .filter_by(completed=None) \
                         .order_by(model.JobOperation.created.desc())
    seen_jobs = set()
    for operation in pending_operations:
        job = operation.job
        log.debug("%s: processing operation %s", job.logname(), operation.op)
        operation.completed = datetime.datetime.utcnow()
        operation.success = True
        st = None
        old_state = operation.job.state.s
        if operation.job_id in seen_jobs:
            # Все операции упорядочены по времени в обратном
            # порядке. Для каждой задачи выполняется только последняя
            # по времени операция.
            operation.success = False
            log_abort(operation, u"new pending operations present")
        else:
            seen_jobs.add(operation.job_id)
            if operation.op == u"start":
                st = try_start(operation)
            elif operation.op == u"pause":
                st = try_pause(operation)
            elif operation.op == u"abort":
                st = try_abort(operation)
            else:
                operation.success = False
                log_abort(operation, u"unknown operation")

        if st is not None:
            Session.add(st)
        Session.add(operation)
        Session.flush()
        if job.state.s != old_state:
            log.debug(u"%s: changed state to %s", job.logname(), job.state.s)
            
    heartbeat.debug("end")

    try:
        queues.operation.get(True, config["operation_loop"])
        while not queues.operation.empty():
            queues.operation.get()
    except eventlet.queue.Empty:
        pass


def trigger(environ, start_response):    
    method = environ.get('REQUEST_METHOD', '')
    if method != 'POST':
        start_response('405 Method Not Allowed', [('Content-type', 'text/plain')])
        return '405 Method Not Allowed\n'

    log.debug("got operation trigger notification")
    queues.operation.put(None)
    start_response('204 No Content', [])
    return ''

def log_abort(operation, reason):
    log.debug(u"%s: aborted operation %s: %s",
              operation.job.logname(), operation.op, reason)


def try_start(operation):
    """
    Отправить задачу из операции на запуск, если это возможно
    """
    job_state = operation.job.state.s
    if job_state in (u"new", u"paused"):
        st = operation.job.add_state(u"starting")
        queues.run.put(operation.job)
        return st

    operation.success = False
    log_abort(operation, u"job cannot be started from state %s" % job_state)
    return None


def try_pause(operation):
    """
    Отправить задачу из операции на остановку, если это возможно
    """
    job_state = operation.job.state.s
    if job_state in (u"running",):
        st = operation.job.add_state(u"pausing")
        queues.pause.put(operation.job)
        return st

    operation.success = False
    log_abort(operation, u"job cannot be paused from state %s" % job_state)
    return None


def try_abort(operation):
    """
    Отправить задачу из операции на отмену выполнения, если это возможно
    """
    job_state = operation.job.state.s
    if job_state in (u"running", u"paused"):
        st = operation.job.add_state(u"aborting")
        queues.abort.put(operation.job)
        return st

    operation.success = False
    log_abort(operation, u"job cannot be aborted from state %s" % job_state)
    return None
