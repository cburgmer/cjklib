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

u"""
Provides L{ReadingConverter}s, classes to convert strings written in a character
reading to another reading.

Examples
========
Convert a string from I{Jyutping} to I{Cantonese Yale}:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert('gwong2jau1waa2', 'Jyutping', 'CantoneseYale')
    u'gw\xf3ngy\u0101uw\xe1'

This is also possible creating a converter instance explicitly using the
factory:

    >>> jyc = f.createReadingConverter('GR', 'Pinyin')
    >>> jyc.convert('Woo.men tingshuo yeou "Yinnduhshyue", "Aijyishyue"')
    u'W\u01d2men t\u012bngshu\u014d y\u01d2u "Y\xecnd\xf9xu\xe9", \
"\u0100ij\xedxu\xe9"'

Convert between different dialects of the same reading I{Wade-Giles}:

    >>> f.convert(u'kuo3-yü2', 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'toneMarkType': 'Numbers'},
    ...     targetOptions={'toneMarkType': 'SuperscriptNumbers'})
    u'kuo\xb3-y\xfc\xb2'

See L{PinyinDialectConverter} for more examples.
"""
import re
import copy

from sqlalchemy import select
from sqlalchemy.sql import and_, or_, not_

from cjklib.exception import (ConversionError, AmbiguousConversionError,
    InvalidEntityError, UnsupportedError)
from cjklib.dbconnector import DatabaseConnector
import operator
import cjklib.reading

class ReadingConverter(object):
    """
    Defines an abstract converter between two or more I{character reading}s.

    The basic method is L{convert()} which converts one input string from one
    reading to another.

    The methods L{getDefaultOptions()} and L{getOption()} provide means to
    handle conversion specific settings.

    The class itself can't be used directly, it has to be subclassed and its
    methods need to be extended.
    """
    CONVERSION_DIRECTIONS = []
    """
    List of tuples for specifying supported conversion directions from reading A
    to reading B. If both directions are supported, two tuples (A, B) and (B, A)
    are given.
    """

    def __init__(self, *args, **options):
        """
        Creates an instance of the ReadingConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        """
        if 'dbConnectInst' in options:
            self.db = options['dbConnectInst']
        else:
            self.db = DatabaseConnector.getDBConnector()

        self.readingFact = cjklib.reading.ReadingFactory(dbConnectInst=self.db)

        self.optionValue = {}
        defaultOptions = self.getDefaultOptions()
        for option in defaultOptions:
            if type(defaultOptions[option]) in [type(()), type([]), type({})]:
                self.optionValue[option] = copy.deepcopy(defaultOptions[option])
            else:
                self.optionValue[option] = defaultOptions[option]

        # get reading operators
        for arg in args:
            if isinstance(arg, operator.ReadingOperator):
                # store reading operator for the given reading
                self.optionValue['sourceOperators'][arg.READING_NAME] = arg
                self.optionValue['targetOperators'][arg.READING_NAME] = arg
            else:
                raise ValueError("unknown type '" + str(type(arg)) \
                    + "' given as ReadingOperator")

        # get specialised source/target readings
        if 'sourceOperators' in options:
            for arg in options['sourceOperators']:
                if isinstance(arg, operator.ReadingOperator):
                    # store reading operator for the given reading
                    self.optionValue['sourceOperators'][arg.READING_NAME] = arg
                else:
                    raise ValueError("unknown type '" + str(type(arg)) \
                        + "' given as source reading operator")

        if 'targetOperators' in options:
            for arg in options['targetOperators']:
                if isinstance(arg, operator.ReadingOperator):
                    # store reading operator for the given reading
                    self.optionValue['targetOperators'][arg.READING_NAME] = arg
                else:
                    raise ValueError("unknown type '" + str(type(arg)) \
                        + "' given as target reading operator")

    @classmethod
    def getDefaultOptions(cls):
        """
        Returns the reading converter's default options.

        The keyword 'dbConnectInst' is not regarded a configuration option of
        the converter and is thus not included in the dict returned.

        @rtype: dict
        @return: the reading converter's default options.
        """
        return {'sourceOperators': {}, 'targetOperators': {}}

    def getOption(self, option):
        """
        Returns the value of the reading converter's option.

        @return: the value of the given reading converter's option.
        """
        return self.optionValue[option]

    def convert(self, string, fromReading, toReading):
        """
        Converts a string in the source reading to the given target reading.

        @type string: str
        @param string: string written in the source reading
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: str
        @returns: the input string converted to the C{toReading}
        @raise DecompositionError: if the string can not be decomposed into
            basic entities with regards to the source reading or the given
            information is insufficient.
        @raise ConversionError: on operations specific to the conversion between
            the two readings (e.g. error on converting entities).
        @raise UnsupportedError: if source or target reading is not supported
            for conversion.
        """
        # decompose string
        fromReadingEntities = self._getFromOperator(fromReading).decompose(
            string)
        # convert entities
        toReadingEntities = self.convertEntities(fromReadingEntities,
            fromReading, toReading)
        # compose
        return self._getToOperator(toReading).compose(toReadingEntities)

    def convertEntities(self, readingEntities, fromReading, toReading):
        """
        Converts a list of entities in the source reading to the given target
        reading.

        The default implementation will raise a NotImplementedError.

        @type readingEntities: list of str
        @param readingEntities: list of entities written in source reading
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: list of str
        @return: list of entities written in target reading
        @raise ConversionError: on operations specific to the conversion between
            the two readings (e.g. error on converting entities).
        @raise UnsupportedError: if source or target reading is not supported
            for conversion.
        @raise InvalidEntityError: if an invalid entity is given.
        """
        raise NotImplementedError

    def _getFromOperator(self, readingN):
        """
        Gets a reading operator instance for conversion from the given reading.

        @type readingN: str
        @param readingN: name of reading
        @rtype: instance
        @return: a L{ReadingOperator} instance
        @raise UnsupportedError: if the given reading is not supported.
        """
        if readingN not in self.getOption('sourceOperators'):
            self.optionValue['sourceOperators'][readingN] \
                = self.readingFact._getReadingOperatorInstance(readingN)
        return self.getOption('sourceOperators')[readingN]

    def _getToOperator(self, readingN):
        """
        Gets a reading operator instance for conversion to the given reading.

        @type readingN: str
        @param readingN: name of reading
        @rtype: instance
        @return: a L{ReadingOperator} instance
        @raise UnsupportedError: if the given reading is not supported.
        """
        if readingN not in self.getOption('targetOperators'):
            self.optionValue['targetOperators'][readingN] \
                = self.readingFact._getReadingOperatorInstance(readingN)
        return self.getOption('targetOperators')[readingN]


class DialectSupportReadingConverter(ReadingConverter):
    """
    Defines an abstract L{ReadingConverter} that support non-standard reading
    representations (dialect) as in- and output.

    Input will be converted to a standard representation of the input reading
    before the actual conversion step is done. If needed the converted reading
    will be converted to a defined dialect.
    """
    DEFAULT_READING_OPTIONS = {}
    """
    Defines the default reading options for the reading dialect used as a bridge
    in conversion between the user specified representation and the target
    reading.

    The most general reading dialect should be specified as to allow for a broad
    range of input.
    """

    def convertEntities(self, readingEntities, fromReading, toReading):
        """
        Converts a list of entities in the source reading to the given target
        reading.

        @type readingEntities: list of str
        @param readingEntities: list of entities written in source reading
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: list of str
        @return: list of entities written in target reading
        @raise AmbiguousConversionError: if conversion for a specific entity of
            the source reading is ambiguous.
        @raise ConversionError: on other operations specific to the conversion
            between the two readings (e.g. error on converting entities).
        @raise UnsupportedError: if source or target reading is not supported
            for conversion.
        @raise InvalidEntityError: if an invalid entity is given.
        """
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")

        # first split into reading and non-reading sequences, so that later
        #   reading conversion is only done for reading entities
        entitySequence = []
        for entity in readingEntities:
            # get last reading entity sequence if any
            if entitySequence and type(entitySequence[-1]) == type([]):
                readingEntitySequence = entitySequence.pop()
            else:
                readingEntitySequence = []

            if self._getFromOperator(fromReading).isReadingEntity(entity):
                # add reading entity to preceding ones
                readingEntitySequence.append(entity)
                entitySequence.append(readingEntitySequence)
            else:
                if readingEntitySequence:
                    entitySequence.append(readingEntitySequence)
                # append non-reading entity
                entitySequence.append(entity)

        # convert to standard form if supported (step 1)
        if self.readingFact.isReadingConversionSupported(fromReading,
            fromReading):
            # get default options if available used for converting the reading
            #   dialect
            if fromReading in self.DEFAULT_READING_OPTIONS:
                fromDefaultOptions = self.DEFAULT_READING_OPTIONS[fromReading]
            else:
                fromDefaultOptions = {}
            # use user specified source operator, set target to default form
            converter = self.readingFact._getReadingConverterInstance(
                fromReading, fromReading,
                sourceOperators=[self._getFromOperator(fromReading)],
                targetOptions=fromDefaultOptions)

            convertedEntitySequence = []
            for sequence in entitySequence:
                if type(sequence) == type([]):
                    convertedEntities = converter.convertEntities(sequence,
                        fromReading, fromReading)
                    convertedEntitySequence.append(convertedEntities)
                else:
                    convertedEntitySequence.append(sequence)
            entitySequence = convertedEntitySequence

        # do the actual conversion to the target reading (step 2)
        toEntitySequence = self.convertEntitySequence(entitySequence,
            fromReading, toReading)

        # convert to requested form if supported (step 3)
        if self.readingFact.isReadingConversionSupported(toReading, toReading):
            # get default options if available used for converting the reading
            #   dialect
            if toReading in self.DEFAULT_READING_OPTIONS:
                toDefaultOptions = self.DEFAULT_READING_OPTIONS[toReading]
            else:
                toDefaultOptions = {}
            # use user specified target operator, set source to default form
            converter = self.readingFact._getReadingConverterInstance(
                toReading, toReading, sourceOptions=toDefaultOptions,
                targetOperators=[self._getToOperator(toReading)])

            convertedEntitySequence = []
            for sequence in toEntitySequence:
                if type(sequence) == type([]):
                    convertedEntities = converter.convertEntities(sequence,
                        toReading, toReading)
                    convertedEntitySequence.append(convertedEntities)
                else:
                    convertedEntitySequence.append(sequence)
            toEntitySequence = convertedEntitySequence

        # flatten into target entity list
        toReadingEntities = []
        for sequence in toEntitySequence:
            if type(sequence) == type([]):
                toReadingEntities.extend(sequence)
            else:
                toReadingEntities.append(sequence)

        return toReadingEntities

    def convertEntitySequence(self, entitySequence, fromReading, toReading):
        """
        Convert a list of reading entities in standard representatinon given by
        L{DEFAULT_READING_OPTIONS} and non reading entities from the source
        reading to the target reading.

        The default implementation will raise a NotImplementedError.

        @type entitySequence: list structure
        @param entitySequence: list of reading entities given as list and
            non-reading entities as single str objects
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: list structure
        @return: list of converted reading entities given as list and
            non-reading entities as single str objects
        """
        raise NotImplementedError


