# -*- encoding: utf-8 -*-

from tests.data import *

from pilot import model
from pilot.model.meta import Session
from nose.plugins.attrib import attr

from pilot.spooler import tasks, matchmaker
from pilot_cli.formats import job_loads, task_loads
from M2Crypto import X509

import mock, pdb

fake_resources = [("tb01.ngrid.ru", "test", "pbs")]
    
@mock.patch("pilot.spooler.matchmaker.matchmake")
def test_task_start(matchmake):
    job = create_job()
    task = job.tasks[0]

    taskdef = task_loads(task.definition)
    jobdef = job_loads(task.job.definition)
    cert = X509.load_cert_string(task.job.proxy)

    matchmake.return_value = { ('tb01.ngrid.ru', 'test'): { 'lrms_type': 'pbs' } }
    results = tasks.matchmake(taskdef, jobdef, cert)
    assert results == fake_resources
