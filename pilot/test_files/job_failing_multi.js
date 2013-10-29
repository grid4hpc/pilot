{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdout": "test.txt"
                             },
               "children": ["c"]
             },
             { "id": "b",
               "definition": { "version": 2,
                               "executable": "/bin/false"
                             },
               "children": ["c"]
             },
             { "id": "c",
               "definition": { "version": 2,
                               "executable": "/bin/false"
                             }
             }
           ],
  "requirements": { "fork": true }
}
