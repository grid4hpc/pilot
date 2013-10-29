# -*- encoding: utf-8 -*-

import logging, urllib2, pickle
import sqlalchemy as sa
from pylons import request, response, config
from pylons.controllers.util import abort

from pilot.lib.base import BaseController, render_data, render_json
from pilot.model.meta import Session
from pilot.lib import helpers as h
from pilot import model
from pilot.spooler import globus

log = logging.getLogger(__name__)

class TaskController(BaseController):
    def find_task(self, jid, task_name, owner=None):
        """Найти и вернуть объект-задание, соответствующее jobid.
        Если задача не найдена, будет возвращена ошибка 404
        Если владелец задачи отличен от owner, будет возвращена ошибка 401
        Если значение owner не задано, используется self.cert_dn.
        """
        if owner is None:
            owner = self.cert_dn

        db_task = Session.query(model.Task).join(model.Job).filter(
            sa.and_(model.Job.jid == jid, model.Task.name == task_name)).first()
        if db_task is None:
            abort(404)

        if db_task.job.owner != owner:
            abort(401)

        Session.refresh(db_task)
        return db_task
        
    def update(self, jid, task_name):
        db_task = self.find_task(jid, task_name)
        if db_task.deleted or db_task.job.deleted:
            response.header['Allow'] = 'GET'
            abort(405)

        db_task.definition = str(request.body)
        Session.flush()

        return render_data('', code=204)

    def index(self, jid, task_name):
        db_task = self.find_task(jid, task_name)

        result = {
            "created": db_task.created,
            "modified": db_task.modified,
            "job": h.url('job', jid=db_task.job.jid),
            "definition": str(db_task.definition),
            "deleted": db_task.deleted,
            "exit_code": db_task.exit_code,
            "state": []
            }

        for state in db_task.states:
            rec = {'s': state.s, 'ts': state.ts}
            if state.info:
                rec['info'] = state.info
            result['state'].append(rec)

        return render_json(result)

    def add_state(self, submission_id):
        """Обновить при необходимости состояние задачи согласно
        полученному сообщению WS-Notification.
        """

        if not submission_id.startswith('uuid:'):
            abort(400)

        submission_uuid = unicode(submission_id.split(':')[1])
        db_task = Session.query(model.Task).filter_by(
            submission_uuid=submission_uuid).first()

        # XXX: do security checks here

        if db_task is None:
            abort(404)
        else:
            Session.refresh(db_task)

        gstate = globus.State.from_string(request.body)
        log_message = "WS-N message: %s %s (pilot:%s) %s" % (submission_id, gstate,
                                                             gstate.pilot_state, gstate.cause)
        if gstate.exit_code is not None:
            log_message += ", exit_code=%d" % gstate.exit_code
        
        log.debug(log_message)

        spooler_request = urllib2.Request('http://localhost:%d/wsn_task_callback/%s' % (
            config['matchmaker_port'], submission_uuid))
        spooler_request.add_header('User-Agent', 'pilot-httpd')
        data = pickle.dumps(gstate)
        spooler_request.add_header('Content-Length', str(len(data)))
        spooler_request.add_data(data)
        spooler_request.get_method = lambda: 'POST'
        try:
            fd = urllib2.urlopen(spooler_request)
            result = fd.read()
            code = fd.code
            fd.close()
        except urllib2.HTTPError, exc:
            code = exc.code
            if exc.fp is not None:
                result = exc.fp.read()
            else:
                result = ''
        except urllib2.URLError, exc:
            abort(503)
                
        if code > 299:
            log.error("pilot-spooler returned an error %d: %s", code, result)

        return render_data('', code=204)
