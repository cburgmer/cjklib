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
Provides simple read access to SQL databases.

A DatabaseConnector connects to one or more SQL databases. It provides four
simple methods for retrieving scalars or rows of data:
    1. C{selectScalar()}: returns one single value
    2. C{selectRow()}: returns only one entry with several columns
    3. C{selectScalars()}: returns entries for a single column
    4. C{selectRows()}: returns multiple entries for multiple columns

This class takes care to load the correct database(s). It provides for
attaching further databases and gives any program that depends on cjklib the
possibility to easily add own data in databases outside cjklib extending the
library's information.

DatabaseConnector has a convenience function L{getDBConnector()} that loads
an instance with the proper settings for the given project. By default
settings for project C{'cjklib'} are chosen, but this behaviour can be
overwritten by passing a different project name:
C{getDBConnector(projectName='My Project')}. Connection settings can also be
provided manually, omitting automatic searching. Multiple calls with the
same connection settings will return the same shared instance.

Example:

    >>> from cjklib import dbconnector
    >>> from sqlalchemy import select
    >>> db = dbconnector.getDBConnector()
    >>> db.selectScalar(select([db.tables['Strokes'].c.Name],
    ...     db.tables['Strokes'].c.StrokeAbbrev == 'T'))
    u'\u63d0'

DatabaseConnector is tested on SQLite and MySQL but should support most
other database systems through I{SQLAlchemy}.

SQLite and Unicode
==================
SQLite be default only provides letter case folding for alphabetic
characters A-Z from ASCII. If SQLite is built against I{ICU}, Unicode
methods are used instead for C{LIKE} and C{upper()/lower()}. If I{ICU} is
not compiled into the database system L{DatabaseConnector} can register own
methods. As this has negative impact on performance, it is disabled by
default. Compatibility support can be enabled by setting option
C{'registerUnicode'} to C{True} when given as configuration to L{__init__()}
or L{getDBConnector()} or alternatively can be set as default in
C{cjklib.conf}.

Multiple database support
=========================
A DatabaseConnector instance is attached to a main database. Further
databases can be attached at any time, providing further tables. Tables from
the main database will shadow any other table with a similar name. A table
not found in the main database will be chosen from a database in the order
of their attachment.

The L{DatabaseConnector.tables} dictionary allows simple lookup of table objects
by short name, without the need of knowing the full qualified name including the
database specifier. Existence of tables can be checked using
L{DatabaseConnector.hasTable()}; L{DatabaseConnector.tables} will only include
table information after the first access. All table names can be retrieved with
L{DatabaseConnector.getTableNames()}.

Table lookup is designed with a stable data set in mind. Moving tables between
databases is not specially supported and while operations through the L{build}
module will update any information in the L{DatabaseConnector.tables}
dictionary, manual creating and dropping of a table or changing its structure
will lead to the dictionary having obsolete information. This can be
circumvented by deleting keys forcing an update:

    >>> del db.tables['my table']

Example:

    >>> from cjklib.dbconnector import DatabaseConnector
    >>> db = DatabaseConnector({'url': 'sqlite:////tmp/mydata.db',
    ...     'attach': ['cjklib']})
    >>> db.tables['StrokeOrder'].fullname
    'cjklib_0.StrokeOrder'

Discovery of attachable databases
---------------------------------
DatabaseConnector has the ability to discover databases attaching them to
the main database. Specifying databases can be done in three ways:
    1. A full URL can be given denoting a single database, e.g.
        X{'sqlite:////tmp/mydata.db'}.
    2. Giving a directory will add any .db file as SQLite database, e.g.
        X{'/usr/local/share/cjklib'}.
    3. Giving a project name will prompt DatabaseConnector to check for
        a project config file and add databases specified there and/or scan
        that project's default directories, e.g. X{'cjklib'}.
