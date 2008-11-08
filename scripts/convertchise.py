#!/usr/bin/python
# -*- coding: utf8 -*-
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

from cjklib.dbconnector import DatabaseConnector
from cjklib.characterlookup import CharacterLookup
from cjklib import exception

# get local language and output encoding
language, default_encoding = locale.getdefaultlocale()

CHISE_FILES = ['IDS-UCS-Basic.txt', 'IDS-UCS-Compat.txt', 'IDS-UCS-Ext-A.txt']

def readExcludeEntries(fileName):
    return [] # TODO implement

def getCjklibEntries():
    result = DatabaseConnector.getDBConnector().select('CharacterDecomposition',
        ['ChineseCharacter', 'Decomposition'])
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

def crossProduct(singleLists):
    """
    Calculates the cross product (aka Cartesian product) of sets given as lists.

    Example:
        >>> ro._crossProduct([['A', 'B'], [1, 2, 3]])
        [['A', 1], ['A', 2], ['A', 3], ['B', 1], ['B', 2], ['B', 3]]

    @type singleLists: list of lists
    @param singleLists: a list of list entries containing various elements
    @rtype: list of lists
    @return: the cross product of the given sets
    """
    # get repeat index for whole set
    lastRepeat = 1
    repeatSet = []
    for elem in singleLists:
        repeatSet.append(lastRepeat)
        lastRepeat = lastRepeat * len(elem)
    repeatEntry = []
    # get dimension of Cartesian product and dimensions of parts
    newListLength = 1
    for i in range(0, len(singleLists)):
        elem = singleLists[len(singleLists) - i - 1]
        repeatEntry.append(newListLength)
        newListLength = newListLength * len(elem)
    repeatEntry.reverse()
    # create product
    newList = [[] for i in range(0, newListLength)]
    lastSetLen = 1
    for i, listElem in enumerate(singleLists):
        for j in range(0, repeatSet[i]):
            for k, elem in enumerate(listElem):
                for l in range(0, repeatEntry[i]):
                    newList[j * lastSetLen + k*repeatEntry[i] \
                        + l].append(elem)
        lastSetLen = repeatEntry[i]
    return newList

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

    cjk = CharacterLookup()

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
            elif cjk.isRadicalChar(c):
                charSet = set([c])
                for l in 'TCJKV':
                    try:
                        equivForm = cjk.getRadicalFormEquivalentCharacter(c, l)
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
                            cjk.getCharacterEquivalentRadicalForms(c, l))
                    except ValueError:
                        pass
                if charSet:
                    augmentedDecomposition.append(list(charSet))
                else:
                    augmentedDecomposition.append([c])

        # check for already existing forms
        for decompList in crossProduct(augmentedDecomposition):
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

