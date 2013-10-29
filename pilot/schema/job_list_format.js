{ "description": "Список заданий, к которым есть доступ у пользователя",
  "type": "array",
  "items": 
  { "type": "object",
    "properties":
    { "uri": 
      { "type": "string",
        "description": "URI задания",
        "format": "uri"
      }
    },
    "additionalProperties": false
  }
}
