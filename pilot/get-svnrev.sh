#!/bin/sh

if [ -e .svn ] ; then
  info_cmd='svn info'
else
  info_cmd='git svn info'
fi

res=`$info_cmd 2>/dev/null | awk '/Last Changed Rev/ { print int($(NF)) }'`
if [ "x$res" == "x0" ] ; then
	echo "HEAD"
else
	echo $res
fi
