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
Provides the library's unit tests for the L{reading.converter} classes.

@todo Impl: Add second dimension to consistency check for converting between
    dialect forms for all entities. Use cartesian product option_list x dialects
"""
import re
import types
import unittest

from cjklib.reading import ReadingFactory, converter, operator
from cjklib import exception

class ReadingConverterTest():
    """Base class for testing of L{ReadingConverter}s."""
    CONVERSION_DIRECTION = None
    """Tuple of reading names for conversion from reading A to reading B."""

    def setUp(self):
        self.fromReading, self.toReading = self.CONVERSION_DIRECTION

        for clss in self.getReadingConverterClasses().values():
            if self.CONVERSION_DIRECTION in clss.CONVERSION_DIRECTIONS:
                self.readingConverterClass = clss
                break
        else:
            self.readingConverterClass = None

        self.f = ReadingFactory()

    def shortDescription(self):
        methodName = getattr(self, self.id().split('.')[-1])
        # get whole doc string and remove superfluous white spaces
        noWhitespaceDoc = re.sub('\s+', ' ', methodName.__doc__.strip())
        # remove markup for epytext format
        clearName = re.sub('[CL]\{([^\}]*)}', r'\1', noWhitespaceDoc)
        # add information about conversion direction
        return clearName + ' (for %s to %s)' % self.CONVERSION_DIRECTION

    @staticmethod
    def getReadingConverterClasses():
        """
        Gets all classes from the reading module that implement
        L{ReadingConverter}.

        @rtype: dictionary of string class pairs
        @return: dictionary of all classes inheriting form
            L{ReadingConverter}
        """
        readingConverterClasses = {}

        # get all non-abstract classes that inherit from ReadingConverter
        readingConverterClasses = dict([(clss.__name__, clss) \
            for clss in converter.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, converter.ReadingConverter) \
            and clss.CONVERSION_DIRECTIONS])

        return readingConverterClasses


class ReadingConverterConsistencyTest(ReadingConverterTest):
    """Base class for consistency testing of L{ReadingConverter}s."""

    OPTIONS_LIST = []
    """
    List of option configurations, simmilar to C{test.readingoperator.DIALECTS}.
    """

    def testReadingConverterUnique(self):
        """Test if only one ReadingConverter exists for each reading."""
        seen = False

        for clss in self.getReadingConverterClasses().values():
            if self.CONVERSION_DIRECTION in clss.CONVERSION_DIRECTIONS:
                self.assert_(not seen,
                    "Conversion %s to %s has more than one converter" \
                    % self.CONVERSION_DIRECTION)
                seen = True

    def testInstantiation(self):
        """Test if given conversion can be instantiated"""
        self.assert_(self.readingConverterClass != None,
            "No reading converter class found" \
                + ' (conversion %s to %s)' % self.CONVERSION_DIRECTION)

        forms = [{}]
        forms.extend(self.OPTIONS_LIST)
        for dialect in forms:
            # instantiate
            self.readingConverterClass(**dialect)

    def testDefaultOptions(self):
        """
        Test if option dict returned by C{getDefaultOptions()} is well-formed
        and includes all options found in the test case's options.
        """
        defaultOptions = self.readingConverterClass.getDefaultOptions()

        self.assertEquals(type(defaultOptions), type({}),
            "Default options %s is not of type dict" % repr(defaultOptions) \
            + ' (conversion %s to %s)' % self.CONVERSION_DIRECTION)
        # test if option names are well-formed
        for option in defaultOptions:
            self.assertEquals(type(option), type(''),
                "Option %s is not of type str" % repr(option) \
                + ' (conversion %s to %s)' % self.CONVERSION_DIRECTION)

        # test all given options
        forms = [{}]
        forms.extend(self.OPTIONS_LIST)
        for options in forms:
            for option in options:
                self.assert_(option in defaultOptions,
                    "Test case option %s not found in default options" \
                        % repr(option) \
                    + ' (conversion %s to %s, options %s)' \
                        % (self.fromReading, self.toReading, options))

        # test instantiation of default options
        defaultInstance = self.readingConverterClass(**defaultOptions)

        # check if option value changes after instantiation
        for option in defaultOptions:
            if option in ['sourceOperators', 'targetOperators']:
                continue # TODO in general forbid changing of options?
            self.assertEqual(defaultInstance.getOption(option),
                defaultOptions[option],
                "Default option value %s for %s changed on instantiation: %s" \
                    % (repr(defaultOptions[option]), repr(option),
                        repr(defaultInstance.getOption(option))) \
                + ' (conversion %s to %s)' % self.CONVERSION_DIRECTION)

        # check options against instance without explicit option dict
        instance = self.readingConverterClass()
        for option in defaultOptions:
            self.assertEqual(instance.getOption(option),
                defaultInstance.getOption(option),
                "Option value for %s unequal for default instances: %s and %s" \
                    % (repr(option), repr(instance.getOption(option)),
                        repr(defaultInstance.getOption(option))) \
                + ' (conversion %s to %s)' % self.CONVERSION_DIRECTION)

    def testLetterCaseConversion(self):
        """
        Check if letter case is transferred during conversion.
        """
        fromReadingClass = self.f.getReadingOperatorClass(self.fromReading)
        if not issubclass(fromReadingClass, operator.RomanisationOperator) \
            or 'case' not in fromReadingClass.getDefaultOptions():
            return

        toReadingClass = self.f.getReadingOperatorClass(self.toReading)
        if not issubclass(toReadingClass, operator.RomanisationOperator) \
            or 'case' not in toReadingClass.getDefaultOptions():
            return

        import unicodedata

        # TODO extend once unit test includes reading dialects
        entities = self.f.getReadingEntities(self.fromReading)
        for dialect in self.OPTIONS_LIST:
            for entity in entities:
                try:
                    toEntity = self.f.convert(entity, self.fromReading,
                        self.toReading, **dialect)
                    self.assert_(toEntity.islower(),
                        'Mismatch in letter case for conversion %s to %s' \
                            % (repr(entity), repr(toEntity)) \
                        + ' (conversion %s to %s, options %s)' \
                            % (self.fromReading, self.toReading, dialect))

                    if 'sourceOptions' in dialect \
                        and 'case' in dialect['sourceOptions'] \
                        and dialect['sourceOptions']['case'] == 'lower':
                        # the following conversions only hold for upper case
                        continue

                    toEntity = self.f.convert(entity.upper(), self.fromReading,
                        self.toReading, **dialect)
                    self.assert_(toEntity.isupper(),
                        'Mismatch in letter case for conversion %s to %s' \
                            % (repr(entity.upper()), repr(toEntity)) \
                        + ' (conversion %s to %s, options %s)' \
                            % (self.fromReading, self.toReading, dialect))

                    ownDialect = dialect.copy()
                    if 'targetOptions' not in ownDialect:
                        ownDialect['targetOptions'] = {}
                    ownDialect['targetOptions']['case'] = 'lower' # TODO
                    toEntity = self.f.convert(entity.upper(), self.fromReading,
                        self.toReading, **ownDialect)

                    self.assert_(toEntity.islower(),
                        'Mismatch in conversion to lower case from %s to %s' \
                            % (repr(entity.upper()), repr(toEntity)) \
                        + ' (conversion %s to %s, options %s)' \
                            % (self.fromReading, self.toReading, dialect))

                    toEntity = self.f.convert(entity.title(), self.fromReading,
                        self.toReading, **dialect)

                    # trade-off for one-char entities: upper-case goes for title
                    oneCharEntity = len([c for c \
                        in unicodedata.normalize("NFD", unicode(entity)) \
                        if 'a' <= c <= 'z']) == 1
                    self.assert_(toEntity.istitle() \
                            or (oneCharEntity and toEntity.isupper()),
                        'Mismatch in title case for conversion %s to %s' \
                            % (repr(entity.title()), repr(toEntity)) \
                        + ' (conversion %s to %s, options %s)' \
                            % (self.fromReading, self.toReading, dialect))
                except exception.ConversionError:
                    pass


class ReadingConverterTestCaseCheck(unittest.TestCase):
    """
    Checks if every L{ReadingConverter} has its own
    L{ReadingConverterConsistencyTest}.
    """
    def testEveryConverterHasConsistencyTest(self):
        """
        Check if every reading has a test case.
        """
        testClasses = self.getReadingConverterConsistencyTestClasses()
        testClassReadingNames = [clss.CONVERSION_DIRECTION for clss \
            in testClasses]
        self.f = ReadingFactory()

        for clss in self.f.getReadingConverterClasses():
            for direction in clss.CONVERSION_DIRECTIONS:
                self.assert_(direction in testClassReadingNames,
                    "Conversion from %s to %s" % direction \
                    + "has no ReadingOperatorConsistencyTest")

    @staticmethod
    def getReadingConverterConsistencyTestClasses():
        """
        Gets all classes implementing L{ReadingConverterConsistencyTest}.

        @rtype: list
        @return: list of all classes inheriting form
            L{ReadingConverterConsistencyTest}
        """
        # get all non-abstract classes that inherit from
        #   ReadingConverterConsistencyTest
        testModule = __import__("cjklib.test.readingconverter")
        testClasses = [clss for clss \
            in testModule.test.readingconverter.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, ReadingConverterConsistencyTest) \
            and clss.CONVERSION_DIRECTION]

        return testClasses


class ReadingConverterReferenceTest(ReadingConverterTest):
    """
    Base class for testing of references against L{ReadingConverter}s.
    These tests assure that the given values are returned correctly.
    """
    CONVERSION_REFERENCES = []
    """
    References to test C{decompose()} operation.
    List of options/reference tuples, schema:
    ({options, sourceOptions={}, targetOptions={}}, [(reference, target)])
    """

    def testConversionReferences(self):
        """Test if the given conversion references are reached."""
        for options, references in self.CONVERSION_REFERENCES:
            for reference, target in references:
                args = [reference, self.fromReading, self.toReading]

                if type(target) == types.TypeType \
                    and issubclass(target, Exception):
                    self.assertRaises(target, self.f.convert, *args, **options)
                else:
                    string = self.f.convert(*args, **options)

                    self.assertEquals(string, target,
                        "Conversion for %s to %s failed: %s " \
                            % (repr(reference), repr(target), repr(string)) \
                        + ' (conversion %s to %s, options %s)' \
                            % (self.fromReading, self.toReading, options))


class CantoneseYaleDialectConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('CantoneseYale', 'CantoneseYale')


# TODO
class CantoneseYaleDialectReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('CantoneseYale', 'CantoneseYale')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {'toneMarkType': 'Numbers'}}, [
            (u'gwóngjāuwá', u'gwong2jau1wa2'),
            (u'gwóngjàuwá', u'gwong2jau1wa2'),
            (u'GWÓNGJĀUWÁ', u'GWONG2JAU1WA2'),
            (u'sīsísisìhsíhsihsīksiksihk', u'si1si2si3si4si5si6sik1sik3sik6'),
            (u'SÌSÍSISÌHSÍHSIHSĪKSIKSIHK', u'SI1SI2SI3SI4SI5SI6SIK1SIK3SIK6'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'Numbers'}, 'targetOptions': {}}, [
            (u'gwong2jau1wa2', u'gwóngjāuwá'),
            (u'gwong2jauwa2', exception.ConversionError),
            (u'GWONG2JAU1WA2', u'GWÓNGJĀUWÁ'),
            (u'si1si2si3si4si5si6sik1sik3sik6', u'sīsísisìhsíhsihsīksiksihk'),
            (u'SI1SI2SI3SI4SI5SI6SIK1SIK3SIK6', u'SĪSÍSISÌHSÍHSIHSĪKSIKSIHK'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'Numbers',
            'YaleFirstTone': '1stToneFalling'},
            'targetOptions': {}}, [
            (u'gwong2jau1wa2', u'gwóngjàuwá'),
            (u'si1si2si3si4si5si6sik1sik3sik6', u'sìsísisìhsíhsihsīksiksihk'),
            (u'SI1SI2SI3SI4SI5SI6SIK1SIK3SIK6', u'SÌSÍSISÌHSÍHSIHSĪKSIKSIHK'),
            ]),
        ({'sourceOptions': {'strictDiacriticPlacement': True},
            'targetOptions': {'toneMarkType': 'Numbers'}}, [
            (u'gwóngjaùwá', u'gwóngjaùwá'),
            ]),
        ({'sourceOptions': {'strictSegmentation': True,
            'strictDiacriticPlacement': True},
            'targetOptions': {'toneMarkType': 'Numbers'}}, [
            (u'gwóngjaùwá', exception.DecompositionError),
            ]),
        ]


class JyutpingDialectConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Jyutping', 'Jyutping')


## TODO
#class JyutpingDialectReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('Jyutping', 'Jyutping')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class JyutpingYaleConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Jyutping', 'CantoneseYale')

    OPTIONS_LIST = [{'YaleFirstTone': '1stToneFalling'}]


# TODO
class JyutpingYaleReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Jyutping', 'CantoneseYale')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            (u'gwong2zau1waa2', u'gwóngjāuwá'),
            (u'gwong2yau1waa2', u'gwóngyau1wá'),
            (u'GWONG2ZAU1WAA2', u'GWÓNGJĀUWÁ'),
            ]),
        ]


class YaleJyutpingConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('CantoneseYale', 'Jyutping')


# TODO
class YaleJyutpingReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('CantoneseYale', 'Jyutping')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            (u'gwóngjāuwá', u'gwong2zau1waa2'),
            (u'gwóngjàuwá', u'gwong2zau1waa2'),
            (u'GWÓNGJĀUWÁ', u'GWONG2ZAU1WAA2'),
            ]),
        ]


class PinyinDialectConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'Pinyin')

    OPTIONS_LIST = [{'keepPinyinApostrophes': True},
        {'breakUpErhua': 'on'}]


class PinyinDialectReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'Pinyin')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            (u'xīān', u"xī'ān"),
            ]),
        ({'sourceOptions': {'toneMarkType': 'Numbers'}, 'targetOptions': {}}, [
            ('lao3shi1', u'lǎoshī'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'Numbers', 'yVowel': 'v'},
            'targetOptions': {}}, [
            ('nv3hai2', u'nǚhái'),
            ('NV3HAI2', u'NǙHÁI'),
            ]),
        ]


class WadeGilesDialectConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'WadeGiles')


## TODO
#class WadeGilesDialectReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('WadeGiles', 'WadeGiles')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class WadeGilesPinyinConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'Pinyin')


# TODO
class WadeGilesPinyinReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'Pinyin')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            (u'kuo', exception.AmbiguousConversionError),
            (u'kuo³-yü²', u'kuo³-yü²'),
            (u'kuo3-yü2', u'guǒyú'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'SuperscriptNumbers'},
            'targetOptions': {}}, [
            (u'kuo³-yü²', u'guǒyú'),
            (u'KUO³-YÜ²', u'GUǑYÚ'),
            ]),
        ]


class PinyinWadeGilesConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'WadeGiles')


## TODO
#class PinyinWadeGilesReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('Pinyin', 'WadeGiles')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class GRDialectConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'GR')

    OPTIONS_LIST = [{'keepGRApostrophes': True}]


# TODO
class GRDialectReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'GR')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {'GRSyllableSeparatorApostrophe': "'"},
            'targetOptions': {'GRRhotacisedFinalApostrophe': "'"}}, [
            (u"tian'anmen", u'tian’anmen'),
            (u'jie’l', u"jie'l")
            ]),
        ]


class GRPinyinConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'Pinyin')

    OPTIONS_LIST = [{'GROptionalNeutralToneMapping': 'neutral'}]


# TODO
class GRPinyinReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'Pinyin')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            # Extract from Y.R. Chao's Sayable Chinese quoted from English
            #   Wikipedia, added concrete tone specifiers to "de", "men",
            #   "jing", "bu" and applied full form for g (.geh) choosing
            #   "always" neutral tone, removed hyphen in i-goong, changed the
            #   Pinyin transcript to not show tone sandhis, fixed punctuation
            #   marks in Pinyin
            (u'"Hannshyue" .de mingcheng duey Jonggwo yeou idean buhtzuenjinq .de yihwey. Woo.men tingshuo yeou "Yinnduhshyue", "Aijyishyue", "Hannshyue", erl meiyeou tingshuo yeou "Shilahshyue", "Luomaashyue", genq meiyeou tingshuo yeou "Inggwoshyue", "Meeigwoshyue". "Hannshyue" jey.geh mingcheng wanchyuan beaushyh Ou-Meei shyuejee duey nahshie yii.jing chernluen .de guulao-gwojia .de wenhuah .de ijoong chingkann .de tayduh.', u'"Hànxué" de míngchēng duì Zhōngguó yǒu yīdiǎn bùzūnjìng de yìwèi. Wǒmen tīngshuō yǒu "Yìndùxué", "Āijíxué", "Hànxué", ér méiyǒu tīngshuō yǒu "Xīlàxué", "Luómǎxué", gèng méiyǒu tīngshuō yǒu "Yīngguóxué", "Měiguóxué". "Hànxué" zhèige míngchēng wánquán biǎoshì Ōu-Měi xuézhě duì nàxiē yǐjing chénlún de gǔlǎo-guójiā de wénhuà de yīzhǒng qīngkàn de tàidù.'),
            #(u'hairtz', u'háizi'), (u'ig', u'yīgè'), (u'sherm', u'shénme'), # TODO implement
            #(u'sherm.me', u'shénme'), (u'tzeem.me', u'zěnme'),
            #(u'tzeem.me', u'zěnme'), (u'tzemm', u'zènme'),
            #(u'tzemm.me', u'zènme'), (u'jemm', u'zhème'),
            #(u'jemm.me', u'zhème'), (u'nemm', u'neme'), (u'nemm.me', u'neme'),
            #(u'.ne.me', u'neme'), (u'woom', u'wǒmen'), (u'shie.x', u'xièxie'),
            #(u'duey .le vx', u'duì le duì le'), (u'j-h-eh', u'zhè'),
            #(u"liibay’i", u'lǐbàiyī'), (u"san’g ren", u'sānge rén'),
            #(u"shyr’ell", u"shí'èr")
            ]),
        ]


class PinyinGRConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'GR')


## TODO
#class PinyinGRReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('Pinyin', 'GR')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class BraillePinyinConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('MandarinBraille', 'Pinyin')


# TODO
class BraillePinyinReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('MandarinBraille', 'Pinyin')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {'toneMarkType': 'Numbers'}}, [
            (u'⠍⠢⠆', exception.AmbiguousConversionError), # mo/me
            (u'⠇⠢⠆', exception.AmbiguousConversionError), # lo/le
            (u'⠢⠆', exception.AmbiguousConversionError),  # o/e
            (u'⠛⠥', u'gu5'),
            (u'⠛⠥⠁', u'gu1'),
            (u'⠛⠬', u'ju5'),
            ]),
        ]


class PinyinBrailleConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'MandarinBraille')


# TODO
class PinyinBrailleReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'MandarinBraille')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {'toneMarkType': 'Numbers'}, 'targetOptions': {}}, [
            ('lao3shi1', u'⠇⠖⠄⠱⠁'),
            ]),
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            (u'lǎoshī', u'⠇⠖⠄⠱⠁'),
            ('lao3shi1', 'lao3shi1'),
            (u'mò', u'⠍⠢⠆'),
            (u'mè', u'⠍⠢⠆'),
            (u'gu', u'⠛⠥'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'Numbers'}, 'targetOptions': {}}, [
            (u'Qing ni deng yi1xia!', u'⠅⠡ ⠝⠊ ⠙⠼ ⠊⠁⠓⠫⠰⠂'),
            (u'mangwen shushe', u'⠍⠦⠒ ⠱⠥⠱⠢'),
            (u'shi4yong', u'⠱⠆⠹'),
            (u'yi1xia', u'⠊⠁⠓⠫'),
            (u'yi3xia', u'⠊⠄⠓⠫'),
            (u'gu', u'⠛⠥'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'Numbers'},
            'targetOptions': {'missingToneMark': 'fifth'}}, [
            (u'gu', exception.ConversionError),
            (u'gu5', u'⠛⠥'),
            ]),
        ]


class PinyinIPAConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'MandarinIPA')

    # TODO add another sandhi function reference
    OPTIONS_LIST = [{'sandhiFunction': None},
        {'coarticulationFunction': \
            converter.PinyinIPAConverter.finalECoarticulation}]


# TODO
class PinyinIPAReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('Pinyin', 'MandarinIPA')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {'toneMarkType': 'Numbers'}, 'targetOptions': {}}, [
            ('lao3shi1', u'lau˨˩.ʂʅ˥˥'),
            ('LAO3SHI1', u'lau˨˩.ʂʅ˥˥'),
            ]),
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            ('lao3shi1', 'lao3shi1'),
            ]),
        ]


class WadeGilesIPAConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'MandarinIPA')

    # TODO add another sandhi function reference
    OPTIONS_LIST = [{'sandhiFunction': None},
        {'coarticulationFunction': \
            converter.PinyinIPAConverter.finalECoarticulation}]


# TODO
class WadeGilesIPAReferenceTest(ReadingConverterReferenceTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'MandarinIPA')

    CONVERSION_REFERENCES = [
        ({'sourceOptions': {}, 'targetOptions': {}}, [
            (u'kuo3-yü2', u'kuo˨˩.y˧˥'),
            (u'LAO3-SHIH1', u'lau˨˩.ʂʅ˥˥'),
            ]),
        ({'sourceOptions': {'toneMarkType': 'SuperscriptNumbers'},
            'targetOptions': {}}, [
            (u'LAO3-SHIH1', 'LAO3-SHIH1'),
            (u'LAO³-SHIH¹', u'lau˨˩.ʂʅ˥˥'),
            ]),
        ]


class MandarinBrailleIPAConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('MandarinBraille', 'MandarinIPA')

    # TODO add another sandhi function reference
    OPTIONS_LIST = [{'sandhiFunction': None},
        {'coarticulationFunction': \
            converter.PinyinIPAConverter.finalECoarticulation}]


## TODO
#class MandarinBrailleIPAReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('MandarinBraille', 'MandarinIPA')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class BrailleGRConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('MandarinBraille', 'GR')


## TODO
#class BrailleGRReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('MandarinBraille', 'GR')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class GRBrailleConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'MandarinBraille')


## TODO
#class GRBrailleReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('GR', 'MandarinBraille')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class GRIPAConsistencyTest(ReadingConverterConsistencyTest, unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'MandarinIPA')

    # TODO add another sandhi function reference
    OPTIONS_LIST = [{'sandhiFunction': None},
        {'coarticulationFunction': \
            converter.PinyinIPAConverter.finalECoarticulation}]


## TODO
#class GRIPAGilesReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('GR', 'MandarinIPA')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class GRWadeGilesConsistencyTest(ReadingConverterConsistencyTest, unittest.TestCase):
    CONVERSION_DIRECTION = ('GR', 'WadeGiles')


## TODO
#class GRWadeGilesReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('GR', 'WadeGiles')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class WadeGilesGRConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'GR')


## TODO
#class WadeGilesGRReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('WadeGiles', 'GR')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class WadeGilesBrailleConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('WadeGiles', 'MandarinBraille')


## TODO
#class WadeGilesBrailleReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('WadeGiles', 'MandarinBraille')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]


class BrailleWadeGilesConsistencyTest(ReadingConverterConsistencyTest,
    unittest.TestCase):
    CONVERSION_DIRECTION = ('MandarinBraille', 'WadeGiles')


## TODO
#class BrailleWadeGilesReferenceTest(ReadingConverterReferenceTest,
    #unittest.TestCase):
    #CONVERSION_DIRECTION = ('MandarinBraille', 'WadeGiles')

    #CONVERSION_REFERENCES = [
        #({'sourceOptions': {}, 'targetOptions': {}}, [
            #]),
        #]
