# -*- encoding: utf-8 -*-

from pilot.lib import certlib
from eventlet.green import os

GRIDMAPDIR = "/etc/grid-security/gridmapdir"
GRIDMAPFILE = "/etc/grid-security/grid-mapfile"

def get_real_subject(chain):
    for cert in chain:
        if not certlib.x509_is_proxy(cert):
            return str(cert.get_subject())

def get_mapping(proxy):
    user_dn = get_real_subject(proxy)
    # first try: grid-mapfile for the subject
    for line in open(GRIDMAPFILE, "r"):
        parts = line.strip("\n").split(" ")
        subject = " ".join(parts[:-1]).strip('"')
        uid = parts[-1]
        if user_dn == subject:
            return uid

    # TODO: second try: grid-mapfile and group-mapfile for voms group

    # user was NOT mapped
    return None

def is_pool(mapping):
    if mapping is None:
        return False
    if mapping[0] == '.':
        return True
    return False

def gridmapdir_name_encode(name):
    result = ""
    for ch in name:
        if ch.isalnum():
            result += ch.lower()
        else:
            result += ("%%%02x" % ord(ch))
    return result

def allocate_pool_account(mapping, proxy):
    user_dn = get_real_subject(proxy)
    entry = gridmapdir_name_encode(user_dn)
    path = os.path.join(GRIDMAPDIR, entry)
    try:
        inode = os.stat(path).st_ino
        return find_account_by_inode(inode)
    except OSError:
        return allocate_new_account(mapping, entry)

def allocate_new_account(mapping, entry):
    pool = mapping[1:]
    for name in os.listdir(GRIDMAPDIR):
        if not name.startswith(pool):
            continue
        good = True
        for ch in name[len(pool):]:
            if not ch.isdigit():
                good = False
                break
        if not good:
            continue
        path = os.path.join(GRIDMAPDIR, name)
        st = os.stat(path)
        if st.st_nlink != 1:
            continue
        try:
            os.link(path, os.path.join(GRIDMAPDIR, entry))
            return name
        except OSError:
            continue

    return None

def find_account_by_inode(inode):
    for name in os.listdir(GRIDMAPDIR):
        if name[0] == "%":
            continue
        path = os.path.join(GRIDMAPDIR, name)
        try:
            if os.stat(path).st_ino == inode:
                return name
        except OSError:
            continue

    return None

    
