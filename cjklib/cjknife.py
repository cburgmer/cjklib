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
*Command line interface* (*CLI*) to the library's functionality.

Check what this script offers on the command line with ``cjknife -h``.

The script's output depends on the following:

- dictionary setting in the cjklib's config file
- user locale settings are checked to guess appropriate values for the
    character locale and the default input and output readings
"""

__all__ = ["CharacterInfo"]

import sys
import getopt
import locale
import warnings

import cjklib
from cjklib import dbconnector
from cjklib import characterlookup
from cjklib import reading
from cjklib import dictionary
from cjklib import exception
from cjklib.util import (getConfigSettings, toCodepoint, isValidSurrogate,
    getCharacterList)

# work around http://bugs.python.org/issue2517
if sys.version_info < (2, 5):
    getExceptionString = lambda e: unicode(e.args[0])
elif sys.version_info < (2, 6):
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

    DICTIONARY_CHAR_LOCALE = {'HanDeDict': 'C', 'CFDICT': 'C', 'CEDICT': 'C',
        'CEDICTGR': 'T', 'EDICT': 'J'}
    """Dictionary default locale."""

    READING_DEFAULT_DICTIONARY = {'Pinyin': 'CEDICT'}
    """Dictionary to use by default for a given reading."""

    VARIANT_TYPE_NAMES = {'C': 'Compatible variant',
        'M': 'Semantic variants', 'P': 'Specialised semantic variants',
        'Z': 'Z-Variants', 'S': 'Simplified variants',
        'T': 'Traditional variants'}
    """List of character variants and their names."""

    def __init__(self, charLocale=None, characterDomain='Unicode',
        readingN=None, dictionaryN=None, dictionaryDatabaseUrl=None):
        """
        Initialises the CharacterInfo object.

        :type charLocale: str
        :param charLocale: *character locale* (one out of TCJKV)
        :type characterDomain: str
        :param characterDomain: *character domain* (see
            L{characterlookup.CharacterLookup.getAvailableCharacterDomains()})
        :type readingN: str
        :param readingN: name of reading
        :type dictionaryN: str
        :param dictionaryN: name of dictionary
        :type dictionaryDatabaseUrl: str
        :param dictionaryDatabaseUrl: database connection setting in the format
            ``driver://user:pass@host/database``.
        """
        if dictionaryN:
            dictObj = dictionary.getDictionaryClass(dictionaryN)

        if readingN:
            self.reading = readingN
        elif dictionaryN and hasattr(dictObj, 'READING') and dictObj.READING:
            self.reading = dictObj.READING
        else:
            self.reading = self.guessReading()

        if dictionaryDatabaseUrl:
            self.db = dbconnector.DatabaseConnector(
                {'sqlalchemy.url': dictionaryDatabaseUrl, 'attach': ['cjklib']})
        else:
            self.db = dbconnector.getDBConnector()

        self.readingFactory = reading.ReadingFactory(dbConnectInst=self.db)

        if dictionaryN:
            if dictionaryN not in self.getAvailableDictionaries():
                raise ValueError("dictionary not available")
            self.dictionary = dictionaryN
        else:
            if self.reading in self.READING_DEFAULT_DICTIONARY \
                and self.reading in self.getAvailableDictionaries():
                self.dictionary = self.READING_DEFAULT_DICTIONARY[self.reading]
            else:
                # get a dictionary that is compatible with the selected reading
                for dictName in self.getAvailableDictionaries():
                    dictObj = dictionary.getDictionaryClass(dictName)
                    if (hasattr(dictObj, 'READING') and dictObj.READING
                        and (dictObj.READING == self.reading
                            or self.readingFactory.isReadingConversionSupported(
                                dictObj.READING, self.reading))):
                        self.dictionary = dictName
                        break
                else:
                    self.dictionary = None

        if charLocale:
            self.locale = charLocale
        elif self.dictionary and self.dictionary in self.DICTIONARY_CHAR_LOCALE:
            self.locale = self.DICTIONARY_CHAR_LOCALE[self.dictionary]
        else:
            self.locale = self.guessCharacterLocale()

        self.characterLookup = characterlookup.CharacterLookup(self.locale,
            characterDomain, dbConnectInst=self.db)
        self.characterLookupTraditional = characterlookup.CharacterLookup('T',
            characterDomain, dbConnectInst=self.db)

    # Settings

    def guessCharacterLocale(self):
        """
        Guesses the best suited character locale using the user's locale
        settings.

        :rtype: str
        :return: locale
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

        :rtype: str
        :return: reading name
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

        :rtype: list of str
        :return: names of available dictionaries
        """
        if not hasattr(self, '_availableDictionaries'):
            self._availableDictionaries = [dic.PROVIDES for dic in
                dictionary.getAvailableDictionaries(self.db)]
            self._availableDictionaries.sort()

        return self._availableDictionaries

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

        :type string: str
        :param string: reading string
        :type readingN: str
        :param readingN: reading name
        :rtype: dict
        :return: reading options
        """
        # guess reading parameters
        classObj = self.readingFactory.getReadingOperatorClass(readingN)
        if hasattr(classObj, 'guessReadingDialect'):
            return classObj.guessReadingDialect(string)
        else:
            return {}

    def getEquivalentCharTable(self, componentList,
        includeEquivalentRadicalForms=True):
        u"""
        Gets a list structure of equivalent chars for the given list of
        characters.

        If option ``includeEquivalentRadicalForms`` is set, all equivalent forms
        will be searched for when a Kangxi radical is given.

        :type componentList: list of str
        :param componentList: list of character components
        :type includeEquivalentRadicalForms: bool
        :param includeEquivalentRadicalForms: if ``True`` then characters in the
            given component list are interpreted as representatives for their
            radical and all radical forms are included in the search. E.g. 肉
            will include ⺼ as a possible component.
        :rtype: list of list of str
        :return: list structure of equivalent characters

        .. todo::
            * Impl: Once mapping of similar radical forms exist (e.g. 言 and 訁)
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

        :type char: str
        :param char: Chinese character
        :type variants: list of str
        :param variants: Chinese characters
        :rtype: bool
        :return: ``True`` if the character is a semantic variant form of the
            given characters, ``False`` otherwise.
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

        :type readingString: str
        :param readingString: string written in the source reading
        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :rtype: str
        :return: the input string converted to the ``toReading``
        :raise DecompositionError: if the string can not be decomposed into
            basic entities with regards to the source reading or the given
            information is insufficient.
        :raise CompositionError: if the target reading's entities can not be
            composed.
        :raise ConversionError: on operations specific to the conversion between
            the two readings (e.g. error on converting entities).
        :raise UnsupportedError: if source or target reading is not supported
            for conversion.

        .. todo::
            * Fix: Conversion without tones will mostly break as the target
              reading doesn't support missing tone information. Prefering
              'diacritic' version (Pinyin/CantoneseYale) over 'numbers' as
              tone marks in the absence of any marks would solve this issue
              (forcing fifth tone), but would mean we prefer possible false
              information over the less specific estimation of the given
              entities as missing tonal information.
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

        :type radicalIndex: int
        :param radicalIndex: Kangxi radical index
        :rtype: list of str
        :return: list of matching Chinese characters
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

        :type readingString: str
        :param readingString: reading entity for lookup
        :type readingN: str
        :param readingN: name of reading
        :rtype: list of str
        :return: list of characters for the given reading
        :raise UnsupportedError: if no mapping between characters and target
            reading exists.
        :raise ConversionError: if conversion from the internal source reading
            to the given target reading fails.
        """
        if not readingN:
            readingN = self.reading
        options = self.getReadingOptions(readingString, readingN)
        return self.characterLookup.getCharactersForReading(readingString,
            readingN, **options)

    def getReadingForCharacters(self, charList):
        """
        Gets a list of readings for a given character string.

        :type charList: list
        :param charList: list of Chinese characters
        :rtype: list of list of str
        :return: a list of readings per character
        :raise exception.UnsupportedError: raised when a translation from
            character to reading is not supported by the given target reading
        :raise exception.ConversionError: if conversion for the string is not
            supported
        """
        readings = []
        for char in charList:
            stringList = self.characterLookup.getReadingForCharacter(char,
                self.reading)
            if stringList:
                readings.append(stringList)
            else:
                readings.append([char])
        return readings

    def getSimplified(self, charList):
        """
        Gets the Chinese simplified character representation for the given
        character string.

        :type charList: list
        :param charList: list of Chinese characters
        :rtype: list of list of str
        :return: list of simplified Chinese characters
        """
        simplified = []
        for char in charList:
            simplifiedVariants \
                = set(self.characterLookup.getCharacterVariants(char, 'S'))
            if self.isSemanticVariant(char, simplifiedVariants):
                simplifiedVariants.add(char)
            if len(simplifiedVariants) == 0:
                simplified.append([char])
            else:
                simplified.append(list(simplifiedVariants))
        return simplified

    def getTraditional(self, charList):
        """
        Gets the traditional character representation for the given character
        string.

        :type charList: list
        :param charList: list of Chinese characters
        :rtype: list of list of str
        :return: list of simplified Chinese characters

        .. todo::
            * Lang: Implementation is too simple to cover all aspects.
        """
        traditional = []
        for char in charList:
            traditionalVariants \
                = set(self.characterLookup.getCharacterVariants(char, 'T'))
            if self.isSemanticVariant(char, traditionalVariants):
                traditionalVariants.add(char)
            if len(traditionalVariants) == 0:
                traditional.append([char])
            else:
                traditional.append(list(traditionalVariants))
        return traditional

    def searchDictionary(self, searchString, readingN=None, limit=None):
        """
        Searches the dictionary for matches of the given string.

        :type searchString: str
        :param searchString: search string
        :type readingN: str
        :param readingN: reading name
        :type limit: int
        :param limit: maximum number of entries
        """
        if not hasattr(self, '_dictInstance'):
            dictObj = dictionary.getDictionaryClass(
                self.dictionary)

            options = {}
            # handle reading conversion
            if (hasattr(dictObj, 'READING') and dictObj.READING
                and self.readingFactory.isReadingConversionSupported(
                    dictObj.READING, self.reading)):
                options['columnFormatStrategies'] = {
                    'Reading': dictionary.format.ReadingConversion(
                        self.reading)}

            # handle multiple headwords
            if issubclass(dictObj, dictionary.CEDICT):
                if self.locale == 'C':
                    options['entryFactory'] \
                        = dictionary.entry.UnifiedHeadword('s')
                else:
                    options['entryFactory'] \
                        = dictionary.entry.UnifiedHeadword('t')

            # create dictionary
            self._dictInstance = dictObj(dbConnectInst=self.db, **options)

        options = self.getReadingOptions(searchString, readingN)

        return self._dictInstance.getFor(searchString, orderBy=['Reading'],
            limit=limit, reading=readingN, **options)

    def getCharactersForComponents(self, componentList,
        includeEquivalentRadicalForms=True):
        u"""
        Gets all characters that contain the given components.

        If option ``includeEquivalentRadicalForms`` is set, all equivalent forms
        will be searched for when a Kangxi radical is given.

        :type componentList: list of str
        :param componentList: list of character components
        :type includeEquivalentRadicalForms: bool
        :param includeEquivalentRadicalForms: if ``True`` then characters in the
            given component list are interpreted as representatives for their
            radical and all radical forms are included in the search. E.g. 肉
            will include ⺼ as a possible component.
        :rtype: list of tuple
        :return: list of pairs of matching characters and their *glyphs*
        :raise ValueError: if an invalid *character locale* is specified

        .. todo::
            * Impl: Once mapping of similar radical forms exist (e.g. 言 and 訁)
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
            - equivalent form (if type is ``'radical'``)
            - radical index
            - radical form (if available)
            - radical variants (if available)
            - stroke count (if available)
            - readings (if type is ``'character'``)
            - variants (if type is ``'character'``)
            - default glyph
            - glyphs

        :type char: str
        :param char: Chinese character
        :rtype: dict
        :return: character information as keyword value pairs
        """
        infoDict = {}

        # general information
        infoDict['char'] = char
        infoDict['locale'] = self.locale
        infoDict['locale name'] = self.CHAR_LOCALE_NAME[self.locale]
        infoDict['characterDomain'] = self.characterLookup.getCharacterDomain()
        infoDict['codepoint hex'] = 'U+%04X' % toCodepoint(char)
        infoDict['codepoint dec'] = str(toCodepoint(char))

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
                        = self.characterLookup.getStrokeCount(char,
                            glyph=glyph)

                    strokes = self.characterLookup.getStrokeOrder(char,
                        glyph=glyph, includePartial=True)
                    if set(strokes) != set([None]):
                        for i in range(len(strokes)):
                            if strokes[i] is None: strokes[i] = u'？'
                        infoDict['glyphs'][glyph]['stroke order'] = strokes

                        infoDict['glyphs'][glyph]['stroke order abbrev'] \
                            = self.characterLookup.getStrokeOrderAbbrev(char,
                                glyph=glyph, includePartial=True)
                except exception.NoInformationError:
                    pass
        except exception.NoInformationError:
            pass

        # character domains
        domains = self.characterLookup.getAvailableCharacterDomains()
        infoDict['domains'] = ['Unicode']
        for characterDomain in domains:
            if characterDomain == 'Unicode':
                continue
            # TODO wasting instances here
            charLookup = characterlookup.CharacterLookup('T', characterDomain,
                dbConnectInst=self.db)
            if charLookup.isCharacterInDomain(char):
                infoDict['domains'].append(characterDomain)

        return infoDict


