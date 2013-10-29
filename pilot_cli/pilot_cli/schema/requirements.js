{ "description": "Требования к ресурсам",
  "type": "object",
  "properties":
  { "hostname": { "type": "array",
                  "description": "Список подходящих хостов",
                  "items": { "type": "string",
                             "description": "имя хоста (FQDN)"
                           },
                  "optional": true,
                  "minItems": 1
                },
    "lrms": { "type": "string",
              "description": "Тип подходящего lrms, case-sensitive.",
              "optional": true
            },
    "fork": { "type": "boolean",
              "description": "Разрешить использовать lrms Fork. По умолчанию используется любой lrms, отличный от Fork (или заданный в lrms). Чтобы использовать lrms Fork, необходимо либо указать \"fork\": true, либо \"lrms\": \"Fork\".",
              "optional": true
            },
    "queue": { "type": "string",
               "description": "Название очереди для scheduler.",
               "optional": true
             },
    "os_name": { "type": "string", "optional": true },
    "os_release": { "type": "string", "optional": true },
    "os_version": { "type": "string", "optional": true },
    "platform": { "type": "string", "optional": true },
    "cpu_instruction_set": { "type": "string", "optional": true },
    "smp_size": { "type": "integer", "optional": true },
    "ram_size": { "type": "integer", "optional": true },
    "virtual_size": { "type": "integer", "optional": true },
    "cpu_hz": { "type": "integer", "optional": true },
    "software": { "type": "string", "optional": true }
  },
  "additionalProperties": false
}
