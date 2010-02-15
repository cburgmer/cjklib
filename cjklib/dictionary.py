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

Entry factories
===============
Similar to SQL interfaces, entries can be returned in different fashion. An
X{entry factory} takes care of preparing the output. For this predefined
factories exist: L{TupleEntryFactory}, which is very basic, will return each
entry as a tuple of its columns while the mostly used L{NamedTupleFactory} will
return tuple objects that are accessible by attribute also.

Formatting strategies
=====================
As reading formattings vary and many readings can be converted into each other,
a X{formatting strategy} can be applied to return the expected format.
L{ReadingConversionStrategy} provides an easy way to convert the reading given
by the dictionary into the user defined reading. Other columns can also be
formatted by applying a strategy, see the example below.

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

Headword search strategies
--------------------------
Searching for headwords is the most simple among the three. Exact searches are
provided by class L{ExactSearchStrategy}. By default class
L{WildcardSearchStrategy} is employed which offers wildcard searches.

Reading search strategies
-------------------------
Readings have more complex and unique representations. Several classes are
provided here: L{ExactSearchStrategy} again can be used for exact matches, and
L{WildcardSearchStrategy} for wildcard searches. L{SimpleReadingSearchStrategy}
and L{SimpleWildcardReadingSearchStrategy} provide similar searching for
transcriptions as found e.g. in CEDICT. A more complex search is provided by
L{TonelessWildcardReadingSearchStrategy} which offers search for readings
missing tonal information.

Translation search strategies
-----------------------------
A basic search is provided by L{SingleEntryTranslationSearchStrategy} which
finds an exact entry in a list of entries separated by slashes ('X{/}'). More
flexible searching is provided by L{SimpleTranslationSearchStrategy} and
L{SimpleWildcardTranslationSearchStrategy} which take into account additional
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

Examples
========

- Create a dictionary instance:

    >>> from cjklib.dictionary import CEDICT
    >>> d = CEDICT()

- Get dictionary entries by reading:

    >>> [e.HeadwordSimplified for e in \\
    ...     d.getForReading('po1', reading='Pinyin', toneMarkType='numbers')]
    [u'\u5761', u'\u6cfc', u'\u948b', u'\u9642', u'\u9887']

- Change a search strategy (here search for a reading without tones):

    >>> d = CEDICT(readingSearchStrategy=SimpleWildcardReadingSearchStrategy())
    >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
    []
    >>> d = CEDICT(readingSearchStrategy=\
TonelessWildcardReadingSearchStrategy())
    >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
    [EntryTuple(HeadwordSimplified=u'\u4f60\u597d',\
 HeadwordTraditional=u'\u4f60\u597d', Reading=u'n\u01d0 h\u01ceo',\
 Translation=u'/hello/hi/how are you?/')]

- Apply a formatting strategy to remove all initial and final slashes on CEDICT
  translations:

    >>> from cjklib.dictionary import *
    >>> class TranslationFormatStrategy(BaseFormatStrategy):
    ...     def format(self, string):
    ...         return string.strip('/')
    ...
    >>> d = CEDICT(
    ...     columnFormatStrategies={'Translation': TranslationFormatStrategy()})
    >>> d.getFor(u'东京')
    [EntryTuple(HeadwordSimplified=u'\u4e1c\u4eac',\
 HeadwordTraditional=u'\u6771\u4eac', Reading=u'D\u014dng j\u012bng',\
 Translation=u'T\u014dky\u014d, capital of Japan')]

- A simple dictionary lookup tool:

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
    ...     d = CEDICT(entryFactory=UnifiedHeadwordEntryFactory())
    ...     result = d.getFor(string, reading=reading, **options)
    ...     # print
    ...     for e in result:
    ...         print e.Headword, e.Reading, e.Translation
    ...
    >>> search('_taijiu', 'Pinyin')
    茅台酒（茅臺酒） máo tái jiǔ /maotai (a Chinese liquor)/CL:杯[bei1],瓶[ping2]/

