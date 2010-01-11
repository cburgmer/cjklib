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
Provides higher level dictionary access.

This module provides classes for easy access to well known CJK dictionaries.
Queries can be done using a headword, reading or translation.

System and Useage
=================
Dictionary sources yield less structured information compared to other data
sources exposed in this library. Owing to this fact, a flexible system is
provided to the user.

Entry factories
---------------
Similar to SQL interfaces, entries can be returned in different fashion. An
X{entry factory} takes care of preparing the output. For this predefined
factories exist: L{ListEntryFactory}, which is used as default, will return each
entry as a list of its columns while L{DictEntryFactory} will return dict
objects.

Reading and translation formatting strategies
---------------------------------------------
As reading formattings vary and many readings can be converted into each other,
a X{reading formatting strategy} can be applied to return the expected format.
L{ReadingConversionStrategy} provides an easy way to convert the reading given
by the dictionary into the user defined reading.

For translations, a X{translation formatting strategy} can adapt given
translation strings. Such a strategy can for example consist of simple string
replacements.

Reading and translation search strategies
-----------------------------------------
Searching in natural language data is a difficult process and highly depends on
the use case at hand. For dictionaries whose readings have dialects a simple
search strategy exists converting the search string to the dictionary's reading.
With L{TonelessReadingSearchStrategy} also a more complex strategy exists to
cope with missing tonal information.

For translations simple strategies exist that take into acount additional
information put into parantheses. More complex ones can be implemented on the
basis of extending the underlying table, e.g. using I{full text search}
capabilities of the database server. One popular way is using stemming
algorithms for copying with inflections by reducing a word to its root form.

Examples
========
- Create a dictionary instance:

    >>> from cjklib.dictionary import *
    >>> d = CEDICT(entryFactory=DictEntryFactory())

- Get dictionary entries by reading:

    >>> [l['HeadwordSimplified'] for l in \\
    ...     d.getForReading('po1', 'Pinyin', toneMarkType='numbers')]
    [u'\u5761', u'\u6cfc', u'\u948b', u'\u9642', u'\u9887']

- Change a strategy (here search for a reading without tones):

    >>> d = CEDICT()
    >>> d.getForReading('nihao', 'Pinyin', toneMarkType='numbers')
    []
    >>> d = CEDICT(readingSearchStrategy=TonelessReadingSearchStrategy())
    >>> d.getForReading('nihao', 'Pinyin', toneMarkType='numbers')
    [(u'\u4f60\u597d', u'\u4f60\u597d', u'n\u01d0 h\u01ceo',\
 u'/hello/hi/how are you?/')]

- A simple dictionary search tool:

    >>> from cjklib.dictionary import *
    >>> from cjklib.reading import ReadingFactory
    >>> def search(string, reading=None):
    ...     # guess reading dialect
    ...     options = {}
    ...     if reading:
    ...         f = ReadingFactory()
    ...         opClass = f.getReadingOperatorClass(reading)
    ...         if hasattr(opClass, 'guessReadingDialect'):
    ...             options = opClass.guessReadingDialect(string)
    ...     # search
    ...     d = CEDICT(entryFactory=DictEntryFactory(),
    ...         readingSearchStrategy=TonelessReadingSearchStrategy())
    ...     result = d.getFor(string, fromReading=reading, **options)
    ...     # print
    ...     for e in result:
    ...         print e['HeadwordSimplified'], e['Reading'], e['Translation']
    ...
    >>> search('Nanjing', 'Pinyin')
    南京 Nán jīng /Nanjing subprovincial city on the Changjiang, capital of
    Jiangsu province 江蘇|江苏/capital of China at different historical periods/
    南靖 Nán jìng /Najing county in Zhangzhou 漳州[Zhang1 zhou1], Fujian/
    宁 níng /peaceful/rather/Ningxia (abbr.)/Nanjing (abbr.)/surname Ning/

