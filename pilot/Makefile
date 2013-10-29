.PHONY: sources dist srpm test-coverage version

#svnrev=$(shell cat version)
svnrev=$(shell ./get-svnrev.sh)

sources: pilot.spec dist/pilot-0.1dev-r$(svnrev).tar.gz

pilot.spec: pilot.spec.in version
	sed -e "s/@SVNREV@/$(svnrev)/" pilot.spec.in > pilot.spec

dist/pilot-0.1dev-r$(svnrev).tar.gz: version
	python setup.py egg_info -Rb dev-r$(svnrev) sdist

dist: version
	svnrev=$(shell cat version)
	python setup.py egg_info -Rb dev-r$(svnrev) sdist

version:
	./get-svnrev.sh > version

srpm: sources
	rpmbuild-md5 --define "_sourcedir dist" --define "_srcrpmdir ." --define "dist .el5.centos" -bs pilot.spec

clean:
	rm -rf *.rpm dist

test-coverage:
	nosetests --with-coverage --cover-erase --cover-html --cover-html-dir coverage_report --cover-package=pilot. tests
