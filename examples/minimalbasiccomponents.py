#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Provides a class to create a set of minimal basic components of Chinese
characters.

2008 Christoph Burgmer (cburgmer@ira.uka.de)

License: MIT License

Copyright (c) 2008 Christoph Burgmer

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

@todo Impl: Be locale dependant.
@todo Impl: How to handle radical/equivalent forms?
"""
from sqlalchemy import select, union

from cjklib import dbconnector
from cjklib import characterlookup

characterSet = 'GB2312Set'

minimalBasicComponents = set()
"""Set of minimal basic components."""
fullyDecomposedCharacters = set()
"""
Set of characters with decomposed components completely contained in
minimalBasicComponents.
"""
db = dbconnector.getDBConnector()
decompositionTable = db.tables['CharacterDecomposition']
strokeOrderTable = db.tables['StrokeOrder']
charsetTable = db.tables[characterSet]

characterQueue = set(db.selectRows(union(
    select([decompositionTable.c.ChineseCharacter,
            decompositionTable.c.Glyph],
        decompositionTable.c.ChineseCharacter.in_(
            select([charsetTable.c.ChineseCharacter])),
        distinct=True),
    select([strokeOrderTable.c.ChineseCharacter,
            strokeOrderTable.c.Glyph],
        strokeOrderTable.c.ChineseCharacter.in_(
            select([charsetTable.c.ChineseCharacter])),
        distinct=True))))

"""Queue of characters needed to be checked."""
characterDecomposition = {}
"""Mapping of character to its decomposition(s)."""

cjk = characterlookup.CharacterLookup('T')

# get mappings
for char, glyph in characterQueue.copy():
    decompositions = cjk.getDecompositionEntries(char, glyph=glyph)
    if decompositions:
        characterDecomposition[(char, glyph)] = decompositions
    else:
        characterQueue.remove((char, glyph))
        minimalBasicComponents.add(char)

# process queue
while characterQueue:
    for charEntry in characterQueue.copy():
        fullyDecomposed = True
        for decomposition in characterDecomposition[charEntry]:
            # check all sub characters
            for subCharEntry in decomposition:
                if type(subCharEntry) == type(u''):
                    # skip IDS operators
                    continue

                subChar, subCharGlyph = subCharEntry
                if subChar == u'？':
                    continue

                if subCharEntry in fullyDecomposedCharacters:
                    continue

                if subCharEntry not in minimalBasicComponents:
                    # sub character is not yet decided on
                    if subCharEntry not in characterQueue:
                        # check if this character wasn't included in the queue
                        #   because it doesn't belong to the characterSet
                        decompositions = cjk.getDecompositionEntries(subChar,
                            glyph=subCharGlyph)
                        if decompositions:
                            # add this sub character and return "not yet
                            #   decomposed"
                            characterDecomposition[subCharEntry] \
                                = decompositions
                            characterQueue.add(subCharEntry)
                            fullyDecomposed = False
                        else:
                            # no decomposition for this character -> minimal
                            minimalBasicComponents.add(subChar)
                    else:
                        fullyDecomposed = False
                        break
        if fullyDecomposed:
            # all sub components are minimal basic components or are already
            #   fully decomposed
            characterQueue.remove(charEntry)
            fullyDecomposedCharacters.add(charEntry)

print "".join(minimalBasicComponents).encode('utf8')