@todo Impl: Use Iterators?
"""

import re
import types

from sqlalchemy import select
from sqlalchemy.sql import or_

from cjklib import reading
from cjklib.dbconnector import DatabaseConnector
from cjklib import exception
from cjklib.util import cross

#{ Entry factories

class ListEntryFactory(object):
    """Default entry factory, returning a list of columns."""
    def getEntries(self, results):
        """
        Returns the dictionary results as lists.
        """
        return results


class DictEntryFactory(object):
    """
    Dict entry factory, returning a dict with keys as given by the dictionary.
    """
    def setColumnNames(self, columnNames):
        """
        Sets the names of the dictionary's columns.

        @type columnNames: list of str
        @param columnNames: column names
        """
        self.columnNames = columnNames

    def getEntries(self, results):
        """
        Returns the dictionary results as dicts.
        """
        for row in results:
            if len(row) != len(self.columnNames):
                raise ValueError("Incompatible element counts %d for result: %d"
                    % (len(self.columnNames), len(row)))

        return [dict([(self.columnNames[i], row) for i, row in enumerate(row)])
            for row in results]

#}
#{ Reading formatting strategies

class PlainReadingStrategy(object):
    """Default reading formatting strategy, doing nothing."""
    def getReading(self, plainReading):
        """
        Returns the formatted reading.

        @type plainReading: str
        @param plainReading: reading as returned by the dictionary
        @rtype: str
        @return: formatted reading
        """
        return plainReading


class ReadingConversionStrategy(PlainReadingStrategy):
    """Converts the entries' reading string to the given target reading."""
    def __init__(self, toReading=None, targetOptions=None):
        """
        Constructs the conversion strategy.

        @type toReading: str
        @param toReading: target reading, if omitted, the dictionary's reading
            is assumed.
        @type targetOptions: dict
        @param targetOptions: target reading conversion options
        """
        self.toReading = toReading
        if targetOptions:
            self.targetOptions = targetOptions
        else:
            self.targetOptions = {}

    def setReadingFactory(self, readingFactory):
        """
        Sets the reading factory. This method is called by the
        dictionary object.

        @type readingFactory: instance
        @param readingFactory: L{ReadingFactory} instance
        """
        self._readingFactory = readingFactory

    def setReadingOptions(self, fromReading, sourceOptions):
        """
        Sets the dictionary reading options. This method is called by the
        dictionary object.

        @type fromReading: str
        @param fromReading: source reading as used in the dictionary
        @type sourceOptions: dict
        @param sourceOptions: source reading options
        """
        self.fromReading = fromReading
        self.sourceOptions = sourceOptions

    def getReading(self, plainReading):
        if not hasattr(self, 'fromReading'):
            raise ValueError('Strategy instance not initialized properly.'
                ' Probably incompatible to dictionary class.')

        toReading = self.toReading or self.fromReading
        try:
            return self._readingFactory.convert(plainReading, self.fromReading,
                toReading, sourceOptions=self.sourceOptions,
                targetOptions=self.targetOptions)
        except (exception.DecompositionError, exception.CompositionError,
            exception.ConversionError):
            return None

#}
#{ Translation formatting strategies

class PlainTranslationStrategy(object):
    """Default translation formatting strategy, doing nothing."""
    def getTranslation(self, plainTranslation):
        """
        Returns the formatted translation.

        @type plainTranslation: str
        @param plainTranslation: translation as returned by the dictionary
        @rtype: str
        @return: formatted translation
        """
        return plainTranslation

#}
#{ Translation search strategy

