# -*- encoding: utf-8 -*-

try:
    import pilot_lib
except ImportError:
    pass

# workaround some CentOS5 import bugs
from pkg_resources import get_distribution
get_distribution('M2Crypto>=0.20.1').activate()
get_distribution('decorator>=3.0.0').activate()
