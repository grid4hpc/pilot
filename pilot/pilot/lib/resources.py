# -*- encoding: utf-8 -*-

import cPickle as pickle
import random
import re
import types
from urllib import urlencode, quote, unquote
from urlparse import urljoin, urlsplit, urlunsplit

from gridproxy.voms import VOMS, VOMSError

from pilot.lib import certlib, json
from pilot_cli import formats

class ResourcesError(RuntimeError): pass


class TimeoutResourcesError(ResourcesError):
    def __init__(self):
        ResourcesError.__init__(self, "request timed out")


class NoResourcesError(ResourcesError):
    def __init__(self):
        ResourcesError.__init__(self, "No compatible resources were found.")


class MatchmakerResourcesError(ResourcesError):
    def __init__(self, code, result):
        ResourcesError.__init__(self,
                                "matchmaker returned HTTP Error %d: %s" % \
                                (code, result))

class RSLResourcesError(ResourcesError):
    def __init__(self, code, result):
        ResourcesError.__init__(self,
                                "matchmaker/rsl returned HTTP Error %d: %s" % \
                                (code, result))


config = {
    'voms_dir': "/etc/grid-security/vomsdir",
    'capath': "/etc/grid-security/certificates",
    'baseurl': "http://localhost:5054/",
    'httplib': __import__("httplib"),
    'timeout': 30,
}


def http_query(method, uri, body=None, timeout=None):
    httplib = config["httplib"]
    _, netloc, path, query, fragment = urlsplit(uri)
    if ':' in netloc:
        host, port = netloc.split(":", 1)
    else:
        host, port = netloc, 80

    rel_uri = urlunsplit(('', '', path, query, fragment))
    
    try:
        conn = httplib.HTTPConnection(host, port)
        conn.connect()
        if timeout is None:
            conn.sock.settimeout(config['timeout'])
        else:
            conn.sock.settimeout(timeout)
        conn.request(method, rel_uri, body, { "User-Agent": "pilot" })
        resp = conn.getresponse()
        result = resp.read()
        code = resp.status
        conn.close()
    except httplib.socket.timeout, exc:
        raise TimeoutResourcesError()
    except Exception, exc:
        code = 500
        result = "%s: %s" % (repr(exc), str(exc))

    return code, result


def query_matchmaker(requirements, fqans, timeout=None):
    query = [("requirements", json.dumps(requirements))] + \
            [("fqan", fqan) for fqan in fqans]
    uri = urljoin(config['baseurl'], "matchmaker")
    uri += "?" + urlencode(query)

    code, result = http_query("GET", uri, None, timeout)

    if code != 200:
        raise MatchmakerResourcesError(code, result)

    return pickle.loads(result)


def list_resources(timeout=None):
    uri = urljoin(config['baseurl'], "matchmaker/resources")
    code, result = http_query("GET", uri, None, timeout)

    if code != 200:
        raise MatchmakerResourcesError(code, result)

    return pickle.loads(result)


def matchmake(taskdef, jobdef, fqans, timeout=None):
    """
    Получить список ресурсов, удовлетворяющих задаче.

    Возвращает таплы realm, hostname, port, lrms_type, queue в порядке приоритета.
    """
    
    requirements = dict()
    requirements.update(jobdef.get('requirements', {}))
    requirements.update(taskdef.get('requirements', {}))
    matching_resources = query_matchmaker(requirements, fqans, timeout)
    resources = matching_resources.keys()
    random.shuffle(resources)
    return resources


def find_resources_single(task, timeout=None):
    u"""
    Найти подходящие ресурсы только для данной задачи (игнорируя группы).
    task: задача из базы данных (models.Task)
    
    @returns: список из tuple(hostname, queue, lrms_type)
    """
    voms = VOMS(config['voms_dir'], config['capath'])
    try:
        certlib.load_voms_chain(voms, task.job.delegation.chain)
    except VOMSError, exc:
        raise ResourcesError("Error loading VOMS attributes: %s" % str(exc))
    
    resources = matchmake(task.definition, task.job.definition,
                          voms.fqans, timeout)
    if len(resources) == 0:
        raise NoResourcesError()
    
    return resources


