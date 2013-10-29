#!/bin/sh

if [[ "$1" == "" ]] ; then
	PYTHON=python
else
	PYTHON=$1
fi

$PYTHON bootstrap.py --download-base=cache/dist -d
