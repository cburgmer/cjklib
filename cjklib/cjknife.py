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
cjknife is a tool that makes the functions offered by L{cjklib} available to the
command line.

Check what this script offers on the command line with C{cjknife -h}.

The script's output depends on the following:
    - dictionary setting in the cjklib's config file
    - user locale settings are checked to guess appropriate values for the
        character locale and the default input and output readings

@copyright: Copyright (C) 2006-2009 cjklib developers
"""

import sys
import getopt
import locale
import re

from sqlalchemy import Table
from sqlalchemy import select, union
from sqlalchemy.sql import and_, or_

import cjklib
from cjklib.dbconnector import DatabaseConnector
from cjklib import characterlookup
from cjklib import reading
from cjklib import exception
from cjklib.util import getConfigSettings

# work around http://bugs.python.org/issue2517
if sys.version_info[0:2] == (2, 5):
    getExceptionString = lambda e: unicode(e.message)
else:
    getExceptionString = lambda e: unicode(e)

class CharacterInfo:
    """
    Provides lookup method services.
    """
    LANGUAGE_CHAR_LOCALE_MAPPING = {'zh': 'C', 'zh_CN': 'C', 'zh_SG': 'C',
        'zh_TW': 'T', 'zh_HK': 'T', 'zh_MO': 'T', 'ja': 'J', 'ko': 'K',
        'vi': 'V'}
    """Mapping table for locale to default character locale."""

    CHAR_LOCALE_NAME = {'T': 'traditional', 'C': 'Chinese simplified',
        'J': 'Japanese', 'K': 'Korean', 'V': 'Vietnamese'}
    """Character locale names."""

    CHAR_LOCALE_DEFAULT_READING = {'zh': "Pinyin", 'zh_CN': "Pinyin",
        'zh_SG': "Pinyin", 'zh_TW': "WadeGiles", 'zh_HK': "CantoneseYale",
        'zh_MO': "Jyutping", 'ko': 'Hangul', 'ja': 'Kana'}
    """Character locale's default character reading."""

    DICTIONARY_INFO = {
        'HanDeDict': {'type': 'CEDICT', 'reading': 'Pinyin',
            'options': {'toneMarkType': 'numbers'}, 'defaultLocale' :'C',
            'readingFunc': lambda entities: ' '.join(entities)},
        'CFDICT': {'type': 'CEDICT', 'reading': 'Pinyin',
            'options': {'toneMarkType': 'numbers'}, 'defaultLocale' :'C',
            'readingFunc': lambda entities: ' '.join(entities)},
        'CEDICT': {'type': 'CEDICT', 'reading': 'Pinyin',
            'options': {'toneMarkType': 'numbers'}, 'defaultLocale' :'C',
            'readingFunc': lambda entities: ' '.join(entities)},
        'CEDICTGR': {'type': 'EDICT', 'reading': 'GR', 'options': {},
            'defaultLocale' :'T',
            'readingFunc': lambda entities: ' '.join(entities)},
        'EDICT': {'type': 'EDICT', 'reading': 'Kana', 'options': {},
            'defaultLocale' :'J',
            'readingFunc': lambda entities: ''.join(entities)},
        }
    """Dictionaries with type (EDICT, CEDICT), reading and reading options."""

    READING_DEFAULT_DICTIONARY = {'Pinyin': 'CEDICT'}
    """Dictionary to use by default for a given reading."""

    VARIANT_TYPE_NAMES = {'C': 'Compatible variant',
        'M': 'Semantic variants', 'P': 'Specialised semantic variants',
        'Z': 'Z-Variants', 'S': 'Simplified variants',
        'T': 'Traditional variants'}
    """List of character variants and their names."""

    def __init__(self, charLocale=None, characterDomain='Unicode',
        readingN=None, dictionary=None, dictionaryDatabaseUrl=None):
        """
        Initialises the CharacterInfo object.

        @type charLocale: str
        @param charLocale: I{character locale} (one out of TCJKV)
        @type characterDomain: str
        @param characterDomain: I{character domain} (see
            L{characterlookup.CharacterLookup.getAvailableCharacterDomains()})
        @type readingN: str
        @param readingN: name of reading
        @type dictionary: str
        @param dictionary: name of dictionary
        @type dictionaryDatabaseUrl: str
        @param dictionaryDatabaseUrl: database connection setting in the format
            C{driver://user:pass@host/database}.
        """
        if charLocale:
            self.locale = charLocale
        elif dictionary and dictionary in self.DICTIONARY_INFO:
            self.locale = self.DICTIONARY_INFO[dictionary]['defaultLocale']
        else:
            self.locale = self.guessCharacterLocale()

        if readingN:
            self.reading = readingN
        elif dictionary and dictionary in self.DICTIONARY_INFO:
            self.reading = self.DICTIONARY_INFO[dictionary]['reading']
        else:
            self.reading = self.guessReading()

        self.characterLookup = characterlookup.CharacterLookup(self.locale,
            characterDomain)
        self.characterLookupTraditional = characterlookup.CharacterLookup('T',
            characterDomain)
        self.readingFactory = reading.ReadingFactory()
        if dictionaryDatabaseUrl:
            self.dictDB = DatabaseConnector({'url': dictionaryDatabaseUrl})
        else:
            self.dictDB = DatabaseConnector.getDBConnector()

        self.availableDictionaries = None

        if dictionary:
            if dictionary not in self.DICTIONARY_INFO:
                raise ValueError("invalid dictionary specified")
            if dictionary not in self.getAvailableDictionaries():
                raise ValueError("dictionary not available")
            self.dictionary = dictionary
        else:
            if self.reading in self.READING_DEFAULT_DICTIONARY \
                and self.reading in self.getAvailableDictionaries():
                self.dictionary = self.READING_DEFAULT_DICTIONARY[self.reading]
            else:
                # get a dictionary that is compatible with the selected reading
                for dictName in self.getAvailableDictionaries():
                    if self.readingFactory.isReadingConversionSupported(
                        self.DICTIONARY_INFO[dictName]['reading'],
                        self.reading):
                        self.dictionary = dictName
                        break
                else:
                    self.dictionary = None

        if self.dictionary:
            # check for FTS3 table (only SQLite)
            self.dictionaryHasFTS3 = self.dictDB.engine.has_table(
                self.dictionary + '_Text')
            self.dictionaryObject = Table(self.dictionary, self.dictDB.metadata,
                autoload=True)
            if self.DICTIONARY_INFO[self.dictionary]['type'] == 'CEDICT':
                if self.locale == 'C':
                    self.headwordColumn \
                        = self.dictionaryObject.c.HeadwordSimplified
                else:
                    self.headwordColumn \
                        = self.dictionaryObject.c.HeadwordTraditional
            else:
                self.headwordColumn = self.dictionaryObject.c.Headword

    # Settings

    def guessCharacterLocale(self):
        """
        Guesses the best suited character locale using the user's locale
        settings.

        @rtype: str
        @return: locale
        """
        # get local language and output encoding
        language, _ = locale.getdefaultlocale()

        # get character locale
        if self.LANGUAGE_CHAR_LOCALE_MAPPING.has_key(language):
            return self.LANGUAGE_CHAR_LOCALE_MAPPING[language]
        elif len(language) >= 2 \
            and self.LANGUAGE_CHAR_LOCALE_MAPPING.has_key(language[0:2]):
            # strip off geographic code
            return self.LANGUAGE_CHAR_LOCALE_MAPPING[language[0:2]]
        else:
            return 'T'

    def guessReading(self):
        """
        Guesses the best suited reading using the user's locale settings.

        @rtype: str
        @return: reading name
        """
        # get local language and output encoding
        language, _ = locale.getdefaultlocale()

        # get reading
        if self.CHAR_LOCALE_DEFAULT_READING.has_key(language):
            return self.CHAR_LOCALE_DEFAULT_READING[language]
        elif len(language) >= 2 \
            and self.CHAR_LOCALE_DEFAULT_READING.has_key(language[0:2]):
            # strip off geographic code
            return self.CHAR_LOCALE_DEFAULT_READING[language[0:2]]
        else:
            return 'Pinyin'

    def getAvailableDictionaries(self):
        """
        Gets a list of available dictionaries supported.

        @rtype: list of str
        @return: names of available dictionaries
        """
        if self.availableDictionaries == None:
            self.availableDictionaries = []
            for dictName in self.DICTIONARY_INFO:
                if self.dictDB.engine.has_table(dictName):
                    self.availableDictionaries.append(dictName)
        return self.availableDictionaries

    def hasDictionary(self):
        return self.dictionary != None

    def setCharacterDomain(self, characterDomain):
        if characterDomain \
            in self.characterLookup.getAvailableCharacterDomains():

            self.characterLookup.setCharacterDomain(characterDomain)
            self.characterLookupTraditional.setCharacterDomain(characterDomain)
            return True
        else:
            return False

    # Internal worker

    def getReadingOptions(self, string, readingN):
        """
        Guesses the reading options using the given string to support reading
        dialects.

        @type string: str
        @param string: reading string
        @type readingN: str
        @param readingN: reading name
        @rtype: dict
        @returns: reading options
        """
        # guess reading parameters
        classObj = self.readingFactory.getReadingOperatorClass(readingN)
        if hasattr(classObj, 'guessReadingDialect'):
            return classObj.guessReadingDialect(string)
        else:
            return {}

    def getReadingEntities(self, string, readingN=None):
        """
        Gets all possible decompositions for the given string.

        @type string: str
        @param string: reading string
        @type readingN: str
        @param readingN: reading name
        @rtype: list of list of str
        @return: decomposition into reading entities.
        """
        if not readingN:
            readingN = self.reading
        options = self.getReadingOptions(string, readingN)

        # for all possible decompositions convert to dictionary's reading
        dictReading = self.DICTIONARY_INFO[self.dictionary]['reading']
        dictReadOpt = self.DICTIONARY_INFO[self.dictionary]['options']
        try:
            try:
                decompositions = self.readingFactory.getDecompositions(string,
                    readingN, **options)
            except exception.UnsupportedError:
                decompositions = [self.readingFactory.decompose(string,
                    readingN, **options)]

            if self.readingFactory.isReadingConversionSupported(readingN,
                dictReading):
                decompEntities = []
                for entities in decompositions:
                    try:
                        decompEntities.append(
                            self.readingFactory.convertEntities(entities,
                                readingN, dictReading, sourceOptions=options,
                                targetOptions=dictReadOpt))
                    except exception.ConversionError:
                        # some conversions might fail even others succeed, e.g.
                        #   bei3jing1 fails for bei3'ji'ng1
                        # TODO throw an exception when all conversions fail?
                        pass

                return decompEntities
            else:
                return decompositions
        except exception.DecompositionError:
            pass

        return [] # TODO rather throw an exception?

    def getSearchReading(self, entities):
        """
        Prepares the given reading entities for a database search. This is
        needed when doing fuzzy searches.

        @type entities: list of str
        @param entities: reading entities
        @rtype: list of str
        @param entities: prepared entities
        """
        # TODO generic on readings
        entitiesFiltered = []
        for entity in entities:
            if re.match(r"\s+$", entity):
                continue
            entitiesFiltered.append(entity)

        dictReading = self.DICTIONARY_INFO[self.dictionary]['reading']
        dictReadOpt = self.DICTIONARY_INFO[self.dictionary]['options']
        # for readings with appended tone marks use placeholder if no tone
        #   specified
        if dictReading in ['Pinyin', 'WadeGiles', 'Jyutping', 'CantoneseYale']:
            entitiesTonal = []
            for entity in entitiesFiltered:
                _, tone = self.readingFactory.splitEntityTone(entity,
                    dictReading, **dictReadOpt)
                if tone == None:
                    # placeholder for SQL
                    entitiesTonal.append(entity.lower() + '_')
                else:
                    entitiesTonal.append(entity.lower())

            return entitiesTonal
        else:
            return entitiesFiltered

    def convertDictionaryResult(self, result):
        """
        Converts the readings of the given dictionary result to the default
        reading.

        @type result: list of tuple
        @param result: database search result
        @rtype: list of tuple
        @return: converted input
        """
        # convert reading
        dictReading = self.DICTIONARY_INFO[self.dictionary]['reading']
        dictReadOpt = self.DICTIONARY_INFO[self.dictionary]['options']

        response = []
        conversionSupported = self.readingFactory.isReadingConversionSupported(
            dictReading, self.reading)

        for simp, readingStr, translation in result:
            if conversionSupported:
                try:
                    readingConv = self.readingFactory.convert(readingStr,
                        dictReading, self.reading, sourceOptions=dictReadOpt)
                except exception.DecompositionError:
                    readingConv = '[' + reading + ']'
                except exception.CompositionError:
                    readingConv = '[' + reading + ']'
                except exception.ConversionError:
                    readingConv = '[' + reading + ']'
            else:
                readingConv = readingStr
            # TODO work with trad forms and EDICT dicts too
            response.append((simp, readingConv, translation))
        return response

    def getEquivalentCharTable(self, componentList,
        includeEquivalentRadicalForms=True):
        u"""
        Gets a list structure of equivalent chars for the given list of
        characters.

        If option C{includeEquivalentRadicalForms} is set, all equivalent forms
        will be searched for when a Kangxi radical is given.

        @type componentList: list of str
        @param componentList: list of character components
        @type includeEquivalentRadicalForms: bool
        @param includeEquivalentRadicalForms: if C{True} then characters in the
            given component list are interpreted as representatives for their
            radical and all radical forms are included in the search. E.g. 肉
            will include ⺼ as a possible component.
        @rtype: list of list of str
        @return: list structure of equivalent characters
        @todo Impl: Once mapping of similar radical forms exist (e.g. 言 and 訁)
            include here.
        """
        # components for which we don't want to retrieve a equivalent character
        #   as it would resemble another radical form
        excludeEquivalentMapping = set([u'⺄', u'⺆', u'⺇', u'⺈', u'⺊', u'⺌',
            u'⺍', u'⺎', u'⺑', u'⺗', u'⺜', u'⺥', u'⺧', u'⺪', u'⺫', u'⺮',
            u'⺳', u'⺴', u'⺶', u'⺷', u'⺻', u'⺼', u'⻏', u'⻕'])

        equivCharTable = []
        for component in componentList:
            componentEquivalents = set([component])
            try:
                # check if component is a radical and get index
                radicalIdx = self.characterLookup.getKangxiRadicalIndex(
                    component)

                if includeEquivalentRadicalForms:
                    # if includeRadicalVariants is set get all forms
                    componentEquivalents.update(self.characterLookup\
                        .getKangxiRadicalRepresentativeCharacters(
                            radicalIdx))
                else:
                    if self.characterLookup.isRadicalChar(component):
                        if component not in excludeEquivalentMapping:
                            try:
                                componentEquivalents.add(self.characterLookup\
                                    .getRadicalFormEquivalentCharacter(
                                        component))
                            except exception.UnsupportedError:
                                # pass if no equivalent char existent
                                pass
                    else:
                        componentEquivalents.update(set(self.characterLookup\
                            .getCharacterEquivalentRadicalForms(component)) \
                            - excludeEquivalentMapping)
            except ValueError:
                pass

            equivCharTable.append(list(componentEquivalents))

        return equivCharTable

    def isSemanticVariant(self, char, variants):
        """
        Checks if the character is a semantic variant form of the given
        characters.

        @type char: str
        @param char: Chinese character
        @type variants: list of str
        @param variants: Chinese characters
        @rtype: bool
        @return: C{True} if the character is a semantic variant form of the
            given characters, C{False} otherwise.
        """
        vVariants = []
        for variant in variants:
            vVariants.extend(
                self.characterLookup.getCharacterVariants(variant, 'M'))
            vVariants.extend(
                self.characterLookup.getCharacterVariants(variant, 'P'))
        return char in vVariants

    # Features

    def convertReading(self, readingString, fromReading, toReading=None):
        """
        Converts a string in the source reading to the given target reading.

        @type readingString: str
        @param readingString: string written in the source reading
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
        @todo Fix:  Conversion without tones will mostly break as the target
            reading doesn't support missing tone information. Prefering
            'diacritic' version (Pinyin/CantoneseYale) over 'numbers' as tone
            marks in the absence of any marks would solve this issue (forcing
            fifth tone), but would mean we prefer possible false information
            over the less specific estimation of the given entities as missing
            tonal information.
        """
        if not toReading:
            toReading = self.reading
        options = self.getReadingOptions(readingString, fromReading)
        return self.readingFactory.convert(readingString, fromReading,
            toReading, sourceOptions=options)

    def getCharactersForKangxiRadicalIndex(self, radicalIndex):
        """
        Gets all characters for the given Kangxi radical index grouped by their
        residual stroke count.

        @type radicalIndex: int
        @param radicalIndex: Kangxi radical index
        @rtype: list of str
        @return: list of matching Chinese characters
        """
        strokeCountDict = {}
        for char, residualStrokeCount \
            in self.characterLookup.getResidualStrokeCountForKangxiRadicalIndex(
                radicalIndex):

            if residualStrokeCount not in strokeCountDict:
                strokeCountDict[residualStrokeCount] = set()
            strokeCountDict[residualStrokeCount].add(char)

        return strokeCountDict

    def getCharactersForReading(self, readingString, readingN=None):
        """
        Gets all know characters for the given reading.

        @type readingString: str
        @param readingString: reading entity for lookup
        @type readingN: str
        @param readingN: name of reading
        @rtype: list of str
        @return: list of characters for the given reading
        @raise UnsupportedError: if no mapping between characters and target
            reading exists.
        @raise ConversionError: if conversion from the internal source reading
            to the given target reading fails.
        """
        if not readingN:
            readingN = self.reading
        options = self.getReadingOptions(readingString, readingN)
        return self.characterLookup.getCharactersForReading(readingString,
            readingN, **options)

    def getReadingForCharacters(self, charString):
        """
        Gets a list of readings for a given character string.

        @type charString: str
        @param charString: string of Chinese characters
        @rtype: list of list of str
        @return: a list of readings per character
        @raise exception.UnsupportedError: raised when a translation from
            character to reading is not supported by the given target reading
        @raise exception.ConversionError: if conversion for the string is not
            supported
        """
        readings = []
        for char in charString:
            stringList = self.characterLookup.getReadingForCharacter(char,
                self.reading)
            if stringList:
                readings.append(stringList)
            else:
                readings.append(char)
        return readings

    def getSimplified(self, charString):
        """
        Gets the Chinese simplified character representation for the given
        character string.

        @type charString: str
        @param charString: string of Chinese characters
        @rtype: list of list of str
        @returns: list of simplified Chinese characters
        """
        simplified = []
        for char in charString:
            simplifiedVariants \
                = set(self.characterLookup.getCharacterVariants(char, 'S'))
            if self.isSemanticVariant(char, simplifiedVariants):
                simplifiedVariants.add(char)
            if len(simplifiedVariants) == 0:
                simplified.append(char)
            else:
                simplified.append(list(simplifiedVariants))
        return simplified

    def getTraditional(self, charString):
        """
        Gets the traditional character representation for the given character
        string.

        @type charString: str
        @param charString: string of Chinese characters
        @rtype: list of list of str
        @returns: list of simplified Chinese characters
        @todo Lang: Implementation is too simple to cover all aspects.
        """
        traditional = []
        for char in charString:
            traditionalVariants \
                = set(self.characterLookup.getCharacterVariants(char, 'T'))
            if self.isSemanticVariant(char, traditionalVariants):
                traditionalVariants.add(char)
            if len(traditionalVariants) == 0:
                traditional.append(char)
            else:
                traditional.append(list(traditionalVariants))
        return traditional

    def searchDictionaryExact(self, searchString, readingN=None, limit=None):
        """
        Searches the dictionary for exact matches to the given string.

        @type searchString: str
        @param searchString: search string
        @type readingN: str
        @param readingN: reading name
        @type limit: int
        @param limit: maximum number of entries
        """
        selectQueries = []
        # Chinese character string
        dictType = self.DICTIONARY_INFO[self.dictionary]['type']
        if dictType == 'EDICT':
            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                self.headwordColumn == searchString, distinct=True))
        elif dictType == 'CEDICT':
            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                or_(self.dictionaryObject.c.HeadwordSimplified == searchString,
                    self.dictionaryObject.c.HeadwordTraditional \
                        == searchString),
                distinct=True))

        # reading string
        decompEntities = self.getReadingEntities(searchString, readingN)
        if decompEntities:
            joinFunc = self.DICTIONARY_INFO[self.dictionary]['readingFunc']

            searchEntities = [joinFunc(self.getSearchReading(entities)) \
                for entities in decompEntities]

            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                self.dictionaryObject.c.Reading.in_(searchEntities),
                distinct=True))

        # translation string
        wordsTable = Table(self.dictionary + '_Words', self.dictDB.metadata,
            autoload=True)
        if dictType == 'EDICT':
            table = self.dictionaryObject.join(wordsTable,
                and_(wordsTable.c.Headword == self.dictionaryObject.c.Headword,
                    wordsTable.c.Reading == self.dictionaryObject.c.Reading))
        elif dictType == 'CEDICT':
            table = self.dictionaryObject.join(wordsTable,
                and_(wordsTable.c.Headword \
                        == self.dictionaryObject.c.HeadwordTraditional,
                    wordsTable.c.Reading == self.dictionaryObject.c.Reading))

        selectQueries.append(select([self.headwordColumn,
            self.dictionaryObject.c.Reading,
            self.dictionaryObject.c.Translation],
            wordsTable.c.Word == searchString.lower(),
            from_obj=table, distinct=True))

        result = self.dictDB.selectRows(
            union(*selectQueries).limit(limit).order_by(
                self.dictionaryObject.c.Reading))

        return self.convertDictionaryResult(result)

    def searchDictionaryContaining(self, searchString, readingN=None,
        position='c', limit=None):
        """
        Searches the dictionary for matches containing the given string.

        A position can be specified to narrow matches for character or reading
        input. C{'c'}, the most general, will allow the string anywhere in a
        match, C{'b'} only at the beginning, C{'e'} only at the end.

        @type searchString: str
        @param searchString: search string
        @type readingN: str
        @param readingN: reading name
        @type position: str
        @param position: position of the string in a match (one out of c, b, e)
        @type limit: int
        @param limit: maximum number of entries
        """
        selectQueries = []
        # Chinese character string
        searchStr = searchString
        if position == 'c' or position == 'e':
            searchStr = '%' + searchStr
        if position == 'c' or position == 'b':
            searchStr = searchStr + '%'

        dictType = self.DICTIONARY_INFO[self.dictionary]['type']
        if dictType == 'EDICT':
            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                self.headwordColumn.like(searchStr), distinct=True))
        elif dictType == 'CEDICT':
            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                or_(self.dictionaryObject.c.HeadwordSimplified.like(searchStr),
                    self.dictionaryObject.c.HeadwordTraditional.like(
                        searchStr)),
                distinct=True))

        # reading string
        decompEntities = self.getReadingEntities(searchString, readingN)
        if decompEntities:
            searchEntities = [self.getSearchReading(entities) \
                for entities in decompEntities]
            searchList = []

            joinFunc = self.DICTIONARY_INFO[self.dictionary]['readingFunc']
            for entities in searchEntities:
                searchStr = joinFunc(entities)
                if position == 'c' or position == 'e':
                    searchStr = '%' + searchStr
                if position == 'c' or position == 'b':
                    searchStr = searchStr + '%'
                searchList.append(searchStr)

            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                or_(*[self.dictionaryObject.c.Reading.like(entities) \
                    for entities in searchList]),
                distinct=True))

        # translation string
        translationTokens = re.findall(ur'(?u)((?:\w|\d)+)', searchString)

        if self.dictionaryHasFTS3 \
            and hasattr(self.dictionaryObject.c.Translation, 'match'):
            # dictionary has FTS3 full text search on SQLite
            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                self.dictionaryObject.c.Translation.match(
                    ' '.join(translationTokens)),
                distinct=True))
        else:
            selectQueries.append(select([self.headwordColumn,
                self.dictionaryObject.c.Reading,
                self.dictionaryObject.c.Translation],
                self.dictionaryObject.c.Translation.like(
                    '%' + ' '.join(translationTokens) + '%'),
                distinct=True))

        result = self.dictDB.selectRows(
            union(*selectQueries).limit(limit).order_by(
                self.dictionaryObject.c.Reading))

        return self.convertDictionaryResult(result)

    def getCharactersForComponents(self, componentList,
        includeEquivalentRadicalForms=True):
        u"""
        Gets all characters that contain the given components.

        If option C{includeEquivalentRadicalForms} is set, all equivalent forms
        will be searched for when a Kangxi radical is given.

        @type componentList: list of str
        @param componentList: list of character components
        @type includeEquivalentRadicalForms: bool
        @param includeEquivalentRadicalForms: if C{True} then characters in the
            given component list are interpreted as representatives for their
            radical and all radical forms are included in the search. E.g. 肉
            will include ⺼ as a possible component.
        @rtype: list of tuple
        @return: list of pairs of matching characters and their I{glyphs}
        @raise ValueError: if an invalid I{character locale} is specified
        @todo Impl: Once mapping of similar radical forms exist (e.g. 言 and 訁)
            include here.
        """
        equivCharTable = self.getEquivalentCharTable(componentList,
            includeEquivalentRadicalForms)
        componentLookupResult \
            = self.characterLookup.getCharactersForEquivalentComponents(
                equivCharTable)
        return [char for char, _ in componentLookupResult]

    def getCharacterInformation(self, char):
        """
        Get the basic information for the given character.

        The following data is collected and returned in a dict:
            - char
            - locale
            - locale name
            - character domain
            - code point hex
            - code point dec
            - type
            - equivalent form (if type is C{'radical'})
            - radical index
            - radical form (if available)
            - radical variants (if available)
            - stroke count (if available)
            - readings (if type is C{'character'})
            - variants (if type is C{'character'})
            - default glyph
            - glyphs

        @type char: str
        @param char: Chinese character
        @rtype: dict
        @return: character information as keyword value pairs
        """
        infoDict = {}

        # general information
        infoDict['char'] = char
        infoDict['locale'] = self.locale
        infoDict['locale name'] = self.CHAR_LOCALE_NAME[self.locale]
        infoDict['characterDomain'] = self.characterLookup.getCharacterDomain()
        infoDict['codepoint hex'] = 'U+%04X' % ord(char)
        infoDict['codepoint dec'] = str(ord(char))

        # radical
        if self.characterLookup.isRadicalChar(char):
            infoDict['type'] = 'radical'

            if self.characterLookup.isKangxiRadicalFormOrEquivalent(char):
                infoDict['radical index'] \
                    = self.characterLookup.getKangxiRadicalIndex(char)
            elif self.characterLookupTraditional\
                .isKangxiRadicalFormOrEquivalent(char):
                infoDict['radical index'] = self.characterLookupTraditional\
                    .getKangxiRadicalIndex(char)
            else:
                infoDict['radical index'] = None

            try:
                infoDict['equivalent form'] \
                    = self.characterLookup.getRadicalFormEquivalentCharacter(
                        char)
            except exception.UnsupportedError:
                pass

        else:
            infoDict['type'] = 'character'
            try:
                infoDict['radical index'] \
                    = self.characterLookup.getCharacterKangxiRadicalIndex(char)
            except exception.NoInformationError:
                infoDict['radical index'] = None

        # regardless of type (radical/radical equivalent/other character) show
        #   radical forms
        if infoDict['radical index']:
            try:
                infoDict['radical form'] \
                    = self.characterLookupTraditional.getKangxiRadicalForm(
                        infoDict['radical index'])
                localeVariantForm \
                    = self.characterLookup.getKangxiRadicalForm(
                        infoDict['radical index'])
                variantList = []
                if localeVariantForm != infoDict['radical form']:
                    variantList.append(localeVariantForm)
                variantList.extend(
                    self.characterLookup.getKangxiRadicalVariantForms(
                        infoDict['radical index']))
                infoDict['radical variants'] = variantList
            except exception.NoInformationError:
                pass

        # stroke count
        try:
            infoDict['stroke count'] = self.characterLookup.getStrokeCount(char)
        except exception.NoInformationError:
            pass

        if not self.characterLookup.isRadicalChar(char):
            # reading information
            infoDict['readings'] = {}

            for readingN in self.readingFactory.getSupportedReadings():
                try:
                    readingList = self.characterLookup.getReadingForCharacter(
                        char, readingN)
                    if readingList:
                        infoDict['readings'][readingN] = readingList
                except exception.UnsupportedError:
                    pass
                except exception.ConversionError:
                    pass

            # character variants
            infoDict['variants'] = {}

            for variantType in self.VARIANT_TYPE_NAMES:
                variants = self.characterLookup.getCharacterVariants(char,
                    variantType)
                if variants:
                    infoDict['variants'][self.VARIANT_TYPE_NAMES[variantType]] \
                        = variants

        try:
            # character decomposition and stroke order
            infoDict['default glyph'] = self.characterLookup.getDefaultGlyph(
                char)
        except exception.NoInformationError:
            pass

        try:
            infoDict['glyphs'] = {}

            for glyph in self.characterLookup.getCharacterGlyphs(char):
                infoDict['glyphs'][glyph] = {}
                # character decomposition
                decomposition = self.characterLookup.getDecompositionTreeList(
                    char, glyph=glyph)

                if decomposition:
                    infoDict['glyphs'][glyph]['decomposition'] \
                        = decomposition

                # stroke order
                try:
                    infoDict['glyphs'][glyph]['stroke count'] \
                        =  self.characterLookup.getStrokeCount(char,
                            glyph=glyph)
                    infoDict['glyphs'][glyph]['stroke order'] \
                        =  self.characterLookup.getStrokeOrder(char,
                            glyph=glyph)
                    infoDict['glyphs'][glyph]['stroke order abbrev'] \
                        =  self.characterLookup.getStrokeOrderAbbrev(char,
                            glyph=glyph)
                except exception.NoInformationError:
                    pass
        except exception.NoInformationError:
            pass

        return infoDict


