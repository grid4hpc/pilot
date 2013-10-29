# -*- encoding: utf-8 -*-

from zope.interface import implements
from pilot.api import *

from distutils.version import LooseVersion
import logging
import time

from pilot.lib import json
from pilot.spooler.gridnnn import GridnnnResource
from eventlet.green import os

def make_resource(cluster, subcluster, queue):
    u"""Делает GridnnnResource из пачки информации из infosys.
    В случае неудачи (отсутствия нужных элементов) выкидывает KeyError
    """
    host = subcluster['Host'][0]
    if 'Rule' in queue.get('ACL', {}):
        acls = queue['ACL']['Rule']
    else:
        acls = []

    software = []
    for pkg in subcluster.get('Software', []):
        print (
            pkg['Name'],
            LooseVersion(pkg['Version']),
            {'extensions': pkg.get("EnvironmentSetup", [{}])[0]},
            )
        software.append((
            pkg['Name'],
            LooseVersion(pkg['Version']),
            {'extensions': pkg.get("EnvironmentSetup", [{}])[0]},
            ))


    info = {
        # GridnnnResource
        'hostname': cluster['UniqueID'],
        'lrms_type': queue['LRMSType'],
        'queue': queue['CEInfo'].split('/', 1)[1],
        'acls': acls, 
        # GridnnnResourceConfig
        'os_name': host['OperatingSystem']['Name'],
        'os_release': host['OperatingSystem']['Release'],
        'os_version': host['OperatingSystem']['Version'],
        'platform': host['Architecture']['PlatformType'],
        'smp_size': host['Architecture']['SMPSize'],
        'cpu_hz': host['Processor']['ClockSpeed'],
        'cpu_instruction_set': host['Processor']['InstructionSet'],
        'cpu_model': host['Processor']['Model'],
        'physical_slots': subcluster['PhysicalSlots'],
        'physical_cpus': subcluster['PhysicalCPUs'],
        'logical_cpus': subcluster['LogicalCPUs'],
        'ram_size': host['MainMemory']['RAMSize'],
        'virtual_size': host['MainMemory']['VirtualSize'],
        # GridnnnResourceSoftware
        'software': software,
        # GridnnnResourceState
        'running_jobs': queue.get('RunningJobs', None),
        'total_jobs': queue.get('TotalJobs', None),
        'waiting_jobs': queue.get('WaitingJobs', None),
        'enabled': queue.get('ServingState', None) == "production",
    }

    return GridnnnResource(info)


class BaseInfosys2InfoProvider(object):
    implements(ICachingResourceEnumerator)

    def __init__(self, ttl):
        u"""
        Параметры:

        ttl: время кеширования информации о ресурсах
        """
        self.timeout = None
        self.last_update = 0
        self.ttl = ttl

        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        self._resources = []

    def get_content(self):
        u"""
        Загрузить откуда-либо данные о ресурсах в формате Infosys2 Hub (JSON)
        """
        raise NotImplementedError

    # IResouceEnumerator

    def enumerate(self):
        return self._resources

    # ICachingResourceEnumerator

    def stale(self):
        if time.time() - self.last_update > self.ttl:
            return True
        return False

    def refresh(self):
        try:
            self.log.debug("refresh started")
            now = time.time()
            content = self.get_content()
            if content is None:
                self.log.error("no infosys2 content returned")

            data = json.loads(content)
            resources = []
            for entry in data:
                if 'Site' not in entry or not hasattr(entry['Site'], 'get'):
                    self.log.warning("Ignoring unknown infosys2 object")
                    continue
                site = entry['Site']
                site_name = site.get("Name", "(site name not set)")
                try:
                    self.log.info("looking at site %s", site_name)
                    for cluster in site.get('Cluster', []):
                        self.log.info("looking at cluster %s", cluster['Name'])
                        for subcluster in cluster.get('SubCluster', []):
                            self.log.info("looking at subcluster %s", subcluster['Name'])
                            for queue in subcluster.get('Queue', []):
                                try:
                                    resources.append(make_resource(cluster,
                                                                   subcluster,
                                                                   queue))
                                except KeyError, exc:
                                    self.log.warning("Failed to parse element %s in "
                                                     "Infosys2 content for site "
                                                     "%s" % (exc, site_name))
                except Exception, exc:
                    self.log.warning("Failed to parse site %s, ignoring: %s", site_name, str(exc))

            self.last_update = now
            self._resources = resources
        finally:
            self.log.debug("refresh finished")


class Infosys2InfoProvider(BaseInfosys2InfoProvider):
    implements(IHTTPConsumer)

    def __init__(self,
                 infosys2_url,
                 ttl=600):
        u"""
        Параметры:

        infosys2_url: url для сервиса Infosys2
        ttl: время кеширования информации о ресурсах
        """
        BaseInfosys2InfoProvider.__init__(self, ttl)
        self.fetch_url = None
        self.url = infosys2_url

    def get_content(self):        
        self.log.debug("querying Infosys2 service at %s", self.url)
        content, status, headers = self.fetch_url(self.url)
        if status >= 400:
            self.log.warning("query failed with error %d" % status)
            return None

        return content


class StaticInfosys2InfoProvider(BaseInfosys2InfoProvider):
    def __init__(self,
                 filename):
        u"""
        Параметры:

        filename: путь к файлу со статической информацией о ресурсах
        ttl: время кеширования информации о ресурсах
        """
        BaseInfosys2InfoProvider.__init__(self, 0)
        self.filename = filename
        self.mtime = None

    def get_content(self):
        try:
            self.mtime = os.stat(self.filename).st_mtime
            return open(self.filename).read()
        except (IOError, OSError):
            return None

    # ICachingResourceEnumerator

    def stale(self):
        if self.mtime is None:
            return True
        
        try:
            mtime = os.stat(self.filename).st_mtime
        except OSError:
            mtime = None

        if self.mtime == mtime:
            return False

        return True

