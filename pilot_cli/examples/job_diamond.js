{ "version": 2,
  "description": "человеческое описание задания",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/job-58a8a28b/",
  "tasks": [ { "id": "a",
               "description": "человеческое описание задачи",
               "children": [ "b", "c" ],
               "filename": "task_simple.js"
             },
             { "id": "b",
               "children": ["d"],
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
                               "requirements": { "hostname": ["tb01.ngrid.ru"] }
                             }
             }
           ],
  "requirements": { "fork": true }
}
