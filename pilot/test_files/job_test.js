{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "./test.py",
                               "stdout": "out.txt",
                               "stderr": "err.txt",
			       "input_files": { "test.py": "gsiftp://tb01.ngrid.ru/home/shamardin/test.py" }
                             }
             }
           ],
  "requirements": { "lrms": "SLURM" }
}