def find_resources(task, timeout=None):
    u"""
    Найти подходящие для задачи ресурсы. В том случае, если задача
    является частью группы, будет выполнен поиск ресурсов для всех
    задач группы.  Если какая-то из задач группы уже 'привязана' к
    конкретному ресурсу (например, выполняется на на нем, то остальные
    задачи из группы будут посылаться на тот же ресурс.

    Ресурсом в данном случае считается пара (hostname, lrms_type)
    
    - task: задача из базы данных (models.Task)

    - timeout: таймаут на одну (!) операцию matchmake, полный поиск
      ресурсов может занять больше времени, в зависимости от числа
      задач в группе.
    
    @returns: список из tuple(hostname, lrms_type, queue)
    """

    group = task.task_group()
    if len(group) == 1:
        return find_resources_single(task, timeout)
    
    original_task = task

    destinations = []
        
    # 1. Найти подходящий список ресурсов для каждой задачи
    for task in group:
        # если какая-то из задач уже где-то выполняется, то остальные
        # задачи должны попасть на этот же ресурс.
        if 'running_at' in task.meta:
            r, h, p, l, q = task.meta['running_at']
            destinations.append(set([(h, l)]))

        # если идет процесс generate_rsl, и одна из задач куда-то уже
        # привязана, то отсльаные должны попасть туда же
        if 'rsl_at' in task.meta:
            r, h, p, l, q = task.meta['rsl_at']
            destinations.append(set([(h, l)]))

        # если у задачи нет ресурсов, найти их
        if 'resources' not in task.meta:
            task.meta['resources'] = find_resources_single(task, timeout)
            
        destinations.append(set((h, l) for (r, h, p, l, q) in task.meta['resources']))

    possible_destinations = reduce(set.intersection, destinations)    
    if len(possible_destinations) == 0:
        raise NoResourcesError()

    for task in group:
        new_resources = []
        for r, h, p, l, q in task.meta['resources']:
            if (h, l) in possible_destinations:
                new_resources.append((r, h, p, l, q))
        task.meta['resources'] = new_resources

    return original_task.meta['resources']

def generate_rsl(task, target, timeout=None):
    u"""
    task: задача из базы данных (models.Task)
    target: строка-имя ресурса, либо (realm, hostname, port, lrms, queue)
    timeout: таймаут в секундах

    @returns: ISubmissionParameters
    """

    if target in types.StringTypes:
        target = parse_resource_name(target)
    
    uri = urljoin(config['baseurl'], "matchmaker/rsl")
    
    substitutions = {
        "jobid": task.job.jid,
        "taskid": task.name,
        "lrms_host": target[1],
        "lrms_port": str(target[2]),
        "lrms": target[3],
        "queue": target[4],
        }
    
    taskdef = formats.substitute_params(task.definition, substitutions)
    jobdef = formats.substitute_params(task.job.definition, substitutions)
    
    code, result = http_query("PUT", uri,
                              pickle.dumps((taskdef, jobdef, target)),
                              timeout)

    if code != 200:
        raise RSLResourcesError(code, result)

    result = pickle.loads(result)
    if result[0] != 'ok':
        raise RSLResourcesError(500,
                                "%s: %s" % (repr(result[1]), str(result[1])))

    return result[1]

def resource_name(realm, host, port, lrms, queue):
    u"""
    Вовзращает имя ресурса, в формате realm@host[:port]/lrms[/queue]
    """
    name = "%s@%s" % (realm, quote(host, ''))
    if port is not None:
        name += ":%s" % port
    name += "/" + quote(lrms, '')
    if queue is not None:
        name += "/" + quote(queue, '')
    return name

def parse_resource_name(name):
    u"""
    Возвращает realm, host, port, lrms, queue, полученные из имени ресурса
    port и queue могуть быть None, если отстутсвуют в имени ресурса.
    """
    realm, rest = name.split('@', 1)
    hostport, rest = rest.split('/', 1)
    if ':' in hostport:
        host, port = hostport.split(':', 1)
        port = int(port)
    else:
        host = hostport
        port = None

    if '/' in rest:
        lrms, queue = rest.split('/', 1)
    else:
        lrms = rest
        queue = None

    host = unquote(host)
    lrms = unquote(lrms)
    if queue: queue = unquote(queue)

    return realm, host, port, lrms, queue
    