def getPrintableList(stringList, joinString = ""):
    """
    Gets a printable representation for the given list.

    @type stringList: list of list of str
    @param stringList: strings that need to be concatenated for output
    @type joinString: str
    @param joinString: string that concatenates the different values
    @rtype: str
    @return: printable representation for the given list
    """
    joinedStringList = []
    for elem in stringList:
        if len(elem) == 1:
            joinedStringList.append(elem[0])
        else:
            joinedStringList.append("[" + joinString.join(elem) + "]")
    return joinString.join(joinedStringList)

def getDecompositionForList(decompositionList):
    """
    Gets a fixed width string representation of the given decompositions.

    @type decompositionList: list
    @param decompositionList: a list of character decompositions
    @rtype: list of str
    @return: string representation of decomposition
    """
    # process a list of different decompositions
    stringList = []
    for decomposition in decompositionList:
        stringList.extend(getDecompositionForEntry(decomposition))
    return stringList

def getDecompositionForEntry(decomposition):
    """
    Gets a fixed width string representation of the given decomposition.

    @type decomposition: list
    @param decomposition: character decomposition tree
    @rtype: list of str
    @return: string representation of decomposition
    """
    # process one character of a decompositions
    stringList = [""]
    if type(decomposition[0]) != type(()):
        # IDS element
        stringList[0] = decomposition[0]
    else:
        char, _, decompList = decomposition[0]
        stringList[0] = char
        maxLineLen = 0
        for line in getDecompositionForList(decompList):
            # add decomposition of character in new line
            stringList.append(line)
            maxLineLen = max(maxLineLen, len(line))
        # add spaces to right side of first line to shift next character
        stringList[0] = stringList[0] \
            + "".join([u"　" for i in range(1, maxLineLen)])
    # process next character and add new lines into list
    if len(decomposition) > 1:
        for i, line in enumerate(getDecompositionForEntry(
            decomposition[1:])):
            # generate new lines if necessary
            if i >= len(stringList):
                stringList.append(u"　")
            stringList[i] = stringList[i] + line
    return stringList

