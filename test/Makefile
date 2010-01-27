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
	cd downloads && python ../../files/downloaddict.py --softLink EDICT

downloads/CEDICT:
	mkdir -p downloads
	cd downloads && python ../../files/downloaddict.py --softLink CEDICT

downloads/CEDICTGR:
	mkdir -p downloads
	cd downloads && python ../../files/downloaddict.py --softLink CEDICTGR

downloads/HanDeDict:
	mkdir -p downloads
	cd downloads && python ../../files/downloaddict.py --softLink HanDeDict

downloads/CFDICT:
	mkdir -p downloads
	cd downloads && python ../../files/downloaddict.py --softLink CFDICT

downloads/Unihan.zip:
	mkdir -p downloads
	cd downloads && python ../download.py Unihan.zip

downloads/kanjidic2.xml.gz:
	mkdir -p downloads
	cd downloads && python ../download.py kanjidic2.xml.gz

.PHONY: clean
clean:
	rm -f downloads
