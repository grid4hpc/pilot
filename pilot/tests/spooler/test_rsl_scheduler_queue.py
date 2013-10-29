# -*- encoding: utf-8 -*-

from pilot.spooler import globus
from pilot_cli.formats import job_loads
from pilot.lib import etree
from cStringIO import StringIO

test_job = """{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdout": "test.txt"
                             }
             }
           ]
}
"""

def test_job_without_scheduler():
    job = job_loads(test_job)
    task = job['tasks'][0]['definition']
    rsl_obj = globus.RSL(task, job,
                         dict(hostname='tb01.ngrid.ru',
                              queue=task.get('queue', None),
                              lrms_type=task.get('requirements', {}).get('lrms', 'Fork')))
    args = ' '.join(rsl_obj.globusrun_args)
    assert '-factory-type Fork' in args
    j = etree.ElementTree(file=StringIO(str(rsl_obj)))
    assert len(j.findall('queue')) == 0

def test_job_with_scheduler():
    job = job_loads(test_job)
    task = job['tasks'][0]['definition']
    task['requirements'] = {'lrms': 'PBS'}
    rsl_obj = globus.RSL(task, job,
                         dict(hostname='tb01.ngrid.ru',
                              queue=task.get('queue', None),
                              lrms_type=task.get('requirements', {}).get('lrms', 'Fork')))
    args = ' '.join(rsl_obj.globusrun_args)
    assert '-factory-type PBS' in args

def test_job_with_queue():
    job = job_loads(test_job)
    task = job['tasks'][0]['definition']
    task['scheduler'] = 'PBS'
    task['queue'] = 'fast'
    task['requirements'] = {'lrms': 'PBS'}
    rsl_obj = globus.RSL(task, job,
                         dict(hostname='tb01.ngrid.ru',
                              queue=task.get('queue', None),
                              lrms_type=task.get('requirements', {}).get('lrms', 'Fork')))
    args = ' '.join(rsl_obj.globusrun_args)
    assert '-factory-type PBS' in args
    j = etree.ElementTree(file=StringIO(str(rsl_obj)))
    q = j.findall('queue')
    assert len(q) == 1
    assert q[0].text == 'fast'
    
