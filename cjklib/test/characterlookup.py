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
Provides the library's unit tests for L{characterlookup.CharacterLookup}.
"""

import re
import unittest

from cjklib.reading import ReadingFactory
from cjklib import characterlookup
from cjklib import exception

class CharacterLookupTest():
    """Base class for testing the L{characterlookup.CharacterLookup} class."""
    def setUp(self):
        self.characterLookup = characterlookup.CharacterLookup('T')

    def shortDescription(self):
        methodName = getattr(self, self.id().split('.')[-1])
        # get whole doc string and remove superfluous white spaces
        noWhitespaceDoc = re.sub('\s+', ' ', methodName.__doc__.strip())
        # remove markup for epytext format
        return re.sub('[CL]\{([^\}]*)}', r'\1', noWhitespaceDoc)


class CharacterLookupReadingMethodsTestCase(CharacterLookupTest,
    unittest.TestCase):
    """
    Runs consistency checks on the reading methods of the
    L{characterlookup.CharacterLookup} class.
    @todo Impl: include script table from Unicode 5.2.0 to get character ranges
        for Hangul and Kana
    """
    class EngineMock(object):
        """
        Serves as a normal SQLAlchemy engine, but fakes existance of some
        tables.
        """
        def __init__(self, engine, mockTables):
            self._engine = engine
            self.mockTables = mockTables
        def has_table(self, table):
            if table in self.mockTables:
                return True
            else:
                return self._engine.has_table(table)
        def __getattr__(self, attr):
            return getattr(self._engine, attr)

    DIALECTS = {}

    SPECIAL_ENTITY_LIST = {}

    def setUp(self):
        CharacterLookupTest.setUp(self)
        self.f = ReadingFactory()

    def testReadingMappingAvailability(self):
        """
        Tests if the readings under
        C{CharacterLookup.CHARARACTER_READING_MAPPING} are available for
        conversion.
        """
        # mock to simulate availability of all tables in
        #   characterLookup.CHARARACTER_READING_MAPPING
        tables = [table for table, _ \
            in self.characterLookup.CHARARACTER_READING_MAPPING.values()]
        self.characterLookup.db.engine \
            = CharacterLookupReadingMethodsTestCase.EngineMock(
                self.characterLookup.db.engine, tables)

        for reading in self.characterLookup.CHARARACTER_READING_MAPPING:
            # only if table exists
            table, _ = self.characterLookup.CHARARACTER_READING_MAPPING[reading]

            self.assert_(
                self.characterLookup.hasMappingForReadingToCharacter(reading))
            self.assert_(
                self.characterLookup.hasMappingForCharacterToReading(reading))

    def testGetCharactersForReadingAcceptsAllEntities(self):
        """Test if C{getCharactersForReading} accepts all reading entities."""
        for reading in self.f.getSupportedReadings():
            if not self.characterLookup.hasMappingForReadingToCharacter(
                reading):
                continue

            dialects = [{}]
            if reading in self.DIALECTS:
                dialects.extend(self.DIALECTS[reading])

            for dialect in dialects:
                if hasattr(self.f.getReadingOperatorClass(reading),
                    'getReadingEntities'):
                    entities = self.f.getReadingEntities(reading, **dialect)
                elif reading in self.SPECIAL_ENTITY_LIST:
                    entities = self.SPECIAL_ENTITY_LIST[reading]
                else:
                    continue

                for entity in entities:
                    try:
                        results = self.characterLookup.getCharactersForReading(
                            entity, reading, **dialect)

                        self.assertEquals(type(results), type([]),
                            "Method getCharactersForReading() doesn't return" \
                                + " a list for entity %s " % repr(entity) \
                        + ' (reading %s, dialect %s)' % (reading, dialect))

                        for entry in results:
                            self.assertEquals(len(entry), 1,
                                "Entry %s in result for %s has length != 1" \
                                    % (repr(entry), repr(entity)) \
                                + ' (reading %s, dialect %s)' \
                                % (reading, dialect))
                    except exception.UnsupportedError:
                        pass
                    except exception.ConversionError:
                        pass
