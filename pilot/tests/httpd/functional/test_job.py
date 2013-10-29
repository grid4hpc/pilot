# -*- encoding: utf-8 -*-

from tests.httpd import *
from tests.data import *

from nose.tools import with_setup

from pilot import model
from pilot.model.meta import Session
import pilot.lib.helpers as h
from pylons import config
from pilot.lib import json
import urlparse

class TestJobController(TestController):
    def __init__(self, *args, **kwargs):
        TestController.__init__(self, *args, **kwargs)

    def remove_all_jobs(self):
        jobs = Session.query(model.Job).all()
        for job in jobs: Session.delete(job)
        Session.flush()

    def rel_uri(self, uri):
        _, _, rel_uri, _, _, _ = urlparse.urlparse(uri)
        return rel_uri

    def test_query_jobs(self):
        self.remove_all_jobs()
        response = self.app.get(url(controller='job', action='index'))
        js = json.loads(response.body)
        assert len(js) == 0

        create_job()
        response = self.app.get(url(controller='job', action='index'))
        js = json.loads(response.body)
        assert len(js) == 1

        self.remove_all_jobs()
        response = self.app.get(url(controller='job', action='index'))
        js = json.loads(response.body)
        assert len(js) == 0

    def test_show_job(self):
        create_job()
        response = self.app.get(url(controller='job', action='index'))
        js = json.loads(response.body)
        job_uri = self.rel_uri(js[-1]['uri'])
        response = self.app.get(job_uri)
        js = json.loads(response.body)
        emptydef = json.loads(simple_fork_job)
        for task in emptydef['tasks']:
            if 'definition' in task:
                task.pop('definition')
        assert js['definition'] == emptydef
