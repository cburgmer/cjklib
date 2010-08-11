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
Creates locale specific decomposition entries for data without specific glyph
information:

1. Read in glyph data from the three files: Decomposition, StrokeOrder,
   LocaleMapping

2. Unify per glyph

3. Bring into an order such that a glyph is only tackled after its components
   have been tackled (as the components can undergo changes)

4. For each locale check if a specific glyph needs to be created. If this is so,
   copy decomposition and stroke order data and adapt the former.

   - In case a glyph was attached to one or more locales and in this process has
     lost all mappings, delete this glyph

5. Write out new data (3 files again)

To use diff to compare the former list with the new, you can run
$ python scripts/localespecificdecomposition.py -n
to yield the original list in a "sorted" order equal to the full run.

As the script cannot guarantee to cover all special cases, it throws out some
warnings that should be checked manually. Of course owing to the idea of the
whole mapping, locale dependent entries might be generated though not
appropriate.

2010 Christoph Burgmer (cburgmer@ira.uka.de)
"""

import sys
import codecs
from optparse import OptionParser
from collections import namedtuple
import itertools

import cjklib
from cjklib.characterlookup import CharacterLookup
from cjklib import util

Glyph = namedtuple('Glyph', 'decompositions strokeOrder locales')

class GlyphReader(object):
    def __init__(self, decompositionFilePath, strokeOrderFilePath,
        localeFilePath):
        self.decompositionFilePath = decompositionFilePath
        self.strokeOrderFilePath = strokeOrderFilePath
        self.localeFilePath = localeFilePath

    def read(self):
        def createGlyph(char, glyphIdx):
            if char in decompositionEntries:
                decompositions = decompositionEntries[char].get(glyphIdx, [])
            else:
                decompositions = []
            if char in strokeOrderEntries:
                strokeOrder = strokeOrderEntries[char].get(glyphIdx, None)
            else:
                strokeOrder = None
            if char in localeEntries:
                locales = localeEntries[char].get(glyphIdx, [])
            else:
                locales = []
            return Glyph(decompositions, strokeOrder, locales)

        decompositionEntries = GlyphReader.readDecomposition(
            self.decompositionFilePath)
        strokeOrderEntries = GlyphReader.readStrokeOrder(
            self.strokeOrderFilePath)
        localeEntries = GlyphReader.readLocaleMapping(self.localeFilePath)

        # unify data
        glyphEntries = {}
        characters = set(decompositionEntries.keys() + strokeOrderEntries.keys()
            + localeEntries.keys())
        for char in characters:
            glyphEntries[char] = {}

            glyphs = set(decompositionEntries.get(char, {}).keys()
                + strokeOrderEntries.get(char, {}).keys()
                + localeEntries.get(char, {}).keys())
            for glyphIdx in glyphs:
                glyphEntries[char][glyphIdx] = createGlyph(char, glyphIdx)

        return glyphEntries

    @staticmethod
    def decompositionFromString(decomposition):
        # taken from CharacterLookup, but adapted to return None if no glyph
        #   given
        componentsList = []
        index = 0
        while index < len(decomposition):
            char = decomposition[index]
            if CharacterLookup.isIDSOperator(char):
                componentsList.append(char)
            else:
                # is Chinese character
                # Special handling for surrogate pairs on UCS-2 systems
                if util.isValidSurrogate(decomposition[index:index+2]):
                    char = decomposition[index:index+2]  # A surrogate pair now
                    index += 1  # Bypass trailing surrogate
                if char == '#':
                    # pseudo character, find digit end
                    offset = 2
                    while index+offset < len(decomposition) \
                        and decomposition[index+offset].isdigit():
                        offset += 1
                    char = int(decomposition[index:index+offset])
                    charGlyph = 0
                elif index+1 < len(decomposition)\
                    and decomposition[index+1] == '[':
                    # extract glyph information
                    endIndex = decomposition.index(']', index+1)
                    charGlyph = int(decomposition[index+2:endIndex])
                    index = endIndex
                else:
                    charGlyph = None
                componentsList.append((char, charGlyph))
            index = index + 1
        return componentsList

    @staticmethod
    def readDecomposition(decompositionFilePath):
        decompositionEntries = {}

        print >> sys.stderr, "reading %r" % decompositionFilePath
        fileHandle = codecs.open(decompositionFilePath, 'r', 'utf8')

        # entries from CSV
        for entry in util.UnicodeCSVFileIterator(fileHandle):

            try:
                char, decomposition, glyphIdx, subIndex, flags = entry
                glyphIdx = int(glyphIdx)
                subIndex = int(subIndex)
                decomposition = GlyphReader.decompositionFromString(
                    decomposition)
            except ValueError, UnicodeEncodeError:
                print entry
                raise

            if char not in decompositionEntries:
                decompositionEntries[char] = {}
            if glyphIdx not in decompositionEntries[char]:
                decompositionEntries[char][glyphIdx] = []
            decompositionEntries[char][glyphIdx].append(
                (decomposition, subIndex, flags))

        return decompositionEntries

    @staticmethod
    def readStrokeOrder(strokeOrderFilePath):
        strokeOrderEntries = {}

        print >> sys.stderr, "reading %r" % strokeOrderFilePath
        fileHandle = codecs.open(strokeOrderFilePath, 'r', 'utf8')

        for entry in util.UnicodeCSVFileIterator(fileHandle):
            try:
                char, strokeOrder, glyphIdx, flags = entry
                glyphIdx = int(glyphIdx)
            except ValueError:
                print entry
                raise

            if char not in strokeOrderEntries:
                strokeOrderEntries[char] = {}
            strokeOrderEntries[char][glyphIdx] = (strokeOrder, flags)

        return strokeOrderEntries

    @staticmethod
    def readLocaleMapping(localeFilePath):
        localeEntries = {}

        print >> sys.stderr, "reading %r" % localeFilePath
        fileHandle = codecs.open(localeFilePath, 'r', 'utf8')

        for entry in util.UnicodeCSVFileIterator(fileHandle):
            try:
                char, glyphIdx, localeString = entry
                glyphIdx = int(glyphIdx)
            except ValueError:
                print entry
                raise
            if char not in localeEntries:
                localeEntries[char] = {}
            localeEntries[char][glyphIdx] = list(localeString)

        return localeEntries


class GlyphWriter(object):
    def __init__(self, decompositionFilePath, strokeOrderFilePath,
        localeFilePath):
        self.decompositionFilePath = decompositionFilePath
        self.strokeOrderFilePath = strokeOrderFilePath
        self.localeFilePath = localeFilePath

    def write(self, glyphEntries):
        GlyphWriter.writeDecomposition(self.decompositionFilePath, glyphEntries)
        GlyphWriter.writeStrokeOrder(self.strokeOrderFilePath, glyphEntries)
        GlyphWriter.writeLocaleMapping(self.localeFilePath, glyphEntries)

    @staticmethod
    def writeDecomposition(decompositionFilePath, glyphEntries):
        def getDecompositionStr(decomposition):
            decompEntities = []
            for entity in decomposition:
                if type(entity) != type(()):
                    decompEntities.append(entity)
                else:
                    char, glyphIdx = entity
                    if glyphIdx is None:
                        decompEntities.append(char)
                    else:
                        decompEntities.append("%s[%d]" % entity)
            return ''.join(decompEntities)

        print >> sys.stderr, "writing %r" % decompositionFilePath
        fileHandle = codecs.open(decompositionFilePath, 'w', 'utf8')

        for char in glyphEntries:
            for glyphIdx, glyph in glyphEntries[char].items():
                for decompositionEntry in glyph.decompositions:
                    decomposition, subIndex, flags = decompositionEntry
                    print >> fileHandle, (
                        '"%(char)s","%(decomp)s",%(glyph)d,%(index)d,%(flags)s'
                            % {'char': char,
                                'decomp': getDecompositionStr(decomposition),
                                'glyph': glyphIdx, 'index': subIndex,
                                'flags': flags})

        fileHandle.close()

    @staticmethod
    def writeStrokeOrder(strokeOrderFilePath, glyphEntries):
        strokeOrderEntries = {}

        print >> sys.stderr, "writing %r" % strokeOrderFilePath
        fileHandle = codecs.open(strokeOrderFilePath, 'w', 'utf8')

        for char in glyphEntries:
            for glyphIdx, glyph in glyphEntries[char].items():
                if glyph.strokeOrder:
                    strokeOrder, flags = glyph.strokeOrder
                    print >> fileHandle, (
                        '"%(char)s","%(so)s",%(glyph)d,%(flags)s'
                            % {'char': char, 'so': strokeOrder,
                                'glyph': glyphIdx, 'flags': flags})

        fileHandle.close()

    @staticmethod
    def writeLocaleMapping(localeFilePath, glyphEntries):
        localeEntries = {}

        print >> sys.stderr, "writing %r" % localeFilePath
        fileHandle = codecs.open(localeFilePath, 'w', 'utf8')

        for char in glyphEntries:
            for glyphIdx, glyph in glyphEntries[char].items():
                if glyph.locales:
                    locale = ''.join(glyph.locales)
                    print >> fileHandle, (
                        '"%(char)s",%(glyph)d,%(locale)s'
                            % {'char': char, 'glyph': glyphIdx,
                                'locale': locale})

        fileHandle.close()


class SortedGlyphIterator(object):
    def __init__(self, glyphEntries):
        self.glyphEntries = glyphEntries

    def __iter__(self):
        def getComponents(char):
            """
            Gets a set of components found in decompositions of all glyphs.
            """
            components = set()
            for glyphIdx in self.glyphEntries[char]:
                for decomp, _, _ in \
                    self.glyphEntries[char][glyphIdx].decompositions:

                    components.update(c for c, _ in
                        [entry for entry in decomp
                            if not isinstance(entry, basestring)])

            return components

        characters = set(self.glyphEntries.keys())
        components = dict((char, getComponents(char))
            for char in self.glyphEntries)

        while characters:
            charCount = len(characters)

            entriesCurrentRun = []
            for char in characters:
                # slow check, but works :)
                if len(components[char] & characters) == 0:
                    entriesCurrentRun.append((char, self.glyphEntries[char]))

            # sort characters of equal dependecy level
            entriesCurrentRun.sort()
            for entries in entriesCurrentRun:
                yield entries

            characters = characters - set(char for char, _ in entriesCurrentRun)

            if charCount == len(characters):
                raise ValueError("Cyclic dependency in decomposition data")


class LocaleDecompositionConverter(object):
    def __init__(self, options):
        self.reader = GlyphReader(options.decomposition, options.strokeorder,
            options.locale)

        self.writer = GlyphWriter(options.decompositionOut,
            options.strokeorderOut, options.localeOut)

        self.noMapping = options.noMapping
        self.explicitGlyph = options.explicitGlyph

    @staticmethod
    def getAugmentedDecompositionDefault(decomposition, defaultGlyphMapping):
        """
        Make the default glyph index explicit.
        """
        decompositionEntities = []
        for entity in decomposition:
            if type(entity) != type(()):
                decompositionEntities.append(entity)
            else:
                char, glyphIdx = entity

                # check if we need a locale specific glyph
                if glyphIdx is None and char in defaultGlyphMapping:
                    glyphIdx = defaultGlyphMapping[char]
                decompositionEntities.append((char, glyphIdx))

        return decompositionEntities

    @staticmethod
    def createGlyphExplicitDecompositions(glyphEntries):
        # get default glyph mappings
        defaultGlyphMapping = {}
        for char in glyphEntries:
            defaultGlyphMapping[char] = min(glyphEntries[char].keys())

        for char in glyphEntries:
            for glyphIdx, glyph in glyphEntries[char].items():
                for subIdx in range(len(glyph.decompositions)):
                    decomposition, subIdx, flags = glyph.decompositions[subIdx]
                    decomposition = LocaleDecompositionConverter\
                        .getAugmentedDecompositionDefault(decomposition,
                            defaultGlyphMapping)
                    glyph.decompositions[subIdx] = (decomposition, subIdx,
                        flags)

    @staticmethod
    def getAugmentedDecomposition(decomposition, locale, localeMapping,
        defaultLocaleMapping):
        """
        Augments a decomposition with a locale specific glyph index for
        components without glyph information
        """
        decompositionEntities = []
        for entity in decomposition:
            if type(entity) != type(()):
                decompositionEntities.append(entity)
            else:
                char, glyphIdx = entity

                # check if we need a locale specific glyph, only store explicit
                #   index if not default glyph
                if (glyphIdx is None and char in localeMapping
                    and locale in localeMapping[char]
                    and defaultLocaleMapping[char]
                        != localeMapping[char][locale]):
                    glyphIdx = localeMapping[char][locale]
                decompositionEntities.append((char, glyphIdx))

        return decompositionEntities

    @staticmethod
    def getLocaleSpecificDecompositions(glyphEntries):
        # get locale mappings
        localeMapping = {}
        defaultLocaleMapping = {}
        for char in glyphEntries:
            defaultLocaleMapping[char] = min(glyphEntries[char].keys())

            localeMapping[char] = {}
            for glyphIdx, glyph in glyphEntries[char].items():
                for locale in glyph.locales:
                    localeMapping[char][locale] = glyphIdx
        assert u'？' not in localeMapping

        # get in order of increasing dependencies
        sortedGlyphEntries = SortedGlyphIterator(glyphEntries)

        newGlyphEntries = util.OrderedDict()

        for char, glyphs in sortedGlyphEntries:
            newGlyphEntries[char] = {}
            newGlyphs = []
            defaultGlyphIdx = defaultLocaleMapping[char]
            # get locales without a mapping: take on default
            localesForDefaultGlyph = (set('TCJKV')
                - set(itertools.chain(*list(
                    glyph.locales for glyph in glyphs.values()))))

            for glyphIdx, glyph in glyphs.items():
                if not glyph.decompositions:
                    # no alteration needed
                    newGlyphEntries[char][glyphIdx] = glyph
                    continue

                locales = list(glyph.locales)
                if glyphIdx == defaultGlyphIdx:
                    locales.extend(localesForDefaultGlyph)
                newLocales = list(locales)

                for locale in locales:
                    decompositions = []
                    for entry in glyph.decompositions:
                        decomposition, subIdx, flags = entry
                        augmentedDecomposition = LocaleDecompositionConverter\
                            .getAugmentedDecomposition(
                                decomposition, locale, localeMapping,
                                defaultLocaleMapping)

                        decompositions.append(
                            (augmentedDecomposition, subIdx, flags))

                    # check if decompositions changed
                    if decompositions != glyph.decompositions:
                        # create new glyph
                        if glyph.strokeOrder:
                            print >> sys.stderr, ("Warning: creating new glyph"
                                " with old stroke order:"
                                " %s[%d] for locale %s"
                                    % (char, glyphIdx, locale))
                        newGlyphs.append(
                            Glyph(decompositions, glyph.strokeOrder, [locale]))
                        # detach locale from old
                        if locale in glyph.locales:
                            glyph.locales.remove(locale)
                        newLocales.remove(locale)

                if locales and not newLocales:
                    # all locales took on a new glyph, we can probably delete
                    #   this entry
                    print >> sys.stderr, ("Warning: deleting glyph"
                        " now without locale mappings:"
                        " %s[%d]" % (char, glyphIdx))
                else:
                    newGlyphEntries[char][glyphIdx] = glyph

            if newGlyphs:
                # new glyphs need to be integrated into the list
                nextGlyphIdx = max(glyphs.keys()) + 1
                for newGlyph in newGlyphs:
                    for glyphIdx, glyph in newGlyphEntries[char].items():
                        if (newGlyph.decompositions == glyph.decompositions
                            and newGlyph.strokeOrder == glyph.strokeOrder):
                            # merge with existing glyph
                            glyph = glyph._replace(
                                locales=glyph.locales + newGlyph.locales)
                            newGlyphEntries[char][glyphIdx] = glyph
                            break
                    else:
                        # no equal glyph found, add
                        newGlyphEntries[char][nextGlyphIdx] = newGlyph
                        nextGlyphIdx += 1

                # update locale map
                defaultLocaleMapping[char] = min(glyphEntries[char].keys())

                localeMapping[char] = {}
                for glyphIdx, glyph in newGlyphEntries[char].items():
                    for locale in glyph.locales:
                        localeMapping[char][locale] = glyphIdx

        return newGlyphEntries

    def run(self):
        # read glyphs from files
        glyphEntries = self.reader.read()

        if self.explicitGlyph:
            self.createGlyphExplicitDecompositions(glyphEntries)

        if self.noMapping:
            # "sort" only, makes a later diff possible
            newGlyphEntries = util.OrderedDict(
                SortedGlyphIterator(glyphEntries))
        else:
            # augment locale mapping with default glyph
            newGlyphEntries = self.getLocaleSpecificDecompositions(glyphEntries)

        # write entries
        self.writer.write(newGlyphEntries)


def main():
    parser = OptionParser(
        usage="usage: %prog",
        version="%prog " + cjklib.__version__)

    parser.add_option("--decomposition", action="store", dest="decomposition",
                      help="Path to current decomposition file",
                      default='cjklib/data/characterdecomposition.csv')
    parser.add_option("--strokeorder", action="store", dest="strokeorder",
                      help="Path to current stroke order file",
                      default='cjklib/data/strokeorder.csv')
    parser.add_option("--locale", action="store", dest="locale",
                      help="Path to current locale file",
                      default='cjklib/data/localecharacterglyph.csv')

    parser.add_option("--decompositionout", action="store",
                      dest="decompositionOut",
                      help="Path to decomposition output",
                      default='characterdecomposition_new.csv')
    parser.add_option("--strokeorderout", action="store", dest="strokeorderOut",
                      help="Path to stroke order output",
                      default='strokeorder_new.csv')
    parser.add_option("--localeout", action="store", dest="localeOut",
                      help="Path to locale output",
                      default='localecharacterglyph_new.csv')

    parser.add_option("-n", "--nomapping", action="store_true",
                      dest="noMapping", default=False,
                      help="Do not augment any entries")
    parser.add_option("-x", "--explicitglyph", action="store_true",
                      dest="explicitGlyph", default=False,
                      help="Make glyph index explicit")

    (options, args) = parser.parse_args()

    LocaleDecompositionConverter(options).run()


if __name__ == "__main__":
    main()
