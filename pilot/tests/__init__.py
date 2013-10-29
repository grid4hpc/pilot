# -*- encoding: utf-8 -*-

from paste.script.appinstall import SetupCommand
from pylons import config, url

from pilot.spooler import load_config_file
from pilot.model import meta, init_model
from sqlalchemy import engine_from_config, create_engine

SetupCommand('setup-app').run([config['__file__']])
init_model(engine_from_config(config, 'database.'))
load_config_file(config['__file__'])
