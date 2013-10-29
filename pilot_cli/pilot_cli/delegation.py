# -*- encoding: utf-8 -*-

import datetime
import os
import pytz
import sys

from pilot_cli.common import exit_codes
from pilot_cli.api import errmsg, setup_app, json_loads, isoformat, PilotError
from pilot_cli import proxylib

def list():
    options, args, log, svc = setup_app(
        usage="%prog [options]",
        description = """
    List current user's delegations and their status.
    """,
        argstest=lambda args: len(args) == 0,
        logname="pilot-delegation-list")

    _, content = svc.get("/delegations")
    if options.json:
        print content
        sys.exit(exit_codes.success)

    fmt = "%-20s|%-15s|%s"
    if not (options.quiet or options.verbose):
        print fmt % ("Name", "VO", "Expires")
        print "-"*75
    for delegation in json_loads(content):
        if delegation['next_expiration'] is None:
            delegation['next_expiration'] = datetime.datetime.fromtimestamp(0, pytz.UTC)
        if options.quiet:
            print ",".join((
                delegation['delegation_id'],
                delegation['uri'],
                isoformat(delegation['next_expiration']),
                delegation['renewable'] and "1" or "0",
                delegation['vo'],
                delegation['fqans']))
        elif options.verbose:
            print "===", delegation['delegation_id']
            print " * URI:", delegation['uri']
            print " * VO:", delegation['vo'], "(FQANs: %s)" % delegation['fqans']
            r = delegation['renewable'] and "Renewable" or "Not renewable"
            print " * Expires:", delegation['next_expiration'].strftime("%c %Z")
        else:
            print fmt % (
                delegation['delegation_id'],
                delegation['vo'],
                delegation['next_expiration'].strftime("%c %Z"))

    sys.exit(exit_codes.success)

def delegation_options(group):
    group.add_option("-m", "--myproxy", metavar="HOST:PORT",
                     help="MyProxy server address (default: $MYPROXY_SERVER)",
                     dest="myproxy_server",
                     default=os.environ.get("MYPROXY_SERVER", None))
    group.add_option("--credname", metavar="NAME",
                     help="MyProxy credential name (if required)",
                     dest="myproxy_credname")
    group.add_option("--renewable", action="store_true",
                     help="Create a renewable delegation (default: %default)",
                     dest="renewable", default=False)

def test_cu_options(args, options):
    if len(args) > 1:
        return False    
    if (not options.renewable) or (options.myproxy_server is not None):
        return True
    else:
        return False
        

def update():
    options, args, log, svc = setup_app(
        usage="%prog [options] [delegation_id]",
        description = """
    Update delegation. Delegation id may by passed as an argument or
    in options.
    """,
        argstest=test_cu_options,
        logname="pilot-delegation-update",
        extra_options=delegation_options)

    if len(args) == 1:
        options.delegation_id = args[0]

    key, chain = proxylib.load_proxy(open(options.proxy).read())
    try:
        svc.update_delegation(options.delegation_id,
                              options.renewable,
                              options.myproxy_server,
                              options.myproxy_credname)
        svc.renew_delegation(options.delegation_id, key, chain)
    except PilotError, exc:
        errmsg("Failed to update delegation: %s", str(exc))
        sys.exit(exit_codes.delegation_error)

    sys.exit(exit_codes.success)

def create():
    options, args, log, svc = setup_app(
        usage="%prog [options] [delegation_id]",
        description = """
    Create a new delegation (or update existing one). Delegation id
    may by passed as an argument or in options.
    """,
        argstest=test_cu_options,
        logname="pilot-delegation-create",
        extra_options=delegation_options)

    if len(args) == 1:
        options.delegation_id = args[0]

    key, chain = proxylib.load_proxy(open(options.proxy).read())
    try:
        svc.update_delegation(options.delegation_id,
                              options.renewable,
                              options.myproxy_server,
                              options.myproxy_credname)
        svc.renew_delegation(options.delegation_id, key, chain)
    except PilotError, exc:
        errmsg("Failed to update delegation: %s", str(exc))
        sys.exit(exit_codes.delegation_error)

    sys.exit(exit_codes.success)

def destroy():
    options, args, log, svc = setup_app(
        usage="%prog [options] [delegation_id]",
        description = """
    Destroy a delegation. Delegation id may by passed as an argument or
    in options.
    """,
        argstest=lambda args: len(args) <= 1,
        logname="pilot-delegation-delete")

    if len(args) == 1:
        options.delegation_id = args[0]

    response, content = svc.delete("/delegations/%s" % options.delegation_id)
    if response.status != 204:
        errmsg("Failed to delete delegation: %s (HTTP Code %d)", content, response.status)
        sys.exit(exit_codes.delegation_error)

    sys.exit(exit_codes.success)

if __name__ == '__main__':
    list()