@todo Impl: Use Iterators?
@todo Impl: Pass entry factories directly to search method in DatabaseConnector
@todo Fix:  Don't "correct" non-reading entities in HanDeDict in builder
@todo Impl: Allow simple FTS3 searching as build support is already provided.
"""

import re
import types

from sqlalchemy import select
from sqlalchemy.sql import and_, or_
from sqlalchemy.sql.expression import func

from cjklib.reading import ReadingFactory
from cjklib.dbconnector import DatabaseConnector
from cjklib import exception
from cjklib.util import cross

# Python 2.4 support
if not hasattr(__builtins__, 'all'):
    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

_wildcardRegexCache = {}
def _escapeWildcards(string, escape='\\'):
    r"""
    Escape characters that would be interpreted by a SQL LIKE statement.

        >>> _escapeWildcards('_%\\ab%c\\%a\\_\\\\_')
        '\\_\\%\\\\ab\\%c\\\\\\%a\\\\\\_\\\\\\\\\\_'
    """
    assert len(escape) == 1
    if escape not in _wildcardRegexCache:
        _wildcardRegexCache[escape] = re.compile(
            r'(%s|[_%%])' % re.escape(escape))
    # insert escape
    return _wildcardRegexCache[escape].sub(r'%s\1' % re.escape(escape), string)

#{ Entry factories

class TupleEntryFactory(object):
    """Basic entry factory, returning a tuple of columns."""
    def getEntries(self, results):
        """
        Returns the dictionary results as lists.
        """
        return map(tuple, results)


class NamedTupleFactory(object):
    """
    Factory returning tuple entries with attribute-style access.
    """
    def _getNamedTuple(self):
        if not hasattr(self, '_namedTuple'):
            self._namedTuple = self._createNamedTuple('EntryTuple',
                self.columnNames)
        return self._namedTuple

    @staticmethod
    def _createNamedTuple(typename, fieldNames):
        # needed for Python 2.4 and 2.5
        try:
            from collections import namedtuple
        except ImportError:
            # Code from Raymond Hettinger under MIT licence,
            #   http://code.activestate.com/recipes/500261/
            from operator import itemgetter as _itemgetter
            from keyword import iskeyword as _iskeyword
            import sys as _sys

            def namedtuple(typename, field_names, verbose=False, rename=False):
                """Returns a new subclass of tuple with named fields.

                >>> Point = namedtuple('Point', 'x y')
                >>> Point.__doc__                   # docstring for the new class
                'Point(x, y)'
                >>> p = Point(11, y=22)             # instantiate with positional args or keywords
                >>> p[0] + p[1]                     # indexable like a plain tuple
                33
                >>> x, y = p                        # unpack like a regular tuple
                >>> x, y
                (11, 22)
                >>> p.x + p.y                       # fields also accessable by name
                33
                >>> d = p._asdict()                 # convert to a dictionary
                >>> d['x']
                11
                >>> Point(**d)                      # convert from a dictionary
                Point(x=11, y=22)
                >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
                Point(x=100, y=22)

                """

                # Parse and validate the field names.  Validation serves two purposes,
                # generating informative error messages and preventing template injection attacks.
                if isinstance(field_names, basestring):
                    field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
                field_names = tuple(map(str, field_names))
                if rename:
                    names = list(field_names)
                    seen = set()
                    for i, name in enumerate(names):
                        if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                            or not name or name[0].isdigit() or name.startswith('_')
                            or name in seen):
                                names[i] = '_%d' % i
                        seen.add(name)
                    field_names = tuple(names)
                for name in (typename,) + field_names:
                    if not min(c.isalnum() or c=='_' for c in name):
                        raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
                    if _iskeyword(name):
                        raise ValueError('Type names and field names cannot be a keyword: %r' % name)
                    if name[0].isdigit():
                        raise ValueError('Type names and field names cannot start with a number: %r' % name)
                seen_names = set()
                for name in field_names:
                    if name.startswith('_') and not rename:
                        raise ValueError('Field names cannot start with an underscore: %r' % name)
                    if name in seen_names:
                        raise ValueError('Encountered duplicate field name: %r' % name)
                    seen_names.add(name)

                # Create and fill-in the class template
                numfields = len(field_names)
                argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
                reprtxt = ', '.join('%s=%%r' % name for name in field_names)
                template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
                for i, name in enumerate(field_names):
                    template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
                if verbose:
                    print template

                # Execute the template string in a temporary namespace
                namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                                _property=property, _tuple=tuple)
                try:
                    exec template in namespace
                except SyntaxError, e:
                    raise SyntaxError(e.message + ':\n' + template)
                result = namespace[typename]

                # For pickling to work, the __module__ variable needs to be set to the frame
                # where the named tuple is created.  Bypass this step in enviroments where
                # sys._getframe is not defined (Jython for example) or sys._getframe is not
                # defined for arguments greater than 0 (IronPython).
                try:
                    result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
                except (AttributeError, ValueError):
                    pass

                return result

        return namedtuple(typename, fieldNames)

    def setDictionaryInstance(self, dictInstance):
        if not hasattr(dictInstance, 'COLUMNS'):
            raise ValueError('Incompatible dictionary')

        self.columnNames = dictInstance.COLUMNS

    def getEntries(self, results):
        """
        Returns the dictionary results as named tuples.
        """
        EntryTuple = self._getNamedTuple()
        return map(EntryTuple._make, results)


class UnifiedHeadwordEntryFactory(NamedTupleFactory):
    """
    Factory adding a simple X{Headword} key for CEDICT style dictionaries to
    provide results compatible with EDICT. An alternative headword is given in
    brackets if two different headword instances are provided in the entry.
    """
    def __init__(self, headword='s'):
        if headword in ('s', 't'):
            self.headword = headword
        else:
            raise ValueError("Invalid type for headword '%s'."
                % headword \
                + " Allowed values 's'implified or 't'raditional")

    def _unifyHeadwords(self, entry):
        entry = list(entry)
        if self.headword == 's':
            headwords = (entry[0], entry[1])
        else:
            headwords = (entry[1], entry[0])

        if headwords[0] == headwords[1]:
            entry.append(headwords[0])
        else:
            entry.append(u'%s（%s）' % headwords)
        return entry

    def getEntries(self, results):
        """
        Returns the dictionary results as named tuples.
        """
        def augmentedEntry(entry):
            entry = self._unifyHeadwords(entry)
            return EntryTuple._make(entry)

        EntryTuple = self._getNamedTuple()
        return map(augmentedEntry, results)

    def setDictionaryInstance(self, dictInstance):
        super(UnifiedHeadwordEntryFactory, self).setDictionaryInstance(
            dictInstance)
        if not hasattr(dictInstance, 'COLUMNS'):
            raise ValueError('Incompatible dictionary')

        self.columnNames = dictInstance.COLUMNS + ['Headword']

#}
#{ Formatting strategies

class BaseFormatStrategy(object):
    """Base formatting strategy, needs to be overridden."""
    def setDictionaryInstance(self, dictInstance):
        self._dictInstance = dictInstance

    def format(self, string):
        """
        Returns the formatted column.

        @type string: str
        @param string: column as returned by the dictionary
        @rtype: str
        @return: formatted column
        """
        raise NotImplementedError()


class ReadingConversionStrategy(BaseFormatStrategy):
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

    def setDictionaryInstance(self, dictInstance):
        super(ReadingConversionStrategy, self).setDictionaryInstance(
            dictInstance)

        if (not hasattr(self._dictInstance, 'READING')
            or not hasattr(self._dictInstance, 'READING_OPTIONS')):
            raise ValueError('Incompatible dictionary')

        self.fromReading = self._dictInstance.READING
        self.sourceOptions = self._dictInstance.READING_OPTIONS

        self._readingFactory = ReadingFactory(
            dbConnectInst=self._dictInstance.db)

        toReading = self.toReading or self.fromReading
        if not self._readingFactory.isReadingConversionSupported(
            self.fromReading, toReading):
            raise ValueError("Conversion from '%s' to '%s' not supported"
                % (self.fromReading, toReading))

    def format(self, string):
        toReading = self.toReading or self.fromReading
        try:
            return self._readingFactory.convert(string, self.fromReading,
                toReading, sourceOptions=self.sourceOptions,
                targetOptions=self.targetOptions)
        except (exception.DecompositionError, exception.CompositionError,
            exception.ConversionError):
            return None

#}
#{ Common search classes

class _CaseInsensitiveBase(object):
    """Base class providing methods for case insensitive searches."""
    def __init__(self, caseInsensitive=False, sqlCollation=None, **options):
        """
        Initialises the _CaseInsensitiveBase.

        @type caseInsensitive: bool
        @param caseInsensitive: if C{True}, latin characters match their
            upper/lower case equivalent, if C{False} case sensitive matches
            will be made (default)
        @type sqlCollation: str
        @param sqlCollation: optional collation to use on columns in SQL queries
        """
        self._caseInsensitive = caseInsensitive
        self._sqlCollation = sqlCollation

    def setDictionaryInstance(self, dictInstance):
        compatibilityUnicodeSupport = getattr(dictInstance.db,
            'compatibilityUnicodeSupport', False)

        # Don't depend on collations, but use ILIKE (PostgreSQL) or
        #   "lower() LIKE lower()" (others)
        self._needsIlike = (compatibilityUnicodeSupport or
            dictInstance.db.engine.name not in ('sqlite', 'mysql'))
        # "lower() LIKE lower()" for DB other than SQLite and MySQL
        self._needsIEquals = (dictInstance.db.engine.name
            not in ('sqlite', 'mysql'))

    def _equals(self, column, query):
        if self._sqlCollation:
            column = column.collate(self._sqlCollation)

        if self._needsIEquals:
            return column.lower() == func.lower(query)
        else:
            return column == query

    def _contains(self, column, query, escape=None):
        escape = escape or self.escape
        if self._sqlCollation:
            column = column.collate(self._sqlCollation)

        if self._needsIlike:
            # Uses ILIKE for PostgreSQL and falls back to "lower() LIKE lower()"
            #   for other engines
            return column.ilike('%' + query + '%')
        else:
            return column.contains(query)

    def _like(self, column, query, escape=None):
        escape = escape or self.escape
        if self._sqlCollation:
            column = column.collate(self._sqlCollation)

        if self._needsIlike:
            # Uses ILIKE for PostgreSQL and falls back to "lower() LIKE lower()"
            #   for other engines
            return column.ilike(query)
        else:
            return column.like(query)

    def _compileRegex(self, regexString):
        if self._caseInsensitive:
            regexString = '(?ui)^' + regexString
        else:
            regexString = '(?u)^' + regexString
        return re.compile(regexString)


class ExactSearchStrategy(_CaseInsensitiveBase):
    """Simple search strategy class."""
    def getWhereClause(self, column, searchStr):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by L{getMatchFunction()}.

        @type column: SQLAlchemy column instance
        @param column: column to check against
        @type searchStr: str
        @param searchStr: search string
        @return: SQLAlchemy clause
        """
        return self._equals(column, searchStr)

    def getMatchFunction(self, searchStr):
        """
        Gets a function that returns C{True} if the entry's cell content matches
        the search string.

        This method provides the sufficient condition for a match. Note that
        matches from other SQL clauses might get included which do not fulfill
        the conditions of L{getWhereClause()}.

        @type searchStr: str
        @param searchStr: search string
        @rtype: function
        @return: function that returns C{True} if the entry is a match
        """
        if self._caseInsensitive:
            searchStr = searchStr.lower()
            return lambda cell: searchStr == cell.lower()
        else:
            return lambda cell: searchStr == cell


