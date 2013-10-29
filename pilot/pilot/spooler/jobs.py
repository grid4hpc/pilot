# -*- encoding: utf-8 -*-

import datetime
import eventlet
import logging
import pytz

import sqlalchemy as sa

from pilot import model
from pilot.model import tools as model_tools
from pilot.spooler import config, wsgi
from pilot.model.meta import Session

from loops import forever
import queues
import tasks

log = logging.getLogger(__name__)
heartbeat = logging.getLogger(u"heartbeat." + __name__)

terminal_states = [u"finished", u"partial", u"aborted"]

@forever
def loop():
    """
    Основной цикл обработки заданий
    """
    heartbeat.debug("start")
    process_starting_jobs()
    process_running_jobs()
    heartbeat.debug("end")

    try:
        queues.run.get(True, config["jobs_loop"])
        while not queues.run.empty():
            queues.run.get()
    except eventlet.queue.Empty:
        pass


def process_starting_jobs():
    """
    Перевести все задачи из состояния starting в состояние running,
    оставив запись в AccountingLog и записав в базе данных связи между
    задачами задания.
    """
    pending_starts = Session.query(model.Job).filter_by(deleted=False) \
                     .join((model.JobState, model.Job.state_id == model.JobState.id)) \
                     .filter(model.JobState.s == u"starting")
    for job in pending_starts:
        log.debug("%s: linking tasks", job.logname())
        model_tools.setup_task_links(job)
        st = job.add_state(u"running")
        Session.add(st)
        log_entry = model.AccountingLog(ts = datetime.datetime.utcnow(),
                                        dn = job.owner,
                                        job_id = job.jid,
                                        event = u"job_started",
                                        vo = job.vo)
        Session.add(log_entry)
        log.debug("%s: job_started", job.logname())
    Session.flush()    

def process_running_jobs():
    """
    Обработать все задания в состоянии running
    """
    #running_jobs = Session.query(model.Job).filter_by(deleted=False) \
    #               .join((model.JobState, model.Job.state_id == model.JobState.id)) \
    #               .filter(model.JobState.s == u"running")
    rp = Session.execute(sa.sql.select(
        [model.jobs_table.c.id],
        sa.sql.and_(model.jobstates_table.c.s==u"running",
                    model.jobs_table.c.dirty==True,
                    model.jobs_table.c.deleted==False),
        model.jobs_table.join(model.jobstates_table,
                              model.jobs_table.c.state_id==model.jobstates_table.c.id)))
    for (job_id,) in rp:
        process_job(job_id)

def process_job(job_id):
    """
    Обработать одно задание
    """

    job = Session.query(model.Job).filter_by(id=job_id).first()

    log.debug(u"%s: started processing", job.logname())
    # если у задания есть задачи, которые можно запустить,
    # отметить их как пригодные для запуска
    have_runnable_or_running_jobs = False
    finished_tasks = 0
    tasks_to_queue = []

    for task in job.tasks:
        task_state = task.state.s

        # новые задачи можно пытаться помечать, как пригодные для запуска
        if task_state == u"new":
            runnable = True
            for parent in task.parents:
                if parent.state.s != u"finished":
                    runnable = False
                    break
            if runnable:
                # если задача еще не была отмечена, как runnable, то
                # отправить ее в очередь задач, ожидающих обработки по
                # завершении обработки задания
                if not task.runnable:
                    tasks_to_queue.append(task)
                have_runnable_or_running_jobs = True
                task.runnable = True
                Session.add(task)
                log.debug("%s: marked as runnable", task.logname())

        elif task_state in (u"starting", u"running", u"pending") or task.runnable:
            have_runnable_or_running_jobs = True

        if task_state == u"finished":
            finished_tasks += 1
            
    # если нет выполняющихся, или пригодных для выполнения задач, то
    # задание надо завершать
    if not have_runnable_or_running_jobs:
        log_entry = model.AccountingLog(ts = datetime.datetime.utcnow(),
                                        dn = job.owner,
                                        job_id = job.jid,
                                        vo = job.vo)
        st = job.add_state(u"dummy")
        # завершенных задач нет вообще - значит, полный aborted
        if finished_tasks == 0:
            log_entry.event = u"job_aborted"
            st.s = u"aborted"
            st.info = u"0 tasks were finished"
        # завершились не все задачи
        elif finished_tasks != len(job.tasks):
            log_entry.event = u"job_aborted"
            st.s = u"partial"
            st.info = u"%d of %d tasks were finished" % (finished_tasks, len(job.tasks))
        # завершились все задачи
        else:
            log_entry.event = u"job_finished"
            st.s = u"finished"
            st.info = u"all tasks have completed successfully"

        log_entry.detail = st.info
        Session.add(st)
        Session.add(log_entry)
        log.debug(u"%s: %s - %s", job.logname(), st.s, st.info)

    job.dirty = False
    Session.flush()

    for task in tasks_to_queue:
        queues.task.put(task)
    log.debug(u"%s: finished processing", job.logname())


