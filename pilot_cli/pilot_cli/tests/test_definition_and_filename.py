# -*- encoding: utf-8 -*-

from pilot_cli import formats
from pilot_cli import tests

job_wrong = """
{ "version": 2,
  "tasks": [ { "id": "a",
               "filename": "a.js",
               "definition": {} } ]
}
"""

def test_pass():
    formats.job_loads(tests.minimal_job)

def test_fail():
    try:
        formats.job_loads(job_wrong)
    except ValueError, e:
        assert str(e) == "both definition and filename present in job task 'a'"
    else:
        raise ValueError("expected failure for job_wrong")
