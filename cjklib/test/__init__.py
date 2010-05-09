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
Unit tests.
"""

__all__ = ['readingoperator', 'readingconverter', 'characterlookup',
    'dictionary', 'attr', 'DatabaseConnectorMock', 'EngineMock']

from cjklib import dbconnector

try:
    from nose.plugins.attrib import attr
except ImportError:
    # dummy decorator
    def attr(attrName):
        return lambda x: x

class NeedsDatabaseTest(object):
    """Base class for unit test with database access."""

    def setUp(self):
        self.db = dbconnector.getDBConnector()


class NeedsTemporaryDatabaseTest(object):
    """Base class for unit test with access to a temporary database."""

    def setUp(self):
        self.db = dbconnector.DatabaseConnector(
            {'sqlalchemy.url': 'sqlite://', 'attach': ['cjklib']})


class CacheDict(dict):
    def __init__(self, cachedDict, *args, **options):
        dict.__init__(self, *args, **options)
        self.cachedDict = cachedDict
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.cachedDict.__getitem__(key)


class DatabaseConnectorMock(object):
    """
    Serves as a normal database connector engine, but fakes existance of
    some tables.
    """
    def __init__(self, dbConnectInst, mockTables=None,
        mockTableDefinition=None, mockNonTables=None):

        self._dbConnectInst = dbConnectInst
        self._dbConnectInst.engine = EngineMock(self._dbConnectInst.engine,
            mockTables, mockNonTables)

        self.mockTables = mockTables or []
        self.mockTableDefinition = mockTableDefinition
        self.mockNonTables = mockNonTables or []

    def getTableNames(self):
        return (self._dbConnectInst.getTableNames()
            - set(self.mockNonTables) | set(self.mockTables))

    def __getattr__(self, attr):
        if attr == 'tables' and self.mockTableDefinition:
            pseudoTables = dict((table.name, table)
                for table in self.mockTableDefinition)
            return CacheDict(self._dbConnectInst.tables, pseudoTables)
        return getattr(self._dbConnectInst, attr)


class EngineMock(object):
    """
    Serves as a normal SQLAlchemy engine, but fakes existence of some
    tables.
    """
    def __init__(self, engine, mockTables=None, mockNonTables=None):
        self._engine = engine
        self.mockTables = mockTables or []
        self.mockNonTables = mockNonTables or []
    def has_table(self, table, *args, **kwargs):
        if table in self.mockTables:
            return True
        elif table in self.mockNonTables:
            return False
        else:
            return self._engine.has_table(table, *args, **kwargs)
    def __getattr__(self, attr):
        return getattr(self._engine, attr)

