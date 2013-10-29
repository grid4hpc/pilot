"""Setup the pilot application"""
import logging

from pylons import config
import os

from pilot.config.environment import load_environment
from pilot.model import meta

log = logging.getLogger(__name__)

def setup_app(command, conf, vars):
    """Place any commands to setup pilot here"""
    load_environment(conf.global_conf, conf.local_conf)

    log.info("Setting up database...")
    from migrate.versioning import api as mapi
    from migrate.versioning import exceptions as me
    url = config['app_conf']['database.url']
    repo = os.path.split(os.path.abspath(__file__))[0] + '/model/repository'
    try:
        log.info("setting up version_control")
        mapi.version_control(url, repo)
    except me.DatabaseAlreadyControlledError:
        log.info("database already in version control")
        pass
    db_version = mapi.db_version(url, repo)
    version = mapi.version(repo)
    if db_version != version:
        log.info("upgrade %d -> %d" % (db_version, version))
        mapi.upgrade(url, repo)
    else:
        log.info("database is already up to date")
    log.info("Database setup done.")