class EntityWiseReadingConverter(ReadingConverter):
    """
    Defines an abstract L{ReadingConverter} between two or more I{readings}s for
    doing entity wise conversion.

    Converters that simply convert one syllable at once can implement this class
    and merely need to overwrite L{convertBasicEntity()}
    """
    def convertEntities(self, readingEntities, fromReading, toReading):
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")

        # do a entity wise conversion to the target reading
        toReadingEntities = []

        for entity in readingEntities:
            # convert reading entities, don't convert the rest
            if self._getFromOperator(fromReading).isReadingEntity(entity):
                toReadingEntity = self.convertBasicEntity(entity, fromReading,
                    toReading)
                toReadingEntities.append(toReadingEntity)
            else:
                toReadingEntities.append(entity)

        return toReadingEntities

    def convertBasicEntity(self, entity, fromReading, toReading):
        """
        Converts a basic entity (e.g. a syllable) in the source reading to the
        given target reading.

        This method is called by L{convertEntities()} and a single entity is
        given for conversion.

        The default implementation will raise a NotImplementedError.

        @type entity: str
        @param entity: string written in the source reading
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: str
        @returns: the entity converted to the C{toReading}
        @raise AmbiguousConversionError: if conversion for this entity of the
            source reading is ambiguous.
        @raise ConversionError: on other operations specific to the conversion
            of the entity.
        @raise InvalidEntityError: if the entity is invalid.
        """
        raise NotImplementedError


class RomanisationConverter(DialectSupportReadingConverter):
    """
    Defines an abstract L{ReadingConverter} between two or more
    I{romanisation}s.

    Reading dialects can produce different entities which have to be handled by
    the conversion process. This is realised by converting the given reading
    dialect to a default form, then converting to the default target reading and
    finally converting to the specified target reading dialect. On conversion
    step thus involves three single conversion steps using a default form. This
    default form can be defined in L{DEFAULT_READING_OPTIONS}.

    Upper or lower case will be transfered between syllables, no special
    formatting according to anyhow defined standards will be guaranteed.
    Upper/lower case will be identified according to three classes: either the
    whole syllable is upper case, only the initial letter is upper case or
    otherwise the whole syllable is assumed being lower case.

    The class itself can't be used directly, it has to be subclassed and
    L{convertBasicEntity()} has to be implemented, as to make the translation of
    a syllable from one romanisation to another possible.
    """

    def convertEntitySequence(self, entitySequence, fromReading, toReading):
        toEntitySequence = []
        for sequence in entitySequence:
            if type(sequence) == type([]):
                toSequence = []
                for entity in sequence:
                    toReadingEntity = self.convertBasicEntity(entity.lower(),
                        fromReading, toReading)

                    # transfer capitalisation, target reading dialect will to
                    #   final transformation (lower/upper/both)
                    if entity.isupper():
                        toReadingEntity = toReadingEntity.upper()
                    elif entity.istitle():
                        toReadingEntity = toReadingEntity.capitalize()

                    toSequence.append(toReadingEntity)
                toEntitySequence.append(toSequence)
            else:
                toEntitySequence.append(sequence)

        return toEntitySequence

    def convertBasicEntity(self, entity, fromReading, toReading):
        """
        Converts a basic entity (e.g. a syllable) in the source reading to the
        given target reading.

        This method is called by L{convertEntities()} and a lower case entity
        is given for conversion. The returned value should be in lower case
        characters too, as L{convertEntities()} will take care of
        capitalisation.

        If a single entity needs to be converted it is recommended to use
        L{convertEntities()} instead. In the general case it can not be ensured
        that a mapping from one reading to another can be done by the simple
        conversion of a basic entity. One-to-many mappings are possible and
        there is no guarantee that any entity of a reading recognised by
        L{operator.ReadingOperator.isReadingEntity()} will be mapped here.

        The default implementation will raise a NotImplementedError.

        @type entity: str
        @param entity: string written in the source reading in lower case
            letters
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: str
        @returns: the entity converted to the C{toReading} in lower case
        @raise AmbiguousConversionError: if conversion for this entity of the
            source reading is ambiguous.
        @raise ConversionError: on other operations specific to the conversion
            of the entity.
        @raise InvalidEntityError: if the entity is invalid.
        """
        raise NotImplementedError


