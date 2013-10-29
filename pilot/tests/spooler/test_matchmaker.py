# -*- encoding: utf-8 -*-

import unittest, mock, pickle
import logging

from pilot.spooler.matchmaker import Matchmaker
from time import time

from pylons import config
from ConfigParser import SafeConfigParser

matchmaker_config = SafeConfigParser()
matchmaker_config.read(config['__file__'])

matchmaker_resources = pickle.loads("""
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
UJBE32NO
""".decode('base64').decode('bz2'))

@mock.patch.object(Matchmaker, 'refresh')
def create_matchmaker(mock_method):
    mm = Matchmaker()
    mm.last_update = time()
    mm.resources = matchmaker_resources

    return mm

log = logging.getLogger('pilot.spooler.matchmaker')

class MatchmakeEmptyTest(unittest.TestCase):
    def setUp(self):
        self.old_level = log.level
        log.setLevel(100)
        self.mm = create_matchmaker()

    def tearDown(self):
        log.setLevel(self.old_level)

    def test_matchmake_empty(self):
        reqs = {}
        self.failUnless(len(self.mm.matchmake(reqs)) > 0)

    def test_matchmake_not_hostreqs(self):
        reqs = {'some':'req'}
        self.assertRaises(ValueError, self.mm.matchmake, reqs)


class MatchmakeHostnames(unittest.TestCase):
    def setUp(self):
        self.old_level = log.level
        log.setLevel(100)
        self.mm = create_matchmaker()

    def tearDown(self):
        log.setLevel(self.old_level)

    def test_matchmake_single_hostname(self):
        req_host = 'ngrid.jinr.ru'
        reqs = {'hostname': [req_host] }
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 0)
        for host, queue in results.iterkeys():
            self.assertEqual(host, req_host)

    def test_matchmake_single_matching_hostname(self):
        req_host = 'ngrid.jinr.ru'
        reqs = {'hostname': [req_host, 'some.host'] }
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 0)
        for host, queue in results.iterkeys():
            self.assertEqual(host, req_host)

    def test_matchmake_multiple_hosts(self):
        hosts = ['ngrid.jinr.ru', 'cleo-devel.ngrid.ru']
        found_hosts = set()
        reqs = {'hostname': hosts}
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 0)
        for (host, queue) in results.iterkeys():
            self.failUnless(host in hosts)
            found_hosts.add(host)

        self.failUnless(found_hosts == set(hosts))


class MatchmakeFork(unittest.TestCase):
    def setUp(self):
        self.old_level = log.level
        log.setLevel(100)
        self.mm = create_matchmaker()

    def tearDown(self):
        log.setLevel(self.old_level)

    def test_matchmake_nofork(self):
        reqs = {'fork': False}
        results = self.mm.matchmake(reqs)
        for result in results.itervalues():
            self.failIf(result['lrms_type'] == 'Fork')

        reqs = {}
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 0)
        for result in results.itervalues():
            self.failIf(result['lrms_type'] == 'Fork')

    def test_matchmake_fork(self):
        reqs = {'fork': True}
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 0)
        for result in results.itervalues():
            self.failUnless(result['lrms_type'] == 'Fork')

    def test_matchmake_fork_name(self):
        reqs = {'lrms': 'Fork'}
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 0)
        for result in results.itervalues():
            self.failUnless(result['lrms_type'] == 'Fork')

class MatchmakeQueues(unittest.TestCase):
    def setUp(self):
        self.old_level = log.level
        log.setLevel(100)
        self.mm = create_matchmaker()

    def tearDown(self):
        log.setLevel(self.old_level)

    def test_noqueue(self):
        reqs = {'lrms': 'Cleo'}
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 1)

    def test_queue(self):
        reqs = {'lrms': 'Cleo', 'queue': 'hdd'}
        results = self.mm.matchmake(reqs)
        self.failIf(len(results) != 1)

    def test_queue_only(self):
        reqs = {'queue': 'batch'}
        results = self.mm.matchmake(reqs)
        self.failUnless(len(results) > 1)
        hosts = [ host for (host, queue) in results.iterkeys() ]
        self.failUnless(len(hosts) > 1)
