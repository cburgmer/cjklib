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
Search strategies for dictionaries.

.. todo::
    * Impl: Allow simple FTS3 searching as build support is already provided.
"""

__all__ = [
    "setDefaultWildcards",
    # base search strategies
    "Exact", "Wildcard",
    # translation search strategies
    "SingleEntryTranslation", "WildcardTranslation", "SimpleTranslation",
    "SimpleWildcardTranslation", "CEDICTTranslation",
    "CEDICTWildcardTranslation", "HanDeDictTranslation",
    "HanDeDictWildcardTranslation",
    # reading search strategies
    "SimpleReading", "SimpleWildcardReading", "TonelessWildcardReading",
    # mixed reading search strategies
    "MixedWildcardReading", "MixedTonelessWildcardReading",
    ]

import re
import string

from sqlalchemy.sql import and_, or_
from sqlalchemy.sql.expression import func

from cjklib.reading import ReadingFactory
from cjklib import exception
from cjklib.util import toCodepoint, getCharacterList

# Python 2.4 support
if not hasattr(__builtins__, 'any'):
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

_FULL_WIDTH_MAP = dict((ord(halfWidth), unichr(ord(halfWidth) + 65248))
    for halfWidth in (string.ascii_uppercase + string.ascii_lowercase))
"""Mapping of halfwidth characters to fullwidth."""

def _mapToFullwidth(string):
    u"""Maps halfwidth characters to fullwidth, e.g. ``U`` to ``Ｕ``."""
    if isinstance(string, str):
        return string
    else:
        return string.translate(_FULL_WIDTH_MAP)

defaultSingleCharacter = '_'
defaultMultipleCharacters = '%'

def setDefaultWildcards(singleCharacter='_', multipleCharacters='%'):
    """Convenience method to change the default wildcard characters globally."""
    global defaultSingleCharacter, defaultMultipleCharacters
    defaultSingleCharacter = singleCharacter
    defaultMultipleCharacters = multipleCharacters

#{ Common search classes

class _CaseInsensitiveBase(object):
    """Base class providing methods for case insensitive searches."""
    def __init__(self, caseInsensitive=False, sqlCollation=None, escape='\\',
        **options):
        """
        :type caseInsensitive: bool
        :param caseInsensitive: if ``True``, latin characters match their
            upper/lower case equivalent, if ``False`` case sensitive matches
            will be made (default)
        :type sqlCollation: str
        :param sqlCollation: optional collation to use on columns in SQL queries
        :type escape: str
        :param escape: character used to escape command characters
        """
        self._caseInsensitive = caseInsensitive
        self._sqlCollation = sqlCollation
        self.__escape = escape

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
        escape = escape or self.__escape
        if self._sqlCollation:
            column = column.collate(self._sqlCollation)

        if self._needsIlike:
            # Uses ILIKE for PostgreSQL and falls back to "lower() LIKE lower()"
            #   for other engines
            return column.ilike('%' + query + '%', escape=escape)
        else:
            return column.contains(query, escape=escape)

    def _like(self, column, query, escape=None):
        escape = escape or self.__escape
        if self._sqlCollation:
            column = column.collate(self._sqlCollation)

        if self._needsIlike:
            # Uses ILIKE for PostgreSQL and falls back to "lower() LIKE lower()"
            #   for other engines
            return column.ilike(query, escape=escape)
        else:
            return column.like(query, escape=escape)

    def _compileRegex(self, regexString):
        if self._caseInsensitive:
            regexString = '(?ui)' + regexString
        else:
            regexString = '(?u)' + regexString
        return re.compile(regexString)


class Exact(_CaseInsensitiveBase):
    """Simple search strategy class."""
    def __init__(self, fullwidthCharacters=False, **options):
        """
        :type caseInsensitive: bool
        :param caseInsensitive: if ``True``, latin characters match their
            upper/lower case equivalent, if ``False`` case sensitive matches
            will be made (default)
        :type sqlCollation: str
        :param sqlCollation: optional collation to use on columns in SQL queries
        :type fullwidthCharacters: bool
        :param fullwidthCharacters: if ``True`` alphabetic halfwidth
            characters are converted to fullwidth.
        """
        _CaseInsensitiveBase.__init__(self, **options)
        self._fullwidthCharacters = fullwidthCharacters

    def getWhereClause(self, column, searchStr):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by
        :meth:`~cjklib.dictionary.search.Exact.getMatchFunction`.

        :type column: SQLAlchemy column instance
        :param column: column to check against
        :type searchStr: str
        :param searchStr: search string
        :return: SQLAlchemy clause
        """
        if self._fullwidthCharacters:
            searchStr = _mapToFullwidth(searchStr)

        return self._equals(column, searchStr)

    def getMatchFunction(self, searchStr):
        """
        Gets a function that returns ``True`` if the entry's cell content
        matches the search string.

        This method provides the sufficient condition for a match. Note that
        matches from other SQL clauses might get included which do not fulfill
        the conditions of
        :meth:`~cjklib.dictionary.search.Exact.getWhereClause`.

        :type searchStr: str
        :param searchStr: search string
        :rtype: function
        :return: function that returns ``True`` if the entry is a match
        """
        if self._fullwidthCharacters:
            searchStr = _mapToFullwidth(searchStr)

        if self._caseInsensitive:
            searchStr = searchStr.lower()
            return lambda cell: searchStr == cell.lower()
        else:
            return lambda cell: searchStr == cell


