# -*- encoding: utf-8 -*-

import copy
import logging, random
from Queue import Queue, Empty
from threading import Thread

import sqlalchemy as sa
from sqlalchemy import and_

from pylons import request, response, config

from pilot.lib.base import BaseController, render_json, render_data, render_no_data, expects_json, abort
import pilot.lib.helpers as h
from pilot import model
from pilot.model.meta import Session
from pilot.lib import certlib, json, resources

import datetime
import urllib
import cPickle as pickle

from pilot_cli.formats import job_validate

log = logging.getLogger(__name__)

class Error(Exception):
    pass

class DeletedJobError(Error):
    pass

class DeletedTaskError(Error):
    pass


class JobTriggerNotifier(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.setName(self.__class__.__name__)

        self.queue = Queue()

    def run(self):
        log.info("%s thread started", self.getName())
        while(True):
            try:
                item = self.queue.get()
                if item is None: return
                while True:
                    try:
                        item = self.queue.get_nowait()
                        if item is None: return
                    except Empty:
                        break
                self.do_notify()
            except Exception, exc:
                log.error("Exception in %s thread: %s, continuning", self.getName(), exc)

    def do_notify(self):
        resp, data = h.SpoolerHttp().request('/job_trigger', method='POST')
        log.debug("Sending job_trigger notification to pilot-spooler")
        if resp.status >= 400:
            log.error("%s: pilot-spooler returned an error %d: %s", self.getName(), resp.status, data)

    def notify(self):
        self.queue.put(1)

    def terminate(self):
        self.queue.put(None)


job_trigger_notifier = JobTriggerNotifier()
job_trigger_notifier.start()


class JobController(BaseController):
    def index(self):
        result = []
        jobs = Session.query(model.Job).filter_by(owner=self.cert_dn, deleted=False)
        for job in jobs:
            result.append({
                'uri': h.url('job', jid=job.jid),
                'job_id': unicode(job.jid)
                })

        return render_json(result)

    def find_job(self, jobid, owner=None):
        """Найти и вернуть объект-задание, соответствующее jobid.
        Если задание не найдено, будет возвращена ошибка 404
        Если владелец задания отличен от owner, будет возвращена ошибка 401
        Если значение owner не задано, используется self.cert_dn.
        """
        if owner is None:
            owner = self.cert_dn
        db_job = Session.query(model.Job).filter_by(jid=jobid).first()
        if db_job is None:
            abort(404)

        if db_job.owner != owner:
            abort(401)

        Session.refresh(db_job)
        return db_job

    def show(self, jid):
        result = {}
        db_job = self.find_job(jid)

        for field in ['created', 'modified', 'expires', 'owner', 'vo']:
            result[field] = getattr(db_job, field)

        result['definition'] = db_job.definition
        result['owner'] = self.cert_dn
        result['state'] = []
        for state in db_job.states:
            record = {'s': state.s, 'ts': state.ts}
            if state.info is not None:
                record['info'] = state.info
            result['state'].append(record)
        result['operation'] = []
        for operation in db_job.operations:
            opinfo = {}
            for attr in ('op', 'id', 'created', 'completed', 'success', 'result'):
                v = getattr(operation, attr, None)
                if v is not None:
                    opinfo[attr] = v
            result['operation'].append(opinfo)
        result['tasks'] = {}
        for task in db_job.definition['tasks']:
            result['tasks'][task['id']] = h.url('task', jid=db_job.jid, task_name=task['id'])
        result['server_time'] = datetime.datetime.utcnow()
        result['server_policy_uri'] = h.url('job_policy')
        result['deleted'] = db_job.deleted
        return render_json(result)

    @expects_json
    def create(self, obj=None):
        try:
            definition = obj['definition']
            job_validate(definition)
        except KeyError, exc:
            abort(400, 'Request must contain job definition.')
        except ValueError, exc:
            abort(400, 'Job definition parsing error: %s' % str(exc))

        try:
            delegation = Session.query(model.Delegation) \
                         .filter_by(owner_hash=self.cert_owner,
                                    delegation_id=obj['delegation_id']).first()
            if delegation is None:
                abort(404, "Delegation \"%s\" not found." % obj['delegation_id'])
        except KeyError, exc:
            try:
                proxy = obj['proxy']
                delegation = model.Delegation.find_or_create(self.cert_owner, self.cert_vo,
                                                             self.fqans_string, proxy)
                delegaion_id = delegation.id
            except KeyError, exc:
                abort(400, 'Request must contain delegation_id or proxy.')

        job = model.Job.from_dict(definition, delegation, self.cert_dn, self.cert_vo)
        Session.add(job)
        Session.flush()
        result = [{'uri': h.url('job', jid=job.jid),
                   'job_id': unicode(job.jid)}]
        response.headers['location'] = result[0]['uri']
        return render_json(result, code=201)

    def delete(self, jid):
        db_job = self.find_job(jid)
        if not db_job.deleted:
            resp, data = h.SpoolerHttp().request('/job_delete/%s' % db_job.jid, method='DELETE')
            if resp.status == 408:
                abort(408)
            if resp.status >= 400:
                log.critical("spooler response to job_delete request is %d: %s", resp.status, data)
                abort(400)

        result = None
        return render_json(result)

    def update(self, jid):
        db_job = self.find_job(jid)

        req = json.loads(request.body)
        if 'proxy' in req:
            db_job.delegation = model.Delegation.find_or_create(self.cert_owner, self.cert_vo, self.fqans_string, req['proxy'])
            Session.flush()

        if 'definition' in req:
            job_state = db_job.current_state(Session).s
            if job_state != u'new':
                abort(400)
                
            try:
                job = req['definition']
                job_validate(job)
            except ValueError, e:
                return render_data('Job definition parsing error: %s' % str(e),
                                   code=400)
            
            # уалить задачи, которых теперь нет в описании из базы данных
            new_task_ids = [task['id'] for task in job['tasks']]
            for task in db_job.tasks:
                if task.name not in new_task_ids:
                    Session.delete(task)

            for task in job['tasks']:
                new_task = False
                db_task = Session.query(model.Task).filter(
                    and_(model.Task.job_id == db_job.id,
                         model.Task.name == unicode(task['id']))).first()
                if not db_task:
                    db_task = model.Task(unicode(task['id']))
                    new_task = True

                if 'definition' in task:
                    db_task.definition = task.pop('definition')

                if new_task:
                    db_task.add_state(u'new')
                    db_job.tasks.append(db_task)

            db_job.definition = job
            Session.flush()

        need_trigger = False
        if 'operation' in req:
            operation = req['operation']
            if 'op' not in operation:
                abort(400)
            if 'id' not in operation:
                abort(400)
            if operation['op'] not in ['start', 'pause', 'abort']:
                abort(400)
            if self.cert_vo is None:
                abort(401)
                
            db_operation = model.JobOperation(unicode(operation['op']), unicode(operation['id']))
            db_job.operations.append(db_operation)
            Session.flush()
            need_trigger = True

        if need_trigger:
            job_trigger_notifier.notify()
        return render_no_data()

    def matchmake(self, jid):
        job = self.find_job(jid)

        if job.deleted: abort(404)
        if self.cert_vo is None: abort(401)

        result = { 'runnable': True, 'resources': [] }

        for task in job.tasks:
            try:
                matches = resources.find_resources(task)
            except resources.ResourcesError, exc:
                result['runnable'] = False
                continue

            result['resources'].append(
                {'task_id': task.name,
                 'resources': [ resources.resource_name(*rhplq) for rhplq in matches ],
                 })

        return render_json(result)

    def get_rsl(self, jid):
        job = self.find_job(jid)

        if job.deleted: abort(404)
        if self.cert_vo is None: abort(401)

        result = { }

        for task in job.tasks:
            if 'rsl_at' in task.meta:
                task.meta.pop('rsl_at')
        Session.flush()

        for task in job.tasks:
            try:
                matches = resources.find_resources(task)
                target = matches[0]
                params = resources.generate_rsl(task, target)
                try:
                    result[task.name] = params.as_dict()
                except AttributeError:
                    result[task.name] = {
                        'RSL': str(params.description),
                        'submission_args': ' '.join(params.arguments),
                        }
                task.meta['rsl_at'] = matches[0]
                Session.flush()
            except resources.ResourcesError, exc:
                result[task.name] = { 'RSL': None, 'submission_args': None }

        return render_json(result)
