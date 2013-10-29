{
  "extensions": { "softenv": ["+gcc-4.4.3", "+libcrypto.so.1.0.0"],
                "nodes": "activemural:ppn=10+5:ia64-compute:ppn=2",
                "resourceAllocationGroup": {
                    "hostName": ["vis001", "vis002"],
                    "cpuCount": "10"
                },
                "complications": [
                    { "extraCase": "13" },
                    { "extraCase": "15", "sin": "13" }
                ]
  }}
