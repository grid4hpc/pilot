import logging

from pylons import config

from pilot.lib.base import BaseController, render_data

log = logging.getLogger(__name__)

class VersionController(BaseController):

    def index(self):
        return render_data(config['version'])
