#!/bin/sh

cat > cache.cfg <<EOF
[buildout]
extends = buildout.cfg
newest = false
install-from-cache = true

EOF

./bin/buildout -c cache.cfg
rm -f cache.cfg
