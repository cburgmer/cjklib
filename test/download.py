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

import urllib

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

FILES = {'Unihan.zip': 'ftp://ftp.unicode.org/Public/UNIDATA/Unihan.zip',
    'kanjidic2.xml.gz': \
        'http://www.csse.monash.edu.au/~jwb/kanjidic2/kanjidic2.xml.gz',
    }

def main():
    for fileName in sys.argv[1:]:
        source = FILES[fileName]
        print "Downloading %s from %s..." % (fileName, source)
        urllib.urlretrieve(source, fileName, progress)

if __name__ == "__main__":
    main()
