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
Provides simple read access to a SQL database.
"""

import logging

from sqlalchemy import MetaData, Table, engine_from_config
from sqlalchemy.sql import text
from sqlalchemy.engine import url

from cjklib.util import getConfigSettings

class DatabaseConnector:
    """
    A DatabaseConnector provides simple read access to a SQL database.

    On initialisation it connects to a given database. Once connected it's
    select methods can be used to quickly access the database content.

    DatabaseConnector supports a wide range of database systems through
    I{SQLalchemy}.

    As only standard select commands are issued further systems should be easy
    to incorporate.

    For selecting entries there are for different methods given:
        1. C{selectRows()}: the most general select method
        2. C{selectScalars()}: returns entries for only one column
        3. C{selectRow()}: returns only one entry
        4. C{selectScalar()}: returns one single value
    """
    _dbconnectInst = None
    """
    Instance of a L{DatabaseConnector} used for all connections to SQL server.
    """
    _dbconnectInstSettings = None
    """
    Database url used to create the connector instance.
    """

    @classmethod
    def getDBConnector(cls, configuration=None, projectName='cjklib'):
        """
        Returns a shared L{DatabaseConnector} instance.

        To connect to a user specific database give
        C{{'url': 'driver://user:pass@host/database'}} as configuration.
        See the documentation of sqlalchemy.create_engine() for more options.

        @param configuration: database connection options for SQLAlchemy
        @type projectName: str
        @param projectName: name of project which will be used as name of the
            config file
        """
        # allow single string and interpret as url
        if type(configuration) in (type(''), type(u'')):
            configuration = {'url': configuration}
        elif not configuration:
            # try to read from config
            configuration = getConfigSettings('Connection', projectName)

            if 'url' not in configuration:
                from pkg_resources import Requirement, resource_filename
                dbFile = resource_filename(Requirement.parse(projectName),
                    '%(proj)s/%(proj)s.db' % {'proj': projectName})
                configuration['url'] = 'sqlite:///%s' % dbFile

        # if settings changed, remove old instance
        if not cls._dbconnectInstSettings \
            or cls._dbconnectInstSettings != configuration:
            cls._dbconnectInst = None

        if not cls._dbconnectInst:
            databaseSettings = configuration.copy()

            cls._dbconnectInst = DatabaseConnector(databaseSettings)
            cls._dbconnectInstSettings = databaseSettings

        return cls._dbconnectInst

    def __init__(self, configuration):
        """
        Constructs the DatabaseConnector object and connects to the database
        specified by the options given in databaseSettings.

        To connect to a user specific database give
        C{{'url': 'driver://user:pass@host/database'}} as configuration.
        See the documentation of sqlalchemy.create_engine() for more options.

        @type configuration: dict
        @param configuration: database connection options for SQLAlchemy
        """
        configuration = configuration or {}
        if type(configuration) in (type(''), type(u'')):
            # backwards compatibility to option databaseUrl
            configuration = {'url': configuration}
        self.databaseUrl = configuration['url']
        """database url"""
        # connect to database
        self.engine = engine_from_config(configuration, prefix='')
        """SQLAlchemy engine object"""
        # create connection
        self.connection = self.engine.connect()
        """SQLAlchemy database connection object"""
        # parse table information
        self.metadata = MetaData(bind=self.connection, reflect=True)
        """SQLAlchemy metadata object"""
        # short cut
        self.tables = self.metadata.tables
        """dictionary of SQLAlchemy table objects"""

        self._registerViews()

    def _registerViews(self):
        """
        Registers all views and makes them accessible through the same methods
        as tables in SQLalchemy.

        @rtype: list of str
        @return: List of registered views
        @attention: Currently only works for MySQL and SQLite.
        """
        if self.engine.name == 'mysql':
            dbName = self.engine.url.database
            viewList = self.execute(
                text("""SELECT table_name FROM Information_schema.views
                    WHERE table_schema = :dbName"""),
                dbName=dbName).fetchall()
        elif self.engine.name == 'sqlite':
            viewList = self.execute(
                text("SELECT name FROM sqlite_master WHERE type IN ('view')"))\
                .fetchall()
        else:
            logging.warning("Don't know how to get all views from database. Unable to register. Views will not show up in list of available tables.")
            return

        for viewName, in viewList:
            # add views that are currently not (well) supported by SQLalchemy
            #   http://www.sqlalchemy.org/trac/ticket/812
            Table(viewName, self.metadata, autoload=True)

        return [viewName for viewName, in viewList]

    def getTables(self):
        """
        Gets all tables (and views) from the Database.

        @rtype: list of str
        @return: all tables and views
        """
        tables = self._registerViews()
        tables.extend(self.engine.table_names())
        return tables

    def execute(self, *options, **keywords):
        """
        Executes a request on the given database.
        """
        return self.connection.execute(*options, **keywords)

    def _decode(self, data):
        """
        Decodes a data row.

        MySQL will currently return utf8_bin collated values as string object
        encoded in utf8. We need to fix that here.
        @param data: a tuple or scalar value
        """
        if type(data) == type(()):
            newData = []
            for cell in data:
                if type(cell) == type(''):
                    cell = cell.decode('utf8')
                newData.append(cell)
            return tuple(newData)
        else:
            if type(data) == type(''):
                return data.decode('utf8')
            else:
                return data

    # select commands

    def selectScalar(self, request):
        """
        Executes a select query and returns a single variable.

        @param request: SQL request
        @return: a scalar
        """
        result = self.connection.execute(request)
        assert result.rowcount <= 1
        firstRow = result.fetchone()
        assert not firstRow or len(firstRow) == 1
        if firstRow:
            return self._decode(firstRow[0])

    def selectScalars(self, request):
        """
        Executes a select query and returns a list of scalars.

        @param request: SQL request
        @return: a list of scalars
        """
        result = self.connection.execute(request)
        return [self._decode(row[0]) for row in result.fetchall()]

    def selectRow(self, request):
        """
        Executes a select query and returns a single table row.

        @param request: SQL request
        @return: a list of scalars
        """
        result = self.connection.execute(request)
        assert result.rowcount <= 1
        firstRow = result.fetchone()
        if firstRow:
            return self._decode(tuple(firstRow))

    def selectRows(self, request):
        """
        Executes a select query and returns a list of table rows.

        @param request: SQL request
        @return: a list of scalars
        """
        result = self.connection.execute(request)
        return [self._decode(tuple(row)) for row in result.fetchall()]
