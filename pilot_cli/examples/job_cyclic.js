{ "version": 2,
  "description": "человеческое описание задания",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/job-58a8a28b/",
  "tasks": [ { "id": "s",
               "children": ["a"]
             },
             { "id": "a",
               "description": "человеческое описание задачи",
               "children": [ "b" ]
             },
             { "id": "b",
               "children": ["c"],
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
                             },
               "children": ["a"]
             }
           ],
  "requirements": { "hostname": ["tb01.ngrid.ru", "tb10.ngrid.ru"] }
}
