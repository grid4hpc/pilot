# -*- encoding: utf-8 -*-

from distutils import dir_util
import os
import optparse
import shutil
import sys

from M2Crypto import X509
from pilot.spooler import config, load_config_file
from mako.template import Template

def template_name(filename):
    here = os.path.dirname(__file__)
    template = os.path.normpath(
        os.path.join(here, "templates/apache/%s" % filename))
    return template

def find_template(filename):
    return Template(filename=template_name(filename))

def parse_args():
    parser = optparse.OptionParser(usage="%prog [options...] output_directory")
    parser.add_option('-c', type='string', metavar='FILE',
                      help='Configuration file to use (default: %default)',
                      dest='configfile', default='pilot.ini')
        
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.print_usage()
        sys.exit(1)

    return opts, args

def detect_hostname():
    x509 = X509.load_cert(config.common_ssl_certificate)
    subject = x509.get_subject()
    if 'CN' not in subject.nid:
        log.fatal("No CN field in certificate subject")
        sys.exit(1)

    cn = subject.get_entries_by_nid(subject.nid['CN'])[0].get_data().as_text()
    hostname = cn.split('/')[-1]
    return hostname

def main():
    opts, args = parse_args()
    load_config_file(opts.configfile)
    
    here = os.path.normpath(os.path.abspath(args[0]))
    if os.path.exists(here):
        print "Warning: directory %s exists, files may be overwritten. Continue?" % here
        yn = raw_input()
        if not yn.lower().startswith('y'):
            sys.exit(1)
    else:
        dir_util.mkpath(here)

    vars = dict(
        server_name=detect_hostname(),
        server_root=here,
        hostcert = config.common_ssl_certificate,
        hostkey = config.common_ssl_privatekey,
        capath = config.common_ssl_capath,
        user = config.common_user,
        group = config.common_group,
        configfile = os.path.abspath(opts.configfile),
        paths = repr(sys.path),
    )
    os.chdir(here)
    for template in ("httpd.conf", "httpd", "wsgi_handler.py",):
        open(template, "wt").write(find_template(template).render(**vars))
    shutil.copy(template_name("functions"), "functions")
    os.chmod("httpd", 0755)
    if not os.path.exists("html"):
        os.mkdir("html")
    
    