class ExactTranslationSearchStrategy(object):
    """Basic translation based search strategy."""
    def setDictionaryInstance(self, dictInstance):
        self._dictInstance = dictInstance
        if not hasattr(dictInstance, 'DICTIONARY_TABLE'):
            raise ValueError('Incompatible dictionary instance')

    def getWhereClause(self, searchStr):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by L{getMatchFunction()}.

        @type searchStr: str
        @param searchStr: search string
        @return: SQLAlchemy clause
        """
        dictionaryTable = self._dictInstance.db.tables[
            self._dictInstance.DICTIONARY_TABLE]
        return dictionaryTable.c.Translation.like('%' + searchStr + '%')

    def getMatchFunction(self, searchStr):
        """
        Gets a function that returns C{True} if the entry's translation matches
        the search string.

        This method provides the sufficient condition for a match. Note that
        matches from other SQL clauses might get included, that do not fulfill
        the conditions of L{getWhereClause()}.

        @type searchStr: str
        @param searchStr: search string
        @rtype: function
        @return: function that returns C{True} if the entry is a match
        """
        return lambda translation: searchStr in translation.split('/')


class SimpleTranslationSearchStrategy(ExactTranslationSearchStrategy):
    """
    Simple translation based search strategy. Takes into account additions put
    in parentheses and allows for multiple entries in one record separated by
    punctuation marks.
    """
    def getMatchFunction(self, searchStr):
        # start with a slash '/', make sure any opening parenthesis is
        #   closed, end any other entry with a punctuation mark, and match
        #   search string. Finish with other content in parantheses and
        #   a slash or punctuation mark
        regex = re.compile('/((\([^\)]+\)|[^\(])+[\,\;\.\?\!])?'
            + '(\s+|\([^\)]+\))*' + re.escape(searchStr) + '(\s+|\([^\)]+\))*'
            + '[/\,\;\.\?\!]')

        return lambda translation: regex.search(translation) is not None


class HanDeDictTranslationSearchStrategy(SimpleTranslationSearchStrategy):
    """
    HanDeDict translation based search strategy. Extends
    L{SimpleTranslationSearchStrategy} by taking into accout peculiarities of
    the HanDeDict format.
    """
    def getMatchFunction(self, searchStr):
        regex = re.compile('/((\([^\)]+\)|[^\(])+'
            + '(?!; Bsp.: [^/]+?--[^/]+)[\,\;\.\?\!])?' + '(\s+|\([^\)]+\))*'
            + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '[/\,\;\.\?\!]')

        return lambda translation: regex.search(translation) is not None

#}
#{ Reading search strategy

class ExactReadingSearchStrategy(object):
    """Basic translation based search strategy."""
    def setDictionaryInstance(self, dictInstance):
        self._dictInstance = dictInstance
        if not hasattr(dictInstance, 'DICTIONARY_TABLE'):
            raise ValueError('Incompatible dictionary instance')

    def getWhereClause(self, readingStr, fromReading, **options):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results
        may then be further narrowed by L{getMatchFunction()}.

        @type readingStr: str
        @param readingStr: search string
        @type fromReading: str
        @param fromReading: source reading as used in the dictionary
        @type options: dict
        @param options: source reading options
        @return: SQLAlchemy clause
        @raise ConversionError: if reading cannot be processed
        @todo Fix: letter case
        """
        dictionaryTable = self._dictInstance.db.tables[
            self._dictInstance.DICTIONARY_TABLE]
        return dictionaryTable.c.Reading == readingStr

    def getMatchFunction(self, readingStr, fromReading, **options):
        """
        Gets a function that returns C{True} if the entry's reading matches the
        search string.

        This method provides the sufficient condition for a match. Note that
        matches from other SQL clauses might get included, that do not fulfill
        the conditions of L{getWhereClause()}.

        @type readingStr: str
        @param readingStr: search string
        @type fromReading: str
        @param fromReading: source reading as used in the dictionary
        @type options: dict
        @param options: source reading options
        @rtype: function
        @return: function that returns C{True} if the entry is a match
        @raise ConversionError: if reading cannot be processed
        """
        return lambda reading: readingStr == reading


class SimpleReadingSearchStrategy(ExactReadingSearchStrategy):
    """
    Simple reading search strategy. Converts search string to dictionary reading
    and separates entities by space.
    """
    def __init__(self):
        super(SimpleReadingSearchStrategy, self).__init__()
        self._getReadingsOptions = None
        self._decompEntities = None

    def setReadingFactory(self, readingFactory):
        """
        Sets the reading factory. This method is called by the
        dictionary object.

        @type readingFactory: instance
        @param readingFactory: L{ReadingFactory} instance
        """
        self._readingFactory = readingFactory

    def _getReadings(self, readingStr, fromReading, **options):
        if self._getReadingsOptions != (readingStr, fromReading, options):
            self._getReadingsOptions = (readingStr, fromReading, options)

            decompEntities = []
            try:
                decompositions = self._readingFactory.getDecompositions(
                    readingStr, fromReading, **options)
                # convert all possible decompositions
                e = None
                for entities in decompositions:
                    try:
                        decompEntities.append(
                            self._readingFactory.convertEntities(entities,
                                fromReading, self._dictInstance.READING,
                                sourceOptions=options,
                                targetOptions=\
                                    self._dictInstance.READING_OPTIONS))
                    except exception.ConversionError, e:
                        # TODO get strict mode, fail on any error
                        pass

            except exception.DecompositionError:
                raise exception.ConversionError(
                    "Decomposition failed for '%s'." % readingStr)

            self._decompEntities = [[entity for entity in entities
                if entity.strip()] for entities in decompEntities]

        if not self._decompEntities:
            raise exception.ConversionError("Conversion failed for '%s'."
                % readingStr \
                + " No decomposition could be converted. Last error: '%s'" \
                    % e)

        return self._decompEntities

    def getWhereClause(self, readingStr, fromReading, **options):
        dictionaryTable = self._dictInstance.db.tables[
            self._dictInstance.DICTIONARY_TABLE]

        decompEntities = self._getReadings(readingStr, fromReading, **options)

        return or_(*[dictionaryTable.c.Reading == ' '.join(entities)
            for entities in decompEntities])


