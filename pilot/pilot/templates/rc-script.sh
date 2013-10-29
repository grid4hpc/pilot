#!/bin/bash
#
# GridNNS Pilot Service
#
# chkconfig: - 85 15
# description: {{description}}
# processname: pilot-{{procname}}
# config: {{config}}
# pidfile: {{pidroot}}/pilot-{{procname}}.pid

. /etc/init.d/functions
. /etc/profile

LOGFILES="{{logfiles}}"
LOGROOT="/var/log"

check_logfiles() {
    for logfile in $LOGFILES ; do
        filename="$LOGROOT/$logfile"
        if [ ! -e $filename ] ; then
            touch $filename
            chmod 640 $filename
            chown {{user}} $filename
        fi
    done
}

start() {
    echo -n $"Starting pilot-{{procname}}: "
    check_logfiles > /dev/null 2>&1
    daemon daemonize -u {{user}} -p {{pidroot}}/pilot-{{procname}}.pid -l {{lockdir}}/pilot-{{procname}} {{bindir}}/pilot-{{procname}} -c {{config}}
    RETVAL=$?
    echo
    return $RETVAL
}

stop() {
    echo -n $"Shutting down pilot-{{procname}}: "
    killproc -p {{pidroot}}/pilot-{{procname}}.pid pilot-{{procname}}
    RETVAL=$?
    [ $RETVAL -eq 0 ] && rm -f {{pidroot}}/pilot-{{procname}}.pid
    [ $RETVAL -eq 0 ] && rm -f {{lockdir}}/pilot-{{procname}}
    echo
    return $RETVAL
}

restart() {
    stop
    start
}

rhstatus() {
    status -p {{pidroot}}/pilot-{{procname}}.pid pilot-{{procname}}
}

condrestart() {
    [ -e {{lockdir}}/pilot-{{procname}} ] && restart
    return 0
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    condrestart)
        condrestart
        ;;
    status)
        rhstatus
        ;;
    *)
        echo $"Usage: $0 {start|stop|restart|status}"
        exit 2
esac

exit $?
