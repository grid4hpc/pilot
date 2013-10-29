This file is for you to describe the pilot application. Typically
you would include information such as the information below:

Installation and Setup
======================

Detailed installation guides for development version of pilot and cli are
available at:

    http://www.ngrid.ru/trac/wiki/PilotCliInstallationGuide
    http://www.ngrid.ru/trac/wiki/PilotServerSvn

Install ``pilot`` using easy_install::

    easy_install pilot

You may also use ``pip`` as an alternative.

Configuration (if installed from source)
========================================

Make a config file as follows::

    paster make-config pilot config.ini

You must run this command from the directory where you unpacked the
sources for building.

Tweak the config file as appropriate and then setup the application::

    paster setup-app config.ini

Generate the init scripts if required, run this command from the
directory where you unpacked the sources::

    paster pilot_initscript pilot

This will generate two scripts, pilot-httpd and pilot-spooler which
will start pilot services using `daemonize`_.

_`daemonize`: http://www.clapper.org/software/daemonize/

Configuration (if installed from RPM)
=====================================

1. Install additional database modules. For Python < 2.5 (CentOS) you
   need python-sqlite2 for SQLite database support or python-psycopg2
   for PosgreSQL. On systems with Python >= 2.5 SQLite support is
   bundled with system python, and you need python-psycopg2 for
   PosgreSQL. You may install these modules running command::

       yum install python-sqlite2
       yum install python-psycopg2

2. Edit config file in /etc/pilot/pilot.ini. You should change at
   least account_access, and you also need to edit database.url if you
   are using PostgreSQL.

   PostgreSQL Notice: Pilot user must be able to change pilot database
   schema (CREATE TABLE, DROP TABLE, ALTER TABLE).

3. Update or create the database schema::

       pilot-manage-db -c /etc/pilot/pilot.ini

4. Enable pilot services autostart if required::

       chkconfig --level 345 pilot-httpd on
       chkconfig --level 345 pilot-spooler on

Updating pilot
==============

1. If you are using pilot RPMs, install the new package(s) using yum
   or rpm. If you are using pilot built from source install the new
   version and remove the old one.

2. Check and update the database schema. Run the following command::

       pilot-manage-db -c /etc/pilot/pilot.ini

   Notice: your pilot config file may be located in other place if you
   are using a version built from source.

3. Restart the services and check for errors in log. If there are any
   new mandatory config options which are missing from the config file
   pilot will servces will refuse to start and log the errors about
   the missing options.
