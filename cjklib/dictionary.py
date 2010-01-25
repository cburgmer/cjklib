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
information is supported and can augment the basic reading search.

Headword search strategies
--------------------------
Searching for headwords is the most simple among the three. Exact searches are
provided by class L{ExactSearchStrategy}. By default class
L{WildcardHeadwordSearchStrategy} is employed which offers wildcard searches.

Reading search strategies
-------------------------
Readings have more complex and unique representations. Several classes are
provided here: L{ExactSearchStrategy} again can be used for exact matches, L{WildcardReadingSearchStrategy} extends this strategy with wildcard searches.
L{SimpleReadingSearchStrategy} and L{SimpleWildcardReadingSearchStrategy}
provide similar searching for readings whose entities are separated by spaces
(e.g. CEDICT). The latter strategy is used by dictionaries with romanisations.
A more complex search is provided by L{TonelessReadingSearchStrategy} which
offers search which supports missing tonal information.

Translation search strategies
-----------------------------
A basic search is provided by L{SingleEntryTranslationSearchStrategy} which
finds an exact entry in a list of entries separated by slashes ('X{/}'). More
flexible searching is provided by L{SimpleTranslationSearchStrategy} and
L{SimpleWildcardTranslationSearchStrategy} which take into account additional
information placed in parantheses. These classes have even more special
implementations adapted to formats found in dictionaries I{CEDICT} and
I{HanDeDict}.

More complex ones could be implemented on the basis of extending the underlying
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

    >>> d = CEDICT()
    >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
    []
    >>> d = CEDICT(readingSearchStrategy=TonelessReadingSearchStrategy())
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
    ...     d = CEDICT(readingSearchStrategy=TonelessReadingSearchStrategy(),
    ...         entryFactory=UnifiedHeadwordEntryFactory())
    ...     result = d.getFor(string, reading=reading, **options)
    ...     # print
    ...     for e in result:
    ...         print e.Headword, e.Reading, e.Translation
    ...
    >>> search('Nanjing', 'Pinyin')
    南京 Nán jīng /Nanjing subprovincial city on the Changjiang, capital of
    Jiangsu province 江蘇|江苏/capital of China at different historical periods/
    南靖 Nán jìng /Najing county in Zhangzhou 漳州[Zhang1 zhou1], Fujian/
    宁（寧） níng /peaceful/rather/Ningxia (abbr.)/Nanjing (abbr.)/surname Ning/

