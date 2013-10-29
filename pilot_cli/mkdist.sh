#!/bin/sh

if [ -f /etc/redhat-release ] ; then
  release_name=`cat /etc/redhat-release | cut -d ' ' -f 1 | tr '[:upper:]' '[:lower:]'`
  release_ver=`cat /etc/redhat-release | egrep -o 'release [[:digit:]]+' | cut -d' ' -f 2`
  case $release_name in
      fedora)
          distcode="fc$release_ver"
          ;;
      redhat|centos)
          distcode="el$release_ver"
          ;;
      *)
          distcode="rh$release_ver"
          ;;
  esac
else
  distcode="linux-`uname -i`"
fi

if [ -d .svn ] ; then
    revline=`svn info | grep Revision:`
else
    revline=`git svn info | grep Revision:`
fi

svn_rev=`echo $revline | cut -d ' ' -f 2`

pkgname=`python setup.py --name`
python setup.py egg_info -Rb dev-r$svn_rev > /dev/null 2>&1
version=`cat $pkgname.egg-info/PKG-INFO | grep ^Version: | cut -d ' ' -f 2`
dist_filename="$pkgname-$version.$distcode"

echo '******************************************************'
echo Building $dist_filename.tar.gz
echo '******************************************************'
echo

cli_dist=`mktemp -d cli-dist.XXXXXX`
./create_env.py -n $cli_dist
pushd $cli_dist
if [ -L lib64 ] ; then
  rm lib64
  ln -s lib lib64 ;
fi
popd
. ./$cli_dist/bin/activate
python setup.py egg_info -Rb dev-r$svn_rev install

python ext_dist/virtualenv-1.3.3.py --relocatable $cli_dist

pushd $cli_dist/bin
rm -f easy_install easy_install-2.4 pip virtualenv python python2.4
( head -2 pilot-job-submit ; sed -e 1d proxy_init ) > pygsi-proxy-init
( head -2 pilot-job-submit ; sed -e 1d proxy_destroy ) > pygsi-proxy-destroy
( head -2 pilot-job-submit ; sed -e 1d proxy_info ) > pygsi-proxy-info
rm -f proxy_init proxy_destroy proxy_info
chmod a+x pygsi-proxy-*
popd

pushd $cli_dist/lib/python2.4/site-packages
rm -rf virtualenv* support-files rebuild-script* refresh-support-files* setup.py*
popd

tmp=`mktemp -d tmp.XXXXXX`
pushd $tmp
mv ../$cli_dist pilot_cli
rm -f $dist_filename.tar.gz
tar cvfz ../$dist_filename.tar.gz pilot_cli/
popd
rm -rf $tmp
mkdir -p dist
mv $dist_filename.tar.gz dist/
