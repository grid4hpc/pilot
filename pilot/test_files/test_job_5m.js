{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/compilation/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "executable": "/bin/sh",
			       "arguments": ["-c", "hostname; date; sleep 7m; date"],
                               "stdout": "7m.txt"
                             }
             }
           ],
  "requirements": { "hostname": ["nnn2.pnpi.nw.ru"] }
}
