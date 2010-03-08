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
Provides the library's unit tests for L{cjklib.dictionary}.
"""

# pylint: disable-msg=E1101
#  testcase attributes and methods are only available in concrete classes

import re
import os
import new
import unittest

from cjklib.dictionary import (getAvailableDictionaries, getDictionaryClass,
    getDictionary)
from cjklib.build import DatabaseBuilder
from cjklib import util
from cjklib.test import NeedsTemporaryDatabaseTest, attr, EngineMock

class DictionaryTest(NeedsTemporaryDatabaseTest):
    """Base class for testing of L{cjklib.dictionary}s."""
    DICTIONARY = None
    """Name of dictionary to test"""

    def setUp(self):
        NeedsTemporaryDatabaseTest.setUp(self)

        self.dictionaryClass = cls = getDictionaryClass(self.DICTIONARY)
        self.table = (hasattr(cls, 'DICTIONARY_TABLE') and cls.DICTIONARY_TABLE
            or None)

    def shortDescription(self):
        methodName = getattr(self, self.id().split('.')[-1])
        # get whole doc string and remove superfluous white spaces
        noWhitespaceDoc = re.sub('\s+', ' ', methodName.__doc__.strip())
        # remove markup for epytext format
        clearName = re.sub('[CLI]\{([^\}]*)}', r'\1', noWhitespaceDoc)
        # add name of reading
        return clearName + ' (for %s)' % self.DICTIONARY


class DictionaryMetaTest(DictionaryTest):
    """Tests meta operations."""
    def testInitialization(self):
        """Test initialisation."""
        originalEngine = self.db.engine

        # test if dictionary is accepted
        self.db.engine = EngineMock(originalEngine, mockTables=[self.table])

        self.assert_(self.dictionaryClass.available(self.db))
        dictionary = getDictionary(self.DICTIONARY, dbConnectInst=self.db)
        self.assert_(self.dictionaryClass in getAvailableDictionaries(self.db))

        # test if character domain is rejected
        self.db.engine = EngineMock(originalEngine, mockNonTables=[self.table])

        self.assert_(not self.dictionaryClass.available(self.db))
        self.assertRaises(ValueError, getDictionary, self.DICTIONARY,
            dbConnectInst=self.db)
        self.assert_(self.dictionaryClass not in getAvailableDictionaries(
            self.db))


class DictionaryResultTest(DictionaryTest):
    """Base class for testing of dictionary return values."""
    INSTALL_CONTENT = None

    ACCESS_RESULTS = []

    class _ContentGenerator(object):
        def getGenerator(self):
            for line in self.content:
                yield line

    def setUp(self):
        DictionaryTest.setUp(self)

        builderClasses = DatabaseBuilder.getTableBuilderClasses(quiet=True)
        dictionaryBuilder = [cls for cls in builderClasses
            if cls.PROVIDES == self.table][0]

        contentBuilder = new.classobj("SimpleDictBuilder",
            (DictionaryResultTest._ContentGenerator, dictionaryBuilder),
            {'content': self.INSTALL_CONTENT})

        builder = DatabaseBuilder(quiet=True, dbConnectInst=self.db,
            additionalBuilders=[contentBuilder], prefer=["SimpleDictBuilder"],
            rebuildExisting=True, noFail=False)
        builder.build(self.DICTIONARY)

        self.dictionary = self.dictionaryClass(dbConnectInst=self.db)

    @util.cachedproperty
    def resultIndexMap(self):
        content = self.INSTALL_CONTENT[:]

        columnFormatStrategies = self.dictionary.columnFormatStrategies
        for column, formatStrategy in columnFormatStrategies.items():
            columnIdx = self.dictionary.COLUMNS.index(column)
            for idx in range(len(content)):
                rowList = list(content[idx])
                rowList[columnIdx] = formatStrategy.format(rowList[columnIdx])
                content[idx] = tuple(rowList)
        return dict((row, idx) for idx, row in enumerate(content))

    def testResults(self):
        """Test results for access methods C{getFor...}."""
        def resultPrettyPrint(indices):
            return '[' + "\n".join(repr(self.INSTALL_CONTENT[index])
                for index in sorted(indices)) + ']'

        for key, requests in self.ACCESS_RESULTS.items():
            methodName, options = key
            options = dict(options) or {}
            method = getattr(self.dictionary, methodName)
            for request, targetResultIndices in requests:
                results = method(request, **options)
                resultIndices = [self.resultIndexMap[tuple(e)] for e in results]
                self.assertEquals(set(resultIndices), set(targetResultIndices),
                        ("Mismatch for method %s and string %s (options %s)\n"
                        % (repr(methodName), repr(request), repr(options))
                        + "Should be\n%s\nbut is\n%s\n"
                            % (resultPrettyPrint(targetResultIndices),
                                resultPrettyPrint(resultIndices))))


class FullDictionaryTest(DictionaryTest):
    """Base class for testing a full database instance."""
    def setUp(self):
        DictionaryTest.setUp(self)

        # build dictionary
        dataPath = [util.getDataPath(), os.path.join('.', 'test'),
            os.path.join('.', 'test', 'downloads')]
        builder = DatabaseBuilder(quiet=True, dbConnectInst=self.db,
            dataPath=dataPath, rebuildExisting=True, noFail=False)
        builder.build(self.DICTIONARY)

        self.dictionary = self.dictionaryClass(dbConnectInst=self.db)


class DictionaryAccessTest(FullDictionaryTest):
    """Tests access methods C{getFor...}."""
    ACCESS_METHODS = ('getFor', 'getForHeadword', 'getForReading',
        'getForTranslation')

    TEST_STRINGS = (u'跼', u'東京', u'とうきょう', u"Xi'an", 'New York', 'term')

    def testAccess(self):
        """Test access methods C{getFor...}."""
        for methodName in self.ACCESS_METHODS:
            method = getattr(self.dictionary, methodName)
            for string in self.TEST_STRINGS:
                method(string)


class EDICTMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'EDICT'

class EDICTAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'EDICT'


class CEDICTMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'CEDICT'

class CEDICTAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'CEDICT'


class CEDICTGRMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'CEDICTGR'

class CEDICTGRAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'CEDICTGR'


class HanDeDictMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'HanDeDict'

class HanDeDictAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'HanDeDict'


class CFDICTMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'CFDICT'

class CFDICTAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'CFDICT'

class CFDICTDictionaryResultTest(DictionaryResultTest, unittest.TestCase):
    DICTIONARY = 'CFDICT'

    INSTALL_CONTENT = [
        (u'对不起', u'對不起', u'dui4 bu5 qi3', u'Excusez-moi'),
        #(u'', u'', u'', u''),
        ]

    ACCESS_RESULTS = {
        ('getFor', ()): [(u'对不起', [0])],
        ('getFor', ()): [(u'對不起', [0])],
        ('getFor', ()): [(u'duì bu qǐ', [0])],
        ('getForReading', (('toneMarkType', 'numbers'),)): [
            (u'dui4bu5qi3', [0])],
        ('getFor', ()): [(u'excusez-moi', [0])],
        ('getForTranslation', ()): [(u'Excusez-moi', [0])],
        }