class _WildcardBase(object):
    """
    Wildcard search base class. Provides wildcard conversion and regular
    expression preparation methods.

    Wildcards can be used as placeholders in searches. By default ``'_'``
    substitutes a single character while ``'%'`` matches zero, one or multiple
    characters. Searches for the actual characters (here ``'_'`` and ``'%'``)
    need to mask those occurences by the escape character, by default a
    backslash ``'\\'``, which needs escaping itself.
    """
    class SingleWildcard:
        """Wildcard matching exactly one character."""
        SQL_LIKE_STATEMENT = '_'
        REGEX_PATTERN = '.'

    class MultipleWildcard:
        """Wildcard matching zero, one or multiple characters."""
        SQL_LIKE_STATEMENT = '%'
        REGEX_PATTERN = '.*'

    def __init__(self, singleCharacter=None, multipleCharacters=None,
        escape='\\', **options):
        """
        :type escape: str
        :param escape: character used to escape command characters
        :type singleCharacter: str
        :param singleCharacter: wildcard character matching a single arbitrary
            character
        :type multipleCharacters: str
        :param multipleCharacters: wildcard character matching zero, one or many
            arbitrary characters
        """
        self.singleCharacter = singleCharacter or defaultSingleCharacter
        self.multipleCharacters = (multipleCharacters
            or defaultMultipleCharacters)
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
        Returns ``True`` if a wildcard character is included in the search
        string.
        """
        for idx, part in enumerate(self._wildcardRegex.split(searchStr)):
            if (idx % 2 == 1
                and part in (self.singleCharacter, self.multipleCharacters)):
                return True
        return False

    def _unescape(self, searchStr):
        """
        Removes escapes from a search string.
        """
        cleaned = []
        for idx, part in enumerate(self._wildcardRegex.split(searchStr)):
            if (idx % 2 == 1 and part[0] == self.escape
                and part[1:] in (self.escape, self.singleCharacter,
                    self.multipleCharacters)):
                part = part[1:]
            cleaned.append(part)

        return ''.join(cleaned)

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


class Wildcard(Exact, _WildcardBase):
    """Basic headword search strategy with support for wildcards."""
    def __init__(self, fullwidthCharacters=False, **options):
        """
        :type caseInsensitive: bool
        :param caseInsensitive: if ``True``, latin characters match their
            upper/lower case equivalent, if ``False`` case sensitive matches
            will be made (default)
        :type sqlCollation: str
        :param sqlCollation: optional collation to use on columns in SQL queries
        :type fullwidthCharacters: bool
        :param fullwidthCharacters: if ``True`` alphabetic halfwidth
            characters are converted to fullwidth.
        :type escape: str
        :param escape: character used to escape command characters
        :type singleCharacter: str
        :param singleCharacter: wildcard character matching a single arbitrary
            character
        :type multipleCharacters: str
        :param multipleCharacters: wildcard character matching zero, one or many
            arbitrary characters
        """
        Exact.__init__(self, fullwidthCharacters, **options)
        _WildcardBase.__init__(self, **options)

    def getWhereClause(self, column, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            if self._fullwidthCharacters:
                searchStr = _mapToFullwidth(searchStr)

            wildcardSearchStr = self._getWildcardQuery(searchStr)
            return self._like(column, wildcardSearchStr)
        else:
            # simple routine is faster
            return Exact.getWhereClause(self, column, self._unescape(searchStr))

    def getMatchFunction(self, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            if self._fullwidthCharacters:
                searchStr = _mapToFullwidth(searchStr)

            regex = self._getWildcardRegex(searchStr)
            return lambda headword: (headword is not None
                and regex.search(headword) is not None)
        else:
            # simple routine is faster
            return Exact.getMatchFunction(self, self._unescape(searchStr))

#}
#{ Translation search strategies

class SingleEntryTranslation(Exact):
    """Basic translation search strategy."""
    def __init__(self, caseInsensitive=True, **options):
        Exact.__init__(self, caseInsensitive=caseInsensitive,
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


class WildcardTranslation(SingleEntryTranslation,
    _WildcardBase):
    """Basic translation search strategy with support for wildcards."""
    def __init__(self, *args, **options):
        SingleEntryTranslation.__init__(self, *args, **options)
        _WildcardBase.__init__(self, *args, **options)

    def _getWildcardRegex(self, searchStr):
        return self._compileRegex('/' + self._prepareWildcardRegex(searchStr)
            + '/')

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
            return SingleEntryTranslation.getMatchFunction(self,
                self._unescape(searchStr))


class SimpleTranslation(SingleEntryTranslation):
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


class SimpleWildcardTranslation(SingleEntryTranslation,
    _SimpleTranslationWildcardBase):
    """
    Simple translation search strategy with support for wildcards. Takes into
    account additions put in parentheses.
    """
    def __init__(self, *args, **options):
        SingleEntryTranslation.__init__(self, *args, **options)
        _SimpleTranslationWildcardBase.__init__(self, *args, **options)

    def _getWildcardRegex(self, searchStr):
        # TODO '* Tokyo' finds "/(n) Tokyo (current capital of Japan)/(P)/"
        #   but should probably disregard that
        regexStr = self._prepareWildcardRegex(searchStr)
        if not searchStr.startswith(self.multipleCharacters):
            regexStr = '(\s+|\([^\)]+\))*' + regexStr
        if not searchStr.endswith(self.multipleCharacters):
            regexStr = regexStr + '(\s+|\([^\)]+\))*'

        return self._compileRegex('/' + regexStr + '/')

    def getWhereClause(self, column, searchStr):
        wildcardSearchStr = self._getWildcardQuery(searchStr)
        return self._contains(column, wildcardSearchStr)

    def getMatchFunction(self, searchStr):
        regex = self._getWildcardRegex(searchStr)
        return lambda translation: (translation is not None
            and regex.search(translation) is not None)


class CEDICTTranslation(SingleEntryTranslation):
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


class CEDICTWildcardTranslation(SingleEntryTranslation,
    _SimpleTranslationWildcardBase):
    """
    CEDICT translation based search strategy with support for wildcards. Takes
    into account additions put in parentheses and appended information separated
    by a comma.
    """
    def __init__(self, *args, **options):
        SingleEntryTranslation.__init__(self, *args, **options)
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
        regex = self._getWildcardRegex(searchStr)
        return lambda translation: (translation is not None
            and regex.search(translation) is not None)


class HanDeDictTranslation(SingleEntryTranslation):
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


class HanDeDictWildcardTranslation(SingleEntryTranslation,
    _SimpleTranslationWildcardBase):
    """
    HanDeDict translation based search strategy with support for wildcards.
    Takes into account additions put in parentheses and appended information
    separated by a comma.
    """
    def __init__(self, *args, **options):
        SingleEntryTranslation.__init__(self, *args, **options)
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
        regex = self._getWildcardRegex(searchStr)
        return lambda translation: (translation is not None
            and regex.search(translation) is not None)

#}
#{ Reading search strategies

class SimpleReading(Exact):
    """
    Simple reading search strategy. Converts search string to the dictionary
    reading and separates entities by space.

    .. todo::
        * Fix: How to handle non-reading entities?
    """
    def __init__(self, caseInsensitive=True, **options):
        Exact.__init__(self, caseInsensitive=caseInsensitive,
            **options)
        self._getReadingsOptions = None

    def setDictionaryInstance(self, dictInstance):
        super(SimpleReading, self).setDictionaryInstance(
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
                newEntities.extend([e for e in getCharacterList(entity)
                    if e != ' '])

        return newEntities

    def _getReadings(self, readingStr, **options):
        raise NotImplementedError

    def _getWildcardForms(self, searchStr, **options):
        """
        Gets reading decomposition and prepares wildcards. Needs a method
        :meth:`~cjklib.dictionary.search._SimpleReadingWildcardBase._getReadings`
        to do the actual decomposition.
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


