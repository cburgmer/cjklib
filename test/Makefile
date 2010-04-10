all=edict cedict cedictgr handedict cfdict unihan kanjidic2

all: $(all)

edict: downloads/EDICT
cedict: downloads/CEDICT
cedictgr: downloads/CEDICTGR
handedict: downloads/HanDeDict
cfdict: downloads/CFDICT
unihan: downloads/Unihan.zip
kanjidic2: downloads/kanjidic2.xml.gz

downloads/EDICT:
	mkdir -p downloads
	rm -f downloads/edict.gz
	python -m cjklib.dictionary.install --download EDICT --targetPath=downloads
	cd downloads && ln -s edict.gz EDICT

downloads/CEDICT:
	mkdir -p downloads
	rm -f downloads/cedict_1_0_ts_utf-8_mdbg.txt.gz
	python -m cjklib.dictionary.install --download CEDICT --targetPath=downloads
	cd downloads && ln -s cedict_1_0_ts_utf-8_mdbg.txt.gz CEDICT

downloads/CEDICTGR:
	mkdir -p downloads
	rm -f downloads/cedictgr.zip
	python -m cjklib.dictionary.install --download CEDICTGR --targetPath=downloads
	cd downloads && ln -s cedictgr.zip CEDICTGR

downloads/HanDeDict:
	mkdir -p downloads
	rm -f downloads/handedict-????????.tar.bz2
	python -m cjklib.dictionary.install --download HanDeDict --targetPath=downloads
	cd downloads && ln -s handedict-????????.tar.bz2 HanDeDict

downloads/CFDICT:
	mkdir -p downloads
	rm -f downloads/cfdict-????????.tar.bz2
	python -m cjklib.dictionary.install --download CFDICT --targetPath=downloads
	cd downloads && ln -s cfdict-????????.tar.bz2 CFDICT

downloads/Unihan.zip:
	mkdir -p downloads
	cd downloads && python ../download.py Unihan.zip

downloads/kanjidic2.xml.gz:
	mkdir -p downloads
	cd downloads && python ../download.py kanjidic2.xml.gz

.PHONY: clean
clean:
	rm -f downloads
