{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdout": "test.txt"
                             }
             }
           ]
}
