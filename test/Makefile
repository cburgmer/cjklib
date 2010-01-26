all=edict cedict cedictgr handedict cfdict unihan kanjidic2

all: $(all)

edict: EDICT
cedict: CEDICT
cedictgr: CEDICTGR
handedict: HanDeDict
cfdict: CFDICT
unihan: Unihan.zip
kanjidic2: kanjidic2.xml.gz

EDICT:
	python ../files/downloaddict.py --softLink EDICT

CEDICT:
	python ../files/downloaddict.py --softLink CEDICT

CEDICTGR:
	python ../files/downloaddict.py --softLink CEDICTGR

HanDeDict:
	python ../files/downloaddict.py --softLink HanDeDict

CFDICT:
	python ../files/downloaddict.py --softLink CFDICT

Unihan.zip:
	python download.py Unihan.zip

kanjidic2.xml.gz:
	python download.py kanjidic2.xml.gz

.PHONY: clean
clean:
	rm -f EDICT edict.gz
	rm -f CEDICT cedict_1_0_ts_utf-8_mdbg.txt.gz
	rm -f CEDICTGR cedictgr.zip
	rm -f HanDeDict handedict-????????.tar.bz2
	rm -f CFDICT cfdict-????????.tar.bz2
	rm -f Unihan.zip
	rm -f kanjidic2.xml.gz
