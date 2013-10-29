{ "description": "Расширенная информация об ошибке",
  "type": "object",
  "properties": 
  { "code": { "type": "string",
              "description": "код ошибки",
              "optional": true },
    "message": { "type": "string",
                 "description": "расширенное описание ошибки" },
    "ts": { "type": "string",
            "format": "date-time",
            "description": "дата и время ошибки" }
  },
  "additionalProperties": true
}
