# -*- encoding: utf-8 -*-

from pilot.spooler import globus
from pilot_cli.formats import job_loads
from pilot.lib import etree
from cStringIO import StringIO

test1 = """{ "version": 2,
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
test1_rsl = "<job><executable>/usr/bin/whoami</executable><directory>${GLOBUS_SCRATCH_DIR}/%(jobid)s/</directory><stdout>${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</stdout><jobType>single</jobType><fileStageIn><transfer><sourceUrl>gsiftp://tb01.ngrid.ru/etc/profile.d/</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageIn><fileStageOut><transfer><sourceUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</sourceUrl><destinationUrl>gsiftp://tb01.ngrid.ru/home/shamardin/jt/test.txt</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageOut><fileCleanUp><deletion><file>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</file></deletion></fileCleanUp></job>"
test1_args = ['-submit', '-batch', '-factory', 'tb01.ngrid.ru', '-factory-type', 'Fork', '-submission-id', u'uuid:%(jobid)s', '-staging-delegate']

test2 = """{ "version": 2,
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami"
                             }
             }
           ]
}
"""

test2_rsl = "<job><executable>/usr/bin/whoami</executable><directory>${GLOBUS_SCRATCH_DIR}/%(jobid)s/</directory><jobType>single</jobType><fileStageIn><transfer><sourceUrl>gsiftp://tb01.ngrid.ru/etc/profile.d/</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageIn><fileCleanUp><deletion><file>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</file></deletion></fileCleanUp></job>"
test2_args = ['-submit', '-batch', '-factory', 'tb01.ngrid.ru', '-factory-type', 'Fork', '-submission-id', u'uuid:%(jobid)s', '-staging-delegate']

test3 = """{ "version": 2,
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "arguments": ["hello", "world"],
                               "count": 3,
                               "environment": { "foo": "bar",
                                                "qux": "xyzzy" },
                               "input_files": { "f1": "f2", "f3": "f4" },
                               "output_files": { "f5": "f6" },                               
                               "stdin" : "some-input.txt",
                               "stdout": "gsiftp://www.some.com/output.txt",
                               "stderr": "errors",
                               "default_storage_base": "gsiftp://foo.com///",
                               "requirements": { "hostname": ["cleo-devel.ngrid.ru"],
                                                 "queue": "fast",
                                                 "lrms": "Cleo"}
                             }
             }
           ]
}
"""
test3_rsl = "<job><executable>/usr/bin/whoami</executable><directory>${GLOBUS_SCRATCH_DIR}/%(jobid)s/</directory><argument>hello</argument><argument>world</argument><environment><name>qux</name><value>xyzzy</value></environment><environment><name>foo</name><value>bar</value></environment><stdin>${GLOBUS_SCRATCH_DIR}/%(jobid)s/in.%(pid)d</stdin><stdout>${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</stdout><stderr>${GLOBUS_SCRATCH_DIR}/%(jobid)s/err.%(pid)d</stderr><count>3</count><jobType>mpi</jobType><fileStageIn><transfer><sourceUrl>gsiftp://tb01.ngrid.ru/etc/profile.d/</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>gsiftp://foo.com///some-input.txt</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/in.%(pid)d</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>gsiftp://foo.com///f2</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/f1</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>gsiftp://foo.com///f4</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/f3</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageIn><fileStageOut><transfer><sourceUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</sourceUrl><destinationUrl>gsiftp://www.some.com/output.txt</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/err.%(pid)d</sourceUrl><destinationUrl>gsiftp://foo.com///errors</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/f5</sourceUrl><destinationUrl>gsiftp://foo.com///f6</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageOut><fileCleanUp><deletion><file>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</file></deletion></fileCleanUp></job>"
test3_args = ['-submit', '-batch', '-factory', 'tb01.ngrid.ru', '-factory-type', 'Cleo', '-submission-id', u'uuid:%(jobid)s', '-staging-delegate']

test4 = """{ "version": 2,
  "default_storage_base": "gsiftp://foo.org/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdin" : "some-input.txt",
                               "stdout": "gsiftp://www.some.com/output.txt",
                               "default_storage_base": "gsiftp://foo.com/"
                             }
             }
           ]
}
"""
test4_rsl = "<job><executable>/usr/bin/whoami</executable><directory>${GLOBUS_SCRATCH_DIR}/%(jobid)s/</directory><stdin>${GLOBUS_SCRATCH_DIR}/%(jobid)s/in.%(pid)d</stdin><stdout>${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</stdout><jobType>single</jobType><fileStageIn><transfer><sourceUrl>gsiftp://tb01.ngrid.ru/etc/profile.d/</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>gsiftp://foo.com/some-input.txt</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/in.%(pid)d</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageIn><fileStageOut><transfer><sourceUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</sourceUrl><destinationUrl>gsiftp://www.some.com/output.txt</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageOut><fileCleanUp><deletion><file>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</file></deletion></fileCleanUp></job>"
test4_args = ['-submit', '-batch', '-factory', 'tb01.ngrid.ru', '-factory-type', 'Fork', '-submission-id', u'uuid:%(jobid)s', '-staging-delegate']

test5 = """{ "version": 2,
  "default_storage_base": "gsiftp://foo.org/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdin" : "some-input.txt",
                               "stdout": "gsiftp://www.some.com/output.txt"
                             }
             }
           ]
}
"""
test5_rsl = "<job><executable>/usr/bin/whoami</executable><directory>${GLOBUS_SCRATCH_DIR}/%(jobid)s/</directory><stdin>${GLOBUS_SCRATCH_DIR}/%(jobid)s/in.%(pid)d</stdin><stdout>${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</stdout><jobType>single</jobType><fileStageIn><transfer><sourceUrl>gsiftp://tb01.ngrid.ru/etc/profile.d/</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</destinationUrl><maxAttempts>5</maxAttempts></transfer><transfer><sourceUrl>gsiftp://foo.org/some-input.txt</sourceUrl><destinationUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/in.%(pid)d</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageIn><fileStageOut><transfer><sourceUrl>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/out.%(pid)d</sourceUrl><destinationUrl>gsiftp://www.some.com/output.txt</destinationUrl><maxAttempts>5</maxAttempts></transfer></fileStageOut><fileCleanUp><deletion><file>file:///${GLOBUS_SCRATCH_DIR}/%(jobid)s/</file></deletion></fileCleanUp></job>"
test5_args = ['-submit', '-batch', '-factory', 'tb01.ngrid.ru', '-factory-type', 'Fork', '-submission-id', u'uuid:%(jobid)s', '-staging-delegate']

def check_desc_rsl(desc, rsl, args):
    job = job_loads(desc)
    task = job['tasks'][0]['definition']
    rsl_obj = globus.RSL(task, job,
                         dict(hostname='tb01.ngrid.ru',
                              queue=task.get('queue', None),
                              lrms_type=task.get('requirements', {}).get('lrms', 'Fork')))
    real_rsl = rsl % dict(jobid=rsl_obj.jobid, pid=rsl_obj.pid)

    if str(rsl_obj).startswith("<?xml"):
        real_rsl = '<?xml version="1.0" encoding="UTF-8"?>' + real_rsl

    assert real_rsl == str(rsl_obj)
    real_args = list(args)
    for i in xrange(0, len(args)):
        if '%(jobid)s' in real_args[i]:
            real_args[i] = real_args[i] % dict(jobid=rsl_obj.jobid)
        if '%(pid)d' in args[i]:
            real_args[i] = real_args[i] % dict(jobid=rsl_obj.pid)
    assert real_args == rsl_obj.globusrun_args

def test_desc1():
    check_desc_rsl(test1, test1_rsl, test1_args)

def test_desc2():
    check_desc_rsl(test2, test2_rsl, test2_args)

def test_desc3():
    check_desc_rsl(test3, test3_rsl, test3_args)

def test_desc4():
    check_desc_rsl(test4, test4_rsl, test4_args)

def test_desc5():
    check_desc_rsl(test5, test5_rsl, test5_args)
