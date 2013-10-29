try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from distutils.command.build import build
from distutils.core import Command
from distutils.spawn import spawn
from distutils import log

try:
    import pilot_lib
except ImportError:
    pass

import os, sys
from distutils.core import Extension

class OpensslBuilder(build_ext):
    """
    Specialization of build_ext to enable swig_opts to inherit any
    include_dirs settings made at the command line or in a setup.cfg
    file
    """

    user_options = build_ext.user_options + [
        ('openssl=', 'o', 'Prefix for openssl installation location'),
        ('swig-extra=', None, 'Extra swig options')]
    
    def initialize_options(self):
        build_ext.initialize_options(self)
        self.swig_extra = None
        if os.name == 'nt':
            self.libraries = ['ssleay32', 'libeay32']
            self.openssl = 'c:\\pkg'
        else:
            self.libraries = ['ssl', 'crypto']
            self.openssl = '/usr'

    def finalize_options(self):
        build_ext.finalize_options(self)

        openssl_include = os.path.join(self.openssl, 'include')
        openssl_lib = os.path.join(self.openssl, 'lib')

        self.swig_opts = ['-I%s' % i for i in self.include_dirs + [openssl_include]] + ['-includeall', '-noproxy']
        if self.swig_extra is not None:
            if hasattr(self.swig_extra, 'pop'):
                self.swig_opts.extend(self.swig_extra)
            else:
                self.swig_opts.append(self.swig_extra)

        self.include_dirs.append(openssl_include)
        self.library_dirs.append(openssl_lib)

m2_ext = Extension(name="pilot.lib.m2_ext",
                   sources=["swig/m2_ext.i"],
                   extra_compile_args=["-DTHREADING"])

requirements_table = [
    # (egg requirement, centos requirement, fedora requirement)
    ("Pylons==0.9.7", None, None),
    ("SQLAlchemy>=0.5.6", "SQLAlchemy>=0.5.6", None),
    ("sqlalchemy-migrate>=0.5.3", None, None),
    ("elementtree>=1.2.6", None, None),
    ("M2Crypto>=0.20.1", "M2Crypto>=0.20.1", None),
    ("ngrid", None, None),
    ("gridproxy", None, None),
    ("eventlet", None, None),
    ("Paste", None, None),
    ("PasteDeploy", None, None),
    ("pilot_cli", None, None),
    ("zope.interface", None, None),
    ("werkzeug", None, None),
    ]

requirements = []
if '--for-epel' in sys.argv:
    idx = sys.argv.index('--for-epel')
    sys.argv.pop(idx)
    r_idx = 1
elif '--for-fedora' in sys.argv:
    idx = sys.argv.index('--for-fedora')
    sys.argv.pop(idx)
    r_idx = 2
else:
    r_idx = 0
for r in requirements_table:
    if r[r_idx] is not None:
        requirements.append(r[r_idx])

setup(
    name='pilot',
    version='0.4',
    description='GridNNS Job Management System',
    author='Lev Shamardin',
    author_email='shamardin@theory.sinp.msu.ru',
    license='BSD',
    url='http://www.ngrid.ru/trac/',
    install_requires = requirements,
    setup_requires=["PasteScript>=1.6.3"],
    ext_modules = [m2_ext],
    cmdclass = {'build_ext': OpensslBuilder,
                },
    packages=find_packages(exclude=['ez_setup', 'tests', 'tools']),
    include_package_data=True,
    test_suite='nose.collector',
    package_data={'pilot': ['i18n/*/LC_MESSAGES/*.mo']},
    #message_extractors={'pilot': [
    #        ('**.py', 'python', None),
    #        ('templates/**.mako', 'mako', {'input_encoding': 'utf-8'}),
    #        ('public/**', 'ignore', None)]},
    zip_safe=False,
    paster_plugins=['PasteScript', 'Pylons'],
    entry_points="""
    [paste.app_factory]
    main = pilot.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [paste.paster_command]
    pilot_initscript=pilot.initscript:WriteInitscript

    [console_scripts]
    pilot-spooler=pilot.spooler.main:main
    pilot-httpd=pilot.lib.paste_server:main
    pilot-werk=pilot.lib.werk:main
    pilot-manage-db=pilot.model.manage:main
    pilot-apache-config=pilot.apacheconfig:main
    pilot-stager=pilot.spooler.stager:main
    """,
)