class SimpleWildcardReading(SimpleReading,
    _SimpleReadingWildcardBase):
    """
    Simple reading search strategy with support for wildcards. Converts search
    string to the dictionary reading and separates entities by space.
    """
    def __init__(self, **options):
        SimpleReading.__init__(self, **options)
        _SimpleReadingWildcardBase.__init__(self, **options)

    def getWhereClause(self, column, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            queries = self._getWildcardQuery(searchStr, **options)
            return or_(*[self._like(column, query) for query in queries])
        else:
            # simple routine is faster
            return SimpleReading.getWhereClause(self, column,
                self._unescape(searchStr), **options)

    def getMatchFunction(self, searchStr, **options):
        if self._hasWildcardCharacters(searchStr):
            return self._getWildcardMatchFunction(searchStr, **options)
        else:
            # simple routine is faster
            return SimpleReading.getMatchFunction(self,
                self._unescape(searchStr), **options)


class _TonelessReadingWildcardBase(_SimpleReadingWildcardBase):
    """
    Wildcard search base class for tonal readings.
    """
    class TonalEntityWildcard(object):
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
                        wildcardEntities.extend(getCharacterList(entity))

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


class TonelessWildcardReading(SimpleReading,
    _TonelessReadingWildcardBase):
    u"""
    Reading based search strategy with support for missing tonal information and
    wildcards.

    Example:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(readingSearchStrategy=search.TonelessWildcardReading())
        >>> [r.Reading for r in d.getForReading('zhidao',\
 toneMarkType='numbers')]
        [u'zh\xec d\u01ceo', u'zh\xed d\u01ceo', u'zh\u01d0 d\u01ceo',\
 u'zh\xed d\xe0o', u'zh\xed d\u01ceo', u'zh\u012b dao']

    .. todo::
        * Impl: Support readings with toneless base forms but without support
          for missing tone
    """
    def __init__(self, **options):
        SimpleReading.__init__(self, **options)
        _TonelessReadingWildcardBase.__init__(self, **options)

    def setDictionaryInstance(self, dictInstance):
        super(TonelessWildcardReading,
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
    class WildcardPairBase(object):
        SQL_LIKE_STATEMENT_HEADWORD = None
        SQL_LIKE_STATEMENT = None
        def __unicode__(self):
            return '<%s %s, %s>' % (self.__class__.__name__,
                repr(self.SQL_LIKE_STATEMENT_HEADWORD),
                repr(self.SQL_LIKE_STATEMENT))

    class SingleWildcard(WildcardPairBase):
        """
        Wildcard matching one arbitrary reading entity and headword character.
        """
        SQL_LIKE_STATEMENT = '_%'
        SQL_LIKE_STATEMENT_HEADWORD = '_'
        def match(self, entity):
            return entity is not None

    class MultipleWildcard(WildcardPairBase):
        """
        Wildcard matching zero, one or multiple reading entities and headword
        characters.
        """
        SQL_LIKE_STATEMENT = '%'
        SQL_LIKE_STATEMENT_HEADWORD = '%'
        def match(self, entity):
            return True

    class HeadwordWildcard(WildcardPairBase):
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

    class ReadingWildcard(WildcardPairBase):
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

    def __init__(self, supportWildcards=True, headwordFullwidthCharacters=False,
        **options):
        _SimpleReadingWildcardBase.__init__(self, **options)
        self._supportWildcards = supportWildcards
        self._headwordFullwidthCharacters = headwordFullwidthCharacters

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
                if self._headwordFullwidthCharacters:
                    # map to fullwidth if applicable
                    entity = _FULL_WIDTH_MAP.get(toCodepoint(entity), entity)
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
                            [self._createHeadwordWildcard(c)
                                for c in getCharacterList(entity)])

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
            headwordChars = getCharacterList(headword)

            if len(headwordChars) != len(readingEntities):
                # error in database entry
                return False

            # match against all pairs
            for searchEntities in searchPairs:
                entities = zip(headwordChars, readingEntities)
                if self._depthFirstSearch(searchEntities, entities):
                    return True

            return False

        if self._caseInsensitive:
            # assume that conversion of lower case results in lower case
            searchStr = searchStr.lower()
        searchPairs = self._getWildcardForms(searchStr, **options)

        if self._caseInsensitive:
            return lambda h, r: matchHeadwordReadingPair(h.lower(), r.lower())
        else:
            return matchHeadwordReadingPair


class MixedWildcardReading(SimpleReading,
    _MixedReadingWildcardBase):
    """
    Reading search strategy that supplements
    :class:`~cjklib.dictionary.search.SimpleWildcardReading` to allow
    intermixing of readings with single characters from the headword.
    By default wildcard searches are supported.

    This strategy complements the basic search strategy. It is not built to
    return results for plain reading or plain headword strings.
    """
    def __init__(self, supportWildcards=True, headwordFullwidthCharacters=False,
        **options):
        """
        :type caseInsensitive: bool
        :param caseInsensitive: if ``True``, latin characters match their
            upper/lower case equivalent, if ``False`` case sensitive matches
            will be made (default)
        :type sqlCollation: str
        :param sqlCollation: optional collation to use on columns in SQL queries
        :type supportWildcards: bool
        :param supportWildcards: if ``True`` wildcard characters are
            interpreted (default).
        :type headwordFullwidthCharacters: bool
        :param headwordFullwidthCharacters: if ``True`` halfwidth characters
            are converted to fullwidth if found in headword.
        :type escape: str
        :param escape: character used to escape command characters
        :type singleCharacter: str
        :param singleCharacter: wildcard character matching a single arbitrary
            character
        :type multipleCharacters: str
        :param multipleCharacters: wildcard character matching zero, one or many
            arbitrary characters
        """
        SimpleReading.__init__(self, **options)
        _MixedReadingWildcardBase.__init__(self, supportWildcards,
            headwordFullwidthCharacters, **options)

    def getWhereClause(self, headwordColumn, readingColumn, searchStr,
        **options):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by
        :meth:`~cjklib.dictionary.search.MixedWildcardReading.getMatchFunction`.

        :type headwordColumn: SQLAlchemy column instance
        :param headwordColumn: headword column to check against
        :type readingColumn: SQLAlchemy column instance
        :param readingColumn: reading column to check against
        :type searchStr: str
        :param searchStr: search string
        :return: SQLAlchemy clause
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
    class TonelessReadingWildcard(_MixedReadingWildcardBase.WildcardPairBase):
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

    def __init__(self, supportWildcards=True, headwordFullwidthCharacters=False,
        **options):
        _MixedReadingWildcardBase.__init__(self, supportWildcards,
            headwordFullwidthCharacters, **options)
        _TonelessReadingWildcardBase.__init__(self, **options)

    def _createTonelessReadingWildcard(self, plainEntity):
        return self.TonelessReadingWildcard(plainEntity, self.escape)

    def _getWildcardForms(self, readingStr, **options):
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
                            [self._createHeadwordWildcard(c)
                                for c in getCharacterList(entity)])

                # discard pure reading or pure headword strings as they will be
                #   covered through other strategies
                if hasReadingEntity and hasHeadwordEntity:
                    self._wildcardForms.append(searchEntities)

        return self._wildcardForms


