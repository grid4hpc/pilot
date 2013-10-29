{ "description": "Файлы, находящиеся в Sandbox",
  "type": "array",
  "items": 
  { "type": "object",
    "description": "файл из Sandbox",
    "properties": 
    { "filename": { "type": "string", 
                    "description": "имя файла" },
      "modified": { "type": "string", "format": "date-time", 
                    "description": "дата модификации файла" },
      "surl": { "type": "string",
                "description": "Storage URL для файла",
                "optional": true },
      "turl": { "type": "string",
                "description": "Transport URL для файла",
                "optional": true }
    }
  }
}
