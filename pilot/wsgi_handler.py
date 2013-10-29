# -*- encoding: utf-8 -*-

import os, sys
here = os.path.dirname(os.path.abspath(__file__))
VENV=os.path.join(here, "srv-debug-env")
AV=os.path.join(VENV, 'bin/activate_this.py')
execfile(AV, dict(__file__=AV))

import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.append(here)
sys.path.append(os.path.join(here, 'cli'))
#os.environ['PYTHON_EGG_CACHE'] = '/...'

from paste.deploy import loadapp
if 'APP_CONFIG' not in os.environ:
    os.environ['APP_CONFIG'] = here + "/dev.ini"
    
application = loadapp('config:' + os.environ['APP_CONFIG'])