class _WildcardBase(object):
    """
    Wildcard search base class. Provides wildcard conversion and regular
    expression preparation methods.

    Wildcards can be used as placeholders in searches. By default C{'_'}
    substitutes a single character while C{'%'} matches zero, one or multiple
    characters. Searches for the actual characters (here C{'_'} and C{'%'}) need
    to mask those occurences by the escape character, by default a backslash
    C{'\\'}, which needs escaping itself.
    """
    class SingleWildcard:
        """Wildcard matching exactly one character."""
        SQL_LIKE_STATEMENT = '_'
        REGEX_PATTERN = '.'

    class MultipleWildcard:
        """Wildcard matching zero, one or multiple characters."""
        SQL_LIKE_STATEMENT = '%'
        REGEX_PATTERN = '.*'

    def __init__(self, singleCharacter='_', multipleCharacters='%',
        escape='\\', **options):
        self.singleCharacter = singleCharacter
        self.multipleCharacters = multipleCharacters
        self.escape = escape
        if len(self.escape) != 1:
            raise ValueError("Escape character %s needs to have length 1"
                % repr(self.escape))

        param = {'esc': re.escape(self.escape),
            'single': re.escape(self.singleCharacter),
            'multiple': re.escape(self.multipleCharacters)}
        # substitute wildcard characters and escape plain parts, make sure
        #   escape is handled properly
        self._wildcardRegex = re.compile(
            r'(%(esc)s{2}|%(esc)s?(?:%(single)s|%(multiple)s)|[_%%\\])'
                % param)

    def _parseWildcardString(self, string):
        entities = []
        for idx, part in enumerate(self._wildcardRegex.split(string)):
            if idx % 2 == 0:
                if part:
                    entities.append(part)
            else:
                if part == self.singleCharacter:
                    entities.append(self.SingleWildcard())
                elif part == self.multipleCharacters:
                    entities.append(self.MultipleWildcard())
                elif (part.startswith(self.escape)
                    and part[1:] in (self.escape, self.singleCharacter,
                        self.multipleCharacters)):
                    # unescape
                    entities.append(part[1:])
                else:
                    entities.append(part)

        return entities

    def _hasWildcardCharacters(self, searchStr):
        """
        Returns C{True} if a wildcard character is included in the search
        string.
        """
        for idx, part in enumerate(self._wildcardRegex.split(searchStr)):
            if (idx % 2 == 1
                and part in (self.singleCharacter, self.multipleCharacters)):
                return True
        return False

    def _getWildcardQuery(self, searchStr):
        """Joins reading entities, taking care of wildcards."""
        entityList = []
        for entity in self._parseWildcardString(searchStr):
            if not isinstance(entity, basestring):
                entity = entity.SQL_LIKE_STATEMENT
            else:
                entity = _escapeWildcards(entity, escape=self.escape)
            entityList.append(entity)

        return ''.join(entityList)

    def _prepareWildcardRegex(self, searchStr):
        entityList = []
        for entity in self._parseWildcardString(searchStr):
            if not isinstance(entity, basestring):
                entity = entity.REGEX_PATTERN
            else:
                entity = re.escape(entity)
            entityList.append(entity)

        return ''.join(entityList)

    def _getWildcardRegex(self, searchStr):
        return self._compileRegex('^' + self._prepareWildcardRegex(searchStr)
            + '$')


