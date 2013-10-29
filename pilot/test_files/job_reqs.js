{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "max_transfer_attempts": 15,
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "/bin/sleep",
			       "arguments": ["10"],
                               "stdout": "test.txt"
                             }
             }
           ],
  "requirements": { "ram_size": 2, "software": "abinit > 6" }
}