"""

__all__ = ["getDBConnector", "getDefaultConfiguration", "DatabaseConnector"]

import os
import logging
import glob

from sqlalchemy import MetaData, Table, engine_from_config
from sqlalchemy.sql import text
from sqlalchemy.engine.url import make_url

from cjklib.util import (getConfigSettings, getSearchPaths, deprecated,
    LazyDict, OrderedDict)

_dbconnectInst = None
# Cached instance of a DatabaseConnector used for connections with settings of
#   _dbconnectInstSettings

_dbconnectInstSettings = None
# Connection configuration for cached instance

def getDBConnector(configuration=None, projectName='cjklib'):
    """
    Returns a shared L{DatabaseConnector} instance.

    To connect to a user specific database give
    C{{'sqlalchemy.url': 'driver://user:pass@host/database'}} as
    configuration.

    If no configuration is passed a connection is made to the default
    database PROJECTNAME.db in the project's folder.


    @see: The documentation of sqlalchemy.create_engine() for more options
    @see: the class documentation of L{DatabaseConnector}.

    @param configuration: database connection options (includes settings for
        SQLAlchemy prefixed by C{'sqlalchemy.'})
    @type projectName: str
    @param projectName: name of project which will be used as name of the
        config file
    """
    global _dbconnectInst, _dbconnectInstSettings
    # allow single string and interpret as url
    if isinstance(configuration, basestring):
        configuration = {'sqlalchemy.url': configuration}

    elif not configuration:
        # try to read from config
        configuration = getDefaultConfiguration(projectName)

    # if settings changed, remove old instance
    if (not _dbconnectInstSettings or _dbconnectInstSettings != configuration):
        _dbconnectInst = None

    if not _dbconnectInst:
        databaseSettings = configuration.copy()

        _dbconnectInst = DatabaseConnector(databaseSettings)
        _dbconnectInstSettings = databaseSettings

    return _dbconnectInst

def getDefaultConfiguration(projectName='cjklib'):
    """
    Gets the default configuration for the given project. Settings are read
    from a configuration file.

    By default an URL to a database PROJECTNAME.db in the project's folder
    is returned and the project's default directories are searched for
    attachable databases.

    @type projectName: str
    @param projectName: name of project which will be used in search for the
        configuration and as the name of the default database
    """
    # try to read from config
    configuration = getConfigSettings('Connection', projectName)

    if 'url' in configuration:
        url = configuration.pop('url')
        if 'sqlalchemy.url' not in configuration:
            configuration['sqlalchemy.url'] = url

    if 'sqlalchemy.url' not in configuration:
        try:
            from pkg_resources import Requirement, resource_filename
            dbFile = resource_filename(Requirement.parse(projectName),
                '%(proj)s/%(proj)s.db' % {'proj': projectName})
        except ImportError:
            # fall back to the directory of this file, only works for cjklib
            libdir = os.path.dirname(os.path.abspath(__file__))
            dbFile = os.path.join(libdir, '%(proj)s.db' % {'proj': projectName})

        configuration['sqlalchemy.url'] = 'sqlite:///%s' % dbFile

    if 'attach' in configuration:
        configuration['attach'] = configuration['attach'].split('\n')
    else:
        configuration['attach'] = [projectName]

    return configuration


class DatabaseConnector(object):
    """
    Database connection object.

    @see: class documentation of L{dbconnector}
    """
    @classmethod
    @deprecated
    def getDBConnector(cls, configuration=None, projectName='cjklib'):
        """
        Deprecated method, use L{dbconnector.getDBConnector()} instead.
        """
        return getDBConnector(configuration, projectName)

    @classmethod
    @deprecated
    def getDefaultConfiguration(cls, projectName='cjklib'):
        """
        Deprecated method, use L{dbconnector.getDefaultConfiguration()} instead.
        """
        return getDefaultConfiguration(projectName)

    def __init__(self, configuration):
        """
        Constructs the DatabaseConnector object and connects to the database
        specified by the options given in databaseSettings.

        To connect to a database give
        C{{'sqlalchemy.url': 'driver://user:pass@host/database'}} as
        configuration. Further databases can be attached by passing a list
        of URLs or names for keyword C{'attach'}, see L{DatabaseConnector}.

        @see: The documentation of sqlalchemy.create_engine() for more options
        @see: the class documentation of L{DatabaseConnector}.

        @type configuration: dict
        @param configuration: database connection options for SQLAlchemy
        """
        configuration = configuration or {}
        if isinstance(configuration, basestring):
            # backwards compatibility to option databaseUrl
            configuration = {'sqlalchemy.url': configuration}

        # allow 'url' as parameter, but move to 'sqlalchemy.url'
        if 'url' in configuration:
            if ('sqlalchemy.url' in configuration
                and configuration['sqlalchemy.url'] != configuration['url']):
                raise ValueError("Two different URLs specified"
                    " for 'url' and 'sqlalchemy.url'."
                    "Check your configuration.")
            else:
                configuration['sqlalchemy.url'] = configuration.pop('url')

        self.databaseUrl = configuration['sqlalchemy.url']
        """Database url"""
        registerUnicode = configuration.pop('registerUnicode', False)
        if isinstance(registerUnicode, basestring):
            registerUnicode = (registerUnicode.lower()
                in ['1', 'yes', 'true', 'on'])
        self.registerUnicode = registerUnicode

        self.engine = engine_from_config(configuration, prefix='sqlalchemy.')
        """SQLAlchemy engine object"""
        self.connection = self.engine.connect()
        """SQLAlchemy database connection object"""
        self.metadata = MetaData(bind=self.connection)
        """SQLAlchemy metadata object"""

        # multi-database table access
        self.tables = LazyDict(self._tableGetter())
        """Dictionary of SQLAlchemy table objects"""

        if self.engine.name == 'sqlite':
            # Main database can be prefixed with 'main.'
            self._mainSchema = 'main'
        else:
            # MySQL uses database name for prefix
            self._mainSchema = self.engine.url.database

        # attach other databases
        self.attached = OrderedDict()
        """Mapping of attached database URLs to internal schema names"""
        attach = configuration.pop('attach', [])
        searchPaths = self.engine.name == 'sqlite'
        for url in self._findAttachableDatabases(attach, searchPaths):
            self.attachDatabase(url)

        # register unicode functions
        self.compatibilityUnicodeSupport = False
        if self.registerUnicode:
            self._registerUnicode()

    def _findAttachableDatabases(self, attachList, searchPaths=False):
        """
        Returns URLs for databases that can be attached to a given database.

        @type searchPaths: bool
        @param searchPaths: if C{True} default search paths will be checked for
            attachable SQLite databases.
        """
        attachable = []
        for name in attachList:
            if '://' in name:
                # database url
                attachable.append(name)
            elif os.path.isabs(name):
                # path
                if not os.path.exists(name):
                    continue

                files = glob.glob(os.path.join(name, "*.db"))
                files.sort()
                attachable.extend([('sqlite:///%s' % f) for f in files])

            elif '/' not in name and '\\' not in name:
                # project name
                configuration = getDefaultConfiguration(name)

                # first add main database
                attachable.append(configuration['sqlalchemy.url'])

                # add attachables from the given project
                attach = configuration['attach']
                if name in attach:
                    # default search path
                    attach.remove(name)
                    if searchPaths:
                        attach.extend(getSearchPaths(name))

                attachable.extend(self._findAttachableDatabases(attach,
                    searchPaths))
            else:
                raise ValueError(("Invalid database reference '%s'."
                    " Check your 'attach' settings!")
                    % name)

        return attachable

    def _registerUnicode(self):
        """
        Register functions and collations to bring Unicode support to certain
        engines.
        """
        if self.engine.name == 'sqlite':
            uUmlaut = self.selectScalar(text(u"SELECT lower('Ü');"))
            if uUmlaut != u'ü':
                # register own Unicode aware functions
                con = self.connection.connection
                con.create_function("lower", 1, lambda s: s and s.lower())
                con.create_collation("NOCASE",
                    lambda a, b: cmp(a.decode('utf8').lower(),
                        b.decode('utf8').lower()))

                self.compatibilityUnicodeSupport = True

    #{ Multiple database support

    def _getViews(self):
        """
        Returns all views.

        @rtype: list of str
        @return: list of views
        @attention: Currently only works for MySQL and SQLite.
        """
        # get views that are currently not (well) supported by SQLalchemy
        #   http://www.sqlalchemy.org/trac/ticket/812
        schemas = [self._mainSchema] + self.attached.values()

        if self.engine.name == 'mysql':
            views = []
            for schema in schemas:
                viewList = self.execute(
                    text("SELECT table_name FROM Information_schema.views"
                        " WHERE table_schema = :schema"),
                    schema=schema).fetchall()
                views.extend([view for view, in viewList if view not in views])
        elif self.engine.name == 'sqlite':
            views = []
            identifier_preparer = self.engine.dialect.identifier_preparer
            for schema in schemas:
                qschema = identifier_preparer.quote_identifier(schema)
                s = ("SELECT name FROM %s.sqlite_master "
                        "WHERE type='view' ORDER BY name") % qschema

                viewList = self.execute(text(s)).fetchall()
                views.extend([view for view, in viewList if view not in views])
        else:
            logging.warning("Don't know how to get all views from database."
                " Unable to register."
                " Views will not show up in list of available tables.")
            return []

        return views

    def attachDatabase(self, databaseUrl):
        """
        Attaches a database to the main database.

        @type databaseUrl: str
        @param databaseUrl: database URL
        @rtype: str
        @return: the database's schema used to access its tables, C{None} if
            that database has been attached before
        """
        if databaseUrl == self.databaseUrl or databaseUrl in self.attached:
            return

        url = make_url(databaseUrl)
        if url.drivername != self.engine.name:
            raise ValueError(
                ("Unable to attach database '%s': Incompatible engines."
                " Check your 'attach' settings!")
                    % databaseUrl)

        if self.engine.name == 'sqlite':
            databaseFile = url.database

            _, dbName = os.path.split(databaseFile)
            if dbName.endswith('.db'): dbName = dbName[:-3]
            schema = '%s_%d' % (dbName, len(self.attached))

            self.execute(text("""ATTACH DATABASE :database AS :schema"""),
                database=databaseFile, schema=schema)
        else:
            schema = url.database

        self.attached[databaseUrl] = schema

        return schema

    def getTableNames(self):
        """
        Gets the unique list of names of all tables (and views) from the
        databases.

        @rtype: iterable
        @return: all tables and views
        """
        tables = set(self._getViews())
        tables.update(self.engine.table_names(schema=self._mainSchema))
        for schema in self.attached.values():
            tables.update(self.engine.table_names(schema=schema))

        return tables

    def _tableGetter(self):
        """
        Returns a function that retrieves a SQLAlchemy Table object for a given
        table name.
        """
        def getTable(tableName):
            schema = self._findTable(tableName)
            if schema is not None:
                return Table(tableName, self.metadata, autoload=True,
                    autoload_with=self.engine, schema=schema)

            raise KeyError("Table '%s' not found in any database" % tableName)

        return getTable

    def _findTable(self, tableName):
        """
        Gets the schema (database name) of the database that offers the given
        table.

        The databases will be accessed in the order as attached.

        @type tableName: str
        @param tableName: name of table to be located
        @rtype: str
        @return: schema name of database including table
        """
        if self.engine.has_table(tableName, schema=self._mainSchema):
            return self._mainSchema
        else:
            for schema in self.attached.values():
                if self.engine.has_table(tableName, schema=schema):
                    return schema
        return None

    def hasTable(self, tableName):
        """
        Returns C{True} if the given table exists in one of the databases.

        @type tableName: str
        @param tableName: name of table to be located
        @rtype: bool
        @return: C{True} if table is found, C{False} otherwise
        """
        schema = self._findTable(tableName)
        return schema is not None

    def mainHasTable(self, tableName):
        """
        Returns C{True} if the given table exists in the main database.

        @type tableName: str
        @param tableName: name of table to be located
        @rtype: bool
        @return: C{True} if table is found, C{False} otherwise
        """
        return self.engine.has_table(tableName, schema=self._mainSchema)

    #}
    #{ Select commands

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

    def selectScalar(self, request):
        """
        Executes a select query and returns a single variable.

        @param request: SQL request
        @return: a scalar
        """
        result = self.execute(request)
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
        result = self.execute(request)
        return [self._decode(row[0]) for row in result.fetchall()]

    def selectRow(self, request):
        """
        Executes a select query and returns a single table row.

        @param request: SQL request
        @return: a list of scalars
        """
        result = self.execute(request)
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
        result = self.execute(request)
        return [self._decode(tuple(row)) for row in result.fetchall()]