class WildcardSearchStrategy(ExactSearchStrategy, _WildcardBase):
    """Basic headword search strategy with support for wildcards."""
    def __init__(self, **options):
        ExactSearchStrategy.__init__(self, **options)
        _WildcardBase.__init__(self, **options)

    def getWhereClause(self, column, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            wildcardSearchStr = self._getWildcardQuery(searchStr)
            return self._like(column, wildcardSearchStr)
        else:
            # simple routine is faster
            return ExactSearchStrategy.getWhereClause(self, column, searchStr)

    def getMatchFunction(self, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda headword: (headword is not None
                and regex.search(headword) is not None)
        else:
            # simple routine is faster
            return ExactSearchStrategy.getMatchFunction(self, searchStr)

#}
#{ Translation search strategies

class SingleEntryTranslationSearchStrategy(ExactSearchStrategy):
    """Basic translation search strategy."""
    def __init__(self, caseInsensitive=True, **options):
        ExactSearchStrategy.__init__(self, caseInsensitive=caseInsensitive,
            **options)

    def getWhereClause(self, column, searchStr):
        return self._contains(column, _escapeWildcards(searchStr), escape='\\')

    def getMatchFunction(self, searchStr):
        if self._caseInsensitive:
            searchStr = searchStr.lower()
            return (lambda translation:
                    searchStr in translation.lower().split('/'))
        else:
            return lambda translation: searchStr in translation.split('/')


class WildcardTranslationSearchStrategy(SingleEntryTranslationSearchStrategy,
    _WildcardBase):
    """Basic translation search strategy with support for wildcards."""
    def __init__(self, *args, **options):
        SingleEntryTranslationSearchStrategy.__init__(self, *args, **options)
        _WildcardBase.__init__(self, *args, **options)

    def _getWildcardRegex(self, searchStr):
        return self._compileRegex('/' + self._prepareWildcardRegex(searchStr)
            + '/')

    def getWhereClause(self, column, searchStr):
        wildcardSearchStr = self._getWildcardQuery(searchStr)
        return self._contains(column, wildcardSearchStr)

    def getMatchFunction(self, searchStr):
        if self._hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(readingStr)
            return lambda translation: (translation is not None
                and regex.search(translation) is not None)
        else:
            # simple routine is faster
            return SingleEntryTranslationSearchStrategy.getMatchFunction(self,
                searchStr)


class SimpleTranslationSearchStrategy(SingleEntryTranslationSearchStrategy):
    """
    Simple translation search strategy. Takes into account additions put in
    parentheses.
    """
    def getMatchFunction(self, searchStr):
        # start with a slash '/', make sure any opening parenthesis is
        #   closed and match search string. Finish with other content in
        #   parantheses and a slash
        regex = self._compileRegex('/' + '(\s+|\([^\)]+\))*'
            + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '/')

        return lambda translation: (translation is not None
            and regex.search(translation) is not None)


class _SimpleTranslationWildcardBase(_WildcardBase):
    """
    Wildcard search base class for translation strings.
    """
    class SingleWildcard:
        SQL_LIKE_STATEMENT = '_'
        # don't match a trailing space or following space if bordered by bracket
        REGEX_PATTERN = '(?:(?:(?<!\)) (?!\())|[^ ])'


class SimpleWildcardTranslationSearchStrategy(SimpleTranslationSearchStrategy,
    _SimpleTranslationWildcardBase):
    """
    Simple translation search strategy with support for wildcards. Takes into
    account additions put in parentheses.
    """
    def __init__(self, *args, **options):
        SimpleTranslationSearchStrategy.__init__(self, *args, **options)
        _SimpleTranslationWildcardBase.__init__(self, *args, **options)

    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith('%'):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith('%'):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return self._compileRegex('/' + regexStr + '/')

    def getWhereClause(self, column, searchStr):
        wildcardSearchStr = self._getWildcardQuery(searchStr)
        return self._contains(column, wildcardSearchStr)

    def getMatchFunction(self, searchStr):
        if self._hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda translation: (translation is not None
                and regex.search(translation) is not None)
        else:
            # simple routine is faster
            return SimpleTranslationSearchStrategy.getMatchFunction(self,
                searchStr)


class CEDICTTranslationSearchStrategy(SingleEntryTranslationSearchStrategy):
    """
    CEDICT translation based search strategy. Takes into account additions put
    in parentheses and appended information separated by a comma.
    """
    def getMatchFunction(self, searchStr):
        # start with a slash '/', make sure any opening parenthesis is
        #   closed and match search string. Finish with other content in
        #   parantheses and a slash
        regex = self._compileRegex('/' + '(\s+|\([^\)]+\))*'
            + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '[/,]')

        return lambda translation: (translation is not None
            and regex.search(translation) is not None)


class CEDICTWildcardTranslationSearchStrategy(CEDICTTranslationSearchStrategy,
    _SimpleTranslationWildcardBase):
    """
    CEDICT translation based search strategy with support for wildcards. Takes
    into account additions put in parentheses and appended information separated
    by a comma.
    """
    def __init__(self, *args, **options):
        CEDICTTranslationSearchStrategy.__init__(self, *args, **options)
        _SimpleTranslationWildcardBase.__init__(self, *args, **options)

    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith('%'):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith('%'):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return self._compileRegex('/' + regexStr + '[/,]')

    def getWhereClause(self, column, searchStr):
        wildcardSearchStr = self._getWildcardQuery(searchStr)
        return self._contains(column, wildcardSearchStr)

    def getMatchFunction(self, searchStr):
        if self._hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda translation: (translation is not None
                and regex.search(translation) is not None)
        else:
            # simple routine is faster
            return CEDICTTranslationSearchStrategy.getMatchFunction(self,
                searchStr)


class HanDeDictTranslationSearchStrategy(SingleEntryTranslationSearchStrategy):
    """
    HanDeDict translation based search strategy. Takes into account additions
    put in parentheses and allows for multiple entries in one record separated
    by punctuation marks.
    """
    def getMatchFunction(self, searchStr):
        # start with a slash '/', make sure any opening parenthesis is
        #   closed, end any other entry with a punctuation mark, and match
        #   search string. Finish with other content in parantheses and
        #   a slash or punctuation mark
        regex = self._compileRegex('/((\([^\)]+\)|[^\(])+'
            + '(?!; Bsp.: [^/]+?--[^/]+)[\,\;\.\?\!])?' + '(\s+|\([^\)]+\))*'
            + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '[/\,\;\.\?\!]')

        return lambda translation: (translation is not None
            and regex.search(translation) is not None)


class HanDeDictWildcardTranslationSearchStrategy(
    HanDeDictTranslationSearchStrategy, _SimpleTranslationWildcardBase):
    """
    HanDeDict translation based search strategy with support for wildcards.
    Takes into account additions put in parentheses and appended information
    separated by a comma.
    """
    def __init__(self, *args, **options):
        HanDeDictTranslationSearchStrategy.__init__(self, *args, **options)
        _SimpleTranslationWildcardBase.__init__(self, *args, **options)

    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith('%'):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith('%'):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return self._compileRegex('/((\([^\)]+\)|[^\(])+'
            + '(?!; Bsp.: [^/]+?--[^/]+)[\,\;\.\?\!])?' + regexStr
            + '[/\,\;\.\?\!]')

    def getWhereClause(self, column, searchStr):
        wildcardSearchStr = self._getWildcardQuery(searchStr)
        return self._contains(column, wildcardSearchStr)

    def getMatchFunction(self, searchStr):
        if self._hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda translation: (translation is not None
                and regex.search(translation) is not None)
        else:
            # simple routine is faster
            return HanDeDictTranslationSearchStrategy.getMatchFunction(self,
                searchStr)

#}
#{ Reading search strategies

class SimpleReadingSearchStrategy(ExactSearchStrategy):
    """
    Simple reading search strategy. Converts search string to the dictionary
    reading and separates entities by space.
    @todo Fix: How to handle non-reading entities?
    """
    def __init__(self, caseInsensitive=True, **options):
        ExactSearchStrategy.__init__(self, caseInsensitive=caseInsensitive,
            **options)
        self._getReadingsOptions = None

    def setDictionaryInstance(self, dictInstance):
        super(SimpleReadingSearchStrategy, self).setDictionaryInstance(
            dictInstance)
        self._dictInstance = dictInstance
        self._readingFactory = ReadingFactory(
            dbConnectInst=self._dictInstance.db)

        if (not hasattr(self._dictInstance, 'READING')
            or not hasattr(self._dictInstance, 'READING_OPTIONS')):
            raise ValueError('Incompatible dictionary')

    def _getReadings(self, readingStr, **options):
        if self._getReadingsOptions != (readingStr, options):
            self._getReadingsOptions = (readingStr, options)

            fromReading = options.get('reading', self._dictInstance.READING)
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

    def getWhereClause(self, column, searchStr, **options):
        decompEntities = self._getReadings(searchStr, **options)

        return or_(*[self._equals(column, ' '.join(entities))
            for entities in decompEntities])

    def getMatchFunction(self, searchStr, **options):
        if self._caseInsensitive:
            # assume that conversion of lower case results in lower case
            searchStr = searchStr.lower()
        decompEntities = self._getReadings(searchStr, **options)

        matchSet = set([' '.join(entities) for entities in decompEntities])

        if self._caseInsensitive:
            return lambda reading: reading.lower() in matchSet
        else:
            return lambda reading: reading in matchSet


class _SimpleReadingWildcardBase(_WildcardBase):
    """
    Wildcard search base class for readings.
    """
    class SingleWildcard:
        """Wildcard matching exactly one reading entity."""
        SQL_LIKE_STATEMENT = '_%'
        def match(self, entity):
            return entity is not None

    class MultipleWildcard:
        """Wildcard matching zero, one or multiple reading entities."""
        SQL_LIKE_STATEMENT = '%'
        def match(self, entity):
            return True

    def __init__(self, **options):
        _WildcardBase.__init__(self, **options)
        self._getWildcardFormsOptions = None

    def _parseWildcardString(self, string):
        entities = _WildcardBase._parseWildcardString(self, string)
        # brake down longer entities into single characters, omit spaces
        newEntities = []
        for entity in entities:
            if entity in (self.escape, self.singleCharacter,
                self.multipleCharacters) or not isinstance(entity, basestring):
                newEntities.append(entity)
            else:
                newEntities.extend([e for e in entity if e != ' '])

        return newEntities

    def _getReadings(self, readingStr, **options):
        raise NotImplementedError

    def _getWildcardForms(self, searchStr, **options):
        """
        Gets reading decomposition and prepares wildcards. Needs a method
        L{_getReadings()} to do the actual decomposition.
        """
        def isReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isReadingEntity(entity,
                    self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        if self._getWildcardFormsOptions != (searchStr, options):
            decompEntities = self._getReadings(searchStr, **options)

            self._wildcardForms = []
            for entities in decompEntities:
                wildcardEntities = []
                for entity in entities:
                    if isReadingEntity(entity):
                        wildcardEntities.append(entity)
                    else:
                        wildcardEntities.extend(
                            self._parseWildcardString(entity))

                self._wildcardForms.append(wildcardEntities)

        return self._wildcardForms

    def _getWildcardReading(self, entities):
        """Joins reading entities, taking care of wildcards."""
        entityList = []
        for entity in entities:
            if not isinstance(entity, basestring):
                entity = entity.SQL_LIKE_STATEMENT
            else:
                entity = _escapeWildcards(entity, escape=self.escape)

            # insert space to separate reading entities, but only if we are
            #   not looking for a wildcard with a possibly empty match
            if entityList and entityList[-1] != '%' and entity != '%':
                entityList.append(' ')
            entityList.append(entity)

        return ''.join(entityList)

    def _getWildcardQuery(self, searchStr, **options):
        wildcardForms = self._getWildcardForms(searchStr, **options)

        wildcardReadings = map(self._getWildcardReading, wildcardForms)
        return wildcardReadings

    def _getReadingEntities(self, reading):
        """Splits a reading string into entities."""
        # simple and efficient method for CEDICT type dictionaries
        return reading.split(' ')

    @staticmethod
    def _depthFirstSearch(searchEntities, entities):
        """
        Depth first search comparing a list of reading entities with wildcards
        against reading entities from a result.
        """
        def matches(searchEntity, entity):
            if isinstance(searchEntity, basestring):
                return searchEntity == entity
            else:
                return searchEntity.match(entity)

        if not searchEntities:
            if not entities:
                return True
            else:
                return False
        elif matches(searchEntities[0], None):
            # matches empty string
            if _SimpleReadingWildcardBase._depthFirstSearch(searchEntities[1:],
                entities):
                # try consume no entity
                return True
            elif entities:
                # consume one entity
                return _SimpleReadingWildcardBase._depthFirstSearch(
                    searchEntities, entities[1:])
            else:
                return False
        elif not entities:
            return False
        elif matches(searchEntities[0], entities[0]):
            # consume one entity
            return _SimpleReadingWildcardBase._depthFirstSearch(
                searchEntities[1:], entities[1:])
        else:
            return False

    def _getWildcardMatchFunction(self, searchStr, **options):
        """Gets a match function for a search string with wildcards."""
        def matchReadingEntities(reading):
            readingEntities = self._getReadingEntities(reading)

            # match against all pairs
            for entities in wildcardForms:
                if self._depthFirstSearch(entities, readingEntities):
                    return True

            return False

        if self._caseInsensitive:
            # assume that conversion of lower case results in lower case
            searchStr = searchStr.lower()
        wildcardForms = self._getWildcardForms(searchStr, **options)

        if self._caseInsensitive:
            return lambda reading: matchReadingEntities(reading.lower())
        else:
            return matchReadingEntities


class SimpleWildcardReadingSearchStrategy(SimpleReadingSearchStrategy,
    _SimpleReadingWildcardBase):
    """
    Simple reading search strategy with support for wildcards. Converts search
    string to the dictionary reading and separates entities by space.
    """
    def __init__(self, **options):
        SimpleReadingSearchStrategy.__init__(self)
        _SimpleReadingWildcardBase.__init__(self, **options)

    def getWhereClause(self, column, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            queries = self._getWildcardQuery(searchStr, **options)
            return or_(*[self._like(column, query) for query in queries])
        else:
            # simple routine is faster
            return SimpleReadingSearchStrategy.getWhereClause(self, column,
                searchStr, **options)

    def getMatchFunction(self, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            return self._getWildcardMatchFunction(searchStr, **options)
        else:
            # simple routine is faster
            return SimpleReadingSearchStrategy.getMatchFunction(self, searchStr,
                **options)


class _TonelessReadingWildcardBase(_SimpleReadingWildcardBase):
    """
    Wildcard search base class for tonal readings.
    """
    class TonalEntityWildcard:
        """
        Wildcard matching a reading entity with any tone that is appended as
        single character.
        """
        def __init__(self, plainEntity, escape):
            self._plainEntity = plainEntity
            self._escape = escape
        def getSQL(self):
            return _escapeWildcards(self._plainEntity, self._escape) + '_'
        SQL_LIKE_STATEMENT = property(getSQL)
        def match(self, entity):
            return entity and (entity == self._plainEntity
                or entity[:-1] == self._plainEntity)

    def __init__(self, supportWildcards=True, **options):
        _SimpleReadingWildcardBase.__init__(self, **options)
        self._supportWildcards = supportWildcards
        self._getPlainFormsOptions = None

    def _createTonalEntityWildcard(self, plainEntity):
        return self.TonalEntityWildcard(plainEntity, self.escape)

    def _getPlainForms(self, searchStr, **options):
        """
        Returns reading entities split into plain entities with tone where
        possible.
        """
        def isReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isReadingEntity(
                    entity, self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        def isPlainReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isPlainReadingEntity(
                    entity, self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        def splitEntityTone(entity, cache={}):
            if entity not in cache:
                try:
                    cache[entity] = self._readingFactory.splitEntityTone(
                        entity, self._dictInstance.READING,
                        **self._dictInstance.READING_OPTIONS)
                except (exception.InvalidEntityError,
                    exception.UnsupportedError):
                    cache[entity] = None
            return cache[entity]

        if self._getPlainFormsOptions != (searchStr, options):
            self._getPlainFormsOptions = (searchStr, options)

            decompEntities = self._getReadings(searchStr, **options)

            self._plainForms = []
            for entities in decompEntities:
                plain = []
                for entity in entities:
                    if isReadingEntity(entity):
                        # default case
                        result = splitEntityTone(entity)
                        if result:
                            plainEntity, tone = result
                            plain.append((entity, plainEntity, tone))
                        else:
                            plain.append((entity, None, None))
                    else:
                        plain.append(entity)
                self._plainForms.append(plain)

        if not self._plainForms:
            raise exception.ConversionError(
                "Converting to plain forms failed for '%s'." % searchStr)

        return self._plainForms

    def _getWildcardForms(self, searchStr, **options):
        if self._getWildcardFormsOptions != (searchStr, options):
            decompEntities = self._getPlainForms(searchStr, **options)

            self._wildcardForms = []
            for entities in decompEntities:
                wildcardEntities = []
                for entity in entities:
                    if not isinstance(entity, basestring):
                        entity, plainEntity, tone = entity
                        if plainEntity is not None and tone is None:
                            entity = self._createTonalEntityWildcard(
                                plainEntity)
                        wildcardEntities.append(entity)
                    elif self._supportWildcards:
                        wildcardEntities.extend(
                            self._parseWildcardString(entity))
                    else:
                        searchEntities.extend(list(entity))

                self._wildcardForms.append(wildcardEntities)

        return self._wildcardForms

    def _hasWildcardForms(self, searchStr, **options):
        wildcardForms = self._getWildcardForms(searchStr, **options)
        return any(any((not isinstance(entity, basestring))
            for entity in entities) for entities in wildcardForms)

    def _getSimpleQuery(self, searchStr, **options):
        #assert not self._hasWildcardForms(searchStr, **options)
        wildcardForms = self._getWildcardForms(searchStr, **options)

        simpleReadings = map(' '.join, wildcardForms)
        return simpleReadings

    def _getSimpleMatchFunction(self, searchStr, **options):
        if self._caseInsensitive:
            searchStr = searchStr.lower()
        simpleForms = self._getWildcardForms(searchStr, **options)

        if self._caseInsensitive:
            return (lambda reading: self._getReadingEntities(reading.lower())
                in simpleForms)
        else:
            return (lambda reading: self._getReadingEntities(reading)
                in simpleForms)


class TonelessWildcardReadingSearchStrategy(SimpleReadingSearchStrategy,
    _TonelessReadingWildcardBase):
    u"""
    Reading based search strategy with support for missing tonal information and
    wildcards.

    Example:

        >>> from cjklib import dictionary
        >>> d = dictionary.CEDICT(
        ...     \
readingSearchStrategy=dictionary.TonelessWildcardReadingSearchStrategy())
        >>> [r.Reading for r in d.getForReading('zhidao',\
 toneMarkType='numbers')]
        [u'zh\xec d\u01ceo', u'zh\xed d\u01ceo', u'zh\u01d0 d\u01ceo',\
 u'zh\xed d\xe0o', u'zh\xed d\u01ceo', u'zh\u012b dao']

    @todo Impl: Support readings with toneless base forms but without support
        for missing tone
    """
    def __init__(self, **options):
        SimpleReadingSearchStrategy.__init__(self)
        _TonelessReadingWildcardBase.__init__(self, **options)

    def setDictionaryInstance(self, dictInstance):
        super(TonelessWildcardReadingSearchStrategy,
            self).setDictionaryInstance(dictInstance)
        if not self._hasTonlessSupport():
            raise ValueError(
                "Dictionary's reading not supported for toneless searching")

    def _hasTonlessSupport(self):
        """
        Checks if the dictionary's reading has tonal support and can be searched
        for.
        """
        return (self._readingFactory.isReadingOperationSupported(
                'splitEntityTone', self._dictInstance.READING,
                **self._dictInstance.READING_OPTIONS)
            and self._readingFactory.isReadingOperationSupported('getTones',
                self._dictInstance.READING,
                **self._dictInstance.READING_OPTIONS)
            and None in self._readingFactory.getTones(
                self._dictInstance.READING,
                **self._dictInstance.READING_OPTIONS))

    def getWhereClause(self, column, searchStr, **options):
        if self._hasWildcardForms(searchStr, **options):
            queries = self._getWildcardQuery(searchStr, **options)
            return or_(*[self._like(column, query) for query in queries])
        else:
            # exact lookup
            queries = self._getSimpleQuery(searchStr, **options)
            return or_(*[self._equals(column, query) for query in queries])

    def getMatchFunction(self, searchStr, **options):
        if self._hasWildcardForms(searchStr, **options):
            return self._getWildcardMatchFunction(searchStr, **options)
        else:
            # exact matching, 6x quicker in Cpython for 'tian1an1men2'
            return self._getSimpleMatchFunction(searchStr, **options)

#}
#{ Mixed reading search strategies

class _MixedReadingWildcardBase(_SimpleReadingWildcardBase):
    """
    Wildcard search base class for readings mixed with headword characters.
    """
    class SingleWildcard:
        """
        Wildcard matching one arbitrary reading entity and headword character.
        """
        SQL_LIKE_STATEMENT = '_%'
        SQL_LIKE_STATEMENT_HEADWORD = '_'
        def match(self, entity):
            return entity is not None

    class MultipleWildcard:
        """
        Wildcard matching zero, one or multiple reading entities and headword
        characters.
        """
        SQL_LIKE_STATEMENT = '%'
        SQL_LIKE_STATEMENT_HEADWORD = '%'
        def match(self, entity):
            return True

    class HeadwordWildcard:
        """
        Wildcard matching an exact headword character and one arbitrary reading
        entity.
        """
        def __init__(self, headwordEntity, escape):
            self._headwordEntity = headwordEntity
            self._escape = escape
        def headwordEntity(self):
            return _escapeWildcards(self._headwordEntity, self._escape)
        SQL_LIKE_STATEMENT = '_%'
        SQL_LIKE_STATEMENT_HEADWORD = property(headwordEntity)
        def match(self, entity):
            if entity is None:
                return False
            headwordEntity, _ = entity
            return headwordEntity == self._headwordEntity

    class ReadingWildcard:
        """
        Wildcard matching an exact reading entity and one arbitrary headword
        character.
        """
        def __init__(self, readingEntity, escape):
            self._readingEntity = readingEntity
            self._escape = escape
        def readingEntity(self):
            return _escapeWildcards(self._readingEntity, self._escape)
        SQL_LIKE_STATEMENT = property(readingEntity)
        SQL_LIKE_STATEMENT_HEADWORD = '_'
        def match(self, entity):
            if entity is None:
                return False
            _, readingEntity = entity
            return readingEntity == self._readingEntity

    def __init__(self, supportWildcards=True, **options):
        _SimpleReadingWildcardBase.__init__(self, **options)
        self._supportWildcards = supportWildcards

    def _createReadingWildcard(self, headwordEntity):
        return self.ReadingWildcard(headwordEntity, self.escape)

    def _createHeadwordWildcard(self, readingEntity):
        return self.HeadwordWildcard(readingEntity, self.escape)

    def _parseWildcardString(self, string):
        entities = _SimpleReadingWildcardBase._parseWildcardString(self, string)
        # return pairs for headword and reading
        newEntities = []
        for entity in entities:
            if isinstance(entity, basestring):
                # single entity, assume belonging to headword
                newEntities.append(self._createHeadwordWildcard(entity))
            else:
                newEntities.append(entity)

        return newEntities

    def _getWildcardForms(self, readingStr, **options):
        def isReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isReadingEntity(entity,
                    self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        if self._getWildcardFormsOptions != (readingStr, options):
            self._getWildcardFormsOptions = (readingStr, options)

            decompEntities = self._getReadings(readingStr, **options)

            # separate reading entities from non-reading ones
            self._wildcardForms = []
            for entities in decompEntities:
                searchEntities = []
                hasReadingEntity = hasHeadwordEntity = False
                for entity in entities:
                    if isReadingEntity(entity):
                        hasReadingEntity = True
                        searchEntities.append(
                            self._createReadingWildcard(entity))
                    elif self._supportWildcards:
                        parsedEntities = self._parseWildcardString(entity)
                        searchEntities.extend(parsedEntities)
                        hasHeadwordEntity = hasHeadwordEntity or any(
                            isinstance(entity, self.HeadwordWildcard)
                            for entity in parsedEntities)
                    else:
                        hasHeadwordEntity = True
                        searchEntities.extend(
                            [self._createHeadwordWildcard(c) for c in entity])

                # discard pure reading or pure headword strings as they will be
                #   covered through other strategies
                if hasReadingEntity and hasHeadwordEntity:
                    self._wildcardForms.append(searchEntities)

        return self._wildcardForms

    def _getWildcardHeadword(self, entities):
        """Join chars, taking care of wildcards."""
        entityList = [entity.SQL_LIKE_STATEMENT_HEADWORD for entity in entities]
        return ''.join(entityList)

    def _getWildcardQuery(self, searchStr, **options):
        """Gets a where clause for a search string with wildcards."""
        searchPairs = self._getWildcardForms(searchStr, **options)

        queries = []
        for searchEntities in searchPairs:
            # search clauses
            wildcardHeadword = self._getWildcardHeadword(searchEntities)
            wildcardReading = self._getWildcardReading(searchEntities)

            queries.append((wildcardHeadword, wildcardReading))

        return queries

    def _getWildcardMatchFunction(self, searchStr, **options):
        """Gets a match function for a search string with wildcards."""
        def matchHeadwordReadingPair(headword, reading):
            readingEntities = self._getReadingEntities(reading)

            if len(headword) != len(readingEntities):
                # error in database entry
                return False

            # match against all pairs
            for searchEntities in searchPairs:
                entities = zip(list(headword), readingEntities)
                if self._depthFirstSearch(searchEntities, entities):
                    return True

            return False

        if self._caseInsensitive:
            # assume that conversion of lower case results in lower case
            searchStr = searchStr.lower()
        searchPairs = self._getWildcardForms(searchStr, **options)

        if self._caseInsensitive:
            return lambda h, r: matchHeadwordReadingPair(h, r.lower())
        else:
            return matchHeadwordReadingPair


class MixedWildcardReadingSearchStrategy(SimpleReadingSearchStrategy,
    _MixedReadingWildcardBase):
    """
    Reading search strategy that supplements
    L{SimpleWildcardReadingSearchStrategy} to allow intermixing of readings with
    single characters from the headword. By default wildcard searches are
    supported.

    This strategy complements the basic search strategy. It is not built to
    return results for plain reading or plain headword strings.
    """
    def __init__(self, supportWildcards=True):
        SimpleReadingSearchStrategy.__init__(self)
        _MixedReadingWildcardBase.__init__(self, supportWildcards)

    def getWhereClause(self, headwordColumn, readingColumn, searchStr,
        **options):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by L{getMatchFunction()}.

        @type headwordColumn: SQLAlchemy column instance
        @param headwordColumn: headword column to check against
        @type readingColumn: SQLAlchemy column instance
        @param readingColumn: reading column to check against
        @type searchStr: str
        @param searchStr: search string
        @return: SQLAlchemy clause
        """
        queries = self._getWildcardQuery(searchStr, **options)
        if queries:
            return or_(*[
                    and_(self._like(headwordColumn, headwordQuery),
                        self._like(readingColumn, readingQuery))
                    for headwordQuery, readingQuery in queries])
        else:
            return None

    def getMatchFunction(self, searchStr, **options):
        return self._getWildcardMatchFunction(searchStr, **options)


class _MixedTonelessReadingWildcardBase(_MixedReadingWildcardBase,
    _TonelessReadingWildcardBase):
    """
    Wildcard search base class for readings missing tonal information mixed with
    headword characters.
    """
    class TonelessReadingWildcard:
        """
        Wildcard matching an exact toneless reading entity and one arbitrary
        headword character.
        """
        def __init__(self, plainEntity, escape):
            self._plainEntity = plainEntity
            self._escape = escape
        def tonelessReadingEntity(self):
            return _escapeWildcards(self._plainEntity, self._escape) + '_'
        SQL_LIKE_STATEMENT = property(tonelessReadingEntity)
        SQL_LIKE_STATEMENT_HEADWORD = '_'
        def match(self, entity):
            if entity is None:
                return False
            _, readingEntity = entity
            return (readingEntity == self._plainEntity
                or readingEntity[:-1] == self._plainEntity)

    def __init__(self, supportWildcards=True, **options):
        _MixedReadingWildcardBase.__init__(self, **options)
        _TonelessReadingWildcardBase.__init__(self, **options)
        self._supportWildcards = supportWildcards

    def _createTonelessReadingWildcard(self, plainEntity):
        return self.TonelessReadingWildcard(plainEntity, self.escape)

    def _getWildcardForms(self, readingStr, **options):
        def isReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isReadingEntity(entity,
                    self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        if self._getWildcardFormsOptions != (readingStr, options):
            self._getWildcardFormsOptions = (readingStr, options)

            decompEntities = self._getPlainForms(readingStr, **options)

            # separate reading entities from non-reading ones
            self._wildcardForms = []
            for entities in decompEntities:
                searchEntities = []
                hasReadingEntity = hasHeadwordEntity = False
                for entity in entities:
                    if not isinstance(entity, basestring):
                        hasReadingEntity = True

                        entity, plainEntity, tone = entity
                        if plainEntity is not None and tone is None:
                            searchEntities.append(
                                self._createTonelessReadingWildcard(
                                    plainEntity))
                        else:
                            searchEntities.append(
                                self._createReadingWildcard(entity))
                    elif self._supportWildcards:
                        parsedEntities = self._parseWildcardString(entity)
                        searchEntities.extend(parsedEntities)
                        hasHeadwordEntity = hasHeadwordEntity or any(
                            isinstance(entity, self.HeadwordWildcard)
                            for entity in parsedEntities)
                    else:
                        hasHeadwordEntity = True
                        searchEntities.extend(
                            [self._createHeadwordWildcard(c) for c in entity])

                # discard pure reading or pure headword strings as they will be
                #   covered through other strategies
                if hasReadingEntity and hasHeadwordEntity:
                    self._wildcardForms.append(searchEntities)

        return self._wildcardForms


class MixedTonelessWildcardReadingSearchStrategy(SimpleReadingSearchStrategy,
    _MixedTonelessReadingWildcardBase):
    """
    Reading search strategy that supplements
    L{TonelessWildcardReadingSearchStrategy} to allow intermixing of readings
    missing tonal information with single characters from the headword. By
    default wildcard searches are supported.

    This strategy complements the basic search strategy. It is not built to
    return results for plain reading or plain headword strings.
    """
    def __init__(self, supportWildcards=True):
        SimpleReadingSearchStrategy.__init__(self)
        _MixedTonelessReadingWildcardBase.__init__(self, supportWildcards)

    def getWhereClause(self, headwordColumn, readingColumn, searchStr,
        **options):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by L{getMatchFunction()}.

        @type headwordColumn: SQLAlchemy column instance
        @param headwordColumn: headword column to check against
        @type readingColumn: SQLAlchemy column instance
        @param readingColumn: reading column to check against
        @type searchStr: str
        @param searchStr: search string
        @return: SQLAlchemy clause
        """
        queries = self._getWildcardQuery(searchStr, **options)
        if queries:
            return or_(*[
                    and_(self._like(headwordColumn, headwordQuery),
                        self._like(readingColumn, readingQuery))
                    for headwordQuery, readingQuery in queries])
        else:
            return None

    def getMatchFunction(self, searchStr, **options):
        return self._getWildcardMatchFunction(searchStr, **options)

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
            self.db = DatabaseConnector.getDBConnector(databaseUrl)
            """L{DatabaseConnector} instance"""

        if 'entryFactory' in options:
            self.entryFactory = options['entryFactory']
        else:
            self.entryFactory = TupleFactory()
            """Factory for formatting row entries."""
        if hasattr(self.entryFactory, 'setDictionaryInstance'):
            self.entryFactory.setDictionaryInstance(self)

        self.columnFormatStrategies = options.get('columnFormatStrategies', {})
        """Strategies for formatting columns."""
        for column in self.columnFormatStrategies.values():
            if hasattr(column, 'setDictionaryInstance'):
                column.setDictionaryInstance(self)

        if 'headwordSearchStrategy' in options:
            self.headwordSearchStrategy = options['headwordSearchStrategy']
        else:
            self.headwordSearchStrategy = WildcardSearchStrategy()
            """Strategy for searching readings."""
        if hasattr(self.headwordSearchStrategy, 'setDictionaryInstance'):
            self.headwordSearchStrategy.setDictionaryInstance(self)

        if 'readingSearchStrategy' in options:
            self.readingSearchStrategy = options['readingSearchStrategy']
        else:
            self.readingSearchStrategy = WildcardSearchStrategy()
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
            self.translationSearchStrategy = WildcardTranslationSearchStrategy()
            """Strategy for searching translations."""
        if hasattr(self.translationSearchStrategy, 'setDictionaryInstance'):
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
    def getAvailableDictionaries(dbConnectInst=None):
        """
        Returns a list of available dictionaries for the given database
        connection.

        @type dbConnectInst: instance
        @param dbConnectInst: optional instance of a L{DatabaseConnector}
        @rtype: list of class
        @return: list of dictionary class objects
        """
        dbConnectInst = dbConnectInst or DatabaseConnector.getDBConnector()
        available = []
        for dictionaryClass in BaseDictionary.getDictionaryClasses():
            if dictionaryClass.available(dbConnectInst):
                available.append(dictionaryClass)

        return available

    @classmethod
    def getDictionaryClass(cls, dictionaryName):
        """
        Get a dictionary class by dictionary name.

        @rtype: type
        @return: dictionary class
        """
        if not hasattr(cls, '_dictionaryMap'):
            cls._dictionaryMap = dict([(dictCls.PROVIDES, dictCls)
                for dictCls in cls.getDictionaryClasses()])

        if dictionaryName not in cls._dictionaryMap:
            raise ValueError('Not a supported dictionary')
        return cls._dictionaryMap[dictionaryName]

    @classmethod
    def getDictionary(cls, dictionaryName, **options):
        """
        Get a dictionary instance by dictionary name.

        @rtype: type
        @return: dictionary instance
        """
        dictCls = cls.getDictionaryClass(dictionaryName)
        return dictCls(**options)

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
            options['entryFactory'] = NamedTupleFactory()
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = SimpleWildcardTranslationSearchStrategy()
        super(EDICTStyleDictionary, self).__init__(**options)

        if not self.available(self.db):
            raise ValueError("Table '%s' for dictionary does not exist"
                % self.DICTIONARY_TABLE)

    @classmethod
    def available(cls, dbConnectInst):
        return (cls.DICTIONARY_TABLE
            and dbConnectInst.hasTable(cls.DICTIONARY_TABLE))

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
            try:
                orderByCols = [dictionaryTable.c[col] for col in orderBy]
            except KeyError:
                raise ValueError("Invalid 'ORDER BY' columns specified: '%s'"
                    % "', '".join(orderBy))

        # lookup in db
        results = self.db.selectRows(
            select([dictionaryTable.c[col] for col in self.COLUMNS],
                whereClause, distinct=True).order_by(*orderByCols).limit(limit))

        # filter
        if filters:
            results = filter(_getFilterFunction(filters), results)

        # format readings and translations
        for column, formatStrategy in self.columnFormatStrategies.items():
            columnIdx = self.COLUMNS.index(column)
            for idx in range(len(results)):
                rowList = list(results[idx])
                rowList[columnIdx] = formatStrategy.format(rowList[columnIdx])
                results[idx] = tuple(rowList)

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
    def __init__(self, **options):

        columnFormatStrategies = options.get('columnFormatStrategies', {})
        if 'Reading' not in columnFormatStrategies:
            columnFormatStrategies['Reading'] = ReadingConversionStrategy()
            options['columnFormatStrategies'] = columnFormatStrategies
        if 'readingSearchStrategy' not in options:
            options['readingSearchStrategy'] \
                = SimpleWildcardReadingSearchStrategy()
        if 'mixedReadingSearchStrategy' not in options:
            options['mixedReadingSearchStrategy'] \
                = MixedWildcardReadingSearchStrategy()
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
                = CEDICTWildcardTranslationSearchStrategy()
        super(CEDICTGR, self).__init__(**options)


class CEDICT(EDICTStyleEnhancedReadingDictionary):
    u"""
    CEDICT dictionary access.

    Example
    =======

    Get dictionary entries with reading IPA:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(
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
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = CEDICTWildcardTranslationSearchStrategy()
        if 'readingSearchStrategy' not in options:
            options['readingSearchStrategy'] \
                = TonelessWildcardReadingSearchStrategy()
        if 'mixedReadingSearchStrategy' not in options:
            options['mixedReadingSearchStrategy'] \
                = MixedTonelessWildcardReadingSearchStrategy()
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
        if 'translationSearchStrategy' not in options:
            options['translationSearchStrategy'] \
                = HanDeDictWildcardTranslationSearchStrategy()
        super(HanDeDict, self).__init__(**options)


class CFDICT(HanDeDict):
    """
    CFDICT dictionary access.

    @see: L{CFDICTBuilder}
    """
    PROVIDES = 'CFDICT'
    DICTIONARY_TABLE = 'CFDICT'

