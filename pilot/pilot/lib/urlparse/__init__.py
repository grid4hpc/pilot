# -*- encoding: utf-8 -*-

"""
imports from urlparse, but with additional initialization for parsing
gsiftp URLs.
"""

import urlparse as u

for scheme in ('gsiftp', ):
    u.uses_relative.insert(0, scheme)
    u.uses_netloc.insert(0, scheme)
    u.uses_params.insert(0, scheme)
    u.uses_fragment.insert(0, scheme)
u._parse_cache = {}

for name in u.__all__:
    locals()[name] = getattr(u, name)

del u, scheme
