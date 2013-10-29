{ "description": "Запрос на модификацию параметров задания",
  "type": "object",
  "properties":
  { "operation": { "type": "object",
                   "description": "Операция с заданием",
                   "properties":
                   { "op": { "type": "string",
                             "description": "операция",
                             "enum": [ "start", "pause", "abort" ] },
                     "id": { "type": "string",
                             "description": "id операции",
                             "maxLength": 36 }
                   },
                   "additionalProperties": true,
                   "optional": true
                 },
    "definition": { "type": "string",
                    "description": "описание задания на языке описания заданий",
                    "format": "application/octet-stream",
                    "optional": true
                  }
  }
}
