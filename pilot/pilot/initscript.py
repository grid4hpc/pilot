# -*- encoding: utf-8 -*-

from paste.script import command
from paste.util.template import Template
from pkg_resources import resource_string
import os, sys

class WriteInitscript(command.Command):
    max_args = 1
    min_args = 1
    usage = "PREFIX"
    summary = "\nCreate pilot startup scripts for /etc/init.d in files PREFIX-spooler and PREFIX-httpd"
    group_name = "Pilot"
    
    parser = command.Command.standard_parser(verbose=True)
    parser.add_option('-c', dest='config', default='pilot.ini',
                      help="Pilot configuration file (default: %default in current directory)")
    parser.add_option('-p', dest='pidroot', default='/var/run', metavar='DIR',
                      help="Directory where to store pid files (default: %default)")
    parser.add_option('-l', dest='lockroot', default='/var/lock/subsys', metavar='DIR',
                      help="Directory where to place subsystem lock files (default: %default)")
    parser.add_option('-b', dest='bindir', metavar='DIR',
                      default=os.path.join(sys.exec_prefix, 'bin'),
                      help="Path to pilot-* commands (default: %default)")
    parser.add_option('-u', dest='user', metavar='USER',
                      default='pilot',
                      help='Run pilot services as USER (default: %default)')

    def command(self):
        prefix = self.args[0]
        for option in ('config', 'pidroot', 'lockroot'):
            setattr(self.options, option,
                    os.path.abspath(getattr(self.options, option)))

        template = Template(resource_string('pilot', 'templates/rc-script.sh'))
        filename = prefix+'-spooler'
        fd = open(filename, "w")
        fd.write(template.substitute(config=self.options.config,
                                     scriptpath=os.path.abspath(self.args[0]),
                                     pidroot=self.options.pidroot,
                                     user=self.options.user,
                                     bindir=self.options.bindir,
                                     lockdir=self.options.lockroot,
                                     description='GridNNS Pilot Spooler Service (pilot-spooler)',
                                     procname='spooler',
                                     logfiles='pilot-spooler.log',
                                     ))
        fd.close()
        os.chmod(filename, 0755)

        filename = prefix + '-httpd'
        fd = open(filename, "w")
        fd.write(template.substitute(config=self.options.config,
                                     scriptpath=os.path.abspath(self.args[0]),
                                     pidroot=self.options.pidroot,
                                     user=self.options.user,
                                     bindir=self.options.bindir,
                                     lockdir=self.options.lockroot,
                                     description='GridNNS Pilot HTTPD Service (pilot-httpd)',
                                     procname='httpd',
                                     logfiles='pilot-access.log pilot-error.log',
                                     ))
        fd.close()
        os.chmod(filename, 0755)