class PinyinDialectConverter(ReadingConverter):
    u"""
    Provides a converter for different representations of the Chinese
    romanisation I{Hanyu Pinyin}.

    Examples
    ========
    The following examples show how to convert between different representations
    of Pinyin.
        - Create the Converter and convert from standard Pinyin to Pinyin with
            tones represented by numbers:

            >>> from cjklib.reading import *
            >>> targetOp = operator.PinyinOperator(toneMarkType='Numbers')
            >>> pinyinConv = converter.PinyinDialectConverter(
            ...     targetOperators=[targetOp])
            >>> pinyinConv.convert(u'hànzì', 'Pinyin', 'Pinyin')
            u'han4zi4'

        - Convert Pinyin written with numbers, the ü (u with umlaut) replaced
            by character v and omitted fifth tone to standard Pinyin:

            >>> sourceOp = operator.PinyinOperator(toneMarkType='Numbers',
            ...    yVowel='v', missingToneMark='fifth')
            >>> pinyinConv = converter.PinyinDialectConverter(
            ...     sourceOperators=[sourceOp])
            >>> pinyinConv.convert('nv3hai2zi', 'Pinyin', 'Pinyin')
            u'n\u01dah\xe1izi'

        - Or more elegantly:

            >>> f = ReadingFactory()
            >>> f.convert('nv3hai2zi', 'Pinyin', 'Pinyin',
            ...     sourceOptions={'toneMarkType': 'Numbers', 'yVowel': 'v',
            ...     'missingToneMark': 'fifth'})
            u'n\u01dah\xe1izi'

        - Decompose the reading of a dictionary entry from CEDICT into syllables
            and convert the ü-vowel and forms of I{Erhua sound}:

            >>> pinyinFrom = operator.PinyinOperator(toneMarkType='Numbers',
            ...     yVowel='u:', Erhua='oneSyllable')
            >>> syllables = pinyinFrom.decompose('sun1nu:r3')
            >>> print syllables
            ['sun1', 'nu:r3']
            >>> pinyinTo = operator.PinyinOperator(toneMarkType='Numbers',
            ...     Erhua='twoSyllables')
            >>> pinyinConv = converter.PinyinDialectConverter(
            ...     sourceOperators=[pinyinFrom], targetOperators=[pinyinTo])
            >>> pinyinConv.convertEntities(syllables, 'Pinyin', 'Pinyin')
            [u'sun1', u'n\xfc3', u'r5']

        - Or more elegantly with entities already decomposed:

            >>> f.convertEntities(['sun1', 'nu:r3'], 'Pinyin', 'Pinyin',
            ...     sourceOptions={'toneMarkType': 'Numbers', 'yVowel': 'u:',
            ...        'Erhua': 'oneSyllable'},
            ...     targetOptions={'toneMarkType': 'Numbers',
            ...        'Erhua': 'twoSyllables'})
            [u'sun1', u'n\xfc3', u'r5']

        - Fix cosmetic errors in Pinyin input (note tone mark and apostrophe):

            >>> f.convert(u"Wǒ peí nǐ qù Xīān.", 'Pinyin', 'Pinyin')
            u"W\u01d2 p\xe9i n\u01d0 q\xf9 X\u012b'\u0101n."
    """
    CONVERSION_DIRECTIONS = [('Pinyin', 'Pinyin')]

    def __init__(self, *args, **options):
        u"""
        Creates an instance of the PinyinDialectConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        @keyword keepPinyinApostrophes: if set to C{True} apostrophes separating
            two syllables in Pinyin will be kept even if not necessary.
            Apostrophes missing according to the given rule will be added
            though.
        @keyword breakUpErhua: if set to C{'on'} I{Erhua} forms will be
            converted to single syllables with a full I{er} syllable regardless
            of the Erhua form setting of the target reading, e.g. I{zher} will
            be converted to I{zhe}, I{er}, if set to C{'auto'} Erhua forms are
            converted if the given target reading operator doesn't support
            Erhua forms, if set to C{'off'} Erhua forms will always be
            conserved.
        """
        super(PinyinDialectConverter, self).__init__(*args, **options)
        # set options
        if 'keepPinyinApostrophes' in options:
            self.optionValue['keepPinyinApostrophes'] \
                = options['keepPinyinApostrophes']

        if 'breakUpErhua' in options:
            if options['breakUpErhua'] not in ['on', 'auto', 'off']:
                raise ValueError("Invalid option '" \
                    + str(options['breakUpErhua']) \
                    + "' for keyword 'breakUpErhua'")
            self.optionValue['breakUpErhua'] = options['breakUpErhua']

        # get yVowel setting
        if self._getFromOperator('Pinyin').getOption('yVowel') != u'ü':
            self.fromYVowel \
                = self._getFromOperator('Pinyin').getOption('yVowel')
        else:
            self.fromYVowel = u'ü'
        if self._getToOperator('Pinyin').getOption('yVowel') != u'ü':
            self.toYVowel = self._getToOperator('Pinyin').getOption('yVowel')
        else:
            self.toYVowel = u'ü'

        # get Erhua settings, 'twoSyllables' is default
        if self.getOption('breakUpErhua') == 'on' \
            or (self.getOption('breakUpErhua') == 'auto' \
                and self._getToOperator('Pinyin').getOption('Erhua') \
                    == 'ignore')\
            or (self._getToOperator('Pinyin').getOption('Erhua') \
                == 'twoSyllables'\
            and self._getFromOperator('Pinyin').getOption('Erhua') \
                == 'oneSyllable'):
            # need to convert from one-syllable-form to two-syllables-form
            self.convertErhuaFunc = self.convertToTwoSyllablesErhua
        elif self._getToOperator('Pinyin').getOption('Erhua') == 'oneSyllable'\
            and self._getFromOperator('Pinyin').getOption('Erhua') \
                != 'oneSyllable':
            # need to convert from two-syllables-form to one-syllable-form
            self.convertErhuaFunc = self.convertToSingleSyllableErhua
        elif self._getFromOperator('Pinyin').getOption('Erhua') != 'ignore'\
            and self._getToOperator('Pinyin').getOption('Erhua') == 'ignore':
            # no real conversion but make sure to raise an error for Erhua forms
            self.convertErhuaFunc = self._checkForErhua
        else:
            # do nothing
            self.convertErhuaFunc = lambda x: x

    @classmethod
    def getDefaultOptions(cls):
        options = super(PinyinDialectConverter, cls).getDefaultOptions()
        options.update({'keepPinyinApostrophes': False, 'breakUpErhua': 'auto'})

        return options

    def convertEntities(self, readingEntities, fromReading='Pinyin',
        toReading='Pinyin'):
        """
        Converts a list of entities in the source reading to the given target
        reading.

        @type readingEntities: list of str
        @param readingEntities: list of entities written in source reading
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading
        @rtype: list of str
        @return: list of entities written in target reading
        @raise AmbiguousConversionError: if conversion for a specific entity of
            the source reading is ambiguous.
        @raise ConversionError: on other operations specific to the conversion
            between the two readings (e.g. error on converting entities).
        @raise UnsupportedError: if source or target reading is not supported
            for conversion.
        @raise InvalidEntityError: if an invalid entity is given.
        """
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")

        # remove apostrophes
        if not self.getOption('keepPinyinApostrophes'):
            readingEntities = self._getFromOperator(fromReading)\
                .removeApostrophes(readingEntities)

        # split syllables into plain syllable and tone part
        entityTuples = []
        for entity in readingEntities:
            # convert reading entities, don't convert the rest
            if self._getFromOperator(fromReading).isReadingEntity(entity):
                # split syllable into plain part and tonal information
                plainSyllable, tone = self._getFromOperator(fromReading)\
                    .splitEntityTone(entity)

                entityTuples.append((plainSyllable, tone))
            else:
                entityTuples.append(entity)

        # fix Erhua forms if needed
        entityTuples = self.convertErhuaFunc(entityTuples)

        targetTones = self._getToOperator(toReading).getTones()

        # convert
        toReadingEntities = []
        for entry in entityTuples:
            if type(entry) == type(()):
                plainSyllable, tone = entry

                # check if target operator supports missing tones
                if tone not in targetTones:
                    # missing tone not supported, raise a conversion error
                    raise AmbiguousConversionError("Target reading does not " \
                        "support missing tone information")

                # fix Erhua form if needed
                if plainSyllable.lower() == 'r' \
                    and ((self.getOption('breakUpErhua') == 'auto' \
                        and self._getToOperator('Pinyin').getOption('Erhua') \
                            == 'ignore') \
                        or self.getOption('breakUpErhua') == 'on'):
                    if plainSyllable.isupper():
                        plainSyllable = 'ER'
                    else:
                        plainSyllable = 'er'

                # check for special vowel for ü on input
                if self.fromYVowel != self.toYVowel:
                    plainSyllable = plainSyllable.replace(self.fromYVowel,
                        self.toYVowel)

                # capitalisation
                if self._getToOperator(toReading).getOption('case') == 'lower':
                    plainSyllable = plainSyllable.lower()
                elif self._getToOperator(toReading).getOption('case') \
                    == 'upper':
                    plainSyllable = plainSyllable.upper()

                try:
                    toReadingEntities.append(
                        self._getToOperator(toReading).getTonalEntity(
                            plainSyllable, tone))
                except InvalidEntityError, e:
                    # handle this as a conversion error as the converted
                    #   syllable is not accepted by the operator
                    raise ConversionError(*e.args)
            elif entry == self._getToOperator(fromReading)\
                .getOption('PinyinApostrophe'):
                toReadingEntities.append(self._getToOperator(toReading)\
                    .getOption('PinyinApostrophe'))
            else:
                toReadingEntities.append(entry)

        return toReadingEntities

    def convertToSingleSyllableErhua(self, entityTuples):
        """
        Converts the various I{Erhua} forms in a list of reading entities to
        a representation with one syllable, e.g. C{['tou2', 'r5']} to
        C{['tour2']}.

        @type entityTuples: list of tuple/str
        @param entityTuples: list of tuples with plain syllable and tone
        @rtype: list of tuple/str
        @return: list of tuples with plain syllable and tone
        """
        convertedTuples = []
        lastEntry = None
        for entry in entityTuples:
            if type(lastEntry) == type(()) and type(entry) == type(()):
                lastPlainSyllable, lastTone = lastEntry
                plainSyllable, tone = entry
                if plainSyllable.lower() == 'r' \
                    and lastPlainSyllable.lower() not in ['e', 'er', 'r', 'n',
                        'ng', 'hng', 'hm', 'm', u'ê']:
                    # merge two syllables and use tone of main syllable
                    convertedTuples.append((lastPlainSyllable + plainSyllable,
                        lastTone))
                    lastEntry = None
                else:
                    convertedTuples.append(lastEntry)
                    lastEntry = entry
            else:
                if lastEntry != None:
                    convertedTuples.append(lastEntry)
                lastEntry = entry
        if lastEntry != None:
            convertedTuples.append(lastEntry)

        return convertedTuples

    def convertToTwoSyllablesErhua(self, entityTuples):
        """
        Converts the various I{Erhua} forms in a list of reading entities to
        a representation with two syllable, e.g. C{['tour2']} to
        C{['tou2', 'r5']}.

        @type entityTuples: list of tuple/str
        @param entityTuples: list of tuples with plain syllable and tone
        @rtype: list of tuple/str
        @return: list of tuples with plain syllable and tone
        """
        convertedTuples = []
        for entry in entityTuples:
            if type(entry) != type(()):
                convertedTuples.append(entry)
            else:
                plainSyllable, tone = entry
                if plainSyllable[-1:].lower() == 'r' \
                    and plainSyllable.lower() not in ['er', 'r']:
                    # split syllable into plain syllable...
                    convertedTuples.append((plainSyllable[:-1], tone))
                    # ...and single 'r'
                    convertedTuples.append((plainSyllable[-1:], 5))
                else:
                    convertedTuples.append(entry)

        return convertedTuples

    def _checkForErhua(self, entityTuples):
        """
        Checks the given entities for Erhua forms and raises a ConversionError.

        @type entityTuples: list of tuple/str
        @param entityTuples: list of tuples with plain syllable and tone
        @rtype: list of tuple/str
        @return: list of tuples with plain syllable and tone
        @raise ConversionError: when an Erhua form is found
        """
        for entry in entityTuples:
            if type(entry) == type(()):
                plainSyllable, _ = entry

                if plainSyllable.endswith('r') and plainSyllable != 'er':
                    raise ConversionError(
                        "Cannot convert Erhua form in syllable '" \
                            + plainSyllable + "'")

        return entityTuples


