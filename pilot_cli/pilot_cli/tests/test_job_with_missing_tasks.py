# -*- encoding: utf-8 -*-

from pilot_cli import formats
from pilot_cli import tests

job_wrong = """
{ "version": 2,
  "tasks": [ { "id": "a",
               "filename": "a.js",
               "children": ["b"]
             } ]
}
"""

def test_pass():
    formats.job_loads(tests.minimal_job)

def test_fail():
    try:
        formats.job_loads(job_wrong)
    except ValueError, e:
        assert str(e) == "child task 'b' for task 'a' does not exist"
    else:
        raise ValueError("expected failure for job_wrong")
