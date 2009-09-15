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
    ...     sourceOptions={'toneMarkType': 'numbers'},
    ...     targetOptions={'toneMarkType': 'superscriptNumbers'})
    u'kuo\xb3-y\xfc\xb2'

See L{PinyinDialectConverter} for more examples.
"""

# pylint: disable-msg=E1101
#  member variables are set by setattr()

import re
import copy
import types

from sqlalchemy import select
from sqlalchemy.sql import and_

from cjklib.exception import (ConversionError, AmbiguousConversionError,
    InvalidEntityError, UnsupportedError)
from cjklib.dbconnector import DatabaseConnector
from cjklib.reading import operator as readingoperator
import cjklib.reading
from cjklib.util import titlecase, istitlecase

class ReadingConverter(object):
    u"""
    Defines an abstract converter between two or more I{character reading}s.

    The basic method is L{convert()} which converts one input string from one
    reading to another.

    The method L{getDefaultOptions()} will return the conversion default
    settings.

    The class itself can't be used directly, it has to be subclassed and its
    methods need to be extended.

    What gets converted
    ===================
    The conversion process uses the L{ReadingOperator} for the source reading to
    decompose the given string into the single entities. The decomposition
    contains reading entities and entities that don't represent any
    pronunciation. While the goal is to convert included reading entities to the
    target reading, some convertes might decide to also convert non-reading
    entities. This can be for example delimiters like apostrophes that differ
    between romanisations or punctuation marks that have a defined
    representation in the target system, e.g. Braille.

    Errors
    ------
    By default conversion won't stop on entities that closely resemble other
    reading entities but itself are not valid. Those will turn up unchanged in
    the result and can cause a L{CompositionError} when the target operator
    decideds that it is impossible to link a converted entity with a
    non-converted one as it would make it impossible to later determine the
    entity boundaries. Most of those errors will probably result from bad input
    that fails on conversion. This can be solved by telling the source operator
    to be strict on decomposition (where supported) so that the error will
    be reported beforehand. The followig example tries to convert I{xiǎo tōu}
    ("thief"), misspelled as I{*xiǎo tō}:

        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> print f.convert(u'xiao3to1', 'Pinyin', 'GR',
        ...     sourceOptions={'toneMarkType': 'numbers'})
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        ...
        cjklib.exception.CompositionError: Unable to delimit non-reading entity\
 'to1'
        >>> print f.convert(u'xiao3to1', 'Pinyin', 'GR',
        ...     sourceOptions={'toneMarkType': 'numbers',
        ...         'strictSegmentation': True})
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        ...
        cjklib.exception.DecompositionError: Segmentation of 'to1' not possible\
 or invalid syllable

    Not being strict results in a lazy conversion, which might fail in some
    cases as shown above. C{u'xiao3 to1'} (with a space in between) though will
    work for the lazy way (C{'to1'} not being converted), while the strict
    version will still report the wrong I{*to1}.

    Other errors that can arise:
        - L{AmbiguousDecompositionError}, if the source string can not be
            decomposed unambigiuously,
        - L{ConversionError}, e.g. if the target system doesn't support a
            feature given in the source string, and
        - L{AmbiguousConversionError}, if a given entity can be mapped to more
            than one entity in the target reading.
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

        self._f = cjklib.reading.ReadingFactory(dbConnectInst=self.db)

        for option, defaultValue in self.getDefaultOptions().items():
            optionValue = options.get(option, defaultValue)
            if option not in ['sourceOperators', 'targetOperators'] \
                and not hasattr(optionValue, '__call__'):
                setattr(self, option, copy.deepcopy(optionValue))
            else:
                setattr(self, option, optionValue)

        if type(self.sourceOperators) != type({}):
            self.sourceOperators \
                = dict([(operatorInst.READING_NAME, operatorInst) \
                    for operatorInst in self.sourceOperators])
        if type(self.targetOperators) != type({}):
            self.targetOperators \
                = dict([(operatorInst.READING_NAME, operatorInst) \
                    for operatorInst in self.targetOperators])

        for operatorInst in self.sourceOperators.values():
            if not isinstance(operatorInst, readingoperator.ReadingOperator):
                raise ValueError(
                    "Unknown type '%s' given as source reading operator"
                        % str(type(operatorInst)))
        for operatorInst in self.targetOperators.values():
            if not isinstance(operatorInst, readingoperator.ReadingOperator):
                raise ValueError(
                    "Unknown type '%s' given as target reading operator"
                        % str(type(operatorInst)))

        # get reading operators from args
        for arg in args:
            if isinstance(arg, readingoperator.ReadingOperator):
                # store reading operator for the given reading
                if arg.READING_NAME in self.sourceOperators \
                    or arg.READING_NAME in self.targetOperators:
                    raise ValueError("Operator for '%s'" \
                            % arg.READING_NAME
                        + " specified twice as plain and keyword argument")
                self.sourceOperators[arg.READING_NAME] = arg
                self.targetOperators[arg.READING_NAME] = arg
            else:
                raise ValueError("Unknown type '%s' given as reading operator"
                    % str(type(arg)))

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
        @raise CompositionError: if the target reading's entities can not be
            composed.
        @raise ConversionError: on operations specific to the conversion between
            the two readings (e.g. error on converting entities).
        @raise UnsupportedError: if source or target reading is not supported
            for conversion.
        @todo Impl: Make parameters fromReading, toReading optional if only
            one conversion direction is given. Same for L{convertEntities()}.
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
        if readingN not in self.sourceOperators:
            self.sourceOperators[readingN] \
                = self._f._getReadingOperatorInstance(readingN)
        return self.sourceOperators[readingN]

    def _getToOperator(self, readingN):
        """
        Gets a reading operator instance for conversion to the given reading.

        @type readingN: str
        @param readingN: name of reading
        @rtype: instance
        @return: a L{ReadingOperator} instance
        @raise UnsupportedError: if the given reading is not supported.
        """
        if readingN not in self.targetOperators:
            self.targetOperators[readingN] \
                = self._f._getReadingOperatorInstance(readingN)
        return self.targetOperators[readingN]


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

            if self._getFromOperator(fromReading).isReadingEntity(entity) \
                or self._getFromOperator(fromReading).isFormattingEntity(
                    entity):
                # add reading entity to preceding ones
                readingEntitySequence.append(entity)
                entitySequence.append(readingEntitySequence)
            else:
                if readingEntitySequence:
                    entitySequence.append(readingEntitySequence)
                # append non-reading entity
                entitySequence.append(entity)

        # convert to standard form if supported (step 1)
        if self._f.isReadingConversionSupported(fromReading, fromReading):
            # get default options if available used for converting the reading
            #   dialect
            if fromReading in self.DEFAULT_READING_OPTIONS:
                fromDefaultOptions = self.DEFAULT_READING_OPTIONS[fromReading]
            else:
                fromDefaultOptions = {}
            # use user specified source operator, set target to default form
            converter = self._f._getReadingConverterInstance(fromReading,
                fromReading,
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
        if self._f.isReadingConversionSupported(toReading, toReading):
            # get default options if available used for converting the reading
            #   dialect
            if toReading in self.DEFAULT_READING_OPTIONS:
                toDefaultOptions = self.DEFAULT_READING_OPTIONS[toReading]
            else:
                toDefaultOptions = {}
            # use user specified target operator, set source to default form
            converter = self._f._getReadingConverterInstance(toReading,
                toReading, sourceOptions=toDefaultOptions,
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
    u"""
    Defines an abstract L{ReadingConverter} between two or more
    I{romanisation}s.

    Reading dialects can produce different entities which have to be handled by
    the conversion process. This is realised by converting the given reading
    dialect to a default form, then converting to the default target reading and
    finally converting to the specified target reading dialect. On conversion
    step thus involves three single conversion steps using a default form. This
    default form can be defined in L{DEFAULT_READING_OPTIONS}.

    Letter case will be transfered between syllables, no special formatting
    according to anyhow defined standards will be guaranteed.
    Letter case will be identified according to three classes: uppercase (all
    case-sensible characters are uppercase), titlecase (all case-sensible
    characters are lowercase except the first case-sensible character),
    lowercase (all case-sensible characters are lowercase). For entities of
    single latin characters uppercase has precedence over titlecase, e.g. I{E5}
    will convert to I{ÉH} in Cantonese Yale, not to I{Éh}. In general letter
    case should be handled outside of cjklib if special formatting is required.

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
                    if self._f.isReadingEntity(entity, fromReading,
                        **self.DEFAULT_READING_OPTIONS[fromReading]):
                        toReadingEntity = self.convertBasicEntity(
                            entity.lower(), fromReading, toReading)

                        # transfer letter case, target reading dialect will take
                        #   care of final transformation (lower/both)
                        if entity.isupper():
                            toReadingEntity = toReadingEntity.upper()
                        elif istitlecase(entity):
                            toReadingEntity = titlecase(toReadingEntity)

                        toSequence.append(toReadingEntity)
                    else:
                        # formatting entity
                        toSequence.append(entity)
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
            >>> targetOp = operator.PinyinOperator(toneMarkType='numbers')
            >>> pinyinConv = converter.PinyinDialectConverter(
            ...     targetOperators=[targetOp])
            >>> pinyinConv.convert(u'hànzì', 'Pinyin', 'Pinyin')
            u'han4zi4'

        - Convert Pinyin written with numbers, the ü (u with umlaut) replaced
            by character v and omitted fifth tone to standard Pinyin:

            >>> sourceOp = operator.PinyinOperator(toneMarkType='numbers',
            ...    yVowel='v', missingToneMark='fifth')
            >>> pinyinConv = converter.PinyinDialectConverter(
            ...     sourceOperators=[sourceOp])
            >>> pinyinConv.convert('nv3hai2zi', 'Pinyin', 'Pinyin')
            u'n\u01dah\xe1izi'

        - Or more elegantly:

            >>> f = ReadingFactory()
            >>> f.convert('nv3hai2zi', 'Pinyin', 'Pinyin',
            ...     sourceOptions={'toneMarkType': 'numbers', 'yVowel': 'v',
            ...     'missingToneMark': 'fifth'})
            u'n\u01dah\xe1izi'

        - Decompose the reading of a dictionary entry from CEDICT into syllables
            and convert the ü-vowel and forms of I{Erhua sound}:

            >>> pinyinFrom = operator.PinyinOperator(toneMarkType='numbers',
            ...     yVowel='u:', Erhua='oneSyllable')
            >>> syllables = pinyinFrom.decompose('sun1nu:r3')
            >>> print syllables
            ['sun1', 'nu:r3']
            >>> pinyinTo = operator.PinyinOperator(toneMarkType='numbers',
            ...     Erhua='twoSyllables')
            >>> pinyinConv = converter.PinyinDialectConverter(
            ...     sourceOperators=[pinyinFrom], targetOperators=[pinyinTo])
            >>> pinyinConv.convertEntities(syllables, 'Pinyin', 'Pinyin')
            [u'sun1', u'n\xfc3', u'r5']

        - Or more elegantly with entities already decomposed:

            >>> f.convertEntities(['sun1', 'nu:r3'], 'Pinyin', 'Pinyin',
            ...     sourceOptions={'toneMarkType': 'numbers', 'yVowel': 'u:',
            ...        'Erhua': 'oneSyllable'},
            ...     targetOptions={'toneMarkType': 'numbers',
            ...        'Erhua': 'twoSyllables'})
            [u'sun1', u'n\xfc3', u'r5']

        - Fix cosmetic errors in Pinyin input (note tone mark and apostrophe):

            >>> f.convert(u"Wǒ peí nǐ qù Xīān.", 'Pinyin', 'Pinyin')
            u"W\u01d2 p\xe9i n\u01d0 q\xf9 X\u012b'\u0101n."

        - Fix more errors in Pinyin input (note diacritics):

            >>> string = u"Wŏ peí nĭ qù Xīān."
            >>> dialect = operator.PinyinOperator.guessReadingDialect(string)
            >>> f.convert(string, 'Pinyin', 'Pinyin', sourceOptions=dialect)
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

        if self.breakUpErhua not in ['on', 'auto', 'off']:
            raise ValueError("Invalid option %s for keyword 'breakUpErhua'"
                % repr(self.breakUpErhua))

        # get Erhua settings, 'twoSyllables' is default
        if self.breakUpErhua == 'on' \
            or (self.breakUpErhua == 'auto' \
                and self._getToOperator('Pinyin').erhua == 'ignore')\
            or (self._getToOperator('Pinyin').erhua == 'twoSyllables'\
            and self._getFromOperator('Pinyin').erhua == 'oneSyllable'):
            # need to convert from one-syllable-form to two-syllables-form
            self._convertErhuaFunc = self.convertToTwoSyllablesErhua
        elif self._getToOperator('Pinyin').erhua == 'oneSyllable'\
            and self._getFromOperator('Pinyin').erhua != 'oneSyllable':
            # need to convert from two-syllables-form to one-syllable-form
            self._convertErhuaFunc = self.convertToSingleSyllableErhua
        elif self._getFromOperator('Pinyin').erhua != 'ignore'\
            and self._getToOperator('Pinyin').erhua == 'ignore':
            # no real conversion but make sure to raise an error for Erhua forms
            self._convertErhuaFunc = self._checkForErhua
        else:
            # do nothing
            self._convertErhuaFunc = lambda x: x

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
        if not self.keepPinyinApostrophes:
            readingEntities = self._getFromOperator(fromReading)\
                .removeApostrophes(readingEntities)

        targetOptions = {}
        for option in ['shortenedLetters', 'yVowel']:
            targetOptions[option] = getattr(self._getToOperator(toReading),
                option)

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
        entityTuples = self._convertErhuaFunc(entityTuples)

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

                plainSyllable = self._getFromOperator(fromReading)\
                    .convertPlainEntity(plainSyllable, targetOptions)

                # fix Erhua form if needed
                if plainSyllable.lower() == 'r' \
                    and ((self.breakUpErhua == 'auto' \
                        and self._getToOperator('Pinyin').erhua == 'ignore') \
                        or self.breakUpErhua == 'on'):
                    # transfer letter case, title() cannot be tested, len() == 1
                    if plainSyllable.isupper():
                        plainSyllable = 'ER'
                    else:
                        plainSyllable = 'er'

                # letter case
                if self._getToOperator(toReading).case == 'lower':
                    plainSyllable = plainSyllable.lower()

                try:
                    toReadingEntities.append(
                        self._getToOperator(toReading).getTonalEntity(
                            plainSyllable, tone))
                except InvalidEntityError, e:
                    # handle this as a conversion error as the converted
                    #   syllable is not accepted by the operator
                    raise ConversionError(*e.args)
            elif entry == self._getToOperator(fromReading).pinyinApostrophe:
                toReadingEntities.append(
                    self._getToOperator(toReading).pinyinApostrophe)
            else:
                toReadingEntities.append(entry)

        return toReadingEntities

    @staticmethod
    def convertToSingleSyllableErhua(entityTuples):
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
                plainSyllable, _ = entry
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

    @staticmethod
    def convertToTwoSyllablesErhua(entityTuples):
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

    @staticmethod
    def _checkForErhua(entityTuples):
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

    Examples
    ========
    Convert to superscript numbers (default):
        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert(u'Ssŭ1ma3 Ch’ien1', 'WadeGiles', 'WadeGiles',
        ...     sourceOptions={'toneMarkType': 'numbers'})
        u'Ss\u016d\xb9-ma\xb3 Ch\u2019ien\xb9'

    Convert form without diacritic to standard form:
        >>> f.convert(u'ch’eng', 'WadeGiles', 'WadeGiles',
        ...     sourceOptions={'diacriticE': 'e'})
        u'ch\u2019\xeang'

    Convert forms with lost umlaut:
        >>> f.convert(u'hsu³-hun¹', 'WadeGiles', 'WadeGiles',
        ...     sourceOptions={'umlautU': 'u'})
        u'hs\xfc\xb3-hun\xb9'

    See L{WadeGilesOperator} for more examples.
    """
    CONVERSION_DIRECTIONS = [('WadeGiles', 'WadeGiles')]

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone \
            = self._getFromOperator(fromReading).splitEntityTone(entity)

        targetOptions = {}
        for option in ['diacriticE', 'zeroFinal', 'umlautU',
            'wadeGilesApostrophe', 'useInitialSz']:
            targetOptions[option] = getattr(self._getToOperator(toReading),
                option)

        plainSyllable = self._getFromOperator(fromReading).convertPlainEntity(
            plainSyllable, targetOptions)

        # fix letter case
        if self._getToOperator(toReading).case == 'lower':
            plainSyllable = plainSyllable.lower()

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

    Upper- or lowercase will be transfered between syllables, no special
    formatting according to anyhow defined standards will be guaranteed.
    Upper-/lowercase will be identified according to three classes: either the
    whole syllable is uppercase, only the initial letter is uppercase
    (titlecase) or otherwise the whole syllable is assumed being lowercase. For
    entities of single latin characters uppercase has precedence over titlecase,
    e.g. I{R5} will convert to I{ER5} when Erhua forms are "unroled", not to
    I{Er5}.

    Conversion cannot in general be done in a one-to-one manner. Standard Pinyin
    has no notion to explicitly specify missing tonal information while this is
    in general given in Wade-Giles by just omitting the tone digits. This
    implementation furthermore doesn't support explicit depiction of I{Erhua} in
    the Wade-Giles romanisation system thus failing when r-colourised syllables
    are found.
    """
    CONVERSION_DIRECTIONS = [('Pinyin', 'WadeGiles'), ('WadeGiles', 'Pinyin')]
    # Use the tone mark type 'numbers' from Pinyin to support missing tonal
    #   information. Erhua furthermore is not supported.
    DEFAULT_READING_OPTIONS = {'Pinyin': {'erhua': 'ignore',
        'toneMarkType': 'numbers'}, 'WadeGiles': {}}

    def convertEntities(self, readingEntities, fromReading, toReading):
        # For conversion from Wade-Giles remove the hyphens that will not be
        #   transfered to Pinyin.
        if fromReading == 'WadeGiles':
            readingEntities = self._getFromOperator(fromReading).removeHyphens(
                readingEntities)

        return super(PinyinWadeGilesConverter, self).convertEntities(
            readingEntities, fromReading, toReading)

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone = self._f.splitEntityTone(entity, fromReading,
            **self.DEFAULT_READING_OPTIONS[fromReading])

        # lookup in database
        if fromReading == "WadeGiles":
            table = self.db.tables['WadeGilesPinyinMapping']
            transSyllable = self.db.selectScalar(
                select([table.c.Pinyin], table.c.WadeGiles == plainSyllable))
        elif fromReading == "Pinyin":
            # mapping from WG to Pinyin has old, dialect forms, use index
            table = self.db.tables['WadeGilesPinyinMapping']
            transSyllables = self.db.selectScalars(
                select([table.c.WadeGiles],
                    and_(table.c.Pinyin == plainSyllable,
                        table.c.PinyinIdx == 0)))
            if len(transSyllables) > 1:
                raise AmbiguousConversionError(
                    "conversion for entity '%s' is ambiguous: %s" \
                        % (entity, ', '.join(transSyllables)))
            elif transSyllables:
                transSyllable = transSyllables[0]
            else:
                transSyllable = None

        if not transSyllable:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' not supported")

        try:
            return self._f.getTonalEntity(transSyllable, tone, toReading,
                **self.DEFAULT_READING_OPTIONS[toReading])
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
        @keyword breakUpAbbreviated: if set to C{'on'} I{abbreviated spellings}
            will be converted to full entities, e.g. I{sherm.me} will be
            converted to I{shern.me}, if set to C{'auto'} abbreviated forms are
            converted if the given target reading operator doesn't support
            those forms, if set to C{'off'} abbreviated forms will always be
            conserved.
        @todo Impl: Strict mode for tone abbreviating spellings. Raise
            AmbiguousConversionError, e.g. raise on I{a} which could be I{.a} or
            I{a}.
        @todo Impl: Add option to remove hyphens, "A Grammar of Spoken Chinese,
            p. xxii", Conversion to Pinyin can use that.
        """
        super(GRDialectConverter, self).__init__(*args, **options)

        # conversion of abbreviated forms
        if self.breakUpAbbreviated not in ['on', 'auto', 'off']:
            raise ValueError(
                "Invalid option %s for keyword 'breakUpAbbreviated'"
                    % repr(self.breakUpAbbreviated))

    @classmethod
    def getDefaultOptions(cls):
        options = super(GRDialectConverter, cls).getDefaultOptions()
        options.update({'keepGRApostrophes': False,
            'breakUpAbbreviated': 'auto'})

        return options

    def convertEntities(self, readingEntities, fromReading='GR',
        toReading='GR'):
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")

        # abbreviated forms
        if self.breakUpAbbreviated == 'on' \
            or (self.breakUpAbbreviated == 'auto' \
                and not self._getToOperator(toReading).abbreviations):
            # remove x, v
            readingEntities = self.convertRepetitionMarker(readingEntities)
            # substitute abbreviations
            readingEntities = self.convertAbbreviatedEntities(readingEntities)

        if self.keepGRApostrophes:
            # convert separator apostrophe
            fromApostrophe = self._getFromOperator(fromReading)\
                .grSyllableSeparatorApostrophe
            toApostrophe = self._getToOperator(toReading)\
                .grSyllableSeparatorApostrophe
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
        if self._getToOperator(toReading).case == 'lower':
            readingEntities = [entity.lower() for entity in readingEntities]

        # convert rhotacised final apostrophe
        fromApostrophe = self._getFromOperator(fromReading)\
            .grRhotacisedFinalApostrophe
        toApostrophe = self._getToOperator(toReading)\
            .grRhotacisedFinalApostrophe
        if fromApostrophe != toApostrophe:
            readingEntities = [entity.replace(fromApostrophe, toApostrophe) \
                for entity in readingEntities]

        # convert optional neutral tone marker
        fromMarker = self._getFromOperator(fromReading)\
            .optionalNeutralToneMarker
        toMarker = self._getToOperator(toReading).optionalNeutralToneMarker
        if fromMarker != toMarker:
            convReadingEntities = []
            for entity in readingEntities:
                if entity.startswith(fromMarker) \
                    and self._getFromOperator(fromReading).isReadingEntity(
                        entity):
                    entity = entity.replace(fromMarker, toMarker, 1)
                convReadingEntities.append(entity)
            readingEntities = convReadingEntities

        return readingEntities

    def convertRepetitionMarker(self, readingEntities):
        """
        Converts the I{repetition markers} I{x} and I{v} to the full form they
        represent.

        @type readingEntities: list of str
        @param readingEntities: reading entities
        @rtype: list of str
        @return: reading entities with subsituted I{repetition markers}
        @raise ConversionError: if repetition markers I{x}, I{v} don't follow a
            reading entity
        """
        def findReadingEntity(readingEntities, idx):
            while idx >= 0:
                if grOperator.isReadingEntity(readingEntities[idx]):
                    return idx
                idx -= 1

            return -1

        def getRepetitionEntity(repetitionEntity, realEntity):
            if realEntity in repeatLast or realEntity in repeatSecondLast:
                raise ConversionError(
                "Cluster of more than two repetition markers")
            try:
                plainRealEntity, realTone = grOperator.splitEntityTone(
                    realEntity)
                baseTone = grOperator.getBaseTone(realTone)
            except UnsupportedError, e:
                raise ConversionError(
                    "Unabled to get ethymological tone if  '%s': %s"
                    % (realEntity, e))

            toneMapping = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}

            if repetitionEntity.startswith('.'):
                tone = '5thToneEtymological%s' % toneMapping[baseTone]
            elif repetitionEntity.startswith(
                grOperator.optionalNeutralToneMarker):
                tone = '%sToneOptional5th' % toneMapping[baseTone]
            else:
                tone = realTone
            return grOperator.getTonalEntity(plainRealEntity, tone)

        repeatedEntities = []
        grOperator = self._getFromOperator('GR')

        # Convert repetition markers, go backwards as 'vx' needs the 'x' to
        #   be concious about the preceding 'v'.
        repeatLast = ['x', '.x', grOperator.optionalNeutralToneMarker + u'x']
        repeatSecondLast = ['v', '.v',
            grOperator.optionalNeutralToneMarker + u'v']
        for idx in range(len(readingEntities)-1, -1, -1):
            # test for 'x'
            if readingEntities[idx] in repeatLast:
                targetEntityIdx = findReadingEntity(readingEntities, idx-1)
                if targetEntityIdx < 0:
                    raise ConversionError(
                        "Target syllable not found for repetition marker"
                        "'x' at '%d'" % idx)

                # Check for special case preceding 'v'.
                vMarkerIdx = None
                if readingEntities[targetEntityIdx] in repeatSecondLast:
                    vMarkerIdx = targetEntityIdx
                    targetEntityIdx = findReadingEntity(readingEntities,
                        targetEntityIdx-1)
                    if targetEntityIdx < 0:
                        raise ConversionError(
                            "Target syllable not found for repetition markers"
                            "'vx' at '%d'" % idx)

                # fix tone and append
                repeatedEntities.insert(0, getRepetitionEntity(
                    readingEntities[idx], readingEntities[targetEntityIdx]))

                # For exact marker 'vx' (without whitespace or other
                #   non-reading characters in-between) include all
                #   non-reading entities between target syllables
                if vMarkerIdx != None and vMarkerIdx + 1 == idx:
                    vTargetEntityIdx = findReadingEntity(readingEntities,
                        targetEntityIdx-1)
                    for i in range(targetEntityIdx-1, vTargetEntityIdx, -1):
                        repeatedEntities.insert(0, readingEntities[i])

            # test for 'v'
            elif readingEntities[idx] in repeatSecondLast:
                # Look for second last entity
                targetEntityIdx = findReadingEntity(readingEntities, idx-1)
                targetEntityIdx = findReadingEntity(readingEntities,
                    targetEntityIdx-1)
                if targetEntityIdx < 0:
                    raise ConversionError(
                        "Target syllable not found for repetition marker"
                        "'v' at '%d'" % idx)

                # fix tone and append
                repeatedEntities.insert(0, getRepetitionEntity(
                    readingEntities[idx], readingEntities[targetEntityIdx]))
            else:
                repeatedEntities.insert(0, readingEntities[idx])

        return repeatedEntities

    def convertAbbreviatedEntities(self, readingEntities):
        """
        Converts the abbreviated GR spellings to the full form. Non-abbreviated
        forms will returned unchanged. Takes care of capitalisation.

        Multi-syllable forms may not be separated by whitespaces or other
        entities.

        To also convert I{repetition markers} run L{convertRepetitionMarker()}
        first.

        @type readingEntities: list of str
        @param readingEntities: reading entities
        @rtype: list of str
        @return: full entities
        @raise AmbiguousConversionError: if conversion is ambiguous.
        """
        convertedEntities = []
        grOperator = self._getFromOperator('GR')

        abbreviatedForms = grOperator.getAbbreviatedForms()
        maxLen = max([len(form) for form in abbreviatedForms])
        i = 0
        while i < len(readingEntities):
            maxLookahead = min(maxLen, len(readingEntities) - i)
            # from max len down to 1, check if this is a abbreviated form
            # testAbbreviationConsistency() from
            #   test.readingconverter.GRDialectConsistencyTest assures
            #   that no abbreviations overlap, so we there's max. one solution
            for entityCount in range(maxLookahead, 0, -1):
                originalEntities = readingEntities[i:i+entityCount]
                entities = [entity.lower() for entity in originalEntities]

                if tuple(entities) in abbreviatedForms:
                    abbrData = grOperator.getAbbreviatedFormData(entities)
                    # get all forms that are neither already full or ignorable
                    fullForms = set([tuple(full) for _, full, info in abbrData \
                        if len(info & set('FI')) == 0])

                    # check for ambiguous mapping
                    if len(fullForms) > 1:
                        full = [' '.join(form) for form in fullForms]
                        raise AmbiguousConversionError(
                            "conversion for entities '%s' is ambiguous: %s" \
                                % (' '.join(entities), ', '.join(full)))
                    elif len(fullForms) == 1:
                        converted = list(fullForms.pop())
                        # get proper letter case
                        if ''.join(originalEntities).isupper():
                            converted = [entity.upper() for entity in converted]
                        elif istitlecase(''.join(originalEntities)):
                            converted[0] = titlecase(converted[0])

                        convertedEntities.extend(converted)
                        i += entityCount

                        break
            else:
                # nothing found, continue to following entities
                convertedEntities.append(readingEntities[i])
                i += 1

        return convertedEntities


class GRPinyinConverter(RomanisationConverter):
    u"""
    Provides a converter between the Chinese romanisation I{Gwoyeu Romatzyh} and
    I{Hanyu Pinyin}.

    Features:
        - configurable mapping of options neutral tone when converting from GR,
        - conversion of abbreviated forms of GR.

    Upper- or lowercase will be transfered between syllables, no special
    formatting according to anyhow defined standards will be guaranteed.
    Upper-/lowercase will be identified according to three classes: either the
    whole syllable is uppercase, only the initial letter is uppercase
    (titlecase) or otherwise the whole syllable is assumed being lowercase. For
    entities of single latin characters uppercase has precedence over titlecase,
    e.g. I{I} will convert to I{YI} from Gwoyeu Romatzyh to Pinyin, not to
    I{Yi}.

    Limitations
    ===========
    Conversion cannot in general be done in a one-to-one manner.
    I{Gwoyeu Romatzyh} (GR) gives the etymological tone for a syllable in
    neutral tone while Pinyin doesn't. Thus converting neutral tone syllables
    from Pinyin to GR will fail as the etymological tone is unknown to the
    operator.

    While tones in GR carry more information, I{r-coloured} syllables
    (I{Erlhuah}) are rendered the way they are pronounced thus loosing
    information about the underlying syllable. Converting those forms to Pinyin
    is not always possible as for example I{jieel} will raise an
    L{AmbiguousConversionError} as it stems from I{jǐ}, I{jiě} and I{jǐn}.
    Having the original string in Chinese characters might help to disambiguate.

    Neutral tone
    ------------
    As described above, converting the neutral tone from Pinyin to GR fails.
    Converting to Pinyin will lose knowledge about the etymological tone, and in
    the case of I{optional neutral tones} it has to be decided whether the
    neutral tone version or the etymological tone is chosen, as Pinyin can only
    display one. This can be controlled using option
    C{'grOptionalNeutralToneMapping'}.
    """
    CONVERSION_DIRECTIONS = [('GR', 'Pinyin'), ('Pinyin', 'GR')]
    # GR deals with Erlhuah in one syllable, force on Pinyin. Convert GR
    #   abbreviations to full forms
    DEFAULT_READING_OPTIONS = {'Pinyin': {'erhua': 'oneSyllable'},
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
        @keyword grOptionalNeutralToneMapping: if set to 'original' GR syllables
            marked with an optional neutral tone will be mapped to the
            etymological tone, if set to 'neutral' they will be mapped to the
            neutral tone in Pinyin.
        """
        super(GRPinyinConverter, self).__init__(*args, **options)

        if self.grOptionalNeutralToneMapping not in ['original', 'neutral']:
            raise ValueError(
                "Invalid option %s for keyword 'grOptionalNeutralToneMapping'"
                    % repr(self.grOptionalNeutralToneMapping))

        # mapping from GR tones to Pinyin
        self._grToneMapping = dict([(tone, int(tone[0])) \
            for tone in readingoperator.GROperator.TONES])
        # set optional neutral mapping
        if self.grOptionalNeutralToneMapping == 'neutral':
            for tone in ['1stToneOptional5th', '2ndToneOptional5th',
                '3rdToneOptional5th', '4thToneOptional5th']:
                self._grToneMapping[tone] = 5

        # mapping from Pinyin tones to GR
        self._pyToneMapping = {1: '1stTone', 2: '2ndTone', 3: '3rdTone',
            4: '4thTone', 5: None}

    @classmethod
    def getDefaultOptions(cls):
        options = super(GRPinyinConverter, cls).getDefaultOptions()
        options.update({'grOptionalNeutralToneMapping': 'original'})

        return options

    def convertBasicEntity(self, entity, fromReading, toReading):
        erlhuahForm = False

        # catch Erlhuah in GR
        if fromReading == "GR" \
            and self._getGROperator().isRhotacisedReadingEntity(entity):
            baseEntities = self._getGROperator().getBaseEntitiesForRhotacised(
                entity)
            if len(baseEntities) > 1:
                raise AmbiguousConversionError(
                    "conversion for entity '%s' is ambiguous (Erlhuah)" \
                        % entity)
            assert(len(baseEntities) == 1)
            plainSyllable, tone = baseEntities.pop()

            erlhuahForm = True
        else:
            # split syllable into plain part and tonal information
            plainSyllable, tone = self._f.splitEntityTone(entity, fromReading,
                **self.DEFAULT_READING_OPTIONS[fromReading])

        # lookup in database
        if fromReading == "GR":
            table = self.db.tables['PinyinGRMapping']
            transSyllable = self.db.selectScalar(select([table.c.Pinyin],
                table.c.GR == plainSyllable))
            transTone = self._grToneMapping[tone]

        elif fromReading == "Pinyin":
            # reduce Erlhuah form
            if plainSyllable != 'er' and plainSyllable.endswith('r'):
                erlhuahForm = True
                plainSyllable = plainSyllable[:-1]

            table = self.db.tables['PinyinGRMapping']
            transSyllable = self.db.selectScalar(select([table.c.GR],
                table.c.Pinyin == plainSyllable))
            if self._pyToneMapping[tone]:
                transTone = self._pyToneMapping[tone]
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
                if toReading == 'Pinyin' and erlhuahForm:
                    transSyllable += 'r'

                return self._f.getTonalEntity(transSyllable, transTone,
                    toReading, **self.DEFAULT_READING_OPTIONS[toReading])
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)

    def _getGROperator(self):
        """Creates an instance of a GROperator if needed and returns it."""
        if not hasattr(self, '_grOperator'):
            self._grOperator = readingoperator.GROperator(
                **self.DEFAULT_READING_OPTIONS['GR'])
        return self._grOperator


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

    DEFAULT_READING_OPTIONS = {'Pinyin': {'erhua': 'ignore',
        'toneMarkType': 'numbers', 'missingToneMark': 'noinfo',
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
        if self.sandhiFunction and not hasattr(self.sandhiFunction, '__call__'):
            raise ValueError("Non-callable object %s" \
                    % repr(self.sandhiFunction)
                + " for keyword 'sandhiFunction'")

        # set the sandhiFunction for handling general phonological changes
        if self.coarticulationFunction \
            and not hasattr(self.coarticulationFunction, '__call__'):
            raise ValueError("Non-callable object %s" \
                    % repr(self.coarticulationFunction)
                + " for keyword 'coarticulationFunction'")

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
                    if self._f.isFormattingEntity(entity, fromReading,
                        **self.DEFAULT_READING_OPTIONS[fromReading]):
                        # ignore formatting entities
                        continue
                    # split syllable into plain part and tonal information
                    plainSyllable, tone = self._f.splitEntityTone(entity,
                        fromReading,
                        **self.DEFAULT_READING_OPTIONS[fromReading])

                    transEntry = None
                    if self.coarticulationFunction:
                        transEntry = self.coarticulationFunction(self,
                            sequence[:idx], plainSyllable, tone,
                                sequence[idx+1:])

                    if not transEntry:
                        # standard conversion
                        transEntry = self._convertSyllable(plainSyllable, tone)

                    ipaTupelList.append(transEntry)

                # handle sandhi
                if self._getToOperator(toReading).toneMarkType != 'None':
                    if self.sandhiFunction:
                        ipaTupelList = self.sandhiFunction(self, ipaTupelList)

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

    @staticmethod
    def lowThirdAndNeutralToneRule(converterInst, entityTuples):
        """
        Converts C{'3rdToneRegular'} to C{'3rdToneLow'} for syllables followed
        by others and C{'5thTone'} to the respective forms when following
        another syllable.

        This function serves as the default rule and can be overwritten by
        giving a function as option C{sandhiFunction} on instantiation.

        @type converterInst: instance
        @param converterInst: instance of the PinyinIPA converter
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
                    tone \
                        = PinyinIPAConverter.NEUTRAL_TONE_MAPPING[precedingTone]
                elif tone == '3rdToneRegular' and idx + 1 != len(entityTuples):
                    tone = '3rdToneLow'
                entry = (plainSyllable, tone)

                precedingTone = tone
            else:
                precedingTone = None

            convertedEntities.append(entry)

        return convertedEntities

    @staticmethod
    def finalECoarticulation(converterInst, leftContext, plainSyllable, tone,
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

        @type converterInst: instance
        @param converterInst: instance of the PinyinIPA converter
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
            _, final = converterInst._getToOperator('Pinyin').getOnsetRhyme(
                plainSyllable)
            if final == 'e':
                # lookup in database
                table = converterInst.db.tables['PinyinIPAMapping']
                transSyllables = converterInst.db.selectScalars(
                    select([table.c.IPA], and_(table.c.Pinyin == plainSyllable,
                        table.c.Feature == '5thTone')))
                if not transSyllables:
                    raise ConversionError("conversion for entity '" \
                        + plainSyllable + "' not supported")
                elif len(transSyllables) != 1:
                    raise ConversionError("conversion for entity '" \
                        + plainSyllable + "' and tone '" + str(tone) \
                        + "' ambiguous")

                return transSyllables[0], \
                    PinyinIPAConverter.TONEMARK_MAPPING[tone]


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

    DEFAULT_READING_OPTIONS = {'Pinyin': {'erhua': 'ignore',
        'toneMarkType': 'numbers', 'missingToneMark': 'noinfo'}}

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
        self._reversePunctuationMapping = {}
        for key in self.PUNCTUATION_SIGNS_MAPPING:
            if key in self._reversePunctuationMapping:
                # ambiguous mapping, so remove
                self._reversePunctuationMapping[key] = None
            else:
                value = self.PUNCTUATION_SIGNS_MAPPING[key]
                self._reversePunctuationMapping[value] = key

        # regex to split out punctuation
        self._pinyinPunctuationRegex = re.compile(ur'(' \
            + '|'.join([re.escape(p) for p \
                in self.PUNCTUATION_SIGNS_MAPPING.keys()]) \
            + '|.+?)')

        braillePunctuation = list(set(self.PUNCTUATION_SIGNS_MAPPING.values()))
        # longer marks first in regex
        braillePunctuation.sort(lambda x, y: len(y) - len(x))
        self._braillePunctuationRegex = re.compile(ur'(' \
            + '|'.join([re.escape(p) for p in braillePunctuation]) + '|.+?)')

    def _createMappings(self):
        """
        Creates the mappings of syllable initials and finals from the database.
        """
        # initials
        self._pinyinInitial2Braille = {}
        self._braille2PinyinInitial = {}

        table = self.db.tables['PinyinBrailleInitialMapping']
        entries = self.db.selectRows(
            select([table.c.PinyinInitial, table.c.Braille]))

        for pinyinInitial, brailleChar in entries:
            # Pinyin 2 Braille
            if pinyinInitial in self._pinyinInitial2Braille:
                raise ValueError(
                    "Ambiguous mapping from Pinyin syllable initial to Braille")
            self._pinyinInitial2Braille[pinyinInitial] = brailleChar
            # Braille 2 Pinyin
            if brailleChar not in self._braille2PinyinInitial:
                self._braille2PinyinInitial[brailleChar] = set()
            self._braille2PinyinInitial[brailleChar].add(pinyinInitial)

        self._pinyinInitial2Braille[''] = ''
        self._braille2PinyinInitial[''] = set([''])

        # finals
        self._pinyinFinal2Braille = {}
        self._braille2PinyinFinal = {}

        table = self.db.tables['PinyinBrailleFinalMapping']
        entries = self.db.selectRows(
            select([table.c.PinyinFinal, table.c.Braille]))

        for pinyinFinal, brailleChar in entries:
            # Pinyin 2 Braille
            if pinyinFinal in self._pinyinFinal2Braille:
                raise ValueError(
                    "Ambiguous mapping from Pinyin syllable final to Braille")
            self._pinyinFinal2Braille[pinyinFinal] = brailleChar
            # Braille 2 Pinyin
            if brailleChar not in self._braille2PinyinFinal:
                self._braille2PinyinFinal[brailleChar] = set()
            self._braille2PinyinFinal[brailleChar].add(pinyinFinal)

        # map ê to same Braille character as e
        self._pinyinFinal2Braille[u'ê'] = self._pinyinFinal2Braille[u'e']

    def convertEntitySequence(self, entitySequence, fromReading, toReading):
        toReadingEntities = []
        if fromReading == "Pinyin":
            for sequence in entitySequence:
                if type(sequence) == type([]):
                    for entity in sequence:
                        if self._f.isReadingEntity(entity, fromReading,
                            **self.DEFAULT_READING_OPTIONS[fromReading]):
                            toReadingEntity = self.convertBasicEntity(entity,
                                fromReading, toReading)
                            toReadingEntities.append(toReadingEntity)
                        else:
                            toReadingEntities.append(entity)
                else:
                    # find punctuation marks
                    for subEntity in self._pinyinPunctuationRegex.findall(
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
                    for subEntity in self._braillePunctuationRegex.findall(
                        sequence):
                        if subEntity in self._reversePunctuationMapping:
                            if not self._reversePunctuationMapping[subEntity]:
                                raise AmbiguousConversionError(
                                    "conversion for entity '" + subEntity \
                                        + "' is ambiguous")
                            toReadingEntities.append(
                                self._reversePunctuationMapping[subEntity])
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
        fromOperator = self._f._getReadingOperatorInstance(fromReading,
            **fromOptions)

        plainEntity, tone = fromOperator.splitEntityTone(entity)
        # lookup in database
        if fromReading == "Pinyin":
            initial, final = fromOperator.getOnsetRhyme(plainEntity)

            if plainEntity not in ['zi', 'ci', 'si', 'zhi', 'chi', 'shi', 'ri']:
                try:
                    transSyllable = self._pinyinInitial2Braille[initial] \
                        + self._pinyinFinal2Braille[final]
                except KeyError:
                    raise ConversionError("conversion for entity '" \
                        + plainEntity + "' not supported")
            else:
                try:
                    transSyllable = self._pinyinInitial2Braille[initial]
                except KeyError:
                    raise ConversionError("conversion for entity '" \
                        + plainEntity + "' not supported")
        elif fromReading == "MandarinBraille":
            # mapping from Braille to Pinyin is ambiguous
            initial, final = fromOperator.getOnsetRhyme(plainEntity)

            # get all possible forms
            forms = []
            for i in self._braille2PinyinInitial[initial]:
                for f in self._braille2PinyinFinal[final]:
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
        if self._getToOperator(toReading).case == 'lower':
            plainSyllable = plainSyllable.lower()

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
        ...     sourceOptions={'toneMarkType': 'numbers',
        ...         'yaleFirstTone': '1stToneFalling'})
        u'gw\xf3ngj\xe0uw\xe1'
    """
    CONVERSION_DIRECTIONS = [('CantoneseYale', 'CantoneseYale')]

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone \
            = self._getFromOperator(fromReading).splitEntityTone(entity)

        # capitalisation
        if self._getToOperator(toReading).case == 'lower':
            plainSyllable = plainSyllable.lower()

        # get syllable with tone mark
        try:
            transEntity = self._getToOperator(toReading).getTonalEntity(
                plainSyllable, tone)

            if istitlecase(entity) and not entity.isupper() \
                and transEntity.isupper():
                # don't change uppercase
                transEntity = titlecase(transEntity)
            return transEntity
        except InvalidEntityError, e:
            # handle this as a conversion error as the converted syllable is not
            #   accepted by the operator
            raise ConversionError(*e.args)


class JyutpingYaleConverter(RomanisationConverter):
    u"""
    Provides a converter between the Cantonese romanisation systems I{Jyutping}
    and I{Cantonese Yale}.

    Upper- or lowercase will be transfered between syllables, no special
    formatting according to anyhow defined standards will be guaranteed.
    Upper-/lowercase will be identified according to three classes: either the
    whole syllable is uppercase, only the initial letter is uppercase
    (titlecase) or otherwise the whole syllable is assumed being lowercase. For
    entities of single latin characters uppercase has precedence over titlecase,
    e.g. I{E5} will convert to I{ÉH} in Cantonese Yale, not to I{Éh}.

    High Level vs. High Falling Tone
    ================================
    As described in L{CantoneseYaleOperator} the Cantonese Yale romanisation
    system makes a distinction between the high level tone and the high falling
    tone in general while Jyutping does not. On conversion it is thus important
    to choose the correct mapping. This can be configured by applying the option
    C{yaleFirstTone} when construction the converter (or telling the
    L{ReadingFactory} which converter to use).

    Example:

        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert(u'gwong2zau1waa2', 'Jyutping', 'CantoneseYale',
        ...     yaleFirstTone='1stToneFalling')
        u'gw\xf3ngj\xe0uw\xe1'
    """
    CONVERSION_DIRECTIONS = [('Jyutping', 'CantoneseYale'),
        ('CantoneseYale', 'Jyutping')]
    # use special dialect for Yale to retain information for first tone and
    #   missing tones
    DEFAULT_READING_OPTIONS = {'Jyutping': {},
        'CantoneseYale': {'toneMarkType': 'internal'}}

    DEFAULT_TONE_MAPPING = {1: '1stToneLevel', 2: '2ndTone', 3: '3rdTone',
        4: '4thTone', 5: '5thTone', 6: '6thTone'}
    """
    Mapping of Jyutping tones to Yale tones. Tone 1 can be changed via option
    'yaleFirstTone'.
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
        @keyword yaleFirstTone: tone in Yale which the first tone from Jyutping
            should be mapped to. Value can be C{'1stToneLevel'} to map to the
            level tone with contour 55 or C{'1stToneFalling'} to map to the
            falling tone with contour 53. This is only important if the target
            reading dialect uses diacritical tone marks.
        """
        super(JyutpingYaleConverter, self).__init__(*args, **options)

        # check yaleFirstTone for handling ambiguous conversion of first
        #   tone in Cantonese that has two different representations in Yale,
        #   but only one in Jyutping
        if self.yaleFirstTone not in ['1stToneLevel', '1stToneFalling']:
            raise ValueError("Invalid option %s for keyword 'yaleFirstTone'"
                % repr(self.yaleFirstTone))

        self.defaultToneMapping = self.DEFAULT_TONE_MAPPING.copy()
        self.defaultToneMapping[1] = self.yaleFirstTone

    @classmethod
    def getDefaultOptions(cls):
        options = super(JyutpingYaleConverter, cls).getDefaultOptions()
        options.update({'yaleFirstTone': '1stToneLevel'})

        return options

    def convertBasicEntity(self, entity, fromReading, toReading):
        # split syllable into plain part and tonal information
        plainSyllable, tone = self._f.splitEntityTone(entity, fromReading,
            **self.DEFAULT_READING_OPTIONS[fromReading])

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
                transTone = self.defaultToneMapping[tone]

        if not transSyllable:
            raise ConversionError("conversion for entity '" + plainSyllable \
                + "' not supported")
        try:
            return self._f.getTonalEntity(transSyllable, transTone, toReading,
                **self.DEFAULT_READING_OPTIONS[toReading])
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
        for fromReading, _, toReading in bridge:
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

        self.conversionOptions = options

    @classmethod
    def getDefaultOptions(cls):
        # merge together options of converters involved in bridge conversion
        def mergeOptions(defaultOptions, options):
            for option, value in options.items():
                assert(option not in defaultOptions \
                    or defaultOptions[option] == value)
                defaultOptions[option] = value

        converterClassLookup = {}
        for clss in cjklib.reading.ReadingFactory.getReadingConverterClasses():
            for fromReading, targetReading in clss.CONVERSION_DIRECTIONS:
                converterClassLookup[(fromReading, targetReading)] = clss

        # get default options for all converters used
        defaultOptions = super(BridgeConverter, cls).getDefaultOptions()
        for fromReading, bridgeReading, targetReading in cls.CONVERSION_BRIDGE:
            # from direction
            fromDefaultOptions = converterClassLookup[
                    (fromReading, bridgeReading)].getDefaultOptions()
            mergeOptions(defaultOptions, fromDefaultOptions)
            # to direction
            toDefaultOptions = converterClassLookup[
                    (bridgeReading, targetReading)].getDefaultOptions()
            mergeOptions(defaultOptions, toDefaultOptions)

        return defaultOptions

    def convertEntities(self, readingEntities, fromReading, toReading):
        if (fromReading, toReading) not in self.CONVERSION_DIRECTIONS:
            raise UnsupportedError("conversion direction from '" \
                + fromReading + "' to '" + toReading + "' not supported")
        bridgeReading = self.bridgeLookup[(fromReading, toReading)]

        # to bridge reading
        options = self.conversionOptions.copy()
        options['sourceOperators'] = [self._getFromOperator(fromReading)]
        bridgeReadingEntities = self._f.convertEntities(readingEntities,
            fromReading, bridgeReading, **options)

        # from bridge reading
        options = self.conversionOptions.copy()
        options['targetOperators'] = [self._getToOperator(toReading)]
        toReadingEntities = self._f.convertEntities(bridgeReadingEntities,
            bridgeReading, toReading, **options)

        return toReadingEntities
