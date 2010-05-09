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
Format strategies for dictionary entries.
"""

__all__ = [
    # meta
    "Base", "Chain", "SingleColumnAdapter",
    # format strategies
    "ReadingConversion", "NonReadingEntityWhitespace",
    ]

import string

from cjklib.reading import ReadingFactory
from cjklib import exception

#{ Formatting strategies

class Base(object):
    """Base formatting strategy, needs to be overridden."""
    def setDictionaryInstance(self, dictInstance):
        self._dictInstance = dictInstance

    def format(self, string):
        """
        Returns the formatted column.

        :type string: str
        :param string: column as returned by the dictionary
        :rtype: str
        :return: formatted column
        """
        raise NotImplementedError()


class Chain(Base):
    """
    Executes a list of formatting strategies, with the first strategy being
    applied first, then the second, and so forth.
    """
    def __init__(self, *args):
        Base.__init__(self)
        self.args = args

    def format(self, *args):
        for strategy in self.args:
            string = strategy.format(*args)
        return string


class SingleColumnAdapter(Base):
    """
    Adapts a formatting strategy for a single column for multi-column input.
    """
    def __init__(self, strategy, columnIndex):
        Base.__init__(self)
        self.strategy = strategy
        self.columnIndex = columnIndex

    def format(self, columns):
        columns = columns[:]
        columns[self.columnIndex] = self.strategy.format(
            columns[self.columnIndex])
        return columns

    def __getattr__(self, name):
        return getattr(self.strategy, name)


class ReadingConversion(Base):
    """Converts the entries' reading string to the given target reading."""
    def __init__(self, toReading=None, targetOptions=None):
        """
        Constructs the conversion strategy.

        :type toReading: str
        :param toReading: target reading, if omitted, the dictionary's reading
            is assumed.
        :type targetOptions: dict
        :param targetOptions: target reading conversion options
        """
        Base.__init__(self)
        self.toReading = toReading
        if targetOptions:
            self.targetOptions = targetOptions
        else:
            self.targetOptions = {}

    def setDictionaryInstance(self, dictInstance):
        super(ReadingConversion, self).setDictionaryInstance(
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


class NonReadingEntityWhitespace(Base):
    """
    Removes spaces between non-reading entities, e.g. ``U S B diàn lǎn`` to
    ``USB diàn lǎn`` for CEDICT style dictionaries.
    """
    FULL_WIDTH_MAP = dict((halfWidth, unichr(ord(halfWidth) + 65248))
        for halfWidth in string.ascii_uppercase)
    """Mapping of halfwidth characters to fullwidth."""

    def format(self, columns):
        headword, headwordSimplified, reading, translation = columns

        readingEntities = []
        precedingIsNonReading = False
        for idx, entity in enumerate(reading.split(' ')):
            if idx < len(headword) and (entity == headword[idx]
                or self.FULL_WIDTH_MAP.get(entity, None) == headword[idx]):
                # for entities showing up in both strings, omit spaces
                #   (e.g. "IC卡", "I C kǎ")
                if not precedingIsNonReading and idx != 0:
                    readingEntities.append(' ')

                precedingIsNonReading = True
            elif idx != 0:
                readingEntities.append(' ')
                precedingIsNonReading = False

            readingEntities.append(entity)

        reading = ''.join(readingEntities)

        return [headword, headwordSimplified, reading, translation]
