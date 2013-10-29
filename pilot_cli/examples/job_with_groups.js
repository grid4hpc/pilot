{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/compilation/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/bin/sh",
			       "arguments": ["-c", "hostname > /tmp/blabla; date +%c >>a"],
                               "stdout": "a-out.txt",
                               "stderr": "a-err.txt"
                             },
               "children": [ "b" ]
             },
             { "id": "b",
               "definition": { "version": 2,
                               "executable": "/bin/sh",
                               "arguments": ["-c", "cat /tmp/blabla ; rm -f /tmp/blabla"],
                               "stdout": "b-out.txt",
                               "stderr": "b-err.txt"
                             }
             }
           ],
  "groups": [ [ "a", "b"] ]
}
