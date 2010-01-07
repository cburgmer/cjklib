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
#{ Reading formatting factories

class PlainReadingFactory(object):
    """Default reading formatting factory, doing nothing."""
    def getReading(self, plainReading):
        return plainReading


class ReadingConversionFactory(object):
    """Converts the entries' reading string to the given target reading."""
    def __init__(self, toReading, targetOptions=None):
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
            raise ValueError('Factory not initialized properly.'
                ' Probably incompatible to dictionary.')

        try:
            return self._readingFactory.convert(plainReading, self.fromReading,
                self.toReading, sourceOptions=self.sourceOptions,
                targetOptions=self.targetOptions)
        except (exception.DecompositionError, exception.CompositionError,
            exception.ConversionError):
            return None


class StandardPinyinReadingFactory(ReadingConversionFactory):
    """Converts the entries' reading string to standard I{Pinyin}."""
    def __init__(self):
        super(StandardPinyinReadingFactory, self).__init__('Pinyin')

#}
#{ Translation formatting factories

class PlainTranslationFactory(object):
    """Default translation formatting factory, doing nothing."""
    def getTranslation(self, plainTranslation):
        return plainTranslation

#}
#{ Dictionary classes

class BaseDictionary(object):
    """
    Base dictionary access class. Needs to be implemented by child classes.
    """
    def __init__(self, entryFactory=None, readingFormatFactory=None,
        translationFormatFactory=None, databaseUrl=None, dbConnectInst=None):
        """
        Initialises the BaseDictionary instance.

        @type entryFactory: instance
        @param entryFactory: entry factory instance
        @type readingFormatFactory: instance
        @param readingFormatFactory: reading formatting factory instance
        @type translationFormatFactory: instance
        @param translationFormatFactory: translation formatting factory instance
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
            """Factory for formatting row entry."""

        if readingFormatFactory:
            self.readingFormatFactory = readingFormatFactory
        else:
            self.readingFormatFactory = PlainReadingFactory()
            """Factory for formatting reading."""
        if hasattr(self.readingFormatFactory, 'setReadingFactory'):
            self.readingFormatFactory.setReadingFactory(self._readingFactory)

        if translationFormatFactory:
            self.translationFormatFactory = translationFormatFactory
        else:
            self.translationFormatFactory = PlainTranslationFactory()
            """Factory for formatting translation."""


class EDICT(BaseDictionary):
    """
    EDICT dictionary access.

    @see: L{EDICTBuilder}
    """

    DICTIONARY_TABLE = 'EDICT'
    COLUMNS = ['Headword', 'Reading', 'Translation']

    def __init__(self, entryFactory=None, readingFormatFactory=None,
        translationFormatFactory=None, databaseUrl=None, dbConnectInst=None):
        super(EDICT, self).__init__(entryFactory, readingFormatFactory,
            translationFormatFactory, databaseUrl, dbConnectInst)

        if hasattr(self.entryFactory, 'setColumnNames'):
            self.entryFactory.setColumnNames(self.COLUMNS)

        if not self.db.has_table(self.DICTIONARY_TABLE):
            raise ValueError("Table '%s' for dictionary does not exist"
                % self.DICTIONARY_TABLE)

    def _search(self, whereClause, orderBy, limit):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        if orderBy is None:
            orderBy = []

        # lookup in db
        results = self.db.selectRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderBy).limit(limit))

        # format readings
        results = [(headword, self.readingFormatFactory.getReading(reading),
            translation) for headword, reading, translation in results]

        # format translations
        results = [(headword, reading,
            self.translationFormatFactory.getTranslation(translation))
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


class CEDICT(EDICT):
    u"""
    CEDICT dictionary access.

    The CEDICT dictionary class extends L{EDICT} by:
        - support for reading conversion, understanding reading format factories
          L{ReadingConversionFactory} and more specifically
          L{StandardPinyinReadingFactory},
        - flexible searching for reading strings,
        - simplified and traditional headword for each entry.

    Example
    =======

    Get dictionary entries with reading IPA:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(entryFactory=DictEntryFactory(),
        ...     readingFormatFactory=ReadingConversionFactory('MandarinIPA'))
        >>> print ', '.join([l['Reading'] for l in d.getForHeadword(u'行')])
        xaŋ˧˥, ɕiŋ˧˥, ɕiŋ˥˩

    @see: L{CEDICTBuilder}
    """
    READING_OPTIONS = {'toneMarkType': 'numbers'}
    """Options for reading of dictionary entries."""

    DICTIONARY_TABLE = 'CEDICT'
    COLUMNS = ['HeadwordSimplified', 'HeadwordTraditional', 'Reading',
        'Translation']

    def __init__(self, headword='s', entryFactory=None,
        readingFormatFactory=None, translationFormatFactory=None,
        databaseUrl=None, dbConnectInst=None):
        if not readingFormatFactory:
            readingFormatFactory = StandardPinyinReadingFactory()
        super(CEDICT, self).__init__(entryFactory, readingFormatFactory,
            translationFormatFactory, databaseUrl, dbConnectInst)

        if hasattr(self.readingFormatFactory, 'setReadingOptions'):
            self.readingFormatFactory.setReadingOptions('Pinyin',
                self.READING_OPTIONS)

        if headword in ('s', 't'):
            self.headword = headword
        else:
            raise ValueError("Invalid type for headword '%s'."
                % headword \
                + " Needs to be either 's' (simplified) or 't' (traditional)")

    def _search(self, whereClause, orderBy, limit):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        if orderBy is None:
            orderBy = []

        # lookup in db
        results = self.db.selectRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderBy).limit(limit))

        # format readings
        results = [(headwordSimplified, headwordTraditional,
            self.readingFormatFactory.getReading(reading), translation)
            for headwordSimplified, headwordTraditional, reading, translation
            in results]

        # format translations
        results = [(headwordSimplified, headwordTraditional,
            reading, self.translationFormatFactory.getTranslation(translation))
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

    def _getReadingClause(self, readingStr, fromReading, **options):
        decompositions = self._readingFactory.getDecompositions(readingStr,
            fromReading, **options)
        # convert all possible decompositions
        decompEntities = []
        e = None
        for entities in decompositions:
            try:
                decompEntities.append(
                    self._readingFactory.convertEntities(entities,
                        fromReading, 'Pinyin', sourceOptions=options,
                        targetOptions=self.READING_OPTIONS))
            except exception.ConversionError, e:
                # TODO get strict mode, fail on any error
                pass
        if not decompEntities:
            raise exception.ConversionError("Conversion failed for '%s'."
                % readingStr \
                + " No decomposition could be converted. Last error: '%s'" \
                    % e)

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        for entities in decompEntities:
            clauses.append(dictionaryTable.c.Reading == ' '.join(
                [entity for entity in entities if entity.strip()]))
        return or_(*clauses)

    def getForReading(self, readingStr, fromReading, **options):
        # TODO support missing tones
        limit = options.pop('limit', None)
        orderBy = options.pop('orderBy', None)

        readingClause = self._getReadingClause(readingStr, fromReading,
            **options)
        return self._search(readingClause, limit, orderBy)


class CEDICTGR(CEDICT):
    """
    CEDICT-GR dictionary access.

    @see: L{CEDICTGRBuilder}
    """
    DICTIONARY_TABLE = 'CEDICTGR'


class HanDeDict(CEDICT):
    """
    HanDeDict dictionary access.

    @see: L{HanDeDictBuilder}
    """
    DICTIONARY_TABLE = 'HanDeDict'


class CFDICT(CEDICT):
    """
    CFDICT dictionary access.

    @see: L{CFDICTBuilder}
    """
    DICTIONARY_TABLE = 'CFDICT'

