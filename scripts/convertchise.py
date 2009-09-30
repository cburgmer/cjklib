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
Converts the CHISE component structure data from
U{http://mousai.as.wakwak.ne.jp/projects/chise/ids/index.html} to the data file
form of the cjklib library.

2008 Christoph Burgmer (cburgmer@ira.uka.de)
"""
import locale
import re
import os.path
import codecs
import sys
import getopt

from sqlalchemy import select

from cjklib.dbconnector import DatabaseConnector
from cjklib.characterlookup import CharacterLookup
from cjklib import exception
from cjklib.util import cross

# get local language and output encoding
language, default_encoding = locale.getdefaultlocale()

CHISE_FILES = ['IDS-UCS-Basic.txt', 'IDS-UCS-Compat.txt', 'IDS-UCS-Ext-A.txt']

_cjk = {}
def getCJK(locale):
    """
    Creates an instance of the L{CharacterLookup} object if needed and returns
    it.

    @rtype: object
    @return: an instance of the L{CharacterLookup} object
    """
    global _cjk
    if locale not in _cjk:
        _cjk[locale] = CharacterLookup(locale)
    return _cjk[locale]

def readExcludeEntries(fileName):
    return [] # TODO implement

def getCjklibEntries():
    db = DatabaseConnector.getDBConnector()
    table = db.tables['CharacterDecomposition']
    result = db.selectRows(
        select([table.c.ChineseCharacter, table.c.Decomposition]))
    cleanResult = []
    for char, decomp in result:
        # return variant information
        decomp = re.sub('\[\d+\]', '', decomp)
        cleanResult.append((char, decomp))
    return cleanResult

def ChiseEntryGenerator(pathList):
    global CHISE_FILES
    for fileName in CHISE_FILES:
        try:
            filePath = findFile(pathList, fileName)
            print >> sys.stderr, "reading '" + filePath + "'"
        except IOError:
            continue
        f = codecs.open(filePath, 'r', 'utf8')
        for line in f:
            if line.startswith('#') or line.startswith(';; -*-'):
                continue
            else:
                matchObj = re.match(r"U\+[ABCDEF0123456789]+\t(.)\t(.+)$", line)
                if not matchObj:
                    print >> sys.stderr, ("error parsing line '" + line + "'")\
                        .encode(default_encoding)
                    continue
                char = matchObj.group(1)
                decomposition = matchObj.group(2)
                yield (char, decomposition)

def findFile(pathList, fileNames):
    """
    Tries to locate a file with a given list of possible file names under
    the given paths.

    For each file name every given path is checked and the first match is
    returned.

    @type pathList: list of strings or string
    @param pathList: possible path names
    @type fileNames: list of strings or string
    @param fileNames: possible file names
    @rtype: string
    @return: path to file of first match in search for existing file
    @raise IOError: if no file found
    """
    if type(pathList) != type([]):
        pathList = [pathList]
    if type(fileNames) != type([]):
        fileNames = [fileNames]
    for fileName in fileNames:
        for path in pathList:
            filePath = os.path.join(os.path.expanduser(path), fileName)
            if os.path.exists(filePath):
                return filePath
    raise IOError("No file found under path(s)'" + "', '".join(pathList) \
        + "' for file names '" + "', '".join(fileNames) + "'")

def isValidDecomposition(decomposition):
    def parseIDS(decomposition, index):
        if index >= len(decomposition):
            raise ValueError

        if not CharacterLookup.isIDSOperator(decomposition[index]):
            return index + 1

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
            raise ValueError

    try:
        return parseIDS(decomposition, 0) == len(decomposition)
    except ValueError:
        return False

def usage():
    """
    Prints the usage for this script.
    """
    print """Usage: convertchise.py COMMAND
convertchise.py provides a simple script to convert the CHISE component
structure data to the data file form of the cjklib library.

General commands:
  --dataPath=PATH            path to data files from CHISE
  -e, --exclude=FILE         exclude entries from the CHISE data listed in the
                               given file
  --ignorePartial            will ignore missing entries if they are partial
                               and an entry for the given character already
                               exists"""

def main():
    # parse command line parameters
    try:
        opts, args = getopt.getopt(sys.argv[1:],
            "e:h", ["help", "dataPath=", "exclude=", "ignorePartial"])
    except getopt.GetoptError:
        # print help information and exit
        usage()
        sys.exit(2)

    DEFAULT_DATA_PATH = ['~']

    dataPathList = []
    excludeEntries = []
    ignorePartial = False

    # start to check parameters
    for o, a in opts:
        a = a.decode(default_encoding)
        # help screen
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        # data path
        elif o in ("--dataPath"):
            dataPathList.append(a)
        # setting of dictionary
        elif o in ("-e", "--exclude"):
            excludeEntries = readExcludeEntries(a)
        elif o in ("--ignorePartial"):
            ignorePartial = True

    # if no path set, asume default
    if not dataPathList:
        dataPathList = DEFAULT_DATA_PATH

    dataPath = []
    for pathEntry in dataPathList:
        dataPath.extend(pathEntry.split(':'))

    cjklibEntries = getCjklibEntries()
    charsWithEntries = set([char for char, decomp in cjklibEntries])

    addedChars = set()

    CountChiseEntries = 0
    CountChiseEntriesInCjklib = 0
    CountInvalidEntries = 0
    for char, decomposition in ChiseEntryGenerator(dataPath):
        CountChiseEntries = CountChiseEntries + 1

        if not CharacterLookup.isIDSOperator(decomposition[0]):
            # TODO currently cjklib doesn't support non-decomposition entries
            continue

        # remove CHISE private character entries
        decomposition = re.sub("&[^;]+;", u'？', decomposition)

        if not isValidDecomposition(decomposition):
            CountInvalidEntries = CountInvalidEntries + 1
            continue

        # augment decomposition with equivalents forms
        augmentedDecomposition = []
        for c in decomposition:
            if c == u'？' or CharacterLookup.isIDSOperator(c):
                augmentedDecomposition.append([c])
            elif getCJK('T').isRadicalChar(c):
                charSet = set([c])
                for l in 'TCJKV':
                    try:
                        equivForm = getCJK(l)\
                            .getRadicalFormEquivalentCharacter(c)
                        charSet.add(equivForm)
                    except ValueError:
                        pass
                    except exception.UnsupportedError:
                        pass
                if charSet:
                    augmentedDecomposition.append(list(charSet))
                else:
                    augmentedDecomposition.append([c])
            else:
                charSet = set([c])
                for l in 'TCJKV':
                    try:
                        charSet.update(
                            getCJK(l).getCharacterEquivalentRadicalForms(c))
                    except ValueError:
                        pass
                if charSet:
                    augmentedDecomposition.append(list(charSet))
                else:
                    augmentedDecomposition.append([c])

        # check for already existing forms
        for decompList in cross(*augmentedDecomposition):
            decomp = ''.join(decompList)

            if (char, decomp) in cjklibEntries:
                CountChiseEntriesInCjklib = CountChiseEntriesInCjklib + 1
                break
        else:
            if char not in charsWithEntries and char not in addedChars:
                print ('"' + char + '","' + decomposition + '",0,0,C')\
                    .encode(default_encoding)
            elif not (ignorePartial and decomposition.find(u'？') >= 0):
                print ('"' + char + '","' + decomposition + '",X,X,C')\
                    .encode(default_encoding)

    print >> sys.stderr, str(CountChiseEntriesInCjklib) + " of " \
        + str(CountChiseEntries) + " entries from CHISE already in cjklib " \
        + "(which has " + str(len(cjklibEntries)) + " entries), " \
        + str(CountInvalidEntries) + " entries with malformed IDS"

if __name__ == "__main__":
    main()

