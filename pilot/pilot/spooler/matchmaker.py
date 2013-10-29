# -*- encoding: utf-8 -*- 
import copy
import logging, re, cgi
import types
from distutils.version import LooseVersion
import eventlet
from eventlet.green.time import time
from eventlet.green.urllib2 import urlopen, Request, HTTPError
from eventlet.green import urllib

import cPickle as pickle

from wsmds import MDSInfoProvider, RegMDSInfoProvider
import pilot.spooler
from pilot.api import *
from pilot.spooler import wsgi, config, grid, write_traceback
from pilot.lib import json, resources
from pilot.lib import helpers as h

log = logging.getLogger(__name__)


class MMError(RuntimeError):
    pass


class RequirementMatcher(object):
    operation_re = re.compile("(<=?|>=?|==|!=)")
    cmp_table = {
        '<=': (True, False, True),
        '<' : (False, False, True),
        '==': (True, False, False),
        '>' : (False, True, False),
        '>=': (True, True, False),
        '!=': (False, True, True)
        }
    def __init__(self, requirement):
        parts = self.operation_re.split(requirement, 1)
        if len(parts) == 1:
            self.name = parts[0].strip()
            self.version = None
        else:
            self.name = parts[0].strip()
            self.version = LooseVersion(parts[2].strip())
            self.compare = self.cmp_table[parts[1]]

    def match(self, name, version):
        if name != self.name:
            return False
        if self.version is None:
            return True
        else:
            if version is None:
                return False
            else:
                cmp_result = self.compare[cmp(version, self.version)]
                return cmp_result


class SoftwareMatcher(object):
    def __init__(self, requirements):
        self.requirements = requirements
        self.matchers = {}
        for req in (x.strip() for x in requirements.split(',')):
            self.matchers[req] = RequirementMatcher(req)

    def __str__(self):
        return "software has [%s]" % self.requirements

    def matching_software(self, software):
        matches = {}
        unmatched = list(self.matchers.keys())
        for sw in software:
            for i, req in enumerate(unmatched):
                if self.matchers[req].match(sw.name, sw.version):
                    unmatched.pop(i)
                    matches[req] = sw
                    break
        return matches            

    def match(self, software):
        if len(software) == 0 and len(self.matchers) > 0:
            return False
        if len(self.matchers) == 0:
            return True
        matches = self.matching_software(software)
        return len(matches) == len(self.matchers)


def normalize_fqan(fqan):
    u"""Возвращает FQAN без Role=NULL и/или Capability=NULL"""
    return '/'.join(
        filter(lambda part: part not in ("Role=NULL", "Capability=NULL"),
               fqan.split('/')))

def wildcard_re(wildcard):
    return '^' + re.escape(wildcard).replace(r'\*', '.*').replace(r'\?', '.') + '$'
    