def getPrintableList(stringList, joinString = ""):
    """
    Gets a printable representation for the given list.

    :type stringList: list of list of str
    :param stringList: strings that need to be concatenated for output
    :type joinString: str
    :param joinString: string that concatenates the different values
    :rtype: str
    :return: printable representation for the given list
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

    :type decompositionList: list
    :param decompositionList: a list of character decompositions
    :rtype: list of str
    :return: string representation of decomposition
    """
    # process a list of different decompositions
    stringList = []
    for decomposition in decompositionList:
        stringList.extend(getDecompositionForEntry(decomposition))
    return stringList

def getDecompositionForEntry(decomposition):
    """
    Gets a fixed width string representation of the given decomposition.

    :type decomposition: list
    :param decomposition: character decomposition tree
    :rtype: list of str
    :return: string representation of decomposition
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
  --database=DATABASEURL     database url
  -x SEARCHSTR               searches the dictionary (wildcards '_' and '%')
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
        + """\nCopyright (C) 2006-2010 cjklib developers

cjknife is part of cjklib.

cjklib is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version if not otherwise noted.
See the data files for their specific licenses.

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
            "convert-reading=", "set-dictionary=", "list-options", "database="])
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
        dictionaryN = configSettings['dictionary']
    else:
        dictionaryN = None
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
            if a.lower() in readingLookup:
                sourceReading = readingLookup[a.lower()]
            else:
                print >> sys.stderr, ("Error: '%s' is not a valid reading" % a
                    ).encode(output_encoding, "replace")
                sys.exit(1)

        # setting of target reading
        elif o in ("-t", "--target-reading"):
            if a.lower() in readingLookup:
                targetReading = readingLookup[a.lower()]
            else:
                print >> sys.stderr, ("Error: '%s' is not a valid reading" % a
                    ).encode(output_encoding, "replace")
                sys.exit(1)

        # setting of locale
        elif o in ("-l", "--locale"):
            if a.upper() in 'TCJKV':
                charLocale = a.upper()
            else:
                print >> sys.stderr, ("Error: '%s' is not a valid locale" % a
                    ).encode(output_encoding, "replace")
                sys.exit(1)

        # setting of locale
        elif o in ("-d", "--domain"):
            charDomain = a

        # setting of dictionary
        elif o in ("-w", "--set-dictionary"):
            dictionaries = dict([(dic.PROVIDES.lower(), dic.PROVIDES) for dic
                in dictionary.getDictionaryClasses()])
            if a.lower() in dictionaries:
                dictionaryN = dictionaries[a.lower()]
            else:
                print >> sys.stderr, ("Error: '%s' is not a valid dictionary" %
                    a).encode(output_encoding, "replace")
                sys.exit(1)

        # setting of database
        elif o in ("--database"):
            url = a

        else:
            # set this as a command executed later
            command = o
            parameter = a

    try:
        try:
            charInfo = CharacterInfo(charLocale=charLocale,
                readingN=targetReading, dictionaryN=dictionaryN,
                dictionaryDatabaseUrl=url)
        except ValueError:
            print >> sys.stderr, (("Error: dictionary '%(dict)s' not available."
                "\nInstall by running 'installcjkdict %(dict)s'")
                    % {'dict': dictionaryN})
            sys.exit(1)
        charLocale = charInfo.locale
        dictionaryN = charInfo.dictionary
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
            if len(parameter) == 1 or isValidSurrogate(parameter):
                infoDict = charInfo.getCharacterInformation(parameter)

                print ("Information for character " + infoDict['char'] + " (" \
                    + infoDict['locale name'] + " locale, " \
                    + infoDict['characterDomain'] + ' domain)')\
                    .encode(output_encoding, "replace")
                print "Unicode codepoint: " + infoDict['codepoint hex'] + " (" \
                    + infoDict['codepoint dec'] + ", "+ infoDict['type'] \
                    + " form)"
                print "In character domains: " + ', '.join(infoDict['domains'])
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
                # encoding errors can lead to a string > 1 char
                print repr(parameter)
                print "Error: bad parameter or encoding error"
                sys.exit(1)

        elif command in ("-q", "-r", "-f", "--get-reading", "--convert-form"):
            charList = getCharacterList(parameter)
            # character to reading conversion
            if command in ("-q", "-r", "--get-reading"):
                try:
                    readingList = charInfo.getReadingForCharacters(charList)
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
                simplified = getPrintableList(charInfo.getSimplified(charList))
                traditional = getPrintableList(charInfo.getTraditional(
                    charList))
                if not parameter in (simplified, traditional):
                    print "Warning: input string has mixed simplified and " \
                        + "traditional forms"
                if simplified == traditional:
                    print "Chinese simplified/Traditional: " \
                        + simplified.encode(output_encoding, "replace")
                else:
                    print "Simplified:  " \
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
            componentList = getCharacterList(parameter)
            charList = charInfo.getCharactersForComponents(componentList)
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
                print >> sys.stderr, ("Error: no dictionary available"
                    "\nInstall one by running 'installcjkdict DICTIONARY_NAME'")
                sys.exit(1)

            results = charInfo.searchDictionary(parameter, sourceReading)
            for entry in results:
                if entry.Reading:
                    string = ("%(Headword)s %(Reading)s %(Translation)s"
                        % entry._asdict())
                else:
                    string = "%(Headword)s %(Translation)s" % entry._asdict()
                print string.encode(output_encoding, "replace")

        # TODO deprecated
        elif command in ("-c", "-b", "-e"):
            alternative = parameter
            if command != "-b":
                alternative = '%%%s' % alternative
            if command != "-e":
                alternative = '%s%%' % alternative

            warnings.warn(("Option '%s' is deprecated"
                " and will disappear from future versions."
                " Use '-x \"%s\"' instead")  % (command, alternative),
                category=DeprecationWarning)

            if not charInfo.hasDictionary():
                print "Error: no dictionary available"
                sys.exit(1)

            results = charInfo.searchDictionary(alternative, sourceReading)
            for entry in results:
                if entry.Reading:
                    string = ("%(Headword)s %(Reading)s %(Translation)s"
                        % entry._asdict())
                else:
                    string = "%(Headword)s %(Translation)s" % entry._asdict()
                print string.encode(output_encoding, "replace")

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
            if dictionaryN:
                print "Current dictionary: %s" % dictionaryN
            else:
                print "Currently no dictionary set"

            availableDictionaries = charInfo.getAvailableDictionaries()
            if availableDictionaries:
                dictionaryList = []
                for dictionaryName in availableDictionaries:
                    dictObj = dictionary.getDictionaryClass(dictionaryName)

                    if dictObj.READING:
                        dictionaryList.append("%s (%s)"
                            % (dictionaryName, dictObj.READING))
                    else:
                        dictionaryList.append(dictionaryName)
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