class WadeGilesDialectConverter(EntityWiseReadingConverter):
    u"""
    Provides a converter for different representations of the Mandarin Chinese
    romanisation I{Wade-Giles}.

    The converter has very limited possibilities for conversion at this time,
    much more different forms of Wade-Giles are possible and should be
    implemented.
    """
    CONVERSION_DIRECTIONS = [('WadeGiles', 'WadeGiles')]

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone \
            = self._getFromOperator(fromReading).splitEntityTone(entity)

        # convert apostrophe
        if (self._getFromOperator(fromReading)\
            .getOption('WadeGilesApostrophe') \
            != self._getToOperator(toReading).getOption('WadeGilesApostrophe')):
            plainSyllable = plainSyllable.replace(
                self._getFromOperator(fromReading)\
                    .getOption('WadeGilesApostrophe'),
                self._getToOperator(toReading).getOption('WadeGilesApostrophe'))

        # capitalisation
        if self._getToOperator(toReading).getOption('case') == 'lower':
            plainSyllable = plainSyllable.lower()
        elif self._getToOperator(toReading).getOption('case') == 'upper':
            plainSyllable = plainSyllable.upper()

        # get syllable with tone mark
        try:
            return self._getToOperator(toReading).getTonalEntity(plainSyllable,
                tone)
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class PinyinWadeGilesConverter(RomanisationConverter):
    """
    Provides a converter between the Chinese romanisation I{Hanyu Pinyin} and
    I{Wade-Giles}.

    Currently only a non standard subset of Wade-Giles is implemented. As many
    different interpretations exist providing a complete coverage seems hardly
    achievable. An important step is support for the revised system by Giles as
    found in his I{Chinese-English Dictionary} (as of 1912). A further target is
    to at least implement means to support concrete shapes found in the usage of
    big bodies e.g. libraries.

    Upper or lower case will be transfered between syllables, no special
    formatting according to the standards (i.e. Pinyin) will be made. Upper/
    lower case will be identified according to three classes: either the whole
    syllable is upper case, only the initial letter is upper case or otherwise
    the whole syllable is assumed being lower case.

    Conversion cannot in general be done in a one-to-one manner. Standard Pinyin
    has no notion to explicitly specify missing tonal information while this is
    in general given in Wade-Giles by just omitting the tone digits. This
    implementation furthermore doesn't support explicit depiction of I{Erhua} in
    the Wade-Giles romanisation system thus failing when r-colourised syllables
    are found.

    @todo Lang: Increase support for different I{reading dialects} of the
        Wade-Giles romanisation system. Includes support in
        L{WadeGilesOperator}. Get proper sources on the syllables and
        mappings. Use well-known instances.
    @warning: This module isn't backed-up by any sources yet and doesn't
        guarantee a syllable mapping free of errors.
    """
    CONVERSION_DIRECTIONS = [('Pinyin', 'WadeGiles'), ('WadeGiles', 'Pinyin')]
    # use the tone mark type 'Numbers' from Pinyin to support missing tonal
    #   information. Erhua furthermore is not supported.
    DEFAULT_READING_OPTIONS = {'Pinyin': {'Erhua': 'ignore',
        'toneMarkType': 'Numbers'}, 'WadeGiles': {}}

    def convertEntities(self, readingEntities, fromReading, toReading):
        # for conversion from Wade-Giles remove the hyphens that will not be
        #   transfered to Pinyin
        if fromReading == 'WadeGiles':
            readingEntities = self._getFromOperator(fromReading).removeHyphens(
                readingEntities)

        return super(PinyinWadeGilesConverter, self).convertEntities(
            readingEntities, fromReading, toReading)

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone = self.readingFact.splitEntityTone(entity,
            fromReading, **self.DEFAULT_READING_OPTIONS[fromReading])

        # lookup in database
        if fromReading == "WadeGiles":
            table = self.db.tables['WadeGilesPinyinMapping']
            transSyllable = self.db.selectScalar(
                select([table.c.Pinyin], table.c.WadeGiles == plainSyllable))
        elif fromReading == "Pinyin":
            # mapping from WG to Pinyin is ambiguous, use index for distinct
            table = self.db.tables['WadeGilesPinyinMapping']
            transSyllable = self.db.selectScalar(
                select([table.c.WadeGiles],
                    and_(table.c.Pinyin == plainSyllable,
                        table.c.PinyinIdx == 0)))
        if not transSyllable:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' not supported")

        try:
            return self.readingFact.getTonalEntity(transSyllable, tone,
                toReading, **self.DEFAULT_READING_OPTIONS[toReading])
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class GRDialectConverter(ReadingConverter):
    u"""
    Provides a converter for different representations of the Chinese
    romanisation I{Gwoyeu Romatzyh}.
    """
    CONVERSION_DIRECTIONS = [('GR', 'GR')]

    def __init__(self, *args, **options):
        u"""
        Creates an instance of the GRDialectConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        @keyword keepGRApostrophes: if set to C{True} apostrophes separating
            two syllables in Gwoyeu Romatzyh will be kept even if not necessary.
            Apostrophes missing before 0-initials will be added though.
        """
        super(GRDialectConverter, self).__init__(*args, **options)
        # set options
        if 'keepGRApostrophes' in options:
            self.optionValue['keepGRApostrophes'] \
                = options['keepGRApostrophes']

    @classmethod
    def getDefaultOptions(cls):
        options = super(GRDialectConverter, cls).getDefaultOptions()
        options.update({'keepGRApostrophes': False})

        return options

    def convertEntities(self, readingEntities, fromReading='GR',
        toReading='GR'):
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")

        if self.getOption('keepGRApostrophes'):
            # convert separator apostrophe
            fromApostrophe = self._getFromOperator(fromReading)\
                .getOption('GRSyllableSeparatorApostrophe')
            toApostrophe = self._getToOperator(toReading)\
                .getOption('GRSyllableSeparatorApostrophe')
            if fromApostrophe != toApostrophe:
                convertedEntities = []
                for entity in readingEntities:
                    if entity == fromApostrophe:
                        convertedEntities.append(toApostrophe)
                    else:
                        convertedEntities.append(entity)
        else:
            # remove syllable separator
            readingEntities = self._getFromOperator(fromReading)\
                .removeApostrophes(readingEntities)

        # capitalisation
        if self._getToOperator(toReading).getOption('case') == 'lower':
            readingEntities = [entity.lower() for entity in readingEntities]
        elif self._getToOperator(toReading).getOption('case') == 'upper':
            readingEntities = [entity.upper() for entity in readingEntities]

        # convert rhotacised final apostrophe
        fromApostrophe = self._getFromOperator(fromReading)\
            .getOption('GRRhotacisedFinalApostrophe')
        toApostrophe = self._getToOperator(toReading)\
            .getOption('GRRhotacisedFinalApostrophe')
        if fromApostrophe != toApostrophe:
            readingEntities = [entity.replace(fromApostrophe, toApostrophe) \
                for entity in readingEntities]

        # abbreviated forms
        if not self._getToOperator(toReading).getOption('abbreviations'):
            convertedEntities = []
            for entity in readingEntities:
                convertedEntities.append(self._getToOperator(toReading)\
                    .convertAbbreviatedEntity(entity))
            readingEntities = convertedEntities

        return readingEntities


