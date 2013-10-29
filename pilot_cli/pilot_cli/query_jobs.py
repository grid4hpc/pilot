# -*- encoding: utf-8 -*-

import sys

from pilot_cli.api import setup_app, json_loads
from pilot_cli.common import exit_codes

def main():
    _, _, _, svc = setup_app(
        description = """
        Query a list of URIs of owned jobs.
        """,
        argstest = lambda args: len(args) == 0,
        logname = "pilot-query-jobs")

    data = svc.get("/jobs")[1]
    for job in json_loads(data):
        print job['uri']
    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