class Matchmaker(object):
    string_match_attributes = ['os_name', 'os_release',
                               'os_version', 'platform', 'cpu_instruction_set']
    int_match_attributes = ['smp_size', 'ram_size', 'virtual_size', 'cpu_hz']
    other_attributes = ['hostname', 'lrms', 'fork', 'queue', 'software']
    known_attributes = string_match_attributes + int_match_attributes + other_attributes
    def __init__(self):
        self.resources = {}
        self.host_allowed = lambda hostname: False
        self.last_update = 0
        self.refresh_in_progress = eventlet.semaphore.Semaphore(1)

        self.load_allowed_hosts()
        self.load()

    def load_patterns(self, option):
        parts = []
        match_all = type('match_all', tuple(), {'match': None})()
        match_all.match = lambda name, *args, **kwargs: True

        value = config.get(u"matchmaker_" + option, None)
        if value is None:
            return match_all

        for pattern in (x.strip() for x in value.split(',')):
            result = pattern
            if '^' not in pattern:
                result = '^' + result
            if '$' not in pattern:
                result = result + '$'
            try:
                re.compile(result, re.I)
                parts.append(result)
            except re.error:
                raise ValueError('Invalid pattern for matchmaker.%s: %s' % (option, pattern))

        return re.compile('|'.join('(' + part + ')' for part in parts), re.I)

    def load_allowed_hosts(self):
        allow_pattern = self.load_patterns('allowed_hosts')
        deny_pattern = self.load_patterns('denied_hosts')

        allow_first = False
        order = config.matchmaker_order.lower()
        if 'deny' not in order or 'allow' not in order:
            raise ValueError('Matchmaker requires matchmaker.order to be in format "deny, allow" or "allow, deny"')
        if order.find('allow') < order.find('deny'):
            allow_first = True

        if allow_first:
            def host_allowed(hostname):
                allow = False
                if allow_pattern.match(hostname) is not None:
                    allow = True
                if deny_pattern.match(hostname) is not None:
                    allow = False
                return allow
            self.host_allowed = host_allowed
        else:
            def host_allowed(hostname):
                allow = False
                if deny_pattern.match(hostname) is not None:
                    allow = False
                if allow_pattern.match(hostname) is not None:
                    allow = True
                return allow
            self.host_allowed = host_allowed

    def refresh(self, force=True):
        log.debug("taking refresh lock")
        try:
            self.refresh_in_progress.acquire()
            log.debug("got refresh lock")
            if force or self.cache_expired():
                try:
                    new_resources = {}
                    for realm in grid.realms():
                        provider = grid.info_provider(realm)
                        if ICachingResourceEnumerator.providedBy(provider):
                            if provider.stale():
                                provider.refresh()
                        for resource in provider.enumerate():
                            new_resources[(realm,
                                           resource.hostname,
                                           resource.port,
                                           resource.lrms,
                                           resource.queue)] = resource
                    self.resources = new_resources
                except Exception, exc:
                    log.debug("Matchmaker refresh failed, working with old data (if any)")
                    log.debug("Exception: %s: %s", repr(exc), str(exc))
                    write_traceback()
                    return
                self.last_update = time()
            else:
                log.debug("refresh not required.")
            self.save()
        finally:
            self.refresh_in_progress.release()
            log.debug("refresh lock released")

    def save(self):
        log.debug("Saving resource information to %s", config.dump_filename)
        data = { 'resources': self.resources,
                 'last_update': self.last_update,
                 'realms': grid.realms(),
               }
        fd = open(config.dump_filename, 'wb')
        pickle.dump(data, fd)
        fd.close()

    def load(self):
        log.debug("Loading resource information from %s", config.dump_filename)
        try:
            fd = open(config.dump_filename, 'rb')
            data = pickle.load(fd)
            fd.close()
            if data['realms'] != grid.realms():
                log.warning("Ignoring matchmaker cache: realms set has changed.")
                return
            self.resources = data['resources']
            self.last_update = data['last_update']
        except TypeError:
            log.warning("Ignoring old matchmaker cache format")
        except IOError:
            log.debug("Load failed")

    def cache_expired(self):
        return (time() - self.last_update) > config.matchmaker_cache_ttl

    def validate_requirements(self, requirements):
        for key in requirements.keys():
            if key not in self.known_attributes:
                raise ValueError("Unknown attribute '%s' in requirements" % key)

    def matchmake(self, requirements, fqans=None):
        u"""Возвращает список ComputingElement'ов, удовлетворяющий набору
        требований.

        @param requirements: список требований
        """
        self.validate_requirements(requirements)

        if self.cache_expired():
            self.refresh(False)
        results = []

        if fqans is None:
            fqans = []
        fqans = [normalize_fqan(fqan) for fqan in fqans]

        if requirements.get('fork', False):
            requirements.pop('fork')
            requirements['lrms'] = 'Fork'

        software_matcher = None
        if 'software' in requirements:
            software_matcher = SoftwareMatcher(requirements['software'])


        matches = {}

        class Incompatible(Exception): pass

        for (realm, _, _, _, _), resource in self.resources.iteritems():
            try:
                if not resource.access_allowed(fqans): raise Incompatible
                
                if resource.hostname not in requirements.get('hostname', [resource.hostname]):
                    raise Incompatible
                
                for attribute in ('lrms', 'queue'):
                    value = getattr(resource, attribute)
                    if requirements.get(attribute, value) != value:
                        raise Incompatible

                for attribute in ('os_name', 'os_release', 'os_version', 'platform', 'cpu_instruction_set'):
                    value = getattr(resource.config, attribute)
                    req = requirements.get(attribute, None)

                    if req is None: continue
                    if value is None: raise Incompatible

                    expr = wildcard_re(req)
                    if expr.match(value) is None: raise Incompatible

                for attribute in ('smp_size', 'ram_size', 'virtual_size', 'cpu_hz'):
                    value = getattr(resource.config, attribute)
                    req = requirements.get(attribute, value)

                    if req < value: raise Incompatible

                if software_matcher is not None:
                    if not software_matcher.match(resource.software):
                        raise Incompatible

                matches[(realm, resource.hostname, resource.port, resource.lrms, resource.queue)] = resource

            except Incompatible:
                continue

        return matches

    def wsgi_matchmake(self, environ, start_response):
        qs = cgi.parse_qs(environ.get('QUERY_STRING', ''))
        requirements = qs.get('requirements', [None])[0]
        fqans = qs.get('fqan', [])

        if requirements is None:
            if self.cache_expired():
                self.refresh(False)
            rc = pickle.dumps(self.resources)
        else:
            try:
                reqs = json.loads(requirements)
                results = self.matchmake(reqs, fqans)
                rc = pickle.dumps(results)
            except ValueError, e:
                raise MMError(str(e))
            except Exception, e:
                import traceback
                log.error("oops? %s: %s", str(e), traceback.format_exc())
                raise MMError(traceback.format_exc())
        
        start_response('200 OK', [('Content-Type', 'application/octet-stream')])
        return rc

    def wsgi_dump_resources(self, environ, start_response):
        if self.cache_expired():
            self.refresh(False)
        start_response('200 OK', [('Content-Type', 'application/octet-stream')])
        return pickle.dumps(self.resources)

    def add_software_extensions(self, taskdef, software, hostname, queue):
        new_taskdef = copy.deepcopy(taskdef)
        matcher = SoftwareMatcher(software)
        if (hostname, queue) not in self.resources:
            log.warning("Called add_software_extensions for unknown resource: %s-%s", hostname, queue)
            return new_taskdef
        resource = self.resources[(hostname, queue)]

        if 'extensions' not in new_taskdef:
            new_taskdef['extensions'] = {}

        sw = matcher.matching_software(resource)
        ext = new_taskdef['extensions']
        for (name, version, meta) in sw.itervalues():
            log.debug("adding sw package %s, extensions: %s", name, meta)
            for k, v in meta['extensions'].iteritems():
                if k not in ext:
                    ext[k] = v
                else:
                    if type(ext[k]) in types.StringTypes:
                        ext[k] = [ext[k], v]
                    else:
                        ext[k].append(v)                

        log.debug("final task definition: %s", new_taskdef)
        return new_taskdef

    def wsgi_generate_rsl(self, environ, start_response):
        try:
            taskdef, jobdef, target = pickle.load(environ['wsgi.input'])
        except Exception, exc:
            raise MMError("Failed to load data: %s" % str(exc))

        for attr in ("default_storage_base", "max_transfer_attempts"):
            if attr in jobdef:
                taskdef.setdefault(attr, jobdef[attr])

        resource = self.resources.get(target)
        if resource is None:
            log.warning("wsgi_generate_rsl called for unknown resource: %s", target)
            result = 'failed', RuntimeError("unknown resource: %s", target)

        requirements = merged_requirements(taskdef, jobdef)
        if 'software' in requirements and resource:
            software_matcher = SoftwareMatcher(requirements['software'])
            for sw in software_matcher.matching_software(resource.software).itervalues():
                sw.activate(taskdef)

        if resource:
            try:
                params = grid.executor(target[0]).get_submission_parameters(taskdef, resource)
                result = 'ok', params
                log.debug("wsgi_generate_rsl result: %s", params)
            except grid.RealmNotFoundError, exc:
                result = 'failed', str(exc)
            except ValueError, exc:
                result = 'failed', exc
        
        start_response('200 OK', [('Content-Type', 'application/octet-stream')])
        return pickle.dumps(result)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO'].split('/')[1:]
        try:
            if path[0] == '':
                return self.wsgi_matchmake(environ, start_response)
            elif path[0] == 'rsl' and environ['REQUEST_METHOD'] == 'PUT':
                return self.wsgi_generate_rsl(environ, start_response)
            elif path[0] == 'resources':
                return self.wsgi_dump_resources(environ, start_response)
        except MMError, exc:
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return str(exc)

        raise wsgi.Error404()


def merged_requirements(taskdef, jobdef):
    u"""
    Получить суммарные требования задачи, с учетом требований задания
    @param taskdef: описание задачи
    @param jobdef: описание задания
    
    @returns dict, содержащий требования
    """
    requirements = jobdef.get('requirements', {}).copy()
    requirements.update(taskdef.get('requirements', {}))
    return requirements
