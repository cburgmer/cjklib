#!/usr/bin/perl
# -*- coding: utf-8 -*-

"""
Takes a list of characters and their reading and generates entries for variant
forms.

This script was used to add traditional character mappings to the
ShanghaineseIPA set.

2010 Christoph Burgmer (cburgmer@ira.uka.de)

License: MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import csv

from cjklib.characterlookup import CharacterLookup
from cjklib.util import UnicodeCSVFileIterator

class Mapper(object):
    def __init__(self, variant='T'):
        self.characterLookup = CharacterLookup('T')
        self.variant = variant

    def mapEntry(self, char, reading):
        entries = []
        for var in self.characterLookup.getCharacterVariants(char,
            self.variant):
            entries.append((var, reading))
        return entries

def _getCSVReader(handle):
    class DefaultDialect(csv.Dialect):
        """Defines a default dialect for the case sniffing fails."""
        quoting = csv.QUOTE_NONE
        delimiter = ','
        lineterminator = '\n'
        quotechar = "'"
        # the following are needed for Python 2.4
        escapechar = "\\"
        doublequote = True
        skipinitialspace = False

    def prependLineGenerator(line, data):
        """
        The first line red for guessing format has to be reinserted.
        """
        yield line
        for nextLine in data:
            yield nextLine

    line = '#'
    try:
        while line.strip().startswith('#'):
            line = handle.next()
    except StopIteration:
        return csv.reader(handle)
    try:
        dialect = csv.Sniffer().sniff(line, ['\t', ','])
        # fix for Python 2.4
        if len(dialect.delimiter) == 0:
            raise csv.Error()
    except csv.Error:
        dialect = DefaultDialect()

    content = prependLineGenerator(line, handle)
    return csv.reader(content, dialect=dialect)


def main():
    variant = 'T'
    if '--variant' in sys.argv:
        variant = sys.argv[sys.argv.index('--variant') + 1]
    newOnly = '--newonly' in sys.argv
    ambiguousOnly = '--ambiguousonly' in sys.argv

    mapper = Mapper(variant)
    csvReader = _getCSVReader(sys.stdin)
    csvWriter = csv.writer(sys.stdout, dialect=csvReader.dialect)
    for lineIdx, entry in enumerate(csvReader):
        if len(entry) != 2:
            raise ValueError("Need two cells %i: %r" % (lineIdx, entry))
        char, reading = [s.decode("utf-8") for s in entry]

        entries = mapper.mapEntry(char, reading)
        if ambiguousOnly and len(entries) < 2:
            continue
        if not newOnly and (char, reading) not in entries:
            entries.insert(0, (char, reading))

        for mappedEntry in entries:
            csvWriter.writerow([s.encode("utf-8") for s in mappedEntry])

if __name__ == "__main__":
    main()
