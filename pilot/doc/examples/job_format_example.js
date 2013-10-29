{ "created": "2009-07-03T10:27:00Z",
  "modified": "2009-07-03T10:27:14Z",
  "expires": "2009-07-04T10:28:30Z",
  "server_time": "2009-07-03T10:28:30Z",
  "server_policy_uri": "https://pilot.ngrid.ru/policy/job/",
  "definition": { "version": 2,
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
  "state": [ { "s": "new",
               "ts": "2009-07-03T10:27:00Z" },
             { "s": "pending",
               "ts": "2009-07-03T10:27:14Z" },
             { "s": "running",
               "ts": "2009-07-03T10:27:22Z" } ],
  "owner": "/C=RU/O=NanoGrid/OU=users/OU=sinp.msu.ru/CN=Lev Shamardin",
  "operation": [ { "op": "start",
                   "id": "c9deca6c-3208-4146-848b-2b65b0943127",
                   "created": "2009-07-03T10:27:03Z",
                   "completed": "2009-07-03T10:27:14Z",
                   "success": true
                 } ],
  "tasks": { 
      "a": "https://pilot.ngrid.ru/jobs/912832/a/"
  },
  "deleted": false
}