class TonelessReadingSearchStrategy(SimpleReadingSearchStrategy):
    """
    Reading based search strategy with support for missing tonal information.
    """
    def setReadingFactory(self, readingFactory):
        """
        Sets the reading factory. This method is called by the
        dictionary object.

        @type readingFactory: instance
        @param readingFactory: L{ReadingFactory} instance
        """
        self._readingFactory = readingFactory

    def getWhereClause(self, readingStr, fromReading, **options):
        def getWildcardForms(decompEntities):
            """Adds wildcards to account for missing tone information."""
            wildcardEntities = []
            for entities in decompEntities:
                newEntities = []
                for entity in entities:
                    if self._readingFactory.isReadingEntity(entity, fromReading,
                        **options):
                        plainEntity, tone \
                            = self._readingFactory.splitEntityTone(entity,
                                fromReading, **options)
                        if tone is None:
                            entity = '%s_' % plainEntity
                    newEntities.append(entity)
                wildcardEntities.append(newEntities)

            return wildcardEntities

        dictionaryTable = self._dictInstance.db.tables[
            self._dictInstance.DICTIONARY_TABLE]

        decompEntities = self._getReadings(readingStr, fromReading, **options)

        # if reading is tonal and includes support for missing tones, handle
        if (self._readingFactory.isReadingOperationSupported(
            'splitEntityTone', fromReading, **options)
            and self._readingFactory.isReadingOperationSupported('getTones',
                fromReading, **options)
            and None in self._readingFactory.getTones(fromReading, **options)):
            # look for missing tone information and use wildcards
            searchEntities = getWildcardForms(decompEntities)

            whereClause = or_(
                *[dictionaryTable.c.Reading.like(' '.join(entities))
                    for entities in searchEntities])
        else:
            whereClause = or_(
                *[dictionaryTable.c.Reading == ' '.join(entities)
                    for entities in decompEntities])

        return whereClause

    def getMatchFunction(self, readingStr, fromReading, **options):
        def getTonalForms(decompEntities):
            """
            Gets all tonal reading strings for decompositions with missing tone
            information.
            """
            formsSet = set()
            for entities in decompEntities:
                newEntities = []
                for entity in entities:
                    entityList = [entity]
                    if self._readingFactory.isReadingEntity(entity, fromReading,
                        **options):
                        plainEntity, tone \
                            = self._readingFactory.splitEntityTone(entity,
                                fromReading, **options)
                        if tone is None:
                            entityList = getTonalEntities(plainEntity)
                    newEntities.append(entityList)

                # build cross product of tonal entities
                formsSet.update([' '.join(entities) for entities
                    in cross(*newEntities)])

            return formsSet

        def getTonalEntities(plainEntity):
            """Gets all tonal forms for a given plain entity."""
            tonalEntities = []
            tones = self._readingFactory.getTones(
                fromReading, **options)
            for tone in tones:
                try:
                    tonalEntities.append(
                        self._readingFactory.getTonalEntity(plainEntity,
                            tone, fromReading, **options))
                except exception.InvalidEntityError:
                    pass
            return tonalEntities

        decompEntities = self._getReadings(readingStr, fromReading,
            **options)

        # if reading is tonal and includes support for missing tones, handle
        if (self._readingFactory.isReadingOperationSupported(
            'splitEntityTone', fromReading, **options)
            and self._readingFactory.isReadingOperationSupported(
                'getTones', fromReading, **options)
            and None in self._readingFactory.getTones(fromReading,
                **options)):
            # look for missing tone information and generate all forms
            matchSet = getTonalForms(decompEntities)
        else:
            matchSet = set([' '.join(entities)
                for entities in decompEntities])

        return lambda reading: reading in matchSet

#}
#{ Dictionary classes

