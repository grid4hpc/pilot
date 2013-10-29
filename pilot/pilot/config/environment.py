"""Pylons environment configuration"""
import os
from pkg_resources import get_distribution

from mako.lookup import TemplateLookup
from pylons import config
from pylons.error import handle_mako_error

from ConfigParser import ConfigParser, NoOptionError

from pilot.lib import app_globals, resources
import pilot.lib.helpers
from pilot.config.routing import make_map
from pilot.model import init_model

from sqlalchemy import engine_from_config

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='pilot', paths=paths)

    config['routes.map'] = make_map()
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = pilot.lib.helpers

    pilot_config = ConfigParser({'here': config['here']})
    pilot_config.read(config['config_file'])
    config['pilot_config'] = pilot_config

    if pilot_config.has_option('httpd', 'port'):
        config['pilot_port'] = pilot_config.getint('httpd', 'port')
    else:
        config['pilot_port'] = 5053
        
    config['matchmaker_port'] = config['pilot_port'] + 1
    config['version'] = u"pilot-%s" % (get_distribution('pilot').version)

    if 'accounting_access' in config:
        config['accounting_access'] = [dn for dn in config['accounting_access'].split("\n") \
                                       if len(dn) > 0]
    else:
        config['accounting_access'] = []

    config['voms_dir'] = '/etc/grid-security/vomsdir'
    config['cert_dir'] = '/etc/grid-security/certificates'
    try:
        config['voms_dir'] = config['pilot_config'].get('common', 'voms_dir')
    except NoOptionError:
        pass
    
    try:
        config['cert_dir'] = config['pilot_config'].get('common', 'ssl_capath')
    except NoOptionError:
        pass

    resources.config['capath'] = config['cert_dir']
    resources.config['voms_dir'] = config['voms_dir']
    resources.config['baseurl'] = "http://localhost:%d/" % \
                                  config['matchmaker_port']
    resources.config['timeout'] = 15
        

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # Setup the SQLAlchemy database engine
    engine = engine_from_config(config, 'database.')
    init_model(engine)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