def usage():
    """
    Prints the usage for this script.
    """
    print """Usage: cjknife COMMAND
cjknife provides a set of functions for dealing with Chinese characters and
their readings. This tool should provide quick access to the major functions of
the cjklib library and at the same time demonstrate how the library can be used.

General commands:
  -i, --information=CHAR     print information about the given char
  -a, --by-reading=READING   prints a list of characters for the given reading
  -r, --get-reading=CHARSTR  prints the reading for a given character string
                               (for characters with multiple readings these are
                               grouped in square brackets; shows the character
                               itself if no reading information available)
  -f, --convert-form=CHARSTR converts the given characters from/to Chinese
                               simplified/traditional form (if ambiguous
                               multiple characters are grouped in brackets)
  -q CHARSTR                 performs commands -r and -f in one step
  -k, --by-radicalidx=RADICALIDX
                             get all characters for a radical given by its index
  -p, --by-components=CHARSTR
                             get all characters that include all the chars
                               contained in the given list as component
  -m, --convert-reading=READING
                             converts the given reading from the input reading
                             to the output reading (compatibility needed)
  -s, --source-reading=SOURCE
                             set given reading as input reading
  -t, --target-reading=TARGET
                             set given reading as output reading
  -l, --locale=LOCALE        set locale, i.e. one character out of TCJKV
  -d, --domain=DOMAIN        set character domain, e.g. 'GB2312'
  -L, --list-options         list available options for parameters
  -V, --version              print version number and exit
  -h, --help                 display this help and exit
Dictionary search:
  -c SEARCHSTR               searches the dictionary, contain string
  -b SEARCHSTR               searches the dictionary, begin with string
  -e SEARCHSTR               searches the dictionary, end with string
  -x SEARCHSTR               searches the dictionary, exact
  -w, --set-dictionary=DICTIONARY
                             set dictionary"""
