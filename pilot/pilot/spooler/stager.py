#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import os
import pwd
import sys
import tempfile

from distutils.dir_util import mkpath
from subprocess import Popen, PIPE
from pilot_cli import proxylib

def ensure_acl(acl, filename):
    out, _ = Popen(["getfacl", "-a", "-c", "-p", "-n", filename],
                   stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(None)
    if acl not in out:
        Popen(["setfacl", "-m", acl, filename],
              stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(None)

def setup_environment(user, puid):
    os.chdir(user.pw_dir)
    os.umask(0077)
    if not os.path.exists(".grid"):
        os.mkdir(".grid")
    out, _ = Popen(["getfacl", "-a", "-c", "-p", "-n", ".grid"],
                   stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(None)
    acl = "user:%d:r-x" % puid
    ensure_acl(acl, ".grid")

def create_scratch(user, puid):
    acl = "user:%d:r-x" % puid
    where = os.path.join(user.pw_dir, ".grid")
    scratch = tempfile.mkdtemp(prefix="pilot.", dir=where)
    ensure_acl(acl, scratch)
    return scratch

def main():
    params = json.load(sys.stdin)
    user = pwd.getpwuid(os.geteuid())
    puid = params["puid"]
    result = {}
    errors = []

    if "proxy" in params:
        proxyfile = proxylib.get_proxy_filename()
        mask = os.umask(0077)
        open(proxyfile, "wb").write(params["proxy"])
        os.umask(mask)
    
    if "in" in params:
        setup_environment(user, puid)
        scratch = create_scratch(user, puid)
        result["scratch"] = scratch
        os.chdir(scratch)
        for local, remote in params["in"]:
            localpath = os.path.abspath(os.path.join(scratch, local))
            localdir = os.path.split(local)[0]
            if not os.path.exists(localdir):
                mkpath(localdir, mode=0700)
            pid = Popen(["uberftp", remote, "file://" + localpath],
                        stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
            stdout, stderr = pid.communicate(None)
            if pid.returncode != 0:
                errors.append((local, remote, stdout + stderr))
    elif "out" in params:
        scratch = params["scratch"]
        os.chdir(scratch)
        for local, remote in params["out"]:
            localpath = os.path.abspath(os.path.join(scratch, local))
            pid = Popen(["uberftp", "file://" + localpath, remote],
                        stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
            stdout, stderr = pid.communicate(None)
            if pid.returncode != 0:
                errors.append((local, remote, stdout + stderr))

    result["errors"] = errors
    json.dump(result, sys.stdout)

if __name__ == '__main__':
    main()
