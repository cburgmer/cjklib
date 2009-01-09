#!/usr/bin/python
# -*- coding: utf8 -*-
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
Provides the central Chinese character based functions.
"""

# import math
from .dbconnector import DatabaseConnector
from . import reading
from . import exception
from . import dbconnector

class CharacterLookup:
    u"""
    CharacterLookup provides access to lookup methods related to Han characters.

    The real system of CharacterLookup lies in the database beneath where all
    relevant data is stored. So for nearly all methods this class needs access
    to a database. Thus on initialisation of the object a connection to a
    database is established, the logic for this provided by the
    L{DatabaseConnector}.

    See the L{DatabaseConnector} for supported database systems.

    CharacterLookup will try to read the config file from either /etc or the
    users home folder. If none is present it will try to open a SQLite database
    stored as C{db} in the same folder by default. You can override this
    behaviour by specifying additional parameters on creation of the object.

    Examples
    ========
    The following examples should give a quick view into how to use this
    package.
        - Create the CharacterLookup object with default settings
            (read from cjklib.conf or 'cjklib.db' in same directory as default):

            >>> from cjklib import characterlookup
            >>> cjk = characterlookup.CharacterLookup()

        - Get a list of characters, that are pronounced "국" in Korean:

            >>> cjk.getCharactersForReading(u'국', 'Hangul')
            [u'匊', u'國', u'局', u'掬', u'菊', u'跼', u'鞠', u'鞫', u'麯', u'麴']

        - Check if a character is included in another character as a component:

            >>> cjk.isComponentInCharacter(u'女', u'好')
            True

        - Get all Kangxi radical variants for Radical 184 (⾷) under the
            traditional locale:

            >>> cjk.getKangxiRadicalVariantForms(184, 'T')
            [u'\u2ede', u'\u2edf']

    X{Character locale}
    ===================
    During the development of characters in the different cultures character
    appearances changed over time to that extent, that the handling of radicals,
    character components and strokes needs to be distinguished, depending on the
    locale.

    To deal with this circumstance I{CharacterLookup} works with a character
    locale. Most of the methods of this class ask for a locale to be specified.
    In these cases the output of the method depends on the specified locale.

    For example in the traditional locale 这 has 8 strokes, but in
    simplified Chinese it has only 7, as the radical ⻌ has different stroke
    counts, depending on the locale.

    X{Z-variant}s
    =============
    One feature of Chinese characters is the glyph form describing the visual
    representation. This feature doesn't need to be unique and so many
    characters can be found in different writing variants e.g. character 福
    (English: luck) which has numerous forms.

    The Unicode Consortium does not include same characters of different
    actual shape in the Unicode standard (called I{Z-variant}s), except a few
    "double" entries which are included as to maintain backward compatibility.
    In fact a code point represents an abstract character not defining any
    visual representation. Thus a distinct appearance description including
    strokes and stroke order cannot be simply assigned to a code point but one
    needs to deal with the notion of I{Z-variants} representing distinct glyphs
    to which a visual description can be applied.

    The name Z-variant is derived from the three-dimensional model representing
    the space of characters relative to three axis, being the X axis
    representing the semantic space, the Y axis representing the abstract shape
    space and finally the Z axis for typeface differences (see "Principles of
    Han Unification" in: The Unicode Standard 5.0, chapter 12). Character
    presentations only differing in the Z dimension are generally unified.

    cjklib tries to offer a simple approach to handle different Z-variants. As
    character components, strokes and the stroke order depend on this variant,
    methods dealing with this kind will ask for a I{Z-variant} value to be
    specified. In these cases the output of the method depends on the specified
    variant.

    Z-variants and character locales
    --------------------------------
    Deviant stroke count, stroke order or decomposition into character
    components for different I{character locales} is implemented using different
    I{Z-variant}s. For the example given above the entry 这 with 8 strokes is
    given as one Z-variant and the form with 7 strokes is given as another
    Z-variant.

    In most cases one might only be interested in a single visual appearance,
    the "standard" one. This visual appearance would be the one generally used
    in the specific locale.

    Instead of specifying a certain Z-variant most functions will allow for
    passing of a character locale. Giving the locale will apply the default
    Z-variant given by the mapping defined in the database which can be obtained
    by calling L{getLocaleDefaultZVariant()}.

    More complex relations as which of several Z-variants for a given character
    are used in a given locale are not covered.

    Kangxi radical functions
    ========================
    Using the Unihan database queries about the Kangxi radical of characters can
    be made.
    It is possible to get a Kangxi radical for a character or lookup all
    characters for a given radical.

    Unicode has extra code points for radical forms (e.g. ⾔), here called
    X{Unicode radical form}s, and radical variant forms (e.g. ⻈), here called
    X{Unicode radical variant}s. These characters should be used when explicitly
    referring to their function as radicals.
    For most of the radicals and variants their exist complementary character
    forms which have the same appearance (e.g. 言 and 讠) and which shall be
    called X{equivalent character}s here.

    Mapping from one to another side is not trivially possible, as some forms
    only exist as radical forms, some only as character forms, but from their
    meaning used in the radical context (called X{isolated radical character}s
    here, e.g. 訁 for Kangxi radical 149).

    Additionally a one to one mapping can't be guaranteed, as some forms have
    two or more equivalent forms in another domain, and mapping is highly
    dependant on the locale.

    CharacterLookup provides methods for dealing with this different kinds of
    characters and the mapping between them.

    X{Character decomposition}
    ==========================
    Many characters can be decomposed into two or more components, that again
    are Chinese characters. This fact can be used in many ways, including
    character lookup, finding patterns for font design or studying characters.
    Even the stroke order and stroke count can be deduced from the stroke
    information of the character's components.

    Character decomposition is highly dependant on the appearance of the
    character, so both I{Z-variant} and I{character locale} need to be clear
    when looking at a decomposition into components.

    More points render this task more complex: decomposition into one set of
    components is not distinct, some characters can be broken down into
    different sets. Furthermore sometimes one component can be given, but the
    other component will not be encoded as a character in its own right.

    These components again might be characters that contain further components
    (again not distinct ones), thus a complex decomposition in several steps is
    possible.

    The basis for the character decomposition lies in the database, where all
    decompositions are stored, using X{Ideographic Description Sequence}s
    (I{IDS}). These sequences consist of Unicode X{IDS operator}s and characters
    to describe the structure of the character. There are
    X{binary IDS operator}s to describe decomposition into two components (e.g.
    ⿰ for one component left, one right as in 好: ⿰女子) or
    X{trinary IDS operator}s for decomposition into three components (e.g. ⿲
    for three components from left to right as in 辨: ⿲⾟刂⾟). Using
    I{IDS operator}s it is possible to give a basic structural information, that
    in many cases is enough for example to derive a overall stroke order from
    two single sets of stroke orders. Further more it is possible to look for
    redundant information in different entries and thus helps to keep the
    definition data clean.

    This class provides methods for retrieving the basic partition entries,
    lookup of characters by components and decomposing as a tree from the
    character as a root down to the X{minimal components} as leaf nodes.

    TODO: Policy about what to classify as partition.

    Strokes
    =======
    Chinese characters consist of different strokes as basic parts. These
    strokes are written in a mostly distinct order called the X{stroke order}
    and have a distinct X{stroke count}.

    The I{stroke order} in the writing of Chinese characters is important e.g.
    for calligraphy or students learning new characters and is normally fixed as
    there is only one possible stroke order for each character. Further more
    there is a fixed set of possible strokes and these strokes carry names.

    As with character decomposition the I{stroke order} and I{stroke count} is
    highly dependant on the appearance of the character, so both I{Z-variant}
    and I{character locale} need to be known.

    Further more the order of strokes can be useful for lookup of characters,
    and so CharacterLookup provides different methods for getting the stroke
    count, stroke order, lookup of stroke names and lookup of characters by
    stroke types and stroke order.

    Most methods work with an abbreviation of stroke names using the first
    letters of each syllable of the Chinese name in Pinyin.

    The I{stroke order} is not always quite clear and even academics fight about
    which order should be considered the correct one, a discussion that
    shouldn't be taking lightly. This circumstance should be considered
    when working with I{stroke order}s.

    TODO: About plans of cjklib how to support different views on the stroke
    order

    TODO: About the different classifications of strokes

    Readings
    ========
    See module L{reading} for a detailed description.

    @see:
        - Radicals:
            U{http://en.wikipedia.org/wiki/Radical_(Chinese_character)}
        - Z-variants:
            U{http://www.unicode.org/reports/tr38/tr38-5.html#N10211}

    @todo Fix:  Incorporate stroke lookup (bigram) techniques
    @todo Fix:  How to handle character forms (either decomposition or stroke
        order), that can only be found as a component in other characters? We
        already mark them by flagging it with an 'S'.
    @todo Impl: Think about applying locale at object creation time and not
        passing it on every method call. Would make the class easier to use.
    @todo Impl: Create a method for specifying which character range is of
        interest for the return values of methods. Narrowing the return results
        is a further way to locale dependant responses. E.g. cjknife could take
        this into account when only displaying characters that can be displayed
        with the current locale (BIG5, GBK...).
    @todo Lang: Add option to component decomposition methods to stop on Kangxi
        radical forms without breaking further down beyond those.
    """

    CHARARACTER_READING_MAPPING = {'Hangul': ('CharacterHangul', {}),
        'Jyutping': ('CharacterJyutping', {'case': 'lower'}),
        'Pinyin': ('CharacterPinyin', {'toneMarkType': 'Numbers',
            'case': 'lower'})
        }
    """
    A list of readings for which a character mapping exists including the
    database's table name and the reading dialect parameters.

    On conversion the first matching reading will be selected, so supplying
    several equivalent readings has limited use.
    """

    def __init__(self, databaseSettings={}, dbConnectInst=None):
        """
        Initialises the CharacterLookup.

        If no parameters are given default values are assumed for the connection
        to the database. Other options can be either passed as dictionary to
        databaseSettings, or as an instantiated L{DatabaseConnector} given to
        dbConnectInst, the latter one will be preferred.

        @type databaseSettings: dict
        @param databaseSettings: database settings passed to the
            L{DatabaseConnector}, see there for feasible values
        @type dbConnectInst: instance
        @param dbConnectInst: instance of a L{DatabaseConnector}
        """
        # get connector to database
        if dbConnectInst:
            self.db = dbConnectInst
        else:
            self.db = DatabaseConnector.getDBConnector(databaseSettings)

        self.readingFactory = None

        # test for existing tables that can be used to speed up look up
        self.hasComponentLookup = self.db.tableExists('ComponentLookup')
        self.hasStrokeCount = self.db.tableExists('StrokeCount')

    def _getReadingFactory(self):
        """
        Gets the L{ReadingFactory} instance.

        @rtype: instance
        @return: a L{ReadingFactory} instance.
        """
        # get reading factory
        if not self.readingFactory:
            self.readingFactory = reading.ReadingFactory(dbConnectInst=self.db)
        return self.readingFactory

    #{ Character reading lookup

    def getCharactersForReading(self, entity, readingN, **options):
        """
        Gets all know characters for the given reading.

        @type entity: str
        @param entity: reading entity for lookup
        @type readingN: str
        @param readingN: name of reading
        @param options: additional options for handling the reading input
        @rtype: list of str
        @return: list of characters for the given reading
        @raise ValueError: if invalid reading entity or several entities are
            given.
        @raise UnsupportedError: if no mapping between characters and target
            reading exists.
        @raise ConversionError: if conversion from the internal source reading
            to the given target reading fails.
        """
        # check reading string is correct
        if not self._getReadingFactory().isReadingEntity(entity, readingN,
            **options):
            raise ValueError("invalid reading entity or several entities given")
        # check for available mapping from Chinese characters to a compatible
        #   reading
        compatReading = self._getCompatibleCharacterReading(readingN)
        table, compatOptions = self.CHARARACTER_READING_MAPPING[compatReading]

        # translate reading form to target reading, for readingN=compatReading
        #   get standard form if supported
        readingFactory = self._getReadingFactory()
        if readingN != compatReading \
            or readingFactory.isReadingConversionSupported(readingN, readingN):
            entity = readingFactory.convert(entity, readingN, compatReading,
                sourceOptions=options, targetOptions=compatOptions)
        # lookup characters
        return self.db.selectSoleValue(table, 'ChineseCharacter',
            {'Reading': entity})

    def getReadingForCharacter(self, char, readingN, **options):
        """
        Gets all know readings for the character in the given target reading.

        @type char: str
        @param char: Chinese character for lookup
        @type readingN: str
        @param readingN: name of target reading
        @param options: additional options for handling the reading output
        @rtype: str
        @return: list of reading entities for the given character
        @raise UnsupportedError: if no mapping between characters and target
            reading exists.
        @raise ConversionError: if conversion from the internal source reading
            to the given target reading fails.
        """
        # check for available mapping from Chinese characters to a compatible
        # reading
        compatReading = self._getCompatibleCharacterReading(readingN, False)
        table, compatOptions = self.CHARARACTER_READING_MAPPING[compatReading]
        readingFactory = self._getReadingFactory()

        # lookup readings
        readings = self.db.selectSoleValue(table, 'Reading',
            {'ChineseCharacter': char}, orderBy=['Reading'])

        # check if we need to convert reading
        if compatReading != readingN \
            or readingFactory.isReadingConversionSupported(readingN, readingN):
            # translate reading forms to target reading, for
            #   readingN=characterReading get standard form if supported
            transReadings = []
            for readingStr in readings:
                readingStr = readingFactory.convert(readingStr, compatReading,
                    readingN, sourceOptions=compatOptions,
                    targetOptions=options)
                if readingStr not in transReadings:
                    transReadings.append(readingStr)
            return transReadings
        else:
            return readings

    def _getCompatibleCharacterReading(self, readingN, toCharReading=True):
        """
        Gets a reading where a mapping from to Chinese characters is supported
        and that is compatible (a conversion is supported) to the given reading.

        @type readingN: str
        @param readingN: name of reading
        @type toCharReading: bool
        @param toCharReading: C{True} if conversion is done in direction to the
            given reading, C{False} otherwise
        @rtype: str
        @return: a reading that is compatible to the given one and where
            character lookup is supported
        @raise UnsupportedError: if no mapping between characters and target
            reading exists.
        """
        # iterate all available char-reading mappings to find a compatible
        # reading
        for characterReading in self.CHARARACTER_READING_MAPPING.keys():
            if readingN == characterReading:
                return characterReading
            elif toCharReading:
                if self._getReadingFactory().isReadingConversionSupported(
                    readingN, characterReading):
                    return characterReading
            elif not toCharReading:
                if self._getReadingFactory().isReadingConversionSupported(
                    characterReading, readingN):
                    return characterReading
        raise exception.UnsupportedError("reading '" + readingN \
            + "' not supported for character lookup")

    #}

    def _locale(self, locale):
        """
        Gets the locale search value for a database lookup on databases with
        I{character locale} dependant content.

        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: str
        @return: search locale used for SQL select
        @raise ValueError: if invalid I{character locale} specified
        @todo Fix: This probably requires a full table scan
        """
        locale = locale.upper()
        if not locale in set('TCJKV'):
            raise ValueError("'" + locale + "' is not a valid character locale")
        return '%' + locale + '%'

    #{ Character variant lookup

    def getCharacterVariants(self, char, variantType):
        """
        Gets the variant forms of the given type for the character.

        The type can be one out of:
            - C, I{compatible character} form (if character was added to Unicode
                to maintain compatibility and round-trip convertibility)
            - M, I{semantic variant} forms, which are often used interchangeably
                instead of the character.
            - P, I{specialised semantic variant} forms, which are often used
                interchangeably instead of the character but limited to certain
                contexts.
            - Z, I{Z-variant} forms, which only differ in typeface (and would
                have been unified if not to maintain round trip convertibility)
            - S, I{simplified Chinese character} forms, originating from the
                character simplification process of the PR China.
            - T, I{traditional character} forms for a
                I{simplified Chinese character}.

        Variants depend on the locale which is not taken into account here. Thus
        some of the returned characters might be only be variants under some
        locales.

        @type char: str
        @param char: Chinese character
        @type variantType: str
        @param variantType: type of variant(s) to be returned
        @rtype: list of str
        @return: list of character variant(s) of given type

        @todo Docu: Write about different kinds of variants
        @todo Impl: Give a source on variant information as information can
            contradict itself
            (U{http://www.unicode.org/reports/tr38/tr38-5.html#N10211}). See
            呆 (U+5446) which has one form each for semantic and specialised
            semantic, each derived from a different source. Change also in
            L{getAllCharacterVariants()}.
        @todo Lang: What is the difference on Z-variants and
            compatible variants? Some links between two characters are
            bidirectional, some not. Is there any rule?
        """
        variantType = variantType.upper()
        if not variantType in set('CMPZST'):
            raise ValueError("'" + variantType \
                + "' is not a valid variant type")
        return self.db.selectSoleValue('CharacterVariant', 'Variant',
            {'ChineseCharacter': char, 'Type': variantType})

    def getAllCharacterVariants(self, char):
        """
        Gets all variant forms regardless of the type for the character.

        A list of tuples is returned, including the character and its variant
        type. See L{getCharacterVariants()} for variant types.

        Variants depend on the locale which is not taken into account here. Thus
        some of the returned characters might be only be variants under some
        locales.

        @type char: str
        @param char: Chinese character
        @rtype: list of tuple
        @return: list of character variant(s) with their type
        """
        return self.db.select('CharacterVariant', ['Variant', 'Type'],
            {'ChineseCharacter': char})

    def getLocaleDefaultZVariant(self, char, locale):
        """
        Gets the default Z-variant for the given character under the given
        locale.

        The Z-variant returned is an index to the internal database of different
        character glyphs and represents the most common glyph used under the
        given locale.

        @type char: str
        @param char: Chinese character
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: int
        @return: Z-variant
        @raise NoInformationError: if no Z-variant information is available
        @raise ValueError: if invalid I{character locale} specified
        """
        zVariant = self.db.selectSingleEntrySoleValue('LocaleCharacterVariant',
            'ZVariant', {'ChineseCharacter': char,
            'Locale': self._locale(locale)})
        if zVariant != None:
            return zVariant
        else:
            # if no entry given, assume default
            return self.getCharacterZVariants(char)[0]

    def getCharacterZVariants(self, char):
        """
        Gets a list of character Z-variant indices (glyphs) supported by the
        database.

        A Z-variant index specifies a particular character glyph which is needed
        by several glyph-dependant methods instead of the abstract character
        defined by Unicode.

        @type char: str
        @param char: Chinese character
        @rtype: list of int
        @return: list of supported Z-variants
        @raise NoInformationError: if no Z-variant information is available
        """
        # return all known variant indices, order to be deterministic
        result = self.db.selectSoleValue('ZVariants', 'ZVariant',
            {'ChineseCharacter': char}, orderBy=['ZVariant'])
        if not result:
            raise exception.NoInformationError(
                "No Z-variant information available for '" + char + "'")

        return result

    #}
    #{ Character stroke functions

    def getStrokeCount(self, char, locale=None, zVariant=0):
        """
        Gets the stroke count for the given character.

        @type char: str
        @param char: Chinese character
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: int
        @return: stroke count of given character
        @raise NoInformationError: if no stroke count information available
        @raise ValueError: if an invalid I{character locale} is specified
        @attention: The quality of the returned data depends on the sources used
            when compiling the database. Unihan itself only gives very general
            stroke order information without being bound to a specific glyph.
        """
        if locale != None:
            zVariant = self.getLocaleDefaultZVariant(char, locale)

        # if table exists use it
        if self.hasStrokeCount:
            result = self.db.selectSingleEntrySoleValue('StrokeCount',
                'StrokeCount', {'ChineseCharacter': char, 'ZVariant': zVariant})
            if not result:
                raise exception.NoInformationError(
                    "Character has no stroke count information")
            return result
        else:
            # use incomplete way with using the stroke order (there might be
            #   less stroke order entries than stroke count entries)
            try:
                so = self.getStrokeOrder(char, zVariant=zVariant)
                strokeList = so.replace(' ', '-').split('-')
                return len(strokeList)
            except exception.NoInformationError:
                raise exception.NoInformationError(
                    "Character has no stroke count information")

    def getStrokeCountDict(self):
        """
        Gets the full stroke count table from the database.

        @rtype: dict
        @return: dictionary of key pair character, Z-variant and value stroke
            count
        @attention: The quality of the returned data depends on the sources used
            when compiling the database. Unihan itself only gives very general
            stroke order information without being bound to a specific glyph.
        """
        return dict([((char, zVariant), strokeCount) \
            for char, zVariant, strokeCount in self.db.select('StrokeCount',
                ['ChineseCharacter', 'ZVariant', 'StrokeCount'])])

    #_strokeIndexLookup = {}
    #"""A dictionary containing the stroke indices for a set index length."""
    #def getStrokeIndexLookup(self, indexLength):
        #"""
        #Gets a stroke lookup table for the given index length and assigns each
        #stroke taken into account with an unique index.

        #The first M{indexLength-1} most frequent strokes are taken into account,
        #all other strokes are rejected from the index.

        #@type indexLength: int
        #@param indexLength: length of the index
        #@rtype: dict
        #@return: dictionary for performing stroke lookups
        #"""
        #if not self._strokeIndexLookup.has_key(indexLength):
            #strokeTable = self.db.selectSoleValue('StrokeFrequency',
                #'Stroke', orderBy = ['Frequency'], orderDescending=True,
                #limit = indexLength)
            #counter = 0
            #strokeIndexLookup = {}
            ## put all stroke abbreviations of stroke from strokeTable into dict
            #for stroke in strokeTable:
                #strokeIndexLookup[stroke] = counter
                #counter = counter + 1
            #self._strokeIndexLookup[indexLength] = strokeIndexLookup
        #return self._strokeIndexLookup[indexLength]

    #def _getStrokeBitField(self, strokeSet, bitLength=30):
        #"""
        #Gets the bigram bit field for the given stroke set.

        #The first M{bitLength-1} strokes are assigned to one bit position, all
        #other strokes are assigned to position M{bitLength}. Bits for strokes
        #present are set to 1 all others to 0.

        #@type strokeSet: list of str
        #@param strokeSet: set of stroke types
        #@type bitLength: int
        #@param bitLength: length of the bit field
        #@rtype: int
        #@return: bit field with bits for present strokes set to 1
        #"""
        #strokeIndexLookup = self.getStrokeIndexLookup(bitLength-1)
        ## now build bit field
        #bitField = 0
        #for strokeAbbrev in strokeSet:
            #stroke = self.getStrokeForAbbrev(strokeAbbrev)
            #if strokeIndexLookup.has_key(stroke):
                #index = strokeIndexLookup[stroke]
            #else:
                #index = bitLength
            #bitField = bitField | int(math.pow(2, index))
        #return bitField

    #_bigramIndexLookup = {}
    #"""A dictionary containing the bigram indices for a set bigram index
        #length."""
    #def _getBigramIndexLookup(self, indexLength):
        #"""
        #Gets a bigram lookup table for the given index length and assigns each
        #bigram taken into account with an unique index.

        #The first M{indexLength-1} most frequent bigrams are taken into account,
        #all other bigrams are rejected from the index.

        #@type indexLength: int
        #@param indexLength: length of the index
        #@rtype: dict
        #@return: dictionary for performing bigram lookups
        #"""
        #if not self._bigramIndexLookup.has_key(indexLength):
            #counter = 0
            #bigramIndexLookup = {}
            ## put all stroke abbreviations of stroke from strokeTable into dict
            #bigramTable = self.db.selectSoleValue('StrokeBigramFrequency',
                #'StrokeBigram', orderBy = ['Frequency'], orderDescending = True,
                #limit = indexLength)
            #for bigram in bigramTable:
                #bigramIndexLookup[bigram] = counter
                #counter = counter + 1
            #self._bigramIndexLookup[indexLength] = bigramIndexLookup
        #return self._bigramIndexLookup[indexLength]

    #def _getBigramBitField(self, strokeList, bitLength=30):
        #"""
        #Gets the bigram bit field for the given list of strokes.

        #The first M{bitLength-1} bigrams are assigned to one bit position, all
        #other bigrams are assigned to position M{bitLength}. Bits for bigrams
        #present are set to 1 all others to 0.

        #@type strokeList: list of str
        #@param strokeList: list of stroke
        #@type bitLength: int
        #@param bitLength: length of the bit field
        #@rtype: int
        #@return: bit field with bits for present bigrams set to 1
        #"""
        #bigramIndexLookup = self._getBigramIndexLookup(bitLength-1)
        ## now build bit field
        #bitField = 0
        #lastStroke = self.getStrokeForAbbrev(strokeList[0])
        #for strokeAbbrev in strokeList[1:]:
            #stroke = self.getStrokeForAbbrev(strokeAbbrev)
            #if bigramIndexLookup.has_key(lastStroke+stroke):
                #index = bigramIndexLookup[lastStroke+stroke]
            #else:
                #index = bitLength
            #bitField = bitField | int(math.pow(2, index))
        #return bitField

    #def getStrokeOrderDistance(self, strokeOrderListA, strokeOrderListB,
        #substitutionPenalty=1, insertionPenalty=1.5, deletionPenalty=1.5):
        #"""
        #Calculates the Levenshtein distance for the two given stroke orders.
 
        #Stroke are given as abbreviated form.

        #@type strokeOrderListA: list of str
        #@param strokeOrderListA: strokes A ordered in list form
        #@type strokeOrderListB: list of str
        #@param strokeOrderListB: strokes B ordered in list form
        #@type substitutionPenalty: float
        #@param substitutionPenalty: penalty for substituting elements
        #@type insertionPenalty: float
        #@param insertionPenalty: penalty for inserting elements
        #@type deletionPenalty: float
        #@param deletionPenalty: penalty for deleting elements
        #@rtype: float
        #@return: Levenshtein distance of both stroke orders
        #"""
        #n = len(strokeOrderListA)
        #m = len(strokeOrderListB)
        #d = [[0 for i in range(0, n+1)]
            #for j in range(0, m+1)]
        #for i in range(0, n+1):
            #d[0][i] = i
        #for j in range(0, m+1):
            #d[j][0] = j
        #for i in range(1, n+1):
            #for j in range(1, m+1):
                #if strokeOrderListA[i-1] == strokeOrderListB[j-1]:
                    #subst = 0
                #else:
                    #subst = substitutionPenalty
                #d[j][i] = min(d[j-1][i-1] + subst,               # substitution
                              #d[j][i-1] + insertionPenalty,      # insertion
                              #d[j-1][i] + deletionPenalty)       # deletion
        #return d[m][n]

    #def getCharactersForStrokes(self, strokeList, locale):
        #"""
        #Gets all characters for the given list of stroke types.
 
        #Stroke types are given as abbreviated form.

        #@type strokeList: list of str
        #@param strokeList: list of stroke types
        #@type locale: str
        #@param locale: I{character locale} (one out of TCJKV)
        #@rtype: list of tuple
        #@return: list of character, Z-variant pairs having the same stroke types
        #@raise ValueError: if an invalid I{character locale} is specified
        #"""
        #return self.db.select('StrokeBitField',
            #['ChineseCharacter', 'ZVariant'],
           # {'StrokeField': self._getStrokeBitField(strokeList),
            #'Locale': self._locale(locale)},
            #orderBy = ['ChineseCharacter'])

    #def getCharactersForStrokeOrder(self, strokeOrder, locale):
        #"""
        #Gets all characters for the given stroke order.
 
        #Strokes are given as abbreviated form and can be separated by a
        #space or a hyphen.

        #@type strokeOrder: str
        #@param strokeOrder: stroke order consisting of stroke abbreviations
            #separated by a space or hyphen
        #@type locale: str
        #@param locale: I{character locale} (one out of TCJKV)
        #@rtype: list of tuple
        #@return: list of character, Z-variant pairs
        #@raise ValueError: if an invalid I{character locale} is specified
        #@bug:  Table 'strokebitfield' doesn't seem to include entries from
            #'strokeorder' but only from character decomposition table:

            #>>> print ",".join([a for a,b in cjk.getCharactersForStrokes(['S','H','HZ'], 'C')])
            #亘,卓,占,古,叶,吉,吐,吕,咕,咭,哇,哩,唱,啡,坦,坫,垣,埋,旦,旧,早,旰,旱,旺,昌,玷,理,田,畦,眭,罟,罡,罩,罪,量,靼,鞋

        #@bug:  Character lookup from stroke order seems to be broken. 皿 is in
            #database but wouldn't be found::
                #./cjknife -o S-HZ-S-S-H
                #田旦占
        #"""
        #strokeList = strokeOrder.replace(' ', '-').split('-')

        #results = self.db.select(['StrokeBitField s', 'BigramBitField b',
            #'StrokeCount c'], ['s.ChineseCharacter', 's.ZVariant'],
           # {'s.Locale': '=b.Locale', 's.Locale': '=c.Locale',
            #'s.ChineseCharacter': '=b.ChineseCharacter',
            #'s.ChineseCharacter': '=c.ChineseCharacter',
            #'s.ZVariant': '=b.ZVariant', 's.ZVariant': '=c.ZVariant',
            #'s.Locale': self._locale(locale),
            #'s.StrokeField': self._getStrokeBitField(strokeList),
            #'b.BigramField': self._getBigramBitField(strokeList),
            #'c.StrokeCount': len(strokeList)})
        #resultList = []
        ## check exact match of stroke order for all possible matches
        #for char, zVariant in results:
            #so = self.getStrokeOrder(char, locale, zVariant)
            #soList = so.replace(' ', '-').split('-')
            #if soList == strokeList:
                #resultList.append((char, zVariant))
        #return resultList

    #def getCharactersForStrokeOrderFuzzy(self, strokeOrder, locale, minEstimate,
        #strokeCountVariance=2, strokeVariance=2, bigramVariance=3):
        #"""
        #Gets all characters for the given stroke order reaching the minimum
        #estimate using a fuzzy search as to allowing fault-tolerant searches.
 
        #Strokes are given as abbreviated form and can be separated by a
        #space or a hyphen.

        #The search is commited by looking for equal stroke count, equal stroke
        #types and stroke bigrams (following pairs of strokes). Specifying
        #C{strokeCountVariance} for allowing variance in stroke count,
        #C{strokeVariance} for variance in stroke occurrences (for frequent ones)
        #and C{bigramVariance} for variance in frequent stroke bigrams can adapt
        #query to fit needs of minimum estimate. Allowing less variances will
        #result in faster queries but lesser results, thus possibly omiting good
        #matches.

        #An estimate on the first search results is calculated and only entries
        #reaching over the specified minimum estimate are included in the output.

        #@type strokeOrder: str
        #@param strokeOrder: stroke order consisting of stroke abbreviations
            #separated by a space or hyphen
        #@type locale: str
        #@param locale: I{character locale} (one out of TCJKV)
        #@type minEstimate: int
        #@param minEstimate: minimum estimate that entries in output have to
            #reach
        #@type strokeCountVariance: int
        #@param strokeCountVariance: variance of stroke count
        #@type strokeVariance: int
        #@param strokeVariance: variance of stroke types
        #@type bigramVariance: int
        #@param bigramVariance: variance of stroke bigrams
        #@rtype: list of tuple
        #@return: list of character, Z-variant pairs
        #@raise ValueError: if an invalid I{character locale} is specified
        #"""
        #strokeList = strokeOrder.replace(' ', '-').split('-')
        #strokeCount = len(strokeList)
        #strokeBitField = self._getStrokeBitField(strokeList)
        #bigramBitField = self._getBigramBitField(strokeList)
        #results = self.db.select(['StrokeBitField s', 'BigramBitField b',
            #'StrokeCount c'], ['s.ChineseCharacter', 's.ZVariant'],
           # {'s.Locale': '=b.Locale', 's.Locale': '=c.Locale',
            #'s.ChineseCharacter': '=b.ChineseCharacter',
            #'s.ChineseCharacter': '=c.ChineseCharacter',
            #'s.ZVariant': '=b.ZVariant', 's.ZVariant': '=c.ZVariant',
            #'s.Locale': self._locale(locale),
            #'bit_count(s.StrokeField ^ ' + str(strokeBitField) + ')':
            #'<=' + str(strokeVariance),
            #'bit_count(b.BigramField ^ ' + str(bigramBitField) + ')':
            #'<=' + str(bigramVariance),
            #'c.StrokeCount': '>=' + str(strokeCount-strokeCountVariance),
            #'c.StrokeCount': '<=' + str(strokeCount+strokeCountVariance)},
            #distinctValues=True)
        #resultList = []
        #for char, zVariant in results:
            #so = self.getStrokeOrder(char, locale, zVariant)
            #soList = so.replace(' ', '-').split('-')
            #estimate = 1.0 / \
                #(math.sqrt(1.0 + (8*float(self.getStrokeOrderDistance(
                    #strokeList, soList)) / strokeCount)))
            #if estimate >= minEstimate:
                #resultList.append((char, zVariant, estimate))
        #return resultList

    _strokeLookup = None
    """A dictionary containing stroke forms for stroke abbreviations."""
    def getStrokeForAbbrev(self, abbrev):
        """
        Gets the stroke form for the given abbreviated name (e.g. 'HZ').

        @type abbrev: str
        @param abbrev: abbreviated stroke name
        @rtype: str
        @return: Unicode stroke character
        @raise ValueError: if invalid stroke abbreviation is specified
        """
        # build stroke lookup table for the first time
        if not self._strokeLookup:
            self._strokeLookup = {}
            for stroke, strokeAbbrev in self.db.select('Strokes',
                ['Stroke', 'StrokeAbbrev']):
                self._strokeLookup[strokeAbbrev] = stroke
        if self._strokeLookup.has_key(abbrev):
            return self._strokeLookup[abbrev]
        else:
            raise ValueError(abbrev + " is no valid stroke abbreviation")

    def getStrokeForName(self, name):
        u"""
        Gets the stroke form for the given name (e.g. '横折').

        @type name: str
        @param name: Chinese name of stroke
        @rtype: str
        @return: Unicode stroke char
        @raise ValueError: if invalid stroke name is specified
        """
        stroke = self.db.selectSingleEntrySoleValue('Strokes', 'Stroke',
            {'Name': name})
        if stroke:
            return stroke
        else:
            raise ValueError(name + " is no valid stroke name")

    def getStrokeOrder(self, char, locale=None, zVariant=0):
        """
        Gets the stroke order sequence for the given character.

        The stroke order is constructed using the character decomposition into
        components. As the stroke order information for some components might be
        not obtainable the returned stroke order might be partial.

        @type char: str
        @param char: Chinese character
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: str
        @return: string of stroke abbreviations separated by spaces and hyphens.
        @raise ValueError: if an invalid I{character locale} is specified
        @raise NoInformationError: if no stroke order information available
        """

        def getStrokeOrderEntry(char, zVariant):
            """
            Gets the stroke order sequence for the given character from the
            database's stroke order lookup table.

            @type char: str
            @param char: Chinese character
            @type zVariant: int
            @param zVariant: I{Z-variant} of the first character
            @rtype: str
            @return: string of stroke abbreviations separated by spaces and
                hyphens.
            @raise NoInformationError: if no stroke order information available
            @raise ValueError: if an invalid I{character locale} is specified
            """
            # get forms for once char, include radical equivalents
            forms = [char]

            result = self.db.selectSingleEntrySoleValue('StrokeOrder',
                'StrokeOrder', {'ChineseCharacter': forms,
                'ZVariant': zVariant}, distinctValues=True)
            if not result:
                raise exception.NoInformationError(
                    "Character has no stroke order information")
            return result

        def getFromDecomposition(decompositionTreeList):
            """
            Gets stroke order from the tree of a single partition entry.

            @type decompositionTreeList: list
            @param decompositionTreeList: list of decomposition trees to derive
                the stroke order from
            @rtype: str
            @return: string of stroke abbreviations separated by spaces and
                hyphens.
            @raise NoInformationError: if no stroke order information available
            """

            def getFromEntry(subTree, index=0):
                """
                Goes through a single layer of a tree recursively.

                @type subTree: list
                @param subTree: decomposition tree to derive the stroke order
                    from
                @type index: int
                @param index: index of current layer
                @rtype: str
                @return: string of stroke abbreviations separated by spaces and
                    hyphens.
                @raise NoInformationError: if no stroke order information
                    available
                """
                strokeOrder = []
                if type(subTree[index]) != type(()):
                    # IDS operator
                    character = subTree[index]
                    if self.isBinaryIDSOperator(character):
                        # check for IDS operators we can't make any order
                        # assumption about
                        if character in [u'⿴', u'⿻']:
                            raise exception.NoInformationError(
                                "Character has no stroke order information")
                        else:
                            if character in [u'⿺', u'⿶']:
                                # IDS operators with order right one first
                                subSequence = [1, 0]
                            else:
                                # IDS operators with order left one first
                                subSequence = [0, 1]
                            # Get stroke order for both components
                            subStrokeOrder = []
                            for i in range(0,2):
                                so, index = getFromEntry(subTree, index+1)
                                subStrokeOrder.append(so)
                            # Append in proper order
                            for seq in subSequence:
                                strokeOrder.append(subStrokeOrder[seq])
                    elif self.isTrinaryIDSOperator(character):
                        # Get stroke order for three components
                        for i in range(0,3):
                            so, index = getFromEntry(subTree, index+1)
                            strokeOrder.append(so)
                else:
                    # no IDS operator but character
                    char, charZVariant, componentTree = subTree[index]
                    # if the character is unknown or there is none raise
                    if char == u'？':
                        raise exception.NoInformationError(
                            "Character has no stroke order information")
                    else:
                        # check if we have a stroke order entry first
                        so = getStrokeOrderEntry(char, charZVariant)
                        if not so:
                            # no entry, so get from partition
                            so = getFromDecomposition(componentTree)
                        strokeOrder.append(so)
                return (' '.join(strokeOrder), index)

            # Try to find a partition without unknown components, if more than
            # one partition is given (take the one with maximum entry length).
            # This ensures we will have a full stroke order if at least one
            # partition is complete. This is important as the database will
            # never be complete.
            strokeOrder = ''
            for decomposition in decompositionTreeList:
                try:
                    so, i = getFromEntry(decomposition)
                    if len(so) >= len(strokeOrder):
                        strokeOrder = so
                except exception.NoInformationError:
                    pass
            if not strokeOrder:
                raise exception.NoInformationError(
                    "Character has no stroke order information")
            return strokeOrder

        if locale != None:
            zVariant = self.getLocaleDefaultZVariant(char, locale)
        # if there is an entry for the whole character return it
        try:
            strokeOrder = getStrokeOrderEntry(char, zVariant)
            return strokeOrder
        except exception.NoInformationError:
            pass
        # try to decompose character into components and build stroke order
        decompositionTreeList = self.getDecompositionTreeList(char,
            zVariant=zVariant)
        strokeOrder = getFromDecomposition(decompositionTreeList)
        return strokeOrder

    #}
    #{ Character radical functions

    def getCharacterKangxiRadicalIndex(self, char):
        """
        Gets the Kangxi radical index for the given character as defined by the
        I{Unihan} database.

        @type char: str
        @param char: Chinese character
        @rtype: int
        @return: Kangxi radical index
        @raise NoInformationError: if no Kangxi radical index information for
            given character
        """
        result = self.db.selectSingleEntrySoleValue('CharacterKangxiRadical',
            'RadicalIndex', {'ChineseCharacter': char})
        if not result:
            raise exception.NoInformationError(
                "Character has no Kangxi radical information")
        return result

    def getCharacterKangxiRadicalResidualStrokeCount(self, char, locale=None,
        zVariant=0):
        u"""
        Gets the Kangxi radical form (either a I{Unicode radical form} or a
        I{Unicode radical variant}) found as a component in the character and
        the stroke count of the residual character components.

        The representation of the included radical or radical variant form
        depends on the respective character variant and thus the form's
        Z-variant is returned. Some characters include the given radical more
        than once and in some cases the representation is different between
        those same forms thus in the general case several matches can be
        returned each entry with a different radical form Z-variant. In these
        cases the entries are sorted by their Z-variant.

        There are characters which include both, the radical form and a variant
        form of the radical (e.g. 伦: 人 and 亻). In these cases both are
        returned.

        This method will return radical forms regardless of the selected locale,
        e.g. radical ⻔ is returned for character 间, though this variant form is
        not recognised under a traditional locale (like the character itself).

        @type char: str
        @param char: Chinese character
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: list of tuple
        @return: list of radical/variant form, its Z-variant, the main layout of
            the character (using a I{IDS operator}), the position of the radical
            wrt. layout (0, 1 or 2) and the residual stroke count.
        @raise NoInformationError: if no stroke count information available
        @raise ValueError: if an invalid I{character locale} is specified
        """
        radicalIndex = self.getCharacterKangxiRadicalIndex(char)
        entries = self.getCharacterRadicalResidualStrokeCount(char,
            radicalIndex, locale, zVariant)
        if entries:
            return entries
        else:
            raise exception.NoInformationError(
                "Character has no radical form information")

    def getCharacterRadicalResidualStrokeCount(self, char, radicalIndex,
        locale=None, zVariant=0):
        u"""
        Gets the radical form (either a I{Unicode radical form} or a
        I{Unicode radical variant}) found as a component in the character and
        the stroke count of the residual character components.

        This is a more general version of
        L{getCharacterKangxiRadicalResidualStrokeCount()} which is not limited
        to the mapping of characters to a Kangxi radical as done by Unihan.

        @type char: str
        @param char: Chinese character
        @type radicalIndex: int
        @param radicalIndex: radical index
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: list of tuple
        @return: list of radical/variant form, its Z-variant, the main layout of
            the character (using a I{IDS operator}), the position of the radical
            wrt. layout (0, 1 or 2) and the residual stroke count.
        @raise NoInformationError: if no stroke count information available
        @raise ValueError: if an invalid I{character locale} is specified
        @todo Lang: Clarify on characters classified under a given radical
            but without any proper radical glyph found as component.
        @todo Lang: Clarify on different radical zVariants for the same radical
            form. At best this method should return one and only one radical
            form (glyph).
        @todo Impl: Give the I{Unicode radical form} and not the equivalent
            character form in the relevant table as to always return the pure
            radical form (also avoids duplicates). Then state:

            If the included component has an appropriate I{Unicode radical form}
            or I{Unicode radical variant}, then this form is returned. In either
            case the radical form can be an ordinary character.
        """
        if locale != None:
            zVariant = self.getLocaleDefaultZVariant(char, locale)
        entries = self.db.select('CharacterRadicalResidualStrokeCount',
            ['RadicalForm', 'RadicalZVariant', 'MainCharacterLayout',
            'RadicalRelativePosition', 'ResidualStrokeCount'],
            {'ChineseCharacter': char, 'ZVariant': zVariant,
            'RadicalIndex': radicalIndex}, orderBy = ['ResidualStrokeCount',
            'RadicalZVariant', 'RadicalForm', 'MainCharacterLayout',
            'RadicalRelativePosition'])
        # add key columns to sort order to make return value deterministic
        if entries:
            return entries
        else:
            raise exception.NoInformationError(
                "Character has no radical form information")

    def getCharacterRadicalResidualStrokeCountDict(self):
        """
        Gets the full table of radical forms (either a I{Unicode radical form}
        or a I{Unicode radical variant}) found as a component in the character
        and the stroke count of the residual character components from the
        database.

        A typical entry looks like
        C{(u'众', 0): {9: [(u'人', 0, u'⿱', 0, 4), (u'人', 0, u'⿻', 0, 4)]}},
        and can be accessed as C{radicalDict[(u'众', 0)][9]} with the Chinese
        character, its Z-variant and Kangxi radical index. The values are given
        in the order I{radical form}, I{radical Z-variant}, I{character layout},
        I{relative position of the radical} and finally the
        I{residual stroke count}.

        @rtype: dict
        @return: dictionary of radical/residual stroke count entries.
        """
        radicalDict = {}
        # get entries from database
        for entry in self.db.select('CharacterRadicalResidualStrokeCount',
            ['ChineseCharacter', 'ZVariant', 'RadicalIndex', 'RadicalForm',
            'RadicalZVariant', 'MainCharacterLayout', 'RadicalRelativePosition',
            'ResidualStrokeCount'],
            orderBy = ['ResidualStrokeCount', 'RadicalZVariant', 'RadicalForm',
            'MainCharacterLayout', 'RadicalRelativePosition']):

            char, zVariant, radicalIndex, radicalForm, radicalZVariant, \
                mainCharacterLayout, radicalReladtivePosition, \
                residualStrokeCount = entry

            if (char, zVariant) not in radicalDict:
                radicalDict[(char, zVariant)] = {}

            if radicalIndex  not in radicalDict[(char, zVariant)]:
                radicalDict[(char, zVariant)][radicalIndex] = []

            radicalDict[(char, zVariant)][radicalIndex].append(
                (radicalForm, radicalZVariant, mainCharacterLayout, \
                    radicalReladtivePosition, residualStrokeCount))

        return radicalDict

    def getCharacterKangxiResidualStrokeCount(self, char, locale=None,
        zVariant=0):
        u"""
        Gets the stroke count of the residual character components when leaving
        aside the radical form.

        This method returns a subset of data with regards to
        L{getCharacterKangxiRadicalResidualStrokeCount()}. It may though offer
        more entries after all, as their might exists information only about
        the residual stroke count, but not about the concrete radical form.

        @type char: str
        @param char: Chinese character
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: int
        @return: residual stroke count
        @raise NoInformationError: if no stroke count information available
        @raise ValueError: if an invalid I{character locale} is specified
        @attention: The quality of the returned data depends on the sources used
            when compiling the database. Unihan itself only gives very general
            stroke order information without being bound to a specific glyph.
        """
        radicalIndex = self.getCharacterKangxiRadicalIndex(char)
        return self.getCharacterResidualStrokeCount(char, radicalIndex,
            locale, zVariant)

    def getCharacterResidualStrokeCount(self, char, radicalIndex, locale=None,
        zVariant=0):
        u"""
        Gets the stroke count of the residual character components when leaving
        aside the radical form.

        This is a more general version of
        L{getCharacterKangxiResidualStrokeCount()} which is not limited to the
        mapping of characters to a Kangxi radical as done by Unihan.

        @type char: str
        @param char: Chinese character
        @type radicalIndex: int
        @param radicalIndex: radical index
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: int
        @return: residual stroke count
        @raise NoInformationError: if no stroke count information available
        @raise ValueError: if an invalid I{character locale} is specified
        @attention: The quality of the returned data depends on the sources used
            when compiling the database. Unihan itself only gives very general
            stroke order information without being bound to a specific glyph.
        """
        if locale != None:
            zVariant = self.getLocaleDefaultZVariant(char, locale)
        entry = self.db.selectSingleEntrySoleValue(
            'CharacterResidualStrokeCount', 'ResidualStrokeCount',
            {'ChineseCharacter': char, 'ZVariant': zVariant,
            'RadicalIndex': radicalIndex})
        if entry != None:
            return entry
        else:
            raise exception.NoInformationError(
                "Character has no residual stroke count information")

    def getCharacterResidualStrokeCountDict(self):
        """
        Gets the full table of stroke counts of the residual character
        components from the database.

        A typical entry looks like C{(u'众', 0): {9: [4]}},
        and can be accessed as C{residualCountDict[(u'众', 0)][9]} with the
        Chinese character, its Z-variant and Kangxi radical index which then
        gives the I{residual stroke count}.

        @rtype: dict
        @return: dictionary of radical/residual stroke count entries.
        """
        residualCountDict = {}
        # get entries from database
        for entry in self.db.select('CharacterResidualStrokeCount',
            ['ChineseCharacter', 'ZVariant', 'RadicalIndex',
            'ResidualStrokeCount']):

            char, zVariant, radicalIndex, residualStrokeCount = entry

            if (char, zVariant) not in residualCountDict:
                residualCountDict[(char, zVariant)] = {}

            residualCountDict[(char, zVariant)][radicalIndex] \
                = residualStrokeCount

        return residualCountDict

    def getCharactersForKangxiRadicalIndex(self, radicalIndex):
        """
        Gets all characters for the given Kangxi radical index.

        @type radicalIndex: int
        @param radicalIndex: Kangxi radical index
        @rtype: list of str
        @return: list of matching Chinese characters
        @todo Docu: Write about how Unihan maps characters to a Kangxi radical.
            Especially Chinese simplified characters.
        """
        return self.db.selectSoleValue('CharacterKangxiRadical',
            'ChineseCharacter', {'RadicalIndex': radicalIndex})

    def getCharactersForRadicalIndex(self, radicalIndex):
        """
        Gets all characters for the given radical index.

        This is a more general version of
        L{getCharactersForKangxiRadicalIndex()} which is not limited to the
        mapping of characters to a Kangxi radical as done by Unihan and one
        character can show up under several different radical indices.

        @type radicalIndex: int
        @param radicalIndex: Kangxi radical index
        @rtype: list of str
        @return: list of matching Chinese characters
        """
        return self.db.selectSoleValue('CharacterResidualStrokeCount',
            'ChineseCharacter', {'RadicalIndex': radicalIndex})

    def getResidualStrokeCountForKangxiRadicalIndex(self, radicalIndex):
        """
        Gets all characters and residual stroke count for the given Kangxi
        radical index.

        This brings together methods L{getCharactersForKangxiRadicalIndex()} and
        L{getCharacterResidualStrokeCountDict()} and reports all characters
        including the given Kangxi radical, additionally supplying the residual
        stroke count.

        @type radicalIndex: int
        @param radicalIndex: Kangxi radical index
        @rtype: list of tuple
        @return: list of matching Chinese characters with residual stroke count
        """
        tables = ['KangxiRadical r', 'RadicalEquivalentCharacter e']
        return self.db.select(
            ['CharacterKangxiRadical k', 'CharacterResidualStrokeCount r'],
            ['r.ChineseCharacter', 'r.ResidualStrokeCount'],
            {'r.ChineseCharacter': '=k.ChineseCharacter',
            'r.RadicalIndex': '=k.RadicalIndex',
            'k.RadicalIndex': radicalIndex})

    def getResidualStrokeCountForRadicalIndex(self, radicalIndex):
        """
        Gets all characters and residual stroke count for the given radical
        index.

        This brings together methods L{getCharactersForRadicalIndex()} and
        L{getCharacterResidualStrokeCountDict()} and reports all characters
        including the given radical without being limited to the mapping of
        characters to a Kangxi radical as done by Unihan, additionally supplying
        the residual stroke count.

        @type radicalIndex: int
        @param radicalIndex: Kangxi radical index
        @rtype: list of tuple
        @return: list of matching Chinese characters with residual stroke count
        """
        return self.db.select('CharacterResidualStrokeCount',
            ['ChineseCharacter', 'ResidualStrokeCount'],
            {'RadicalIndex': radicalIndex})

    #}
    #{ Radical form functions

    def getKangxiRadicalForm(self, radicalIdx, locale):
        u"""
        Gets a I{Unicode radical form} for the given Kangxi radical index.

        This method will always return a single non null value, even if there
        are several radical forms for one index.

        @type radicalIdx: int
        @param radicalIdx: Kangxi radical index
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: str
        @return: I{Unicode radical form}
        @raise ValueError: if an invalid I{character locale} or radical index is
            specified
        @todo Lang: Check if radicals for which multiple radical forms exists
            include a simplified form or other variation (e.g. ⻆, ⻝, ⺐).
            There are radicals for which a Chinese simplified character
            equivalent exists and that is mapped to a different radical under
            Unicode.
        """
        if radicalIdx < 1 or radicalIdx > 214:
            raise ValueError("Radical index '" + unicode(radicalIdx) \
                + "' not in range between 1 and 214")
        radicalForms = self.db.selectSoleValue('KangxiRadical', 'Form',
            {'RadicalIndex': radicalIdx, 'Type': 'R',
            'Locale': self._locale(locale)}, orderBy = ['SubIndex'])
        return radicalForms[0]

    def getKangxiRadicalVariantForms(self, radicalIdx, locale):
        """
        Gets a list of I{Unicode radical variant}s for the given Kangxi radical
        index.

        This method can return an empty list if there are no
        I{Unicode radical variant} forms. There might be non
        I{Unicode radical variant}s for this radial as character forms though.

        @type radicalIdx: int
        @param radicalIdx: Kangxi radical index
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: list of str
        @return: list of I{Unicode radical variant}s
        @raise ValueError: if an invalid I{character locale} is specified
        @todo Lang: Narrow locales, not all variant forms are valid under all
            locales.
        """
        return self.db.selectSoleValue('KangxiRadical', 'Form',
            {'RadicalIndex': radicalIdx, 'Type': 'V',
             'Locale': self._locale(locale)},
            orderBy = ['SubIndex'])

    def getKangxiRadicalIndex(self, radicalForm, locale=None):
        """
        Gets the Kangxi radical index for the given form.

        The given form might either be an I{Unicode radical form} or an
        I{equivalent character}.

        If there is an entry for the given radical form it still might not be a
        radical under the given character locale. So specifying a locale allows
        strict radical handling.

        @type radicalForm: str
        @param radicalForm: radical form
        @type locale: str
        @param locale: optional I{character locale} (one out of TCJKV)
        @rtype: int
        @return: Kangxi radical index
        @raise ValueError: if invalid I{character locale} or radical form is
            specified
        """
        # check in radical table
        if locale:
            locale = self._locale(locale)
        else:
            locale = '%'
        result = self.db.selectSingleEntrySoleValue('KangxiRadical',
                'RadicalIndex', {'Form': radicalForm,
                'Locale': locale})
        if result:
            return result
        else:
            # check in radical equivalent character table, join tables
            tables = ['KangxiRadical r', 'RadicalEquivalentCharacter e']
            result = self.db.selectSoleValue(tables, 'r.RadicalIndex',
                {'e.EquivalentForm': radicalForm, 'e.Locale': locale,
                'r.Locale': locale, 'r.Form': '=e.Form'})
            if result:
                return result[0]
            else:
                # check in isolated radical equivalent character table
                result = self.db.selectSingleEntrySoleValue(
                    'KangxiRadicalIsolatedCharacter',
                    'RadicalIndex', {'EquivalentForm': radicalForm,
                    'Locale': locale})
                if result:
                    return result
        raise ValueError(radicalForm +  "is no valid Kangxi radical," \
            + " variant form or equivalent character")

    def getKangxiRadicalRepresentativeCharacters(self, radicalIdx, locale):
        u"""
        Gets a list of characters that represent the radical for the given
        Kangxi radical index.

        This includes the radical form(s), character equivalents
        and variant forms and equivalents.

        E.g. character for I{to speak/to say/talk/word} (Pinyin I{yán}):
        ⾔ (0x2f94), 言 (0x8a00), ⻈ (0x2ec8), 讠 (0x8ba0), 訁 (0x8a01)

        @type radicalIdx: int
        @param radicalIdx: Kangxi radical index
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: list of str
        @return: list of Chinese characters representing the radical for the
            given index, including Unicode radical and variant forms and their
            equivalent real character forms
        @raise ValueError: if invalid I{character locale} specified
        """
        # get radical/variant forms
        representativeChars = []
        representativeChars.extend(self.db.selectSoleValue('KangxiRadical',
            'Form', {'RadicalIndex': radicalIdx,
            'Locale': self._locale(locale)}))
        # get equivalent characters, join tables
        tables = ['KangxiRadical r', 'RadicalEquivalentCharacter e']
        representativeChars.extend(self.db.selectSoleValue(tables,
            'e.EquivalentForm', {'r.RadicalIndex': radicalIdx,
            'r.Locale': self._locale(locale), 'e.Locale': self._locale(locale),
            'r.Form': '=e.Form'},
            distinctValues=True))
        # get isolated characters (normal characters that represent a radical)
        representativeChars.extend(self.db.selectSoleValue(
            'KangxiRadicalIsolatedCharacter', 'EquivalentForm',
            {'RadicalIndex': radicalIdx, 'Locale': self._locale(locale)}))
        return representativeChars

    def isKangxiRadicalFormOrEquivalent(self, form, locale=None):
        """
        Checks if the given form is a Kangxi radical form or a radical
        equivalent. This includes I{Unicode radical form}s,
        I{Unicode radical variant}s, I{equivalent character} and
        I{isolated radical character}s.

        If there is an entry for the given radical form it still might not be a
        radical under the given character locale. So specifying a locale allows
        strict radical handling.

        @type form: str
        @param form: Chinese character
        @type locale: str
        @param locale: optional I{character locale} (one out of TCJKV)
        @rtype: bool
        @return: C{True} if given form is a radical or I{equivalent character},
            C{False} otherwise
        @raise ValueError: if an invalid I{character locale} is specified
        """
        try:
            self.getKangxiRadicalIndex(form, locale)
            return True
        except ValueError:
            return False

    def isRadicalChar(self, char):
        """
        Checks if the given character is a I{Unicode radical form} or
        I{Unicode radical variant}.

        This method does a quick Unicode code index checking. So there is no
        guarantee this form has actually a radical entry in the database.

        @type char: str
        @param char: Chinese character
        @rtype: bool
        @return: C{True} if given form is a radical form, C{False} otherwise
        """
        # check if Unicode code point of character lies in between U+2e80 and
        # U+2fd5
        return char >= u'⺀' and char <= u'⿕'

    def getRadicalFormEquivalentCharacter(self, radicalForm, locale):
        u"""
        Gets the I{equivalent character} of the given I{Unicode radical form} or
        I{Unicode radical variant}.

        The mapping mostly follows the X{Han Radical folding} specified in
        the Draft X{Unicode Technical Report #30} X{Character Foldings} under
        U{http://www.unicode.org/unicode/reports/tr30/#HanRadicalFolding}.
        All radical forms except U+2E80 (⺀) have an equivalent character. These
        equivalent characters are not necessarily visual identical and can be
        subject to major variation.

        This method may raise a UnsupportedError if there is no supported
        I{equivalent character} form.

        @type radicalForm: str
        @param radicalForm: I{Unicode radical form}
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: str
        @return: I{equivalent character} form
        @raise UnsupportedError: if there is no supported
            I{equivalent character} form
        @raise ValueError: if invalid I{character locale} or radical form is
            specified
        """
        if not self.isRadicalChar(radicalForm):
            raise ValueError(radicalForm + " is no valid radical form")

        equivChar = self.db.selectSingleEntrySoleValue(
            'RadicalEquivalentCharacter', 'EquivalentForm',
            {'Form': radicalForm, 'Locale': self._locale(locale)})
        if equivChar:
            return equivChar
        else:
            raise exception.UnsupportedError(
                "no equivalent character supported for '" + radicalForm + "'")

    def getCharacterEquivalentRadicalForms(self, equivalentForm, locale):
        """
        Gets I{Unicode radical form}s or I{Unicode radical variant}s for the
        given I{equivalent character}.

        The mapping mostly follows the I{Han Radical folding} specified in
        the Draft I{Unicode Technical Report #30} I{Character Foldings} under
        U{http://www.unicode.org/unicode/reports/tr30/#HanRadicalFolding}.
        Several radical forms can be mapped to the same equivalent character
        and thus this method in general returns several values.

        @type equivalentForm: str
        @param equivalentForm: Equivalent character of I{Unicode radical form}
            or I{Unicode radical variant}
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: list of str
        @return: I{equivalent character} forms
        @raise ValueError: if invalid I{character locale} or equivalent
            character is specified
        """
        result = self.db.selectSoleValue('RadicalEquivalentCharacter', 'Form',
            {'EquivalentForm': equivalentForm, 'Locale': self._locale(locale)})
        if result:
            return result
        else:
            raise ValueError(equivalentForm \
                + " is no valid equivalent character under the given locale")

    #}
    #{ Character component functions

    IDS_BINARY = [u'⿰', u'⿱', u'⿴', u'⿵', u'⿶', u'⿷', u'⿸', u'⿹', u'⿺',
        u'⿻']
    """
    A list of I{binary IDS operator}s used to describe character decompositions.
    """
    IDS_TRINARY = [u'⿲', u'⿳']
    """
    A list of I{trinary IDS operator}s used to describe character
    decompositions.
    """

    @classmethod
    def isBinaryIDSOperator(cls, char):
        """
        Checks if given character is a I{binary IDS operator}.

        @type char: str
        @param char: Chinese character
        @rtype: bool
        @return: C{True} if I{binary IDS operator}, C{False} otherwise
        """
        return char in set(cls.IDS_BINARY)

    @classmethod
    def isTrinaryIDSOperator(cls, char):
        """
        Checks if given character is a I{trinary IDS operator}.

        @type char: str
        @param char: Chinese character
        @rtype: bool
        @return: C{True} if I{trinary IDS operator}, C{False} otherwise
        """
        return char in set(cls.IDS_TRINARY)

    @classmethod
    def isIDSOperator(cls, char):
        """
        Checks if given character is an I{IDS operator}.

        @type char: str
        @param char: Chinese character
        @rtype: bool
        @return: C{True} if I{IDS operator}, C{False} otherwise
        """
        return cls.isBinaryIDSOperator(char) or cls.isTrinaryIDSOperator(char)

    def getCharactersForComponents(self, componentList, locale,
        includeEquivalentRadicalForms=True, resultIncludeRadicalForms=False):
        u"""
        Gets all characters that contain the given components.

        If option C{includeEquivalentRadicalForms} is set, all equivalent forms
        will be search for when a Kangxi radical is given.

        @type componentList: list of str
        @param componentList: list of character components
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @type includeEquivalentRadicalForms: bool
        @param includeEquivalentRadicalForms: if C{True} then characters in the
            given component list are interpreted as representatives for their
            radical and all radical forms are included in the search. E.g. 肉
            will include ⺼ as a possible component.
        @type resultIncludeRadicalForms: bool
        @param resultIncludeRadicalForms: if C{True} the result will include
            I{Unicode radical forms} and I{Unicode radical variants}
        @rtype: list of tuple
        @return: list of pairs of matching characters and their Z-variants
        @raise ValueError: if an invalid I{character locale} is specified
        @todo Impl: Table of same character glyphs, including special radical
            forms (e.g. 言 and 訁).
        @todo Data: Adopt locale dependant Z-variants for parent characters
            (e.g. 鬼 in 隗 愧 嵬).
        @todo Data: Use radical forms and radical variant forms instead of
            equivalent characters in decomposition data. Mapping looses
            information.
        @todo Lang: By default we get the equivalent character for a radical
            form. In some cases these equivalent characters will be only
            abstractly related to the given radical form (e.g. being the main
            radical form), so that the result set will be too big and doesn't
            reflect the original query. Set up a table including only strict
            visual relations between radical forms and equivalent characters.
            Alternatively restrict decomposition data to only include radical
            forms if appropriate, so there would be no need for conversion.
        """
        equivCharTable = []
        for component in componentList:
            try:
                # check if component is a radical and get index
                radicalIdx = self.getKangxiRadicalIndex(component, locale)

                componentEquivalents = [component]
                if includeEquivalentRadicalForms:
                    # if includeRadicalVariants is set get all forms
                    componentEquivalents = \
                        self.getKangxiRadicalRepresentativeCharacters(
                            radicalIdx, locale)
                else:
                    if self.isRadicalChar(component):
                        try:
                            componentEquivalents.append(
                                self.getRadicalFormEquivalentCharacter(
                                    component, locale))
                        except exception.UnsupportedError:
                            # pass if no equivalent char existent
                            pass
                    else:
                        componentEquivalents.extend(
                            self.getCharacterEquivalentRadicalForms(component,
                                locale))
                equivCharTable.append(componentEquivalents)
            except ValueError:
                equivCharTable.append([component])

        return self.getCharactersForEquivalentComponents(equivCharTable, locale,
            resultIncludeRadicalForms=resultIncludeRadicalForms)

    def getCharactersForEquivalentComponents(self, componentConstruct,
        locale=None, resultIncludeRadicalForms=False):
        u"""
        Gets all characters that contain at least one component per list entry,
        sorted by stroke count if available.

        This is the general form of L{getCharactersForComponents()} and allows a
        set of characters per list entry of which at least one character must be
        a component in the given list.

        If a I{character locale} is specified only characters will be returned
        for which the locale's default I{Z-variant}'s decomposition will apply
        to the given components. Otherwise all Z-variants will be considered.

        @type componentConstruct: list of list of str
        @param componentConstruct: list of character components given as single
            characters or, for alternative characters, given as a list
        @type resultIncludeRadicalForms: bool
        @param resultIncludeRadicalForms: if C{True} the result will include
            I{Unicode radical forms} and I{Unicode radical variants}
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV)
        @rtype: list of tuple
        @return: list of pairs of matching characters and their Z-variants
        @raise ValueError: if an invalid I{character locale} is specified
        """
        # create where clauses
        tableList = ['ComponentLookup s' + str(i)
            for i in range(1, len(componentConstruct))]

        if locale:
            # join with LocaleCharacterVariant and allow only forms matching the
            #   given locale, unless no locale entry exists
            if self.hasStrokeCount:
                tableList.append('ComponentLookup s0 LEFT JOIN StrokeCount c ' \
                    + 'ON (s0.ChineseCharacter = c.ChineseCharacter) ' \
                    + 'LEFT JOIN LocaleCharacterVariant l ON ' \
                    + '(s0.ChineseCharacter = l.ChineseCharacter AND ' \
                    + 's0.ZVariant = l.ZVariant) ' \
                    + 'LEFT JOIN LocaleCharacterVariant l2 ON ' \
                    + '(s0.ChineseCharacter = l2.ChineseCharacter)')
                orderBy = ['c.StrokeCount']
            else:
                tableList.append('ComponentLookup s0 LEFT JOIN ' \
                    + 'LocaleCharacterVariant l ON ' \
                    + '(s0.ChineseCharacter = l.ChineseCharacter AND '\
                    + 's0.ZVariant = l.ZVariant) ' \
                    + 'LEFT JOIN LocaleCharacterVariant l2 ON ' \
                    + '(s0.ChineseCharacter = l2.ChineseCharacter)')
                orderBy = []
            # TODO locale clauses look like: "a OR (b AND C)". The database
            #   abstraction layer only works with normal forms and thus we need
            #   to work around extensively. Furthermore a UNION is needed for
            #   SQLite as with an alternative realisation as OR it slows down
            #   tremendously
            localeClauses = [{'l.Locale': self._locale(locale)},
                {'l2.Locale': 'IS NULL', 'l.Locale': 'IS NULL'}]
        else:
            if self.hasStrokeCount:
                tableList.append('ComponentLookup s0 LEFT JOIN StrokeCount c ' \
                    + 'ON (s0.ChineseCharacter = c.ChineseCharacter)')
                orderBy = ['c.StrokeCount']
            else:
                tableList.append('ComponentLookup s0')
                orderBy = []

        whereClauses = {}

        for i, characterList in enumerate(componentConstruct):
            whereClauses['s'+str(i)+'.Component'] = characterList
            if i > 0:
                whereClauses['s' + str(i-1) + '.ZVariant'] = '= s' \
                    + str(i) + '.ZVariant'
                whereClauses['s' + str(i-1) + '.ChineseCharacter'] = '= s' \
                    + str(i) + '.ChineseCharacter'

        if locale:
            selectCommands = []
            for localeClause in localeClauses[:-1]:
                localeClause.update(whereClauses)
                selectCommands.append(self.db.getSelectCommand(tableList,
                    ['s0.ChineseCharacter', 's0.ZVariant', 'StrokeCount'],
                    localeClause, distinctValues=True))

            localeClauses[-1].update(whereClauses)
            selectCommands.append(self.db.getSelectCommand(tableList,
                ['s0.ChineseCharacter', 's0.ZVariant', 'StrokeCount'],
                localeClauses[-1], orderBy=['StrokeCount'],
                distinctValues=True))

            cur = DatabaseConnector.getDBConnector().getCursor()
            cur.execute(' UNION '.join(selectCommands))
            result = list(cur.fetchall())
            for i, entry in enumerate(result): # TODO bug in python-mysql
                entry = list(entry)
                for j, cell in enumerate(entry):
                    if type(cell) == type(""):
                        entry[j] = cell.decode('utf8')
                result[i] = tuple(entry)

            result = [(char, zVariant) for char, zVariant, _ in result]
        else:
            result = self.db.select(tableList,
                ['s0.ChineseCharacter', 's0.ZVariant'], whereClauses,
                orderBy=orderBy, distinctValues=True)

        if not resultIncludeRadicalForms:
            # exclude radical characters found in decomposition
            result = [(char, zVariant) for char, zVariant in result \
                if not self.isRadicalChar(char)]

        return result

    def getDecompositionEntries(self, char, locale=None, zVariant=0):
        """
        Gets the decomposition of the given character into components from the
        database. The resulting decomposition is only the first layer in a tree
        of possible paths along the decomposition as the components can be
        further subdivided.

        There can be several decompositions for one character so a list of
        decomposition is returned.

        Each entry in the result list consists of a list of characters (with its
        Z-variant) and IDS operators.

        @type char: str
        @param char: Chinese character that is to be decomposed into components
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: list
        @return: list of first layer decompositions
        @raise ValueError: if an invalid I{character locale} is specified
        """
        if locale != None:
            try:
                zVariant = self.getLocaleDefaultZVariant(char, locale)
            except exception.NoInformationError:
                # no decomposition available
                return []

        # get entries from database
        result = self.db.selectSoleValue('CharacterDecomposition',
            'Decomposition', {'ChineseCharacter': char, 'ZVariant': zVariant},
            orderBy = ['SubIndex'])

        # extract character Z-variant information (example entry: '⿱卜[1]尸')
        return [self._getDecompositionFromString(decomposition) \
            for decomposition in result]

    def getDecompositionEntriesDict(self):
        """
        Gets the full decomposition table from the database.

        @rtype: dict
        @return: dictionary with key pair character, Z-variant and the first
            layer decomposition as value
        """
        decompDict = {}
        # get entries from database
        for char, zVariant, decomposition in self.db.select(
            'CharacterDecomposition',
            ['ChineseCharacter', 'ZVariant', 'Decomposition'],
            orderBy = ['SubIndex']):

            if (char, zVariant) not in decompDict:
                decompDict[(char, zVariant)] = []

            decompDict[(char, zVariant)].append(
                self._getDecompositionFromString(decomposition))

        return decompDict

    def _getDecompositionFromString(self, decomposition):
        """
        Gets a tuple representation with character/Z-variant of the given
        character's decomposition into components.

        Example: Entry C{⿱尚[1]儿} will be returned as
        C{[u'⿱', (u'尚', 1), (u'儿', 0)]}.

        @type decomposition: str
        @param decomposition: character decomposition with IDS operator,
            compontens and optional Z-variant index
        @rtype: list
        @return: decomposition with character/Z-variant tuples
        """
        componentsList = []
        index = 0
        while index < len(decomposition):
            char = decomposition[index]
            if self.isIDSOperator(char):
                componentsList.append(char)
            else:
                # is Chinese character
                if index+1 < len(decomposition)\
                    and decomposition[index+1] == '[':

                    endIndex = decomposition.index(']', index+1)
                    # extract Z-variant information
                    charZVariant = int(decomposition[index+2:endIndex])
                    index = endIndex
                else:
                    # take default Z-variant if none specified
                    charZVariant = 0
                componentsList.append((char, charZVariant))
            index = index + 1
        return componentsList

    def getDecompositionTreeList(self, char, locale=None, zVariant=0):
        """
        Gets the decomposition of the given character into components as a list
        of decomposition trees.

        There can be several decompositions for one character so one tree per
        decomposition is returned.

        Each entry in the result list consists of a list of characters (with its
        Z-variant and list of further decomposition) and IDS operators. If a
        character can be further subdivided, its containing list is non empty
        and includes yet another list of trees for the decomposition of the
        component.

        @type char: str
        @param char: Chinese character that is to be decomposed into components
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @rtype: list
        @return: list of decomposition trees
        @raise ValueError: if an invalid I{character locale} is specified
        """
        if locale != None:
            try:
                zVariant = self.getLocaleDefaultZVariant(char, locale)
            except exception.NoInformationError:
                # no decomposition available
                return []

        decompositionTreeList = []
        # get tree for each decomposition
        for componentsList in self.getDecompositionEntries(char,
            zVariant=zVariant):
            decompositionTree = []
            for component in componentsList:
                if type(component) != type(()):
                    # IDS operator
                    decompositionTree.append(component)
                else:
                    # Chinese character with zVariant info
                    character, characterZVariant = component
                    # get partition of component recursively
                    componentTree = self.getDecompositionTreeList(character,
                        zVariant=characterZVariant)
                    decompositionTree.append((character, characterZVariant,
                        componentTree))
            decompositionTreeList.append(decompositionTree)
        return decompositionTreeList

    def isComponentInCharacter(self, component, char, locale=None, zVariant=0,
        componentZVariant=None):
        """
        Checks if the given character contains the second character as a
        component.

        @type component: str
        @param component: character questioned to be a component
        @type char: str
        @param char: Chinese character
        @type locale: str
        @param locale: I{character locale} (one out of TCJKV). Giving the locale
            will apply the default I{Z-variant} defined by
            L{getLocaleDefaultZVariant()}. The Z-variant supplied with option
            C{zVariant} will be ignored.
        @type zVariant: int
        @param zVariant: I{Z-variant} of the first character
        @type componentZVariant: int
        @param componentZVariant: Z-variant of the component; if left out every
            Z-variant matches for that character.
        @rtype: bool
        @return: C{True} if C{component} is a component of the given character,
            C{False} otherwise
        @raise ValueError: if an invalid I{character locale} is specified
        @todo Impl: Implement means to check if the component is really not
            found, or if our data is just insufficient.
        """
        if locale != None:
            try:
                zVariant = self.getLocaleDefaultZVariant(char, locale)
            except exception.NoInformationError:
                # TODO no way to check if our data is insufficent
                return False

        # if table exists use it to speed up look up
        if self.hasComponentLookup:
            zVariants = self.db.selectSoleValue('ComponentLookup',
                'ComponentZVariant', {'ChineseCharacter': char,
                    'ZVariant': zVariant, 'Component': component})
            return zVariants and (componentZVariant == None \
                or componentZVariant in zVariants)
        else:
            # use slow way with going through the decomposition tree
            # get decomposition for the first character from table
            for componentsList in self.getDecompositionEntries(char,
                zVariant=zVariant):
                # got through decomposition and check for components
                for charComponent in componentsList:
                    if type(charComponent) == type(()):
                        character, characterZVariant = charComponent
                        if character != u'？':
                            # check if character and Z-variant match
                            if character == component \
                                and (componentZVariant == None or
                                    characterZVariant == componentZVariant):
                                return True
                            # else recursively step into decomposition of
                            #   current component
                            if self.isComponentInCharacter(character, component,
                                zVariant=characterZVariant,
                                componentZVariant=componentZVariant):
                                return True
            return False
