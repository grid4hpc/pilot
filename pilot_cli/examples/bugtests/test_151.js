{ "version": 2,
  "default_storage_base": "gsiftp://tb01.ngrid.ru/home/shamardin/bugtests/",
  "tasks": [ { "id": "a",
               "definition": { "version": 2,
                               "description": "task a",
                               "executable": "ex.sh",
                               "input_files": { "ex.sh": "ex.sh"
                                              },
                               "output_files": { "out0": "out/out0"
                                               },
                               "stderr": "out/stderr_i0",
                               "stdout": "out/stdout_i0"
                             }
             }
           ]
}
