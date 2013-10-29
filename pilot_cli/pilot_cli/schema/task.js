{ "description": "Задача",
  "type": "object",
  "properties":
  { "version": { "type": "integer",
                 "description": "Номер версии используемой схемы описания задачи, для данной схемы это 2."
               },
    "description": { "type": "string",
                     "description": "Человеческое описание задачи",
                     "optional": true
                   },
    "executable": { "type": "string",
                    "description": "Локальный (относительно директории запуска задачи) или абсолютный путь выполняемого файла. Если вы хотите выполнить программу, находящуюся на удаленном ресурсе, необходимо для запуска передать ее в input_files, и она должна иметь атрибут executable на удаленном ресурсе."
                  },
    "jobtype": { "type": "string",
                 "description": "Тип mpi-задания. Разрешенные типы: single, mpi, openmp, hybrid. Если атрибут не указан, используется тип задания single.",
                 "optional": true
               },
    "nodes": { "type": "integer",
               "description": "Количество узлов, резервируемых для выполнения задачи.",
               "optional": true
             },
    "ppn": { "type": "integer",
             "description": "Количество экземпляров MPI-задачи, запускаемой на одном узле кластера.",
             "optional": true
           },
    "arguments": { "type": "array",
                   "description": "аргументы командной строки",
                   "items": { "type": "string" },
                   "optional": true
                 },
    "environment": { "type": "object",
                     "description": "дополнительные переменные среды окружения, которые будут установлены перед запуском задачи; атрибуты данного объекта являются названиями переменных окружения (будут переведены в верхний регистр), значения задают значения переменных",
                     "additionalProperties": true,
                     "optional": true
                   },
    "count": { "type": "integer",
               "description": "Количество процессоров, необходимых для выполнения задачи. Значение этого атрибута более 1 означает, что задача является MPI-задачей. Любые другие значения или отсутствие атрибута означают, что задача не является MPI-задачей.",
               "optional": true
             },
    "input_files": { "type": "object",
                     "description": "Входные файлы задачи. Название атрибутов данного объекта задает названия файлов, значения задают относительные пути или URLы файлов. Путь указывается относительно параметра default_storage_base. Если данный параметр отсутствует в описании задачи, то будет взято значение параметра default_storage_base задания. Если данный параметр отсутствует в описании задания, то все файлы для которых указаны относительные пути будут проигнорированы.",
                     "optional": true },
    "output_files": { "type": "object",
                      "description": "Выходные файлы задачи. Значения аналогично параметру input_files.",
                      "optional": true
                    },
    "stdin": { "type": "string",
               "description": "Отосительный путь или URL для stdin задачи. См. описание параметра input_files.",
               "optional": true               
             },
    "stdout": { "type": "string",
                "description": "Отосительный путь или URL для stdout задачи. См. описание параметра input_files.",
                "optional": true
              },
    "stderr": { "type": "string",
                "description": "Отосительный путь или URL для stderr задачи. См. описание параметра input_files.",
                "optional": true
              },
    "default_storage_base": { "type": "string",
                              "format": "uri",
                              "description": "URI, используемый для всех относительных путей файлов как база",
                              "optional": true
                            },
    "max_success_code": { "type": "integer",
                          "optional": true,
                          "description": "Максимальное значение кода выхода программы, при котором завершение считается нормальным (не аварийным). Код выхода рассматривается как беззнаковое целое. Если данный параметр не указан, используется значение по умолчанию, равное 0."
                        },
    "max_transfer_attempts": { "type": "integer",
                               "description": "Количество повторных попыток передачи каждого файла, завершающихся неудачей, прежде чем передача в целом будет считаться неуспешной.",
                               "optional": true
                             },
                          
    "requirements": { "type": "object",
                      "description": "описание требований задания в целом. Схема прилагается отдельно.",
                      "optional": true
                    },
    "extensions": { "type": "object",
                    "description": "Дополнительные расширения для запуска задачи.",
                    "optional": true
                  },
    "nodes": { "type": "integer",
               "optional": true,
               "description": "Количество узлов, на которых будет запущено mpi-задание"
             },
    "ppn": { "type": "integer",
             "optional": true,
             "description": "Количество mpi-процессов, которое будет запущено на каждом узле"
           },
    "meta": { "type": "object",
              "optional": true
            }
  },
  "additionalProperties": false
}
