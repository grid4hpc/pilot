{ "version": 2,
  "tasks": [ { "id": "a",
               "children": [ "b" ],
               "definition": { "version": 2,
                               "executable": "/bin/date"
                             }
             },
             { "id": "b",
               "children": [ "c" ],
               "definition": { "version": 2,
                               "executable": "/bin/true"
                             }
             },
             { "id": "c",
               "definition": { "version": 2,
                               "executable": "/bin/false"
                             }
             }
           ]
}