class GRPinyinConverter(RomanisationConverter):
    """
    Provides a converter between the Chinese romanisation I{Gwoyeu Romatzyh} and
    I{Hanyu Pinyin}.

    Features:
        - configurable mapping of options neutral tone when converting from GR,
        - conversion of abbreviated forms of GR.

    Upper or lower case will be transfered between syllables, no special
    formatting according to the standards (i.e. Pinyin) will be made. Upper/
    lower case will be identified according to three classes: either the whole
    syllable is upper case, only the initial letter is upper case or otherwise
    the whole syllable is assumed being lower case.

    Limitations
    ===========
    Conversion cannot in general be done in a one-to-one manner.
    I{Gwoyeu Romatzyh} (GR) gives the etymological tone for a syllable in
    neutral tone while Pinyin doesn't. In contrast to tones in GR carrying more
    information I{r-coloured} syllables (I{Erlhuah}) are rendered the way they
    are pronounced that loosing the original syllable. Converting those forms to
    Pinyin in a general manner is not possible while yielding the original
    string in Chinese characters might help do disambiguate. Another issue
    tone-wise is that Pinyin allows to specify the changed tone when dealing
    with tone sandhis instead of the etymological one while GR doesn't. Only
    working with the Chinese character string might help to restore the original
    tone.

    Conversion from Pinyin is crippled as the neutral tone in this form cannot
    be transfered to GR as described above. More information is needed to
    resolve this. For the other direction the neutral tone can be mapped but the
    etymological tone information is lost. For the optional neutral tone either
    a mapping is done to the neutral tone in Pinyin or to the original
    (etymological).
    """
    CONVERSION_DIRECTIONS = [('GR', 'Pinyin'), ('Pinyin', 'GR')]
    # GR deals with Erlhuah in one syllable, force on Pinyin. Convert GR
    #   abbreviations to full forms
    DEFAULT_READING_OPTIONS = {'Pinyin': {'Erhua': 'oneSyllable'},
        'GR': {'abbreviations': False}}

    def __init__(self, *args, **options):
        """
        Creates an instance of the GRPinyinConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        @keyword GROptionalNeutralToneMapping: if set to 'original' GR syllables
            marked with an optional neutral tone will be mapped to the
            etymological tone, if set to 'neutral' they will be mapped to the
            neutral tone in Pinyin.
        """
        super(GRPinyinConverter, self).__init__(*args, **options)

        if 'GROptionalNeutralToneMapping' in options:
            if options['GROptionalNeutralToneMapping'] not in ['original',
                'neutral']:
                raise ValueError("Invalid option '" \
                    + str(options['GROptionalNeutralToneMapping']) \
                    + "' for keyword 'GROptionalNeutralToneMapping'")
            self.optionValue['GROptionalNeutralToneMapping'] \
                = options['GROptionalNeutralToneMapping']

        # mapping from GR tones to Pinyin
        self.grToneMapping = dict([(tone, int(tone[0])) \
            for tone in operator.GROperator.TONES])
        # set optional neutral mapping
        if self.getOption('GROptionalNeutralToneMapping') == 'neutral':
            for tone in ['1stToneOptional5th', '2ndToneOptional5th',
                '3rdToneOptional5th', '4thToneOptional5th']:
                self.grToneMapping[tone] = 5

        # mapping from Pinyin tones to GR
        self.pyToneMapping = {1: '1stTone', 2: '2ndTone', 3: '3rdTone',
            4: '4thTone', 5: None}

        # GROperator instance
        self.grOperator = None

    @classmethod
    def getDefaultOptions(cls):
        options = super(GRPinyinConverter, cls).getDefaultOptions()
        options.update({'GROptionalNeutralToneMapping': 'original'})

        return options

    def convertBasicEntity(self, entity, fromReading, toReading):
        # we can't convert Erlhuah in GR
        if fromReading == "GR" and entity.endswith('l') \
            and entity not in ['el', 'erl', 'eel', 'ell']:
            raise AmbiguousConversionError("conversion for entity '" + entity \
                + "' is ambiguous")

        # split syllable into plain part and tonal information
        plainSyllable, tone = self.readingFact.splitEntityTone(entity,
            fromReading, **self.DEFAULT_READING_OPTIONS[fromReading])

        # lookup in database
        if fromReading == "GR":
            table = self.db.tables['PinyinGRMapping']
            transSyllable = self.db.selectScalar(select([table.c.Pinyin],
                table.c.GR == plainSyllable))
            transTone = self.grToneMapping[tone]

        elif fromReading == "Pinyin":
            # reduce Erlhuah form
            if plainSyllable != 'er' and plainSyllable.endswith('r'):
                erlhuahForm = True
                plainSyllable = plainSyllable[:-1]
            else:
                erlhuahForm = False

            table = self.db.tables['PinyinGRMapping']
            transSyllable = self.db.selectScalar(select([table.c.GR],
                table.c.Pinyin == plainSyllable))
            if self.pyToneMapping[tone]:
                transTone = self.pyToneMapping[tone]
            else:
                raise AmbiguousConversionError("conversion for entity '" \
                    + plainSyllable + "' with tone '" + str(tone) \
                    + "' is ambiguous")

        if not transSyllable:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' not supported")

        try:
            if toReading == 'GR' and erlhuahForm:
                try:
                    # lookup Erlhuah form for GR
                    return self._getGROperator().getRhotacisedTonalEntity(
                        transSyllable, transTone)
                except UnsupportedError, e:
                    # handle this as a conversion error as the there is no
                    #   Erlhuah form given for the given tone
                    raise ConversionError(e)
            else:
                return self.readingFact.getTonalEntity(transSyllable, transTone,
                    toReading, **self.DEFAULT_READING_OPTIONS[toReading])
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)

    def _getGROperator(self):
        """Creates an instance of a GROperator if needed and returns it."""
        if self.grOperator == None:
            self.grOperator = operator.GROperator(
                **self.DEFAULT_READING_OPTIONS['GR'])
        return self.grOperator


