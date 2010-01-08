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

Translation search strategies
-----------------------------
Searching in natural language data is a difficult process and highly depends on
the use case at hand. One popular way is using stemming algorithms for copying
with inflections by reducing a word to its root form. Here, a basic search
strategy is given for each dictionary. More complex ones can be implemented on
the basis of extending the underlying table, e.g. using I{full text search}
capabilities of the database server.

Examples
========
- Create a dictionary instance:

    >>> from cjklib.dictionary import *
    >>> d = CEDICT(entryFactory=DictEntryFactory())

- Get dictionary entries by reading:

    >>> [l['HeadwordSimplified'] for l in \\
    ...     d.getForReading('po1', 'Pinyin', **{'toneMarkType': 'numbers'})]
    [u'\u5761', u'\u6cfc', u'\u948b', u'\u9642', u'\u9887']
"""

import re
import types

from sqlalchemy import select
from sqlalchemy.sql import or_

from cjklib import reading
from cjklib.dbconnector import DatabaseConnector
from cjklib import exception

#{ Entry factories

class ListEntryFactory(object):
    """Default entry factory, returning a list of columns."""
    def getEntries(self, results):
        return results


class DictEntryFactory(object):
    """
    Dict entry factory, returning a dict with keys as given by the dictionary.
    """
    def setColumnNames(self,columnNames):
        self.columnNames = columnNames

    def getEntries(self, results):
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
        return plainReading


class ReadingConversionStrategy(object):
    """Converts the entries' reading string to the given target reading."""
    def __init__(self, toReading=None, targetOptions=None):
        self.toReading = toReading
        if targetOptions:
            self.targetOptions = targetOptions
        else:
            self.targetOptions = {}

    def setReadingFactory(self, readingFactory):
        self._readingFactory = readingFactory

    def setReadingOptions(self, fromReading, sourceOptions):
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
        Returns a SQLAlchemy clause that is necessary condition for a possible
        match. This clause is used in the database query.

        @type searchStr: str
        @param searchStr: search string
        @return: SQLAlchemy clause
        """
        dictionaryTable = self._dictInstance.db.tables[
            self._dictInstance.DICTIONARY_TABLE]
        return dictionaryTable.c.Translation.like('%' + searchStr + '%')

    def isMatch(self, searchStr, translation):
        """
        Returns true if the entry's translation matches the search string. This
        method provides the sufficient condition for a match.

        @type searchStr: str
        @param searchStr: search string
        @type translation: str
        @param translation: entry's translation
        @rtype: bool
        @return: C{True} if the entry is a match
        """
        return searchStr in translation.split('/')


class SimpleTranslationSearchStrategy(ExactTranslationSearchStrategy):
    """
    Simple translation based search strategy. Takes into account additions put
    in parentheses.
    """
    def __init__(self):
        self._lastSearchStr = None
        self._regex = None

    def isMatch(self, searchStr, translation):
        if self._lastSearchStr != searchStr:
            self._lastSearchStr = searchStr
            self._regex = re.compile('[/\,\;\.\?\!]' + '(\s+|\([^\)]+\))*'
                + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '[/\,\;\.\?\!]')
        return self._regex.search(translation) is not None


class HanDeDictTranslationSearchStrategy(SimpleTranslationSearchStrategy):
    """HanDeDict translation based search strategy."""
    def isMatch(self, searchStr, translation):
        if self._lastSearchStr != searchStr:
            self._lastSearchStr = searchStr
            self._regex = re.compile('(?!; Bsp.: [^/]+?--[^/]+)'
                + '[/\,\;\.\?\!]' + '(\s+|\([^\)]+\))*'
                + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '[/\,\;\.\?\!]')
        return self._regex.search(translation) is not None

#}
#{ Dictionary classes

class BaseDictionary(object):
    """
    Base dictionary access class. Needs to be implemented by child classes.
    """
    PROVIDES = None
    """Name of dictionary that is provided by this class."""

    def __init__(self, entryFactory=None, readingFormatStrategy=None,
        translationFormatStrategy=None, translationSearchStrategy=None,
        databaseUrl=None, dbConnectInst=None):
        """
        Initialises the BaseDictionary instance.

        @type entryFactory: instance
        @param entryFactory: entry factory instance
        @type readingFormatStrategy: instance
        @param readingFormatStrategy: reading formatting strategy instance
        @type translationFormatStrategy: instance
        @param translationFormatStrategy: translation formatting strategy
            instance
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

        self._readingFactory = reading.ReadingFactory(dbConnectInst=self.db)

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
        if hasattr(self.readingFormatStrategy, 'setReadingFactory'):
            self.readingFormatStrategy.setReadingFactory(self._readingFactory)

        if translationFormatStrategy:
            self.translationFormatStrategy = translationFormatStrategy
        else:
            self.translationFormatStrategy = PlainTranslationStrategy()
            """Strategy for formatting translations."""

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
        available = []
        for dictionaryClass in BaseDictionary.getDictionaryClasses():
            if dictionaryClass.available(dbConnectInst):
                available.append(dictionaryClass)

        return available

    @classmethod
    def available(cls, dbConnectInst):
        raise NotImplementedError()


