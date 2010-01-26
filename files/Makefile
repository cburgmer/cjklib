installpath=/usr/local/share/cjklib

all=edict cedict cedictgr handedict cfdict

all: $(all)

edict: build/edict.db
cedict: build/cedict.db
cedictgr: build/cedictgr.db
handedict: build/handedict.db
cfdict: build/cfdict.db

build/tmp/edict.gz:
	mkdir -p build/tmp
	cd build/tmp && python ../../downloaddict.py EDICT --targetName=edict.gz

build/tmp/cedict.gz:
	mkdir -p build/tmp
	cd build/tmp && python ../../downloaddict.py CEDICT --targetName=cedict.gz

build/tmp/cedictgr.zip:
	mkdir -p build/tmp
	cd build/tmp && python ../../downloaddict.py CEDICTGR --targetName=cedictgr.zip

build/tmp/handedict.tar.bz2:
	mkdir -p build/tmp
	cd build/tmp && python ../../downloaddict.py HanDeDict --targetName=handedict.tar.bz2

build/tmp/cfdict.tar.bz2:
	mkdir -p build/tmp
	cd build/tmp && python ../../downloaddict.py CFDICT --targetName=cfdict.tar.bz2


build/edict.db: build/tmp/edict.gz
	mkdir -p build/
	python -m cjklib.build.cli -r build EDICT --filePath=build/tmp/edict.gz --database=sqlite:///build/edict.db

build/cedict.db: build/tmp/cedict.gz
	mkdir -p build
	python -m cjklib.build.cli -r build CEDICT --filePath=build/tmp/cedict.gz --database=sqlite:///build/cedict.db

build/cedictgr.db: build/tmp/cedictgr.zip
	mkdir -p build
	python -m cjklib.build.cli -r build CEDICTGR --filePath=build/tmp/cedictgr.zip --database=sqlite:///build/cedictgr.db

build/handedict.db: build/tmp/handedict.tar.bz2
	mkdir -p build
	python -m cjklib.build.cli -r build HanDeDict --filePath=build/tmp/handedict.tar.bz2 --database=sqlite:///build/handedict.db

build/cfdict.db: build/tmp/cfdict.tar.bz2
	mkdir -p build
	python -m cjklib.build.cli -r build CFDICT --filePath=build/tmp/cfdict.tar.bz2 --database=sqlite:///build/cfdict.db

files := $(wildcard build/*.db)
install: $(files)
	install -d $(installpath)
	install -m 644 $(files) $(installpath)

.PHONY: clean
clean:
	rm -rf build/tmp
	rm -rf build/edict.db
	rm -rf build/cedict.db
	rm -rf build/cedictgr.db
	rm -rf build/handedict.db
	rm -rf build/cfdict.db
