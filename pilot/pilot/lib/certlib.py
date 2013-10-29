# -*- encoding: utf-8 -*-

import os
import re

from M2Crypto import X509, ASN1, m2, SSL, RSA, BIO, EVP
from pilot.lib import m2_ext

def x509_ext_get_object(self):
    return ASN1.ASN1_Object(m2_ext.x509_extension_get_object(self._ptr()), 0)

def asn1_object_get_oid(self):
    return m2.obj_obj2txt(self._ptr(), 1)

def asn1_object_get_sn(self):
    return m2.obj_nid2sn(m2.obj_obj2nid(self._ptr()))

def x509_is_proxy(self):
    for i in xrange(self.get_ext_count()):
        ext = self.get_ext_at(i)
        ext_obj = x509_ext_get_object(ext)
        oid = asn1_object_get_oid(ext_obj)
        if oid == '1.3.6.1.5.5.7.1.14':
            return True
    return False

def rsa_to_der(rsa):
    buf = BIO.MemoryBuffer()
    rsa.save_key_der_bio(buf)
    return buf.getvalue()
    
def monkey():
    X509.X509_Extension.get_object = x509_ext_get_object
    ASN1.ASN1_Object.get_oid = asn1_object_get_oid
    ASN1.ASN1_Object.get_sn = asn1_object_get_sn
    X509.X509.is_proxy = x509_is_proxy
    RSA.RSA.as_der = rsa_to_der

class CustomContext(SSL.Context):
    def set_client_cert(self, cert):
        return m2.ssl_ctx_use_x509(self.ctx, cert.x509)

    def set_client_key(self, key):
        return m2.ssl_ctx_use_rsa_privkey(self.ctx, key.rsa)

    def add_extra_chain_cert(self, cert):
        copy = X509.load_cert_der_string(cert.as_der())
        copy._pyfree = 0
        return m2_ext.ssl_ctx_add_extra_chain_cert(self.ctx, copy.x509)

def rsa_unencrypted_der_to_pem(buffer):
    pem_buffer = """-----BEGIN RSA PRIVATE KEY-----
%s
-----END RSA PRIVATE KEY-----
""" % str(buffer).encode('base64').strip()
    return pem_buffer

def rsa_load_unencrypted_der(buffer):
    def password_callback(*args, **kwargs):
        return ''
    return RSA.load_key_string(rsa_unencrypted_der_to_pem(buffer))

def x509_load_chain_der(buffer):
    return X509.X509_Stack(m2.make_stack_from_der_sequence(str(buffer)), _pyfree=1)

def split_proxy(proxy):
    u"""
    Разделить содержимое proxy на два списка:
    * certs - сертификаты
    * keys - ключи.

    Возвращает (certs, keys)
    """
    lines = proxy.split("\n")
    result = ([], [])
    state = 3
    endtag = None
    buffer = []
    while len(lines) > 0:
        line = lines[0]
        lines = lines[1:]

        if state != 2:
            buffer.append(line)

        if line == endtag:
            if state < 2:
                result[state].append("\n".join(buffer))
            state = 3
            endtag = None
            buffer = []
            continue
            
        if state == 3:
            what = re.findall("^-----BEGIN (.*)-----$", line)
            if len(what) == 1:
                endtag = "-----END %s-----" % what[0]
                if what[0] == "CERTIFICATE":
                    state = 0
                elif what[0].endswith(" KEY"):
                    state = 1
                else:
                    state = 2
    return result
    
def load_proxy(proxy):
    certs, keys = split_proxy(proxy)
    if len(keys) != 0:
        key = RSA.load_key_string(keys[0])
    else:
        key = None
    chain = X509.X509_Stack()
    for pem in certs:
        chain.push(X509.load_cert_string(pem))

    return key, chain

def sha1sum(buf):
    md = EVP.MessageDigest('sha1')
    md.update(buf)
    return md.final().encode('hex')

def noproxy_chain(stack):
    stk = X509.X509_Stack()
    proxy = True
    for cert in stack:
        if proxy and x509_is_proxy(cert):
            continue
        else:
            proxy = False
        stk.push(cert)

    return stk

def combined_subject_hash(stack):
    md = EVP.MessageDigest('sha1')
    for cert in stack:
        md.update(cert.get_subject().as_der())
    return md.final().encode('hex')

# XXX: выкинуть после того, как исчезнет запуск без делегации и
# пропадет необходимость в функции proxy_owner_hash
__ca_path = "/etc/grid-security/certificates"

def proxy_owner_hash(stack):
    chain = noproxy_chain(stack)
    if not chain[-1].check_ca():
        ca_file = os.path.join(__ca_path, "%08x.0" % chain[-1].get_issuer().as_hash())
        for pem in split_proxy(open(ca_file, "r").read())[0]:
            chain.push(X509.load_cert_string(pem))
        
    return combined_subject_hash(chain)

def rsa_load_pub_key_der(buffer):
    pem = "-----BEGIN PUBLIC KEY-----\n%s-----END PUBLIC KEY-----\n" % buffer.encode('base64')
    return RSA.load_pub_key_bio(BIO.MemoryBuffer(pem))

def load_voms_chain(voms_ac, chain):
    rest = X509.X509_Stack()
    for cert in chain[1:]:
        rest.push(cert)
    cert = chain[0]
    return voms_ac.from_x509_cert_chain(cert, rest)    
