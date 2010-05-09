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
High level dictionary access.

This module provides classes for easy access to well known CJK dictionaries.
Queries can be done using a headword, reading or translation.

Dictionary sources yield less structured information compared to other data
sources exposed in this library. Owing to this fact, a flexible system is
provided to the user.
"""

__all__ = [
    # plugin classes
    "entry", "format", "search",
    # access methods
    "getDictionaryClasses", "getAvailableDictionaries", "getDictionaryClass",
    "getDictionary",
    # base dictionary classes
    "BaseDictionary", "EDICTStyleDictionary",
    "EDICTStyleEnhancedReadingDictionary",
    # dictionaries
    "EDICT", "CEDICTGR", "CEDICT", "HanDeDict", "CFDICT"
    ]

import types
from itertools import imap, ifilter

from sqlalchemy import select, Table
from sqlalchemy.sql import or_
from sqlalchemy.exc import NoSuchTableError

from cjklib import dbconnector
from cjklib import exception
from cjklib.util import cachedproperty

from cjklib.dictionary import entry as entryfactory
from cjklib.dictionary import format as formatstrategy
from cjklib.dictionary import search as searchstrategy

#{ Access methods

def getDictionaryClasses():
    """
    Gets all classes in module that implement
    :class:`~cjklib.dictionary.BaseDictionary`.

    :rtype: set
    :return: list of all classes inheriting form
        :class:`~cjklib.dictionary.BaseDictionary`
    """
    dictionaryModule = __import__("cjklib.dictionary")
    # get all classes that inherit from BaseDictionary
    return set([clss \
        for clss in dictionaryModule.dictionary.__dict__.values() \
        if type(clss) == types.TypeType \
        and issubclass(clss, dictionaryModule.dictionary.BaseDictionary) \
        and clss.PROVIDES])

def getAvailableDictionaries(dbConnectInst=None):
    """
    Returns a list of available dictionaries for the given database
    connection.

    :type dbConnectInst: instance
    :param dbConnectInst: optional instance of a
        :class:`~cjklib.dbconnector.DatabaseConnector`
    :rtype: list of class
    :return: list of dictionary class objects
    """
    dbConnectInst = dbConnectInst or dbconnector.getDBConnector()
    available = []
    for dictionaryClass in getDictionaryClasses():
        if dictionaryClass.available(dbConnectInst):
            available.append(dictionaryClass)

    return available

_dictionaryMap = None
def getDictionaryClass(dictionaryName):
    """
    Get a dictionary class by dictionary name.

    :type dictionaryName: str
    :param dictionaryName: dictionary name
    :rtype: type
    :return: dictionary class
    """
    global _dictionaryMap
    if _dictionaryMap is None:
        _dictionaryMap = dict([(dictCls.PROVIDES, dictCls)
            for dictCls in getDictionaryClasses()])

    if dictionaryName not in _dictionaryMap:
        raise ValueError('Not a supported dictionary')
    return _dictionaryMap[dictionaryName]

def getDictionary(dictionaryName, **options):
    """
    Get a dictionary instance by dictionary name.

    :type dictionaryName: str
    :param dictionaryName: dictionary name
    :rtype: type
    :return: dictionary instance
    """
    dictCls = getDictionaryClass(dictionaryName)
    return dictCls(**options)

#}
#{ Dictionary classes

class BaseDictionary(object):
    """
    Base dictionary access class. Needs to be implemented by child classes.
    """
    PROVIDES = None
    """Name of dictionary that is provided by this class."""
    COLUMNS = None
    """Columns of the dictionary. Can be assigned a format strategy."""

    def __init__(self, **options):
        """
        Initialises the BaseDictionary instance.

        :keyword entryFactory: entry factory instance
        :keyword columnFormatStrategies: column formatting strategy instances
        :keyword headwordSearchStrategy: headword search strategy instance
        :keyword readingSearchStrategy: reading search strategy instance
        :keyword translationSearchStrategy: translation search strategy instance
        :keyword mixedReadingSearchStrategy: mixed reading search strategy
            instance
        :keyword databaseUrl: database connection setting in the format
            ``driver://user:pass@host/database``.
        :keyword dbConnectInst: instance of a :class:`~cjklib.dbconnector.DatabaseConnector`
        """
        # get connector to database
        if 'dbConnectInst' in options:
            self.db = options['dbConnectInst']
        else:
            databaseUrl = options.pop('databaseUrl', None)
            self.db = dbconnector.getDBConnector(databaseUrl)
            """:class:`~cjklib.dbconnector.DatabaseConnector` instance"""

        if 'entryFactory' in options:
            self.entryFactory = options['entryFactory']
        else:
            self.entryFactory = entryfactory.Tuple()
            """Factory for formatting row entries."""
        if hasattr(self.entryFactory, 'setDictionaryInstance'):
            self.entryFactory.setDictionaryInstance(self)

        columnFormatStrategies = options.get('columnFormatStrategies', {})
        self.setColumnFormatStrategies(columnFormatStrategies)

        if 'headwordSearchStrategy' in options:
            self.headwordSearchStrategy = options['headwordSearchStrategy']
        else:
            self.headwordSearchStrategy = searchstrategy.Wildcard()
            """Strategy for searching readings."""
        if hasattr(self.headwordSearchStrategy, 'setDictionaryInstance'):
            self.headwordSearchStrategy.setDictionaryInstance(self)

        if 'readingSearchStrategy' in options:
            self.readingSearchStrategy = options['readingSearchStrategy']
        else:
            self.readingSearchStrategy = searchstrategy.Wildcard()
            """Strategy for searching readings."""
        if hasattr(self.readingSearchStrategy, 'setDictionaryInstance'):
            self.readingSearchStrategy.setDictionaryInstance(self)

        self.mixedReadingSearchStrategy = options.get(
            'mixedReadingSearchStrategy', None)
        """Strategy for mixed searching of headword/reading."""
        if (self.mixedReadingSearchStrategy
            and hasattr(self.mixedReadingSearchStrategy,
                'setDictionaryInstance')):
            self.mixedReadingSearchStrategy.setDictionaryInstance(self)

        if 'translationSearchStrategy' in options:
            self.translationSearchStrategy \
                = options['translationSearchStrategy']
        else:
            self.translationSearchStrategy \
                = searchstrategy.WildcardTranslation()
            """Strategy for searching translations."""
        if hasattr(self.translationSearchStrategy, 'setDictionaryInstance'):
            self.translationSearchStrategy.setDictionaryInstance(self)

    def getSolumnFormatStrategies(self):
        """Strategies for formatting columns."""
        return self._columnFormatStrategies

    def setColumnFormatStrategies(self, columnFormatStrategies):
        # None is passed to overwrite a default formating
        for column in columnFormatStrategies.keys():
            if columnFormatStrategies[column] is None:
                del columnFormatStrategies[column]

        self._columnFormatStrategies = columnFormatStrategies
        self._formatStrategies = []
        if columnFormatStrategies:
            for strategy in columnFormatStrategies.values():
                if hasattr(strategy, 'setDictionaryInstance'):
                    strategy.setDictionaryInstance(self)

            fullRowStrategy = columnFormatStrategies.pop(None, None)
            for column, strategy in columnFormatStrategies.items():
                columnIdx = self.COLUMNS.index(column)

                self._formatStrategies.append(
                    formatstrategy.SingleColumnAdapter(strategy, columnIdx))
            if fullRowStrategy:
                self._formatStrategies.append(fullRowStrategy)

    columnFormatStrategies = property(getSolumnFormatStrategies,
        setColumnFormatStrategies)

    @classmethod
    def available(cls, dbConnectInst):
        """
        Returns ``True`` if the dictionary is available for the given database
        connection.

        :type dbConnectInst: instance
        :param dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`
        :rtype: bool
        :return: ``True`` if the database exists, ``False`` otherwise.
        """
        raise NotImplementedError()


class EDICTStyleDictionary(BaseDictionary):
    """Access for EDICT-style dictionaries."""
    DICTIONARY_TABLE = None
    """Name of dictionary table."""
    COLUMNS = ['Headword', 'Reading', 'Translation']
    """Columns of dictionary table."""
    READING = None
    """Reading."""
    READING_OPTIONS = {}
    """Options for reading of dictionary entries."""

    def __init__(self, **options):
        if 'entryFactory' not in options:
            options['entryFactory'] = entryfactory.NamedTuple()
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = searchstrategy.SimpleWildcardTranslation()
        super(EDICTStyleDictionary, self).__init__(**options)

        if not self.available(self.db):
            raise ValueError("Table '%s' for dictionary does not exist"
                % self.DICTIONARY_TABLE)

    @classmethod
    def available(cls, dbConnectInst):
        return (cls.DICTIONARY_TABLE
            and dbConnectInst.hasTable(cls.DICTIONARY_TABLE))

    @cachedproperty
    def version(self):
        """Version (date) of the dictionary. ``None`` if not available."""
        try:
            versionTable = Table('Version', self.db.metadata, autoload=True,
                autoload_with=self.db.engine,
                schema=self.db.tables[self.DICTIONARY_TABLE].schema)

            return self.db.selectScalar(select([versionTable.c.ReleaseDate],
                versionTable.c.TableName == self.DICTIONARY_TABLE))
        except NoSuchTableError:
            pass

    def _search(self, whereClause, filters, limit, orderBy):
        """
        Does the actual search for a given where clause and then narrows the
        result set given a list of filters. The results are then formatted
        given the instance's rules.
        """
        def _getFilterFunction(filterList):
            """Creates a function for filtering search results."""
            def anyFunc(row):
                for itemsIdx, function in functionList:
                    if function(*[row[idx] for idx in itemsIdx]):
                        return True
                return False

            functionList = []
            for columns, function in filterList:
                columnsIdx = [self.COLUMNS.index(column) for column in columns]
                functionList.append((columnsIdx, function))

            return anyFunc

        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        orderByCols = []
        if orderBy is not None:
            if type(orderBy) != type([]):
                orderBy = [orderBy]

            for col in orderBy:
                if isinstance(col, basestring):
                    orderByCols.append(dictionaryTable.c[col])
                else:
                    orderByCols.append(col)

        # lookup in db
        results = self.db.iterRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderByCols).limit(limit))

        # filter
        if filters:
            results = ifilter(_getFilterFunction(filters), results)

        # format readings and translations
        if self.columnFormatStrategies:
            results = imap(list, results)
            for strategy in self._formatStrategies:
                results = imap(strategy.format, results)
            results = imap(tuple, results)

        # format results
        entries = self.entryFactory.getEntries(results)

        return entries

    def getAll(self, limit=None, orderBy=None):
        """
        Get all dictionary entries.

        :type limit: int
        :param limit: limiting number of returned entries
        :type orderBy: list
        :param orderBy: list of column names or SQLAlchemy column objects giving
            the order of returned entries
        """
        return self._search(None, None, limit, orderBy)

    def _getHeadwordSearch(self, headwordStr, **options):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        headwordClause = self.headwordSearchStrategy.getWhereClause(
            dictionaryTable.c.Headword, headwordStr)

        headwordMatchFunc = self.headwordSearchStrategy.getMatchFunction(
            headwordStr)

        return [headwordClause], [(['Headword'], headwordMatchFunc)]

    def getForHeadword(self, headwordStr, limit=None, orderBy=None, **options):
        """
        Get dictionary entries whose headword matches the given string.

        :type limit: int
        :param limit: limiting number of returned entries
        :type orderBy: list
        :param orderBy: list of column names or SQLAlchemy column objects giving
            the order of returned entries

        .. todo::
            * bug: Specifying a ``limit`` might yield less results than
              possible.
        """
        clauses, filters = self._getHeadwordSearch(headwordStr)

        return self._search(or_(*clauses), filters, limit, orderBy)

    def _getReadingSearch(self, readingStr, **options):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        filters = []

        # reading search
        readingClause = self.readingSearchStrategy.getWhereClause(
            dictionaryTable.c.Reading, readingStr, **options)
        clauses.append(readingClause)

        readingMatchFunc = self.readingSearchStrategy.getMatchFunction(
            readingStr, **options)
        filters.append((['Reading'], readingMatchFunc))

        # mixed search
        if self.mixedReadingSearchStrategy:
            mixedClause = self.mixedReadingSearchStrategy.getWhereClause(
                dictionaryTable.c.Headword, dictionaryTable.c.Reading,
                readingStr, **options)
            if mixedClause:
                clauses.append(mixedClause)

                mixedReadingMatchFunc \
                    = self.mixedReadingSearchStrategy.getMatchFunction(
                        readingStr, **options)
                filters.append((['Headword', 'Reading'],
                    mixedReadingMatchFunc))

        return clauses, filters

    def getForReading(self, readingStr, limit=None, orderBy=None, **options):
        """
        Get dictionary entries whose reading matches the given string.

        :type limit: int
        :param limit: limiting number of returned entries
        :type orderBy: list
        :param orderBy: list of column names or SQLAlchemy column objects giving
            the order of returned entries
        :raise ConversionError: if search string cannot be converted to the
            dictionary's reading.

        .. todo::
            * bug: Specifying a ``limit`` might yield less results than
              possible.
        """
        clauses, filters = self._getReadingSearch(readingStr, **options)

        return self._search(or_(*clauses), filters, limit, orderBy)

    def _getTranslationSearch(self, translationStr, **options):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        translationClause = self.translationSearchStrategy.getWhereClause(
            dictionaryTable.c.Translation, translationStr)

        translationMatchFunc = self.translationSearchStrategy.getMatchFunction(
            translationStr)

        return [translationClause], [(['Translation'], translationMatchFunc)]

    def getForTranslation(self, translationStr, limit=None, orderBy=None,
        **options):
        """
        Get dictionary entries whose translation matches the given string.

        :type limit: int
        :param limit: limiting number of returned entries
        :type orderBy: list
        :param orderBy: list of column names or SQLAlchemy column objects giving
            the order of returned entries

        .. todo::
            * bug: Specifying a ``limit`` might yield less results than
              possible.
        """
        clauses, filters = self._getTranslationSearch(translationStr)

        return self._search(or_(*clauses), filters, limit, orderBy)

    def getFor(self, searchStr, limit=None, orderBy=None, **options):
        """
        Get dictionary entries whose headword, reading or translation matches
        the given string.

        :type limit: int
        :param limit: limiting number of returned entries
        :type orderBy: list
        :param orderBy: list of column names or SQLAlchemy column objects giving
            the order of returned entries

        .. todo::
            * bug: Specifying a ``limit`` might yield less results than
              possible.
        """
        clauseList = []
        filterList = []
        for searchFunc in (self._getHeadwordSearch, self._getReadingSearch,
            self._getTranslationSearch):
            try:
                clauses, filters =  searchFunc(searchStr, **options)
            except exception.ConversionError:
                pass
            clauseList.extend(clauses)
            filterList.extend(filters)

        return self._search(or_(*clauseList), filterList, limit, orderBy)


class EDICT(EDICTStyleDictionary):
    """
    EDICT dictionary access.

    .. seealso:: :class:`~cjklib.build.builder.EDICTBuilder`
    """
    PROVIDES = 'EDICT'
    READING = 'Kana'
    DICTIONARY_TABLE = 'EDICT'


class EDICTStyleEnhancedReadingDictionary(EDICTStyleDictionary):
    u"""
    Access for EDICT-style dictionaries with enhanced reading support.

    The EDICTStyleEnhancedReadingDictionary dictionary class extends
    :class:`cjklib.dictionary.EDICT` by:

    - support for reading conversion, understanding reading format strategy
        :class:`cjklib.dictionary.format.ReadingConversion`,
    - flexible searching for reading strings.
    """
    def __init__(self, **options):

        columnFormatStrategies = options.get('columnFormatStrategies', {})
        if 'Reading' not in columnFormatStrategies:
            columnFormatStrategies['Reading'] \
                = formatstrategy.ReadingConversion()
            options['columnFormatStrategies'] = columnFormatStrategies
        if 'readingSearchStrategy' not in options:
            options['readingSearchStrategy'] \
                = searchstrategy.SimpleWildcardReading()
        if 'mixedReadingSearchStrategy' not in options:
            options['mixedReadingSearchStrategy'] \
                = searchstrategy.MixedWildcardReading()
        super(EDICTStyleEnhancedReadingDictionary, self).__init__(**options)


class CEDICTGR(EDICTStyleEnhancedReadingDictionary):
    """
    CEDICT-GR dictionary access.

    .. seealso:: :class:`~cjklib.build.builder.CEDICTGRBuilder`
    """
    PROVIDES = 'CEDICTGR'
    READING = 'GR'
    DICTIONARY_TABLE = 'CEDICTGR'

    def __init__(self, **options):
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = searchstrategy.CEDICTWildcardTranslation()
        super(CEDICTGR, self).__init__(**options)


class CEDICT(EDICTStyleEnhancedReadingDictionary):
    u"""
    CEDICT dictionary access.

    .. seealso:: :class:`~cjklib.build.builder.CEDICTBuilder`
    """
    PROVIDES = 'CEDICT'
    DICTIONARY_TABLE = 'CEDICT'
    COLUMNS = ['HeadwordTraditional', 'HeadwordSimplified', 'Reading',
        'Translation']

    READING = 'Pinyin'
    READING_OPTIONS = {'toneMarkType': 'numbers', 'yVowel': 'u:'}

    def __init__(self, **options):
        """
        Initialises the CEDICT instance. By default the both, simplified and
        traditional, headword forms are used for lookup.

        :keyword entryFactory: entry factory instance
        :keyword columnFormatStrategies: column formatting strategy instances
        :keyword headwordSearchStrategy: headword search strategy instance
        :keyword readingSearchStrategy: reading search strategy instance
        :keyword translationSearchStrategy: translation search strategy instance
        :keyword mixedReadingSearchStrategy: mixed reading search strategy
            instance
        :keyword databaseUrl: database connection setting in the format
            ``driver://user:pass@host/database``.
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`
        :keyword headword: ``'s'`` if the simplified headword is used as
            default, ``'t'`` if the traditional headword is used as default,
            ``'b'`` if both are tried.
        """
        columnFormatStrategies = options.get('columnFormatStrategies', {})
        if None not in columnFormatStrategies:
            columnFormatStrategies[None] \
                = formatstrategy.NonReadingEntityWhitespace()
            options['columnFormatStrategies'] = columnFormatStrategies

        if 'headwordSearchStrategy' not in options:
            options['headwordSearchStrategy'] = searchstrategy.Wildcard(
                fullwidthCharacters=True)
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = searchstrategy.CEDICTWildcardTranslation()
        if 'readingSearchStrategy' not in options:
            options['readingSearchStrategy'] \
                = searchstrategy.TonelessWildcardReading()
        if 'mixedReadingSearchStrategy' not in options:
            options['mixedReadingSearchStrategy'] \
                = searchstrategy.MixedTonelessWildcardReading(
                    headwordFullwidthCharacters=True)
        super(CEDICT, self).__init__(**options)

        headword = options.get('headword', 'b')
        if headword in ('s', 't', 'b'):
            self.headword = headword
        else:
            raise ValueError("Invalid type for headword '%s'."
                % headword \
                + " Allowed values 's'implified, 't'raditional, or 'b'oth")

    def _getReadingSearch(self, readingStr, **options):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        filters = []

        # reading search
        readingClause = self.readingSearchStrategy.getWhereClause(
            dictionaryTable.c.Reading, readingStr, **options)
        clauses.append(readingClause)

        readingMatchFunc = self.readingSearchStrategy.getMatchFunction(
            readingStr, **options)
        filters.append((['Reading'], readingMatchFunc))

        # mixed search
        if self.mixedReadingSearchStrategy:
            mixedClauses = []
            if self.headword != 't':
                mixedClauseS = self.mixedReadingSearchStrategy.getWhereClause(
                    dictionaryTable.c.HeadwordSimplified,
                    dictionaryTable.c.Reading, readingStr, **options)
                if mixedClauseS: mixedClauses.append(mixedClauseS)
            if self.headword != 's':
                mixedClauseT = self.mixedReadingSearchStrategy.getWhereClause(
                    dictionaryTable.c.HeadwordTraditional,
                    dictionaryTable.c.Reading, readingStr, **options)
                if mixedClauseT: mixedClauses.append(mixedClauseT)

            if mixedClauses:
                clauses.extend(mixedClauses)
                mixedReadingMatchFunc \
                    = self.mixedReadingSearchStrategy.getMatchFunction(
                        readingStr, **options)
                if self.headword != 't':
                    filters.append((['HeadwordSimplified', 'Reading'],
                        mixedReadingMatchFunc))
                if self.headword != 's':
                    filters.append((['HeadwordTraditional', 'Reading'],
                        mixedReadingMatchFunc))

        return clauses, filters

    def _getHeadwordSearch(self, headwordStr, **options):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        clauses = []
        filters = []
        if self.headword != 't':
            clauses.append(self.headwordSearchStrategy.getWhereClause(
                dictionaryTable.c.HeadwordSimplified, headwordStr))
            filters.append((['HeadwordSimplified'],
                self.headwordSearchStrategy.getMatchFunction(headwordStr)))
        if self.headword != 's':
            clauses.append(self.headwordSearchStrategy.getWhereClause(
                dictionaryTable.c.HeadwordTraditional, headwordStr))
            filters.append((['HeadwordTraditional'],
                self.headwordSearchStrategy.getMatchFunction(headwordStr)))

        return clauses, filters


class HanDeDict(CEDICT):
    """
    HanDeDict dictionary access.

    .. seealso:: :class:`~cjklib.build.builder.HanDeDictBuilder`
    """
    PROVIDES = 'HanDeDict'
    DICTIONARY_TABLE = 'HanDeDict'

    def __init__(self, **options):
        columnFormatStrategies = options.get('columnFormatStrategies', {})
        if None not in columnFormatStrategies:
            columnFormatStrategies[None] \
                = formatstrategy.NonReadingEntityWhitespace()
            options['columnFormatStrategies'] = columnFormatStrategies

        if 'headwordSearchStrategy' not in options:
            options['headwordSearchStrategy'] = searchstrategy.Wildcard()
        if 'mixedReadingSearchStrategy' not in options:
            options['mixedReadingSearchStrategy'] \
                = searchstrategy.MixedTonelessWildcardReading()
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = searchstrategy.HanDeDictWildcardTranslation()
        super(HanDeDict, self).__init__(**options)


class CFDICT(HanDeDict):
    """
    CFDICT dictionary access.

    .. seealso:: :class:`~cjklib.build.builder.CFDICTBuilder`
    """
    PROVIDES = 'CFDICT'
    DICTIONARY_TABLE = 'CFDICT'

