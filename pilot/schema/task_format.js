{ "description": "Отдельная задача",
  "type": "object",
  "properties":
  { "created": { "type": "string", "format": "date-time" },
    "modified": { "type": "string", "format": "date-time", "optional": true },
    "job": { "type": "string", "format": "uri", 
             "description": "URI задания, к которому относится данная задача" },
    "definition": { "type": "string",
                    "description": "описание задачи на языке описания задач",
                    "format": "application/octet-stream"
                  },
    "state": { "type": "array", 
               "description": "Состояние задачи, со всей историей его изменений", 
               "items": { "type": "object",
                          "description": "Запись о состоянии задачи.",
                          "properties":
                          { "s": { "type": "string", 
                                   "description": "состояние",
                                   "enum": [ "new", "pending", "running", "paused", "finished", "aborted"] },
                            "ts": { "type": "string",
                                    "format": "date-time",
                                    "description": "время, когда наступило данное состояние" }
                          },
                          "additionalProperties": true
                        }
             }
  },
  "additionalProperties": false
}