class BaseDictionary(object):
    """
    Base dictionary access class. Needs to be implemented by child classes.
    """
    PROVIDES = None
    """Name of dictionary that is provided by this class."""

    def __init__(self, entryFactory=None, readingFormatStrategy=None,
        translationFormatStrategy=None, readingSearchStrategy=None,
        translationSearchStrategy=None, databaseUrl=None, dbConnectInst=None):
        """
        Initialises the BaseDictionary instance.

        @type entryFactory: instance
        @param entryFactory: entry factory instance
        @type readingFormatStrategy: instance
        @param readingFormatStrategy: reading formatting strategy instance
        @type translationFormatStrategy: instance
        @param translationFormatStrategy: translation formatting strategy
            instance
        @type readingSearchStrategy: instance
        @param readingSearchStrategy: reading search strategy instance
        @type translationSearchStrategy: instance
        @param translationSearchStrategy: translation search strategy instance
        @type databaseUrl: str
        @param databaseUrl: database connection setting in the format
            C{driver://user:pass@host/database}.
        @type dbConnectInst: instance
        @param dbConnectInst: instance of a L{DatabaseConnector}
        """
        # get connector to database
        if dbConnectInst:
            self.db = dbConnectInst
        else:
            self.db = DatabaseConnector.getDBConnector(databaseUrl)
            """L{DatabaseConnector} instance"""

        if entryFactory:
            self.entryFactory = entryFactory
        else:
            self.entryFactory = ListEntryFactory()
            """Factory for formatting row entries."""

        if readingFormatStrategy:
            self.readingFormatStrategy = readingFormatStrategy
        else:
            self.readingFormatStrategy = PlainReadingStrategy()
            """Strategy for formatting readings."""

        if translationFormatStrategy:
            self.translationFormatStrategy = translationFormatStrategy
        else:
            self.translationFormatStrategy = PlainTranslationStrategy()
            """Strategy for formatting translations."""

        if readingSearchStrategy:
            self.readingSearchStrategy = readingSearchStrategy
        else:
            self.readingSearchStrategy = ExactReadingSearchStrategy()
            """Strategy for searching readings."""
        self.readingSearchStrategy.setDictionaryInstance(self)

        if translationSearchStrategy:
            self.translationSearchStrategy = translationSearchStrategy
        else:
            self.translationSearchStrategy = ExactTranslationSearchStrategy()
            """Strategy for searching translations."""
        self.translationSearchStrategy.setDictionaryInstance(self)

    @staticmethod
    def getDictionaryClasses():
        """
        Gets all classes in module that implement L{BaseDictionary}.

        @rtype: set
        @return: list of all classes inheriting form L{BaseDictionary}
        """
        dictionaryModule = __import__("cjklib.dictionary")
        # get all classes that inherit from BaseDictionary
        return set([clss \
            for clss in dictionaryModule.dictionary.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, dictionaryModule.dictionary.BaseDictionary) \
            and clss.PROVIDES])

    @staticmethod
    def getAvailableDictionaries(dbConnectInst):
        """
        Returns a list of available dictionaries for the given database
        connection.

        @type dbConnectInst: instance
        @param dbConnectInst: instance of a L{DatabaseConnector}
        @rtype: list of class
        @return: list of dictionary class objects
        """
        available = []
        for dictionaryClass in BaseDictionary.getDictionaryClasses():
            if dictionaryClass.available(dbConnectInst):
                available.append(dictionaryClass)

        return available

    @classmethod
    def available(cls, dbConnectInst):
        """
        Returns C{True} if the dictionary is available for the given database
        connection.

        @type dbConnectInst: instance
        @param dbConnectInst: instance of a L{DatabaseConnector}
        @rtype: bool
        @return: C{True} if the database exists, C{False} otherwise.
        """
        raise NotImplementedError()


