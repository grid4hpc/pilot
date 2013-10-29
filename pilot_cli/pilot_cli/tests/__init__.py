# -*- encoding: utf-8 -*-

minimal_job = """
{ "version": 2,
  "tasks": [ { "id": "a",
               "definition": {
                   "version": 2,
                   "executable": "/bin/true"
               }
              } ],
  "requirements": { "hostname": ["tb01.ngrid.ru"] }
}
"""
