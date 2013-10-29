#!/bin/sh

if [ -e .svn ] ; then
  info_cmd='svn info'
else
  info_cmd='git svn info'
fi

$info_cmd | awk '/Last Changed Rev/ { print $(NF) }'
