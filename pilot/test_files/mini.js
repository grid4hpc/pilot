{ "version": 2,
  "description": "тестовое задание",
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "/bin/ls"
                             }
             }
           ],
  "requirements": {
       "hostname": ["gridmsu4.sinp.msu.ru"],
       "lrms": "PBS",
       "queue": "ngrid"
  }
}
