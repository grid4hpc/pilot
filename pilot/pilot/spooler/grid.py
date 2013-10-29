# -*- encoding: utf-8 -*-

import logging
import sys

from pilot.api import *
from pilot.spooler import config, comm

log = logging.getLogger(__name__)
_grid_config = {}

def configure():
    if 'common_realms' not in config:
        log.fatal("No realms configured for loading.")
        sys.exit(1)

    for realm in [r.strip() for r in config['common_realms'].split(",")]:
        if '(' in realm:
            module_name, instance_name = realm.split("(", 1)
            instance_name = instance_name.strip("()")
        else:
            module_name = realm
            instance_name = realm.split(".")[-1]

        pilot_module = "pilot.spooler.realm.%s" % module_name

        try:
            __import__(pilot_module)
            module = sys.modules[pilot_module]
        except ImportError:
            try:
                __import__(module_name)
                module = sys.modules[module_name]
            except ImportError:
                log.fatal("Can't load %s: no module %s or %s could be imported.",
                          module_name, pilot_module, module_name)
                sys.exit(1)
                
        try:
            realm_config = dict(module.config)
            for realm_key in module.config:
                config_key = instance_name + "_" + realm_key
                if config_key in config:
                    realm_config[realm_key] = config[config_key]

            _grid_config[instance_name] = module.load(realm_config)
        except RuntimeError, exc:
            log.fatal("Failed to load realm %s: %s", realm, str(exc))
            sys.exit(1)

        log.info("Loaded realm: %s", realm)
    
    fetcher = comm.EventletFetcher(comm.SSLFetcher(
        cert=config['common_ssl_certificate'],
        key=config['common_ssl_privatekey'],
        capath=config['common_ssl_capath']))

    for realm in realms():
        provider = info_provider(realm)
        provider.timeout = 10
        
        if IHTTPConsumer.providedBy(provider):
            provider.fetch_url = fetcher.fetch_url

class RealmNotFoundError(RuntimeError):
    def __init__(self, realm):
        RuntimeError.__init__(self, u"Tasks realm '%s' is not configured" % realm)

def realms():
    return _grid_config.keys()

def info_provider(realm):
    if realm in _grid_config:
        return _grid_config[realm][0]
    else:
        raise RealmNotFoundError(realm)

def executor(realm):
    if realm in _grid_config:
        return _grid_config[realm][1]
    else:
        raise RealmNotFoundError(realm)