class MixedTonelessWildcardReading(SimpleReading,
    _MixedTonelessReadingWildcardBase):
    """
    Reading search strategy that supplements
    :class:`~cjklib.dictionary.search.TonelessWildcardReading` to allow
    intermixing of readings missing tonal information with single characters
    from the headword. By default wildcard searches are supported.

    This strategy complements the basic search strategy. It is not built to
    return results for plain reading or plain headword strings.
    """
    def __init__(self, supportWildcards=True, headwordFullwidthCharacters=False,
        **options):
        """
        :type caseInsensitive: bool
        :param caseInsensitive: if ``True``, latin characters match their
            upper/lower case equivalent, if ``False`` case sensitive matches
            will be made (default)
        :type sqlCollation: str
        :param sqlCollation: optional collation to use on columns in SQL queries
        :type supportWildcards: bool
        :param supportWildcards: if ``True`` wildcard characters are
            interpreted (default).
        :type headwordFullwidthCharacters: bool
        :param headwordFullwidthCharacters: if ``True`` halfwidth characters
            are converted to fullwidth if found in headword.
        :type escape: str
        :param escape: character used to escape command characters
        :type singleCharacter: str
        :param singleCharacter: wildcard character matching a single arbitrary
            character
        :type multipleCharacters: str
        :param multipleCharacters: wildcard character matching zero, one or many
            arbitrary characters
        """
        SimpleReading.__init__(self, **options)
        _MixedTonelessReadingWildcardBase.__init__(self, supportWildcards,
            headwordFullwidthCharacters, **options)

    def getWhereClause(self, headwordColumn, readingColumn, searchStr,
        **options):
        """
        Returns a SQLAlchemy clause that is the necessary condition for a
        possible match. This clause is used in the database query. Results may
        then be further narrowed by
        :meth:`~MixedTonelessWildcardReading.getMatchFunction`.

        :type headwordColumn: SQLAlchemy column instance
        :param headwordColumn: headword column to check against
        :type readingColumn: SQLAlchemy column instance
        :param readingColumn: reading column to check against
        :type searchStr: str
        :param searchStr: search string
        :return: SQLAlchemy clause
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