# TODO
  #-o, --by-strokes=STROKES   get all characters for a given stroke order
                               #(fuzzy search)

def version():
    """
    Prints the version of this script.
    """
    print "cjknife " + str(cjklib.__version__) \
        + """\nCopyright (C) 2006-2009 Christoph Burgmer

cjknife is part of cjklib.

cjklib is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

cjklib is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with cjklib.  If not, see <http://www.gnu.org/licenses/>."""

# Alternative reading names lookup
ALTERNATIVE_READING_NAMES = {'Hangul': ['hg'], 'Pinyin': ['py'],
    'WadeGiles': ['wade-giles', 'wg'], 'Jyutping': ['lshk', 'jp'],
    'CantoneseYale': ['cy']}

def main():
    """
    Main method
    """
    default_encoding = locale.getpreferredencoding()
    output_encoding = sys.stdout.encoding or locale.getpreferredencoding() \
        or 'ascii'

    # parse command line parameters
    try:
        opts, _ = getopt.getopt(sys.argv[1:],
            "i:a:r:f:q:k:p:o:m:s:t:l:d:c:b:e:x:w:LVh", ["help", "version",
            "locale=", "domain=", "source-reading=", "target-reading=",
            "information=", "by-reading=", "get-reading=", "convert-form=",
            "by-radicalidx=", "by-components=", "by-strokes=",
            "convert-reading=", "set-dictionary=", "list-options"])
    except getopt.GetoptError:
        # print help information and exit
        usage()
        sys.exit(2)

    # build lookup table for reading input names to reading 
    readingLookup = {}
    for readingN in reading.ReadingFactory().getSupportedReadings():
        readingLookup[readingN.lower()] = readingN
    for readingN in ALTERNATIVE_READING_NAMES:
        # add alternative names
        for name in ALTERNATIVE_READING_NAMES[readingN]:
            readingLookup[name] = readingN

    configSettings = getConfigSettings('cjknife')
    if 'url' in configSettings and configSettings['url']:
        url = configSettings['url']
    else:
        url = None
    if 'dictionary' in configSettings and configSettings['dictionary']:
        dictionary = configSettings['dictionary']
    else:
        dictionary = None
    if 'reading' in configSettings and configSettings['reading']:
        sourceReading = configSettings['reading']
        targetReading = configSettings['reading']
    else:
        sourceReading = None
        targetReading = None
    if 'locale' in configSettings and configSettings['locale']:
        charLocale = configSettings['locale']
    else:
        charLocale = None
    if 'domain' in configSettings and configSettings['domain']:
        charDomain = configSettings['domain']
    else:
        charDomain = 'Unicode'

    # command that will be executed once all parameters are parsed
    command = None
    parameter = None

    # start to check parameters
    if len(opts) == 0:
        print "Use parameter -h for a short summary on supported functions"

    for o, a in opts:
        a = a.decode(default_encoding)

        # help screen
        if o in ("-h", "--help"):
            usage()
            sys.exit()

        # version message
        elif o in ("-V", "--version"):
            version()
            sys.exit()

        # setting of source reading
        elif o in ("-s", "--source-reading"):
            if readingLookup.has_key(a.lower()):
                sourceReading = readingLookup[a.lower()]
            else:
                print "Error:", "'" + a.encode(output_encoding, "replace") \
                    + "' is not a valid reading name"
                sys.exit(1)

        # setting of target reading
        elif o in ("-t", "--target-reading"):
            if readingLookup.has_key(a.lower()):
                targetReading = readingLookup[a.lower()]
            else:
                print "Error:", "'" + a.encode(output_encoding, "replace") \
                    + "' is not a valid reading name"
                sys.exit(1)

        # setting of locale
        elif o in ("-l", "--locale"):
            if a.upper() in 'TCJKV':
                charLocale = a.upper()
            else:
                print "Error:", "'" + a.encode(output_encoding, "replace") \
                    + "' is not a valid locale"
                sys.exit(1)

        # setting of locale
        elif o in ("-d", "--domain"):
            charDomain = a

        # setting of dictionary
        elif o in ("-w", "--set-dictionary"):
            dictionaries = dict([(name.lower(), name) \
                for name in CharacterInfo.DICTIONARY_INFO])
            if a.lower() in dictionaries:
                dictionary = dictionaries[a.lower()]
            else:
                print "Error:", "'" + a.encode(output_encoding, "replace") \
                    + "' is not a valid dictionary"
                sys.exit(1)

        else:
            # set this as a command executed later
            command = o
            parameter = a

    try:
        charInfo = CharacterInfo(charLocale=charLocale, readingN=targetReading,
            dictionary=dictionary, dictionaryDatabaseUrl=url)
        charLocale = charInfo.locale
        dictionary = charInfo.dictionary
        if not charInfo.setCharacterDomain(charDomain):
            print >> sys.stderr, "Warning: Unknown character domain '%s'" \
                % charDomain

        if not sourceReading:
            sourceReading = charInfo.reading
        if not targetReading:
            targetReading = charInfo.reading

        # execute command

        # character information table
        if command in ("-i", "--information"):
            if len(parameter) == 1:
                infoDict = charInfo.getCharacterInformation(parameter)

                print ("Information for character " + infoDict['char'] + " (" \
                    + infoDict['locale name'] + " locale, " \
                    + infoDict['characterDomain'] + ' domain)')\
                    .encode(output_encoding, "replace")
                print "Unicode codepoint: " + infoDict['codepoint hex'] + " (" \
                    + infoDict['codepoint dec'] + ", "+ infoDict['type'] \
                    + " form)"
                if 'equivalent form' in infoDict:
                    print ("Equivalent character form: " \
                        + infoDict['equivalent form'])\
                        .encode(output_encoding, "replace")

                if infoDict['radical index']:
                    radicalForms = ""
                    if infoDict['radical form']:
                        radicalForms = ", radical form: " \
                            + infoDict['radical form']
                    if infoDict['radical variants']:
                        radicalForms = radicalForms + ", variants: " \
                            + ", ".join(infoDict['radical variants'])
                    print ("Radical index: " + str(infoDict['radical index']) \
                        + radicalForms)\
                        .encode(output_encoding, "replace")

                if 'stroke count' in infoDict:
                    strokeCount = str(infoDict['stroke count'])
                else:
                    strokeCount = 'N/A'
                print ("Stroke count: " + strokeCount)\
                    .encode(output_encoding, "replace")

                if infoDict['type'] == 'character':
                    readingList = infoDict['readings'].keys()
                    readingList.sort()
                    for readingN in readingList:
                        print ("Phonetic data (" + readingN + "): " \
                            + ", ".join(infoDict['readings'][readingN]))\
                            .encode(output_encoding, "replace")

                    variantList = infoDict['variants'].keys()
                    variantList.sort()
                    for variantType in variantList:
                        print (variantType + ': ' \
                            + ', '.join(infoDict['variants'][variantType]))\
                            .encode(output_encoding, "replace")

                glyphList = infoDict['glyphs'].keys()
                glyphList.sort()
                for glyph in glyphList:
                    if 'stroke count' in infoDict['glyphs'][glyph]:
                        strokeCount \
                            = str(infoDict['glyphs'][glyph]['stroke count'])
                    else:
                        strokeCount = 'N/A'
                    default = ""
                    if glyph == infoDict['default glyph']:
                        default = "(*)"
                    print "Glyph " + str(glyph) + default + ', stroke count: ' \
                        + strokeCount

                    if 'decomposition' in infoDict['glyphs'][glyph]:
                        stringList = getDecompositionForList(
                            infoDict['glyphs'][glyph]['decomposition'])
                        print ("\n".join(stringList))\
                            .encode(output_encoding, "replace")
                    if 'stroke order' in infoDict['glyphs'][glyph]:
                        print ("Stroke order: " + ''.join(
                            infoDict['glyphs'][glyph]['stroke order']) + ' (' \
                            + infoDict['glyphs'][glyph]['stroke order abbrev'] \
                            + ')')\
                            .encode(output_encoding, "replace")
            else:
                print "Error: bad parameter"
                sys.exit(1)

        elif command in ("-q", "-r", "-f", "--get-reading", "--convert-form"):
            # character to reading conversion
            if command in ("-q", "-r", "--get-reading"):
                try:
                    readingList = charInfo.getReadingForCharacters(parameter)
                    print getPrintableList(readingList, " ")\
                        .encode(output_encoding, "replace")
                except exception.UnsupportedError:
                    print "Error: no character mapping for this reading." \
                        + " Maybe the mapping in question has not been " \
                        + "installed."
                    sys.exit(1)
                except exception.ConversionError:
                    print "Error: unable to convert to internal reading"
                    sys.exit(1)

            # conversion between simplified/traditional forms
            if command in ("-q", "-f", "--convert-form"):
                simplified = getPrintableList(charInfo.getSimplified(parameter))
                traditional = getPrintableList(charInfo.getTraditional(
                    parameter))
                if not parameter in (simplified, traditional):
                    print "Warning: input string has mixed simplified and " \
                        + "traditional forms"
                if simplified == traditional:
                    print "Chinese simplified/Traditional: " \
                        + simplified.encode(output_encoding, "replace")
                else:
                    print "Chinese simplified: " \
                        + simplified.encode(output_encoding, "replace")
                    print "Traditional: " + traditional.encode(output_encoding,
                        "replace")

        # character lookup by reading
        elif command in ("-a", "--by-reading"):
            try:
                characterList = charInfo.getCharactersForReading(parameter,
                    sourceReading)
                print "".join(characterList).encode(output_encoding, "replace")
            except exception.UnsupportedError:
                print "Error: no character mapping for this reading." \
                    + " Maybe the mapping in question has not been installed."
                sys.exit(1)
            except exception.ConversionError:
                print "Error: unable to convert to internal reading"
                sys.exit(1)

        # character lookup by Kangxi radical index
        elif command in ("-k", "--by-radicalidx"):
            try:
                strokeCountDict = charInfo.getCharactersForKangxiRadicalIndex(
                    int(parameter))
                for residualStrokeCount in sorted(strokeCountDict.keys()):
                    print '+' + str(residualStrokeCount) + ': ' \
                        + ''.join(strokeCountDict[residualStrokeCount])\
                            .encode(output_encoding, "replace")
            except ValueError:
                print "Error: bad parameter"
                sys.exit(1)

        # character lookup by components
        elif command in ("-p", "--by-components"):
            charList = charInfo.getCharactersForComponents(parameter)
            print ''.join(charList).encode(output_encoding, "replace")

        # TODO
        ## character lookup by stroke order
        #elif command in ("-o", "--by-strokes"):
            #strokeLookupResult = charInfo.getCharactersForStrokeOrderFuzzy(
                #parameter, charLocale, 0.46)
            #strokeLookupResult.sort(reverse=True, key=operator.itemgetter(2))
            #charList = [char for char, _, _ in strokeLookupResult]
            #print ''.join(charList).encode(output_encoding, "replace")

        # reading conversion
        elif command in ("-m", "--convert-reading"):
            try:
                print charInfo.convertReading(parameter, sourceReading,
                    targetReading).encode(output_encoding, "replace")
            except exception.DecompositionError, m:
                print "Error: invalid input string:", \
                    getExceptionString(m).encode(output_encoding, "replace")
                sys.exit(1)
            except exception.CompositionError, m:
                print "Error: can't compose target entities:", \
                    getExceptionString(m).encode(output_encoding, "replace")
                sys.exit(1)
            except exception.AmbiguousConversionError, m:
                print "Error: input reading is ambiguous, can't convert:", \
                    getExceptionString(m).encode(output_encoding, "replace")
                sys.exit(1)
            except exception.ConversionError, m:
                print "Error: can't convert input string:", \
                    getExceptionString(m).encode(output_encoding, "replace")
                sys.exit(1)
            except exception.UnsupportedError:
                print "Error: conversion for given readings not supported"
                sys.exit(1)

        # dictionary search
        elif command == "-x":
            if not charInfo.hasDictionary():
                print "Error: no dictionary available"
                sys.exit(1)
            try:
                results = charInfo.searchDictionaryExact(parameter,
                    sourceReading)
                for c, r, t in results:
                    print (c + ", " + r + ", " + t)\
                        .encode(output_encoding, "replace")
            except exception.UnsupportedError:
                print "Error: conversion for given readings not supported"
                sys.exit(1)

        elif command in ("-c", "-b", "-e"):
            if not charInfo.hasDictionary():
                print "Error: no dictionary available"
                sys.exit(1)
            try:
                results = charInfo.searchDictionaryContaining(parameter,
                    sourceReading, command[1])
                for c, r, t in results:
                    print (c + ", " + r + ", " + t)\
                        .encode(output_encoding, "replace")
            except exception.UnsupportedError:
                print "Error: conversion for given readings not supported"
                sys.exit(1)

        # listing of available options for parameter setting
        elif command in ("-L", "--list-options"):
            # locales
            print "Current locale: " + charLocale + " (" \
                + CharacterInfo.CHAR_LOCALE_NAME[charLocale] + ")"
            print "Supported locales: " + ", ".join(
                ["%s: %s" % entry for entry \
                    in sorted(CharacterInfo.CHAR_LOCALE_NAME.items())])
            # character domain
            print "Current character domain: " + charDomain
            print "Available domains: " + ", ".join(
                charInfo.characterLookup.getAvailableCharacterDomains())
            # readings
            print "Current source reading: %s" % sourceReading
            print "Current target reading: %s" % targetReading
            readingsList = []
            for readingName in reading.ReadingFactory().getSupportedReadings():
                if ALTERNATIVE_READING_NAMES.has_key(readingName):
                    readingsList.append(readingName + " (" \
                        + ", ".join(ALTERNATIVE_READING_NAMES[readingName]) \
                        + ")")
                else:
                    readingsList.append(readingName)
            print "Supported readings: " + ", ".join(readingsList)
            # dictionary
            if dictionary:
                print "Current dictionary: %s" % dictionary
            else:
                print "Currently no dictionary set"

            availableDictionaries = charInfo.getAvailableDictionaries()
            if availableDictionaries:
                dictionaryList = []
                for dictionaryName in availableDictionaries:
                    dictData = CharacterInfo.DICTIONARY_INFO[dictionaryName]
                    dictionaryList.append(
                        "%s (%s)" % (dictionaryName, dictData['reading']))
                print "Available dictionaries: " + ", ".join(dictionaryList)
            else:
                print "No dictionaries available"

        else:
            print "Error: command unknown"
            usage()
            sys.exit(1)

    except KeyboardInterrupt:
        print >> sys.stderr, "Keyboard interrupt."

if __name__ == "__main__":
    main()
