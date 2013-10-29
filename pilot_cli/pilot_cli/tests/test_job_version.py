# -*- encoding: utf-8 -*-

from pilot_cli import formats
from pilot_cli import tests

job_wrong_version = """
{ "version": 100,
  "tasks": [ { "id": "a" } ]
}
"""

def test_pass():
    formats.job_loads(tests.minimal_job)

def test_fail():
    try:
        formats.job_loads(job_wrong_version)
    except ValueError, e:
        assert str(e) == "unknown job description version: 100"
    else:
        raise ValueError("expected failure for job_wrong_version")
