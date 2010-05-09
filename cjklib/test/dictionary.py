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
Unit tests for :mod:`cjklib.dictionary`.
"""

# pylint: disable-msg=E1101
#  testcase attributes and methods are only available in concrete classes

import re
import os
import new
import unittest

from cjklib.dictionary import (getAvailableDictionaries, getDictionaryClass,
    getDictionary)
from cjklib.dictionary import search as searchstrategy
from cjklib.build import DatabaseBuilder
from cjklib import util
from cjklib.test import NeedsTemporaryDatabaseTest, attr, EngineMock

class DictionaryTest(NeedsTemporaryDatabaseTest):
    """Base class for testing of :mod:`cjklib.dictionary` classes."""
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
    """
    Content the dictionary mock will include. Should follow the dictionary's
    actual format.
    """

    ACCESS_RESULTS = []
    """List of query/result tuples."""

    DICTIONARY_OPTIONS = {}
    """Options for the dictionary instance passed when constructing object."""

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

        self.builder = DatabaseBuilder(quiet=True, dbConnectInst=self.db,
            additionalBuilders=[contentBuilder], prefer=["SimpleDictBuilder"],
            rebuildExisting=True, noFail=False)
        self.builder.build(self.DICTIONARY)
        assert self.db.mainHasTable(self.DICTIONARY)

        self.dictionary = self.dictionaryClass(dbConnectInst=self.db,
            **self.DICTIONARY_OPTIONS)

    def tearDown(self):
        self.builder.remove(self.DICTIONARY)
        assert not self.db.mainHasTable(self.DICTIONARY)

    @util.cachedproperty
    def resultIndexMap(self):
        content = self.INSTALL_CONTENT[:]

        content = map(list, content)
        for strategy in self.dictionary._formatStrategies:
            content = map(strategy.format, content)
        content = map(tuple, content)

        return dict((row, idx) for idx, row in enumerate(content))

    def testResults(self):
        """Test results for access methods ``getFor...``."""
        def resultPrettyPrint(indices):
            return '[' + "\n".join(repr(self.INSTALL_CONTENT[index])
                for index in sorted(indices)) + ']'

        for methodName, options, requests in self.ACCESS_RESULTS:
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
        self.builder = DatabaseBuilder(quiet=True, dbConnectInst=self.db,
            dataPath=dataPath, rebuildExisting=True, noFail=False)
        self.builder.build(self.DICTIONARY)

        self.dictionary = self.dictionaryClass(dbConnectInst=self.db)

    def tearDown(self):
        self.builder.remove(self.DICTIONARY)


class DictionaryAccessTest(FullDictionaryTest):
    """Tests access methods ``getFor...``."""
    ACCESS_METHODS = ('getFor', 'getForHeadword', 'getForReading',
        'getForTranslation')

    TEST_STRINGS = (u'跼', u'東京', u'とうきょう', u"Xi'an", 'New York', 'term')

    def testAccess(self):
        """Test access methods ``getFor...``."""
        for methodName in self.ACCESS_METHODS:
            method = getattr(self.dictionary, methodName)
            for string in self.TEST_STRINGS:
                method(string)


class EDICTMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'EDICT'

class EDICTAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'EDICT'

class EDICTDictionaryResultTest(DictionaryResultTest, unittest.TestCase):
    DICTIONARY = 'EDICT'

    INSTALL_CONTENT = [
        (u'東京', u'とうきょう', u'/(n) Tokyo (current capital of Japan)/(P)/'),
        (u'東京語', u'とうきょうご', u'/(n) Tokyo dialect (esp. historical)/'),
        (u'東京都', u'とうきょうと', u'/(n) Tokyo Metropolitan area/'),
        (u'頭胸部', u'とうきょうぶ', u'/(n) cephalothorax/'),
        #(u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getForHeadword', (), [(u'東京', [0])]),
        ('getFor', (), [(u'とうきょう_', [1, 2, 3])]),
        ('getForHeadword', (), [(u'Tokyo', [])]),
        ('getForHeadword', (), [(u'東%', [0, 1, 2])]),
        ('getFor', (), [(u'Tokyo', [0])]),
        ('getFor', (), [(u'_Tokyo', [])]),
        ('getForTranslation', (), [(u'tokyo%', [0, 1, 2])]),
    ]


class CEDICTMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'CEDICT'

class CEDICTAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'CEDICT'

class CEDICTDictionaryResultTest(DictionaryResultTest, unittest.TestCase):
    DICTIONARY = 'CEDICT'

    INSTALL_CONTENT = [
        (u'知道', u'知道', u'zhi1 dao5', u'/to know/to be aware of/'),
        (u'執導', u'执导', u'zhi2 dao3', u'/to direct (a film, play etc)/'),
        (u'直搗', u'直捣', u'zhi2 dao3', u'/to storm/to attack directly/'),
        (u'直到', u'直到', u'zhi2 dao4', u'/until/'),
        (u'指導', u'指导', u'zhi3 dao3', u'/to guide/to give directions/to direct/to coach/guidance/tuition/CL:個|个[ge4]/'),
        (u'制導', u'制导', u'zhi4 dao3', u'/to control (the course of sth)/to guide (a missile)/'),
        (u'指導教授', u'指导教授', u'zhi3 dao3 jiao4 shou4', u'/adviser/advising professor/'),
        (u'指導課', u'指导课', u'zhi3 dao3 ke4', u'/tutorial/period of tuition for one or two students/'),
        (u'個', u'个', u'ge4', u'/individual/this/that/size/classifier for people or objects in general/'),
        (u'西安', u'西安', u'Xi1 an1', u"/Xi'an city, subprovincial city and capital of Shaanxi 陝西省|陕西省[Shan3 xi1 sheng3] in northwest China/see 西安區|西安区[Xi1 an1 qu1]/"),
        (u'仙', u'仙', u'xian1', u'/immortal/'),
        (u'Ｃ盤', u'Ｃ盘', u'C pan2', u'/C drive or default startup drive (computing)/'),
        (u'ＵＳＢ手指', u'ＵＳＢ手指', u'U S B shou3 zhi3', u'/USB flash drive/'),
        (u'\U000289c0\U000289c0', u'\U000289c0\U000289c0', u'bo1 bo1', u'/Bohrium Bohrium/'),
        (u'\U000289c0', u'\U000289c0', u'bo1', u'/Bohrium/'),
        #(u'', u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getFor', (('toneMarkType', 'numbers'),),
            [(u'zhidao', [0, 1, 2, 3, 4, 5])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'zhi2dao', [1, 2, 3])]),
        ('getFor', (), [(u'to %', [0, 1, 2, 4, 5])]),
        ('getForTranslation', (), [(u'to guide', [4, 5])]),
        ('getForReading', (('toneMarkType', 'numbers'),),
            [(u'zhi导', [1, 4, 5])]),
        ('getForReading', (('toneMarkType', 'numbers'),),
            [(u'zhi导%', [1, 4, 5, 6, 7])]),
        ('getFor', (), [(u'個', [8])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'xian1', [9, 10])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'C pan', [11])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'Ｃpan', [11])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'Ｃ pan', [11])]),
        ('getFor', (), [(u'Ｃ盘', [11])]),
        ('getFor', (), [(u'C盘', [11])]),
        ('getForReading', (('toneMarkType', 'numbers'),),
            [(u'USB shou指', [12])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'bo', [14])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'\U000289c0bo1', [13])]),
        ]


class CEDICTGRMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'CEDICTGR'

class CEDICTGRAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'CEDICTGR'


class HanDeDictMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'HanDeDict'

class HanDeDictAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'HanDeDict'

class HanDeDictDictionaryResultTest(DictionaryResultTest, unittest.TestCase):
    DICTIONARY = 'HanDeDict'

    INSTALL_CONTENT = [
        (u'對不起', u'对不起', u'dui4 bu5 qi3', u'/Entschuldigung (u.E.) (S)/sorry (u.E.)/'),
        (u'自由大學', u'自由大学', 'zi4 you2 da4 xue2', u'/Freie Universität, FU (meist FU Berlin) (u.E.) (Eig)/'),
        (u'西柏林', u'西柏林', u'xi1 bo2 lin2', u'/West-Berlin (u.E.) (Eig, Geo)/'),
        (u'柏林', u'柏林', u'bo2 lin2', u'/Berlin (u.E.) (Eig, Geo)/'),
        (u'北', u'北', u'bei3', u'/Norden (S)/nördlich (Adj)/nordwärts, nach Norden, gen Norden (Adv)/Nord-; Bsp.: 北風 北风 -- Nordwind/'),
        (u'朔風', u'朔风', u'shuo4 feng1', u'/Nordwind (u.E.) (S)/'),
        (u'IC卡', u'IC卡', u'I C ka3', u'/Chipkarte (S)/'),
        (u'USB電纜', u'USB电缆', u'U S B dian4 lan3', u'/USB-Kabel (u.E.) (S)/'),
        (u'\U000289c0\U000289c0', u'\U000289c0\U000289c0', u'bo1 bo1', u'/Bohrium Bohrium/'),
        (u'\U000289c0', u'\U000289c0', u'bo1', u'/Bohrium/'),
        #(u'', u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getFor', (), [(u'对不起', [0])]),
        ('getFor', (), [(u'對不起', [0])]),
        ('getFor', (), [(u'对_起', [0])]),
        ('getFor', (), [(u'duì bu qǐ', [0])]),
        ('getFor', (), [(u'duì_qǐ', [0])]),
        ('getForReading', (('toneMarkType', 'numbers'),),
            [(u'dui4bu5qi3', [0])]),
        ('getFor', (), [(u'Sorry', [0])]),
        ('getForTranslation', (), [(u'Entschuldigung', [0])]),
        ('getForTranslation', (), [(u'Berlin', [3])]),
        ('getForTranslation', (), [(u'%Berlin', [2, 3])]),
        ('getFor', (), [(u'Nordwind', [5])]),
        ('getFor', (), [(u'%Nordwind%', [4, 5])]),
        ('getForReading', (('toneMarkType', 'numbers'),), [(u'IC ka', [6])]),
        ('getForReading', (('toneMarkType', 'numbers'),),
            [(u'USB dian纜', [7])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'bo', [9])]),
        ('getFor', (('toneMarkType', 'numbers'),), [(u'\U000289c0bo1', [8])]),
        ]


class CFDICTMetaTest(DictionaryMetaTest, unittest.TestCase):
    DICTIONARY = 'CFDICT'

class CFDICTAccessTest(DictionaryAccessTest, unittest.TestCase):
    DICTIONARY = 'CFDICT'

class CFDICTDictionaryResultTest(DictionaryResultTest, unittest.TestCase):
    DICTIONARY = 'CFDICT'

    INSTALL_CONTENT = [
        (u'對不起', u'对不起', u'dui4 bu5 qi3', u'/Excusez-moi!/'),
        #(u'', u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getFor', (), [(u'对不起', [0])]),
        ('getFor', (), [(u'對不起', [0])]),
        ('getFor', (), [(u'对_起', [0])]),
        ('getFor', (), [(u'duì bu qǐ', [0])]),
        ('getFor', (), [(u'duì_qǐ', [0])]),
        ('getForReading', (('toneMarkType', 'numbers'),),
            [(u'dui4bu5qi3', [0])]),
        ('getFor', (), [(u'excusez-moi', [0])]),
        ('getForTranslation', (), [(u'Excusez-moi', [0])]),
        ('getForTranslation', (), [(u'excusez-moi!', [0])]),
        ('getForTranslation', (), [(u'%-moi', [0])]),
        ]


class ParameterTest(DictionaryResultTest):
    PARAMETER_DESC = None

    def shortDescription(self):
        methodName = getattr(self, self.id().split('.')[-1])
        # get whole doc string and remove superfluous white spaces
        noWhitespaceDoc = re.sub('\s+', ' ', methodName.__doc__.strip())
        # remove markup for epytext format
        clearName = re.sub('[CLI]\{([^\}]*)}', r'\1', noWhitespaceDoc)
        # add name of reading
        return clearName + ' (for %s)' % self.PARAMETER_DESC



class EscapeParameterTest(ParameterTest, unittest.TestCase):
    """Test if non-standard escape will yield proper results."""
    DICTIONARY = 'EDICT'
    PARAMETER_DESC = 'escape'

    INSTALL_CONTENT = [
        (u'東京', u'とうきょう', u'/(n) Tokyo (current capital of Japan)/(P)/'),
        (u'東京語', u'とうきょうご', u'/(n) Tokyo dialect (esp. historical)/'),
        (u'東京都', u'とうきょうと', u'/(n) Tokyo Metropolitan area/'),
        (u'頭胸部', u'とうきょうぶ', u'/(n) cephalothorax/'),
        #(u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getForHeadword', (), [(u'東京', [0])]),
        ('getFor', (), [(u'とうきょう_', [1, 2, 3])]),
        ('getForHeadword', (), [(u'Tokyo', [])]),
        ('getForHeadword', (), [(u'東%', [0, 1, 2])]),
        ('getFor', (), [(u'Tokyo', [0])]),
        ('getForTranslation', (), [(u'Tokyyo', [0])]),
        ('getFor', (), [(u'_Tokyo', [])]),
        ('getForTranslation', (), [(u'tokyo%', [0, 1, 2])]),
        ('getForTranslation', (), [(u'tokyyo%', [0, 1, 2])]),
    ]

    DICTIONARY_OPTIONS = {
        'translationSearchStrategy': searchstrategy.SimpleWildcardTranslation(
            escape='y'),
        }


class CaseInsensitiveParameterTest(ParameterTest, unittest.TestCase):
    """
    Test if non-default setting of caseInsensitive will yield proper results.
    """
    DICTIONARY = 'EDICT'
    PARAMETER_DESC = 'caseInsensitive'

    INSTALL_CONTENT = [
        (u'東京', u'とうきょう', u'/(n) Tokyo (current capital of Japan)/(P)/'),
        (u'東京語', u'とうきょうご', u'/(n) Tokyo dialect (esp. historical)/'),
        (u'東京都', u'とうきょうと', u'/(n) Tokyo Metropolitan area/'),
        (u'頭胸部', u'とうきょうぶ', u'/(n) cephalothorax/'),
        #(u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getFor', (), [(u'Tokyo', [0])]),
        ('getFor', (), [(u'tokyo', [])]),
        ('getForTranslation', (), [(u'tokyo%', [])]),
        ('getForTranslation', (), [(u'Tokyo%', [0, 1, 2])]),
    ]

    DICTIONARY_OPTIONS = {
        'translationSearchStrategy': searchstrategy.SimpleWildcardTranslation(
            caseInsensitive=False),
        }


class WildcardParameterTest(ParameterTest, unittest.TestCase):
    """
    Test if non-default settings of wildcards will yield proper results.
    """
    DICTIONARY = 'EDICT'
    PARAMETER_DESC = 'singleCharacter/multipleCharacters'

    INSTALL_CONTENT = [
        (u'東京', u'とうきょう', u'/(n) Tokyo% (current capital of Japan)/(P)/'),
        (u'東京', u'とうきょう', u'/(n) Tokyo_ (current capital of Japan)/(P)/'),
        (u'東京語', u'とうきょうご', u'/(n) Tokyo dialect (esp. historical)/'),
        (u'東京都', u'とうきょうと', u'/(n) Tokyo Metropolitan area/'),
        (u'頭胸部', u'とうきょうぶ', u'/(n) cephalothorax/'),
        #(u'', u'', u''),
        ]

    ACCESS_RESULTS = [
        ('getFor', (), [(u'Tokyo', [])]),
        ('getForTranslation', (), [(u'Tokyo%', [0])]),
        ('getForTranslation', (), [(u'tokyo%', [0])]),
        ('getForTranslation', (), [(u'Tokyo*', [0, 1, 2, 3])]),
        ('getForTranslation', (), [(u'Tokyo?', [0, 1])]),
        ('getForTranslation', (), [(u'Tokyo_', [1])]),
    ]

    DICTIONARY_OPTIONS = {
        'translationSearchStrategy': searchstrategy.SimpleWildcardTranslation(
            singleCharacter='?', multipleCharacters='*'),
        }
