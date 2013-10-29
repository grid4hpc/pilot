# -*- encoding: utf-8 -*-

import os
import sys

paths = ${paths}
sys.path[0:0] = list(set(paths) - set(sys.path))

from paste.deploy import loadapp
if 'APP_CONFIG' not in os.environ:
   os.environ['APP_CONFIG'] = '${configfile}'

import logging
logging.basicConfig(level=logging.DEBUG)
    
application = loadapp('config:' + os.environ['APP_CONFIG'])
