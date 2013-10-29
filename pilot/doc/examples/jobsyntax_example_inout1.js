{ "version": 2,
  "default_storage_base": "gsiftp://example.org/my/files/",
  "tasks": [
      { "id": "a",
        "definition":
        { "version": 2,
          "executable": "/bin/cp",
          "arguments": ["hello.txt", "qux/test.txt"],
          "input_files": 
          { "hello.txt": "hello.txt",
            "foo.txt": "/bar.txt",
            "qux": "gsiftp://example.org/my/directory/qux/"
          },
          "ouput_files":
          { "qux/test.txt": "gsiftp://example.org/my/output/117/test.txt"
          }
        }
      },
      { "id": "b",
        "definition":
        { "version": 2,
          "executable": "/bin/cat",
          "arguments": ["hello.txt", "foo.txt"],
          "default_storage_base": "gsiftp://example.org/other/files/",
          "input_files": 
          { "hello.txt": "hello.txt",
            "foo.txt": "/bar.txt"
          }
        }
      }
  ]
}
