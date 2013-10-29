# -*- encoding: utf-8 -*-

import copy
import datetime
import eventlet
import logging
import pickle
import random

from M2Crypto import X509, BIO
import uuid

from pilot import model
from pilot.api import *
from pilot.model import tools as model_tools
from pilot.model.meta import Session
from pilot.spooler import config, wsgi, grid
from pilot.lib.resources import find_resources, generate_rsl, TimeoutResourcesError, ResourcesError, resource_name

from pilot.spooler.realm.gws import GT4TaskState

from loops import forever
import queues


log = logging.getLogger(__name__)
heartbeat = logging.getLogger(u"heartbeat." + __name__)


def reset_tasks():
    """
    Установить флаг runnable на задачах, которые в базе данных имеют
    состояние starting.

    Вызывается один раз при старте spooler.
    """
    starting_tasks = Session.query(model.Task).join(model.Task.state) \
                     .filter(model.TaskState.s == u"starting")
    for task in starting_tasks:
        log.info("%s: resetting from starting state" % task.logname())
        st = task.add_state(u"pending")
        Session.add(st)
        task.runnable = True
    Session.flush()


def terminal_state(task):
    if task.state and task.state.s in (u"finished", u"aborted"):
        return True
    else:
        return False


starters = {}


def start(task):
    """
    Запустить задачу.
    """
    def do_start(task):
        log.debug(u"%s: matchmaking", task.logname())
        try:
            matches = find_resources(task)
        except TimeoutResourcesError, exc:
            log.debug(u"%s: timeout during matchmake, will retry start later", task.logname())
            task.runnable = True
            Session.add(task.add_state(u"new"))
            return False
        except ResourcesError, exc:
            abort(task, unicode(exc), dont_kill=True)
            return False

        log.debug(u"%s: matching resources: %s", task.logname(),
                  u", ".join(resource_name(*rhplq) for rhplq in matches))

        epr = None

        for target in matches*3:
            log.debug(u"%s: trying to submit to %s", task.logname(),
                      resource_name(*target))        
            try:
                params = generate_rsl(task, target)
            except ResourcesError, exc:
                abort(task, u"cannot generate submission parameters: %s" % exc,
                      dont_kill=True)
                return False

            if hasattr(params, 'id'):
                task.submission_uuid = params.id
            else:
                task.submission_uuid = str(uuid.uuid4())
            log.debug(u"%s: %s", task.logname(), str(params))

            try:
                task.native_id = grid.executor(target[0]).submit(params, task.job.proxy)
                task.native_type = unicode(target[0])
                break
            except FatalTaskExecutorError, exc:
                task.native_id = None
                task.native_type = None
                abort(task, u"task submission failed: %s" % exc, dont_kill=True)
                return False
            except NonFatalTaskExecutorError, exc:
                task.native_id = None
                task.native_type = None
                msg = u"submission to %s has failed: %s" % \
                      (resource_name(*target), exc)
                log.debug("%s: %s", task.logname(), msg)
                st = task.add_state(u"starting")
                st.info = msg
                Session.add(st)

        if task.native_id is None:
            abort(task, u"submission to all compatible resources have failed.",
                  dont_kill=True)
            return False

        st = task.add_state(u"running")
        st.info = "%s:%s" % (resource_name(*target), task.submission_uuid)
        Session.add(st)

        task.meta['running_at'] = target

        log_entry = model.AccountingLog(ts = datetime.datetime.utcnow(),
                                        dn = task.job.owner,
                                        job_id = task.job.jid,
                                        task_id = task.name,
                                        event = u"task_started",
                                        vo = task.job.vo,
                                        info = dict(submission_id = task.submission_uuid,
                                                    hostname = target[1],
                                                    lrms_type = target[3],
                                                    queue = target[4]))
        Session.add(log_entry)
        log.info("%s: task started", task.logname())
        return True
        
    try:
        if do_start(task):
            queues.task_poll.put(task.id)
    finally:
        if task.id in starters:
            starters.pop(task.id)
        Session.flush()

