[
  {
    "__metadata": {
      "infosys2_site_version": "0.5.0"
    },
    "CreationTime": "2012-03-16T13:13:18Z",
    "Site": {
      "Info": {
        "ServiceEndpoint": {
          "MDS": "https://tb13.ngrid.ru:8443/wsrf/services/DefaultIndexService",
          "GRAM": [
            "https://tb13.ngrid.ru:8443/wsrf/services/ManagedJobFactoryService"
          ],
          "GridFTP": [
            "gsiftp://tb13.ngrid.ru:2811"
          ],
          "RFT": [
            "https://tb13.ngrid.ru:8443/wsrf/services/ReliableFileTransferFactoryService"
          ]
        }
      },
      "Web": "http://www.ngrid.ru/",
      "Name": "sinp_mpi",
      "OtherInfo": [
        ""
      ],
      "Longitude": 0.0,
      "Cluster": [
        {
          "TmpDir": "",
          "WNTmpDir": "/tmp",
          "Name": "sinp_mpi-cluster",
          "SubCluster": [
            {
              "Name": "tb13.ngrid.ru/subcluster0",
              "PhysicalCPUs": 16,
              "LogicalCPUs": 384,
              "Queue": [
                {
                  "FreeSlots": 384,
                  "MaxWallTime": 600,
                  "ServingState": "production",
                  "StagingJobs": 0,
                  "TotalJobs": 0,
                  "WaitingJobs": 0,
                  "ACL": {
                    "Rule": [
                      "VOMS:/gridnnn",
                      "VOMS:/sysadmin",
                      "VOMS:/abinit",
                      "VOMS:/education",
                      "VOMS:/nanochem"
                    ]
                  },
                  "RunningJobs": 0,
                  "LRMSType": "pbs",
                  "UsedSlots": 0,
                  "CEInfo": "tb13.ngrid.ru/batch"
                }
              ],
              "Host": [
                {
                  "RunTimeEnv": [
                    ""
                  ],
                  "OperatingSystem": {
                    "Release": "5.6",
                    "Version": "Final",
                    "Name": "CentOS"
                  },
                  "Architecture": {
                    "SMPSize": 16,
                    "PlatformType": "x86_64"
                  },
                  "UniqueID": "tb13.ngrid.ru/host",
                  "MainMemory": {
                    "RAMSize": 16041,
                    "VirtualSize": 16384
                  },
                  "Processor": {
                    "ClockSpeed": 2400,
                    "Model": "E5620",
                    "Vendor": "Intel Xeon",
                    "InstructionSet": "x86_64"
                  }
                }
              ],
              "UniqueID": "tb13.ngrid.ru/subcluster0",
              "PhysicalSlots": 16,
              "WNTmpDir": "/tmp",
              "TmpDir": "",
              "Software": [
                {
                  "InstalledRoot": "/shared/abinit-6.4.3-openmpi",
                  "Version": "6.4.3",
                  "Name": "abinit",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+abinit-6.4.3-gfortran44-openmpi"
                    }
                  ],
                  "LocalID": "abinit-6.4.3"
                },
                {
                  "InstalledRoot": "/shared/itmo",
                  "Version": "0.0.0",
                  "Name": "extmodel",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+extmodel"
                    }
                  ],
                  "LocalID": "extmodel"
                },
                {
                  "InstalledRoot": "/shared/itmo",
                  "Version": "0.0.0",
                  "Name": "extspread",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+extspread"
                    }
                  ],
                  "LocalID": "extspread"
                },
                {
                  "ModuleName": "abinit",
                  "Name": "abinit",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+abinit-6.6"
                    }
                  ],
                  "LocalID": "abinit-6.6",
                  "ACL": {
                    "Rule": [
                      "VOMS:/abinit"
                    ]
                  },
                  "Version": "6.6",
                  "InstalledRoot": "/shared/abinit/6.6/bin/"
                },
                {
                  "ModuleName": "lmp",
                  "Name": "lammps",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+lammps-25sep11"
                    }
                  ],
                  "LocalID": "lammps-25Sep11",
                  "ACL": {
                    "Rule": [
                      "VOMS:/sysadmin",
                      "VOMS:/gridnnn",
                      "VOMS:/education",
                      "VOMS:/abinit"
                    ]
                  },
                  "Version": "25Sep11",
                  "InstalledRoot": "/shared/lammps"
                },
                {
                  "Name": "gromacs",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+gromacs-4.5.5-mpi"
                    }
                  ],
                  "LocalID": "gromacs-4.5.5-mpi",
                  "ACL": {
                    "Rule": [
                      "VOMS:/sysadmin",
                      "VOMS:/gridnnn"
                    ]
                  },
                  "Version": "4.5.5",
                  "InstalledRoot": "/shared/gromacs/"
                },
                {
                  "Name": "openmx",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+openmx3.5-mpi"
                    }
                  ],
                  "LocalID": "openmx3.5-mpi",
                  "ACL": {
                    "Rule": [
                      "VOMS:/sysadmin",
                      "VOMS:/gridnnn"
                    ]
                  },
                  "Version": "3.5",
                  "InstalledRoot": "/shared/openmx/"
                },
                {
                  "InstalledRoot": "/shared/tesis/FlowVision3.08",
                  "Version": "3.08.01",
                  "Name": "FlowVision",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+flowvision"
                    }
                  ],
                  "LocalID": "FlowVision-3.08.01"
                },
                {
                  "ModuleName": "",
                  "Name": "gamess",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+gamess2010R3"
                    }
                  ],
                  "LocalID": "Gamess2010R3",
                  "ACL": {
                    "Rule": [
                      "VOMS:/sysadmin",
                      "VOMS:/gridnnn",
                      "VOMS:/nanochem"
                    ]
                  },
                  "Version": "2010R3",
                  "InstalledRoot": "/shared/gamess/"
                },
                {
                  "Name": "namd",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+namd-2.8"
                    }
                  ],
                  "LocalID": "namd-2.8",
                  "ACL": {
                    "Rule": [
                      "VOMS:/gridnnn",
                      "VOMS:/sysadmin"
                    ]
                  },
                  "Version": "2.8",
                  "InstalledRoot": "/shared/namd/NAMD_2.8_Source/Linux-x86_64-g++"
                },
                {
                  "Name": "openfoam",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+openfoam-2.0.1"
                    },
                    {
                      "profile": "openmpi"
                    }
                  ],
                  "LocalID": "openfoam-2.0.1",
                  "ACL": {
                    "Rule": [
                      "VOMS:/openfoam",
                      "VOMS:/gridnnn"
                    ]
                  },
                  "Version": "2.0.1",
                  "InstalledRoot": "/shared/openfoam"
                },
                {
                  "Name": "fdtd-ii",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+fdtd-ii-1.9.0"
                    },
                    {
                      "profile": "mpich2"
                    }
                  ],
                  "LocalID": "fdtd-ii-1.9.0",
                  "ACL": {
                    "Rule": [
                      "VOMS:/fdtd",
                      "VOMS:/gridnnn"
                    ]
                  },
                  "Version": "1.9.0",
                  "InstalledRoot": "/shared/fdtd-ii"
                },
                {
                  "Name": "firefly",
                  "EnvironmentSetup": [
                    {
                      "softenv": "+firefly-7.1g"
                    },
                    {
                      "profile": "mpich2"
                    }
                  ],
                  "LocalID": "firefly-7.1g",
                  "ACL": {
                    "Rule": [
                      "VOMS:/firefly",
                      "VOMS:/gridnnn"
                    ]
                  },
                  "Version": "7.1g",
                  "InstalledRoot": "/shared/firefly/ff71g"
                }
              ]
            }
          ],
          "UniqueID": "tb13.ngrid.ru"
        }
      ],
      "SysAdminContact": "mailto: shamardin@theory.sinp.msu.ru",
      "Location": "Moscow, Russia",
      "UniqueID": "tb13.ngrid.ru",
      "Latitude": 0.0,
      "UserSupportContact": "mailto: shamardin@theory.sinp.msu.ru",
      "SecurityContact": "mailto: shamardin@theory.sinp.msu.ru",
      "Description": "SINP MSU MPI"
    },
    "Validity": 30
  }
]
