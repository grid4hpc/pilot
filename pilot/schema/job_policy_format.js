{ "description": "Информация о политике обработки заданий на сервере",
  "type": "object",
  "properties": 
  { "server_time": 
    { "type": "string", "format": "date-time",
      "description": "Текущие дата и время на сервере" },
    "job_expiration": 
    { "type": "integer",
      "description": "сколько секунд после окончания выполнения задания оно хранится на сервере" }
  },
  "additionalProperties": true
}
