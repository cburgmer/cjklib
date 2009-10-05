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
Provides utilities.
"""

import re
import os.path
import ConfigParser
import csv

def getConfigSettings(section, projectName='cjklib'):
    """
    Reads the configuration from the given section of the project's config file.

    @type section: str
    @param section: section of the config file
    @type projectName: str
    @param projectName: name of project which will be used as name of the
        config file
    @rtype: dict
    @return: configuration settings for the given project
    """
    # don't convert to lowercase
    h = ConfigParser.SafeConfigParser.optionxform
    try:
        ConfigParser.SafeConfigParser.optionxform = lambda self, x: x
        config = ConfigParser.SafeConfigParser()
        config.read([os.path.join(os.path.expanduser('~'),
            '.%s.conf' % projectName),
            os.path.join('/', 'etc', '%s.conf' % projectName)])

        configuration = dict(config.items(section))
    except ConfigParser.NoSectionError:
        configuration = {}

    ConfigParser.SafeConfigParser.optionxform = h

    return configuration

# define our own titlecase methods, as the Python implementation is currently
#   buggy (http://bugs.python.org/issue6412), see also
#   http://www.unicode.org/mail-arch/unicode-ml/y2009-m07/0066.html
_FIRST_NON_CASE_IGNORABLE = re.compile(ur"(?u)([.˳｡￮₀ₒ]?\W*)(\w)(.*)$")
"""
Regular expression matching the first alphabetic character. Include GR neutral
tone forms.
"""
def titlecase(strng):
    u"""
    Returns the string (without "word borders") in titlecase.

    This function is not designed to work for multi-entity strings in general
    but rather for syllables with apostrophes (e.g. C{'Ch’ien1'}) and combining
    diacritics (e.g. C{'Hm\\u0300h'}). It additionally needs to support cases
    where a multi-entity string can derive from a single entity as in the case
    for I{GR} (e.g. C{'Shern.me'} for C{'Sherm'}).

    @type strng: str
    @param strng:  a string
    @rtype: str
    @return: the given string in titlecase
    @todo Impl: While this function is only needed as long Python doesn't ship
        with a proper title casing algorithm as defined by Unicode, we need
        a proper handling for I{Wade-Giles}, as I{Pinyin} I{Erhua} forms will
        convert to two entities being separated by a hyphen, which does not fall
        in to the Unicode title casing algorithm's definition of a
        case-ignorable character.
    """
    matchObj = _FIRST_NON_CASE_IGNORABLE.match(strng.lower())
    if matchObj:
        tonal, firstChar, rest = matchObj.groups()
        return tonal + firstChar.upper() + rest

def istitlecase(strng):
    """
    Checks if the given string is in titlecase.

    @type strng: str
    @param strng:  a string
    @rtype: bool
    @return: C{True} if the given string is in titlecase according to
        L{titlecase()}.
    """
    return titlecase(strng) == strng

def cross(*args):
    """
    Builds a cross product of the given lists.

    Example:
        >>> cross(['A', 'B'], [1, 2, 3])
        [['A', 1], ['A', 2], ['A', 3], ['B', 1], ['B', 2], ['B', 3]]
    """
    ans = [[]]
    for arg in args:
        ans = [x+[y] for x in ans for y in arg]
    return ans

def crossDict(*args):
    """Builds a cross product of the given dicts."""
    def joinDict(a, b):
        a = a.copy()
        a.update(y)
        return a

    ans = [{}]
    for arg in args:
        ans = [joinDict(x, y) for x in ans for y in arg]
    return ans

class CharacterRangeIterator(object):
    """Iterates over a given set of codepoint ranges given in hex."""
    def __init__(self, ranges):
        self.ranges = ranges[:]
        self._curRange = self._popRange()
    def _popRange(self):
        if self.ranges:
            charRange = self.ranges[0]
            del self.ranges[0]
            if type(charRange) == type(()):
                rangeFrom, rangeTo = charRange
            else:
                rangeFrom, rangeTo = (charRange, charRange)
            return (int(rangeFrom, 16), int(rangeTo, 16))
        else:
            return []
    def __iter__(self):
        return self
    def next(self):
        if not self._curRange:
            raise StopIteration

        curIndex, toIndex = self._curRange
        if curIndex < toIndex:
            self._curRange = (curIndex + 1, toIndex)
        else:
            self._curRange = self._popRange()
        return unichr(curIndex)


class UnicodeCSVFileIterator(object):
    """Provides a CSV file iterator supporting Unicode."""
    class DefaultDialect(csv.Dialect):
        """Defines a default dialect for the case sniffing fails."""
        quoting = csv.QUOTE_NONE
        delimiter = ','
        lineterminator = '\n'
        quotechar = "'"
        # the following are needed for Python 2.4
        escapechar = "\\"
        doublequote = True
        skipinitialspace = False

    def __init__(self, fileHandle):
        self.fileHandle = fileHandle

    def __iter__(self):
        return self

    def next(self):
        if not hasattr(self, '_csvReader'):
            self._csvReader = self._getCSVReader(self.fileHandle)

        return [unicode(cell, 'utf-8') for cell in self._csvReader.next()]

    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    @staticmethod
    def byte_string_dialect(dialect):
        class ByteStringDialect(csv.Dialect):
            def __init__(self, dialect):
                for attr in ["delimiter", "quotechar", "escapechar",
                    "lineterminator"]:
                    old = getattr(dialect, attr)
                    if old is not None:
                        setattr(self, attr, str(old))

                for attr in ["doublequote", "skipinitialspace", "quoting"]:
                    setattr(self, attr, getattr(dialect, attr))

                csv.Dialect.__init__(self)

        return ByteStringDialect(dialect)

    def _getCSVReader(self, fileHandle):
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
            return csv.reader(fileHandle)
        try:
            self.fileDialect = csv.Sniffer().sniff(line, ['\t', ','])
            # fix for Python 2.4
            if len(self.fileDialect.delimiter) == 0:
                raise csv.Error()
        except csv.Error:
            self.fileDialect = UnicodeCSVFileIterator.DefaultDialect()

        content = prependLineGenerator(line, fileHandle)
        return csv.reader(
            UnicodeCSVFileIterator.utf_8_encoder(content),
            dialect=UnicodeCSVFileIterator.byte_string_dialect(
                self.fileDialect))
        #return csv.reader(content, dialect=self.fileDialect) # TODO
