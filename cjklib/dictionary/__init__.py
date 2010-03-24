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

Dictionary sources yield less structured information compared to other data
sources exposed in this library. Owing to this fact, a flexible system is
provided to the user.

G{classtree BaseDictionary}

Examples
========
Examples how to use this module:
    - Create a dictionary instance:

        >>> from cjklib.dictionary import CEDICT
        >>> d = CEDICT()

    - Get dictionary entries by reading:

        >>> [e.HeadwordSimplified for e in \\
        ...     d.getForReading('zhi dao', reading='Pinyin',\
 toneMarkType='numbers')]
        [u'\u5236\u5bfc', u'\u6267\u5bfc', u'\u6307\u5bfc', u'\u76f4\u5230',\
 u'\u76f4\u6363', u'\u77e5\u9053']

    - Change a search strategy (here search for a reading without tones):

        >>> d = CEDICT(readingSearchStrategy=search.SimpleWildcardReading())
        >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
        []
        >>> d = CEDICT(readingSearchStrategy=search.TonelessWildcardReading())
        >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
        [EntryTuple(HeadwordTraditional=u'\u4f60\u597d',\
 HeadwordSimplified=u'\u4f60\u597d', Reading=u'n\u01d0 h\u01ceo',\
 Translation=u'/hello/hi/how are you?/')]

    - Apply a formatting strategy to remove all initial and final slashes on
      CEDICT translations:

        >>> from cjklib.dictionary import *
        >>> class TranslationFormatStrategy(format.Base):
        ...     def format(self, string):
        ...         return string.strip('/')
        ...
        >>> d = CEDICT(
        ...     columnFormatStrategies={'Translation':\
 TranslationFormatStrategy()})
        >>> d.getFor(u'东京')
        [EntryTuple(HeadwordTraditional=u'\u6771\u4eac',\
 HeadwordSimplified=u'\u4e1c\u4eac', Reading=u'D\u014dng j\u012bng',\
 Translation=u'T\u014dky\u014d, capital of Japan')]

    - A simple dictionary lookup tool:

        >>> from cjklib.dictionary import *
        >>> from cjklib.reading import ReadingFactory
        >>> def search(string, reading=None, dictionary='CEDICT'):
        ...     # guess reading dialect
        ...     options = {}
        ...     if reading:
        ...         f = ReadingFactory()
        ...         opClass = f.getReadingOperatorClass(reading)
        ...         if hasattr(opClass, 'guessReadingDialect'):
        ...             options = opClass.guessReadingDialect(string)
        ...     # search
        ...     d = getDictionary(dictionary,\
 entryFactory=entry.UnifiedHeadword())
        ...     result = d.getFor(string, reading=reading, **options)
        ...     # print
        ...     for e in result:
        ...         print e.Headword, e.Reading, e.Translation
        ...
        >>> search('_taijiu', 'Pinyin')
        茅台酒（茅臺酒） máo tái jiǔ /maotai (a Chinese\
 liquor)/CL:杯[bei1],瓶[ping2]/

Entry factories
===============
Similar to SQL interfaces, entries can be returned in different fashion. An
X{entry factory} takes care of preparing the output. For this predefined
factories exist: L{entry.Tuple}, which is very basic, will return each
entry as a tuple of its columns while the mostly used L{entry.NamedTuple} will
return tuple objects that are accessible by attribute also.

Formatting strategies
=====================
As reading formattings vary and many readings can be converted into each other,
a X{formatting strategy} can be applied to return the expected format.
L{format.ReadingConversion} provides an easy way to convert the reading given
by the dictionary into the user defined reading. Other columns can also be
formatted by applying a strategy, see the example above.

A hybrid approach makes it possible to apply strategies on single cells, giving
a mapping from the cell name to the strategy, or a strategy that operates on the
entire result entry, by giving a mapping from C{None} to the strategy. In the
latter case the formatting strategy needs to deal with the dictionary specific
entry structure:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(columnFormatStrategies={
        ...     'Translation': format.TranslationFormatStrategy()})
        >>> d = CEDICT(columnFormatStrategies={
        ...     None: format.NonReadingEntityWhitespace()})

Formatting strategies can be chained together using the L{format.Chain} class.

