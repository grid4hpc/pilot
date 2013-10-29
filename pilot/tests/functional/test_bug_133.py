# -*- encoding: utf-8 -*-

from nose.plugins.attrib import attr

from commands import getstatusoutput
from tempfile import mktemp
import time
import simplejson

@attr('slow')
def test_bug_133_stagein():
    jobspec_filename = mktemp()
    fd = open(jobspec_filename, "w")
    fd.write("""
{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/not/existing/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdin": "test.txt"
                             }
             }
           ]
}
""")
    fd.close()

    rc, output = getstatusoutput("pilot-job-submit -q %s" % jobspec_filename)
    assert rc == 0
    job_uri = output.strip()
    assert len(job_uri) != 0
    assert '/jobs/' in job_uri
    output = ""
    iterations = 1
    while 'aborted' not in output and iterations < 30:
        rc, output = getstatusoutput("pilot-job-status -q %s" % job_uri)
        assert rc == 0
        iterations += 1
        time.sleep(0.5)

    assert 'aborted' in output

    rc, output = getstatusoutput("pilot-uri-helper %s" % job_uri)
    assert rc == 0
    j = simplejson.loads(output)
    task_uri = j['tasks']['a']
    rc, output = getstatusoutput("pilot-uri-helper %s" % task_uri)
    assert rc == 0
    
    st = simplejson.loads(output)
    aborts = 0
    abort = None
    for state in st['state']:
        if state['s'] == 'aborted':
            aborts += 1
            assert 'info' in state
            abort = state

    assert aborts == 1
    assert "Staging error for RSL element fileStageIn" in abort['info']

@attr('slow')
def test_bug_133_stageout():
    jobspec_filename = mktemp()
    fd = open(jobspec_filename, "w")
    fd.write("""
{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/not/existing/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdout": "test.txt"
                             }
             }
           ]
}
""")
    fd.close()

    rc, output = getstatusoutput("pilot-job-submit -q %s" % jobspec_filename)
    assert rc == 0
    job_uri = output.strip()
    assert len(job_uri) != 0
    assert '/jobs/' in job_uri
    output = ""
    iterations = 1
    while 'aborted' not in output and iterations < 30:
        rc, output = getstatusoutput("pilot-job-status -q %s" % job_uri)
        assert rc == 0
        iterations += 1
        time.sleep(0.5)

    assert 'aborted' in output

    rc, output = getstatusoutput("pilot-uri-helper %s" % job_uri)
    assert rc == 0
    j = simplejson.loads(output)
    task_uri = j['tasks']['a']
    rc, output = getstatusoutput("pilot-uri-helper %s" % task_uri)
    assert rc == 0
    
    st = simplejson.loads(output)
    aborts = 0
    abort = None
    for state in st['state']:
        if state['s'] == 'aborted':
            aborts += 1
            assert 'info' in state
            abort = state

    assert aborts == 1
    assert "Staging error for RSL element fileStageOut" in abort['info']
