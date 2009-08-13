#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of cjklib.
#
# cjklib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cjklib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cjklib.  If not, see <http://www.gnu.org/licenses/>.

"""
Automatically downloads external files to test against the build process.
"""

import re
import os
import os.path
import stat
import urllib
import urlparse

from cjklib.build import warn


class DictionaryDownloader:
    DOWNLOADER_NAME = 'default'
    DEFAULT_DOWNLOAD_PAGE = None
    DOWNLOAD_REGEX = None

    def __init__(self):
        self.downloadUrl = None

    def getDownloadLink(self):
        if self.downloadUrl == None:
            print "Getting download page...",
            f = urllib.urlopen(self.DEFAULT_DOWNLOAD_PAGE)
            downloadPageContent = f.read()
            f.close()

            matchObj = self.DOWNLOAD_REGEX.search(downloadPageContent)
            if not matchObj:
                raise IOError('cannot read download page')

            baseUrl = matchObj.group(1)
            self.downloadUrl = urlparse.urljoin(self.DEFAULT_DOWNLOAD_PAGE,
                baseUrl)
            print "done"

        return self.downloadUrl

    def download(self):
        link = self.getDownloadLink()
        _, _, onlinePath, _, _ = urlparse.urlsplit(link)
        fileName = os.path.basename(onlinePath)

        print "Downloading %s..." % link
        urllib.urlretrieve(link, fileName, progress)
        print "Checking for previous symlink...",
        if os.path.exists(self.DOWNLOADER_NAME):
            if stat.S_ISLNK(os.lstat(self.DOWNLOADER_NAME)[stat.ST_MODE]):
                os.remove(self.DOWNLOADER_NAME)
                print "done"
            else:
                print "failed"
                return
        print "Creating symlink to %s" % self.DOWNLOADER_NAME,
        os.symlink(fileName, self.DOWNLOADER_NAME)
        print "done"


class HanDeDictDownloader(DictionaryDownloader):
    DOWNLOADER_NAME = 'HanDeDict'
    DEFAULT_DOWNLOAD_PAGE \
        = u'http://www.chinaboard.de/chinesisch_deutsch.php?mode=dl'
    DOWNLOAD_REGEX = re.compile(
        u'<a href="(handedict/handedict-(?:\d+).tar.bz2)">')


class CFDICTDownloader(DictionaryDownloader):
    DOWNLOADER_NAME = 'CFDICT'
    DEFAULT_DOWNLOAD_PAGE = u'http://www.chinaboard.de/cfdict.php?mode=dl'
    DOWNLOAD_REGEX = re.compile(u'<a href="(cfdict/cfdict-(?:\d+).tar.bz2)">')


class CEDICTDownloader(DictionaryDownloader):
    DOWNLOADER_NAME = 'CEDICT'
    DEFAULT_DOWNLOAD_PAGE \
        = u'http://www.mdbg.net/chindict/chindict.php?page=cc-cedict'
    DOWNLOAD_REGEX = re.compile(
        u'<a href="(export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz)">')


class CEDICTGRDownloader(DictionaryDownloader):
    DOWNLOADER_NAME = 'CEDICTGR'
    DOWNLOAD_LINK = u'http://home.iprimus.com.au/richwarm/gr/cedictgr.zip'

    def getDownloadLink(self):
        return self.DOWNLOAD_LINK


class EDICTDownloader(DictionaryDownloader):
    DOWNLOADER_NAME = 'EDICT'
    DOWNLOAD_LINK = u'http://ftp.monash.edu.au/pub/nihongo/edict.gz'

    def getDownloadLink(self):
        return self.DOWNLOAD_LINK


try:
    from progressbar import *
    widgets = [Percentage(), ' ', Bar(), ' ', ETA(), ' ', FileTransferSpeed()]
    def progress(i, chunkSize, total):
        global pbar
        if i == 0:
            global widgets
            pbar = ProgressBar(widgets=widgets, maxval=total/chunkSize+1)
            pbar.start()
        pbar.update(min(i, total/chunkSize+1))

except ImportError:
    def progress(i, chunkSize, total):
        print '#',

CLASS_DICT = {'CEDICT': CEDICTDownloader, 'HanDeDict': HanDeDictDownloader,
    'CFDICT': CFDICTDownloader, 'CEDICTGR': CEDICTGRDownloader,
    'EDICT': EDICTDownloader}

def main():
    print "Starting download"
    # Get Unihan.zip
    unihanSource = 'ftp://ftp.unicode.org/Public/UNIDATA/Unihan.zip'
    print "Downloading Unihan.zip from %s..." % unihanSource
    urllib.urlretrieve(unihanSource, 'Unihan.zip', progress)

    # Get KANJIDIC2
    kanjidicSource \
        = 'http://www.csse.monash.edu.au/~jwb/kanjidic2/kanjidic2.xml.gz'
    print "Downloading kanjidic2.xml.gz from %s..." % kanjidicSource
    urllib.urlretrieve(kanjidicSource, 'kanjidic2.xml.gz', progress)

    # Get Dictionaries
    for dictionary, downloaderClass in CLASS_DICT.items():
        print "Downloading %s" % dictionary
        downloaderClass().download()

if __name__ == "__main__":
    main()
