# -*- encoding: utf-8 -*-

import sys, os
import optparse

def main():
    parser = optparse.OptionParser(usage="%prog [options...] command [options...]")
    parser.disable_interspersed_args()
    parser.add_option('-c', '--config',
                      help="Pilot config file (default: pilot.ini in current directory)",
                      default="pilot.ini")

    opts, args = parser.parse_args()

    if len(args) < 1:
        parser.print_usage()
        sys.exit(1)

    if not os.path.exists(opts.config):
        print "Config file %s not found." % opts.config
        sys.exit(1)
        
    sys.argv[1:] = args

    from migrate.versioning.shell import main
    from ConfigParser import SafeConfigParser

    conf = SafeConfigParser()
    conf.read(opts.config)

    if not conf.has_option('app:pilot', 'database.url'):
        print "Config file %s does not have an options [app:pilot]/database.url" % opts.config
        sys.exit(1)

    url = conf.get('app:pilot', 'database.url')

    print "Using database url:", url
    repopath = os.path.join(os.path.split(__file__)[0],
                            'repository')
    print "Using repostirory path:", repopath
    main(url=url,repository=repopath)
