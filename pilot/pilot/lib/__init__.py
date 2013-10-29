# -*- encoding: utf-8 -*-

try:
    import json
except ImportError:
    import simplejson as json

try:
    from xml.etree import ElementTree as etree
except ImportError:
    from elementtree import ElementTree as etree
