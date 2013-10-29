from tests.data import *
from tests.httpd import *

import webtest

from M2Crypto import RSA, BIO, X509, EVP
from pilot.lib import certlib
from pilot_cli import proxylib

class TestDelegationsController(TestController):

    def test_index(self):
        empty_db()
        response = self.app.get(url(controller='delegations', action='index'))
        parsed = json.loads(response.body)
        assert parsed == []
        delegation = create_delegation(delegation_id="test")
        response = self.app.get(url(controller='delegations', action='index'))
        parsed = json.loads(response.body)
        assert len(parsed) == 1
        
        d = parsed[0]
        for attr in ('delegation_id', 'uri', 'vo', 'fqans'):
            assert d[attr] != ''

        assert d['uri'].endswith('/test')

    def test_get_delegation(self):
        empty_db()
        delegation = create_delegation(delegation_id="test")
        response = self.app.get(url('delegation', delegation_id='test'))
        d = json.loads(response.body)
        assert d['delegation_id'] == delegation.delegation_id
        assert d['fqans'] == delegation.fqans
        assert d['next_expiration'] == delegation.next_expiration.isoformat() + 'Z'
        assert d['renewable'] == delegation.renewable
        assert d['vo'] == delegation.vo

    def test_create_delegation(self):
        empty_db()
        assert Session.query(model.Delegation).count() == 0
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false }')
        assert response.status_int == 204
        assert Session.query(model.Delegation).count() == 1
        delegation = Session.query(model.Delegation).first()
        assert delegation.delegation_id == 'test'
        assert delegation.renewable == False
        try:
            response = self.app.put(url('delegation', delegation_id='test'),
                                    params='{ "renewable": false, "next_expiration": 1 }')
            assert "Should raise AppError"
        except webtest.AppError, exc:
            assert '400 Bad Request' in str(exc)

    def test_update_delegation(self):
        empty_db()
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false }')
        delegation = Session.query(model.Delegation).first()
        assert delegation.renewable == False
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": true }')
        assert response.status_int == 204
        delegation = Session.query(model.Delegation).first()
        assert delegation.renewable == True
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false, "myproxy_server": "blah" }')
        assert response.status_int == 204
        delegation = Session.query(model.Delegation).first()
        assert delegation.myproxy_server == "blah"

    def test_update_delegation_part(self):
        empty_db()
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false }')
        delegation = Session.query(model.Delegation).first()
        assert delegation.renewable == False
        response = self.app.put(url('delegation_attribute',
                                    delegation_id='test', attr='renewable'),
                                params='true')
        assert response.status_int == 204
        delegation = Session.query(model.Delegation).first()
        assert delegation.renewable == True

    def test_delete_delegation_part(self):
        empty_db()
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false, "myproxy_server": "blah" }')
        delegation = Session.query(model.Delegation).first()
        assert delegation.myproxy_server is not None
        response = self.app.delete(url('delegation_attribute',
                                       delegation_id='test', attr='myproxy_server'))
        assert response.status_int == 204
        delegation = Session.query(model.Delegation).first()
        assert delegation.myproxy_server is None
        

    def test_delegation_get_pubkey_csr(self):
        empty_db()
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false }')
        delegation = Session.query(model.Delegation).first()

        response = self.app.get(url('delegation_pubkey', delegation_id='test'))
        pubkey1 = response.body

        response = self.app.get(url('delegation_pubkey', delegation_id='test'))
        pubkey2 = response.body

        response = self.app.get(url('delegation_pubkey', delegation_id='test'),
                                headers={'Accept': 'application/x-pkcs1'})
        pubkey3 = response.body

        key1 = RSA.load_pub_key_bio(BIO.MemoryBuffer(pubkey1))
        key3 = certlib.rsa_load_pub_key_der(pubkey3)

        assert key1.pub() == delegation.new_key.pub()
        assert pubkey1 == pubkey2
        assert key1.pub() == key3.pub()

        response = self.app.get(url('delegation_request', delegation_id='test'),
                                headers={'Accept': 'application/x-pkcs10+der'})
        req = X509.load_request_der_string(response.body)

        assert key1.pub() == req.get_pubkey().get_rsa().pub()

    def test_delegation_renew(self):
        empty_db()
        response = self.app.put(url('delegation', delegation_id='test'),
                                params='{ "renewable": false }')
        delegation = Session.query(model.Delegation).first()

        response = self.app.get(url('delegation_pubkey', delegation_id='test'))
        pub_key = RSA.load_pub_key_bio(BIO.MemoryBuffer(response.body))
        pkey = EVP.PKey()
        pkey.assign_rsa(pub_key)

        key, chain = certlib.load_proxy(test_user_proxy)
        proxy = proxylib.generate_proxycert(pkey, chain[0], key)

        new_chain = X509.X509_Stack()
        new_chain.push(proxy)
        for cert in chain:
            new_chain.push(cert)

        response = self.app.put(url('delegation_renew', delegation_id='test'),
                                params=new_chain.as_der(),
                                headers={'Content-Type': 'application/x-pkix-chain+der'})
        assert response.status_int == 204

        try:
            response = self.app.put(url('delegation_renew', delegation_id='test'),
                                    params=new_chain.as_der(),
                                    headers={'Content-Type': 'application/x-pkix-chain+der'})
            raise "Should raise AppError"
        except webtest.AppError, exc:
            assert 'No pending renew key pair found' in exc.args[0]

        response = self.app.get(url('delegation_pubkey', delegation_id='test'))
        try:
            response = self.app.put(url('delegation_renew', delegation_id='test'),
                                    params=new_chain.as_der(),
                                    headers={'Content-Type': 'application/x-pkix-chain+der'})
            raise "Should raise AppError"
        except webtest.AppError, exc:
            assert 'does not match delegation key' in exc.args[0]

