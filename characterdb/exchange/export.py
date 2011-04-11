#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Exports a data set from characterdb.cjklib.org and prints a CSV list to stdout.

Copyright (c) 2008, 2010, Christoph Burgmer

Released unter the MIT License.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import urllib
import codecs
import sys
import re
import logging

QUERY_URL = ("http://characterdb.cjklib.org/wiki/Special:Ask/"
             "%(query)s/%(properties)s/format=csv/sep=,/headers=hide/"
             "limit=%(limit)d/offset=%(offset)d")
"""Basic query URL."""

MAX_ENTRIES = 100
"""Maximum entries per GET request."""

#class AppURLopener(urllib.FancyURLopener):
    #version="Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"

#urllib._urlopener = AppURLopener()

def decompositionEntryPreparator(entryList):
    columns = ['glyph', 'decomposition']
    entryDict = dict(zip(columns, entryList))

    character, glyphIndex = entryDict['glyph'].split('/', 1)

    decomp = entryDict.get('decomposition', '').strip('"')
    decompositionEntries = re.findall('([^ ,]+); (\d+)', decomp)

    entries = []
    for decomposition, index in decompositionEntries:
        entries.append((character, 
                        re.sub(r'(\D)/(\d+)', r'\1[\2]', decomposition),
                        glyphIndex, index, ''))

    return entries

def strokeorderEntryPreparator(entryList):
    columns = ['glyph', 'strokeorder']
    entryDict = dict(zip(columns, entryList))

    character, glyphIndex = entryDict['glyph'].split('/', 1)
    if 'strokeorder' in entryDict:
        return [(character, entryDict['strokeorder'].strip('"'), glyphIndex, '')]
    else:
        return []

def localeEntryPreparator(entryList):
    columns = ['glyph', 'locale']
    entryDict = dict(zip(columns, entryList))

    character, glyphIndex = entryDict['glyph'].split('/', 1)

    locales = entryDict.get('locale', '').strip('"')
    localeEntries = sorted(re.findall(r'(\w)', locales))

    if localeEntries:
        return [(character, glyphIndex, ''.join(localeEntries))]
    else:
        return []

DATA_SETS = {'characterdecomposition':
                ({'query': '[[Category:Glyph]] [[Decomposition::!]]',
                  'properties': ['Decomposition']},
                 decompositionEntryPreparator),
             'strokeorder':
                ({'query': '[[Category:Glyph]] [[ManualStrokeOrder::!]]', 'properties': ['ManualStrokeOrder']},
                 strokeorderEntryPreparator),
             'strokeorder_all':
                ({'query': '[[Category:Glyph]] [[StrokeOrder::!]]', 'properties': ['StrokeOrder']},
                 strokeorderEntryPreparator),
             'localecharacterglyph':
                ({'query': '[[Category:Glyph]] [[ManualLocale::!]]', 'properties': ['Locale']},
                 localeEntryPreparator),
            }
"""Defined download sets."""

def getDataSetIterator(name):
    try:
        parameter, preparatorFunc = DATA_SETS[name]
    except KeyError:
        raise ValueError("Unknown data set %r" % name)

    parameter = parameter.copy()
    if 'properties' in parameter:
        parameter['properties'] = '/'.join(('?' + prop) for prop
                                           in parameter['properties'])

    codecReader = codecs.getreader('UTF-8')
    run = 0
    while True:
        queryDict = {'offset': run * MAX_ENTRIES, 'limit': MAX_ENTRIES}
        queryDict.update(parameter)

        query = QUERY_URL % queryDict
        query = urllib.quote(query, safe='/:=').replace('%', '-')
        logging.info("Opening %r" % query)
        try:
            f = codecReader(urllib.urlopen(query))
        except IOError:
            # Try to catch time out
            f = codecReader(urllib.urlopen(query))

        lineCount = 0
        line = f.readline()
        while line:
            line = line.rstrip('\n')
            entry = re.findall(r'"[^"]+"|[^,]+', line)
            if preparatorFunc:
                for e in preparatorFunc(entry):
                    yield e
            else:
                yield entry

            lineCount += 1
            line = f.readline()

        f.close()
        logging.info("  read %d/%d entries" % (lineCount, MAX_ENTRIES))
        if lineCount < MAX_ENTRIES:
            break
        run += 1


def main():
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) != 2:
        print """usage: python export.py DATA_SET
Exports a data set from characterdb.cjklib.org and prints a CSV list to stdout.

Available data sets:"""
        print "\n".join(('  ' + name) for name in DATA_SETS.keys())
        sys.exit(1)

    for a in getDataSetIterator(sys.argv[1].lower()):
        print ','.join(('"%s"' % cell) for cell in a).encode('utf8')


if __name__ == "__main__":
    main()
