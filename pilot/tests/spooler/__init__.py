# -*- encoding: utf-8 -*-

from ConfigParser import SafeConfigParser
from cStringIO import StringIO

from pilot.spooler import config

from pilot.spooler import loops
loops.__singlestep__ = True

for param in config:
    if param.endswith("_loop"):
        config[param] = 0

import logging
logging.root.handlers = []

from pilot.spooler import globus
globus.GLOBUSRUN_WS = "pyglobusrun-ws"
globus.WSRF_QUERY = "pywsrf-query"
