{ "version": 2,
  "description": "тестовое задание",
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/jt/",
  "max_transfer_attempts": 15,
  "tasks": [ { "id": "a",
               "description": "задача #1",
               "definition": { "version": 2,
                               "executable": "/usr/bin/whoami",
                               "stdout": "test.txt",
                               "extensions": { "softenv": ["+gcc-4.4.3", "+libcrypto.so.1.0.0"],
                                               "nodes": "activemural:ppn=10+5:ia64-compute:ppn=2",
                                               "resourceAllocationGroup": {
                                                   "hostName": ["vis001", "vis002"],
                                                   "cpuCount": "10"
                                               },
                                               "complications": [
                                                   { "extraCase": "13" },
                                                   { "extraCase": "15", "sin": "13" }
                                               ]
                                             }
                             }
             }
           ],
  "requirements": { "fork": true, "hostname": ["tb01.ngrid.ru"] }
}
