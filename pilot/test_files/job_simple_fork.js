{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/bin/date",
			       "arguments": ["+%c"],
                               "stdout": "test.txt"
                             }
             }
           ],
  "requirements": { "fork": true }
}
