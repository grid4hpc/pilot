{ "description": "Задание",
  "type": "object",
  "properties":
  { "created": { "type": "string", "format": "date-time" },
    "modified": { "type": "string", "format": "date-time", "optional": true },
    "expires": { "type": "string", "format": "date-time", 
                 "description": "Дата, когда данная задача будет удалена с сервера." },
    "server_time": { "type": "string", "format": "date-time",
                     "description": "Текущие дата и время на сервере" },
    "server_policy_uri": { "type": "string", "format": "uri",
                           "description": "URI ресурса с описанием политики работы сервера" },
    "owner": { "type": "string", 
               "description": "DN пользователя, создавшего задание",
               "maxLength": 256 },
    "vo": { "type": "string", 
            "description": "Виртуальная организация задания",
            "maxLength": 64 },
    "state": { "type": "array", 
               "description": "Состояние задания, со всей историей его изменений", 
               "items": { "type": "object",
                          "description": "Запись о состоянии задания.",
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
             },
    "operation": { "type": "array",
                   "description": "операции, которые должны быть выполнены с данным заданием",
                   "items": { "type": "object",
                              "description": "Операция с заданием",
                              "properties":
                              { "op": { "type": "string",
                                        "description": "операция",
                                        "enum": [ "start", "pause", "abort" ] },
                                "id": { "type": "string",
                                        "description": "id операции",
                                        "maxLength": 36 },
                                "created": { "type": "string",
                                             "format": "date-time",
                                             "description": "время, когда была запрошена данная операция" },
                                "completed": { "type": "string",
                                               "format": "date-time",
                                               "description": "время, когда была вполнена данная операция",
                                               "optional": true,
                                               "requires": "success" },
                                "success": { "type": "boolean",
                                             "description": "было ли выполнение операции успешным",
                                             "optional": true,
                                             "requires": "completed" },
                                "result": { "type": "object",
                                            "description": "результат завершения операции",
                                            "optional": true,
                                            "requires": "completed" }
                                
                              },
                              "additionalProperties": true
                            }
                 },
    "definition": { "type": "string",
                    "description": "описание задания на языке описания заданий",
                    "format": "application/octet-stream"
                  },
    "tasks": { "type": "array",
               "description": "список URI задач задания",
               "items": { "type": "string",
                          "format": "uri" }
             }
  },
  "additionalProperties": false
}
