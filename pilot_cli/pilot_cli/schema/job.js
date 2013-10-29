{ "description": "Задание",
  "type": "object",
  "properties":
  { "version": { "type": "integer",
                 "description": "Номер версии используемой схемы описания задания, для данной схемы это 2."
               },
    "description": { "type": "string",
                     "description": "Человеческое описание задания",
                     "optional": true
                   },
    "default_storage_base": { "type": "string",
                              "format": "uri",
                              "description": "URI, используемый для всех относительных путей файлов как база",
                              "optional": true
                            },
    "max_transfer_attempts": { "type": "integer",
                               "description": "Количество повторных попыток передачи каждого файла, завершающихся неудачей, прежде чем передача в целом будет считаться неуспешной.",
                               "optional": true
                             },
    "tasks": { "type": "array",
               "description": "Задачи, из которых состоит задание",
               "items": { "type": "object",
                          "description": "Задача задания",
                          "additionalProperties": false,
                          "properties":
                          { "id": 
                            { "type": "string",
                              "description": "машинный идентификатор задания, из алфавита [a-zA-Z0-9\\-]+"
                            },
                            "description": 
                            { "type": "string",
                              "description": "человеческое описание/название задачи задания",
                              "optional": true
                            },
                            "definition":
                            { "type": "object",
                              "description": "Описание задачи. Данный атрибут может отсутствовать, в этом случае описание задачи загружается на сервис pilot отдельно. Схема прилагается отдельно.",
                              "optional": true
                            },
                            "children":
                            { "type": "array",
                              "description": "Дочерние задачи для данной задачи",
                              "items": { "type": "string",
                                         "description": "идентификатор задачи (значение ее id)"
                                       },
                              "optional": true
                            },
                            "filename":
                            { "type": "string",
                              "description": "Локальное имя файла с задачей",
                              "optional": true
                            },
                            "meta": { "type": "object",
                                      "optional": true
                                    }
                          }
                        },
               "minItems": 1
             },
    "groups": { "type": "array",
                "description": "группы задач",
                "items": { "type": "array",
                           "description": "идентификаторы задач из одной группы",
                           "items": { "type": "string",
                                      "description": "идентификатор задачи"
                                    },
                           "minItems": 2
                         },
                "optional": true,
                "minItems": 1
              },
    "requirements": { "type": "object",
                      "description": "описание требований задания в целом. Схема прилагается отдельно.",
                      "optional": true
                    },
    "meta": { "type": "object",
              "optional": true
            }
  },
  "additionalProperties": false
}
