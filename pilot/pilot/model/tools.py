# -*- encoding: utf-8 -*-

import copy
import sqlalchemy as sa
from pilot import model
from pilot.model.meta import Session


def setup_task_links(db_job, debug=False):
    """
    Расставить связи между задачами задания в базе данных
    если debug=True, возвращает отладочные сообщения (как итератор)
    """
    task_ids = {}
    for db_task in db_job.tasks:
        task_ids[db_task.name] = db_task.id

    messages = []

    Session.begin()
    try:
        old_parents = Session.query(model.TaskParent).filter(model.TaskParent.task_id.in_(task_ids.values()))
        if old_parents.count() > 0:
            for tp in old_parents:
                if debug:
                    messages.append("Deleting old link %s" % tp)
                Session.delete(tp)
        jobdef = copy.deepcopy(db_job.definition)
        for task in jobdef['tasks']:
            parent_id = task_ids[task['id']]        
            children = task.get("children", [])
            for child_id in (task_ids[child] for child in task.get("children", [])):
                Session.add(model.TaskParent(child_id, parent_id))
                if debug:
                    messages.append("Task %d is parent of task %d" % (parent_id, child_id))
        Session.commit()
    except:
        Session.rollback()
        raise

    return messages