class PinyinIPAConverter(DialectSupportReadingConverter):
    u"""
    Provides a converter between the Mandarin Chinese romanisation
    I{Hanyu Pinyin} and the I{International Phonetic Alphabet} (I{IPA}) for
    Standard Mandarin. This converter provides only basic support for tones and
    the user needs to specify additional means when handling tone sandhi
    occurrences.

    The standard conversion table is based on the source mentioned below.
    Though depiction in IPA depends on many factors and therefore might highly
    vary it seems this source is not error-free: final I{-üan} written [yan]
    should be similar to I{-ian} [iɛn] and I{-iong} written [yŋ] should be
    similar to I{-ong} [uŋ].

    As IPA allows for a big range of different representations for the sounds
    in a varying degree no conversion to Pinyin is offered.

    Currently conversion of I{Erhua sound} is not supported.

    Features:
        - Default tone sandhi handling for lower third tone and neutral tone,
        - extensibility of tone sandhi handling,
        - extensibility for general coarticulation effects.

    Limitations:
        - Tone sandhi needs special treatment depending on the user's needs,
        - transcription of onomatopoeic words will be limited to the general
            syllable scheme,
        - limited linking between syllables (e.g. for 啊、呕) will not be
            considered and
        - stress, intonation and accented speech are not covered.

    Tone sandhi
    ===========
    Speech in tonal languages is generally subject to X{tone sandhi}. For
    example in Mandarin I{bu4 cuo4} for 不错 will render to I{bu2 cuo4}, or
    I{lao3shi1} (老师) with a tone contour of 214 for I{lao3} and 55 for I{shi1}
    will render to a contour 21 for I{lao3}.

    When translating to IPA the system has to deal with these tone sandhis and
    therefore provides an option C{'sandhiFunction'} that can be set to the user
    specified handler. PinyinIPAConverter will only provide a very basic handler
    L{lowThirdAndNeutralToneRule()} which will apply the contour 21 for the
    third tone when several syllables occur and needs the user to supply proper
    tone information, e.g. I{ke2yi3} (可以) instead of the normal rendering as
    I{ke3yi3} to indicate the tone sandhi for the first syllable.

    Further support will be provided for varying stress on syllables in the
    neutral tone. Following a first tone the weak syllable will have a half-low
    pitch, following a second tone a middle, following a third tone a half-high
    and following a forth tone a low pitch.

    There a further occurrences of tone sandhis:
        - pronunciations of 一 and 不 vary in different tones depending on their
            context,
        - directional complements like 拿出来 I{ná chu lai} under some
            circumstances loose their tone,
        - in a three syllable group ABC the second syllable B changes from
            second tone to first tone when A is in the first or second tone and
            C is not in the neutral tone.

    Coarticulation
    ==============
    In most cases conversion from Pinyin to IPA is straightforward if one does
    not take tone sandhi into account. There are case though (when leaving
    aside tones), where phonetic realisation of a syllable depends on its
    context. The converter allows for handling coarticulation effects by
    adding a hook C{coarticulationFunction} to which a user-implemented
    function can be given. An example implementation is given with
    L{finalECoarticulation()}.

    Source
    ======
    - Hànyǔ Pǔtōnghuà Yǔyīn Biànzhèng (汉语普通话语音辨正). Page 15, Běijīng Yǔyán
        Dàxué Chūbǎnshè (北京语言大学出版社), 2003, ISBN 7-5619-0622-6.
    - San Duanmu: The Phonology of Standard Chinese. Second edition, Oxford
        University Press, 2007, ISBN 978-0-19-921578-2, ISBN 978-0-19-921579-9.
    - Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
        Press, Berkeley, 1968, ISBN 0-520-00219-9.

    @see:
        - Mandarin tone sandhi:
            U{http://web.mit.edu/jinzhang/www/pinyin/tones/index.html}
        - IPA: U{http://en.wikipedia.org/wiki/International_Phonetic_Alphabet}
        - The Phonology of Standard Chinese. First edition, 2000:
            U{http://books.google.de/books?id=tG0-Ad9CrBcC}

    @todo Impl: Two different methods for tone sandhi and coarticulation
        effects?
    @todo Lang: Support for I{Erhua} in mapping.
    """
    CONVERSION_DIRECTIONS = [('Pinyin', 'MandarinIPA')]

    DEFAULT_READING_OPTIONS = {'Pinyin': {'Erhua': 'ignore',
        'toneMarkType': 'Numbers', 'missingToneMark': 'noinfo',
        'case': 'lower'}}
    # TODO once we support Erhua, use oneSyllable form to lookup

    TONEMARK_MAPPING = {1: '1stTone', 2: '2ndTone', 3: '3rdToneRegular',
        4: '4thTone', 5: '5thTone'}

    NEUTRAL_TONE_MAPPING = {'1stTone': '5thToneHalfLow',
        '2ndTone': '5thToneMiddle', '3rdToneRegular': '5thToneHalfHigh',
        '3rdToneLow': '5thToneHalfHigh', '4thTone': '5thToneLow',
        '5thTone': '5thTone', '5thToneHalfHigh': '5thToneHalfHigh',
        '5thToneMiddle': '5thToneMiddle', '5thToneHalfLow':'5thToneHalfLow',
        '5thToneLow': '5thToneLow'}
    """Mapping of neutral tone following another tone."""

    def __init__(self, *args, **options):
        """
        Creates an instance of the PinyinIPAConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        @keyword sandhiFunction: a function that handles tonal changes
            and converts a given list of entities to accommodate sandhi
            occurrences, see L{lowThirdAndNeutralToneRule()} for the default
            implementation.
        @keyword coarticulationFunction: a function that handles coarticulation
            effects, see L{finalECoarticulation()} for an example
            implementation.
        """
        super(PinyinIPAConverter, self).__init__(*args, **options)

        # set the sandhiFunction for handling tonal changes
        if 'sandhiFunction' in options:
            self.optionValue['sandhiFunction'] = options['sandhiFunction']
        # set the sandhiFunction for handling general phonological changes
        if 'coarticulationFunction' in options:
            self.optionValue['coarticulationFunction'] \
                = options['coarticulationFunction']

    @classmethod
    def getDefaultOptions(cls):
        options = super(PinyinIPAConverter, cls).getDefaultOptions()
        options.update({'coarticulationFunction': None, 
            'sandhiFunction': PinyinIPAConverter.lowThirdAndNeutralToneRule})

        return options

    def convertEntitySequence(self, entitySequence, fromReading, toReading):
        toEntitySequence = []
        for sequence in entitySequence:
            if type(sequence) == type([]):
                ipaTupelList = []
                for idx, entity in enumerate(sequence):
                    # split syllable into plain part and tonal information
                    plainSyllable, tone = self.readingFact.splitEntityTone(
                        entity, fromReading,
                        **self.DEFAULT_READING_OPTIONS[fromReading])

                    transEntry = None
                    if self.getOption('coarticulationFunction'):
                        transEntry = self.getOption('coarticulationFunction')\
                            (self, sequence[:i], plainSyllable, tone,
                                sequence[i+1:])

                    if not transEntry:
                        # standard conversion
                        transEntry = self._convertSyllable(plainSyllable, tone)

                    ipaTupelList.append(transEntry)

                # handle sandhi
                if self._getToOperator(toReading).getOption('toneMarkType') \
                    != 'None':
                    sandhiFunction = self.getOption('sandhiFunction')
                    ipaTupelList = sandhiFunction(self, ipaTupelList)

                # get tonal forms
                toSequence = []
                for plainSyllable, tone in ipaTupelList:
                    entity = self._getToOperator(toReading).getTonalEntity(
                        plainSyllable, tone)
                    toSequence.append(entity)

                toEntitySequence.append(toSequence)
            else:
                toEntitySequence.append(sequence)

        return toEntitySequence

    def _convertSyllable(self, plainSyllable, tone):
        """
        Converts a single syllable from Pinyin to IPA.

        @type plainSyllable: str
        @param plainSyllable: plain syllable in the source reading
        @type tone: int
        @param tone: the syllable's tone
        @rtype: str
        @return: IPA representation
        """
        # lookup in database
        table = self.db.tables['PinyinIPAMapping']
        transSyllables = self.db.selectScalars(select([table.c.IPA],
            and_(table.c.Pinyin == plainSyllable,
                table.c.Feature.in_(['', 'Default']))))

        if not transSyllables:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' not supported")
        elif len(transSyllables) != 1:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' ambiguous")
        if tone:
            transTone = self.TONEMARK_MAPPING[tone]
        else:
            transTone = None

        return transSyllables[0], transTone

    def lowThirdAndNeutralToneRule(self, entityTuples):
        """
        Converts C{'3rdToneRegular'} to C{'3rdToneLow'} for syllables followed
        by others and C{'5thTone'} to the respective forms when following
        another syllable.

        This function serves as the default rule and can be overwritten by
        giving a function as option C{sandhiFunction} on instantiation.

        @type entityTuples: list of tuple/str
        @param entityTuples: a list of tuples and strings. An IPA entity is
            given as a tuple with the plain syllable and its tone, other content
            is given as plain string.
        @rtype: list
        @return: converted entity list
        @todo Lang: What to do on several following neutral tones?
        """
        # only convert 3rd tone to lower form when multiple syllables occur
        if len(entityTuples) <= 1:
            return entityTuples

        # convert
        convertedEntities = []
        precedingTone = None
        for idx, entry in enumerate(entityTuples):
            if type(entry) == type(()):
                plainSyllable, tone = entry

                if tone == '5thTone' and precedingTone:
                    tone = self.NEUTRAL_TONE_MAPPING[precedingTone]
                elif tone == '3rdToneRegular' and idx + 1 != len(entityTuples):
                    tone = '3rdToneLow'
                entry = (plainSyllable, tone)

                precedingTone = tone
            else:
                precedingTone = None

            convertedEntities.append(entry)

        return convertedEntities

    def finalECoarticulation(self, leftContext, plainSyllable, tone,
        rightContext):
        u"""
        Example function for handling coarticulation of final I{e} for the
        neutral tone.

        Only syllables with final I{e} are considered for other syllables
        C{None} is returned. This will trigger the regular conversion method.

        Pronunciation of final I{e}
        ===========================
        The final I{e} found in syllables I{de}, I{me} and others is
        pronounced /ɤ/ in the general case (see source below) but if tonal
        stress is missing it will be pronounced /ə/. This implementation will
        take care of this for the fifth tone. If no tone is specified
        (C{'None'}) an L{ConversionError} will be raised for the syllables
        affected.

        Source: Hànyǔ Pǔtōnghuà Yǔyīn Biànzhèng (汉语普通话语音辨正). Page 15,
        Běijīng Yǔyán Dàxué Chūbǎnshè (北京语言大学出版社), 2003,
        ISBN 7-5619-0622-6.

        @type leftContext: list of tuple/str
        @param leftContext: syllables preceding the syllable in question in the
            source reading
        @type plainSyllable: str
        @param plainSyllable: plain syllable in the source reading
        @type tone: int
        @param tone: the syllable's tone
        @type rightContext: list of tuple/str
        @param rightContext: syllables following the syllable in question in the
            source reading
        @rtype: str
        @return: IPA representation
        """
        if tone == 5:
            _, final = self._getToOperator('Pinyin').getOnsetRhyme(
                plainSyllable)
            if final == 'e':
                # lookup in database
                table = self.db.tables['PinyinIPAMapping']
                transSyllable = self.db.selectScalars(select([table.c.IPA],
                    and_(table.c.Pinyin == plainSyllable,
                        table.c.Feature == '5thTone')))
                if not transSyllables:
                    raise ConversionError("conversion for entity '" \
                        + plainSyllable + "' not supported")
                elif len(transSyllables) != 1:
                    raise ConversionError("conversion for entity '" \
                        + plainSyllable + "' and tone '" + str(tone) \
                        + "' ambiguous")

                return transSyllables[0], self.TONEMARK_MAPPING[tone]


