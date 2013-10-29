# -*- encoding: utf-8 -*-

import datetime
import grp
import logging
import os
import pwd
import re
import traceback
import types
from ConfigParser import SafeConfigParser
from cStringIO import StringIO

import eventlet
import eventlet.greenpool
os.environ['EVENTLET_THREADPOOL_SIZE'] = '100'
import eventlet.tpool

from pilot.lib.storage import storage

matchmaker_port = 5054
config = storage({
    "pidfile": "/var/run/pilot-spooler.pid",
    "logfile": "/var/log/pilot-spooler.log",
    "debug_level": 1,
    "matchmaker_port": 5054,
    "dump_filename": "/var/tmp/pilot-resources.state",
    'job_submit_timeout': 15,
    'job_query_timeout': 15,
    'job_kill_timeout': 15,
    'job_operation_check_period': 5,
    'memory_heartbeat': 5,
    'job_running_set_refresh': 5,
    'job_poll_period': 1,
    'wsn_poll_period': 120,
    'garbage_collection_cycle': 600,
    'accounting_log_keep_days': 14,
    "operation_loop": 5,
    "jobs_loop": 5,
    "task_starters": 3,
    "delegations_loop": 5,
    "delegations_renew_threshold": 300,
    "host_proxy_filename": "/var/tmp/pilot-host-proxy.pem",
    })

def load_config_file(filename):
    here = os.path.dirname(os.path.abspath(filename))
    defaults = {
        "here": here,
        }

    def guess_value(name, value):
        if name in config:
            return type(config[name])(value)
        elif type(value) in types.StringTypes:
            if re.match(r'^\d+$', value):
                return int(value)
            elif "\n" in value:
                return [line.strip() for line in value.split("\n") if line.strip() != ""]
            else:
                return value
        else:
            return value
        
    cf = SafeConfigParser()
    cf.read([filename])

    for name, value in cf.items("spooler", vars=defaults):
        config[name] = guess_value(name, value)

    def interested(name):
        if name == "spooler":
            return False
        elif ":" in name and name != "app:pilot":
            return False
        elif name.startswith("formatter_"):
            return False
        else:
            return True

    def sections(cf):
        return (secname for secname in cf.sections() if interested(secname))

    for secname in sections(cf):
        for name, value in cf.items(secname, vars=defaults):
            if secname == "app:pilot":
                keyname = "pilot_" + name
            else:
                keyname = secname+"_"+name
            config.setdefault(keyname, guess_value(keyname, value))

    config_set_defaults()

def config_set_defaults():
    defaults = {
        "httpd_port": 5053,
        "common_ssl_certificate": "/etc/grid-security/containercert.pem",
        "common_ssl_privatekey": "/etc/grid-security/containerkey.pem",
        "common_ssl_cafile": None,
        "common_ssl_capath": "/etc/grid-security/certificates",
        "common_voms_dir": "/etc/grid-security/vomsdir",
        "common_user": pwd.getpwuid(os.getuid())[0],
        "common_group": grp.getgrgid(os.getgid())[0],
        "matchmaker_connection_timeout": 15,
        "matchmaker_cache_ttl": 180,
        "matchmaker_order": "deny, allow",
    }
    for k, v in defaults.iteritems():
        config.setdefault(k, v)

def update_config_from_options(options):
    for name, value in options.__dict__.iteritems():
        if value is not None:
            if name in config:
                construct = type(config[name])
            else:
                construct = lambda x: x
            config[name] = construct(value)

wsn_enabled = False

exec_pool = eventlet.greenpool.GreenPool(size=15)

def write_known_traceback(traceback_text):
    """Save stack traceback info provided as text to a temporary file"""
    log = logging.getLogger('spooler.traceback')
    now = datetime.datetime.now()
    traceback_filename = "/tmp/pilot-spooler-traceback-%s.%s.txt" % (
        now.strftime("%Y%m%d%H%M%S"), str(now.microsecond))
    log.error("traceback saved to %s", traceback_filename)
    fd = open(traceback_filename, 'w')
    fd.write(traceback_text)
    fd.close()

    
def write_traceback():
    """Save stack traceback after exception to a temporary file"""
    traceback_text = traceback.format_exc()
    write_known_traceback(traceback_text)