Search strategies
=================
Searching in natural language data is a difficult process and highly depends on
the use case at hand. This task is provided by X{search strategies} which
account for the more complex parts of this module. Strategies exist for the
three main parts of dictionary entries: headword, reading and translation.
Additionally mixed searching for a headword partially expressed by reading
information is supported and can augment the basic reading search. Several
instances of search strategies exist offering basic or more sophisticated
routines. For example wildcard searching is offered on top of many basic
strategies offering by default placeholders C{'_'} for a single character, and
C{'%'} for a match of zero to many characters.

G{classtree search.Exact}

Headword search strategies
--------------------------
Searching for headwords is the most simple among the three. Exact searches are
provided by class L{search.Exact}. By default class L{search.Wildcard} is
employed which offers wildcard searches.

Reading search strategies
-------------------------
Readings have more complex and unique representations. Several classes are
provided here: L{search.Exact} again can be used for exact matches, and
L{search.Wildcard} for wildcard searches. L{search.SimpleReading}
and L{search.SimpleWildcardReading} provide similar searching for
transcriptions as found e.g. in CEDICT. A more complex search is provided by
L{search.TonelessWildcardReading} which offers search for readings
missing tonal information.

Translation search strategies
-----------------------------
A basic search is provided by L{search.SingleEntryTranslation} which
finds an exact entry in a list of entries separated by slashes ('X{/}'). More
flexible searching is provided by L{search.SimpleTranslation} and
L{search.SimpleWildcardTranslation} which take into account additional
information placed in parantheses. These classes have even more special
implementations adapted to formats found in dictionaries I{CEDICT} and
I{HanDeDict}.

More complex ones can be implemented on the basis of extending the underlying
table in the database, e.g. using I{full text search} capabilities of the
database server. One popular way is using stemming algorithms for copying with
inflections by reducing a word to its root form.

Mixed reading search strategies
-------------------------------
Special support for a string with mixed reading and headword entities is
provided by X{mixed reading search strategies}. For example X{'dui4 不 qi3'}
will find all entries with headwords whose middle character out of three is
X{'不'} and whose left character is read X{'dui4'} while the right character is
read X{'qi3'}.

Case insensitivity & Collations
===============================
Case insensitive searching is done through collations in the underlying database
system and for databases without collation support by employing function
C{lower()}. A default case independent collation is chosen in the appropriate
build method in L{cjklib.build.builder}.

I{SQLite} by default has no Unicode support for string operations. Optionally
the I{ICU} library can be compiled in for handling alphabetic non-ASCII
characters. The I{DatabaseConnector} can register own Unicode functions if ICU
support is missing. Queries with C{LIKE} will then use function C{lower()}. This
compatible mode has a negative impact on performance and as it is not needed for
dictionaries like EDICT or CEDICT it is disabled by default.

@todo Impl: Use Iterators?
@todo Impl: Pass entry factories directly to search method in DatabaseConnector
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

