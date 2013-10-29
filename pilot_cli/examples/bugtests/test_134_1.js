{ "version": 2,
  "tasks": [ { "id": "a",
               "description": "task 1",
               "children": [ "b" ],
               "filename": "js.jt"
             },
             { "id": "b",
               "children": [ "c" ],
               "description": "task 2",
               "filename": "js.jt"
             },
             { "id": "c",
               "children": [ "a" ],
               "description": "task 3",
               "filename": "js.jt"
             }
           ]
}
