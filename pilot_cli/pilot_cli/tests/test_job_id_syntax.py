# -*- encoding: utf-8 -*-

from pilot_cli import formats
from pilot_cli import tests

job_wrong = """
{ "version": 2,
  "tasks": [ { "id": "a,be",
               "filename": "a.js"
             } ]
}
"""

def test_pass():
    formats.job_loads(tests.minimal_job)

def test_fail():
    try:
        formats.job_loads(job_wrong)
    except ValueError, e:
        assert str(e) == "task id 'a,be' is invalid"
    else:
        raise ValueError("expected failure for job_wrong")
