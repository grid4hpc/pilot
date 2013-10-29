{ "version": 2,
  "tasks": [
      { "id": "a",
        "executable": "/bin/hostname",
        "requirements": {
            "queue": "long"
        }
      }
  ],
  "requirements": {
      "lrms": "Cleo"
  }
}

{ "version": 2,
  "tasks": [
      { "id": "a",
        "executable": "/bin/hostname",
        "requirements": {
            "lrms": "Cleo",
            "queue": "long"
        }
      }
  ]
}