class EDICTStyleDictionary(BaseDictionary):
    """Access for EDICT-style dictionaries."""
    DICTIONARY_TABLE = None
    COLUMNS = ['Headword', 'Reading', 'Translation']

    def __init__(self, entryFactory=None, readingFormatStrategy=None,
        translationFormatStrategy=None, readingSearchStrategy=None,
        translationSearchStrategy=None, databaseUrl=None, dbConnectInst=None):
        if not translationSearchStrategy:
            translationSearchStrategy = SimpleTranslationSearchStrategy()
        super(EDICTStyleDictionary, self).__init__(entryFactory,
            readingFormatStrategy, translationFormatStrategy,
            readingSearchStrategy, translationSearchStrategy, databaseUrl,
            dbConnectInst)

        if hasattr(self.entryFactory, 'setColumnNames'):
            self.entryFactory.setColumnNames(self.COLUMNS)

        if not self.available(self.db):
            raise ValueError("Table '%s' for dictionary does not exist"
                % self.DICTIONARY_TABLE)

    @classmethod
    def available(cls, dbConnectInst):
        return (cls.DICTIONARY_TABLE
            and dbConnectInst.has_table(cls.DICTIONARY_TABLE))

    def _search(self, whereClause, orderBy, limit, filterResult=None):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        if orderBy is None:
            orderBy = []

        # lookup in db
        results = self.db.selectRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderBy).limit(limit))

        # filter
        if filterResult:
            results = [row for row in results if filterResult(*row)]

        # format readings
        results = [(headword, self.readingFormatStrategy.getReading(reading),
            translation) for headword, reading, translation in results]

        # format translations
        results = [(headword, reading,
            self.translationFormatStrategy.getTranslation(translation))
            for headword, reading, translation in results]

        # format results
        entries = self.entryFactory.getEntries(results)

        return entries

    def getAll(self, limit=None, orderBy=None):
        return self._search(None, limit, orderBy)

    def getForHeadword(self, headword, limit=None, orderBy=None):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        return self._search(dictionaryTable.c.Headword == headword,
            limit, orderBy)

    def getForReading(self, readingStr, limit=None, orderBy=None):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        return self._search(dictionaryTable.c.Reading == readingStr,
            limit, orderBy)

    def getForTranslation(self, translationStr, limit=None, orderBy=None):
        def filterResult(headword, reading, translation):
            return isMatch(translation)

        isMatch = self.translationSearchStrategy.getMatchFunction(
            translationStr)

        return self._search(
            self.translationSearchStrategy.getWhereClause(translationStr),
            limit, orderBy, filterResult)

    def getFor(self, searchStr, limit=None, orderBy=None):
        def filterResult(headword, reading, translation):
            if searchStr == headword:
                return True
            elif searchStr == reading:
                return True
            elif translationClause and isMatch(translation):
                return True
            else:
                return False

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        # headword
        clauses.append(dictionaryTable.c.Headword == searchStr)
        # reading
        clauses.append(dictionaryTable.c.Reading == searchStr)
        # translation
        translationClause = self.translationSearchStrategy.getWhereClause(
            searchStr)
        if translationClause:
            clauses.append(translationClause)
            isMatch = self.translationSearchStrategy.getMatchFunction(searchStr)

        return self._search(or_(*clauses), limit, orderBy, filterResult)


class EDICT(EDICTStyleDictionary):
    """
    EDICT dictionary access.

    @see: L{EDICTBuilder}
    """
    PROVIDES = 'EDICT'
    DICTIONARY_TABLE = 'EDICT'


class EDICTStyleEnhancedReadingDictionary(EDICTStyleDictionary):
    u"""
    Access for EDICT-style dictionaries with enhanced reading support.

    The EDICTStyleEnhancedReadingDictionary dictionary class extends L{EDICT}
    by:
        - support for reading conversion, understanding reading format strategy
          L{ReadingConversionStrategy},
        - flexible searching for reading strings.
    """
    READING = None
    """Reading."""
    READING_OPTIONS = {}
    """Options for reading of dictionary entries."""

    def __init__(self, entryFactory=None, readingFormatStrategy=None,
        translationFormatStrategy=None, readingSearchStrategy=None,
        translationSearchStrategy=None, databaseUrl=None, dbConnectInst=None):
        if not readingFormatStrategy:
            readingFormatStrategy = ReadingConversionStrategy()
        if not readingSearchStrategy:
            readingSearchStrategy = SimpleReadingSearchStrategy()
        super(EDICTStyleEnhancedReadingDictionary, self).__init__(entryFactory,
            readingFormatStrategy, translationFormatStrategy,
            readingSearchStrategy, translationSearchStrategy, databaseUrl,
            dbConnectInst)

        self._readingFactory = reading.ReadingFactory(dbConnectInst=self.db)

        if hasattr(self.readingFormatStrategy, 'setReadingFactory'):
            self.readingFormatStrategy.setReadingFactory(self._readingFactory)
        if hasattr(self.readingFormatStrategy, 'setReadingOptions'):
            self.readingFormatStrategy.setReadingOptions(self.READING,
                self.READING_OPTIONS)

        if hasattr(self.readingSearchStrategy, 'setReadingFactory'):
            self.readingSearchStrategy.setReadingFactory(self._readingFactory)

    def getForReading(self, readingStr, fromReading=None, **options):
        # TODO document: raises conversion error
        def filterResult(headword, reading, translation):
            return isMatch(reading)

        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        if not fromReading:
            fromReading = self.READING

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        readingClause = self.readingSearchStrategy.getWhereClause(readingStr,
            fromReading, **options)
        isMatch = self.readingSearchStrategy.getMatchFunction(readingStr,
            fromReading, **options)

        return self._search(readingClause, limit, orderBy, filterResult)

    def getFor(self, searchStr, **options):
        def filterResult(headword, reading, translation):
            if searchStr == headword:
                return True
            elif readingClause and isReadingMatch(reading):
                return True
            elif translationClause and isTranslationMatch(translation):
                return True
            else:
                return False

        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        fromReading = options.pop('fromReading', self.READING)

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        # headword
        clauses.append(dictionaryTable.c.Headword == searchStr)
        # reading
        readingClause = None
        try:
            readingClause = self.readingSearchStrategy.getWhereClause(
                searchStr, fromReading, **options)
            clauses.append(readingClause)
        except ConversionError:
            pass
        if readingClause:
            isReadingMatch = self.readingSearchStrategy.getMatchFunction(
                searchStr, fromReading, **options)
        # translation
        translationClause = self.translationSearchStrategy.getWhereClause(
            searchStr)
        if translationClause:
            clauses.append(translationClause)
            isTranslationMatch \
                = self.translationSearchStrategy.getMatchFunction(searchStr)

        return self._search(or_(*clauses), limit, orderBy, filterResult)


