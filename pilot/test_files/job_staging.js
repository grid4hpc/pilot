{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "test.sh",
                               "stdout": "test.txt",
			       "stderr": "test-err.txt",
			       "input_files":
			       { "test.sh": "test.sh"
			       }
                             }
             }
           ],
  "requirements": { "fork": true }
}
