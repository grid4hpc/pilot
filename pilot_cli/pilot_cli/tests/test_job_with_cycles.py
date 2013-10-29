# -*- encoding: utf-8 -*-

from pilot_cli import formats
from pilot_cli import tests

job_wrong = """
{ "version": 2,
  "description": "человеческое описание задания",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/job-58a8a28b/",
  "tasks": [ { "id": "s",
               "children": ["a"]
             },
             { "id": "a",
               "description": "человеческое описание задачи",
               "children": [ "b" ]
             },
             { "id": "b",
               "children": ["c"],
               "filename": "task_simple.js"
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
                               "stdout": "out-d.txt",
                               "requirements":
                                   { "hostname": ["tb01.ngrid.ru"] }
                             },
               "children": ["a"]
             }
           ],
  "requirements":
      { "hostname": ["tb01.ngrid.ru", "tb10.ngrid.ru"] }
}
"""

job_cyclic_no_parents = """
{ "version": 2,
  "tasks": [ { "id": "a",
               "description": "task 1",
               "children": [ "b" ],
               "filename": "js.jt"
             },
             { "id": "b",
               "children": [ "c" ],
               "description": "task 2",
               "filename": "js.jt"
             },
             { "id": "c",
               "children": [ "a" ],
               "description": "task 3",
               "filename": "js.jt"
             }
           ]
}
"""

def test_pass():
    formats.job_loads(tests.minimal_job)

def test_fail():
    try:
        formats.job_loads(job_wrong)
    except ValueError, e:
        assert str(e).startswith('job contains cycle')
    else:
        raise ValueError("expected failure for job_wrong")

    try:
        formats.job_loads(job_cyclic_no_parents)
    except ValueError, e:
        assert str(e).startswith('job does not have any start task')
    else:
        raise ValueError("expected failure for job_cyclic_no_parents")