class CEDICTGR(EDICTStyleEnhancedReadingDictionary):
    """
    CEDICT-GR dictionary access.

    @see: L{CEDICTGRBuilder}
    """
    PROVIDES = 'CEDICTGR'
    READING = 'GR'
    DICTIONARY_TABLE = 'CEDICTGR'


class CEDICT(EDICTStyleEnhancedReadingDictionary):
    u"""
    CEDICT dictionary access.

    Example
    =======

    Get dictionary entries with reading IPA:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(entryFactory=DictEntryFactory(),
        ...     readingFormatStrategy=ReadingConversionStrategy('MandarinIPA'))
        >>> print ', '.join([l['Reading'] for l in d.getForHeadword(u'行')])
        xaŋ˧˥, ɕiŋ˧˥, ɕiŋ˥˩

    @see: L{CEDICTBuilder}
    """
    PROVIDES = 'CEDICT'
    DICTIONARY_TABLE = 'CEDICT'
    COLUMNS = ['HeadwordSimplified', 'HeadwordTraditional', 'Reading',
        'Translation']

    READING = 'Pinyin'
    READING_OPTIONS = {'toneMarkType': 'numbers'}

    def __init__(self, entryFactory=None, readingFormatStrategy=None,
        translationFormatStrategy=None, readingSearchStrategy=None,
        translationSearchStrategy=None, databaseUrl=None, dbConnectInst=None,
        headword='b'):
        """
        Initialises the CEDICT instance. By default the both, simplified and
        traditional, headword forms are used for lookup.

        @type entryFactory: instance
        @param entryFactory: entry factory instance
        @type readingFormatStrategy: instance
        @param readingFormatStrategy: reading formatting strategy instance
        @type translationFormatStrategy: instance
        @param translationFormatStrategy: translation formatting strategy
            instance
        @type readingSearchStrategy: instance
        @param readingSearchStrategy: reading search strategy instance
        @type translationSearchStrategy: instance
        @param translationSearchStrategy: translation search strategy instance
        @type databaseUrl: str
        @param databaseUrl: database connection setting in the format
            C{driver://user:pass@host/database}.
        @type dbConnectInst: instance
        @param dbConnectInst: instance of a L{DatabaseConnector}
        @type headword: str
        @param headword: C{'s'} if the simplified headword is used as default,
            C{'t'} if the traditional headword is used as default, C{'b'} if
            both are tried.
        """
        super(CEDICT, self).__init__(entryFactory, readingFormatStrategy,
            translationFormatStrategy, readingSearchStrategy,
            translationSearchStrategy, databaseUrl, dbConnectInst)

        if headword in ('s', 't', 'b'):
            self.headword = headword
        else:
            raise ValueError("Invalid type for headword '%s'."
                % headword \
                + " Allowed values 's'implified, 't'raditional, or 'b'oth")

    def _search(self, whereClause, orderBy, limit, filterResult=None):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        if orderBy is None:
            orderBy = []

        # lookup in db
        results = self.db.selectRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderBy).limit(limit))

        # filter
        if filterResult:
            results = [row for row in results if filterResult(*row)]

        # format readings
        results = [(headwordSimplified, headwordTraditional,
            self.readingFormatStrategy.getReading(reading), translation)
            for headwordSimplified, headwordTraditional, reading, translation
            in results]

        # format translations
        results = [(headwordSimplified, headwordTraditional,
            reading, self.translationFormatStrategy.getTranslation(translation))
            for headwordSimplified, headwordTraditional, reading, translation
            in results]

        # format results
        entries = self.entryFactory.getEntries(results)

        return entries

    def getForHeadword(self, headword, limit=None, orderBy=None):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        if self.headword == 's':
            whereClause = dictionaryTable.c.HeadwordSimplified == headword
        elif self.headword == 't':
            whereClause = dictionaryTable.c.HeadwordTraditional == headword
        else:
            whereClause = or_(dictionaryTable.c.HeadwordSimplified == headword,
                dictionaryTable.c.HeadwordTraditional == headword)

        return self._search(whereClause, limit, orderBy)

    def getForTranslation(self, translationStr, limit=None, orderBy=None):
        def filterResult(headwordS, headwordT, reading, translation):
            return isMatch(translation)

        isMatch = self.translationSearchStrategy.getMatchFunction(
            translationStr)

        return self._search(
            self.translationSearchStrategy.getWhereClause(translationStr),
            limit, orderBy, filterResult)

    def getForReading(self, readingStr, fromReading=None, **options):
        # raises conversion error
        def filterResult(headwordS, headwordT, reading, translation):
            return isMatch(reading)

        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        if not fromReading:
            fromReading = self.READING

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        readingClause = self.readingSearchStrategy.getWhereClause(readingStr,
            fromReading, **options)
        isMatch = self.readingSearchStrategy.getMatchFunction(readingStr,
            fromReading, **options)

        return self._search(readingClause, limit, orderBy, filterResult)

    def getFor(self, searchStr, **options):
        def filterResult(headwordS, headwordT, reading, translation):
            if self.headword != 't' and searchStr == headwordS:
                return True
            elif self.headword != 's' and searchStr == headwordT:
                return True
            elif readingClause and isReadingMatch(reading):
                return True
            elif translationClause and isTranslationMatch(translation):
                return True
            else:
                return False

        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        fromReading = options.pop('fromReading', self.READING)

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        # headword
        if self.headword == 's':
            headwordClause = dictionaryTable.c.HeadwordSimplified == searchStr
        elif self.headword == 't':
            headwordClause = dictionaryTable.c.HeadwordTraditional == searchStr
        else:
            headwordClause = or_(
                dictionaryTable.c.HeadwordSimplified == searchStr,
                dictionaryTable.c.HeadwordTraditional == searchStr)
        clauses.append(headwordClause)
        # reading
        readingClause = None
        try:
            readingClause = self.readingSearchStrategy.getWhereClause(
                searchStr, fromReading, **options)
            clauses.append(readingClause)
        except ConversionError:
            pass
        if readingClause:
            isReadingMatch = self.readingSearchStrategy.getMatchFunction(
                searchStr, fromReading, **options)
        # translation
        translationClause = self.translationSearchStrategy.getWhereClause(
            searchStr)
        if translationClause:
            clauses.append(translationClause)
            isTranslationMatch \
                = self.translationSearchStrategy.getMatchFunction(searchStr)

        return self._search(or_(*clauses), limit, orderBy, filterResult)


class HanDeDict(CEDICT):
    """
    HanDeDict dictionary access.

    @see: L{HanDeDictBuilder}
    """
    PROVIDES = 'HanDeDict'
    DICTIONARY_TABLE = 'HanDeDict'

    def __init__(self, entryFactory=None,
        readingFormatStrategy=None, translationFormatStrategy=None,
        readingSearchStrategy=None, translationSearchStrategy=None,
        databaseUrl=None, dbConnectInst=None, headword='b'):
        if not translationSearchStrategy:
            translationSearchStrategy = HanDeDictTranslationSearchStrategy()
        super(HanDeDict, self).__init__(entryFactory, readingFormatStrategy,
            translationFormatStrategy, readingSearchStrategy,
            translationSearchStrategy, databaseUrl, dbConnectInst, headword)


class CFDICT(CEDICT):
    """
    CFDICT dictionary access.

    @see: L{CFDICTBuilder}
    """
    PROVIDES = 'CFDICT'
    DICTIONARY_TABLE = 'CFDICT'

