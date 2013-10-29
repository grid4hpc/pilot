# -*- encoding: utf-8 -*-

u"""
Ресурс ГридННС. Используется gws, gt5 в конфигурации с ГридННС. В
качестве информационной системы могут выступать WS-MDS или Infosys2.
"""

from zope.interface import implements
from pilot.api import *

from distutils.version import LooseVersion
import types

class GridnnnResource(object):
    implements(IResource)

    def __init__(self, chewed_dict):
        self.hostname = chewed_dict['hostname']
        self.port = 8443
        self.lrms = chewed_dict['lrms_type']
        self.queue = chewed_dict['queue']
        self.version = None
        self.config = GridnnnResourceConfig(chewed_dict)
        self.software = [GridnnnResourceSoftware(*sw) for sw in chewed_dict['software']]
        self.state = GridnnnResourceState(chewed_dict)

        self._fqans = set()

        for acl in chewed_dict['acls']:
            if acl.startswith("VOMS:"):
                self._fqans.add(acl.split(':', 1)[1])

    # IResource
    
    def access_allowed(self, fqans):
        return len(set(fqans) & self._fqans) != 0

    # other methods

    def __repr__(self):
        return "Resource(%s-%s-%s, state=%s, sw=%s)" % \
               (self.hostname, self.lrms, self.queue, self.state,
                self.software)

    def get_acls(self):
        return sorted(list(self._fqans))

class GridnnnResourceConfig(object):
    implements(IResourceConfiguration)

    def __init__(self, chewed_dict):
        for attr in ('os_name', 'os_release', 'os_version', 'platform',
                     'smp_size', 'cpu_hz', 'cpu_instruction_set', 'cpu_model',
                     'physical_slots', 'physical_cpus', 'logical_cpus',
                     'ram_size', 'virtual_size'):
            setattr(self, attr, chewed_dict.get(attr, None))

class GridnnnResourceSoftware(object):
    implements(IResourceSoftware)

    def __init__(self, name, version, meta):
        self.name = name
        self.version = version
        self._ext = meta.get('extensions', {})

    def activate(self, task_definition):
        if 'extensions' not in task_definition:
            task_definition['extensions'] = {}
        ext = task_definition['extensions']
        for k, v in self._ext.iteritems():
            if k not in ext:
                ext[k] = v
            else:
                if type(ext[k]) in types.StringTypes:
                    ext[k] = [ext[k], v]
                else:
                    ext[k].append(v)

    def __repr__(self):
        return "Software(%s, %s)" % (self.name, self.version.vstring)

class GridnnnResourceState(object):
    implements(IResourceState)

    def __init__(self, chewed_dict):
        for attr in ('total_cpus', 'free_cpus', 'running_jobs', 'total_jobs',
                     'waiting_jobs', 'enabled'):
            setattr(self, attr, chewed_dict.get(attr, None))

    def __repr__(self):
        return "State(%s/%s free)" % (self.free_cpus, self.total_cpus)
