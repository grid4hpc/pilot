.PHONY: sources dist srpm

#svnrev=$(shell cat version)
svnrev=$(shell ./get-svnrev.sh)

sources: pilot-cli.spec dist/pilot_cli-0.1dev-r$(svnrev).tar.gz

pilot-cli.spec: pilot-cli.spec.in version
	sed -e "s/@SVNREV@/$(svnrev)/" pilot-cli.spec.in > pilot-cli.spec

dist/pilot_cli-0.1dev-r$(svnrev).tar.gz: version
	python setup.py egg_info -Rb dev-r$(svnrev) sdist

dist:
	./get-svnrev.sh > version
	python setup.py egg_info -Rb dev-r$(svnrev) sdist

srpm: sources
	rpmbuild-md5 --define "_sourcedir dist" --define "_srcrpmdir ." --define "dist .el5.centos" -bs pilot-cli.spec