def getAvailableDictionaries(dbConnectInst=None):
    """
    Returns a list of available dictionaries for the given database
    connection.

    @type dbConnectInst: instance
    @param dbConnectInst: optional instance of a L{DatabaseConnector}
    @rtype: list of class
    @return: list of dictionary class objects
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

    @type dictionaryName: str
    @param dictionaryName: dictionary name
    @rtype: type
    @return: dictionary class
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

    @type dictionaryName: str
    @param dictionaryName: dictionary name
    @rtype: type
    @return: dictionary instance
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

    def __init__(self, **options):
        """
        Initialises the BaseDictionary instance.

        @keyword entryFactory: entry factory instance
        @keyword columnFormatStrategies: column formatting strategy instances
        @keyword headwordSearchStrategy: headword search strategy instance
        @keyword readingSearchStrategy: reading search strategy instance
        @keyword translationSearchStrategy: translation search strategy instance
        @keyword mixedReadingSearchStrategy: mixed reading search strategy
            instance
        @keyword databaseUrl: database connection setting in the format
            C{driver://user:pass@host/database}.
        @keyword dbConnectInst: instance of a L{DatabaseConnector}
        """
        # get connector to database
        if 'dbConnectInst' in options:
            self.db = options['dbConnectInst']
        else:
            databaseUrl = options.pop('databaseUrl', None)
            self.db = dbconnector.getDBConnector(databaseUrl)
            """L{DatabaseConnector} instance"""

        if 'entryFactory' in options:
            self.entryFactory = options['entryFactory']
        else:
            self.entryFactory = entryfactory.Tuple()
            """Factory for formatting row entries."""
        if hasattr(self.entryFactory, 'setDictionaryInstance'):
            self.entryFactory.setDictionaryInstance(self)

        columnFormatStrategies = options.get('columnFormatStrategies', {})
        self.setSolumnFormatStrategies(columnFormatStrategies)

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

    def setSolumnFormatStrategies(self, columnFormatStrategies):
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
        setSolumnFormatStrategies)

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
        """Version (date) of the dictionary. C{None} if not available."""
        try:
            versionTable = Table('Version', self.db.metadata, autoload=True,
                autoload_with=self.db.engine,
                schema=self.db.tables[self.DICTIONARY_TABLE].schema)

            return self.db.selectScalar(select([versionTable.c.ReleaseDate],
                versionTable.c.TableName == self.DICTIONARY_TABLE))
        except NoSuchTableError:
            pass

    def _search(self, whereClause, filters, limit, orderBy):
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
        results = self.db.selectRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderByCols).limit(limit))

        # filter
        if filters:
            results = filter(_getFilterFunction(filters), results)

        # format readings and translations
        if self.columnFormatStrategies:
            results = map(list, results)
            for strategy in self._formatStrategies:
                results = map(strategy.format, results)
            results = map(tuple, results)

        # format results
        entries = self.entryFactory.getEntries(results)

        return entries

    def getAll(self, limit=None, orderBy=None):
        return self._search(None, limit, orderBy)

    def _getHeadwordSearch(self, headwordStr, **options):
        dictionaryTable = self.db.tables[self.DICTIONARY_TABLE]

        headwordClause = self.headwordSearchStrategy.getWhereClause(
            dictionaryTable.c.Headword, headwordStr)

        headwordMatchFunc = self.headwordSearchStrategy.getMatchFunction(
            headwordStr)

        return [headwordClause], [(['Headword'], headwordMatchFunc)]

    def getForHeadword(self, headwordStr, limit=None, orderBy=None, **options):
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
        # TODO document: raises conversion error
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
        clauses, filters = self._getTranslationSearch(translationStr)

        return self._search(or_(*clauses), filters, limit, orderBy)

    def getFor(self, searchStr, limit=None, orderBy=None, **options):
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

    @see: L{EDICTBuilder}
    """
    PROVIDES = 'EDICT'
    READING = 'Kana'
    DICTIONARY_TABLE = 'EDICT'


class EDICTStyleEnhancedReadingDictionary(EDICTStyleDictionary):
    u"""
    Access for EDICT-style dictionaries with enhanced reading support.

    The EDICTStyleEnhancedReadingDictionary dictionary class extends L{EDICT}
    by:
        - support for reading conversion, understanding reading format strategy
          L{format.ReadingConversion},
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

    @see: L{CEDICTGRBuilder}
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

    Example
    =======

    Get dictionary entries with reading IPA:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(
        ...     readingFormatStrategy=format.ReadingConversion('MandarinIPA'))
        >>> print ', '.join([l['Reading'] for l in d.getForHeadword(u'行')])
        xaŋ˧˥, ɕiŋ˧˥, ɕiŋ˥˩

    @see: L{CEDICTBuilder}
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

        @keyword entryFactory: entry factory instance
        @keyword columnFormatStrategies: column formatting strategy instances
        @keyword headwordSearchStrategy: headword search strategy instance
        @keyword readingSearchStrategy: reading search strategy instance
        @keyword translationSearchStrategy: translation search strategy instance
        @keyword mixedReadingSearchStrategy: mixed reading search strategy
            instance
        @keyword databaseUrl: database connection setting in the format
            C{driver://user:pass@host/database}.
        @keyword dbConnectInst: instance of a L{DatabaseConnector}
        @keyword headword: C{'s'} if the simplified headword is used as default,
            C{'t'} if the traditional headword is used as default, C{'b'} if
            both are tried.
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

    @see: L{HanDeDictBuilder}
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

    @see: L{CFDICTBuilder}
    """
    PROVIDES = 'CFDICT'
    DICTIONARY_TABLE = 'CFDICT'