@forever
def loop():
    """
    Основной цикл обработки задач.
    """
    runnable_tasks = Session.query(model.Task).filter_by(runnable=True)
    for task in runnable_tasks:
        if len(starters) >= config["task_starters"]:
            break
        
        task.runnable = False
        Session.add(task.add_state(u"starting"))
        starters[task.id] = eventlet.spawn(start, task)
    Session.flush()    

    try:
        queues.task.get(True, 1)
        while not queues.task.empty():
            queues.task.get()
    except eventlet.queue.Empty:
        pass


def wsgi_wsn_notification(environ, start_response):
    """
    Обработка WS-Notification
    """
    path = environ.get('PATH_INFO', '').strip('/').split('/')
    method = environ.get('REQUEST_METHOD', '')
    if method != 'POST':
        start_response('405 Method Not Allowed', [('Content-type', 'text/plain')])
        return '405 Method Not Allowed\n'

    if len(path) != 1 or path[0] == '':
        raise wsgi.Error404

    submission_uuid = unicode(path[0])
    try:
        gstate = pickle.load(environ['wsgi.input'])
    except (EOFError, IOError), exc:
        raise wsgi.HttpError(400, 'Could not load state information: %s' % str(exc))
    log.debug("WS-N: %s: %s", submission_uuid, gstate)
    task = Session.query(model.Task).filter_by(submission_uuid=submission_uuid).first()
    if task is None:
        log.debug("WS-N: %s is not present in the database", submission_uuid)
        raise wsgi.Error404

    update_state(task, GT4TaskState.from_gstate(gstate))

    start_response('204 No Content', [])
    return ''


def update_state(task, state):
    """
    Обновить информацию о состоянии задачи task
    """
    # TODO: записать время последнего обновления информации
    if state.state == "aborted":
        abort(task, unicode(state.reason))
    elif state.state == "finished":
        finish(task, state.exit_code)


def abort(task, cause, dont_kill=False, dont_flush=False):
    """
    Оборвать выполнение задачи. При необходимости убить поток, запускающий задачу.
    Если задача была запущена на ресурс, убить ее.
    """
    if terminal_state(task):
        log.info(u"%s: abort: task is already %s.", task.logname(), task.state.s)
        return
    
    log.info(u"%s: aborted: %s", task.logname(), cause)
    if task.id in starters:
        thread = starters.pop(task.id)
        if not dont_kill:
            thread.kill()

    if task.state is not None and task.state.s == u"running":
        try:
            realm = task.native_type
            grid.executor(realm).kill(str(task.native_id), task.job.proxy)
        except TaskExecutorError, exc:
            log.warn(u"%s: error killing '%s' task, "
                     u"continuing abort without task kill: %s",
                     task.logname(), realm, str(exc))
        except grid.RealmNotFoundError, exc:
            log.error(u"%s: can't kill task, "
                      u"continuing abort without task kill: %s",
                      task.logname(), str(exc))
        except Exception, exc:
            log.critical(u"%s: exception in ITaskExecutor.kill: %s",
                         task.logname(), str(exc))

    task.runnable = False
    st = task.add_state(u"aborted")
    st.info = cause
    Session.add(st)

    log_entry = model.AccountingLog(ts = datetime.datetime.utcnow(),
                                    dn = task.job.owner,
                                    job_id = task.job.jid,
                                    task_id = task.name,
                                    event = u"task_aborted",
                                    vo = task.job.vo,
                                    detail = cause)
    Session.add(log_entry)
    if not dont_flush:
        Session.flush()

    queues.run.put(task.job)


def finish(task, exit_code):
    if terminal_state(task):
        log.info(u"%s: finish: task is already %s.", task.logname(), task.state.s)
        return
    log.info(u"%s: finished with exit code %d", task.logname(), exit_code)
    task.exit_code = exit_code
    st = task.add_state(u"finished")
    st.info = u"%d" % exit_code
    Session.add(st)
    Session.add(task)
    log_entry = model.AccountingLog(ts = datetime.datetime.utcnow(),
                                    dn = task.job.owner,
                                    job_id = task.job.jid,
                                    task_id = task.name,
                                    event = u"task_finished",
                                    vo = task.job.vo,
                                    detail = u"%d" % exit_code)
    Session.add(log_entry)
    Session.flush()

    queues.run.put(task.job)
