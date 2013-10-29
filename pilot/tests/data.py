# -*- encoding: utf-8 -*-

import os
import pdb

try:
    import json
except ImportError:
    import simplejson as json

from pilot import model
from pilot.model.meta import Session
from pilot.lib import certlib

from pylons import config
config_file = config['__file__']

simple_fork_job = """
{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             }
             }
           ],
  "requirements": { "fork": true }
}
"""

simple_fork_ab_job = """
{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             },
               "children": ["b"]
             },
             { "id": "b",
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             }
             }
           ],
  "requirements": { "fork": true }
}
"""

simple_diamond_job = """
{ "version": 2,
  "description": "человеческое описание задания",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/job-58a8a28b/",
  "tasks": [ { "id": "a",
               "description": "человеческое описание задачи",
               "children": [ "b1", "c" ],
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             }
             },
             { "id": "b1",
               "children": ["b2"],
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             }
             },
             { "id": "b2",
               "children": ["d"],
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             }
             },
             { "id": "c",
               "description": "задача C" ,
               "children": ["d"],
               "definition": { "version": 2,
                               "executable": "/bin/ls",
                               "stdout": "c/out.txt"
                             }
             },
             { "id": "d",
               "definition": { "version": 2,
                               "executable": "/bin/ls",
                               "stdout": "out-d.txt"
                             }
             }
           ],
  "requirements": { "fork": true }
}
"""

simple_fork_job_dict = json.loads(simple_fork_job)
simple_fork_ab_job_dict = json.loads(simple_fork_ab_job)
simple_diamond_job_dict = json.loads(simple_diamond_job)

test_user_proxy = open("/tmp/x509up_u%d" % os.getuid()).read()
test_user_bad_proxy = """
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
""".decode('base64').decode('zip')
test_user_dn = u"/C=RU/O=RDIG/OU=users/OU=sinp.msu.ru/CN=Test User"
test_user_vo = u"gridnnn"
test_user_fqans = ['/%s' % test_user_vo]

from pilot.lib import ssl_voms_auth_mw
ssl_voms_auth_mw.configure_testing_environ(
    test_user_dn,
    certlib.proxy_owner_hash(certlib.load_proxy(test_user_proxy)[1]),
    test_user_vo, test_user_fqans)

def empty_db():
    for job in Session.query(model.Job):
        Session.delete(job)
    for delegation in Session.query(model.Delegation):
        Session.delete(delegation)
    Session.flush()

def create_delegation(proxy=test_user_proxy, delegation_id=None):
    key, chain = certlib.load_proxy(proxy)    
    delegation = model.Delegation.find_or_create(
        certlib.proxy_owner_hash(chain),
        test_user_dn, "/%s" % test_user_vo, key=key, chain=chain,
        delegation_id=delegation_id)
    Session.flush()
    ssl_voms_auth_mw.configure_testing_environ(test_user_dn, delegation.owner_hash,
                                               test_user_vo, test_user_fqans)
    return delegation
    
def create_job(job_dict=None, proxy=test_user_proxy):
    if job_dict is None:
        job_dict = simple_fork_job_dict
    key, chain = certlib.load_proxy(proxy)
    delegation = model.Delegation.find_or_create(certlib.proxy_owner_hash(chain),
                                                 test_user_dn, "/%s" % test_user_vo, key=key, chain=chain)
    job = model.Job.from_dict(job_dict, delegation,
                              test_user_dn, test_user_vo)
    job.operations.append(model.JobOperation(u'start', u'1'))
    Session.add(job)
    Session.flush()
    Session.refresh(job)

    return job

def empty_db_and_create_job():
    empty_db()
    return create_job()

def empty_db_and_create_ab_job():
    empty_db()
    return create_job(simple_fork_ab_job_dict)

def empty_db_and_create_diamond_job():
    empty_db()
    return create_job(simple_diamond_job_dict)

def last_log():
    return Session.query(model.AccountingLog) \
           .order_by(model.AccountingLog.ts.desc()).first()

def state_count(something, s):
    return sum([1 for state in something.states if state.s == s])


class FakeRsl(object):
    submission_uuid = u"345b17fa-f9b5-4da8-b2fd-95210856ae52"
    globusrun_args = ['--blah']
    def __str__(self):
        return "<rsl/>"

fake_rsl = FakeRsl()