@todo Fix: letter case
@todo Impl: Use Iterators?
@todo Impl: Pass entry factories directly to search method in DatabaseConnector
@todo Fix:  Don't "correct" non-reading entities in HanDeDict in builder
@todo Impl: Allow simple FTS3 searching as build support is already provided.
"""

import re
import types

from sqlalchemy import select
from sqlalchemy.sql import and_, or_

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

class ExactSearchStrategy(object):
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
        return column == searchStr

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
        return lambda cell: searchStr == cell


class WildcardBase(object):
    """
    Wildcard search base class. Provides wildcard conversion and regular
    expression preparation methods.
    """
    def __init__(self, singleCharacter='_', multipleCharacters='%',
        escape='\\'):
        self.singleCharacter = singleCharacter
        self.multipleCharacters = multipleCharacters
        self.escape = escape
        if len(self.escape) != 1:
            raise ValueError("Escape character %s needs to have length 1"
                % repr(self.escape))

    def hasWildcardCharacters(self, searchStr):
        """
        Returns C{True} if a wildcard character is included in the search
        string. Escaping is not considered.
        """
        return (self.singleCharacter in searchStr
            or self.multipleCharacters in searchStr)

    def _getWildcardString(self, searchStr):
        param = {'esc': re.escape(self.escape),
            'single': re.escape(self.singleCharacter),
            'multiple': re.escape(self.multipleCharacters)}
        # substitute wildcard characters, make sure escape is handled properly
        if self.singleCharacter != '_':
            searchStr = re.sub(
                '(?<!%(esc)s)((?:%(esc)s{2}|[^%(esc)s])*?)%(single)s' % param,
                r'\1_', searchStr)
        if self.multipleCharacters != '%':
            searchStr = re.sub(
                '(?<!%(esc)s)((?:%(esc)s{2}|[^%(esc)s])*?)%(multiple)s' % param,
                r'\1%', searchStr)

        return searchStr

    def _prepareWildcardRegex(self, searchStr):
        # TODO allow '/' to fill in for wildcard?
        param = {'esc': re.escape(self.escape),
            'single': re.escape(self.singleCharacter),
            'multiple': re.escape(self.multipleCharacters)}
        # substitute wildcard characters and escape plain parts, make sure
        #   escape is handled properly
        parts = re.split(r'(\\{2}|\\?(?:%(single)s|%(multiple)s))' % param,
            searchStr)

        preparedParts = []
        for part in parts:
            if part == self.singleCharacter:
                preparedParts.append('.')
            elif part == self.multipleCharacters:
                preparedParts.append('.*')
            else:
                preparedParts.append(re.escape(part))

        return ''.join(preparedParts)

    def _getWildcardRegex(self, searchStr):
        return re.compile('^' + self._prepareWildcardRegex(searchStr) + '$')

#}
#{ Headword search strategies

class WildcardHeadwordSearchStrategy(ExactSearchStrategy, WildcardBase):
    """Basic headword search strategy with support for wildcards."""
    def getWhereClause(self, column, searchStr):
        if self.hasWildcardCharacters(searchStr):
            wildcardSearchStr = self._getWildcardString(searchStr)
            return column.like(wildcardSearchStr, escape=self.escape)
        else:
            # simple routine is faster
            return ExactSearchStrategy.getWhereClause(self, column, searchStr)

    def getMatchFunction(self, searchStr):
        if self.hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda headword: regex.search(headword) is not None
        else:
            # simple routine is faster
            return ExactSearchStrategy.getMatchFunction(self, searchStr)

#}
#{ Translation search strategies

class SingleEntryTranslationSearchStrategy(ExactSearchStrategy):
    """Basic translation search strategy."""
    def getWhereClause(self, column, searchStr):
        # TODO escape searchStr, no wildcards inside
        return column.like('%' + searchStr + '%')

    def getMatchFunction(self, searchStr):
        return lambda translation: searchStr in translation.split('/')


class WildcardTranslationSearchStrategy(SingleEntryTranslationSearchStrategy,
    WildcardBase):
    """Basic translation search strategy with support for wildcards."""
    def _getWildcardRegex(self, searchStr):
        return re.compile('/' + self._prepareWildcardRegex(searchStr) + '/')

    def getWhereClause(self, column, searchStr):
        wildcardSearchStr = self._getWildcardString(searchStr)
        if not wildcardSearchStr.startswith('%'):
            wildcardSearchStr = '%' + wildcardSearchStr
        if not searchStr.endswith('%'):
            wildcardSearchStr = wildcardSearchStr + '%'
        return column.like(wildcardSearchStr, escape=self.escape)

    def getMatchFunction(self, searchStr):
        if self.hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(readingStr)
            return lambda translation: regex.search(translation) is not None
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
        regex = re.compile('/' + '(\s+|\([^\)]+\))*' + re.escape(searchStr)
            + '(\s+|\([^\)]+\))*' + '/')

        return lambda translation: regex.search(translation) is not None


class SimpleWildcardTranslationSearchStrategy(
    WildcardTranslationSearchStrategy, SimpleTranslationSearchStrategy):
    """
    Simple translation search strategy with support for wildcards. Takes into
    account additions put in parentheses.
    """
    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith('%'):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith('%'):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return re.compile('/' + regexStr + '/')

    def getMatchFunction(self, searchStr):
        if self.hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(readingStr)
            return lambda translation: regex.search(translation) is not None
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
        regex = re.compile('/' + '(\s+|\([^\)]+\))*' + re.escape(searchStr)
            + '(\s+|\([^\)]+\))*' + '[/,]')

        return lambda translation: regex.search(translation) is not None


class CEDICTWildcardTranslationSearchStrategy(
    WildcardTranslationSearchStrategy, CEDICTTranslationSearchStrategy):
    """
    CEDICT translation based search strategy with support for wildcards. Takes
    into account additions put in parentheses and appended information separated
    by a comma.
    """
    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith('%'):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith('%'):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return re.compile('/' + regexStr + '[/,]')

    def getMatchFunction(self, searchStr):
        if self.hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda translation: regex.search(translation) is not None
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
        regex = re.compile('/((\([^\)]+\)|[^\(])+'
            + '(?!; Bsp.: [^/]+?--[^/]+)[\,\;\.\?\!])?' + '(\s+|\([^\)]+\))*'
            + re.escape(searchStr) + '(\s+|\([^\)]+\))*' + '[/\,\;\.\?\!]')

        return lambda translation: regex.search(translation) is not None


class HanDeDictWildcardTranslationSearchStrategy(
    WildcardTranslationSearchStrategy, HanDeDictTranslationSearchStrategy):
    """
    HanDeDict translation based search strategy with support for wildcards.
    Takes into account additions put in parentheses and appended information
    separated by a comma.
    """
    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith('%'):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith('%'):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return re.compile('/((\([^\)]+\)|[^\(])+'
            + '(?!; Bsp.: [^/]+?--[^/]+)[\,\;\.\?\!])?' + regexStr
            + '[/\,\;\.\?\!]')

    def getMatchFunction(self, searchStr):
        if self.hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(searchStr)
            return lambda translation: regex.search(translation) is not None
        else:
            # simple routine is faster
            return HanDeDictTranslationSearchStrategy.getMatchFunction(self,
                searchStr)

#}
#{ Reading search strategies

class WildcardReadingSearchStrategy(ExactSearchStrategy, WildcardBase):
    """Basic reading search strategy with support for wildcards."""
    def _getWildcardRegex(self, searchStr):
        return re.compile(self._prepareWildcardRegex(searchStr) + '$')

    def getWhereClause(self, column, searchStr, **options):
        if self.hasWildcardCharacters(searchStr):
            wildcardReadingStr = self._getWildcardString(readingStr)
            return column.like(wildcardReadingStr, escape=self.escape)
        else:
            # simple routine is faster
            return ExactSearchStrategy.getWhereClause(self, column, searchStr)

    def getMatchFunction(self, searchStr, **options):
        if self.hasWildcardCharacters(searchStr):
            regex = self._getWildcardRegex(readingStr)
            return lambda reading: regex.search(reading) is not None
        else:
            # simple routine is faster
            return ExactSearchStrategy.getMatchFunction(self, searchStr)


class SimpleReadingSearchStrategy(ExactSearchStrategy):
    """
    Simple reading search strategy. Converts search string to the dictionary
    reading and separates entities by space.
    @todo Fix: How to handle non-reading entities?
    """
    def __init__(self):
        self._getReadingsOptions = None

    def setDictionaryInstance(self, dictInstance):
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

        return or_(*[column == ' '.join(entities)
            for entities in decompEntities])

    def getMatchFunction(self, searchStr, **options):
        decompEntities = self._getReadings(searchStr, **options)

        matchSet = set([' '.join(entities) for entities in decompEntities])

        return lambda reading: reading in matchSet


class SimpleWildcardReadingSearchStrategy(SimpleReadingSearchStrategy,
    WildcardBase):
    """
    Simple reading search strategy with support for wildcards. Converts search
    string to the dictionary reading and separates entities by space.
    """
    def __init__(self, **options):
        SimpleReadingSearchStrategy.__init__(self)
        WildcardBase.__init__(self, **options)

    def _getWildcardForms(self, decompEntities):
        def isReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isReadingEntity(entity,
                    self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        param = {'esc': re.escape(self.escape),
            'single': re.escape(self.singleCharacter),
            'multiple': re.escape(self.multipleCharacters)}
        # substitute wildcard characters and escape plain parts, make sure
        #   escape is handled properly
        wildcardRegex = re.compile(
            r'( |\\{2}|\\?(?:%(single)s|%(multiple)s))' % param)

        wildcardForms = []
        for entities in decompEntities:
            wildcardEntities = []
            for entity in entities:
                if isReadingEntity(entity):
                    wildcardEntities.append(entity)
                else:
                    for part in wildcardRegex.split(entity):
                        if part == self.singleCharacter:
                            wildcardEntities.append('_%')
                        elif part == self.multipleCharacters:
                            wildcardEntities.append('%')
                        else:
                            # one char each
                            wildcardEntities.extend(part.strip())
            wildcardForms.append(wildcardEntities)

        return wildcardForms

    def getWhereClause(self, column, searchStr, **options):
        def getWildcardReading(entities):
            entityList = []
            for entity in entities:
                # insert space to separate reading entities, but only if we are
                #   not looking for a wildcard with a possibly empty match
                if entityList and entityList[-1] != '%' and entity != '%':
                    entityList.append(' ')
                entityList.append(entity)
            return ''.join(entityList)

        if self.hasWildcardCharacters(searchStr):
            decompEntities = self._getReadings(searchStr, **options)

            wildcardForms = self._getWildcardForms(decompEntities)
            wildcardReadings = map(getWildcardReading, wildcardForms)

            return or_(*[column.like(reading, escape=self.escape)
                for reading in wildcardReadings])
        else:
            # simple routine is faster
            return SimpleReadingSearchStrategy.getWhereClause(self, column,
                searchStr, **options)

    def getMatchFunction(self, searchStr, **options):
        def getReadingEntities(reading):
            # simple and efficient method for CEDICT type dictionaries
            return reading.split(' ')

        def depthFirstSearch(searchEntities, entities):
            if not searchEntities:
                if not entities:
                    return True
                else:
                    return False
            if searchEntities[0] == '%':
                if depthFirstSearch(searchEntities[1:], entities):
                    # try consume no entity
                    return True
                else:
                    # consume one entity
                    return depthFirstSearch(searchEntities, entities[1:])
            elif searchEntities[0] == '_%':
                # consume one entity
                return depthFirstSearch(searchEntities[1:], entities[1:])
            elif entities and searchEntities[0] == entities[0]:
                return depthFirstSearch(searchEntities[1:], entities[1:])
            else:
                return False

        def matchReadingEntities(reading):
            readingEntities = getReadingEntities(reading)

            # match against all pairs
            for entities in wildcardForms:
                if depthFirstSearch(entities, readingEntities):
                    return True

            return False

        if self.hasWildcardCharacters(searchStr):
            decompEntities = self._getReadings(searchStr, **options)

            wildcardForms = self._getWildcardForms(decompEntities)

            return matchReadingEntities
        else:
            # simple routine is faster
            return SimpleReadingSearchStrategy.getMatchFunction(self, searchStr,
                **options)


class TonelessReadingSearchStrategy(SimpleReadingSearchStrategy):
    """
    Reading based search strategy with support for missing tonal information.
    """
    # TODO implement wildcard version
    def getWhereClause(self, column, searchStr, **options):
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

        decompEntities = self._getReadings(searchStr, **options)

        fromReading = options.get('reading', self._dictInstance.READING)
        # if reading is tonal and includes support for missing tones, handle
        if (self._readingFactory.isReadingOperationSupported('splitEntityTone',
            fromReading, **options)
            and self._readingFactory.isReadingOperationSupported('getTones',
                fromReading, **options)
            and None in self._readingFactory.getTones(fromReading, **options)):
            # look for missing tone information and use wildcards
            searchEntities = getWildcardForms(decompEntities)

            whereClause = or_(*[column.like(' '.join(entities))
                for entities in searchEntities])
        else:
            whereClause = or_(*[column == ' '.join(entities)
                for entities in decompEntities])

        return whereClause

    def getMatchFunction(self, searchStr, **options):
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
                    tonalEntities.append(self._readingFactory.getTonalEntity(
                        plainEntity, tone, fromReading, **options))
                except exception.InvalidEntityError:
                    pass
            return tonalEntities

        decompEntities = self._getReadings(searchStr, **options)

        fromReading = options.get('reading', self._dictInstance.READING)
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
#{ Mixed reading search strategies

class MixedReadingSearchStrategy(SimpleReadingSearchStrategy):
    """
    Reading search strategy that extends L{SimpleReadingSearchStrategy} to allow
    intermixing of readings with single characters from the headword.

    This strategy complements the basic search strategy. It is not built to
    return results for plain reading or plain headword strings.
    """
    # TODO implement wildcard version
    def __init__(self):
        super(MixedReadingSearchStrategy, self).__init__()
        self._getReadingsSearchPairsOptions = None

    def _getReadingsSearchPairs(self, readingStr, **options):
        def isReadingEntity(entity, cache={}):
            if entity not in cache:
                cache[entity] = self._readingFactory.isReadingEntity(entity,
                    self._dictInstance.READING,
                    **self._dictInstance.READING_OPTIONS)
            return cache[entity]

        if self._getReadingsSearchPairsOptions != (readingStr, options):
            self._getReadingsSearchPairsOptions = (readingStr, options)

            decompEntities = self._getReadings(readingStr, **options)

            # separate reading entities from non-reading ones
            self._searchPairs = []
            for entities in decompEntities:
                searchEntities = []
                hasReadingEntity = hasHeadwordEntity = False
                for entity in entities:
                    if isReadingEntity(entity):
                        hasReadingEntity = True
                        searchEntities.append((None, entity))
                    else:
                        hasHeadwordEntity = True
                        searchEntities.extend([(c, None) for c in entity])

                # discard pure reading or pure headword strings as they will be
                #   covered through other strategies
                if hasReadingEntity and hasHeadwordEntity:
                    self._searchPairs.append(searchEntities)

        return self._searchPairs

    def getWhereClause(self, headwordColumn, readingColumn, searchStr,
        **options):

        searchPairs = self._getReadingsSearchPairs(searchStr, **options)

        fromReading = options.get('reading', self._dictInstance.READING)
        clauses = []
        for searchEntities in searchPairs:
            # search clauses
            headwordSearchEntities = []
            readingSearchEntities = []
            for headwordEntity, readingEntity in searchEntities:
                if headwordEntity is None:
                    headwordSearchEntities.append('_')
                else:
                    headwordSearchEntities.append(headwordEntity)
                if readingEntity is None:
                    readingSearchEntities.append('_%')
                else:
                    readingSearchEntities.append(readingEntity)

            headwordClause = headwordColumn.like(
                ''.join(headwordSearchEntities))
            readingClause = readingColumn.like(' '.join(readingSearchEntities))

            clauses.append(and_(headwordClause, readingClause))

        if clauses:
            return or_(*clauses)
        else:
            return None

    def getMatchFunction(self, searchStr, **options):
        def getReadingEntities(reading):
            # simple and efficient method for CEDICT type dictionaries
            return reading.split(' ')

        def matchHeadwordReadingPair(headword, reading):
            readingEntities = getReadingEntities(reading)

            # match against all pairs
            for searchEntities in searchPairs:
                for idx, entryTuple in enumerate(searchEntities):
                    headwordEntity, readingEntity = entryTuple
                    if (headwordEntity is not None
                        and headword[idx] != headwordEntity):
                        break
                    if (readingEntity is not None
                        and readingEntities[idx] != readingEntity):
                        break
                else:
                    return True

            return False

        searchPairs = self._getReadingsSearchPairs(searchStr, **options)

        return matchHeadwordReadingPair

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
            self.headwordSearchStrategy = WildcardHeadwordSearchStrategy()
            """Strategy for searching readings."""
        if hasattr(self.headwordSearchStrategy, 'setDictionaryInstance'):
            self.headwordSearchStrategy.setDictionaryInstance(self)

        if 'readingSearchStrategy' in options:
            self.readingSearchStrategy = options['readingSearchStrategy']
        else:
            self.readingSearchStrategy = WildcardReadingSearchStrategy()
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

    def getForHeadword(self, headwordStr, limit=None, orderBy=None):
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

    def getForTranslation(self, translationStr, limit=None, orderBy=None):
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

