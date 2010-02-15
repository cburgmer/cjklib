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
Converts the component structure data from different sources to a data file as
understood by cjklib:
    - CHISE: U{http://mousai.as.wakwak.ne.jp/projects/chise/ids/index.html}
    - "Groovy set": U{http://code.google.com/p/vy-language/}, packaged locally
      under C{scripts/groovyset.csv}

2009 Christoph Burgmer (cburgmer@ira.uka.de)
"""

import sys
import codecs
import os
import locale
import re
from optparse import OptionParser

from sqlalchemy import select

import cjklib
from cjklib.characterlookup import CharacterLookup
from cjklib import dbconnector
from cjklib.util import cross, UnicodeCSVFileIterator

# get local language and output encoding
language, default_encoding = locale.getdefaultlocale()


class CjklibGenerator(object):
    #def __init__(self, quiet=False):
        #self.quiet = quiet

    def __iter__(self):
        return self

    def next(self):
        if not hasattr(self, '_decompositions'):
            self._decompositions = self._getDecompositionEntriesDict()

        if not self._decompositions: raise StopIteration()
        return self._decompositions.pop()

    @classmethod
    def _getDecompositionEntriesDict(cls):
        """
        Gets the decomposition table from the database.

        @rtype: dict
        @return: dictionary with key pair character, I{glyph} and the first
            layer decomposition as value with the entry's flag
        """
        decompDict = {}
        # get entries from database
        db = dbconnector.getDBConnector()
        table = db.tables['CharacterDecomposition']

        result = db.selectRows(select([table.c.ChineseCharacter,
            table.c.Glyph, table.c.Decomposition, table.c.Flags])\
                .order_by(table.c.SubIndex))
        entries = []
        for char, glyph, decompString, flags in result:
            decomposition = CharacterLookup.decompositionFromString(
                decompString)
            entries.append((char, glyph, decomposition, set(flags)))

        return entries


class FileGenerator(object):
    def __init__(self, filePath, quiet=False):
        self.filePath = filePath
        self.quiet = quiet

    def __iter__(self):
        return self

    def next(self):
        if not hasattr(self, '_fileIterator'):
            if not self.quiet:
                print >> sys.stderr, "FILE: reading '%s'" % self.filePath
            fileHandle = codecs.open(self.filePath, 'r', default_encoding)
            self._fileIterator = UnicodeCSVFileIterator(fileHandle)

        while True:
            char, decompString, glyph, _, flags = self._fileIterator.next()
            if len(char) > 1:
                # pseudo char
                if not char.startswith('#'):
                    print >> sys.stderr, ("FILE: Error parsing entry '%s', %s"
                        % (char, glyph)).encode(default_encoding)
                    continue
                else:
                    char = int(char[1:])

            decomposition = CharacterLookup.decompositionFromString(
                decompString)
            return (char, int(glyph), decomposition, set(flags))


class ChiseEntryGenerator(object):
    CHISE_FILES = ['IDS-UCS-Basic.txt', 'IDS-UCS-Compat.txt',
        'IDS-UCS-Ext-A.txt']

    ENTRY_REGEX = re.compile(r"U\+[ABCDEF0123456789]+\t(.)\t(.+)$")

    def __init__(self, pathList, quiet=False):
        self.pathList = pathList
        self.quiet = quiet

    def __iter__(self):
        return self

    def next(self):
        entry = self._getNextEntry()
        if entry is None:
            raise StopIteration()
        else:
            char, decompString = entry
            # TODO support CHISE private character entries
            # remove CHISE private character entries
            decompString = re.sub("&[^;]+;", u'？', decompString)

            decomposition = []
            for c in decompString:
                if CharacterLookup.isIDSOperator(c):
                    decomposition.append(c)
                else:
                    decomposition.append((c, 0))
            # flag 'C'HISE
            return (char, 0, decomposition, set('C'))

    def _getNextEntry(self):
        if not hasattr(self, '_curFile'):
            self._curFile = None
            self._unseenFiles = self.CHISE_FILES[:]

        while True:
            while not self._curFile and self._unseenFiles:
                fileName = self._unseenFiles.pop()
                try:
                    filePath = self._findFile([fileName])
                    if not self.quiet:
                        print >> sys.stderr, "CHISE: reading '%s'" % filePath
                    self._curFile = codecs.open(filePath, 'r', 'utf8')
                except IOError:
                    pass

            if not (self._curFile or self._unseenFiles):
                return None

            try:
                line = self._curFile.next()
                if not (line.startswith('#') or line.startswith(';; -*-')):
                    matchObj = self.ENTRY_REGEX.match(line)
                    if matchObj:
                        return matchObj.groups()
                    else:
                        if not self.quiet:
                            print >> sys.stderr, \
                                ("CHISE: Error parsing line '%s'" % line)\
                                    .encode(default_encoding)
            except StopIteration:
                self._curFile = None

    def _findFile(self, fileNames):
        """
        Tries to locate a file with a given list of possible file names under
        the given paths.

        For each file name every given path is checked and the first match is
        returned.

        @type fileNames: list of strings or string
        @param fileNames: possible file names
        @rtype: string
        @return: path to file of first match in search for existing file
        @raise IOError: if no file found
        """
        if type(fileNames) != type([]):
            fileNames = [fileNames]
        for fileName in fileNames:
            for path in self.pathList:
                filePath = os.path.join(os.path.expanduser(path), fileName)
                if os.path.exists(filePath):
                    return filePath

        raise IOError("No file found under path(s) '%s' for file names '%s'"
        % ("', '".join(pathList), "', '".join(fileNames)))


class GroovySetGenerator(object):
    """Iterates over the "groovy" character list."""

    DESCRIPTION_MAP = {
        'PlainAcross': u'⿰',
        'TouchAcross': u'⿰', # same as 'PlainAcross', but components touch
        'PlainDown': u'⿱',
        'TouchDown': u'⿱', # same as 'PlainDown', but components touch
        'Within': u'⿻',
        'Lock': u'⿻',
        'BetweenAcross': u'⿻', # more specific than 'Within', e.g. 辩
        'BetweenDown': u'⿻', # more specific than 'Within', e.g. 裒,衣,臼
        'NeedleAcross': u'⿻', # more specific than 'Within', e.g. 卅,川,一
        'NeedleDown': u'⿻', # more specific than 'Within', e.g. 中,口,丨
        'FullSurround': u'⿴',
        'TopSurround': u'⿵',
        'BottomSurround': u'⿶',
        'LeftSurround': u'⿷',
        'ToprightSurround': u'⿹',
        'TopleftSurround': u'⿸',
        'BottomleftSurround': u'⿺',
        }

    DESCRIPTION_RULE = {
        'StrokeModified': lambda a, b: [[u'⿻', a, u'？']],
        'ToprightSurroundMold': lambda a, b: [[u'⿹', a, u'？'],
            [u'⿹', u'？', b]],
        'MoldAcross': lambda a, b: [[u'⿰', a, u'？'], [u'⿰', u'？', b]],
        'MoldDown': lambda a, b: [[u'⿱', a, u'？'], [u'⿱', u'？', b]],
        'SnapDown': lambda a, b: [[u'⿱', a, u'？'], [u'⿱', u'？', b]],
        'RepeatMoldDown': lambda a, b: [[u'⿱', a, u'？'], [u'⿱', u'？', a]],
        'RepeatAcross': lambda a, b: [[u'⿰', a, a]],
        'RepeatThreeAcross': lambda a, b: [[u'⿲', a, a, a]],
        'RepeatDown': lambda a, b: [[u'⿱', a, a]],
        'RepeatTriangle': lambda a, b: [[u'⿱', a, u'⿰', a, a]],
        'RepeatSquare': lambda a, b: [[u'⿱', u'⿰', a, a, u'⿰', a, a]],
        'RepeatTopSurround': lambda a, b: [[u'⿵', a, a]],
        }

    IGNORE = set(['CornerJoin', 'Component', 'Diagonal', 'RadicalVersion',
        'SpecialModified',
        # Rather recreate character by hand, than implement general rules:
        'RepeatThreeDown', 'RepeatFourAcross', 'RightSurround', 'WithinMold',
        'StrokeModifiedMold'])

    def __init__(self, filePath, quiet=False):
        self.filePath = filePath
        self.quiet = quiet
        self._unknownDescriptions = set()
        self._skipCount = 0
        self._entrySet = None
        self._pseudoCharacters = {}

    def __iter__(self):
        return self

    def next(self):
        if not self._entrySet:
            self._entrySet = self._getNextEntries()
        char, decomposition = self._entrySet.pop()
        # flag 'G'roovy set
        return (char, 0, decomposition, set('G'))

    def _getNextEntries(self):
        def checkPseudoCharacter(c):
            """Returns an id if c is a pseudo character"""
            if len(c) > 1:
                # add new pseude character
                if c not in self._pseudoCharacters:
                    key = len(self._pseudoCharacters)
                    self._pseudoCharacters[c] = key
                return self._pseudoCharacters[c]
            else:
                return c

        def isPrivateUse(c):
            if type(c) != type(0):
                # really a character
                return ord(c) >= int('E000', 16) and ord(c) <= int('F8FF', 16)
            return False

        while True:
            try:
                # open file on first run
                if not hasattr(self, '_file'):
                    if not self.quiet:
                        print >> sys.stderr, ("Groovy: reading '%s'"
                            % self.filePath)
                    self._file = codecs.open(self.filePath, 'r', 'utf8')

                    # remove initial lines (should be LICENSE)
                    while True:
                        line = self._file.next()
                        if re.match('([^,]{1,2},){3}[^,]+$',
                            line):
                            break
                else:
                    line = self._file.next()

                if not line.strip():
                    continue

                if line.count(',') != 3:
                    print >> sys.stderr, ("Groovy: Error parsing line '%s'"
                        % line).encode(default_encoding)
                    continue

                char, componentA, componentB, description \
                    = line.strip().split(',')
                char = checkPseudoCharacter(char)
                if isPrivateUse(char):
                    self._skipCount += 1
                    continue
                componentA = checkPseudoCharacter(componentA)
                if isPrivateUse(componentA): componentA = u'？'
                componentB = checkPseudoCharacter(componentB)
                if isPrivateUse(componentB): componentB = u'？'

                entries = self._buildEntry(componentA, componentB, description)
                if entries:
                    return [(char, decomposition) for decomposition in entries]
                else:
                    self._skipCount += 1
            except StopIteration:
                if not self.quiet:
                    print >> sys.stderr, ('Groovy: Unknown descriptions: %s'
                        % ', '.join(self._unknownDescriptions))
                    print >> sys.stderr, 'Groovy: Skipped: %d' % self._skipCount

                raise

    def _buildEntry(self, componentA, componentB, description):
        def getDecomposition(structure):
            # add glyph information
            decomposition = []
            for c in structure:
                if type(c) == type(u'') and CharacterLookup.isIDSOperator(c):
                    decomposition.append(c)
                else:
                    decomposition.append((c, 0))
            return decomposition

        if description in self.IGNORE:
            return

        if description in self.DESCRIPTION_RULE:
            structures = self.DESCRIPTION_RULE[description](componentA,
                componentB)
            if type(structures) != type([]):
                structures = [structures]

            return [getDecomposition(structure) for structure in structures]

        elif description in self.DESCRIPTION_MAP:
            return [[self.DESCRIPTION_MAP[description],
                (componentA, 0), (componentB, 0)]]

        else:
            self._unknownDescriptions.add(description)


class DecompositionConverter(object):
    def __init__(self, options):
        # Sources
        self.filePaths = options.filePaths
        self.chiseDirectory = options.chiseDirectory
        self.groovySource = options.groovySource
        self.includeCjklib = options.includeCjklib

        # options
        self.includeMinimal = options.includeMinimal
        self.includePseudoCharacters = options.includePseudoCharacters
        self.quiet = options.quiet

    def read(self):
        def checkPseudoCharacter(char, startIndex):
            """
            Apply offset to pseudo character indices to circumvent overlapping
            identifiers.
            """
            if type(char) == type(0):
                char = startIndex + char
                if char not in pseudoCharacters:
                    pseudoCharacters.add(char)
            return char

        def checkPseudoCharactersDecomposition(decomposition, startIndex):
            for idx, c in enumerate(decomposition):
                if type(c) == type(()):
                    component, glyph = c
                    component = checkPseudoCharacter(component, startIndex)
                    decomposition[idx] = (component, glyph)

        def addDecomposition(corpus, char, glyph, decomposition, flags,
            pseudoCharacterStartIndex):
            # fix pseudo char index
            char = checkPseudoCharacter(char, pseudoCharacterStartIndex)

            if char not in decompositionEntries:
                decompositionEntries[char] = {}
                flagEntries[char] = {}
            if glyph not in decompositionEntries[char]:
                decompositionEntries[char][glyph] = set()
                flagEntries[char][glyph] = {}

            # fix pseudo char index
            checkPseudoCharactersDecomposition(decomposition,
                pseudoCharacterStartIndex)

            if DecompositionConverter.isValidDecomposition(char, glyph,
                decomposition):
                decomposition = tuple(decomposition)
                # add decomposition
                decompositionEntries[char][glyph].add(decomposition)
                # add flags
                if decomposition not in flagEntries[char][glyph]:
                    flagEntries[char][glyph][decomposition] = set()
                flagEntries[char][glyph][decomposition].update(flags)
            else:
                if corpus not in badEntries:
                    badEntries[corpus] = []
                badEntries[corpus].append((char, glyph))

        decompositionEntries = {}
        flagEntries = {}
        badEntries = {}
        pseudoCharacters = set()

        # get entries from cjklib (specific as glyphs)
        if self.includeCjklib:
            if not self.quiet:
                print >> sys.stderr, "reading from cjklib"

            pseudoCharacterStartIndex = len(pseudoCharacters)

            for char, glyph, decomposition, flags in CjklibGenerator():
                addDecomposition('cjklib', char, glyph, decomposition,
                    flags, pseudoCharacterStartIndex)

        # entries from CSV
        for filePath in self.filePaths:
            pseudoCharacterStartIndex = len(pseudoCharacters)

            for char, glyph, decomposition, flags in FileGenerator(filePath,
                self.quiet):

                addDecomposition(filePath, char, glyph, decomposition,
                    flags, pseudoCharacterStartIndex)

        # entries from CHISE
        if self.chiseDirectory:
            pseudoCharacterStartIndex = len(pseudoCharacters)

            for char, glyph, decomposition, flags \
                in ChiseEntryGenerator(self.chiseDirectory, self.quiet):

                addDecomposition('CHISE', char, glyph, decomposition,
                    flags, pseudoCharacterStartIndex)

        # entries from the 'groovy set'
        if self.groovySource:
            pseudoCharacterStartIndex = len(pseudoCharacters)

            for char, glyph, decomposition, flags \
                in GroovySetGenerator(self.groovySource, self.quiet):

                addDecomposition('Groovy', char, glyph, decomposition,
                    flags, pseudoCharacterStartIndex)

        if not self.quiet and badEntries:
            print >> sys.stderr, 'Found malformed entries:'
            for corpus in badEntries:
                print >> sys.stderr, corpus, (' '.join(
                    [char for char, _ in badEntries[corpus]]))\
                    .encode(default_encoding)

        return decompositionEntries, flagEntries

    def run(self):
        decompositionEntries, flagEntries = self.read()

        # Remove pseudo characters by merging entries
        if not self.includePseudoCharacters:
            decompositionEntries, flagEntries = self._removePseudoCharacters(
                decompositionEntries, flagEntries)

        # Remove minimal component entries
        if not self.includeMinimal:
            for char in sorted(decompositionEntries.keys()):
                for glyph in decompositionEntries[char]:
                    for decomposition \
                        in decompositionEntries[char][glyph].copy():

                        if len(decomposition) == 1:
                            decompositionEntries[char][glyph].remove(
                                decomposition)
                            del flagEntries[char][glyph][decomposition]

        # Merge similar decompositions, removing inferior ones
        self._mergeSimilarDecompositions(decompositionEntries, flagEntries)

        # Write entries
        for char in sorted(decompositionEntries.keys()):
            for glyph in decompositionEntries[char]:
                for idx, decomposition in enumerate(
                    sorted(decompositionEntries[char][glyph])):
                    decompStr = CharacterLookup.decompositionToString(
                        decomposition)
                    if type(char) == type(0):
                        # pseudo character
                        char = '#%d' % char
                    flagStr = ''.join(sorted(
                        flagEntries[char][glyph][decomposition]))
                    print (
                        '"%(char)s","%(decomp)s",%(glyph)d,%(index)d,%(flags)s'
                            % {'char': char, 'decomp': decompStr,
                                'glyph': glyph, 'index': idx,
                                'flags': flagStr}).encode(default_encoding)

    @staticmethod
    def isValidDecomposition(char, glyph, decomposition):
        def parseIDS(decomposition, index):
            if index >= len(decomposition):
                raise ValueError()

            if type(decomposition[index]) == type(()):
                # consume one component
                return index + 1

            if not CharacterLookup.isIDSOperator(decomposition[index]):
                # simple chars should be IDS operators
                raise ValueError()

            if CharacterLookup.isBinaryIDSOperator(decomposition[index]):
                index = index + 1
                index = parseIDS(decomposition, index)
                return parseIDS(decomposition, index)
            elif CharacterLookup.isTrinaryIDSOperator(decomposition[index]):
                index = index + 1
                index = parseIDS(decomposition, index)
                index = parseIDS(decomposition, index)
                return parseIDS(decomposition, index)
            else:
                raise ValueError()

        if len(decomposition) == 1:
            # minimal component entry
            if type(decomposition[0]) != type(()):
                return False
            component, componentGlyph = decomposition[0]
            return char == component and glyph == componentGlyph
        try:
            return parseIDS(decomposition, 0) == len(decomposition)
        except ValueError:
            return False

    def _mergeSimilarDecompositions(self, decompositionEntries, flagEntries):
        """
        Merges two decompositions, if they are the same, except:
            - one has an unknown component while the other doesn't,
            - one has a subtree that is the decomposition of the corresponding
              component of the other decomposition.
        """
        def consumeComponent(decomposition):
            """
            Consumes a component on the top level, e.g. for 㐯, C{⿱⿱亠吕香}
            consumes C{⿱亠吕} when given the partial decomposition C{⿱亠吕香}.
            """
            if type(decomposition[0]) == type(()):
                # consume one component
                return decomposition[1:]

            if CharacterLookup.isBinaryIDSOperator(decomposition[0]):
                decomposition = consumeComponent(decomposition[1:])
                return consumeComponent(decomposition)
            elif CharacterLookup.isTrinaryIDSOperator(decomposition[0]):
                decomposition = consumeComponent(decomposition[1:])
                decomposition = consumeComponent(decomposition)
                return consumeComponent(decomposition)

        def compareTrees(decompositionA, decompositionB):
            """
            Checks for similar decomposition trees, taking care of unknown
            components.

            Returns C{None} if the trees are not equal, a integer if the trees
            are similar. If the left tree (decompositionA) should be preferred a
            negative number is returned, or a positive number for the right tree
            (decompositionB). If C{0} is returned, both trees are equally good
            to choose from.
            """
            if not decompositionA and not decompositionB:
                # equal
                return 0
            elif not decompositionA or not decompositionB:
                # if all preceding components are the same that shouldn't happen
                raise ValueError()
            elif decompositionA[0] == decompositionB[0]:
                return compareTrees(decompositionA[1:], decompositionB[1:])

            elif (type(decompositionA[0]) == type(())
                and decompositionA[0][0] == u'？'):
                decompositionB = consumeComponent(decompositionB)
                result = compareTrees(decompositionA[1:], decompositionB)
                if result is None or result < 0:
                    # unequal or the left side is preferred later on
                    return None
                else:
                    return +1

            elif (type(decompositionB[0]) == type(())
                and decompositionB[0][0] == u'？'):
                decompositionA = consumeComponent(decompositionA)
                result = compareTrees(decompositionA, decompositionB[1:])
                if result is None or result > 0:
                    # unequal or the right side is preferred later on
                    return None
                else:
                    return -1

            elif (CharacterLookup.isIDSOperator(decompositionA[0])
                and CharacterLookup.isIDSOperator(decompositionB[0])):
                # No way these decompositions can be equal
                #   (simplified subseq. checking)
                return None

            elif CharacterLookup.isIDSOperator(decompositionA[0]):
                # expand tree B
                char, glyph = decompositionB[0]
                if (char in decompositionEntries
                    and glyph in decompositionEntries[char]):

                    for decomposition in decompositionEntries[char][glyph]:
                        result = compareTrees(
                            decompositionA, decomposition + decompositionB[1:])
                        if result is not None and result >= 0:
                            # right side preferred and so do we...
                            #   A shorted description is better
                            return 1

                return None

            elif CharacterLookup.isIDSOperator(decompositionB[0]):
                # expand tree A
                char, glyph = decompositionA[0]
                if (char in decompositionEntries
                    and glyph in decompositionEntries[char]):

                    for decomposition in decompositionEntries[char][glyph]:
                        result = compareTrees(
                            decomposition + decompositionA[1:], decompositionB)
                        if result is not None and result <= 0:
                            # left side preferred and so do we...
                            #   A shorted description is better
                            return -1
                return None
            else:
                return None

        for char in decompositionEntries:
            for glyph in decompositionEntries[char]:
                idxA = 0
                decompositions = list(decompositionEntries[char][glyph])
                flagsDict = flagEntries[char][glyph]
                # Check every decomposition with all others to the right
                while idxA < len(decompositions):
                    idxB = idxA + 1
                    while idxB < len(decompositions):
                        try:
                            result = compareTrees(decompositions[idxA],
                                decompositions[idxB])
                            if result is not None and result == 0:
                                # Entries are equal, we can transfer flags
                                flagsDict[decompositions[idxA]].update(
                                    flagsDict[decompositions[idxB]])
                                del flagsDict[decompositions[idxB]]
                                del decompositions[idxB]
                            elif result is not None and result < 0:
                                del flagsDict[decompositions[idxB]]
                                del decompositions[idxB]
                            elif result is not None and result > 0:
                                del flagsDict[decompositions[idxA]]
                                del decompositions[idxA]
                                # No need for further testing for this decomp
                                break
                            else:
                                # Only increase if the list didn't shift to the
                                #   left
                                idxB += 1
                        except ValueError:
                            print >> sys.stderr, (
                                "Error comparing decompositions %s and %s"
                                % (CharacterLookup.decompositionToString(
                                    decompositions[idxA]),
                                    CharacterLookup.decompositionToString(
                                        decompositions[idxB])))\
                                    .encode(default_encoding)
                            idxB += 1
                    else:
                        idxA += 1
                decompositionEntries[char][glyph] = set(decompositions)

    def _removePseudoCharacters(self, decompositionEntries, flagEntries):
        """
        Removes all pseudo character entries and subsitutes their occurence
        by their own entries.
        """
        def substitutePseudoCharacters(decomposition):
            newDecomposition = []
            for c in decomposition:
                if type(c) != type(()):
                    # IDS
                    newDecomposition.append([[c]])
                else:
                    char, _ = c
                    if type(char) == type(0):
                        if c in pseudoCharacterMap:
                            # get all decompositions of this pseudo character
                            newPseudoDecomp = []
                            for decomp in pseudoCharacterMap[c]:
                                newDecomps = substitutePseudoCharacters(decomp)
                                if newDecomps:
                                    newPseudoDecomp.extend(newDecomps)
                            newDecomposition.append(newPseudoDecomp)
                        else:
                            return
                    else:
                        # normal char
                        newDecomposition.append([[c]])
            # all combinations of sub-decompositions
            flatDecomp = set()
            for newDecomp in cross(*newDecomposition):
                flatEntry = []
                for entry in newDecomp:
                    flatEntry.extend(entry)
                flatDecomp.add(tuple(flatEntry))
            return flatDecomp

        # find pseude characters first
        pseudoCharacterMap = {}
        for char in decompositionEntries:
            if type(char) == type(0):
                for glyph in decompositionEntries[char]:
                    pseudoCharacterMap[(char, glyph)] \
                        = decompositionEntries[char][glyph]

        # now apply
        newDecompositionsEntries = {}
        newFlagEntries = {}
        for char in decompositionEntries:
            if type(char) == type(0):
                continue
            newDecompositionsEntries[char] = {}
            newFlagEntries[char] = {}
            for glyph in decompositionEntries[char]:
                newDecompositionsEntries[char][glyph] = set()
                newFlagEntries[char][glyph] = {}
                for decomposition in decompositionEntries[char][glyph]:
                    newDecompositions = substitutePseudoCharacters(decomposition)
                    if newDecompositions:
                        newDecompositionsEntries[char][glyph].update(
                            newDecompositions)
                        # transfer flags
                        for newDecomposition in newDecompositions:
                            newFlagEntries[char][glyph][newDecomposition] \
                                = flagEntries[char][glyph][decomposition]
                    elif not self.quiet:
                        print >> sys.stderr, ("Unable to resolve decomposition"
                            + " with pseudo character for '%s': " % char
                            + CharacterLookup.decompositionToString(
                                decomposition))\
                            .encode(default_encoding)

        return newDecompositionsEntries, newFlagEntries


def main():
    parser = OptionParser(usage="usage: %prog [options]",
                        version="%prog " + cjklib.__version__)


    parser.add_option("-f", "--file",
                    action="append", type="string", dest="filePaths",
                    default=[],
                    help="CSV file of known format")
    parser.add_option("-c", "--chise",
                    action="append", type="string", dest="chiseDirectory",
                    default=[],
                    help="Directory containing CHISE files")
    parser.add_option("-g", "--groovy",
                    type="string", dest="groovySource",
                    help="File path of \"Groovy set\"")
    parser.add_option("-l", "--cjklib",
                    action="store_true", dest="includeCjklib",
                    help="Include data from cjklib")
    parser.add_option("-m", action="store_true", dest="includeMinimal",
                    help="Include minimal component entries")
    parser.add_option("-p", "--pseudo", action="store_true",
                    dest="includePseudoCharacters",
                    help="Include pseudo characters in list")
    #parser.add_option("-a", action="store_true", dest="augmentRadicalForms", # TODO
                    #help="Augment decompositions with radical forms")
    #parser.add_option("-z", action="store_true", dest="augmentCompatibleForms", # TODO
                    #help="Create entries for compatible forms")
    #parser.add_option("--suggestShorter", action="store_true",  # TODO
                    #dest="suggestShorter",
                    #help="Suggest shorter trees by finding super-components")
    # TODO find "nearly similar" decompositions?
    #"徵","⿰彳⿰⿱山⿱一王攵",0,0,G
    #"徵","⿲彳⿱山⿱一王攵",0,1,O
    # TODO check same stroke count if several decompositions are given for a glyph
    #parser.add_option("--checkStrokeCount", action="store_true",
                    #dest="checkStrokeCount",
                    #help="Cross check for valid stroke count")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                    help="Do not print any statistics")

    (options, args) = parser.parse_args()

    DecompositionConverter(options).run()


if __name__ == "__main__":
    main()
