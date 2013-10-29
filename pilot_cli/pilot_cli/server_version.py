# -*- encoding: utf-8 -*-

import sys

from pilot_cli.common import exit_codes
from pilot_cli.api import setup_app

def main():
    _, _, _, svc = setup_app(
        usage = "%prog [options]",
        description = """Print the pilot server version.""",
        argstest = lambda args: len(args) == 0,
        logname = "pilot-server-version")

    print svc.server_version()
    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
