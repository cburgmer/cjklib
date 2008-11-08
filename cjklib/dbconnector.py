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
Provides simple read access to a SQL database.
"""

import re
import os

class DatabaseConnector:
    """
    A DatabaseConnector provides simple read access to a SQL database.

    On initialisation it connects to a given database. Once connected it's
    select methods can be used to quickly access the database content.

    Supported database types are:
        - MySQL
        - SQLite

    As only standard select commands are issued further systems should be easy
    to incorporate.

    For selecting entries there are for different methods given:
        1. C{select()}: the most general select method
        2. C{selectSoleValue()}: returns entries for only one column
        3. C{selectSingleEntry()}: returns only one entry
        4. C{selectSingleEntrySoleValue()}: returns one single value

    @todo Impl: Timing function with logging of query to allow for optimising
        of queries.
    @todo Impl: Use own exceptions that abstract from the MySQL and SQLite ones.
    @bug:  DatabaseConnector was designed to ease the implementation of SQL
        queries but totally fails at this task.
    @bug:  If one column is specified more than once for a where clause,
        its last definition overwrites the ones before.
    """
    dbconnectInst = None
    """
    Instance of a L{DatabaseConnector} used for all connections to SQL server.
    """
    databaseSettings = None
    """
    Database settings used to create the connector instance.
    """

    @classmethod
    def getDBConnector(cls, databaseSettings = {}):
        """
        Returns a shared L{DatabaseConnector} instance.

        @type databaseSettings: dictionary
        @param databaseSettings: database settings passed to the
            L{DatabaseConnector}, see there for feasible values.
        """
        if cls.databaseSettings and databaseSettings \
            and cls.databaseSettings != databaseSettings:
            cls.dbconnectInst = None

        if not cls.dbconnectInst:
            # get database settings and connect to database
            # if no settings given read from config or assume default
            if len(databaseSettings.keys()) == 0:
                # try to read from config
                databaseSettings = DatabaseConnector.getConfigSettings('cjklib')
                if not ((databaseSettings.has_key('sqliteDatabase') \
                    and databaseSettings['sqliteDatabase']) \
                    or (databaseSettings.has_key('mysqlServer') \
                    and databaseSettings['mysqlServer'])):
                    # default
                    databaseSettings['sqliteDatabase'] = 'cjklib.db'
            cls.dbconnectInst = DatabaseConnector(databaseSettings)
            cls.databaseSettings = databaseSettings
        return cls.dbconnectInst

    @staticmethod
    def getConfigSettings(projectName):
        """
        Gets the SQL connection parameters from a config file.

        @type projectName: string
        @param projectName: name of project which will be used as name of the
            config file
        @rtype: dictionary
        @return: settings that can be used as I{databaseSettings} for making a
            connection to the SQL server
        """
        databaseSettings = {}
        import ConfigParser
        import os
        import os.path
        config = ConfigParser.ConfigParser()
        config.read([os.path.join(os.path.expanduser('~'), '.' + projectName \
                + '.conf'), os.path.join('/', 'etc', projectName + '.conf')])
        dbType = config.get("General", "database_type")
        if dbType == 'SQLite':
            databaseSettings['sqliteDatabase'] = config.get("SQLite", "db_path")
        elif dbType == 'MySQL':
            try:
                databaseSettings['mysqlServer'] = config.get("MySQL",
                    "hostname")
                databaseSettings['mysqlUser'] = config.get("MySQL", "user")
                databaseSettings['mysqlDatabase'] = config.get("MySQL",
                    "database")
                databaseSettings['mysqlPassword'] = config.get("MySQL",
                    "password")
            except ConfigParser.NoOptionError:
                pass
        else:
            raise Error("Error reading config file, database type '" + dbType \
                + "' not recognised")
        return databaseSettings

    def __init__(self, databaseSettings):
        """
        Constructs the DatabaseConnector object and connects to the database
        specified by the options given in databaseSettings.

        @type databaseSettings: dictionary
        @param databaseSettings: This dictionary takes the settings for the
            selected database.

            Either of the keys 'mysqlServer' or 'sqliteDatabase' need to be 
            present so that a connection to a database is opened.
            The following keys are allowed:
                1. mysqlServer: host name of the server (MySQL)
                2. mysqlUser: user name to login with (MySQL)
                3. mysqlPassword: password to login with (MySQL)
                4. mysqlDatabase: name of the database (MySQL)
                5. sqliteDatabase: path to the database (SQLite)
        """
        # get default user name from environment var USER
        if os.environ.has_key('USER'):
            defaultUser = os.environ['USER']
        # set default settings for parameters
        defaultValueDic = {'mysqlServer' : 'localhost',
            'mysqlUser': defaultUser, 'mysqlPassword': '',
            'mysqlDatabase': 'cjklib'}
        databaseSettings = databaseSettings.copy()
        for varName, defValue in defaultValueDic.iteritems():
            if not databaseSettings.has_key(varName):
                databaseSettings[varName] = defValue

        # check for major parameter and load database accordingly
        if databaseSettings.has_key('sqliteDatabase'):
            from pysqlite2 import dbapi2 as sqlite
            self.con = sqlite.connect(databaseSettings['sqliteDatabase'])
            self.dbType = 'SQLite'
        elif databaseSettings.has_key('mysqlServer'):
            import MySQLdb
            self.con = MySQLdb.connect(databaseSettings['mysqlServer'],
                databaseSettings['mysqlUser'],
                databaseSettings['mysqlPassword'],
                databaseSettings['mysqlDatabase'], use_unicode=True,
                charset='utf8')
            self.dbType = 'MySQL'
            self.dbName = databaseSettings['mysqlDatabase']
        else:
            raise ValueError, "no database specified"
        self.cur = self.con.cursor()
        if self.dbType == 'MySQL':
            self.cur.execute('set names utf8')

    def getConnection(self):
        """
        Get the SQL connection object.
        @rtype: object
        @return: the SQL connection object
        """
        return self.con

    def getCursor(self):
        """
        Get the SQL cursor object.

        @rtype: object
        @return: the SQL cursor object
        """
        return self.cur

    def getDatabaseType(self):
        """
        Gets the SQL connection type. Values can be I{MySQL} and I{SQLite}.

        @rtype: object
        @return: the SQL connection object
        """
        return self.dbType

    def escapeString(self, string):
        """
        Escapes the string for use in a SQL command.
        @todo Impl: Implement escaping for SQLite.
        """
        if self.dbType == 'MySQL':
            return self.con.escape_string(string)
        else:
            return string

    def tableExists(self, tableName):
        """
        Returns true if the given table or view exists in the database.

        @type tableName: string
        @param tableName: name of table to check
        @rtype: boolean
        @return: True, if table exists
        """
        if self.getDatabaseType() == 'MySQL':
            return self.selectSingleEntrySoleValue('Information_schema.tables',
                '1', {'table_schema': self.dbName, 'table_name': tableName}) \
                    != None
        elif self.getDatabaseType() == 'SQLite':
            return self.selectSingleEntrySoleValue('sqlite_master', '1',
                {'type': ['table', 'view'], 'name': tableName}) != None

    # select commands

    def getSelectCommand(self, tableNames, columnList, clauses, orderBy=[],
        orderDescending=False, limit=None, distinctValues=False):
        """
        Construct the SQL select command from the given parameters.

        @type tableNames: string or list of strings
        @param tableNames: name(s) of table(s) to query
        @type columnList: list of strings
        @param columnList: name of columns to include in response
        @type clauses: dictionary
        @param clauses: key, value pairs to query the given tables; The key
            represents a column and the corresponding value represents it's
            value that has to be satisfied.

            Value can be either a simple value, or an expression including a SQL
            operator (e.g. C{E{lb}'name': "<> 'Smith'"E{rb}}). Simple values
            like C{'Apple'} or C{'%pple'} are automatically transformed to
            C{"key = 'Apple'"} and C{"key like '%pple'"} correspondingly.
        @type orderBy: list of strings
        @param orderBy: name of columns for ordering output
        @type orderDescending: boolean
        @param orderDescending: indicates that the output is sorted in
            descending order. If not specified but orderBy is given the sort
            order is ascending.
        @type limit: number
        @param limit: specify the maximum count of entries returned
        @type distinctValues: boolean
        @param distinctValues: if true only distinct values will be returned
        @rtype: string
        @return: SQL select command

        @todo Fix:  Escape all column and table names to prevent SQL injection
            attacks, use L{escapeString()}.
        """
        def getClause(column, whereClause):
            """
            Construct a SQL where clause for a given column and clause.

            @type column: string
            @param column: name of the column
            @type whereClause: string or list of strings
            @param whereClause: SQL clause for the given column. If an array is
                passed multiple clauses are created concatenated by an C{or}
                clause.
                Simple values (non strings, or strings without an operator) are
                transformed to a clause including an C{=} or C{like} operator.
            @rtype: string
            @return: SQL where clause
            @todo Fix:  Don't automatically interpret _ or % as placeholders.
            """
            if type(whereClause) in (type([]), type(set())):
                if not whereClause:
                    raise ValueError(\
                        "error creating sql query: empty array provided")
                # tuple used for OR operator, break down into single clauses
                return '(' + " or ".join([getClause(column, entry)
                    for entry in whereClause]) + ')'
            elif not type(whereClause) in (type(""), type(u"")):
                return column + "=" + str(whereClause)
            # TODO interpreting content as command is bad
            elif not re.match('(?i)(not\s)?(=|!=|<>|in\s|' \
                + 'like\s|is\s|between\s|match\s|' \
                + '<|>|<=|>=)', whereClause) \
                or whereClause == '':
                value = "'" + whereClause.replace("'", "''") + "'"
                #if value.find('%') >= 0 or value.find('_')>=0:
                    #eqStatement = " like " + value
                    #return column + eqStatement
                #else:
                    #eqStatement = "=" + value
                    #return column + eqStatement
                eqStatement = " like " + value
                return column + eqStatement
            else:
                return column + ' ' + whereClause

        whereClause = ''
        if type(clauses) == type([]):
            # list of dictionaries represents alternative matches
            whereClause = " WHERE " + " OR ".join(["(" \
                + " AND ".join([getClause(key, clauseDict[key])
                for key in clauseDict.keys()]) + ")" for clauseDict in clauses])
        elif len(clauses.keys()) > 0:
            whereClause = " WHERE " + " AND ".join([getClause(key, clauses[key])
                for key in clauses.keys()])
        orderByString = ''
        if len(orderBy) > 0:
            if orderDescending:
                order = 'DESC'
            else:
                order = 'ASC'
            orderByString = " ORDER BY " + ", ".join(orderBy) + ' ' + order
        limitString = ''
        if limit:
            limitString = ' LIMIT ' + str(limit)
        if type(tableNames) == type([]):
            tableString = ', '.join(tableNames)
        else:
            tableString = tableNames
        selectBegin = "SELECT "
        if distinctValues:
            selectBegin = selectBegin + "DISTINCT "

        return selectBegin + ", ".join(columnList) + " FROM " + tableString \
            + whereClause + orderByString + limitString

    def select(self, tableNames, columnList, clauses={}, orderBy=[],
        orderDescending=False, limit=None, distinctValues=False):
        """
        Run a general SQL select query for the specified parameters.

        @type tableNames: string or list of strings
        @param tableNames: name(s) of table(s) to query
        @type columnList: list of strings
        @param columnList: name of columns to include in response
        @type clauses: dictionary
        @param clauses: key, value pairs to query the given tables; The key
            represents a column and the corresponding value represents it's
            value that has to be satisfied.

            Value can be either a simple value, or an expression including a SQL
            operator (e.g. C{E{lb}'name': "<> 'Smith'"E{rb}}). Simple values
            like C{'Apple'} or C{'%pple'} are automatically transformed to
            C{"key = 'Apple'"} and C{"key like '%pple'"} correspondingly.
        @type orderBy: list of strings
        @param orderBy: name of columns for ordering output
        @type orderDescending: boolean
        @param orderDescending: indicates that the output is sorted in
            descending order. If not specified but orderBy is given the sort
            order is ascending.
        @type limit: number
        @param limit: specify the maximum count of entries returned
        @type distinctValues: boolean
        @param distinctValues: if true only distinct values will be returned
        @rtype: list of string tuples
        @return: multiple found entries with multiple columns
        """
        searchCmd = self.getSelectCommand(tableNames, columnList, clauses,
            orderBy, orderDescending, limit, distinctValues) + ';'
        self.cur.execute(searchCmd)
        returnList = list(self.cur.fetchall())
        for i, entry in enumerate(returnList): # TODO stupid recoding
            entry = list(entry)
            for j, cell in enumerate(entry):
                if type(cell) == type(""):
                    entry[j] = cell.decode('utf8')
            returnList[i] = tuple(entry)
        return returnList

    def selectSoleValue(self, tableNames, column, clauses={}, orderBy=[],
        orderDescending=False, limit=None, distinctValues=False):
        """
        Run a SQL select query for only one column for the specified parameters.

        @type tableNames: string or list of strings
        @param tableNames: name(s) of table(s) to query
        @type column: string
        @param column: name of column for response
        @type clauses: dictionary
        @param clauses: key, value pairs to query the given tables; The key
            represents a column and the corresponding value represents it's
            value that has to be satisfied.

            Value can be either a simple value, or an expression including a SQL
            operator (e.g. C{E{lb}'name': "<> 'Smith'"E{rb}}). Simple values
            like C{'Apple'} or C{'%pple'} are automatically transformed to
            C{"key = 'Apple'"} and C{"key like '%pple'"} correspondingly.
        @type orderBy: list of strings
        @param orderBy: name of columns for ordering output
        @type orderDescending: boolean
        @param orderDescending: indicates that the output is sorted in
            descending order. If not specified but orderBy is given the sort
            order is ascending.
        @type limit: number
        @param limit: specify the maximum count of entries returned
        @type distinctValues: boolean
        @param distinctValues: if true only distinct values will be returned
        @rtype: list of strings
        @return: multiple found entries with one column each
        """
        resultList = []
        for row in self.select(tableNames, [column], clauses, orderBy,
            orderDescending, limit, distinctValues):
            resultList.append(row[0])
        return resultList

    def selectSingleEntry(self, tableNames, columnList, clauses,
        distinctValues=False):
        """
        Run a SQL select query resulting in only one entry for the specified
        parameters.

        @type tableNames: string or list of strings
        @param tableNames: name(s) of table(s) to query
        @type columnList: list of strings
        @param columnList: name of columns to include in response
        @type clauses: dictionary
        @param clauses: key, value pairs to query the given tables; The key
            represents a column and the corresponding value represents it's
            value that has to be satisfied.

            Value can be either a simple value, or an expression including a SQL
            operator (e.g. C{E{lb}'name': "<> 'Smith'"E{rb}}). Simple values
            like C{'Apple'} or C{'%pple'} are automatically transformed to
            C{"key = 'Apple'"} and C{"key like '%pple'"} correspondingly.
        @type distinctValues: boolean
        @param distinctValues: if true only distinct values will be returned
        @rtype: string tuple
        @return: one found entry with multiple columns
        """
        # make sure the user doesn't specify a string, e.g. using wrong method
        if type(columnList) != type([]):
            raise ValueError("type of parameter columnList is not a list type")
        resultList = self.select(tableNames, columnList, clauses,
            distinctValues=distinctValues)
        assert not resultList or len(resultList) == 1
        if resultList:
            return resultList[0]

    def selectSingleEntrySoleValue(self, tableNames, column, clauses,
        distinctValues=False):
        """
        Run a SQL select query for only one column resulting in only one entry
        for the specified parameters.

        @type tableNames: string or list of strings
        @param tableNames: name(s) of table(s) to query
        @type column: string
        @param column: name of column for response
        @type clauses: dictionary
        @param clauses: key, value pairs to query the given tables; The key
            represents a column and the corresponding value represents it's
            value that has to be satisfied.

            Value can be either a simple value, or an expression including a SQL
            operator (e.g. C{E{lb}'name': "<> 'Smith'"E{rb}}). Simple values
            like C{'Apple'} or C{'%pple'} are automatically transformed to
            C{"key = 'Apple'"} and C{"key like '%pple'"} correspondingly.
        @type distinctValues: boolean
        @param distinctValues: if true only distinct values will be returned
        @rtype: string
        @return: one found entry with one column
        """
        row = self.selectSingleEntry(tableNames, [column], clauses,
            distinctValues)
        if row:
            return row[0]