def abort(job, reason):
    """
    Сделать задаче abort.
    Если есть процессы, запускающие задачи задания, они будут убиты.
    Session.flush() не вызывается.
    """
    log_entry = model.AccountingLog(ts = datetime.datetime.utcnow(),
                                    dn = job.owner,
                                    job_id = job.jid,
                                    vo = job.vo,
                                    event = u"job_aborted")
    st = job.add_state(u"aborted")
    st.info = reason
    log_entry.detail = reason
    Session.add(st)
    Session.add(log_entry)

    for task in job.tasks:
        task.runnable = False
        # убить процессы, запускающие задачи, если такие существуют:
        if task.id in tasks.starters:
            tid = tasks.starters.pop(task.id)
            try:
                tid.kill()
            except Exception, exc:
                log.warn(u"exception during task starter kill: %s", unicode(exc))
        # убить выполняющиеся задачи, если задание абортится:
        if task.state.s != u"new":
            tasks.abort(task, u"parent job was aborted", dont_flush=True)

    Session.flush()
    log.debug(u"%s: %s - %s", job.logname(), st.s, st.info)


def wsgi_delete(environ, start_response):
    """
    Обработка удаления заданий
    """
    path = environ.get('PATH_INFO', '').strip('/').split('/')
    method = environ.get('REQUEST_METHOD', '')
    if method != 'DELETE':
        raise wsgi.HttpError(405)

    if len(path) != 1 or path[0] == '':
        raise wsgi.Error404()

    jid = unicode(path[0])
    job = Session.query(model.Job).filter(model.Job.jid == jid).first()
    if job is None:
        raise wsgi.Error404()

    job.deleted = True
    Session.add(job)

    if job.state.s not in ([u"new"] + terminal_states):
        abort(job, u"job was deleted")
        
    Session.flush()
    
    start_response('204 No Content', [])
    return ''


@forever
def garbage_collector():
    now = datetime.datetime.now(pytz.UTC)
    log.debug("started garbage collection cycle")
    for job in Session.query(model.Job).filter(model.Job.expires < now):
        log.debug("collected %s job %s (created %s, modified %s, expires %s)",
                  job.deleted and "deleted" or "not deleted",
                  job.jid,
                  job.created.strftime("%c"),
                  job.modified.strftime("%c"),
                  job.expires.strftime("%c"))
        Session.delete(job)
    Session.flush()
    eventlet.sleep()
    query = Session.query(model.AccountingLog).filter(model.AccountingLog.ts < (now - datetime.timedelta(days=config['accounting_log_keep_days'])))
    log.debug("Purged %d old accounting entries", query.count())
    query.delete()
    Session.flush()
    log.debug("finished garbage collection cycle")
    eventlet.sleep(config['garbage_collection_cycle'])
    