class EDICTStyleDictionary(BaseDictionary):
    """
    EDICT dictionary access.

    @see: L{EDICTBuilder}
    """
    DICTIONARY_TABLE = None
    COLUMNS = ['Headword', 'Reading', 'Translation']

    def __init__(self, entryFactory=None, readingFormatStrategy=None,
        translationFormatStrategy=None, translationSearchStrategy=None,
        databaseUrl=None, dbConnectInst=None):
        super(EDICTStyleDictionary, self).__init__(entryFactory,
            readingFormatStrategy, translationFormatStrategy,
            translationSearchStrategy, databaseUrl, dbConnectInst)

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
            return self.translationSearchStrategy.isMatch(translationStr,
                translation)

        return self._search(
            self.translationSearchStrategy.getWhereClause(translationStr),
            limit, orderBy, filterResult)

    def getFor(self, searchStr, limit=None, orderBy=None):
        def filterResult(headword, reading, translation):
            if searchStr == headword:
                return True
            elif searchStr == reading:
                return True
            else:
                return self.translationSearchStrategy.isMatch(searchStr,
                    translation)

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
    EDICT dictionary access with enhanced reading support.

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
        translationFormatStrategy=None, translationSearchStrategy=None,
        databaseUrl=None, dbConnectInst=None):
        if not readingFormatStrategy:
            readingFormatStrategy = ReadingConversionStrategy()
        super(EDICTStyleEnhancedReadingDictionary, self).__init__(entryFactory,
            readingFormatStrategy, translationFormatStrategy,
            translationSearchStrategy, databaseUrl, dbConnectInst)

        if hasattr(self.readingFormatStrategy, 'setReadingOptions'):
            self.readingFormatStrategy.setReadingOptions(self.READING,
                self.READING_OPTIONS)

    def _getReadingStrings(self, readingStr, fromReading, **options):
        decompositions = self._readingFactory.getDecompositions(readingStr,
            fromReading, **options)
        # convert all possible decompositions
        decompEntities = []
        e = None
        for entities in decompositions:
            try:
                decompEntities.append(
                    self._readingFactory.convertEntities(entities,
                        fromReading, self.READING, sourceOptions=options,
                        targetOptions=self.READING_OPTIONS))
            except exception.ConversionError, e:
                # TODO get strict mode, fail on any error
                pass
        if not decompEntities:
            raise exception.ConversionError("Conversion failed for '%s'."
                % readingStr \
                + " No decomposition could be converted. Last error: '%s'" \
                    % e)

        strings = []
        for entities in decompEntities:
            strings.append(' '.join(
                [entity for entity in entities if entity.strip()]))
        return strings

    def getForReading(self, readingStr, fromReading=None, **options):
        # TODO support missing tones
        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        if not fromReading:
            fromReading = self.READING

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        readingStrings = self._getReadingStrings(readingStr, fromReading,
            **options)
        readingClause = or_(*[dictionaryTable.c.Reading == reading
            for reading in readingStrings])

        return self._search(readingClause, limit, orderBy)

    def getFor(self, searchStr, **options):
        def filterResult(headword, reading, translation):
            if searchStr == headword:
                return True
            elif fromReading and reading in readingStrings:
                return True
            else:
                return self.translationSearchStrategy.isMatch(searchStr,
                    translation)

        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        fromReading = options.pop('fromReading', self.READING)

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        # headword
        clauses.append(dictionaryTable.c.Headword == searchStr)
        # reading
        if fromReading:
            readingStrings = self._getReadingStrings(searchStr, fromReading,
                **options)
            readingClause = or_(*[dictionaryTable.c.Reading == reading
                for reading in readingStrings])
            clauses.append(readingClause)
        # translation
        translationClause = self.translationSearchStrategy.getWhereClause(
            searchStr)
        if translationClause:
            clauses.append(translationClause)

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

    def __init__(self, headword='s', entryFactory=None,
        readingFormatStrategy=None, translationFormatStrategy=None,
        translationSearchStrategy=None, databaseUrl=None, dbConnectInst=None):
        if not translationSearchStrategy:
            translationSearchStrategy = SimpleTranslationSearchStrategy()
        super(CEDICT, self).__init__(entryFactory, readingFormatStrategy,
            translationFormatStrategy, translationSearchStrategy, databaseUrl,
            dbConnectInst)

        if headword in ('s', 't'):
            self.headword = headword
        else:
            raise ValueError("Invalid type for headword '%s'."
                % headword \
                + " Needs to be either 's' (simplified) or 't' (traditional)")

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
        else:
            whereClause = dictionaryTable.c.HeadwordTraditional == headword

        return self._search(whereClause, limit, orderBy)

    def getForTranslation(self, translationStr, limit=None, orderBy=None):
        def filterResult(headwordS, headwordT, reading, translation):
            return self.translationSearchStrategy.isMatch(translationStr,
                translation)

        return self._search(
            self.translationSearchStrategy.getWhereClause(translationStr),
            limit, orderBy, filterResult)

    def getFor(self, searchStr, **options):
        def filterResult(headwordS, headwordT, reading, translation):
            if self.headword != 't' and searchStr == headwordS:
                return True
            elif self.headword != 's' and searchStr == headwordT:
                return True
            elif fromReading and reading in readingStrings:
                return True
            else:
                return self.translationSearchStrategy.isMatch(searchStr,
                    translation)

        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)
        fromReading = options.pop('fromReading', self.READING)

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        # headword
        if self.headword == 's':
            headwordClause = dictionaryTable.c.HeadwordSimplified == searchStr
        else:
            headwordClause = dictionaryTable.c.HeadwordTraditional == searchStr
        clauses.append(headwordClause)
        # reading
        if fromReading:
            readingStrings = self._getReadingStrings(searchStr, fromReading,
                **options)
            readingClause = or_(*[dictionaryTable.c.Reading == reading
                for reading in readingStrings])
            clauses.append(readingClause)
        # translation
        translationClause = self.translationSearchStrategy.getWhereClause(
            searchStr)
        if translationClause:
            clauses.append(translationClause)

        return self._search(or_(*clauses), limit, orderBy, filterResult)


class HanDeDict(CEDICT):
    """
    HanDeDict dictionary access.

    @see: L{HanDeDictBuilder}
    """
    PROVIDES = 'HanDeDict'
    DICTIONARY_TABLE = 'HanDeDict'

    def __init__(self, headword='s', entryFactory=None,
        readingFormatStrategy=None, translationFormatStrategy=None,
        translationSearchStrategy=None, databaseUrl=None, dbConnectInst=None):
        if not translationSearchStrategy:
            translationSearchStrategy = HanDeDictTranslationSearchStrategy()
        super(HanDeDict, self).__init__(headword, entryFactory,
            readingFormatStrategy, translationFormatStrategy,
            translationSearchStrategy, databaseUrl, dbConnectInst)


class CFDICT(CEDICT):
    """
    CFDICT dictionary access.

    @see: L{CFDICTBuilder}
    """
    PROVIDES = 'CFDICT'
    DICTIONARY_TABLE = 'CFDICT'

