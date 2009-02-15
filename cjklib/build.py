#!/usr/bin/python
# -*- coding: utf-8  -*-
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
Provides the building methods for the cjklib package.

Each table that needs to be created has to be implemented by a L{TableBuilder}.
The L{DatabaseBuilder} is the central instance for managing the build process.
As the creation of a table can depend on other tables the DatabaseBuilder keeps
track of dependencies to process a build in the correct order.

Building is supported (i.e. tested) for the following storage methods:
    - SQL dump to stdout (only for tables which don't depend on the presence of
        other tables)
    - SQLite
    - MySQL

Some L{TableBuilder} implementations aren't used by the CJK library but are
provided here for additional usage.

For MS Windows default versions provided seem to be a "X{narrow build}" and not
support characters outside the BMP (see e.g.
U{http://wordaligned.org/articles/narrow-python}). Currently no Unicode
characters outside the BMP will thus be supported on Windows platforms.

Examples
========
The following examples should give a quick view into how to use this
package.
    - Create the DatabaseBuilder object with default settings (read from
        cjklib.conf or using 'cjklib.db' in same directory as default):

        >>> from cjklib import build
        >>> dbBuilder = build.DatabaseBuilder(dataPath=['./cjklib/data/'])
        Removing conflicting builder(s) 'CharacterVariantBMPBuilder' in favour
        of 'CharacterVariantBuilder'
        Removing conflicting builder(s) 'SlimUnihanBuilder', 'UnihanBuilder',
        'UnihanBMPBuilder' in favour of 'SlimUnihanBMPBuilder'
        Removing conflicting builder(s) 'StrokeCountBuilder' in favour of
        'CombinedStrokeCountBuilder'
        Removing conflicting builder(s) 'CharacterResidualStrokeCountBuilder' in
        favour of 'CombinedCharacterResidualStrokeCountBuilder'

    - Build the table of Jyutping syllables from a csv file:

        >>> dbBuilder.build(['JyutpingSyllables'])
        building table 'JyutpingSyllables' with builder
        'JyutpingSyllablesBuilder'...
        Reading table definition from file './cjklib/data/jyutpingsyllables.sql'
        Reading table 'JyutpingSyllables' from file
        './cjklib/data/jyutpingsyllables.csv'

@todo Impl: Further character domains: BIG5 (Taiwan), kIRG_GSource (Unicode,
    Simplified Chinese), kIRG_JSource (Unicode, Japanese), kIRG_KPSource and
    kIRG_KSource (Unicode, Korean), kIRG_TSource (Unicode, Traditional Chinese),
    kIRG_VSource (Unicode, Vietnamese)
@todo Fix:  On interruption (Ctrl+C) remove tables that were only created
    because of dependencies.
"""

import types
import locale
import sys
import re
import warnings
import os.path
import xml.sax
import csv

from cjklib import dbconnector
from cjklib import characterlookup
from cjklib import exception

#{ TableBuilder and generic classes

class TableBuilder(object):
    """
    TableBuilder provides the abstract layout for classes that build a distinct
    table.
    """
    PROVIDES = ''
    """Contains the name of the table provided by this module."""
    DEPENDS = []
    """Contains the names of the tables needed for the build process."""

    def __init__(self, dataPath=None, dbConnectInst=None, quiet=False):
        """
        Constructs the TableBuilder.

        @type dataPath: list of str
        @param dataPath: optional list of paths to the data file(s)
        @type dbConnectInst: instance
        @param dbConnectInst: instance of a L{DatabaseConnector}. If not given
            all sql code will be printed to stdout.
        @type quiet: bool
        @param quiet: if true no status information will be printed to stderr
        """
        self.dataPath = dataPath
        self.quiet = quiet
        self.db = dbConnectInst
        if self.db:
            self.target = self.db.getDatabaseType()
            if self.target == 'MySQL':
                warnings.filterwarnings("ignore", "Unknown table.*")
        else:
            self.target = 'dump'

    def build(self):
        """
        Build the table provided by the TableBuilder.

        Methods should raise an IOError if reading a data source fails. The
        L{DatabaseBuilder} knows how to handle this case and is able to proceed.
        """
        pass


    def findFile(self, fileNames, fileType=None):
        """
        Tries to locate a file with a given list of possible file names under
        the classes default data paths.

        For each file name every given path is checked and the first match is
        returned.

        @type fileNames: str/list of str
        @param fileNames: possible file names
        @type fileType: str
        @param fileType: textual type of file used in error msg
        @rtype: str
        @return: path to file of first match in search for existing file
        @raise IOError: if no file found
        """
        if type(fileNames) != type([]):
            fileNames = [fileNames]
        for fileName in fileNames:
            for path in self.dataPath:
                filePath = os.path.join(os.path.expanduser(path), fileName)
                if os.path.exists(filePath):
                    return filePath
        if fileType == None:
            fileType = "file"
        raise IOError("No " + fileType + " found for '" + self.PROVIDES \
            + "' under path(s)'" + "', '".join(self.dataPath) \
            + "' for file names '" + "', '".join(fileNames) + "'")


class EntryGeneratorBuilder(TableBuilder):
    """
    Implements an abstract class for building a table from a generator
    providing entries.
    """
    COLUMNS = []
    """Columns that will be built"""
    PRIMARY_KEYS = []
    """Primary keys of the created table"""
    INDEX_KEYS = []
    """Index keys (not unique) of the created table"""
    COLUMN_TYPES = {}
    """Column types for created table"""
    ENTRY_GENERATOR = None
    """Generator of table entries"""

    def build(self):
        # get drop table statement
        dropStatement = getDropTableStatement(self.PROVIDES)
        # get create statement
        createStatement = getCreateTableStatement(self.PROVIDES, self.COLUMNS,
            self.COLUMN_TYPES, primaryKeyColumns=self.PRIMARY_KEYS)
        if self.target == 'dump':
            output(dropStatement)
            output(createStatement)
        else:
            self.db.getCursor().execute(dropStatement)
            self.db.getCursor().execute(createStatement)
            self.db.getCursor().execute('BEGIN;')

        # write table content
        for newEntry in self.ENTRY_GENERATOR:
            insertStatement = getInsertStatement(self.PROVIDES, newEntry)
            if self.target == 'dump':
                output(insertStatement)
            elif self.target == 'MySQL':
                import _mysql_exceptions
                try:
                    self.db.getCursor().execute(insertStatement)
                except _mysql_exceptions.IntegrityError:
                    warn(insertStatement)
                    raise
            elif self.target == 'SQLite':
                import pysqlite2.dbapi2
                try:
                    self.db.getCursor().execute(insertStatement)
                except pysqlite2.dbapi2.IntegrityError:
                    warn(insertStatement)
                    raise

        if self.target != 'dump':
            self.db.getConnection().commit()

        # get create index statement
        indexStatements = getCreateIndexStatement(self.PROVIDES,
            self.INDEX_KEYS)
        if self.target == 'dump':
            for statement in indexStatements:
                output(statement)
        else:
            for statement in indexStatements:
                self.db.getCursor().execute(statement)


class ListGenerator:
    """A simple generator for a given list of elements."""
    def __init__(self, entryList):
        """
        Initialises the ListGenerator.

        @type entryList: list of str
        @param entryList: user defined entry
        """
        self.entryList = entryList

    def __iter__(self):
        for entry in self.entryList:
            yield entry

#}
#{ Unihan character information

class UnihanGenerator:
    """
    Regular expression matching one entry in the Unihan database
    (e.g. C{U+8682  kMandarin       MA3 MA1 MA4}).
    """
    keySet = None
    """Set of keys of the Unihan table."""

    def __init__(self, fileName, useKeys=None, quiet=False):
        """
        Constructs the UnihanGenerator.

        @type fileName: str
        @param fileName: path to the Unihan database file
        @type useKeys: list
        @param useKeys: if given only these keys will be read from the table,
            otherwise all keys will be returned
        @type quiet: bool
        @param quiet: if true no status information will be printed to stderr
        """
        self.ENTRY_REGEX = re.compile(ur"U\+([0-9A-F]+)\s+(\w+)\s+(.+)\s*$")
        self.fileName = fileName
        self.quiet = quiet
        if useKeys != None:
            self.limitKeys = True
            self.keySet = set(useKeys)
        else:
            self.limitKeys = False

    def __iter__(self):
        """
        Iterates over the Unihan entries.

        The character definition is converted to the character's representation,
        all other data is given as is. These are merged into one entry for each
        character.
        """
        # attributes a separated over several lines. Read over lines until new
        # character found and yield old entry.
        handle = self.getHandle()
        entryIndex = -1
        entry = {}
        for line in handle:
            # ignore comments
            if line.startswith('#'):
                continue
            resultObj = self.ENTRY_REGEX.match(line)
            if not resultObj:
                if not self.quiet:
                    warn("can't read line from Unihan.txt: '" + line + "'")
                continue
            unicodeHexIndex, key, value = resultObj.group(1, 2, 3)

            # if we have a limited target key set, check if the current one is
            # to be included
            if self.limitKeys and not key in self.keySet:
                continue
            # check if new character entry found
            if entryIndex != unicodeHexIndex and entryIndex != -1:
                try:
                    # yield old one
                    char = unichr(int(entryIndex, 16))
                    yield(char, entry)
                except ValueError:
                    # catch for Unicode characters outside BMP for narrow builds
                    pass
                # empty old entry
                entry = {}
            entryIndex = unicodeHexIndex
            entry[key] = value
        # generate last entry
        if entry:
            try:
                # yield old one
                char = unichr(int(entryIndex, 16))
                yield(char, entry)
            except ValueError:
                # catch for Unicode characters outside BMP for narrow builds
                pass
        handle.close()

    def getHandle(self):
        """ 
        Returns a handle of the Unihan database file.

        @rtype: file
        @return: file handle of the Unihan file
        """
        import zipfile
        if zipfile.is_zipfile(self.fileName):
            import StringIO
            z = zipfile.ZipFile(self.fileName, "r")
            handle = StringIO.StringIO(z.read("Unihan.txt").decode('utf-8'))
        else:
            import codecs
            handle = codecs.open(self.fileName, 'r', 'utf-8')
        return handle

    def keys(self):
        """
        Returns all keys read for the Unihan table.

        If the whole table is read a seek through the file is needed first to
        find all keys, otherwise the predefined set is returned.
        @rtype: list
        @return: list of column names
        """
        if not self.keySet:
            if not self.quiet:
                warn("looking for all keys in Unihan database...")
            self.keySet = set()
            handle = self.getHandle()
            for line in handle:
                # ignore comments
                if line.startswith('#'):
                    continue
                resultObj = self.ENTRY_REGEX.match(line)
                if not resultObj:
                    continue

                unicodeHexIndex, key, value = resultObj.group(1, 2, 3)
                self.keySet.add(key)
            handle.close()
        return list(self.keySet)


class UnihanBuilder(EntryGeneratorBuilder):
    """Builds the Unihan database from the Unihan file provided by Unicode."""
    class EntryGenerator:
        """Generates the entries of the Unihan table."""

        def __init__(self, generator):
            """
            Initialises the EntryGenerator.

            @type generator: instance
            @param generator: a L{UnihanGenerator} instance
            """
            self.generator = generator

        def __iter__(self):
            """Provides all data of one character per entry."""
            columns = self.generator.keys()
            for char, entryDict in self.generator:
                newEntryDict = {UnihanBuilder.CHARACTER_COLUMN: char}
                for column in columns:
                    if entryDict.has_key(column):
                        newEntryDict[column] = entryDict[column]
                    else:
                        newEntryDict[column] = None
                yield newEntryDict

    PROVIDES = 'Unihan'
    CHARACTER_COLUMN = 'ChineseCharacter'
    """Name of column for Chinese character key."""
    COLUMN_TYPES = {CHARACTER_COLUMN: 'VARCHAR(1)', 'kCantonese': 'TEXT',
        'kFrequency': 'INTEGER', 'kHangul': 'TEXT', 'kHanyuPinlu': 'TEXT',
        'kJapaneseKun': 'TEXT', 'kJapaneseOn': 'TEXT', 'kKorean': 'TEXT',
        'kMandarin': 'TEXT', 'kRSJapanese': 'TEXT', 'kRSKanWa': 'TEXT',
        'kRSKangXi': 'TEXT', 'kRSKorean': 'TEXT', 'kSimplifiedVariant': 'TEXT',
        'kTotalStrokes': 'INTEGER', 'kTraditionalVariant': 'TEXT',
        'kVietnamese': 'TEXT', 'kZVariant': 'TEXT'}
    generator = None

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(UnihanBuilder, self).__init__(dataPath, dbConnectInst, quiet)
        generator = self.getGenerator()
        self.COLUMNS = [self.CHARACTER_COLUMN]
        self.COLUMNS.extend(generator.keys())
        self.PRIMARY_KEYS = [self.CHARACTER_COLUMN]
        self.ENTRY_GENERATOR = UnihanBuilder.EntryGenerator(generator)

    def getGenerator(self):
        """
        Returns the L{UnihanGenerator}. Constructs it if needed.

        @rtype: instance
        @return: instance of a L{UnihanGenerator}
        """
        if not self.generator:
            path = self.findFile(['Unihan.txt', 'Unihan.zip'],
                "Unihan database file")
            self.generator = UnihanGenerator(path)
            if not self.quiet:
                warn("reading file '" + path + "'")
        return self.generator


class UnihanBMPBuilder(UnihanBuilder):
    """
    Builds the Unihan database from the Unihan file provided by Unicode for
    characters from the Basic Multilingual Plane (BMP) with code values between
    U+0000 and U+FFFF.

    MySQL < 6 doesn't support true UTF-8, and uses a Version with max 3 bytes:
    U{http://dev.mysql.com/doc/refman/6.0/en/charset-unicode.html}
    """
    class BMPEntryGenerator:

        def __init__(self, generator):
            """
            Initialises the EntryGenerator.

            @type generator: instance
            @param generator: a L{UnihanGenerator} instance
            """
            self.entryGen = UnihanBuilder.EntryGenerator(generator)

        def __iter__(self):
            for entryDict in self.entryGen:
                # skip characters outside the BMP, i.e. for Chinese characters
                # >= 0x20000
                char = entryDict[UnihanBuilder.CHARACTER_COLUMN]
                if ord(char) < int('20000', 16):
                    yield entryDict

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(UnihanBMPBuilder, self).__init__(dataPath, dbConnectInst, quiet)
        generator = self.getGenerator()
        self.COLUMNS = [self.CHARACTER_COLUMN]
        self.COLUMNS.extend(generator.keys())
        self.PRIMARY_KEYS = [self.CHARACTER_COLUMN]
        self.ENTRY_GENERATOR = UnihanBMPBuilder.BMPEntryGenerator(generator)


class SlimUnihanBuilder(UnihanBuilder):
    """
    Builds a slim version of the Unihan database.

    Keys imported into the database are specified in L{INCLUDE_KEYS}.
    """
    INCLUDE_KEYS = ['kCompatibilityVariant', 'kCantonese', 'kFrequency',
        'kHangul', 'kHanyuPinlu', 'kJapaneseKun', 'kJapaneseOn', 'kMandarin',
        'kRSJapanese', 'kRSKanWa', 'kRSKangXi', 'kRSKorean', 'kSemanticVariant',
        'kSimplifiedVariant', 'kSpecializedSemanticVariant', 'kTotalStrokes',
        'kTraditionalVariant', 'kVietnamese', 'kXHC1983', 'kZVariant',
        'kIICore', 'kGB0']
    """Keys for that data is read into the Unihan table in database."""

    def getGenerator(self):
        if not self.generator:
            path = self.findFile(['Unihan.txt', 'Unihan.zip'],
                "Unihan database file")
            self.generator = UnihanGenerator(path, self.INCLUDE_KEYS)
            if not self.quiet:
                warn("reading file '" + path + "'")
        return self.generator


class SlimUnihanBMPBuilder(SlimUnihanBuilder, UnihanBMPBuilder):
    """
    Builds a slim version of the Unihan database from the Unihan file provided
    by Unicode for characters from the Basic Multilingual Plane (BMP) with code
    values between U+0000 and U+FFFF.

    MySQL < 6 doesn't support true UTF-8, and uses a Version with max 3 bytes:
    U{http://dev.mysql.com/doc/refman/6.0/en/charset-unicode.html}

    Keys imported into the database are specified in L{INCLUDE_KEYS}.
    """
    # all work is done in SlimUnihanBuilder and UnihanBMPBuilder
    pass


class Kanjidic2Builder(EntryGeneratorBuilder):
    """
    Builds the Kanjidic database from the Kanjidic2 XML file
    U{http://www.csse.monash.edu.au/~jwb/kanjidic2/}.
    """
    class XMLHandler(xml.sax.ContentHandler):
        """Extracts a list of given tags."""
        def __init__(self, entryList, tagDict):
            self.entryList = entryList
            self.tagDict = tagDict

            self.currentElement = []
            self.targetTag = None
            self.targetTagTopElement = None

        def endElement(self, name):
            assert(len(self.currentElement) > 0)
            assert(self.currentElement[-1] == name)
            self.currentElement.pop()

            if name == self.targetTagTopElement:
                self.targetTag = None
                self.targetTagTopElement = None

            if name == 'character':
                entryDict = {}
                for tag, func in self.tagDict.values():
                    if tag in self.currentEntry:
                        entryDict[tag] = func(self.currentEntry[tag])
                self.entryList.append(entryDict)

        def characters(self, content):
            if self.targetTag:
                if self.targetTag not in self.currentEntry:
                    self.currentEntry[self.targetTag] = []
                self.currentEntry[self.targetTag].append(content)

        def startElement(self, name, attrs):
            self.currentElement.append(name)
            if name == 'character':
                self.currentEntry = {}
            else:
                if 'character' in self.currentElement:
                    idx = self.currentElement.index('character') + 1
                    tagHierachy = tuple(self.currentElement[idx:])

                    key = (tagHierachy, frozenset(attrs.items()))
                    if key in self.tagDict:
                        self.targetTagTopElement = name
                        self.targetTag, _ = self.tagDict[key]

    class KanjidicGenerator:
        """Generates the KANJIDIC table."""
        def __init__(self, dataPath, tagDict):
            """
            Initialises the KanjidicGenerator.

            @type dataPath: list of str
            @param dataPath: optional list of paths to the data file(s)
            """
            self.dataPath = dataPath
            self.tagDict = tagDict

        def getHandle(self):
            """
            Returns a handle of the KANJIDIC database file.

            @rtype: file
            @return: file handle of the KANJIDIC file
            """
            import gzip
            if self.dataPath.endswith('.gz'):
                import StringIO
                z = gzip.GzipFile(self.dataPath, 'r')
                handle = StringIO.StringIO(z.read())
            else:
                import codecs
                handle = codecs.open(self.dataPath, 'r')
            return handle

        def __iter__(self):
            """Provides a pronunciation and a path to the audio file."""
            entryList = []
            xmlHandler = Kanjidic2Builder.XMLHandler(entryList, self.tagDict)

            saxparser = xml.sax.make_parser()
            saxparser.setContentHandler(xmlHandler)
            ## don't check DTD as this raises an exception
            #saxparser.setFeature(xml.sax.handler.feature_external_ges, False)
            saxparser.parse(self.getHandle())

            for entry in entryList:
                yield(entry)

    PROVIDES = 'Kanjidic'
    CHARACTER_COLUMN = 'ChineseCharacter'
    """Name of column for Chinese character key."""
    COLUMN_TYPES = {CHARACTER_COLUMN: 'VARCHAR(1)', 'NelsonRadical': 'INTEGER',
        'CharacterJapaneseOn': 'TEXT', 'CharacterJapaneseKun': 'TEXT'}
    KANJIDIC_TAG_MAPPING = {
        (('literal', ), frozenset()): ('ChineseCharacter', lambda x: x[0]),
        (('radical', 'rad_value'),
            frozenset([('rad_type', 'nelson_c')])): ('NelsonCRadical',
                lambda x: int(x[0])),
        (('radical', 'rad_value'),
            frozenset([('rad_type', 'nelson_n')])): ('NelsonNRadical',
                lambda x: int(x[0])),
        # TODO On and Kun reading in KANJIDICT include further optional
        #   attributes that makes the method miss the entry:
        #   on_type and r_status, these are currently not implemented in the
        #   file though
        (('reading_meaning', 'rmgroup', 'reading'),
            frozenset([('r_type', 'ja_on')])): ('CharacterJapaneseOn',
                lambda x: ','.join(x)),
        (('reading_meaning', 'rmgroup', 'reading'),
            frozenset([('r_type', 'ja_kun')])): ('CharacterJapaneseKun',
                lambda x: ','.join(x)),
        #(('reading_meaning', 'rmgroup', 'reading'),
            #frozenset([('r_type', 'pinyin')])): ('Pinyin',
                #lambda x: ','.join(x)),
        (('misc', 'rad_name'), frozenset()): ('RadicalName',
                lambda x: ','.join(x)),
        (('reading_meaning', 'rmgroup', 'meaning'), frozenset()): ('Meaning_en',
                lambda x: '/'.join(x)),
        (('reading_meaning', 'rmgroup', 'meaning'),
            frozenset([('m_lang', 'fr')])): ('Meaning_fr',
                lambda x: '/'.join(x)),
        (('reading_meaning', 'rmgroup', 'meaning'),
            frozenset([('m_lang', 'es')])): ('Meaning_es',
                lambda x: '/'.join(x)),
        (('reading_meaning', 'rmgroup', 'meaning'),
            frozenset([('m_lang', 'pt')])): ('Meaning_pt',
                lambda x: '/'.join(x)),
        }
    """
    Dictionary of tag keys mapping to a table column including a function
    generating a string out of a list of entries given from the KANJIDIC entry.
    The tag keys constist of a tuple giving the xml element hierarchy below the
    'character' element and a set of attribute value pairs.
    """

    generator = None

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(Kanjidic2Builder, self).__init__(dataPath, dbConnectInst, quiet)
        tags = [tag for tag, _ in self.KANJIDIC_TAG_MAPPING.values()]
        self.COLUMNS = tags
        self.PRIMARY_KEYS = [self.CHARACTER_COLUMN]
        self.ENTRY_GENERATOR = self.getGenerator()

    def getGenerator(self):
        """
        Returns the L{KanjidicGenerator}. Constructs it if needed.

        @rtype: instance
        @return: instance of a L{KanjidicGenerator}
        """
        if not self.generator:
            path = self.findFile(['kanjidic2.xml.gz', 'kanjidic2.xml'],
                "KANJIDIC2 XML file")
            self.generator = Kanjidic2Builder.KanjidicGenerator(path,
                self.KANJIDIC_TAG_MAPPING)
            if not self.quiet:
                warn("reading file '" + path + "'")
        return self.generator


class UnihanDerivedBuilder(EntryGeneratorBuilder):
    """
    Provides an abstract class for building a table with a relation between a
    Chinese character and another column using the Unihan database.
    """
    DEPENDS=['Unihan']
    COLUMN_SOURCE = None
    """
    Unihan table column providing content for the table. Needs to be overwritten
    in subclass.
    """
    COLUMN_TARGET = None
    """
    Column name for new data in created table. Needs to be overwritten in
    subclass.
    """
    COLUMN_TARGET_TYPE = 'VARCHAR(255)'
    """
    Type of column for new data in created table.
    """
    GENERATOR_CLASS = None
    """
    Class defining the iterator for creating the table's data. The constructor
    needs to take two parameters for the list of entries from the Unihan
    database and the 'quiet' flag. Needs to be overwritten in subclass.
    """

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(UnihanDerivedBuilder, self).__init__(dataPath, dbConnectInst,
            quiet)
        # create name mappings
        self.COLUMNS = ['ChineseCharacter', self.COLUMN_TARGET]
        self.PRIMARY_KEYS = self.COLUMNS
        # set column types
        self.COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)',
            self.COLUMN_TARGET: self.COLUMN_TARGET_TYPE}
        # create generator
        tableEntries = self.db.select('Unihan', ['ChineseCharacter',
            self.COLUMN_SOURCE], {self.COLUMN_SOURCE: 'IS NOT NULL'})
        self.ENTRY_GENERATOR = self.GENERATOR_CLASS(tableEntries, self.quiet)

    def build(self):
        if not self.quiet:
            warn("Reading table content from Unihan column '" \
                + self.COLUMN_SOURCE + "'")
        super(UnihanDerivedBuilder, self).build()


class UnihanStrokeCountBuilder(UnihanDerivedBuilder):
    """
    Builds a mapping between characters and their stroke count using the Unihan
    data.
    """
    class StrokeCountExtractor:
        """Extracts the character stroke count mapping."""
        def __init__(self, entries, quiet=False):
            """
            Initialises the StrokeCountExtractor.

            @type entries: list of tuple
            @param entries: character entries from the Unihan database
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            self.entries = entries
            self.quiet = quiet

        def __iter__(self):
            """Provides one entry per radical and character."""
            for character, strokeCount in self.entries:
                yield(character, strokeCount)

    PROVIDES = 'UnihanStrokeCount'
    COLUMN_SOURCE = 'kTotalStrokes'
    COLUMN_TARGET = 'StrokeCount'
    COLUMN_TARGET_TYPE = 'INTEGER'
    GENERATOR_CLASS = StrokeCountExtractor


class CharacterRadicalBuilder(UnihanDerivedBuilder):
    """
    Provides an abstract class for building a character radical mapping table
    using the Unihan database.
    """
    class RadicalExtractor:
        """Generates the radical to character mapping from the Unihan table."""
        def __init__(self, rsEntries, quiet=False):
            """
            Initialises the RadicalExtractor.

            @type rsEntries: list of tuple
            @param rsEntries: character radical entries from the Unihan database
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            self.RADICAL_REGEX = re.compile(ur"(\d+)\.(\d+)")
            self.rsEntries = rsEntries
            self.quiet = quiet

        def __iter__(self):
            """Provides one entry per radical and character."""
            for character, radicalStroke in self.rsEntries:
                matchObj = self.RADICAL_REGEX.match(radicalStroke)
                if matchObj:
                    radical = matchObj.group(1)
                    yield(character, radical)
                elif not self.quiet:
                    warn("unable to read radical information of character '" \
                        + character + "': '" + radicalStroke + "'")

    COLUMN_TARGET = 'RadicalIndex'
    COLUMN_TARGET_TYPE = 'INTEGER'
    GENERATOR_CLASS = RadicalExtractor


class CharacterKangxiRadicalBuilder(CharacterRadicalBuilder):
    """
    Builds the character Kangxi radical mapping table from the Unihan database.
    """
    PROVIDES = 'CharacterKangxiRadical'
    COLUMN_SOURCE = 'kRSKangXi'


class CharacterKanWaRadicalBuilder(CharacterRadicalBuilder):
    """
    Builds the character Dai Kan-Wa jiten radical mapping table from the Unihan
    database.
    """
    PROVIDES = 'CharacterKanWaRadical'
    COLUMN_SOURCE = 'kRSKanWa'


class CharacterJapaneseRadicalBuilder(CharacterRadicalBuilder):
    """
    Builds the character Japanese radical mapping table from the Unihan
    database.
    """
    PROVIDES = 'CharacterJapaneseRadical'
    COLUMN_SOURCE = 'kRSJapanese'


class CharacterKoreanRadicalBuilder(CharacterRadicalBuilder):
    """
    Builds the character Korean radical mapping table from the Unihan
    database.
    """
    PROVIDES = 'CharacterKoreanRadical'
    COLUMN_SOURCE = 'kRSKorean'


class CharacterVariantBuilder(EntryGeneratorBuilder):
    """
    Builds a character variant mapping table from the Unihan database.
    """
    class VariantGenerator:
        """Generates the character to variant mapping from the Unihan table."""

        # Regular expressions for different entry types
        HEX_INDEX_REGEX = re.compile(ur"\s*U\+([0-9A-F]+)\s*$")
        MULT_HEX_INDEX_REGEX = re.compile(ur"\s*(U\+([0-9A-F]+)( |(?=$)))+\s*$")
        MULT_HEX_INDEX_FIND_REGEX = re.compile(ur"U\+([0-9A-F]+)(?: |(?=$))")
        SEMANTIC_REGEX = re.compile(ur"(U\+[0-9A-F]+(<\S+)?( |(?=$)))+$")
        SEMANTIC_FIND_REGEX = re.compile(ur"U\+([0-9A-F]+)(?:<\S+)?(?: |(?=$))")
        ZVARIANT_REGEX = re.compile(ur"\s*U\+([0-9A-F]+)(?:\:\S+)?\s*$")

        VARIANT_REGEX_MAPPING = {'C': (HEX_INDEX_REGEX, HEX_INDEX_REGEX),
            'M': (SEMANTIC_REGEX, SEMANTIC_FIND_REGEX),
            'S': (MULT_HEX_INDEX_REGEX, MULT_HEX_INDEX_FIND_REGEX),
            'P': (SEMANTIC_REGEX, SEMANTIC_FIND_REGEX),
            'T': (MULT_HEX_INDEX_REGEX, MULT_HEX_INDEX_FIND_REGEX),
            'Z': (ZVARIANT_REGEX, ZVARIANT_REGEX)}
        """
        Mapping of entry types to regular expression describing the entry's
        pattern.
        """

        def __init__(self, variantEntries, typeList, quiet=False):
            """
            Initialises the VariantGenerator.

            @type variantEntries: list of tuple
            @param variantEntries: character variant entries from the Unihan
                database
            @type typeList: list of str
            @param typeList: variant types in the order given in tableEntries
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            self.variantEntries = variantEntries
            self.typeList = typeList
            self.quiet = quiet

        def __iter__(self):
            """Provides one entry per variant and character."""
            for entries in self.variantEntries:
                character = entries[0]
                for i, variantType in enumerate(self.typeList):
                    variantInfo = entries[i+1]
                    if variantInfo:
                        # get proper regular expression for given variant info
                        matchR, findR = self.VARIANT_REGEX_MAPPING[variantType]
                        if matchR.match(variantInfo):
                            # get all hex indices
                            variantIndices = findR.findall(variantInfo)
                            for unicodeHexIndex in variantIndices:
                                try:
                                    variant = unichr(int(unicodeHexIndex, 16))
                                    yield(character, variant, variantType)
                                except ValueError:
                                    # catch for Unicode characters outside BMP
                                    #   for narrow builds
                                    pass
                        elif not self.quiet:
                            # didn't match the regex
                            warn('unable to read variant information of ' \
                                + "character '" + character + "' for type '" \
                                + variantType + "': '" + variantInfo + "'")

    PROVIDES = 'CharacterVariant'
    DEPENDS=['Unihan']

    COLUMN_SOURCE_ABBREV = {'kCompatibilityVariant': 'C',
        'kSemanticVariant': 'M', 'kSimplifiedVariant': 'S',
        'kSpecializedSemanticVariant': 'P', 'kTraditionalVariant': 'T',
        'kZVariant': 'Z'}
    """
    Unihan table columns providing content for the table together with their
    abbreviation used in the target table.
    """

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CharacterVariantBuilder, self).__init__(dataPath, dbConnectInst,
            quiet)
        # create name mappings
        self.COLUMNS = ['ChineseCharacter', 'Variant', 'Type']
        self.PRIMARY_KEYS = self.COLUMNS
        # set column types
        self.COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)',
            'Variant': 'VARCHAR(1)', 'Type': 'CHAR'}
        # create generator
        keys = self.COLUMN_SOURCE_ABBREV.keys()
        variantTypes = [self.COLUMN_SOURCE_ABBREV[key] for key in keys]
        selectKeys = ['ChineseCharacter']
        selectKeys.extend(keys)
        tableEntries = self.db.select('Unihan', selectKeys)
        self.ENTRY_GENERATOR = \
            CharacterVariantBuilder.VariantGenerator(tableEntries, variantTypes,
                self.quiet)

    def build(self):
        if not self.quiet:
            warn("Reading table content from Unihan columns '" \
                + ', '.join(self.COLUMN_SOURCE_ABBREV.keys()) + "'")
        super(CharacterVariantBuilder, self).build()


class CharacterVariantBMPBuilder(CharacterVariantBuilder):
    """
    Builds a character variant mapping table from the Unihan database for
    characters from the Basic Multilingual Plane (BMP) with code values between
    U+0000 and U+FFFF.

    MySQL < 6 doesn't support true UTF-8, and uses a Version with max 3 bytes:
    U{http://dev.mysql.com/doc/refman/6.0/en/charset-unicode.html}
    """
    class BMPVariantGenerator:

        def __init__(self, variantEntries, typeList, quiet=False):
            """
            Initialises the BMPVariantGenerator.

            @type variantEntries: list of tuple
            @param variantEntries: character variant entries from the Unihan
                database
            @type typeList: list of str
            @param typeList: variant types in the order given in tableEntries
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            self.variantGen = CharacterVariantBuilder.VariantGenerator( \
                variantEntries, typeList, quiet)

        def __iter__(self):
            for character, variant, variantType in self.variantGen:
                # skip characters outside the BMP, i.e. for Chinese characters
                # >= 0x20000
                if ord(variant) < int('20000', 16):
                    yield(character, variant, variantType)

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CharacterVariantBMPBuilder, self).__init__(dataPath,
            dbConnectInst, quiet)
        # create generator
        keys = self.COLUMN_SOURCE_ABBREV.keys()
        variantTypes = [self.COLUMN_SOURCE_ABBREV[key] for key in keys]
        selectKeys = ['ChineseCharacter']
        selectKeys.extend(keys)
        tableEntries = self.db.select('Unihan', selectKeys)
        self.ENTRY_GENERATOR = \
            CharacterVariantBMPBuilder.BMPVariantGenerator(tableEntries,
                variantTypes, self.quiet)


class UnihanCharacterSetBuilder(EntryGeneratorBuilder):
    """
    Builds a simple list of characters that belong to a specific class using the
    Unihan data.
    """
    DEPENDS=['Unihan']

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(UnihanCharacterSetBuilder, self).__init__(dataPath, dbConnectInst,
            quiet)
        # create name mappings
        self.COLUMNS = ['ChineseCharacter']
        self.PRIMARY_KEYS = self.COLUMNS
        # set column types
        self.COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)'}
        # create generator
        tableEntries = self.db.selectSoleValue('Unihan', 'ChineseCharacter',
            {self.COLUMN_SOURCE: 'IS NOT NULL'})
        self.ENTRY_GENERATOR = ListGenerator(tableEntries)

    def build(self):
        if not self.quiet:
            warn("Reading table content from Unihan column '" \
                + self.COLUMN_SOURCE + "'")
        super(UnihanCharacterSetBuilder, self).build()


class IICoreSetBuilder(UnihanCharacterSetBuilder):
    u"""
    Builds a simple list of all characters in X{IICore}
    (Unicode I{International Ideograph Core)}.
    @see: Chinese Wikipedia on IICore:
        U{http://zh.wikipedia.org/wiki/國際表意文字核心}
    """
    PROVIDES = 'IICoreSet'
    COLUMN_SOURCE = 'kIICore'


class GB2312SetBuilder(UnihanCharacterSetBuilder):
    """
    Builds a simple list of all characters in the Chinese standard X{GB2312-80}.
    """
    PROVIDES = 'GB2312Set'
    COLUMN_SOURCE = 'kGB0'

#}
#{ Unihan reading information

class CharacterReadingBuilder(UnihanDerivedBuilder):
    """
    Provides an abstract class for building a character reading mapping table
    using the Unihan database.
    """
    class SimpleReadingSplitter:
        """Generates the reading entities from the Unihan table."""
        SPLIT_REGEX = re.compile(r"(\S+)")

        def __init__(self, readingEntries, quiet=False):
            """
            Initialises the ReadingSplitter.

            @type readingEntries: list of tuple
            @param readingEntries: character reading entries from the Unihan
                database
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            self.readingEntries = readingEntries
            self.quiet = quiet

        def __iter__(self):
            """Provides one entry per reading entity and character."""
            for character, readings in self.readingEntries:
                readingList = self.SPLIT_REGEX.findall(readings)
                if not self.quiet and len(set(readingList)) < len(readingList):
                    warn('reading information of character ' + character \
                        + ' is inconsistent: ' + ', '.join(readingList))
                for reading in set(readingList):
                    yield(character, reading.lower())

    COLUMN_TARGET = 'Reading'
    COLUMN_TARGET_TYPE = 'VARCHAR(255)'
    GENERATOR_CLASS = SimpleReadingSplitter
    DEPENDS=['Unihan']


class CharacterUnihanPinyinBuilder(CharacterReadingBuilder):
    """
    Builds the character Pinyin mapping table from the Unihan database.
    """
    PROVIDES = 'CharacterUnihanPinyin'
    COLUMN_SOURCE = 'kMandarin'


class CharacterJyutpingBuilder(CharacterReadingBuilder):
    """Builds the character Jyutping mapping table from the Unihan database."""
    PROVIDES = 'CharacterJyutping'
    COLUMN_SOURCE = 'kCantonese'


class CharacterJapaneseKunBuilder(CharacterReadingBuilder):
    """Builds the character Kun'yomi mapping table from the Unihan database."""
    PROVIDES = 'CharacterJapaneseKun'
    COLUMN_SOURCE = 'kJapaneseKun'


class CharacterJapaneseOnBuilder(CharacterReadingBuilder):
    """Builds the character On'yomi mapping table from the Unihan database."""
    PROVIDES = 'CharacterJapaneseOn'
    COLUMN_SOURCE = 'kJapaneseOn'


class CharacterHangulBuilder(CharacterReadingBuilder):
    """Builds the character Hangul mapping table from the Unihan database."""
    PROVIDES = 'CharacterHangul'
    COLUMN_SOURCE = 'kHangul'


class CharacterVietnameseBuilder(CharacterReadingBuilder):
    """
    Builds the character Vietnamese mapping table from the Unihan database.
    """
    PROVIDES = 'CharacterVietnamese'
    COLUMN_SOURCE = 'kVietnamese'


class CharacterXHPCReadingBuilder(CharacterReadingBuilder):
    """
    Builds the Xiandai Hanyu Pinlu Cidian Pinyin mapping table using the Unihan
    database.
    """
    class XHPCReadingSplitter(CharacterReadingBuilder.SimpleReadingSplitter):
        """
        Generates the Xiandai Hanyu Pinlu Cidian Pinyin syllables from the
        Unihan table.
        """
        SPLIT_REGEX = re.compile(ur"([a-zü]+[1-5])\([0-9]+\)")

    GENERATOR_CLASS = XHPCReadingSplitter

    PROVIDES = 'CharacterXHPCPinyin'
    COLUMN_SOURCE = 'kHanyuPinlu'


class CharacterXHCReadingBuilder(CharacterReadingBuilder):
    """
    Builds the Xiandai Hanyu Cidian Pinyin mapping table using the Unihan
    database.
    """
    class XHCReadingSplitter(CharacterReadingBuilder.SimpleReadingSplitter):
        """
        Generates the Xiandai Hanyu Cidian Pinyin syllables from the Unihan
        table.
        """
        SPLIT_REGEX = re.compile(r"[0-9,.*]+:(\S+)")

        TONEMARK_VOWELS = [u'a', u'e', u'i', u'o', u'u', u'ü', u'n', u'm', u'r',
            u'ê']

        TONEMARK_MAP = {u'\u0304': 1, u'\u0301': 2, u'\u030c': 3, u'\u0300': 4}

        def __init__(self, readingEntries, quiet=False):
            """
            Initialises the XHCReadingSplitter.

            @type readingEntries: list of tuple
            @param readingEntries: character reading entries from the Unihan
                database
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            CharacterReadingBuilder.SimpleReadingSplitter.__init__(self,
                readingEntries, quiet)
            self._toneMarkRegex = re.compile(u'[' \
                + ''.join(self.TONEMARK_MAP.keys()) + ']')

        def convertTonemark(self, entity):
            """
            Converts the entity with diacritics into an entity with tone mark
            as appended number.

            @type entity: str
            @param entity: entity with tonal information
            @rtype: tuple
            @return: plain entity without tone mark and entity's tone index
                (starting with 1)
            """
            import unicodedata
            # get decomposed Unicode string, e.g. C{'ū'} to C{'u\u0304'}
            entity = unicodedata.normalize("NFD", unicode(entity))
            # find character with tone marker
            matchObj = self._toneMarkRegex.search(entity)
            if matchObj:
                diacriticalMark = matchObj.group(0)
                tone = self.TONEMARK_MAP[diacriticalMark]
                # strip off diacritical mark
                plainEntity = entity.replace(diacriticalMark, '')
                # compose Unicode string (used for ê) and return with tone
                return unicodedata.normalize("NFC", plainEntity) + str(tone)
            else:
                # fifth tone doesn't have any marker
                return unicodedata.normalize("NFC", entity) + '5'

        def __iter__(self):
            """Provides one entry per reading entity and character."""
            for character, readings in self.readingEntries:
                readingList = self.SPLIT_REGEX.findall(readings)
                if not self.quiet and len(set(readingList)) < len(readingList):
                    warn('reading information of character ' + character \
                        + ' is inconsistent: ' + ', '.join(readingList))
                for reading in set(readingList):
                    yield(character, self.convertTonemark(reading.lower()))

    GENERATOR_CLASS = XHCReadingSplitter

    PROVIDES = 'CharacterXHCPinyin'
    COLUMN_SOURCE = 'kXHC1983'


class CharacterPinyinBuilder(EntryGeneratorBuilder):
    """
    Builds the character Pinyin mapping table from the several sources.
    """
    PROVIDES = 'CharacterPinyin'
    DEPENDS=['CharacterUnihanPinyin', 'CharacterXHPCPinyin',
        'CharacterXHCPinyin']

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CharacterPinyinBuilder, self).__init__(dataPath, dbConnectInst,
            quiet)
        # create name mappings
        self.COLUMNS = ['ChineseCharacter', 'Reading']
        self.PRIMARY_KEYS = self.COLUMNS
        # set column types
        self.COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)',
            'Reading': 'VARCHAR(255)'}
        # create generator
        self.db.getCursor().execute(u' UNION '.join(\
            [self.db.getSelectCommand(table, self.COLUMNS, {}) \
                for table in self.DEPENDS]) + ';')
        tableEntries = self.db.getCursor().fetchall()
        self.ENTRY_GENERATOR = ListGenerator(tableEntries)

#}
#{ CSV file based

class CSVFileLoader(TableBuilder):
    """
    Builds a table by loading its data from a list of comma separated values
    (CSV).
    """
    TABLE_CSV_FILE_MAPPING = ''
    """csv file path"""
    TABLE_DECLARATION_FILE_MAPPING = ''
    """file path containing SQL create table code."""
    INDEX_KEYS = []
    """Index keys (not unique) of the created table"""

    class DefaultDialect(csv.Dialect):
        """Defines a default dialect for the case sniffing fails."""
        quoting = csv.QUOTE_NONE
        delimiter = ','
        lineterminator = '\n'
        quotechar = "'"

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CSVFileLoader, self).__init__(dataPath, dbConnectInst, quiet)

    # TODO unicode_csv_reader(), utf_8_encoder(), byte_string_dialect() used
    #  to work around missing Unicode support in csv module
    @staticmethod
    def unicode_csv_reader(unicode_csv_data, dialect, **kwargs):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
        csv_reader = csv.reader(CSVFileLoader.utf_8_encoder(unicode_csv_data),
            dialect=CSVFileLoader.byte_string_dialect(dialect), **kwargs)
        for row in csv_reader:
            # decode UTF-8 back to Unicode, cell by cell:
            yield [unicode(cell, 'utf-8') for cell in row]

    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    @staticmethod
    def byte_string_dialect(dialect):
        class ByteStringDialect(csv.Dialect):
            def __init__(self, dialect):
                self.delimiter = str(dialect.delimiter)
                if dialect.escapechar:
                    self.escapechar = str(dialect.escapechar)
                self.lineterminator = str(dialect.lineterminator)
                self.quotechar = str(dialect.quotechar)
                self.quoting = dialect.quoting

        return ByteStringDialect(dialect)

    def getCSVReader(self, fileHandle):
        """
        Returns a csv reader object for a given file name.

        The file can start with the character '#' to mark comments. These will
        be ignored. The first line after the leading comments will be used to
        guess the csv file's format.

        @type fileHandle: file
        @param fileHandle: file handle of the CSV file
        @rtype: instance
        @return: CSV reader object returning one entry per line
        """
        def prependLineGenerator(line, data):
            """
            The first line red for guessing format has to be reinserted.
            """
            yield line
            for nextLine in data:
                yield nextLine

        line = '#'
        try:
            while line.strip().startswith('#'):
                line = fileHandle.next()
        except StopIteration:
            raise IOError("error reading from input")
        try:
            self.fileDialect = csv.Sniffer().sniff(line, ['\t', ','])
        except csv.Error:
            self.fileDialect = CSVFileLoader.DefaultDialect()

        content = prependLineGenerator(line, fileHandle)
        #return csv.reader(content, dialect=self.fileDialect) # TODO
        return CSVFileLoader.unicode_csv_reader(content, self.fileDialect)

    def build(self):
        import locale
        import codecs
        # create drop table statement
        dropStatement = getDropTableStatement(self.PROVIDES)
        # get create statement
        filePath = self.findFile([self.TABLE_DECLARATION_FILE_MAPPING],
            "SQL table definition file")
        if not self.quiet:
            warn("Reading table definition from file '" + filePath + "'")

        fileHandle = codecs.open(filePath, 'r', 'utf-8')
        createStatement = ''.join(fileHandle.readlines()).strip("\n")
        if self.target == 'dump':
            output(dropStatement)
            output(createStatement)
        else:
            self.db.getCursor().execute(dropStatement)
            self.db.getCursor().execute(createStatement)
            self.db.getCursor().execute('BEGIN;')

        # write table content
        filePath = self.findFile([self.TABLE_CSV_FILE_MAPPING], "table")
        if not self.quiet:
            warn("Reading table '" + self.PROVIDES + "' from file '" \
                + filePath + "'")
        fileHandle = codecs.open(filePath, 'r', 'utf-8')

        for line in self.getCSVReader(fileHandle):
            insertStatement = getInsertStatement(self.PROVIDES, line)
            if self.target == 'dump':
                output(insertStatement)
            else:
                try:
                    self.db.getCursor().execute(insertStatement)
                except Exception, strerr: # TODO get a better exception here
                    warn("Error '" + str(strerr) \
                        + "' inserting line with following code: '" \
                        + insertStatement + "'")

        # get create index statement
        indexStatements = getCreateIndexStatement(self.PROVIDES,
            self.INDEX_KEYS)
        if self.target == 'dump':
            for statement in indexStatements:
                output(statement)
        else:
            for statement in indexStatements:
                self.db.getCursor().execute(statement)

        if self.target != 'dump':
            self.db.getConnection().commit()


class PinyinSyllablesBuilder(CSVFileLoader):
    """
    Builds a list of Pinyin syllables.
    """
    PROVIDES = 'PinyinSyllables'

    TABLE_CSV_FILE_MAPPING = 'pinyinsyllables.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'pinyinsyllables.sql'


class PinyinInitialFinalBuilder(CSVFileLoader):
    """
    Builds a mapping from Pinyin syllables to their initial/final parts.
    """
    PROVIDES = 'PinyinInitialFinal'

    TABLE_CSV_FILE_MAPPING = 'pinyininitialfinal.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'pinyininitialfinal.sql'


class WadeGilesSyllablesBuilder(CSVFileLoader):
    """
    Builds a list of Wade-Giles syllables.
    """
    PROVIDES = 'WadeGilesSyllables'

    TABLE_CSV_FILE_MAPPING = 'wadegilessyllables.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'wadegilessyllables.sql'


class GRSyllablesBuilder(CSVFileLoader):
    """
    Builds a list of Gwoyeu Romatzyh syllables.
    """
    PROVIDES = 'GRSyllables'

    TABLE_CSV_FILE_MAPPING = 'grsyllables.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'grsyllables.sql'


class GRRhotacisedFinalsBuilder(CSVFileLoader):
    """
    Builds a list of Gwoyeu Romatzyh rhotacised finals.
    """
    PROVIDES = 'GRRhotacisedFinals'

    TABLE_CSV_FILE_MAPPING = 'grrhotacisedfinals.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'grrhotacisedfinals.sql'


class GRAbbreviationBuilder(CSVFileLoader):
    """
    Builds a list of Gwoyeu Romatzyh abbreviated spellings.
    """
    PROVIDES = 'GRAbbreviation'

    TABLE_CSV_FILE_MAPPING = 'grabbreviation.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'grabbreviation.sql'


class JyutpingSyllablesBuilder(CSVFileLoader):
    """
    Builds a list of Jyutping syllables.
    """
    PROVIDES = 'JyutpingSyllables'

    TABLE_CSV_FILE_MAPPING = 'jyutpingsyllables.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'jyutpingsyllables.sql'


class JyutpingInitialFinalBuilder(CSVFileLoader):
    """
    Builds a mapping from Jyutping syllables to their initial/final parts.
    """
    PROVIDES = 'JyutpingInitialFinal'

    TABLE_CSV_FILE_MAPPING = 'jyutpinginitialfinal.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'jyutpinginitialfinal.sql'


class CantoneseYaleSyllablesBuilder(CSVFileLoader):
    """
    Builds a list of Cantonese Yale syllables.
    """
    PROVIDES = 'CantoneseYaleSyllables'

    TABLE_CSV_FILE_MAPPING = 'cantoneseyalesyllables.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'cantoneseyalesyllables.sql'


class CantoneseYaleInitialNucleusCodaBuilder(CSVFileLoader):
    """
    Builds a mapping of Cantonese syllable in the Yale romanisation
    system to the syllables' initial, nucleus and coda.
    """
    PROVIDES = 'CantoneseYaleInitialNucleusCoda'

    TABLE_CSV_FILE_MAPPING = 'cantoneseyaleinitialnucleuscoda.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'cantoneseyaleinitialnucleuscoda.sql'


class JyutpingYaleMappingBuilder(CSVFileLoader):
    """
    Builds a mapping between syllables in Jyutping and the Yale romanization
    system.
    """
    PROVIDES = 'JyutpingYaleMapping'

    TABLE_CSV_FILE_MAPPING = 'jyutpingyalemapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'jyutpingyalemapping.sql'


class WadeGilesPinyinMappingBuilder(CSVFileLoader):
    """
    Builds a mapping between syllables in Wade-Giles and Pinyin.
    """
    PROVIDES = 'WadeGilesPinyinMapping'

    TABLE_CSV_FILE_MAPPING = 'wadegilespinyinmapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'wadegilespinyinmapping.sql'


class PinyinGRMappingBuilder(CSVFileLoader):
    """
    Builds a mapping between syllables in Pinyin and Gwoyeu Romatzyh.
    """
    PROVIDES = 'PinyinGRMapping'

    TABLE_CSV_FILE_MAPPING = 'pinyingrmapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'pinyingrmapping.sql'


class PinyinIPAMappingBuilder(CSVFileLoader):
    """
    Builds a mapping between syllables in Pinyin and their representation in
    IPA.
    """
    PROVIDES = 'PinyinIPAMapping'

    TABLE_CSV_FILE_MAPPING = 'pinyinipamapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'pinyinipamapping.sql'


class MandarinIPAInitialFinalBuilder(CSVFileLoader):
    """
    Builds a mapping from Mandarin syllables in IPA to their initial/final
    parts.
    """
    PROVIDES = 'MandarinIPAInitialFinal'

    TABLE_CSV_FILE_MAPPING = 'mandarinipainitialfinal.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'mandarinipainitialfinal.sql'


class JyutpingIPAMappingBuilder(CSVFileLoader):
    """
    Builds a mapping between syllables in Jyutping and their representation in
    IPA.
    """
    PROVIDES = 'JyutpingIPAMapping'

    TABLE_CSV_FILE_MAPPING = 'jyutpingipamapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'jyutpingipamapping.sql'


class CantoneseIPAInitialFinalBuilder(CSVFileLoader):
    """
    Builds a mapping from Cantonese syllables in IPA to their initial/final
    parts.
    """
    PROVIDES = 'CantoneseIPAInitialFinal'

    TABLE_CSV_FILE_MAPPING = 'cantoneseipainitialfinal.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'cantoneseipainitialfinal.sql'


class KangxiRadicalBuilder(CSVFileLoader):
    """
    Builds a mapping between Kangxi radical index and radical characters.
    """
    PROVIDES = 'KangxiRadical'

    TABLE_CSV_FILE_MAPPING = 'kangxiradical.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'kangxiradical.sql'


class KangxiRadicalIsolatedCharacterBuilder(CSVFileLoader):
    """
    Builds a mapping between Kangxi radical index and radical equivalent
    characters without radical form.
    """
    PROVIDES = 'KangxiRadicalIsolatedCharacter'

    TABLE_CSV_FILE_MAPPING = 'kangxiradicalisolatedcharacter.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'kangxiradicalisolatedcharacter.sql'


class RadicalEquivalentCharacterBuilder(CSVFileLoader):
    """
    Builds a mapping between I{Unicode radical forms} and
    I{Unicode radical variants} on one side and I{equivalent characters} on the
    other side.
    """
    PROVIDES = 'RadicalEquivalentCharacter'

    TABLE_CSV_FILE_MAPPING = 'radicalequivalentcharacter.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'radicalequivalentcharacter.sql'


class StrokesBuilder(CSVFileLoader):
    """
    Builds a list of strokes and their names.
    """
    PROVIDES = 'Strokes'

    TABLE_CSV_FILE_MAPPING = 'strokes.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'strokes.sql'


class StrokeOrderBuilder(CSVFileLoader):
    """
    Builds a mapping between characters and their stroke order.
    """
    PROVIDES = 'StrokeOrder'

    TABLE_CSV_FILE_MAPPING = 'strokeorder.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'strokeorder.sql'


class CharacterDecompositionBuilder(CSVFileLoader):
    """
    Builds a mapping between characters and their decomposition.
    """
    PROVIDES = 'CharacterDecomposition'

    TABLE_CSV_FILE_MAPPING = 'characterdecomposition.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'characterdecomposition.sql'
    INDEX_KEYS = [['ChineseCharacter', 'ZVariant']]


class LocaleCharacterVariantBuilder(CSVFileLoader):
    """
    Builds a mapping between a character under a locale and its default variant.
    """
    PROVIDES = 'LocaleCharacterVariant'

    TABLE_CSV_FILE_MAPPING = 'localecharactervariant.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'localecharactervariant.sql'


class MandarinBraileInitialBuilder(CSVFileLoader):
    """
    Builds a mapping of Mandarin Chinese syllable initials in Pinyin to Braille
    characters.
    """
    PROVIDES = 'PinyinBrailleInitialMapping'

    TABLE_CSV_FILE_MAPPING = 'pinyinbrailleinitialmapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'pinyinbrailleinitialmapping.sql'


class MandarinBraileFinalBuilder(CSVFileLoader):
    """
    Builds a mapping of Mandarin Chinese syllable finals in Pinyin to Braille
    characters.
    """
    PROVIDES = 'PinyinBrailleFinalMapping'

    TABLE_CSV_FILE_MAPPING = 'pinyinbraillefinalmapping.csv'
    TABLE_DECLARATION_FILE_MAPPING = 'pinyinbraillefinalmapping.sql'


#}
#{ Library dependant

class ZVariantBuilder(EntryGeneratorBuilder):
    """
    Builds a list of glyph indices for characters.
    @todo Impl: Check if all Z-variants in LocaleCharacterVariant are included.
    """
    PROVIDES = 'ZVariants'
    DEPENDS = ['CharacterDecomposition', 'StrokeOrder', 'Unihan']
    # TODO 'LocaleCharacterVariant'

    COLUMNS = ['ChineseCharacter', 'ZVariant']
    PRIMARY_KEYS = ['ChineseCharacter', 'ZVariant']
    INDEX_KEYS = [['ChineseCharacter']]
    COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)', 'ZVariant': 'INTEGER'}

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(ZVariantBuilder, self).__init__(dataPath, dbConnectInst, quiet)
        self.ENTRY_GENERATOR = self.getGenerator()

    def getGenerator(self):
        characterSet = set(self.db.select('CharacterDecomposition',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        characterSet.update(self.db.select('StrokeOrder',
            ['ChineseCharacter', 'ZVariant']))
        # TODO
        #characterSet.update(self.db.select('LocaleCharacterVariant',
            #['ChineseCharacter', 'ZVariant']))
        # Add characters from Unihan as Z-variant 0
        unihanCharacters = self.db.selectSoleValue('Unihan', 'ChineseCharacter',
            [{'kTotalStrokes': 'IS NOT NULL'}, {'kRSKangXi': 'IS NOT NULL'}])
        characterSet.update([(char, 0) for char in unihanCharacters])

        return ListGenerator(characterSet)


class StrokeCountBuilder(EntryGeneratorBuilder):
    """
    Builds a mapping between characters and their stroke count.
    """
    class StrokeCountGenerator:
        """Generates the character stroke count mapping."""
        def __init__(self, dbConnectInst, characterSet, quiet=False):
            """
            Initialises the StrokeCountGenerator.

            @type dbConnectInst: instance
            @param dbConnectInst: instance of a L{DatabaseConnector}.
            @type characterSet: set
            @param characterSet: set of characters to generate the table for
            @type quiet: bool
            @param quiet: if true no status information will be printed to
                stderr
            """
            self.characterSet = characterSet
            self.quiet = quiet
            self.cjk = characterlookup.CharacterLookup(
                dbConnectInst=dbConnectInst)
            # make sure a currently existing table is not used
            self.cjk.hasStrokeCount = False

        def __iter__(self):
            """Provides one entry per character, z-Variant and locale subset."""
            for char, zVariant in self.characterSet:
                try:
                    # cjklib's stroke count method uses the stroke order
                    #   information as long as this table doesn't exist
                    strokeCount = self.cjk.getStrokeCount(char,
                        zVariant=zVariant)
                    yield {'ChineseCharacter': char, 'StrokeCount': strokeCount,
                        'ZVariant': zVariant}
                except exception.NoInformationError:
                    pass
                except IndexError:
                    if not self.quiet:
                        warn("malformed IDS for character '" + char \
                            + "'")

    PROVIDES = 'StrokeCount'
    DEPENDS = ['CharacterDecomposition', 'StrokeOrder']

    COLUMNS = ['ChineseCharacter', 'StrokeCount', 'ZVariant']
    PRIMARY_KEYS = ['ChineseCharacter', 'ZVariant']
    COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)', 'StrokeCount': 'INTEGER',
        'ZVariant': 'INTEGER'}

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(StrokeCountBuilder, self).__init__(dataPath, dbConnectInst, quiet)
        self.ENTRY_GENERATOR = self.getGenerator()

    def getGenerator(self):
        characterSet = set(self.db.select('CharacterDecomposition',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        characterSet.update(self.db.select('StrokeOrder',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        return StrokeCountBuilder.StrokeCountGenerator(self.db, characterSet,
            self.quiet)


class CombinedStrokeCountBuilder(StrokeCountBuilder):
    """
    Builds a mapping between characters and their stroke count. Includes stroke
    count data from the Unihan database to make up for missing data in own data
    files.
    """
    class CombinedStrokeCountGenerator:
        """Generates the character stroke count mapping."""
        def __init__(self, dbConnectInst, characterSet, tableEntries,
            preferredBuilder, quiet=False):
            """
            Initialises the CombinedStrokeCountGenerator.

            @type dbConnectInst: instance
            @param dbConnectInst: instance of a L{DatabaseConnector}.
            @type characterSet: set
            @param characterSet: set of characters to generate the table for
            @type tableEntries: list of list
            @param tableEntries: list of characters with Z-variant
            @type preferredBuilder: instance
            @param preferredBuilder: TableBuilder which forms are preferred over
                entries from the Unihan table
            @type quiet: bool
            @param quiet: if true no status information will be printed to
                stderr
            """
            self.characterSet = characterSet
            self.tableEntries = tableEntries
            self.preferredBuilder = preferredBuilder
            self.quiet = quiet
            self.cjk = characterlookup.CharacterLookup(
                dbConnectInst=dbConnectInst)
            self.db = dbConnectInst

        def getStrokeCount(self, char, zVariant, strokeCountDict,
            unihanStrokeCountDict, decompositionDict):
            """
            Gets the stroke count of the given character by summing up the
            stroke count of its components and using the Unihan table as
            fallback.

            For the sake of consistency this method doesn't take the stroke
            count given by Unihan directly but sums up the stroke counts of the
            components to make sure the sum of component's stroke count will
            always give the characters stroke count. The result yielded will be
            in many cases even more precise than the value given in Unihan (not
            depending on the actual glyph form).

            Once calculated the stroke count will be cached in the given
            strokeCountDict object.

            @type char: str
            @param char: Chinese character
            @type zVariant: int
            @param zVariant: Z-variant of character
            @rtype: int
            @return: stroke count
            @raise ValueError: if stroke count is ambiguous due to inconsistent
                values wrt Unihan vs. own data.
            @raise NoInformationError: if decomposition is incomplete
            """
            if char == u'？':
                # we have an incomplete decomposition, can't build
                raise exception.NoInformationError("incomplete decomposition")

            if (char, zVariant) not in strokeCountDict:
                lastStrokeCount = None
                if (char, zVariant) in decompositionDict:
                    # try all decompositions of this character, all need to
                    #   return the same count for sake of consistency
                    for decomposition in decompositionDict[(char, zVariant)]:
                        try:
                            accumulatedStrokeCount = 0

                            for entry in decomposition:
                                if type(entry) == types.TupleType:
                                    component, componentZVariant = entry

                                    accumulatedStrokeCount += \
                                        self.getStrokeCount(component,
                                            componentZVariant, strokeCountDict,
                                            unihanStrokeCountDict,
                                            decompositionDict)

                            if lastStrokeCount != None \
                                and lastStrokeCount != accumulatedStrokeCount:
                                # different stroke counts taken from different
                                #   decompositions, can't build at all
                                raise ValueError("ambiguous stroke count " \
                                    + "information, due to various stroke " \
                                    + "count sources for " \
                                    + repr((char, ZVariant)))
                            else:
                                # first run or equal to previous calculation
                                lastStrokeCount = accumulatedStrokeCount

                        except exception.NoInformationError:
                            continue

                if lastStrokeCount != None:
                    strokeCountDict[(char, zVariant)] = lastStrokeCount
                else:
                    # couldn't get stroke counts from components, check fallback
                    #   resources
                    if (char, 0) in strokeCountDict:
                        # own sources have info for fallback zVariant
                        strokeCountDict[(char, zVariant)] \
                            = strokeCountDict[(char, 0)]

                    elif char in unihanStrokeCountDict:
                        # take Unihan info
                        strokeCountDict[(char, zVariant)] \
                            = unihanStrokeCountDict[char]

                    else:
                        strokeCountDict[(char, zVariant)] = None

            if strokeCountDict[(char, zVariant)] == None:
                raise exception.NoInformationError(
                    "missing stroke count information")
            else:
                return strokeCountDict[(char, zVariant)]

        def __iter__(self):
            """Provides one entry per character, z-Variant and locale subset."""
            # handle chars from own data first
            strokeCountDict = {}
            for entry in self.preferredBuilder:
                yield entry

                # save stroke count for later processing, prefer Z-variant 0
                key = (entry['ChineseCharacter'], entry['ZVariant'])
                strokeCountDict[key] = entry['StrokeCount']

            # now get stroke counts from Unihan table

            # get Unihan table stroke count data
            unihanStrokeCountDict = {}
            for char, strokeCount in self.tableEntries:
                if (char, 0) not in strokeCountDict:
                    unihanStrokeCountDict[char] = strokeCount

            # finally fill up with characters from Unihan; proper glyph
            #   information missing though in some cases.

            # remove glyphs we already have an entry for
            self.characterSet.difference_update(strokeCountDict.keys())

            # get character decompositions
            decompositionDict = self.cjk.getDecompositionEntriesDict()

            for char, zVariant in self.characterSet:
                warningZVariants = []
                try:
                    # build stroke count from mixed source
                    strokeCount = self.getStrokeCount(char, zVariant,
                        strokeCountDict, unihanStrokeCountDict,
                        decompositionDict)

                    yield {'ChineseCharacter': char, 'ZVariant': zVariant,
                        'StrokeCount': strokeCount}
                except ValueError, e:
                    warningZVariants.append(zVariant)
                except exception.NoInformationError:
                    pass

                if not self.quiet and warningZVariants:
                    warn("ambiguous stroke count information (mixed sources) " \
                        "for character '" + char + "' for Z-variant(s) '" \
                        + ''.join([str(z) for z in warningZVariants]) + "'")

    DEPENDS = ['CharacterDecomposition', 'StrokeOrder', 'Unihan']
    COLUMN_SOURCE = 'kTotalStrokes'

    def getGenerator(self):
        characterSet = set(self.db.select('CharacterDecomposition',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        characterSet.update(self.db.select('StrokeOrder',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        preferredBuilder = \
            CombinedStrokeCountBuilder.StrokeCountGenerator(self.db,
                characterSet, self.quiet)
        # get main builder
        tableEntries = self.db.select('Unihan', ['ChineseCharacter',
            self.COLUMN_SOURCE], {self.COLUMN_SOURCE: 'IS NOT NULL'})

        # get characters to build combined stroke count for. Some characters
        #   from the CharacterDecomposition table might not have a stroke count
        #   entry in Unihan though their components do have.
        characterSet.update([(char, 0) for char, totalCount in tableEntries])

        return CombinedStrokeCountBuilder.CombinedStrokeCountGenerator(self.db,
            characterSet, tableEntries, preferredBuilder, self.quiet)


class CharacterComponentLookupBuilder(EntryGeneratorBuilder):
    """
    Builds a mapping between characters and their components.
    """
    class CharacterComponentGenerator:
        """Generates the component to character mapping."""

        def __init__(self, dbConnectInst, characterSet):
            """
            Initialises the CharacterComponentGenerator.

            @type dbConnectInst: instance
            @param dbConnectInst: instance of a L{DatabaseConnector}
            @type characterSet: set
            @param characterSet: set of characters to generate the table for
            """
            self.characterSet = characterSet
            self.cjk = characterlookup.CharacterLookup(
                dbConnectInst=dbConnectInst)

        def getComponents(self, char, zVariant, decompositionDict,
            componentDict):
            """
            Gets all character components for the given glyph.

            @type char: str
            @param char: Chinese character
            @type zVariant: int
            @param zVariant: Z-variant of character
            @rtype: set
            @return: all components of the character
            """
            if (char, zVariant) not in componentDict:
                componentDict[(char, zVariant)] = set()

                if (char, zVariant) in decompositionDict:
                    for decomposition in decompositionDict[(char, zVariant)]:
                        componentDict[(char, zVariant)].update(
                            [entry for entry in decomposition \
                                if type(entry) == types.TupleType])

            componentSet = set()
            for component, componentZVariant in componentDict[(char, zVariant)]:
                componentSet.add((component, componentZVariant))
                # get sub-components
                componentSet.update(self.getComponents(component,
                    componentZVariant, decompositionDict, componentDict))

            return componentSet

        def __iter__(self):
            """Provides the component entries."""
            decompositionDict = self.cjk.getDecompositionEntriesDict()
            componentDict = {}
            for char, zVariant in self.characterSet:
                for component, componentZVariant \
                    in self.getComponents(char, zVariant, decompositionDict,
                        componentDict):
                    yield {'ChineseCharacter': char, 'ZVariant': zVariant,
                        'Component': component,
                        'ComponentZVariant': componentZVariant}

    PROVIDES = 'ComponentLookup'
    DEPENDS = ['CharacterDecomposition']

    COLUMNS = ['ChineseCharacter', 'ZVariant', 'Component', 'ComponentZVariant']
    PRIMARY_KEYS = COLUMNS
    INDEX_KEYS = [['Component']]
    COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)', 'ZVariant': 'INTEGER',
        'Component': 'VARCHAR(1)', 'ComponentZVariant': 'INTEGER'}

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CharacterComponentLookupBuilder, self).__init__(dataPath,
            dbConnectInst, quiet)
        characterSet = set(self.db.select('CharacterDecomposition',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        self.ENTRY_GENERATOR = \
            CharacterComponentLookupBuilder.CharacterComponentGenerator(self.db,
                characterSet)


class CharacterRadicalStrokeCountBuilder(EntryGeneratorBuilder):
    """
    Builds a mapping between characters and their radical with stroke count of
    residual components.

    This class can be extended by inheriting
    L{CharacterRadicalStrokeCountGenerator} and overwriting
    L{CharacterRadicalStrokeCountGenerator.getFormRadicalIndex()} to implement
    which forms should be regarded as radicals as well as
    L{CharacterRadicalStrokeCountGenerator.filterForms()} to filter entries
    before creation.
    """
    class CharacterRadicalStrokeCountGenerator:
        """Generates the character to radical/residual stroke count mapping."""

        def __init__(self, dbConnectInst, characterSet, quiet=False):
            """
            Initialises the CharacterRadicalStrokeCountGenerator.

            @type dbConnectInst: instance
            @param dbConnectInst: instance of a L{DatabaseConnector}
            @type characterSet: set
            @param characterSet: set of characters to generate the table for
            @type quiet: bool
            @param quiet: if true no status information will be printed to
                stderr
            """
            self.characterSet = characterSet
            self.quiet = quiet
            self.cjk = characterlookup.CharacterLookup(
                dbConnectInst=dbConnectInst)
            self.radicalForms = None

        def getFormRadicalIndex(self, form):
            """
            Returns the Kangxi radical index for the given component.

            @type form: str
            @param form: component
            @rtype: int
            @return: radical index of the given radical form.
            """
            if self.radicalForms == None:
                self.radicalForms = {}
                for loc in ['T', 'C', 'J', 'K', 'V']:
                    for radicalIdx in range(1, 215):
                        for f in \
                            self.cjk.getKangxiRadicalRepresentativeCharacters(
                                radicalIdx, loc):
                            self.radicalForms[f] = radicalIdx

            if form not in self.radicalForms:
                return None
            return self.radicalForms[form]

        def filterForms(self, formSet):
            u"""
            Filters the set of given radical form entries to return only one
            single occurrence of a radical.

            @type formSet: set of dict
            @param formSet: radical/residual stroke count entries as generated
                by L{getEntries()}.
            @rtype: set of dict
            @return: subset of input
            @todo Lang: On multiple occurrences of same radical (may be in
                different forms): Which one to choose? Implement to turn down
                unwanted forms.
            """
            return formSet

        def getEntries(self, char, zVariant, strokeCountDict, decompositionDict,
            entriesDict):
            u"""
            Gets all radical/residual stroke count combinations from the given
            decomposition.

            @rtype: list
            @return: all radical/residual stroke count combinations for the
                character
            @raise ValueError: if IDS is malformed or ambiguous residual stroke
                count is calculated
            @todo Fix:  Remove validity check, only needed as long
                decomposition entries aren't checked against stroke order
                entries.
            """
            def getCharLayout(mainCharacterLayout, mainLayoutPosition,
                subCharLayout, subLayoutPosition):
                u"""
                Returns the character layout for the radical form within the
                component with layout subCharLayout itself belonging to a parent
                char with layout mainCharacterLayout.
                E.g. 鸺 can be decomposed into ⿰休鸟 and 休 can be furthermore
                decomposed into ⿰亻木. 亻 is found in a lower layer of
                decomposition, but as the structure of 休 and 鸺 are the same,
                and 亻 is on the left side of 休 which is on the left side of 鸺
                one can deduce 亻 as being on the utmost left side of 鸺. Thus
                (⿰, 0) would be returned.
                """
                specialReturn = {
                    (u'⿰', 0, u'⿰', 0): (u'⿰', 0),
                    (u'⿰', 1, u'⿰', 1): (u'⿰', 1),
                    (u'⿱', 0, u'⿱', 0): (u'⿱', 0),
                    (u'⿱', 1, u'⿱', 1): (u'⿱', 1),
                    (u'⿲', 0, u'⿲', 0): (u'⿰', 0),
                    (u'⿲', 2, u'⿲', 2): (u'⿰', 1),
                    (u'⿳', 0, u'⿳', 0): (u'⿱', 0),
                    (u'⿳', 2, u'⿳', 2): (u'⿱', 0),
                    (u'⿲', 0, u'⿰', 0): (u'⿰', 0),
                    (u'⿲', 2, u'⿰', 1): (u'⿰', 1),
                    (u'⿰', 0, u'⿲', 0): (u'⿰', 0),
                    (u'⿰', 1, u'⿲', 1): (u'⿰', 1),
                    (u'⿳', 0, u'⿱', 0): (u'⿱', 0),
                    (u'⿳', 2, u'⿱', 1): (u'⿱', 1),
                    (u'⿱', 0, u'⿳', 0): (u'⿱', 0),
                    (u'⿱', 1, u'⿳', 2): (u'⿱', 1),
                    }
                entry = (mainCharacterLayout, mainLayoutPosition, subCharLayout,
                    subLayoutPosition)
                if entry in specialReturn:
                    return specialReturn[entry]
                elif subCharLayout == u'⿻':
                    # default value for complex position
                    return (u'⿻', 0)
                elif mainCharacterLayout == None:
                    # main layout
                    return subCharLayout, subLayoutPosition
                else:
                    # radical component has complex position
                    return (u'⿻', 0)

            # if no decomposition available then there is nothing to do
            if (char, zVariant) not in decompositionDict:
                return []

            if (char, zVariant) not in entriesDict:
                entriesDict[(char, zVariant)] = set()

                for decomposition in decompositionDict[(char, zVariant)]:
                    componentRadicalForms = []
                    # if a radical is found in a subcharacter an entry is added
                    #   containing the radical form, its variant, the stroke
                    #   count of residual characters in this main character and
                    #   it's position in the main char (e.g. for 鸺 contains
                    #   Form 鸟, Z-variant 0, residual stroke count 6, main
                    #   layout ⿰ and position 1 (right side), as 亻 and 木
                    #   together form the residual components, and the
                    #   simplified structure of 鸺 applies to a left/right
                    #   model, with 鸟 being at the 2nd position.

                    # get all radical entries

                    # layout stack which holds the IDS operators and a position
                    #   in the IDS operator itself for each Chinese character
                    layoutStack = [(None, None)]

                    for entry in decomposition:
                        try:
                            layout, position = layoutStack.pop()
                        except IndexError:
                            raise ValueError("malformed IDS for character '" \
                                + mainChar + "'")

                        if type(entry) != types.TupleType:
                            # ideographic description character found, derive
                            #   layout from IDS and parent character and store
                            #   in layout stack to be consumed by following
                            #   Chinese characters
                            if self.cjk.isTrinaryIDSOperator(entry):
                                posRange = [2, 1, 0]
                            else:
                                posRange = [1, 0]

                            for componentPos in posRange:
                                # append to stack one per following element,
                                #   adapt layout to parent one
                                layoutStack.append(getCharLayout(layout,
                                    position, entry, componentPos))
                        else:
                            # Chinese character found
                            componentChar, componentZVariant = entry

                            # create entries for this component
                            radicalIndex \
                                = self.getFormRadicalIndex(componentChar)
                            if radicalIndex != None:
                                # main component is radical, no residual stroke
                                #   count, save relative position in main
                                #   character
                                componentRadicalForms.append(
                                    {'Component': entry,
                                    'Form': componentChar,
                                    'Z-variant': componentZVariant,
                                    'ResidualStrokeCount': 0,
                                    'CharacterLayout': layout,
                                    'RadicalIndex': radicalIndex,
                                    'RadicalPosition': position})

                            # get all radical forms for this entry from
                            #   sub-components
                            for radicalEntry in self.getEntries(componentChar,
                                componentZVariant, strokeCountDict,
                                decompositionDict, entriesDict):

                                # get layout for this character wrt parent char
                                charLayout, charPosition = getCharLayout(layout,
                                    position, radicalEntry['CharacterLayout'],
                                    radicalEntry['RadicalPosition'])
                                componentEntry = radicalEntry.copy()
                                componentEntry['Component'] = entry
                                componentEntry['CharacterLayout'] = charLayout
                                componentEntry['RadicalPosition'] = charPosition
                                componentRadicalForms.append(componentEntry)

                    # for each character get the residual characters first
                    residualCharacters = {}
                    charactersSeen = []
                    for entry in decomposition:
                        # get Chinese characters
                        if type(entry) == types.TupleType:
                            # fill up already seen characters with next found
                            for seenEntry in residualCharacters:
                                residualCharacters[seenEntry].append(entry)

                            # set current character to already seen ones
                            residualCharacters[entry] = charactersSeen[:]

                            charactersSeen.append(entry)

                    # calculate residual stroke count and create entries
                    for componentEntry in componentRadicalForms:
                        # residual stroke count is the sum of the component's
                        #   residual stroke count (with out radical) and count
                        #   of the other components
                        for entry in \
                            residualCharacters[componentEntry['Component']]:

                            if entry not in strokeCountDict:
                                break

                            componentEntry['ResidualStrokeCount'] \
                                += strokeCountDict[entry]
                        else:
                            # all stroke counts available
                            del componentEntry['Component']
                            entriesDict[(char, zVariant)].add(
                                frozenset(componentEntry.items()))

                # validity check # TODO only needed as long decomposition and
                #   stroke order entries aren't checked for validity
                seenEntriesDict = {}
                for entry in [dict(d) for d in entriesDict[(char, zVariant)]]:
                    keyEntry = (entry['Form'], entry['Z-variant'],
                        entry['CharacterLayout'], entry['RadicalIndex'],
                        entry['RadicalPosition'])
                    if keyEntry in seenEntriesDict \
                        and seenEntriesDict[keyEntry] \
                            != entry['ResidualStrokeCount']:
                        raise ValueError("ambiguous residual stroke count for " \
                            + "character '" + mainChar + "' with entry '" \
                            + "', '".join(list([unicode(column) \
                                for column in keyEntry])) \
                            + "': '" + str(seenEntriesDict[keyEntry]) + "'/'" \
                            + str(entry['ResidualStrokeCount']) + "'")
                    seenEntriesDict[keyEntry] = entry['ResidualStrokeCount']

            # filter forms, i.e. for multiple radical occurrences prefer one
            return self.filterForms(
                [dict(d) for d in entriesDict[(char, zVariant)]])

        def __iter__(self):
            """Provides the radical/stroke count entries."""
            strokeCountDict = self.cjk.getStrokeCountDict()
            decompositionDict = self.cjk.getDecompositionEntriesDict()
            entryDict = {}

            for char, zVariant in self.characterSet:
                if self.cjk.isRadicalChar(char):
                    # ignore Unicode radical forms
                    continue

                for entry in self.getEntries(char, zVariant, strokeCountDict,
                    decompositionDict, entryDict):

                    yield [char, zVariant, entry['RadicalIndex'], entry['Form'],
                        entry['Z-variant'], entry['CharacterLayout'],
                        entry['RadicalPosition'], entry['ResidualStrokeCount']]

    PROVIDES = 'CharacterRadicalResidualStrokeCount'
    DEPENDS = ['CharacterDecomposition', 'StrokeCount', 'KangxiRadical',
        'KangxiRadicalIsolatedCharacter', 'RadicalEquivalentCharacter',
        'CharacterKangxiRadical']

    COLUMNS = ['ChineseCharacter', 'ZVariant', 'RadicalIndex', 'RadicalForm',
        'RadicalZVariant', 'MainCharacterLayout', 'RadicalRelativePosition',
        'ResidualStrokeCount']
    PRIMARY_KEYS = ['ChineseCharacter', 'ZVariant', 'RadicalForm',
        'RadicalZVariant', 'MainCharacterLayout', 'RadicalRelativePosition']
    COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)', 'RadicalIndex': 'INTEGER',
        'RadicalForm': 'VARCHAR(1)', 'ZVariant': 'INTEGER',
        'RadicalZVariant': 'INTEGER', 'MainCharacterLayout': 'VARCHAR(1)',
        'RadicalRelativePosition': 'INTEGER', 'ResidualStrokeCount': 'INTEGER'}

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CharacterRadicalStrokeCountBuilder, self).__init__(dataPath,
            dbConnectInst, quiet)
        # get all characters we have component information for
        characterSet = set(self.db.select('CharacterDecomposition',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True)) 
        self.ENTRY_GENERATOR = CharacterRadicalStrokeCountBuilder\
            .CharacterRadicalStrokeCountGenerator(self.db, characterSet,
                self.quiet)


class CharacterResidualStrokeCountBuilder(EntryGeneratorBuilder):
    """
    Builds a mapping between characters and their residual stroke count when
    splitting of the radical form. This is stripped off information gathered
    from table C{CharacterRadicalStrokeCount}.
    """
    class ResidualStrokeCountExtractor:
        """
        Generates the character to residual stroke count mapping from the
        C{CharacterRadicalResidualStrokeCount} table.
        """
        def __init__(self, dbConnectInst, characterSet):
            """
            Initialises the ResidualStrokeCountExtractor.

            @type dbConnectInst: instance
            @param dbConnectInst: instance of a L{DatabaseConnector}
            @type characterSet: set
            @param characterSet: set of characters to generate the table for
            """
            self.characterSet = characterSet
            self.cjk = characterlookup.CharacterLookup(
                dbConnectInst=dbConnectInst)

        def getEntries(self, char, zVariant, radicalDict):
            u"""
            Gets a list of radical residual entries. For multiple radical
            occurrences (e.g. 伦) only returns the residual stroke count for the
            "main" radical form.

            @type char: str
            @param char: Chinese character
            @type zVariant: int
            @param zVariant: I{Z-variant} of given character
            @rtype: list of tuple
            @return: list of residual stroke count entries
            @todo Lang: Implement, find a good algorithm to turn down unwanted
                forms, don't just choose random one. See the following list::

                >>> from cjklib import characterlookup
                >>> cjk = characterlookup.CharacterLookup()
                >>> for char in cjk.db.selectSoleValue('CharacterRadicalResidualStrokeCount',
                ...     'ChineseCharacter', distinctValues=True):
                ...     try:
                ...         entries = cjk.getCharacterKangxiRadicalResidualStrokeCount(char, 'C')
                ...         lastEntry = entries[0]
                ...         for entry in entries[1:]:
                ...             # print if diff. radical forms and diff. residual stroke count
                ...             if lastEntry[0] != entry[0] and lastEntry[2] != entry[2]:
                ...                 print char
                ...                 break
                ...             lastEntry = entry
                ...     except:
                ...         pass
                ...
                渌
                犾
                玺
                珏
                缧
                >>> cjk.getCharacterKangxiRadicalResidualStrokeCount(u'缧')
                [(u'\u7cf8', 0, u'\u2ffb', 0, 8), (u'\u7e9f', 0, u'\u2ff0', 0, 11)]
            """
            # filter entries to return only the main radical form
            # TODO provisional solution, take first entry per radical index
            filteredEntries = []
            for radicalIdx in radicalDict[(char, zVariant)]:
                _, _, _, _, residualStrokeCount \
                    = radicalDict[(char, zVariant)][radicalIdx][0]
                filteredEntries.append((radicalIdx, residualStrokeCount))

            return filteredEntries

        def __iter__(self):
            """Provides one entry per character, z-Variant and locale subset."""
            radicalDict = self.cjk.getCharacterRadicalResidualStrokeCountDict()
            for char, zVariant in self.characterSet:
                for radicalIndex, residualStrokeCount in self.getEntries(char,
                    zVariant, radicalDict):
                    yield [char, zVariant, radicalIndex, residualStrokeCount]

    PROVIDES = 'CharacterResidualStrokeCount'
    DEPENDS = ['CharacterRadicalResidualStrokeCount']

    COLUMNS = ['ChineseCharacter', 'ZVariant', 'RadicalIndex',
        'ResidualStrokeCount']
    PRIMARY_KEYS = ['ChineseCharacter', 'ZVariant', 'RadicalIndex']
    INDEX_KEYS = [['RadicalIndex']]
    COLUMN_TYPES = {'ChineseCharacter': 'VARCHAR(1)', 'RadicalIndex': 'INTEGER',
        'ZVariant': 'INTEGER', 'ResidualStrokeCount': 'INTEGER'}

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(CharacterResidualStrokeCountBuilder, self).__init__(dataPath,
            dbConnectInst, quiet)
        self.ENTRY_GENERATOR = self.getGenerator()

    def getGenerator(self):
        characterSet = set(self.db.select('CharacterRadicalResidualStrokeCount',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        return CharacterResidualStrokeCountBuilder.ResidualStrokeCountExtractor(
            self.db, characterSet)


class CombinedCharacterResidualStrokeCountBuilder(
    CharacterResidualStrokeCountBuilder):
    """
    Builds a mapping between characters and their residual stroke count when
    splitting of the radical form. Includes stroke count data from the Unihan
    database to make up for missing data in own data files.
    """
    class CombinedResidualStrokeCountExtractor:
        """
        Generates the character to residual stroke count mapping.
        """
        def __init__(self, tableEntries, preferredBuilder, quiet=False):
            """
            Initialises the CombinedResidualStrokeCountExtractor.

            @type tableEntries: list of list
            @param tableEntries: list of characters with Z-variant
            @type preferredBuilder: instance
            @param preferredBuilder: TableBuilder which forms are preferred over
                entries from the Unihan table
            @type quiet: bool
            @param quiet: if true no status information will be printed
            """
            self.RADICAL_REGEX = re.compile(ur"(\d+)\.(\d+)")
            self.tableEntries = tableEntries
            self.preferredBuilder = preferredBuilder
            self.quiet = quiet

        def __iter__(self):
            """Provides one entry per character and z-Variant."""
            # handle chars from own data first
            seenCharactersSet = set()
            for entry in self.preferredBuilder:
                yield entry
                char = entry[0]
                radicalIdx = entry[2]
                seenCharactersSet.add((char, radicalIdx))

            # now fill up with characters from Unihan, Z-variant missing though
            for char, radicalStroke in self.tableEntries:
                matchObj = self.RADICAL_REGEX.match(radicalStroke)
                if matchObj:
                    try:
                        radicalIndex = int(matchObj.group(1))
                        residualStrokeCount = int(matchObj.group(2))
                        if (char, radicalIndex) not in seenCharactersSet:
                            yield [char, 0, radicalIndex, residualStrokeCount]
                    except ValueError:
                        if not self.quiet:
                            warn("unable to read radical information of " \
                                + "character '" + character + "': '" \
                                    + radicalStroke + "'")
                elif not self.quiet:
                    warn("unable to read radical information of character '" \
                        + character + "': '" + radicalStroke + "'")

    DEPENDS = ['CharacterRadicalResidualStrokeCount', 'Unihan']
    COLUMN_SOURCE = 'kRSKangXi'

    def getGenerator(self):
        characterSet = set(self.db.select('CharacterRadicalResidualStrokeCount',
            ['ChineseCharacter', 'ZVariant'], distinctValues=True))
        preferredBuilder = CombinedCharacterResidualStrokeCountBuilder\
            .ResidualStrokeCountExtractor(self.db, characterSet)
        # get main builder
        tableEntries = self.db.select('Unihan', ['ChineseCharacter',
            self.COLUMN_SOURCE], {self.COLUMN_SOURCE: 'IS NOT NULL'})
        return CombinedCharacterResidualStrokeCountBuilder\
            .CombinedResidualStrokeCountExtractor(tableEntries,
                preferredBuilder, self.quiet)

#}
#{ Dictionary builder

class EDICTFormatBuilder(EntryGeneratorBuilder):
    """
    Provides an abstract class for loading EDICT formatted dictionaries.

    One column will be provided for the headword, one for the reading (in EDICT
    that is the Kana) and one for the translation.
    """
    class TableGenerator:
        """Generates the dictionary entries."""

        def __init__(self, fileHandle, quiet=False, entryRegex=None,
            columns=None, filterFunc=None):
            """
            Initialises the TableGenerator.

            @type fileHandle: file
            @param fileHandle: handle of file to read from
            @type quiet: bool
            @param quiet: if true no status information will be printed
            @type entryRegex: instance
            @param entryRegex: regular expression object for entry pattern
            @type columns: list of str
            @param columns: column names of generated data
            @type filterFunc: function
            @param filterFunc: function used to filter entry content
            """
            self.fileHandle = fileHandle
            self.quiet = quiet
            self.columns = columns
            self.filterFunc = filterFunc
            if entryRegex:
                self.entryRegex = entryRegex
            else:
                # the EDICT dictionary itself omits the KANA in brackets if
                # the headword is already a KANA word
                # KANJI [KANA] /english_1/english_2/.../
                # KANA /english_1/.../
                self.entryRegex = \
                    re.compile(r'\s*(\S+)\s*(?:\[([^\]]*)\]\s*)?(/.*/)\s*$')

        def __iter__(self):
            """Provides the dictionary entries."""
            a = 0
            for line in self.fileHandle:
                # ignore comments
                if line.lstrip().startswith('#'):
                    continue
                # parse line
                matchObj = self.entryRegex.match(line)
                if not matchObj:
                    if line.strip() != '':
                        warn("error reading line '" + line + "'")
                    continue
                # get entries
                entry = matchObj.groups()
                if self.columns:
                    entry = dict([(self.columns[idx], cell) for idx, cell \
                        in enumerate(entry)])
                if self.filterFunc:
                    entry = self.filterFunc(entry)
                yield entry

    COLUMNS = ['Headword', 'Reading', 'Translation']
    PRIMARY_KEYS = []
    INDEX_KEYS = [['Headword'], ['Reading']]
    COLUMN_TYPES = {'Headword': 'VARCHAR(255)', 'Reading': 'VARCHAR(255)',
        'Translation': 'TEXT'}

    FULLTEXT_COLUMNS = ['Translation']
    """Column names which shall be fulltext searchable."""
    FILE_NAMES = None
    """Names of file containing the edict formated dictionary."""
    ZIP_CONTENT_NAME = None
    """
    Name of file in the zipped archive containing the edict formated dictionary.
    """
    ENCODING = 'utf-8'
    """Encoding of the dictionary file."""
    ENTRY_REGEX = None
    """
    Regular Expression matching a dictionary entry. Needs to be overwritten if
    not strictly follows the EDICT format.
    """
    IGNORE_LINES = 0
    """Number of starting lines to ignore."""
    FILTER = None
    """Filter to apply to the read entry before writing to table."""

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(EDICTFormatBuilder, self).__init__(dataPath, dbConnectInst, quiet)
        # get file handle
        import os.path as path
        filePath = self.findFile(self.FILE_NAMES)
        handle = self.getFileHandle(filePath, self.ZIP_CONTENT_NAME)
        if not self.quiet:
            warn("Reading table from file '" + filePath + "'")
        # ignore starting lines
        for i in range(0, self.IGNORE_LINES):
            handle.readline()
        # create generator
        self.ENTRY_GENERATOR = EDICTFormatBuilder.TableGenerator(handle,
            self.quiet, self.ENTRY_REGEX, self.COLUMNS, self.FILTER)

    def getFileHandle(self, filePath, compressedContent):
        """
        Returns a handle to the give file.

        The file can be either normal content, zip, tar, .tar.gz, tar.bz2

        @type filePath: str
        @param filePath: path of file
        @type compressedContent: str
        @param compressedContent: file name to extract from compressed file, if
            filePath represents a container format
        @rtype: file
        @return: handle to file's content
        """
        import zipfile
        import tarfile
        if zipfile.is_zipfile(filePath):
            z = zipfile.ZipFile(filePath, 'r')
            return StringIO.StringIO(z.read(compressedContent)\
                .decode(self.ENCODING))
        elif tarfile.is_tarfile(filePath):
            import StringIO
            mode = ''
            if filePath.endswith('bz2'):
                mode = ':bz2'
            elif filePath.endswith('gz'):
                mode = ':gz'
            z = tarfile.open(filePath, 'r' + mode)
            file = z.extractfile(compressedContent)
            return StringIO.StringIO(file.read().decode(self.ENCODING))
        elif filePath.endswith('.gz'):
            import gzip
            import StringIO
            z = gzip.GzipFile(filePath, 'r')
            return StringIO.StringIO(z.read().decode(self.ENCODING))
        else:
            import codecs
            return codecs.open(filePath, 'r', self.ENCODING)

    def build(self):
        """
        Build the table provided by the TableBuilder.

        A search index is created to allow for fulltext searching.
        """
        hasFTS3 = self.target == 'SQLite' and testFTS3(self.db.getCursor())
        if not hasFTS3:
            # get drop table statement
            dropStatement = getDropTableStatement(self.PROVIDES)
            # get create statement
            createStatement = getCreateTableStatement(self.PROVIDES,
                self.COLUMNS, self.COLUMN_TYPES,
                primaryKeyColumns=self.PRIMARY_KEYS)
        else:
            # get drop table statement
            dropStatement = getFTS3DropTableStatement(self.PROVIDES)
            # get create statement
            createStatement = getFTS3CreateTableStatement(self.PROVIDES,
                self.COLUMNS, self.COLUMN_TYPES,
                primaryKeyColumns=self.PRIMARY_KEYS,
                fullTextColumns=self.FULLTEXT_COLUMNS)

        if self.target == 'dump':
            output(dropStatement)
            output(createStatement)
        elif self.target != 'SQLite':
            self.db.getCursor().execute(dropStatement)
            self.db.getCursor().execute(createStatement)
        else:
            self.db.getCursor().execute('PRAGMA synchronous = OFF;')
            self.db.getCursor().executescript(dropStatement)
            self.db.getCursor().executescript(createStatement)

        if not hasFTS3:
            # write table content
            for newEntry in self.ENTRY_GENERATOR:
                insertStatement = getInsertStatement(self.PROVIDES, newEntry)
                if self.target == 'dump':
                    output(insertStatement)
                else:
                    self.db.getCursor().execute(insertStatement)
        else:
            # write table content
            for newEntry in self.ENTRY_GENERATOR:
                insertStatement = getFTS3InsertStatement(self.PROVIDES,
                    newEntry, fullTextColumns=self.FULLTEXT_COLUMNS)
                self.db.getCursor().executescript(insertStatement)

        if self.target != 'dump':
            self.db.getConnection().commit()
        if self.target == 'SQLite':
            self.db.getCursor().execute('PRAGMA synchronous = FULL;')

        # get create index statement
        if not hasFTS3:
            indexStatements = getCreateIndexStatement(self.PROVIDES,
                self.INDEX_KEYS)
        else:
            indexStatements = getFTS3CreateIndexStatement(self.PROVIDES,
                self.INDEX_KEYS)
        if self.target == 'dump':
            for statement in indexStatements:
                output(statement)
        else:
            for statement in indexStatements:
                self.db.getCursor().execute(statement)


class WordIndexBuilder(EntryGeneratorBuilder):
    """
    Builds a translation word index for a given dictionary.

    Searching for a word will return a headword and reading. This allows to find
    several dictionary entries with same headword and reading, with only one
    including the translation word.

    @todo Fix:  Word regex is specialised for HanDeDict.
    @todo Fix:  Using a row_id for joining instead of Headword(Traditional) and
        Reading would maybe speed up table joins. Needs a workaround to include
        multiple rows for one actual headword entry though.
    """
    class WordEntryGenerator:
        """Generates words for a list of dictionary entries."""

        def __init__(self, entries):
            """
            Initialises the WordEntryGenerator.

            @type entries: list of tuple
            @param entries: a list of headword and its translation
            """
            self.entries = entries
            # TODO this regex is adapted to HanDeDict, might be not general
            #   enough
            self.wordRegex = re.compile(r'\([^\)]+\)|' \
                + r'(?:; Bsp.: [^/]+?--[^/]+)|([^/,\(\)\[\]\!\?]+)')

        def __iter__(self):
            """Provides all data of one word per entry."""
            # remember seen entries to prevent double entries
            seenWordEntries = set()
            newEntryDict = {}

            for headword, reading, translation in self.entries:
                newEntryDict['Headword'] = headword
                newEntryDict['Reading'] = reading
                for word in self.wordRegex.findall(translation):
                    word = word.strip().lower()
                    if not word:
                        continue
                    if word \
                        and (headword, reading, word) not in seenWordEntries:
                        seenWordEntries.add((headword, reading, word))
                        newEntryDict['Word'] = word
                        yield newEntryDict

    COLUMNS = ['Headword', 'Reading', 'Word']
    COLUMN_TYPES = {'Headword': 'VARCHAR(255)', 'Reading': 'VARCHAR(255)',
        'Word': 'VARCHAR(255)'}
    INDEX_KEYS = [['Word']]

    TABLE_SOURCE = None
    """Dictionary source"""
    HEADWORD_SOURCE = 'Headword'
    """Source of headword"""

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        super(WordIndexBuilder, self).__init__(dataPath, dbConnectInst, quiet)

        entries = self.db.select(self.TABLE_SOURCE, [self.HEADWORD_SOURCE,
            'Reading', 'Translation'])

        self.ENTRY_GENERATOR = WordIndexBuilder.WordEntryGenerator(entries)


class EDICTBuilder(EDICTFormatBuilder):
    """
    Builds the EDICT dictionary.
    """
    PROVIDES = 'EDICT'
    FILE_NAMES = ['edict.gz', 'edict.zip', 'edict']
    ZIP_CONTENT_NAME = 'edict'
    ENCODING = 'euc-jp'
    IGNORE_LINES = 1


class EDICTWordIndexBuilder(WordIndexBuilder):
    """
    Builds the word index of the EDICT dictionary.
    """
    PROVIDES = 'EDICT_Words'
    DEPENDS = ['EDICT']
    TABLE_SOURCE = 'EDICT'


class CEDICTFormatBuilder(EDICTFormatBuilder):
    """
    Provides an abstract class for loading CEDICT formatted dictionaries.

    Two column will be provided for the headword (one for traditional and
    simplified writings each), one for the reading (e.g. in CEDICT Pinyin) and
    one for the translation.
    @todo Impl: Proper collation for Translation and Reading columns.
    """
    COLUMNS = ['HeadwordTraditional', 'HeadwordSimplified', 'Reading',
        'Translation']
    INDEX_KEYS = [['HeadwordTraditional'], ['HeadwordSimplified'], ['Reading']]
    COLUMN_TYPES = {'HeadwordTraditional': 'VARCHAR(255)',
        'HeadwordSimplified': 'VARCHAR(255)', 'Reading': 'VARCHAR(255)',
        'Translation': 'TEXT'}

    def __init__(self, dataPath, dbConnectInst, quiet=False):
        self.ENTRY_REGEX = \
            re.compile(r'\s*(\S+)(?:\s+(\S+))?\s*\[([^\]]*)\]\s*(/.*/)\s*$')
        super(CEDICTFormatBuilder, self).__init__(dataPath, dbConnectInst,
            quiet)


class CEDICTBuilder(CEDICTFormatBuilder):
    """
    Builds the CEDICT dictionary.
    """
    def filterUmlaut(self, entry):
        """
        Converts the C{'u:'} to C{'ü'}.

        @type entry: tuple
        @param entry: a dictionary entry
        @rtype: tuple
        @return: the given entry with corrected ü-voul
        """
        if type(entry) == type({}):
            entry['Reading'] = entry['Reading'].replace('u:', u'ü')
            return entry
        else:
            trad, simp, reading, translation = entry
            reading = reading.replace('u:', u'ü')
            return [trad, simp, reading, translation]

    PROVIDES = 'CEDICT'
    FILE_NAMES = ['cedict_1_0_ts_utf-8_mdbg.zip',
        'cedict_1_0_ts_utf-8_mdbg.txt.gz', 'cedictu8.zip', 'cedict_ts.u8']
    ZIP_CONTENT_NAME = 'cedict_ts.u8'
    ENCODING = 'utf-8'
    FILTER = filterUmlaut


class CEDICTWordIndexBuilder(WordIndexBuilder):
    """
    Builds the word index of the CEDICT dictionary.
    """
    PROVIDES = 'CEDICT_Words'
    DEPENDS = ['CEDICT']
    TABLE_SOURCE = 'CEDICT'
    HEADWORD_SOURCE = 'HeadwordTraditional'


class CEDICTGRBuilder(EDICTFormatBuilder):
    """
    Builds the CEDICT-GR dictionary.
    """
    PROVIDES = 'CEDICTGR'
    FILE_NAMES = ['cedictgr.zip', 'cedictgr.b5']
    ZIP_CONTENT_NAME = 'cedictgr.b5'
    ENCODING = 'big5hkscs'


class CEDICTGRWordIndexBuilder(WordIndexBuilder):
    """
    Builds the word index of the CEDICT-GR dictionary.
    """
    PROVIDES = 'CEDICTGR_Words'
    DEPENDS = ['CEDICTGR']
    TABLE_SOURCE = 'CEDICTGR'
    HEADWORD_SOURCE = 'Headword'


class HanDeDictBuilder(CEDICTFormatBuilder):
    """
    Builds the HanDeDict dictionary.
    @todo Fix: Improve file name handling to find older downloads of HanDeDict.
    """
    def filterSpacing(self, entry):
        """
        Converts wrong spacing in readings of entries in HanDeDict.

        @type entry: tuple
        @param entry: a dictionary entry
        @rtype: tuple
        @return: the given entry with corrected spacing
        """
        if type(entry) == type({}):
            headword = entry['HeadwordTraditional']
            reading = entry['Reading']
        else:
            headword, headwordSimplified, reading, translation = entry

        readingEntities = []
        precedingIsNonReading = False
        for idx, entity in enumerate(reading.split(' ')):
            if idx < len(headword) and entity == headword[idx]:
                # for entities showing up in both strings, ommit spaces
                #   (e.g. "IC卡", "I C kǎ")
                if not precedingIsNonReading:
                    readingEntities.append(' ')

                precedingIsNonReading = True
            elif idx != 0:
                readingEntities.append(' ')
                precedingIsNonReading = False

            readingEntities.append(entity)

        reading = ''.join(readingEntities)

        if type(entry) == type({}):
            entry['Reading'] = reading
            return entry
        else:
            return [headword, headwordSimplified, reading, translation]

    def timestamp(minusDays=0):
        from datetime import date, timedelta
        return (date.today() - timedelta(minusDays)).strftime("%Y%m%d")

    PROVIDES = 'HanDeDict'
    FILE_NAMES = ['handedict-' + timestamp() + '.zip',
        'handedict-' + timestamp() + '.tar.bz2', 'handedict.u8']
    ZIP_CONTENT_NAME = 'handedict-' + timestamp() + '/handedict.u8'
    ENCODING = 'utf-8'
    FILTER = filterSpacing


class HanDeDictWordIndexBuilder(WordIndexBuilder):
    """
    Builds the word index of the HanDeDict dictionary.
    """
    PROVIDES = 'HanDeDict_Words'
    DEPENDS = ['HanDeDict']
    TABLE_SOURCE = 'HanDeDict'
    HEADWORD_SOURCE = 'HeadwordTraditional'

#}
#{ DatabaseBuilder

class DatabaseBuilder:
    """
    DatabaseBuilder provides the main class for building up a database for the
    cjklib package.

    It contains all L{TableBuilder} classes and a dependency graph to handle
    build requests.
    """
    def __init__(self, dataPath=None, databaseSettings={}, quiet=False,
        rebuildDepending=True, rebuildExisting=True, noFail=False, prefer=[],
        additionalBuilders=[]):
        """
        Constructs the DatabaseBuilder.

        @type dataPath: list of str
        @param dataPath: optional list of paths to the data file(s)
        @type databaseSettings: dict
        @param databaseSettings: dictionary holding the database options for the
            dbconnector module. If key 'dump' is given all sql code will be
            printed to stdout.
        @type quiet: bool
        @param quiet: if true no status information will be printed to stderr
        @type rebuildDepending: bool
        @param rebuildDepending: if true existing tables that depend on updated
            tables will be dropped and built from scratch
        @type rebuildExisting: bool
        @param rebuildExisting: if true existing tables will be dropped and
            built from scratch
        @type noFail: bool
        @param noFail: if true build process won't terminate even if one table
            fails to build
        @type prefer: list
        @param prefer: list of L{TableBuilder} names to prefer in conflicting
            cases
        @type additionalBuilders: list of classobj
        @param additionalBuilders: list of externally provided TableBuilders
        """
        if not dataPath:
            buildModule = __import__("cjklib.build")
            self.dataPath = [os.path.join(buildModule.__path__[0], 'data')]
        else:
            if type(dataPath) == type([]):
                self.dataPath = dataPath
            else:
                # wrap as list
                self.dataPath = [dataPath]
        self.quiet = quiet
        self.rebuildDepending = rebuildDepending
        self.rebuildExisting = rebuildExisting
        self.noFail = noFail
        # get connector to database
        if databaseSettings and databaseSettings.has_key('dump'):
            self.db = None
        else:
            self.db = dbconnector.DatabaseConnector.getDBConnector(
                databaseSettings)
        # get TableBuilder classes
        tableBuilderClasses = DatabaseBuilder.getTableBuilderClasses(
            set(prefer), quiet=self.quiet,
            additionalBuilders=additionalBuilders)

        # build lookup
        self.tableBuilderLookup = {}
        for tableBuilder in tableBuilderClasses.values():
            if self.tableBuilderLookup.has_key(tableBuilder.PROVIDES):
                raise Exception("Table '" + tableBuilder.PROVIDES \
                    + "' provided by several builders")
            self.tableBuilderLookup[tableBuilder.PROVIDES] = tableBuilder

    def setDataPath(self, dataPath):
        """
        Changes the data path.

        @type dataPath: list of str
        @param dataPath: list of paths to the data file(s)
        """
        if type(dataPath) == type([]):
            self.dataPath = dataPath
        else:
            # wrap as list
            self.dataPath = [dataPath]

    def build(self, tables):
        """
        Builds the given tables.

        @type tables: list
        @param tables: list of tables to build
        """
        if type(tables) != type([]):
            tables = [tables]

        # remove tables that don't need to be rebuilt
        filteredTables = []
        for table in tables:
            if table not in self.tableBuilderLookup:
                raise exception.UnsupportedError("Table '" + table \
                    + "' not provided")

            if self.needsRebuild(table):
                filteredTables.append(table)
            else:
                if not self.quiet:
                    warn("Skipping table '" + table + "' as it already exists")
        tables = filteredTables

        # get depending tables that need to be updated when dependencies change
        dependingTables = []
        if self.rebuildDepending:
            dependingTables = self.getRebuiltDependingTables(tables)
            if dependingTables:
                warn("Tables rebuilt because of dependencies updated: '" \
                    +"', '".join(dependingTables) + "'")
                tables.extend(dependingTables)

        # get table list according to dependencies
        buildDependentTables = self.getBuildDependentTables(tables)
        buildTables = set(tables) | buildDependentTables
        # get build order and remove tables we don't need to build
        builderClasses = self.getClassesInBuildOrder(buildTables)

        # check if we only dump tables, no database available then and no
        #   tables with dependencies can be created
        if not self.db:
            noBuild = set()
            for builder in builderClasses:
                if builder.DEPENDS:
                    message = "Builder '" + builder.__name__ \
                        + "' depends on table(s) '" \
                        + "', '".join(builder.DEPENDS) \
                        + "' and needs to be built with database support"
                    if self.noFail:
                        warn(message + ', skipping')
                        noBuild.add(builder)
                    else:
                        raise Exception(message)
            # remove tables with dependencies
            builderClasses = [clss for clss in builderClasses \
                if not clss in noBuild]

        # build tables
        if not self.quiet and self.rebuildExisting:
            warn("Rebuilding tables and overwriting old ones...")
        builderClasses.reverse()
        instancesUnrequestedTable = set()
        while builderClasses:
            builder = builderClasses.pop()
            # check first if the table will only be created for resolving
            # dependencies and note it down for deletion
            try:
                if not self.quiet:
                    warn("Building table '" + builder.PROVIDES \
                        + "' with builder '" + builder.__name__ + "'...")
                instance = builder(self.dataPath, self.db, self.quiet)
                # mark tables as deletable if its only provided because of
                #   dependencies and the table doesn't exists yet
                if builder.PROVIDES in buildDependentTables \
                    and not self.db.tableExists(builder.PROVIDES):
                    instancesUnrequestedTable.add(instance)
                instance.build()
            except IOError, e:
                # data not available, can't build table
                if self.noFail:
                    if not self.quiet:
                        warn("Building table '" + builder.PROVIDES \
                            + "' failed: '" + str(e) + "', skipping")
                    dependingTables = [builder.PROVIDES]
                    remainingBuilderClasses = []
                    for clss in builderClasses:
                        if set(clss.DEPENDS) & set(dependingTables):
                            # this class depends on one being removed
                            dependingTables.append(clss.PROVIDES)
                        else:
                            remainingBuilderClasses.append(clss)
                    if not self.quiet and len(dependingTables) > 1:
                        warn("Ignoring depending table(s) '" \
                            + "', '".join(dependingTables[1:]) + "'")
                    builderClasses = remainingBuilderClasses
                else:
                    raise

        # remove tables that where only created as build dependencies
        if instancesUnrequestedTable:
            for instance in instancesUnrequestedTable:
                if not self.quiet:
                    warn("Removing table '" + instance.PROVIDES \
                        + "' as it was only created to solve build " \
                        + "dependencies")
                dropStatement = getDropTableStatement(instance.PROVIDES)
                self.db.getCursor().execute(dropStatement)

    def needsRebuild(self, tableName):
        """
        Returns true if either rebuild is turned on by default or we build into
        database and the table doesn't exist yet.

        @type tableName: classobj
        @param tableName: L{TableBuilder} class
        @rtype: bool
        @return: True, if table needs to be rebuilt
        """
        if self.rebuildExisting or not self.db:
            return True
        else:
            return not self.db.tableExists(tableName)

    def getBuildDependentTables(self, tableNames):
        """
        Gets the name of the tables that needs to be built to resolve
        dependencies.

        @type tableNames: list of str
        @param tableNames: list of tables to build
        @rtype: list of str
        @return: names of tables needed to resolve dependencies
        """
        def solveDependencyRecursive(table):
            """
            Gets all tables on which the given table depends and that need to be
            rebuilt. Also will mark tables skipped which won't be rebuilt.

            Uses parent's variables to store data.

            @type table: str
            @param table: table name for which to solve dependencies
            """
            if table in tableNames:
                # don't add dependant tables if they are given explicitly
                return
            if self.db and self.db.tableExists(table):
                skippedTables.add(table)
                return

            dependedTablesNames.add(table)

            # add dependent tables if needed (recursively)
            if not self.tableBuilderLookup.has_key(table):
                # either we have no builder or the builder was removed in
                # favour of another builder that shares at least one table
                # with the removed one
                raise exception.UnsupportedError("table '" + table \
                    + "' not provided, might be related to conflicting " \
                    + "builders")
            builderClass = self.tableBuilderLookup[table]
            for dependantTable in builderClass.DEPENDS:
                solveDependencyRecursive(dependantTable)

        tableNames = set(tableNames)
        dependedTablesNames = set()
        skippedTables = set()

        for table in tableNames:
            builderClass = self.tableBuilderLookup[table]
            for depededTable in builderClass.DEPENDS:
                solveDependencyRecursive(depededTable)

        if not self.quiet and skippedTables:
            warn("Depending on table(s) '" + "', '".join(skippedTables) \
                + "' but skipping as already existent")
        return dependedTablesNames

    def getDependingTables(self, tableNames):
        """
        Gets the name of the tables that depend on the given tables to be built
        and are not included in the given set.

        Dependencies depend on the choice of table builders and thus may vary.

        @type tableNames: list of str
        @param tableNames: list of tables
        @rtype: list of str
        @return: names of tables that depend on given tables
        """
        dependencyTables = set(tableNames)
        dependingTablesNames = set()
        residualTables = self.getCurrentSupportedTables() - dependencyTables

        while dependencyTables:
            dependencyTable = dependencyTables.pop()
            for table in residualTables:
                builderClass = self.tableBuilderLookup[table]
                if  dependencyTable in builderClass.DEPENDS:
                    # found a table that depends on the given table
                    dependingTablesNames.add(table)
                    # queue for check of depending tables
                    dependencyTables.add(table)
                    # no need for further testing on the newly found table
            residualTables = residualTables - dependencyTables

        return dependingTablesNames

    def getRebuiltDependingTables(self, tableNames):
        """
        Gets the name of the tables that depend on the given tables to be built
        and already exist, thus need to be rebuilt.

        @type tableNames: list of str
        @param tableNames: list of tables
        @rtype: list of str
        @return: names of tables that need to be rebuilt because of dependencies
        """
        dependingTables = self.getDependingTables(tableNames)
        if not self.db:
            # if dumping sql code build all
            return dependingTables

        needRebuild = set()
        for tableName in dependingTables:
            if self.db.tableExists(tableName):
                needRebuild.add(tableName)
        return needRebuild

    def getClassesInBuildOrder(self, tableNames):
        """
        Gets the build order for the given table names.

        @type tableNames: list of str
        @param tableNames: list of names of tables to build
        @rtype: list of classobj
        @return: L{TableBuilder}s in build order
        """
        # get dependencies and save order
        tableBuilderClasses = []
        for table in set(tableNames):
            if not self.tableBuilderLookup.has_key(table):
                # either we have no builder or the builder was removed in favour
                # of another builder that shares at least one table with the
                # removed one
                raise exception.UnsupportedError("table '" + table \
                    + "' not provided, might be related to conflicting " \
                    + "builders")
            tableBuilderClasses.append(self.tableBuilderLookup[table])
        return self.getBuildDependencyOrder(tableBuilderClasses)

    @staticmethod
    def getBuildDependencyOrder(tableBuilderClasses):
        """
        Create order in which the tables have to be created.

        @type tableBuilderClasses: list of classobj
        @param tableBuilderClasses: list of L{TableBuilder} classes
        @rtype: list of classobj
        @return: the given classes ordered in build dependency order
        """
        dependencyOrder = []
        providedTables = [bc.PROVIDES for bc in tableBuilderClasses]
        includedTableNames = set()
        while tableBuilderClasses:
            for builderClass in tableBuilderClasses:
                if set(builderClass.DEPENDS).intersection(providedTables) \
                    <= includedTableNames:
                    # found a terminal class or one whose dependencies are
                    #   already covered (at least no dependency on one of the
                    #   tables in the list)
                    break
            else:
                # one dependency can not be fulfilled, might be that no
                #   TableBuilder is  implemented, that it was removed due to
                #   conflicting other builder, or that a cycle in DEPEND graph
                #   exists
                raise Exception("Unfulfillable depend request, " \
                    + "might be related to conflicting builders or cycle. " \
                    + "Builders included: '" \
                    + "', '".join([clss.__name__ for clss in dependencyOrder]) \
                    + "'. Builders with open depends: '" \
                    + "', '".join([builder.PROVIDES \
                        for builder in tableBuilderClasses]) + "'")
            dependencyOrder.append(builderClass)
            includedTableNames.add(builderClass.PROVIDES)
            tableBuilderClasses.remove(builderClass)
        return dependencyOrder

    @staticmethod
    def getTableBuilderClasses(preferClassSet=set(), resolveConflicts=True,
        quiet=True, additionalBuilders=[]):
        """
        Gets all classes in module that implement L{TableBuilder}.

        @type preferClassSet: set of str
        @param preferClassSet: set of L{TableBuilder} names to prefer in
            conflicting cases, resolveConflicting must be True to take effect
            (default)
        @type resolveConflicts: bool
        @param resolveConflicts: if true conflicting builders will be removed
            so that only one builder is left per Table.
        @type quiet: bool
        @param quiet: if true no status information will be printed to stderr
        @type additionalBuilders: list of classobj
        @param additionalBuilders: list of externally provided TableBuilders
        @rtype: dict
        @return: dictionary of all classes inheriting form L{TableBuilder} that
            provide a table (i.d. non abstract implementations), with its name
            as key
        """
        tableBuilderClasses = {}
        buildModule = __import__("cjklib.build")
        # get all classes that inherit from TableBuilder
        tableBuilderClasses = dict([(clss.__name__, clss) \
            for clss in buildModule.build.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, buildModule.build.TableBuilder) \
            and clss.PROVIDES])
        # add additionally provided
        tableBuilderClasses.update(dict([(clss.__name__, clss) \
            for clss in additionalBuilders]))

        # check for conflicting builders and keep only one per conflicting group
        # group builders first
        tableToBuilderMapping = {}
        for clssName, clss in tableBuilderClasses.iteritems():
            if clss.PROVIDES not in tableToBuilderMapping:
                tableToBuilderMapping[clss.PROVIDES] = set()

            tableToBuilderMapping[clss.PROVIDES].add(clssName)

        if resolveConflicts:
            # now check conflicting and choose preferred if given
            for tableName, builderClssSet in tableToBuilderMapping.items():
                preferredBuilders = builderClssSet & preferClassSet
                if preferredBuilders:
                    if len(preferredBuilders) > 1:
                        # the user specified more than one preferred table that
                        # both provided at least one same table
                        raise Exception("More than one TableBuilder " \
                            + "preferred for conflicting table.")
                    preferred = preferredBuilders.pop()
                    builderClssSet.remove(preferred)
                else:
                    preferred = builderClssSet.pop()
                if not quiet and builderClssSet:
                    warn("Removing conflicting builder(s) '" \
                        + "', '".join(builderClssSet) + "' in favour of '" \
                        + preferred + "'")
                # remove other conflicting
                for clssName in builderClssSet:
                    del tableBuilderClasses[clssName]
        return tableBuilderClasses

    @staticmethod
    def getSupportedTables():
        """
        Gets names of supported tables.

        @rtype: list of str
        @return: names of tables
        """
        classDict = DatabaseBuilder.getTableBuilderClasses(
            resolveConflicts=False)
        return set([clss.PROVIDES for clss in classDict.values()])

    def getCurrentSupportedTables(self):
        """
        Gets names of tables supported by this instance of the database builder.

        This list can have more entries then L{getSupportedTables()} as
        additional external builders can be supplied on instantiation.

        @rtype: list of str
        @return: names of tables
        """
        return set(self.tableBuilderLookup.keys())

#}
#{ Global methods

def output(message):
    """
    Prints the given message to stdout with the system's default encoding.

    @type message: str
    @param message: message to print
    """
    print message.encode(locale.getpreferredencoding(), 'replace')

def warn(message):
    """
    Prints the given message to stderr with the system's default encoding.

    @type message: str
    @param message: message to print
    """
    print >> sys.stderr, message.encode(locale.getpreferredencoding(),
        'replace')

def getDropTableStatement(tableName):
    """
    Returns the SQL remove table statement for removing a table with the given
    name if it exists.

    @type tableName: str
    @param tableName: name of table to add data to
    @rtype: str
    @return: SQL drop table statement
    """
    return 'DROP TABLE IF EXISTS ' + tableName + ';'

def getFTS3DropTableStatement(tableName):
    """
    Returns the SQL remove table statement for removing a table with the given
    name if it exists.

    @type tableName: str
    @param tableName: name of table to add data to
    @rtype: str
    @return: SQL drop table statement
    """
    normalColumnsTableName = tableName + '_Normal'
    fullTextColumnsTableName = tableName + '_Text'
    return "\n".join(['DROP TABLE IF EXISTS ' + normalColumnsTableName + ';',
        'DROP TABLE IF EXISTS ' + fullTextColumnsTableName + ';',
        'DROP VIEW IF EXISTS ' + tableName + ';'])

def getCreateTableStatement(tableName, columnList, columnTypes={},
    columnDefaults={}, primaryKeyColumns=[], uniqueKeyColumns=[]):
    """
    Returns the SQL create table statement for creating a new table for the
    given columns.

    @type tableName: str
    @param tableName: name of table to add data to
    @type columnList: list of str
    @param columnList: name of columns to include in table
    @type columnTypes: dict
    @param columnTypes: sql type of columns
    @type columnDefaults: dict
    @param columnDefaults: default value for columns, if omitted NOT NULL
        will be assumed
    @type primaryKeyColumns: list of str
    @param primaryKeyColumns: column names that build the default key
    @type uniqueKeyColumns: list of list of str
    @param uniqueKeyColumns: several lists of column names, each list
        building a unique key
    @rtype: str
    @return: SQL create table statement
    """
    # construct column definitions
    columnDef = []
    # get key columns
    keysSet = set(primaryKeyColumns)
    for uniqueKeys in uniqueKeyColumns:
        keysSet.update(uniqueKeys)
    for column in columnList:
        if columnTypes.has_key(column):
            colType = columnTypes[column]
        else:
            colType = "TEXT"
        if columnDefaults.has_key(column):
            colDefault = ' ' + columnDefaults[column]
        elif column in keysSet:
            colDefault = ' NOT NULL'
        else:
            colDefault = ' DEFAULT NULL'
        columnDef.append(column + "\t" + colType + colDefault)
    # construct primary and unique key definitions
    primaryKeyDef = ''
    uniqueKeysDef = ''
    if primaryKeyColumns:
        primaryKeyDef = ",\n  PRIMARY KEY(" + ', '.join(primaryKeyColumns) \
        + ")"
    if uniqueKeyColumns:
        uniqueKeysDef = "\n, " \
            + "\n, ".join(['UNIQUE (' + ', '.join(columns) + ')' \
                for columns in uniqueKeyColumns])

    return "CREATE TABLE " + tableName + " (\n  " + ",\n  ".join(columnDef) \
        + primaryKeyDef + uniqueKeysDef + "\n);"

def testFTS3(cur):
    """
    Tests if the SQLite FTS3 extension is supported on the build system.

    @param cur: db cursor object
    @rtype: bool
    @return: C{True} if the FTS3 extension exists, C{False} otherwise.
    """
    # Until #3436 is fixed (http://www.sqlite.org/cvstrac/tktview?tn=3436,5)
    #   do it the bad way
    import pysqlite2.dbapi2
    try:
        cur.executescript(getFTS3CreateTableStatement(
            'cjklib_test_fts3_presence', ['dummy']))
        try:
            cur.executescript(getFTS3DropTableStatement(
                'cjklib_test_fts3_presence'))
        except pysqlite2.dbapi2.OperationalError:
            pass
        return True
    except pysqlite2.dbapi2.OperationalError:
        return False

def getFTS3CreateTableStatement(tableName, columnList, columnTypes={},
    columnDefaults={}, primaryKeyColumns=[], uniqueKeyColumns=[],
    fullTextColumns=[]):
    """
    Returns the SQL create table statement for creating a new table for the
    given columns using the SQLite FTS3 extension for fulltext searching.

    @type tableName: str
    @param tableName: name of table to add data to
    @type columnList: list of str
    @param columnList: name of columns to include in table
    @type columnTypes: dict
    @param columnTypes: sql type of columns
    @type columnDefaults: dict
    @param columnDefaults: default value for columns, if omitted NOT NULL
        will be assumed
    @type primaryKeyColumns: list of str
    @param primaryKeyColumns: column names that build the default key
    @type uniqueKeyColumns: list of list of str
    @param uniqueKeyColumns: several lists of column names, each list
        building a unique key
    @type fullTextColumns: list of str
    @param fullTextColumns: column names that are indexed for fulltext search
    @rtype: str
    @return: SQL create table statement
    """
    # construct column definitions
    columnDef = []
    # get key columns
    keysSet = set(primaryKeyColumns)
    for uniqueKeys in uniqueKeyColumns:
        keysSet.update(uniqueKeys)
    for column in columnList:
        if column in set(fullTextColumns):
            continue
        if columnTypes.has_key(column):
            colType = columnTypes[column]
        else:
            colType = "TEXT"
        if columnDefaults.has_key(column):
            colDefault = ' ' + columnDefaults[column]
        elif column in keysSet:
            colDefault = ' NOT NULL'
        else:
            colDefault = ' DEFAULT NULL'
        columnDef.append(column + "\t" + colType + colDefault)
    # construct primary and unique key definitions
    primaryKeyDef = ''
    uniqueKeysDef = ''
    if primaryKeyColumns:
        primaryKeyDef = ",\n  PRIMARY KEY(" + ', '.join(primaryKeyColumns) \
        + ")"
    if uniqueKeyColumns:
        uniqueKeysDef = "\n, " \
            + "\n, ".join(['UNIQUE (' + ', '.join(columns) + ')' \
                for columns in uniqueKeyColumns])
    normalColumnsTableName = tableName + '_Normal'
    normalColumnsTable = "CREATE TABLE " + normalColumnsTableName + " (\n  " \
        + ",\n  ".join(columnDef) + primaryKeyDef + uniqueKeysDef + "\n);"

    # fulltext table
    fullTextColumnsTableName = tableName + '_Text'
    fullTextColumnsTable = "CREATE VIRTUAL TABLE " + fullTextColumnsTableName \
        + " USING FTS3(" + ", ".join(fullTextColumns) + ");"

    # master table as view
    viewTable = "CREATE VIEW " + tableName + " AS SELECT * from " \
        + normalColumnsTableName + " JOIN " + fullTextColumnsTableName \
        + " ON " + normalColumnsTableName + ".rowid = " \
        + fullTextColumnsTableName + ".rowid;"

    return "\n".join([normalColumnsTable, fullTextColumnsTable, viewTable])

def getInsertStatement(tableName, data):
    """
    Returns the SQL insert statement for adding a new entry to the given table.

    The given data can be either passed in a list, where it will be assumed to
    have the order compatible to the table definition, or as a dictionary where
    the keys are the columns to write.

    @type tableName: str
    @param tableName: name of table to add data to
    @type data: dict/list
    @param data: key value pairs, with keys giving the column names or a simple
        list of values
    @rtype: str
    @return: SQL insert values statement
    """
    if type(data) == type({}):
        columnList = data.keys()
        cellList = [data[column] for column in columnList]
        columnDef = ' (' + ', '.join(columnList) + ')'
    else:
        columnDef = ''
        cellList = data
    return 'INSERT INTO ' + tableName + columnDef + ' VALUES (' \
        + ', '.join(prepareData(cellList)) + ');'

def getFTS3InsertStatement(tableName, data, fullTextColumns=[]):
    """
    Returns the SQL insert statement for adding a new entry to the given table.

    The given data can be either passed in a list, where it will be assumed to
    have the order compatible to the table definition, or as a dictionary where
    the keys are the columns to write.

    @type tableName: str
    @param tableName: name of table to add data to
    @type data: dict/list
    @param data: key value pairs, with keys giving the column names or a simple
        list of values
    @type fullTextColumns: list of str
    @param fullTextColumns: column names that are indexed for fulltext search
    @rtype: str
    @return: SQL insert values statement
    """
    normalColumnsTableName = tableName + '_Normal'

    columnList = [column for column in data.keys() \
        if column not in fullTextColumns]
    cellList = [data[column] for column in columnList]
    columnDef = ' (' + ', '.join(columnList) + ')'

    normalColumnsTable = 'INSERT INTO ' + normalColumnsTableName + columnDef \
        + ' VALUES (' + ', '.join(prepareData(cellList)) + ');'

    # fulltext table
    fullTextColumnsTableName = tableName + '_Text'

    columnList = [column for column in data.keys() \
        if column in fullTextColumns]
    cellList = [data[column] for column in columnList]
    columnDef = ' (rowid, ' + ', '.join(columnList) + ')'

    fullTextColumnsTable = 'INSERT INTO ' + fullTextColumnsTableName \
        + columnDef + ' VALUES (last_insert_rowid(), ' \
        + ', '.join(prepareData(cellList)) + ');'

    return normalColumnsTable + "\n" + fullTextColumnsTable

def getCreateIndexStatement(tableName, indexKeyColumns):
    """
    Returns the SQL create index statement for creating indices for the
    given columns.

    @type tableName: str
    @param tableName: name of table to add data to
    @type indexKeyColumns: list of list of str
    @param indexKeyColumns: several lists of column names, each list
        building index key
    @rtype: list of str
    @return: SQL create index statements
    """
    if not indexKeyColumns:
        return []
    for columns in indexKeyColumns:
        return ['CREATE INDEX ' + tableName + '__' + '_'.join(columns) \
            + ' ON ' + tableName + ' (' + ', '.join(columns) + ');' \
                for columns in indexKeyColumns]

def getFTS3CreateIndexStatement(tableName, indexKeyColumns):
    """
    Returns the SQL create index statement for creating indices for the
    given columns for tables created with the FTS3 extension in mind.

    @type tableName: str
    @param tableName: name of table to add data to
    @type indexKeyColumns: list of list of str
    @param indexKeyColumns: several lists of column names, each list
        building index key
    @rtype: list of str
    @return: SQL create index statements
    """
    if not indexKeyColumns:
        return []
    normalColumnsTableName = tableName + '_Normal'
    for columns in indexKeyColumns:
        return ['CREATE INDEX ' + tableName + '__' + '_'.join(columns) \
            + ' ON ' + normalColumnsTableName + ' (' + ', '.join(columns) \
            + ');' for columns in indexKeyColumns]

def prepareData(valueList):
    """
    Prepares the given list of values for a SQL operation.

    @type valueList: list
    @param valueList: list of values
    @rtype: list
    @return: list of values, C{None} replaced through C{'NULL'}, apostrophe
        escaped
    """
    newList = []
    for entry in valueList:
        if entry == None:
            newList.append('NULL')
        elif type(entry) in (type(0), type(0L)):
            newList.append(str(entry))
        else:
            newList.append("'" + entry.replace("'", "''") + "'")
    return newList
