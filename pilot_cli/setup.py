#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages
import sys, os

version = '0.4'

requirements_table = [
    # (egg requirement, centos requirement, fedora requirement)
    ("pytz>=2006p", None, "pytz>=2006p"),
    ("M2Crypto>=0.16", None, "M2Crypto>=0.16"),
    ("simplejson>=2.0.5", "simplejson>=2.0.5", "simplejson>=2.0.5"),
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

setup(name='pilot_cli',
      version=version,
      description="Pilot CLI",
      long_description="""\
Pilot command-line interface utilities""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Lev Shamardin',
      author_email='shamardin@theory.sinp.msu.ru',
      url='http://www.ngrid.ru/trac/wiki/Pilot',
      license='BSD',
      packages=find_packages(exclude=["tests", "tests.*", "*.tests"]),
      package_data = {'pilot_cli': ['schema/*.js']},
      include_package_data=True,
      zip_safe=False,
      install_requires = requirements,
      #entry_points="""
      ## -*- Entry points: -*-
      #""",
      entry_points = {
          'console_scripts': [
              'pilot-job-submit=pilot_cli.job_submit:main',
              'pilot-job-status=pilot_cli.job_status:main',
              'pilot-job-info=pilot_cli.job_info:main',
              'pilot-job-cancel=pilot_cli.job_cancel:main',
              'pilot-job-pause=pilot_cli.job_pause:main',
              'pilot-job-resume=pilot_cli.job_resume:main',
              'pilot-job-matchmake=pilot_cli.job_matchmake:main',
              'pilot-job-generate-rsl=pilot_cli.job_generate_rsl:main',
              'pilot-cancel-my-jobs=pilot_cli.cancel_my_jobs:main',
              'pilot-query-jobs=pilot_cli.query_jobs:main',
              'pilot-task-status=pilot_cli.task_status:main',
              'pilot-uri-helper=pilot_cli.uri_helper:main',
              'pilot-server-version=pilot_cli.server_version:main',
              'pilot-delegation-list=pilot_cli.delegation:list',
              'pilot-delegation-create=pilot_cli.delegation:create',
              'pilot-delegation-update=pilot_cli.delegation:update',
              'pilot-delegation-destroy=pilot_cli.delegation:destroy',
              ],
         }
      )
