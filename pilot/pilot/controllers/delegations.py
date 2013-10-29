# -*- encoding: utf-8 -*-

import datetime
import logging
import struct

from paste.util import mimeparse

from pylons import config, request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from pilot.lib.base import BaseController, render_json, render_no_data, expects_json, render_data
import pilot.lib.helpers as h
from pilot import model
from pilot.model.meta import Session

from pilot.lib import certlib
from M2Crypto import RSA, BIO, ASN1, EVP, X509
from gridproxy import voms

from pilot.lib import json

log = logging.getLogger(__name__)

def make_key():
    return RSA.gen_key(1024, 65537, lambda x: 1)

def delegation_info(delegation):
    """
    Возвращает информаию о делегации в виде словаря с атрибутами
    согласно API.
    """
    result = {}
    for required in ('vo', 'fqans', 'renewable', 'next_expiration', 'delegation_id'):
        result[required] = getattr(delegation, required)
    for optional in ('myproxy_server', 'credname'):
        v = getattr(delegation, optional)
        if v is not None:
            result[optional] = v
    return result

class DelegationsController(BaseController):
    required_attrs = ('renewable',)
    editable_attrs = ('renewable', 'myproxy_server', 'credname')
    optional_attrs = ('myproxy_server', 'credname')
    
    def index(self):
        result = []
        for delegation in Session.query(model.Delegation).filter_by(owner_hash=self.cert_owner):
            info = delegation_info(delegation)
            info["uri"] = h.url('delegation', delegation_id=delegation.delegation_id)
            result.append(info)
        return render_json(result)

    def find_delegation(self, delegation_id):
        delegation = Session.query(model.Delegation) \
                     .filter_by(owner_hash=self.cert_owner, delegation_id=delegation_id) \
                     .first()
        if delegation is None:
            abort(404)
        return delegation

    def get(self, delegation_id):
        delegation = self.find_delegation(delegation_id)
        return render_json(delegation_info(delegation))

    @expects_json
    def create_or_update(self, delegation_id, obj=None):
        for attr in obj:
            if attr not in self.editable_attrs:
                abort(400)        

        delegation = Session.query(model.Delegation) \
                     .filter_by(owner_hash=self.cert_owner, delegation_id=delegation_id) \
                     .first()
        if delegation is None:
            for attr in self.required_attrs:
                if attr not in obj:
                    abort(400)
            delegation = model.Delegation(owner_hash=self.cert_owner,
                                          vo = self.cert_vo,
                                          fqans = self.fqans_string,
                                          delegation_id = delegation_id)

        for attr, value in obj.iteritems():
            setattr(delegation, attr, value)

        Session.add(delegation)
        Session.flush()
        return render_no_data()

    @expects_json
    def update_attribute(self, delegation_id, attr, obj=None):
        if attr not in self.editable_attrs:
            abort(400)        
        delegation = self.find_delegation(delegation_id)
        setattr(delegation, attr, obj)
        Session.flush()
        return render_no_data()

    def delete_attribute(self, delegation_id, attr):
        if attr not in self.optional_attrs:
            abort(400)        
        delegation = self.find_delegation(delegation_id)
        setattr(delegation, attr, None)
        Session.flush()
        return render_no_data()    

    def get_pubkey(self, delegation_id):
        request_formats = ('application/x-pkcs1+pem', 'application/x-pkcs1', 'application/x-pkcs1+der')
        format = mimeparse.best_match(request_formats, request.headers.get('Accept', '*/*'))
        if format == '':
            format = request_formats[0]
        enc = 'der'
        if '+' in format:
            enc = format.split('+')[1]
        if enc not in ('pem', 'der'):
            abort(412, 'This object may be served only in these Content-Types: %s.' % ', '.join(request_formats),
                  headers={'Content-Type': 'text/plain'})

        delegation = self.find_delegation(delegation_id)
        if delegation.new_key is None:
            delegation.new_key = make_key()
            Session.flush()
        buf = BIO.MemoryBuffer()
        delegation.new_key.save_pub_key_bio(buf)
        pubkey_pem = buf.getvalue()
        if enc == 'pem':
            return render_data(pubkey_pem, format)
        else:
            return render_data(pubkey_pem.split("-----")[2].decode('base64'), format)


    def get_request(self, delegation_id):
        request_formats = ('application/x-pkcs10+der', 'application/x-pkcs10', 'application/x-pkcs10+pem')
        format = mimeparse.best_match(request_formats, request.headers.get('Accept', '*/*'))
        if format == '':
            format = request_formats[0]
        enc = 'der'
        if '+' in format:
            enc = format.split('+')[1]
        if enc not in ('pem', 'der'):
            abort(412, 'This object may be served only in these Content-Types: %s.' % ', '.join(request_formats),
                  headers={'Content-Type': 'text/plain'})
            
        delegation = self.find_delegation(delegation_id)
        if delegation.new_key is None:
            delegation.new_key = make_key()
            Session.flush()

        pkey = EVP.PKey()
        pkey.assign_rsa(delegation.new_key)

        req = X509.Request()
        req.set_pubkey(pkey)

        subj = X509.X509_Name()
        digest = EVP.MessageDigest('sha1')
        digest.update(pkey.as_der())
        serial = struct.unpack("<L", digest.final()[:4])[0]
        subj.add_entry_by_txt('CN', ASN1.MBSTRING_ASC, str(serial), -1, -1, 0)
        req.set_subject(subj)
        req.sign(pkey, 'sha1')

        if enc == 'pem':
            return render_data(req.as_pem(), format)
        else:
            return render_data(req.as_der(), format)
                
    def renew(self, delegation_id):
        parts = mimeparse.parse_mime_type(request.headers.get('Content-Type', 'application/x-pkix-chain+pem'))
        ctype = parts[0] + '/' + parts[1]

        chain = None
        if ctype == 'application/x-pkix-chain+pem':
            chain = X509.X509_Stack()
            for pem in certlib.split_proxy(request.body)[0]:
                chain.push(X509.load_cert_string(pem))
        elif ctype in ('application/x-pkix-chain', 'application/x-pkix-chain+der'):
            chain = certlib.x509_load_chain_der(request.body)
        else:
            abort(415, "Unknown content-type: %s" % ctype)

        delegation = self.find_delegation(delegation_id)
        if delegation.new_key is None:
            abort(400, "No pending renew key pair found")

        if chain[0].get_pubkey().get_rsa().pub() != delegation.new_key.pub():
            abort(400, "Proxy certificate does not match delegation key. Please try again.")

        voms_ac = voms.VOMS(config['voms_dir'], config['cert_dir'])
        try:
            certlib.load_voms_chain(voms_ac, chain)
        except voms.VOMSError, exc:
            abort(400, "Failed to load voms extensions: %s" % str(exc))
            
        delegation.key = delegation.new_key
        delegation.chain = chain
        delegation.new_key = None
        delegation.vo = unicode(voms_ac.vo)
        delegation.fqans = ':'.join(voms_ac.fqans)
        not_after = min(cert.get_not_after().get_datetime() for cert in chain)
        not_after = min(not_after, voms_ac.not_after)
        # отрезать TZ
        not_after = datetime.datetime(*not_after.timetuple()[:6])
        delegation.next_expiration = not_after
        Session.flush()
        return render_no_data()
