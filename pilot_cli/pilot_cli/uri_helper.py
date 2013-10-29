# -*- encoding: utf-8 -*-

import sys

from pilot_cli.api import setup_app, errmsg
from pilot_cli.common import exit_codes

def main():
    options, args, log, svc = setup_app(
        usage = "%prog [options] URI ...",
        description = """Fetch information from the specified URI using https proxy authentication. Warning: if this program is called with -j option, it will fail if server response does not have appropriate Content-Type.""",
        argstest = lambda args: len(args) == 1,
        logname = "pilot-uri-helper")

    uri = args[0]
    response, data = svc.get(uri)
    json_contenttypes = ['application/json', 'text/javascript']
    if response['content-type'] not in json_contenttypes and options.json:
        errmsg("Server did not return JSON output.")
        log.debug("Server did not return JSON output.")
        sys.exit(exit_codes.content_error)
    sys.stdout.write(data)
    sys.exit(exit_codes.success)

if __name__ == '__main__':
    main()
