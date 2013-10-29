# -*- encoding: utf-8 -*-

import copy
import os
import simplejson
from pilot_cli.ext import jsonschema

from pkg_resources import resource_stream
from cStringIO import StringIO
import re

def _pkg_resources_loader(name):
    return resource_stream('pilot_cli', 'schema/%s.js' % name)

class _schema:
    def __init__(self, loader=None):
        self.loader = loader
        self._schemas = {}

    def __getattr__(self, attr):
        try:
            if attr not in self._schemas:
                self._schemas[attr] = simplejson.load(self.loader(attr))
            return self._schemas[attr]
        except:
            raise AttributeError("no such schema: %s" % attr)

schema = _schema(_pkg_resources_loader)
    
def job_load(stream):
    u"""Загрузить задание из открытого файла

    @param stream: file-like object with job definition"""
    data = simplejson.load(stream)
    job_validate(data)
    return data

def job_loads(desc):
    u"""Загрузить задание из строки

    @param desc: string with job definition"""
    return job_load(StringIO(desc))

def task_load(stream):
    u"""Загрузить задачу из открытого файла

    @param stream: file-like object with task definition"""
    data = simplejson.load(stream)
    task_validate(data)
    return data

def task_loads(desc):
    u"""Загрузить задачу из строки

    @param desc: string with task definition"""
    return task_load(StringIO(desc))

def job_validate(data):
    u"""
    Проверить задание на соответствие схемам описания задания, задачи
    и требований
    """
    jsonschema.validate(data, schema.job)
    if data['version'] != 2:
        raise ValueError("unknown job description version: %s" % \
                         str(data['version']))
    task_ids = [task['id'] for task in data['tasks']]
    for task in data['tasks']:
        if 'definition' in task and 'filename' in task:
            raise ValueError("both definition and filename present "
                             "in job task '%s'" % task['id'])
        
        if not re.match(r'^[a-zA-Z0-9\-]+$', task['id']):
            raise ValueError("task id '%s' is invalid" % task['id'])

        if 'definition' in task:
            task_validate(task['definition'])

        if 'children' in task:
            for child in task['children']:
                if child not in task_ids:
                    raise ValueError("child task '%s' for task '%s' "
                                     "does not exist" % (child, task['id']))

    if 'requirements' in data:
        requirements_validate(data['requirements'])

    job_validate_no_cycles(data)

def job_validate_no_cycles(job):
    u"""
    Проверить задание на отсутствие циклов в задачах.
    """
    tasks_by_id = {}
    parents = {}
    for task in job['tasks']:
        tasks_by_id[task['id']] = task
        parents[task['id']] = set()
        
    for task in job['tasks']:
        for child in task.get('children', []):
            parents[child].add(task['id'])

    start_nodes = []
    for task_id in parents:
        if len(parents[task_id]) == 0:
            start_nodes.append(task_id)

    if len(start_nodes) == 0:
        raise ValueError("job does not have any start task: "
                         "all tasks have parents.")

    def find_cycle(node, path):
        if node in path:
            raise ValueError("job contains cycle: %s" % "->".join(path+[node]))
        for child_node in tasks_by_id[node].get('children', []):
            find_cycle(child_node, path+[node])

    for node in start_nodes:
        find_cycle(node, path=[])

def task_validate(data):
    u"""
    Проверить задачу на соответствие схемам задачи и требований
    """
    jsonschema.validate(data, schema.task)
    if 'requirements' in data:
        requirements_validate(data['requirements'])

def requirements_validate(data):
    u"""
    Проверить описание требований на соответствие схеме.
    """
    jsonschema.validate(data, schema.requirements)


def job_from_file(filename):
    """
    Загрузить задание в формате JSON из файла filename. Автоматически
    подгрузить задачи, указанные через filename внутри задания.
    """
    
    try:
        fd = open(filename, "rb")
        definition = job_load(fd)
        fd.close()
    except ValueError, exc:
        raise ValueError("Error parsing job file %s: %s" % (filename, str(exc)))

    job_dir = os.path.dirname(filename)

    for task in definition['tasks']:
        if 'filename' in task:
            filename = os.path.join(job_dir, task.pop('filename'))
            try:
                fd = open(filename, 'rb')
                task['definition'] = task_load(fd)
                fd.close()
            except ValueError, exc:
                raise ValueError("Error parsing task file %s: %s" % \
                                 (filename, str(exc)))

    return definition

def parse_software_reqs(software):
    u"""
    Разобрать строку требований к ПО на компоненты. Возвращает
    словарь, в котором ключи - названия пакетов ПО, значения -
    требования для соответствующих пакетов (либо пустая строка, либо
    критерий сравнения + версия)
    """
    packages = [e.strip() for e in software.split(",") if e.strip() != ""]
    sw = {}
    for parts in (re.split("(<=?|>=?|==|!=)", pkg, 1) for pkg in packages):
        if len(parts) == 1:
            sw[parts[0]] = ""
        else:
            sw[parts[0]] = parts[1] + parts[2]
    return sw

def add_software(job, software):
    u"""
    Обновляет требования для ПО в задании.

    job - объект-задание
    software - строка требований к ПО

    Если задание уже содержит требования для определенного пакета, то
    они не модифицируются, иначе требования для пакета добавляются в
    задание.
    """

    if "requirements" not in job:
        job["requirements"] = {}

    if "software" not in job["requirements"]:
        job["requirements"]["software"] = ""

    existing = parse_software_reqs(job["requirements"]["software"])
    software = parse_software_reqs(software)
    software.update(existing)

    job["requirements"]["software"] = ", ".join(
        k + v for (k, v) in software.iteritems())


def substitute_params(obj, substitutions):
    u"""
    Замнеить переменные в задании или задаче obj.
    substitutions - словарь с переменными для замены.
    """
    def substitute(value):
        def replace(match):
            var = match.groups()[0]
            return str(substitutions.get(var, "{%s}" % var))
        return re.sub('{(.+?)}', replace, value)

    obj = copy.deepcopy(obj)

    for attr in ('default_storage_base', ):
        if attr in obj:
            obj[attr] = substitute(obj[attr])
    if 'tasks' in obj:
        # если это задание - на этом все.
        return obj
    
    for attr in ('executable', 'stdin', 'stdout', 'stderr'):
        if attr in obj:
            obj[attr] = substitute(obj[attr])
            
    if 'arguments' in obj:
        obj['arguments'] = [substitute(arg) for arg in obj['arguments']]
        
    if 'environment' in obj:
        for k, v in obj['environment'].iteritems():
            obj['environment'][k] = substitute(v)
            
    for attr in ('input_files', 'output_files'):
        if attr in obj:
            obj[attr] = dict((substitute(k), substitute(v)) \
                             for k, v in obj[attr].iteritems())

    return obj