class PinyinBrailleConverter(DialectSupportReadingConverter):
    u"""
    PinyinBrailleConverter defines a converter between the Mandarin Chinese
    romanisation I{Hanyu Pinyin} and the I{Braille} system for Mandarin Chinese.

    Conversion from Braille to Pinyin is ambiguous. The syllable pairs mo/me,
    e/o and le/lo will yield an L{AmbiguousConversionError}. Furthermore
    conversion from Pinyin to Braille is lossy if tones are omitted, which seems
    to be frequent in writing Braille for Chinese. Braille doesn't mark the
    fifth tone, so converting back to Pinyin will give syllables without a tone
    mark the fifth tone, changing originally unknown ones. See
    L{MandarinBrailleOperator}.

    Examples
    ========
    Convert from Pinyin to Braille using the L{ReadingFactory}:

        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert(u'Qǐng nǐ děng yīxià!', 'Pinyin', 'MandarinBraille',
        ...     targetOptions={'toneMarkType': 'None'})
        u'\u2805\u2821 \u281d\u280a \u2819\u283c \u280a\u2813\u282b\u2830\u2802'

    @see:
        - How is Chinese written in Braille?:
            U{http://www.braille.ch/pschin-e.htm}
        - Chinese Braille: U{http://en.wikipedia.org/wiki/Chinese_braille}
    """
    CONVERSION_DIRECTIONS = [('Pinyin', 'MandarinBraille'),
        ('MandarinBraille', 'Pinyin')]

    DEFAULT_READING_OPTIONS = {'Pinyin': {'Erhua': 'ignore',
        'toneMarkType': 'Numbers', 'missingToneMark': 'noinfo'}}

    PUNCTUATION_SIGNS_MAPPING = {u'。': u'⠐⠆', u',': u'⠐', u'?': u'⠐⠄',
        u'!': u'⠰⠂', u':': u'⠒', u';': u'⠰', u'-': u'⠠⠤', u'…': u'⠐⠐⠐',
        u'·': u'⠠⠄', u'(': u'⠰⠄', u')': u'⠠⠆', u'[': u'⠰⠆', u']': u'⠰⠆'}

    def __init__(self, *args, **options):
        """
        Creates an instance of the PinyinBrailleConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        """
        super(PinyinBrailleConverter, self).__init__(*args, **options)
        # get mappings
        self._createMappings()

        # punctuation mapping
        self.reversePunctuationMapping = {}
        for key in self.PUNCTUATION_SIGNS_MAPPING:
            if key in self.reversePunctuationMapping:
                # ambiguous mapping, so remove
                self.reversePunctuationMapping[key] = None
            else:
                value = self.PUNCTUATION_SIGNS_MAPPING[key]
                self.reversePunctuationMapping[value] = key

        # regex to split out punctuation
        self.pinyinPunctuationRegex = re.compile(ur'(' \
            + '|'.join([re.escape(p) for p \
                in self.PUNCTUATION_SIGNS_MAPPING.keys()]) \
            + '|.+?)')

        braillePunctuation = list(set(self.PUNCTUATION_SIGNS_MAPPING.values()))
        # longer marks first in regex
        braillePunctuation.sort(lambda x,y: len(y) - len(x))
        self.braillePunctuationRegex = re.compile(ur'(' \
            + '|'.join([re.escape(p) for p in braillePunctuation]) + '|.+?)')

    def _createMappings(self):
        """
        Creates the mappings of syllable initials and finals from the database.
        """
        # initials
        self.pinyinInitial2Braille = {}
        self.braille2PinyinInitial = {}

        table = self.db.tables['PinyinBrailleInitialMapping']
        entries = self.db.selectRows(
            select([table.c.PinyinInitial, table.c.Braille]))

        for pinyinInitial, brailleChar in entries:
            # Pinyin 2 Braille
            if pinyinInitial in self.pinyinInitial2Braille:
                raise ValueError(
                    "Ambiguous mapping from Pinyin syllable initial to Braille")
            self.pinyinInitial2Braille[pinyinInitial] = brailleChar
            # Braille 2 Pinyin
            if brailleChar not in self.braille2PinyinInitial:
                self.braille2PinyinInitial[brailleChar] = set()
            self.braille2PinyinInitial[brailleChar].add(pinyinInitial)

        self.pinyinInitial2Braille[''] = ''
        self.braille2PinyinInitial[''] = set([''])

        # finals
        self.pinyinFinal2Braille = {}
        self.braille2PinyinFinal = {}

        table = self.db.tables['PinyinBrailleFinalMapping']
        entries = self.db.selectRows(
            select([table.c.PinyinFinal, table.c.Braille]))

        for pinyinFinal, brailleChar in entries:
            # Pinyin 2 Braille
            if pinyinFinal in self.pinyinFinal2Braille:
                raise ValueError(
                    "Ambiguous mapping from Pinyin syllable final to Braille")
            self.pinyinFinal2Braille[pinyinFinal] = brailleChar
            # Braille 2 Pinyin
            if brailleChar not in self.braille2PinyinFinal:
                self.braille2PinyinFinal[brailleChar] = set()
            self.braille2PinyinFinal[brailleChar].add(pinyinFinal)

        # map ê to same Braille character as e
        self.pinyinFinal2Braille[u'ê'] = self.pinyinFinal2Braille[u'e']

    def convertEntitySequence(self, entitySequence, fromReading, toReading):
        toReadingEntities = []
        if fromReading == "Pinyin":
            for sequence in entitySequence:
                if type(sequence) == type([]):
                    for entity in sequence:
                        toReadingEntity = self.convertBasicEntity(entity,
                            fromReading, toReading)
                        toReadingEntities.append(toReadingEntity)
                else:
                    # find punctuation marks
                    for subEntity in self.pinyinPunctuationRegex.findall(
                        sequence):
                        if subEntity in self.PUNCTUATION_SIGNS_MAPPING:
                            toReadingEntities.append(
                                self.PUNCTUATION_SIGNS_MAPPING[subEntity])
                        else:
                            toReadingEntities.append(subEntity)
        elif fromReading == "MandarinBraille":
            for sequence in entitySequence:
                if type(sequence) == type([]):
                    for entity in sequence:
                        toReadingEntity = self.convertBasicEntity(
                            entity.lower(), fromReading, toReading)
                        toReadingEntities.append(toReadingEntity)
                else:
                    # find punctuation marks
                    for subEntity in self.braillePunctuationRegex.findall(
                        sequence):
                        if subEntity in self.reversePunctuationMapping:
                            if not self.reversePunctuationMapping[subEntity]:
                                raise AmbiguousConversionError(
                                    "conversion for entity '" + subEntity \
                                        + "' is ambiguous")
                            toReadingEntities.append(
                                self.reversePunctuationMapping[subEntity])
                        else:
                            toReadingEntities.append(subEntity)

        return toReadingEntities

    def convertBasicEntity(self, entity, fromReading, toReading):
        """
        Converts a basic entity (a syllable) in the source reading to the given
        target reading.

        This method is called by L{convertEntities()} and a single entity
        is given for conversion.

        If a single entity needs to be converted it is recommended to use
        L{convertEntities()} instead. In the general case it can not be ensured
        that a mapping from one reading to another can be done by the simple
        conversion of a basic entity. One-to-many mappings are possible and
        there is no guarantee that any entity of a reading recognised by
        L{operator.ReadingOperator.isReadingEntity()} will be mapped here.

        @type entity: str
        @param entity: string written in the source reading in lower case
            letters
        @type fromReading: str
        @param fromReading: name of the source reading
        @type toReading: str
        @param toReading: name of the target reading, different from the source
            reading
        @rtype: str
        @returns: the entity converted to the C{toReading} in lower case
        @raise AmbiguousConversionError: if conversion for this entity of the
            source reading is ambiguous.
        @raise ConversionError: on other operations specific to the conversion
            of the entity.
        @raise InvalidEntityError: if the entity is invalid.
        """
        # split entity into plain part and tonal information
        if fromReading in self.DEFAULT_READING_OPTIONS:
            fromOptions = self.DEFAULT_READING_OPTIONS[fromReading]
        else:
            fromOptions = {}
        fromOperator = self.readingFact._getReadingOperatorInstance(fromReading,
            **fromOptions)

        plainEntity, tone = fromOperator.splitEntityTone(entity)
        # lookup in database
        if fromReading == "Pinyin":
            initial, final = fromOperator.getOnsetRhyme(plainEntity)

            if plainEntity not in ['zi', 'ci', 'si', 'zhi', 'chi', 'shi', 'ri']:
                try:
                    transSyllable = self.pinyinInitial2Braille[initial] \
                        + self.pinyinFinal2Braille[final]
                except KeyError:
                    raise ConversionError("conversion for entity '" \
                        + plainEntity + "' not supported")
            else:
                try:
                    transSyllable = self.pinyinInitial2Braille[initial]
                except KeyError:
                    raise ConversionError("conversion for entity '" \
                        + plainEntity + "' not supported")
        elif fromReading == "MandarinBraille":
            # mapping from Braille to Pinyin is ambiguous
            initial, final = fromOperator.getOnsetRhyme(plainEntity)

            # get all possible forms
            forms = []
            for i in self.braille2PinyinInitial[initial]:
                for f in self.braille2PinyinFinal[final]:
                    # get Pinyin syllable
                    table = self.db.tables['PinyinInitialFinal']
                    entry = self.db.selectScalar(
                        select([table.c.Pinyin],
                            and_(table.c.PinyinInitial == i,
                                table.c.PinyinFinal == f)))
                    if entry:
                        forms.append(entry)

            # narrow down to possible ones
            if len(forms) > 1:
                for form in forms[:]:
                    if not self._getToOperator(toReading).isPlainReadingEntity(
                        form):
                        forms.remove(form)
            if not forms:
                raise ConversionError("conversion for entity '" \
                    + plainEntity + "' not supported")
            if len(forms) > 1:
                raise AmbiguousConversionError("conversion for entity '" \
                    + plainEntity + "' is ambiguous")
            else:
                transSyllable = forms[0]

        try:
            return self._getToOperator(toReading).getTonalEntity(transSyllable,
                tone)
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class JyutpingDialectConverter(EntityWiseReadingConverter):
    u"""
    Provides a converter for different representations of the Cantonese
    romanisation I{Jyutping}.
    """
    CONVERSION_DIRECTIONS = [('Jyutping', 'Jyutping')]

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone \
            = self._getFromOperator(fromReading).splitEntityTone(entity)

        # capitalisation
        if self._getToOperator(toReading).getOption('case') == 'lower':
            plainSyllable = plainSyllable.lower()
        elif self._getToOperator(toReading).getOption('case') == 'upper':
            plainSyllable = plainSyllable.upper()

        # get syllable with tone mark
        try:
            return self._getToOperator(toReading).getTonalEntity(plainSyllable,
                tone)
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class CantoneseYaleDialectConverter(EntityWiseReadingConverter):
    u"""
    Provides a converter for different representations of the I{Cantonese Yale}
    romanisation system.

    High Level vs. High Falling Tone
    ================================
    As described in L{CantoneseYaleOperator} the abbreviated form of the
    Cantonese Yale romanisation system which uses numbers as tone marks makes no
    distinction between the high level tone and the high falling tone. On
    conversion to the form with diacritical marks it is thus important to choose
    the correct mapping. This can be configured by applying a special instance
    of a L{CantoneseYaleOperator} (or telling the L{ReadingFactory} which
    operator to use).

    Example:

        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert(u'gwong2jau1wa2', 'CantoneseYale', 'CantoneseYale',
        ...     sourceOptions={'toneMarkType': 'Numbers',
        ...         'YaleFirstTone': '1stToneFalling'})
        u'gw\xf3ngj\xe0uw\xe1'
    """
    CONVERSION_DIRECTIONS = [('CantoneseYale', 'CantoneseYale')]

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone \
            = self._getFromOperator(fromReading).splitEntityTone(entity)

        # capitalisation
        if self._getToOperator(toReading).getOption('case') == 'lower':
            plainSyllable = plainSyllable.lower()
        elif self._getToOperator(toReading).getOption('case') == 'upper':
            plainSyllable = plainSyllable.upper()

        # get syllable with tone mark
        try:
            return self._getToOperator(toReading).getTonalEntity(plainSyllable,
                tone)
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class JyutpingYaleConverter(RomanisationConverter):
    u"""
    Provides a converter between the Cantonese romanisation systems I{Jyutping}
    and I{Cantonese Yale}.

    Upper or lower case will be transfered between syllables, no special
    formatting according to the standards will be made. Upper/lower case will be
    identified according to three classes: either the whole syllable is upper
    case, only the initial letter is upper case or otherwise the whole syllable
    is assumed being lower case.

    High Level vs. High Falling Tone
    ================================
    As described in L{CantoneseYaleOperator} the Cantonese Yale romanisation
    system makes a distinction between the high level tone and the high falling
    tone in general while Jyutping does not. On conversion it is thus important
    to choose the correct mapping. This can be configured by applying the option
    C{YaleFirstTone} when construction the converter (or telling the
    L{ReadingFactory} which converter to use).

    Example:

        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert(u'gwong2zau1waa2', 'Jyutping', 'CantoneseYale',
        ...     YaleFirstTone='1stToneFalling')
        u'gw\xf3ngj\xe0uw\xe1'
    """
    CONVERSION_DIRECTIONS = [('Jyutping', 'CantoneseYale'),
        ('CantoneseYale', 'Jyutping')]
    # use special dialect for Yale to retain information for first tone and
    #   missing tones
    DEFAULT_READING_OPTIONS = {'Jyutping': {},
        'CantoneseYale': {'toneMarkType': 'Internal'}}

    DEFAULT_TONE_MAPPING = {1: '1stToneLevel', 2: '2ndTone', 3: '3rdTone',
        4: '4thTone', 5: '5thTone', 6: '6thTone'}
    """
    Mapping of Jyutping tones to Yale tones. Tone 1 can be changed via option
    'YaleFirstTone'.
    """

    def __init__(self, *args, **options):
        """
        Creates an instance of the JyutpingYaleConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        @keyword YaleFirstTone: tone in Yale which the first tone from Jyutping
            should be mapped to. Value can be C{'1stToneLevel'} to map to the
            level tone with contour 55 or C{'1stToneFalling'} to map to the
            falling tone with contour 53. This is only important if the target
            reading dialect uses diacritical tone marks.
        """
        super(JyutpingYaleConverter, self).__init__(*args, **options)

        # set the YaleFirstTone for handling ambiguous conversion of first
        #   tone in Cantonese that has two different representations in Yale,
        #   but only one in Jyutping
        if 'YaleFirstTone' in options:
            if options['YaleFirstTone'] not in ['1stToneLevel',
                '1stToneFalling']:
                raise ValueError("Invalid option '" \
                    + unicode(options['YaleFirstTone']) \
                    + "' for keyword 'YaleFirstTone'")
            self.optionValue['YaleFirstTone'] = options['YaleFirstTone']

        self.optionValue['defaultToneMapping'][1] \
            = self.optionValue['YaleFirstTone']

    @classmethod
    def getDefaultOptions(cls):
        options = super(JyutpingYaleConverter, cls).getDefaultOptions()
        options.update({'YaleFirstTone': '1stToneLevel',
            'defaultToneMapping': cls.DEFAULT_TONE_MAPPING})

        return options

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone = self.readingFact.splitEntityTone(entity,
            fromReading, **self.DEFAULT_READING_OPTIONS[fromReading])

        # lookup in database
        if fromReading == "CantoneseYale":
            table = self.db.tables['JyutpingYaleMapping']
            transSyllable = self.db.selectScalar(
                select([table.c.Jyutping],
                    table.c.CantoneseYale == plainSyllable))
            # get tone
            if tone:
                # get tone number from first character of string representation
                transTone = int(tone[0])
            else:
                transTone = None
        elif fromReading == "Jyutping":
            table = self.db.tables['JyutpingYaleMapping']
            transSyllable = self.db.selectScalar(
                select([table.c.CantoneseYale],
                    table.c.Jyutping == plainSyllable))
            # get tone
            if not tone:
                transTone = None
            else:
                transTone = self.optionValue['defaultToneMapping'][tone]

        if not transSyllable:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' not supported")
        try:
            return self.readingFact.getTonalEntity(transSyllable, transTone,
                toReading, **self.DEFAULT_READING_OPTIONS[toReading])
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class BridgeConverter(ReadingConverter):
    """
    Provides a L{ReadingConverter} that converts between readings over a third
    reading called bridge reading.
    """
    def _getConversionDirections(bridge):
        """
        Extracts all conversion directions implicitly stored in the bridge
        definition.

        @type bridge: list of tuple
        @param bridge: 3-tuples indicating conversion direction over a third
            reading (bridge)
        @rtype: list of tuple
        @return: conversion directions
        """
        dirSet = set()
        for fromReading, bridgeReading, toReading in bridge:
            dirSet.add((fromReading, toReading))
        return list(dirSet)

    CONVERSION_BRIDGE = [('WadeGiles', 'Pinyin', 'MandarinIPA'),
        ('MandarinBraille', 'Pinyin', 'MandarinIPA'),
        ('WadeGiles', 'Pinyin', 'MandarinBraille'),
        ('MandarinBraille', 'Pinyin', 'WadeGiles'),
        ('GR', 'Pinyin', 'WadeGiles'), ('MandarinBraille', 'Pinyin', 'GR'),
        ('WadeGiles', 'Pinyin', 'GR'), ('GR', 'Pinyin', 'MandarinBraille'),
        ('GR', 'Pinyin', 'MandarinIPA'), # TODO remove once there is a proper
                                         #   converter for GR to IPA
        ]
    """
    List containing all conversion directions together with the bridge reading
    over which the conversion is made.
    Form: (fromReading, bridgeReading, toReading)
    As conversion may be lossy it is important which conversion path is chosen.
    """

    CONVERSION_DIRECTIONS = _getConversionDirections(CONVERSION_BRIDGE)

    def __init__(self, *args, **options):
        """
        Creates an instance of the BridgeConverter.

        @param args: optional list of L{RomanisationOperator}s to use for
            handling source and target readings.
        @param options: extra options passed to the L{ReadingConverter}s
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword sourceOperators: list of L{ReadingOperator}s used for handling
            source readings.
        @keyword targetOperators: list of L{ReadingOperator}s used for handling
            target readings.
        """
        super(BridgeConverter, self).__init__(*args, **options)

        self.bridgeLookup = {}
        for fromReading, bridgeReading, toReading in self.CONVERSION_BRIDGE:
            self.bridgeLookup[(fromReading, toReading)] = bridgeReading

    def convertEntities(self, readingEntities, fromReading, toReading):
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")
        bridgeReading = self.bridgeLookup[(fromReading, toReading)]

        # to bridge reading
        bridgeReadingEntities = self.readingFact.convertEntities(
            readingEntities, fromReading, bridgeReading,
            sourceOperators=[self._getFromOperator(fromReading)])

        # from bridge reading
        toReadingEntities = self.readingFact.convertEntities(
            bridgeReadingEntities, bridgeReading, toReading,
            targetOperators=[self._getToOperator(toReading)])
        return toReadingEntities
