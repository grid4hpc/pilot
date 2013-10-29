{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "/bin/sleep",
			       "arguments": ["600"],
                               "stdout": "test.txt"
                             }
             }
           ],
  "requirements": { "platform": "i686" }
}
