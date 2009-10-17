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
Provides the build class for the cjklib package.

Each table that needs to be created has to be implemented by subclassing a
L{TableBuilder}. The L{DatabaseBuilder} is the central instance for managing the
build process. As the creation of a table can depend on other tables the
DatabaseBuilder keeps track of dependencies to process a build in the correct
order.

Building is tested on the following storage methods:
    - SQLite
    - MySQL

Examples
========
The following examples should give a quick view into how to use this
package.
    - Create the DatabaseBuilder object with default settings (read from
        cjklib.conf or using 'cjklib.db' in same directory as default):

        >>> from cjklib import build
        >>> dbBuilder = build.DatabaseBuilder(dataPath=['./cjklib/data/'])
        Removing conflicting builder(s) 'StrokeCountBuilder' in favour of \
'CombinedStrokeCountBuilder'
        Removing conflicting builder(s) 'CharacterResidualStrokeCountBuilder' \
in favour of 'CombinedCharacterResidualStrokeCountBuilder'

    - Build the table of Jyutping syllables from a csv file:

        >>> dbBuilder.build(['JyutpingSyllables'])
        building table 'JyutpingSyllables' with builder
        'JyutpingSyllablesBuilder'...
        Reading table definition from file './cjklib/data/jyutpingsyllables.sql'
        Reading table 'JyutpingSyllables' from file
        './cjklib/data/jyutpingsyllables.csv'
"""

import types
import locale
import sys
import os.path

from sqlalchemy.exceptions import OperationalError

from cjklib import dbconnector
from cjklib import exception

class DatabaseBuilder:
    """
    DatabaseBuilder provides the main class for building up a database for the
    cjklib package.

    It contains all L{TableBuilder} classes and a dependency graph to handle
    build requests.
    """
    def __init__(self, **options):
        """
        Constructs the DatabaseBuilder.

        To modify the behaviour of L{TableBuilder}s global or local options can
        be specified, see L{getBuilderOptions()}.

        @keyword databaseUrl: database connection setting in the format
            C{driver://user:pass@host/database}.
        @keyword dbConnectInst: instance of a L{DatabaseConnector}
        @keyword dataPath: optional list of paths to the data file(s)
        @keyword quiet: if C{True} no status information will be printed to
            stderr
        @keyword rebuildDepending: if C{True} existing tables that depend on
            updated tables will be dropped and built from scratch
        @keyword rebuildExisting: if C{True} existing tables will be dropped and
            built from scratch
        @keyword noFail: if C{True} build process won't terminate even if one
            table fails to build
        @keyword prefer: list of L{TableBuilder} names to prefer in conflicting
            cases
        @keyword additionalBuilders: list of externally provided TableBuilders
        @raise ValueError: if two different options from two different builder
            collide.
        """
        if 'dataPath' not in options:
            # look for data underneath the build module
            from pkg_resources import Requirement, resource_filename
            options['dataPath'] \
                = resource_filename(Requirement.parse("cjklib"), "cjklib/data")
        elif type(options['dataPath']) in (type(''), type(u'')):
            # wrap as list
            options['dataPath'] = [options['dataPath']]

        self.quiet = options.get('quiet', False)
        """Controls status information printed to stderr"""
        self.rebuildDepending = options.pop('rebuildDepending', True)
        """Controls if tables that depend on updated tables will be rebuilt."""
        self.rebuildExisting = options.pop('rebuildExisting', True)
        """Controls if existing tables will be rebuilt."""
        self.noFail = options.pop('noFail', False)
        """Controls if build process terminate on failed tables."""
        # get connector to database
        databaseUrl = options.pop('databaseUrl', None)
        if 'dbConnectInst' in options:
            self.db = options.pop('dbConnectInst')
        else:
            self.db = dbconnector.DatabaseConnector.getDBConnector(databaseUrl)
            """L{DatabaseConnector} instance"""

        # get TableBuilder classes
        tableBuilderClasses = DatabaseBuilder.getTableBuilderClasses(
            set(options.pop('prefer', [])), quiet=self.quiet,
            additionalBuilders=options.pop('additionalBuilders', []))

        # build lookup
        self._tableBuilderLookup = {}
        for tableBuilder in tableBuilderClasses:
            if tableBuilder.PROVIDES in self._tableBuilderLookup:
                raise Exception("Table '%s' provided by several builders" \
                    % tableBuilder.PROVIDES)
            self._tableBuilderLookup[tableBuilder.PROVIDES] = tableBuilder

        # options for TableBuilders
        self.options = options
        """Table builder options dictionary"""

    def getBuilderOptions(self, builderClass, ignoreUnknown=False):
        """
        Gets a dictionary of options for the given builder that were specified
        to the DatabaseBuilder.

        Options included are I{global} options understood by the builder (e.g.
        C{'dataPath'}) or I{local} options given in the formats
        C{'--BuilderClassName-option'} or C{'--TableName-option'}. For example
        C{'--Unihan-wideBuild'} sets the option C{'wideBuild'} for all builders
        providing the C{Unihan} table. C{'--BuilderClassName-option'} has
        precedence over C{'--TableName-option'}.

        @type builderClass: classobj
        @param builderClass: L{TableBuilder} class
        @rtype: dict
        @return: dictionary of options for the given table builder.
        @type ignoreUnknown: bool
        @param ignoreUnknown: if set to C{True} unknown options will be ignored,
            otherwise a ValueError is raised.
        @raise ValueError: if unknown option is specified and ignoreUnknown is
            C{False}
        """
        understoodOptions = builderClass.getDefaultOptions()

        # set all globals first
        builderOptions = dict([(o, v) for o, v in self.options.items() \
            if not o.startswith('--')])

        # no set (and maybe overwrite with) locals
        builderSpecificOptions = {}
        for option, value in self.options.items():
            if option.startswith('--'):
                # local options
                className, optionName = option[2:].split('-', 1)

                if className == builderClass.__name__ \
                    or className == builderClass.PROVIDES:
                    if optionName in understoodOptions:
                        if className == builderClass.__name__:
                            # queue for later adding
                            builderSpecificOptions[optionName] = value
                        else:
                            builderOptions[optionName] = value
                    elif className and not self.quiet:
                        errorMsg = "Unknown option '%s' for builder '%s'" \
                            % (optionName, className)
                        if ignoreUnknown:
                            warn(errorMsg + ", ignoring")
                        else:
                            raise ValueError(errorMsg)

        # now add builder specific options that can overwrite table options
        builderOptions.update(builderSpecificOptions)

        return builderOptions

    def setBuilderOptions(self, builderClass, options, exclusive=False):
        """
        Sets the options for the given builder that were specified.

        @type builderClass: classobj
        @param builderClass: L{TableBuilder} class
        @type options: dict
        @param options: dictionary of options for the given table builder.
        @type exclusive: bool
        @param exclusive: if set to C{True} unspecified options will be set to
            the default value.
        @raise ValueError: if unknown option is specified
        """
        understoodOptions = builderClass.getDefaultOptions()
        newOptions = {}

        for option, value in options.items():
            if option not in understoodOptions:
                raise ValueError("Unknown option '%s' for builder '%s'" \
                    % (option, builderClass.__name__))
            localOptName = '--%s-%s' % (builderClass.__name__, option)
            newOptions[localOptName] = value

        if exclusive:
            for option, defaultValue in understoodOptions.items():
                if option not in options:
                    localOptName = '--%s-%s' % (builderClass.__name__, option)
                    newOptions[localOptName] = defaultValue

        self.options.update(newOptions)

    def build(self, tables):
        """
        Builds the given tables.

        @type tables: list
        @param tables: list of tables to build
        @raise IOError: if a table builder fails to read its data; only if
            L{noFail} is set to C{False}
        """
        if type(tables) != type([]):
            tables = [tables]

        if not self.quiet:
            warn("Building database '%s'" % self.db.databaseUrl)

        # remove tables that don't need to be rebuilt
        filteredTables = []
        for table in tables:
            if table not in self._tableBuilderLookup:
                raise exception.UnsupportedError("Table '%s' not provided" \
                    % table)

            if self.needsRebuild(table):
                filteredTables.append(table)
            else:
                if not self.quiet:
                    warn("Skipping table '%s' because it already exists" \
                        % table)
        tables = filteredTables

        # get depending tables that need to be updated when dependencies change
        dependingTables = []
        if self.rebuildDepending:
            dependingTables = self.getRebuiltDependingTables(tables)
            if dependingTables:
                if not self.quiet:
                    warn("Tables rebuilt because of dependencies updated: '" \
                        +"', '".join(dependingTables) + "'")
                tables.extend(dependingTables)

        # get table list according to dependencies
        buildDependentTables = self.getBuildDependentTables(tables)
        buildTables = set(tables) | buildDependentTables
        # get build order and remove tables we don't need to build
        builderClasses = self.getClassesInBuildOrder(buildTables)

        # build tables
        if not self.quiet and self.rebuildExisting:
            warn("Rebuilding tables and overwriting old ones...")
        builderClasses.reverse()
        self.instancesUnrequestedTable = set()
        while builderClasses:
            builder = builderClasses.pop()
            # check first if the table will only be created for resolving
            # dependencies and note it down for deletion
            transaction = self.db.connection.begin()

            try:
                # get specific options given to the DatabaseBuilder
                options = self.getBuilderOptions(builder, ignoreUnknown=True)
                options['dbConnectInst'] = self.db
                instance = builder(**options)
                # mark tables as deletable if its only provided because of
                #   dependencies and the table doesn't exists yet
                if builder.PROVIDES in buildDependentTables \
                    and not self.db.engine.has_table(builder.PROVIDES):
                    self.instancesUnrequestedTable.add(instance)

                if self.db.engine.has_table(builder.PROVIDES):
                    if not self.quiet:
                        warn("Removing previously built table '%s'" \
                            % builder.PROVIDES)
                    instance.remove()

                if not self.quiet:
                    warn("Building table '%s' with builder '%s'..." \
                        % (builder.PROVIDES, builder.__name__))

                instance.build()
                transaction.commit()
            except IOError, e:
                transaction.rollback()
                # data not available, can't build table
                if self.noFail:
                    if not self.quiet:
                        warn("Building table '%s' failed: '%s', skipping" \
                            % (builder.PROVIDES, str(e)))
                    dependingTables = [builder.PROVIDES]
                    remainingBuilderClasses = []
                    for clss in builderClasses:
                        if set(clss.DEPENDS) & set(dependingTables):
                            # this class depends on one being removed
                            dependingTables.append(clss.PROVIDES)
                        else:
                            remainingBuilderClasses.append(clss)
                    if not self.quiet and len(dependingTables) > 1:
                        warn("Ignoring depending table(s) '%s'" \
                            % "', '".join(dependingTables[1:]))
                    builderClasses = remainingBuilderClasses
                else:
                    raise
            except Exception, e:
                transaction.rollback()
                raise

        self.clearTemporary()

    def clearTemporary(self):
        """
        Removes all tables only built temporarily as to satisfy build
        dependencies. This method is called before L{build()} terminates. If the
        build process is interruptes (e.g. by the user pressing Ctrl+C), this
        method should be called as to make sure that these temporary tables are
        removed and not included in later builds.
        """
        # remove tables that where only created as build dependencies
        if 'instancesUnrequestedTable' in self.__dict__:
            for instance in self.instancesUnrequestedTable:
                if not self.quiet:
                    warn("Removing table '" + instance.PROVIDES \
                        + "' as it was only created to solve build " \
                        + "dependencies")
                try:
                    instance.remove()
                except OperationalError:
                    pass

    def remove(self, tables):
        """
        Removes the given tables.

        @type tables: list
        @param tables: list of tables to remove
        @raise UnsupportedError: if an unsupported table is given.
        """
        if type(tables) != type([]):
            tables = [tables]

        tableBuilderClasses = []
        for table in set(tables):
            if table not in self._tableBuilderLookup:
                raise exception.UnsupportedError("Table '%s' not provided"
                    % table)
            tableBuilderClasses.append(self._tableBuilderLookup[table])

        for builder in tableBuilderClasses:
            if self.db.engine.has_table(builder.PROVIDES):
                if not self.quiet:
                    warn("Removing previously built table '%s'"
                        % builder.PROVIDES)

                # get specific options given to the DatabaseBuilder
                options = self.getBuilderOptions(builder, ignoreUnknown=True)
                options['dbConnectInst'] = self.db
                instance = builder(**options)
                instance.remove()

    def needsRebuild(self, tableName):
        """
        Returns true if either rebuild is turned on by default or we build into
        database and the table doesn't exist yet.

        @type tableName: classobj
        @param tableName: L{TableBuilder} class
        @rtype: bool
        @return: C{True}, if table needs to be rebuilt
        """
        if self.rebuildExisting:
            return True
        else:
            return not self.db.engine.has_table(tableName)

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
            if self.db.engine.has_table(table):
                skippedTables.add(table)
                return

            dependedTablesNames.add(table)

            # add dependent tables if needed (recursively)
            if table not in self._tableBuilderLookup:
                # either we have no builder or the builder was removed in
                # favour of another builder that shares at least one table
                # with the removed one
                raise exception.UnsupportedError("table '%s'" + table \
                    + " not provided, might be related to conflicting " \
                    + "builders")
            builderClass = self._tableBuilderLookup[table]
            for dependantTable in builderClass.DEPENDS:
                solveDependencyRecursive(dependantTable)

        tableNames = set(tableNames)
        dependedTablesNames = set()
        skippedTables = set()

        for table in tableNames:
            builderClass = self._tableBuilderLookup[table]
            for depededTable in builderClass.DEPENDS:
                solveDependencyRecursive(depededTable)

        if not self.quiet and skippedTables:
            warn("Newly built tables depend on table(s) '" \
                + "', '".join(skippedTables) \
                + "' but skipping because they already exist")
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
                builderClass = self._tableBuilderLookup[table]
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

        needRebuild = set()
        for tableName in dependingTables:
            if self.db.engine.has_table(tableName):
                needRebuild.add(tableName)
        return needRebuild

    def getClassesInBuildOrder(self, tableNames):
        """
        Gets the build order for the given table names.

        @type tableNames: list of str
        @param tableNames: list of names of tables to build
        @rtype: list of classobj
        @return: L{TableBuilder}s in build order
        @raise UnsupportedError: if an unsupported table is given.
        """
        # get dependencies and save order
        tableBuilderClasses = []
        for table in set(tableNames):
            if table not in self._tableBuilderLookup:
                # either we have no builder or the builder was removed in favour
                # of another builder that shares at least one table with the
                # removed one
                raise exception.UnsupportedError("table '" + table \
                    + "' not provided, might be related to conflicting " \
                    + "builders")
            tableBuilderClasses.append(self._tableBuilderLookup[table])
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
                    dependencyOrder.append(builderClass)
                    includedTableNames.add(builderClass.PROVIDES)
                    tableBuilderClasses.remove(builderClass)
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
        return dependencyOrder

    @staticmethod
    def _checkOptionUniqueness(tableBuilderClasses):
        # check if no option appears multiple times with different
        #   characteristics
        optionDefaultValues = {}
        optionMetaData = {}
        for builder in tableBuilderClasses:
            for option, defaultValue in builder.getDefaultOptions().items():
                # check default value
                if option in optionDefaultValues:
                    thatValue, thatBuilder = optionDefaultValues[option]
                    if thatValue != defaultValue:
                        raise ValueError("Option '%s' defined in %s and %s" \
                                % (option, builder, thatBuilder) \
                            + " but different default values: %s and %s" \
                                % (repr(defaultValue), repr(thatValue)))
                optionDefaultValues[option] = (defaultValue, builder)

                # check meta data
                try:
                    metaData = builder.getOptionMetaData(option)
                except KeyError:
                    continue
                if option in optionMetaData:
                    thatMetaData, thatBuilder = optionMetaData[option]
                    if thatMetaData != metaData:
                        raise ValueError("Option '%s' defined in %s and %s" \
                                % (option, builder, thatBuilder) \
                            + " but different meta data: %s and %s" \
                                % (repr(metaData), repr(thatMetaData)))
                optionMetaData[option] = (metaData, builder)

    @staticmethod
    def getTableBuilderClasses(preferClassNameSet=set(), resolveConflicts=True,
        quiet=True, additionalBuilders=None):
        """
        Gets all classes in module that implement L{TableBuilder}.

        @type preferClassNameSet: set of str
        @param preferClassNameSet: set of L{TableBuilder} names to prefer in
            conflicting cases, resolveConflicting must be True to take effect
            (default)
        @type resolveConflicts: bool
        @param resolveConflicts: if true conflicting builders will be removed
            so that only one builder is left per Table.
        @type quiet: bool
        @param quiet: if true no status information will be printed to stderr
        @type additionalBuilders: list of classobj
        @param additionalBuilders: list of externally provided TableBuilders
        @rtype: set
        @return: list of all classes inheriting form L{TableBuilder} that
            provide a table (i.d. non abstract implementations), with its name
            as key
        @raise ValueError: if two different options with the same name collide.
        """
        additionalBuilders = additionalBuilders or []
        buildModule = __import__("cjklib.build.builder")
        # get all classes that inherit from TableBuilder
        tableBuilderClasses = set([clss \
            for clss in buildModule.build.builder.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, buildModule.build.builder.TableBuilder) \
            and clss.PROVIDES])
        # add additionally provided
        tableBuilderClasses.update(additionalBuilders)

        # check for conflicting builders and keep only one per conflicting group
        # group builders first
        tableToBuilderMapping = {}
        for clss in tableBuilderClasses:
            if clss.PROVIDES not in tableToBuilderMapping:
                tableToBuilderMapping[clss.PROVIDES] = set()

            tableToBuilderMapping[clss.PROVIDES].add(clss)

        preferClassSet = set([clss for clss in tableBuilderClasses \
            if clss.__name__ in preferClassNameSet])

        if resolveConflicts:
            # now check conflicting and choose preferred if given
            for builderClssSet in tableToBuilderMapping.values():
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
                    warn("Removing conflicting builder(s) '%s'" \
                            % "', '".join(
                                [clss.__name__ for clss in builderClssSet]) \
                        + " in favour of '%s'" % preferred.__name__)
                # remove other conflicting
                for clss in builderClssSet:
                    tableBuilderClasses.remove(clss)

        # check if all options are unique
        DatabaseBuilder._checkOptionUniqueness(tableBuilderClasses)

        return tableBuilderClasses

    @staticmethod
    def getSupportedTables():
        """
        Gets names of supported tables.

        @rtype: list of str
        @return: names of tables
        """
        classList = DatabaseBuilder.getTableBuilderClasses(
            resolveConflicts=False)
        return set([clss.PROVIDES for clss in classList])

    def getCurrentSupportedTables(self):
        """
        Gets names of tables supported by this instance of the database builder.

        This list can have more entries then L{getSupportedTables()} as
        additional external builders can be supplied on instantiation.

        @rtype: list of str
        @return: names of tables
        """
        return set(self._tableBuilderLookup.keys())

    def getTableBuilder(self, tableName):
        """
        Gets the L{TableBuilder} used by this instance of the database builder
        to build the given table.

        @type tableName: str
        @param tableName: name of table
        @rtype: classobj
        @return: L{TableBuilder} used to build the given table by this build
            instance.
        @raise UnsupportedError: if an unsupported table is given.
        """
        if tableName not in self._tableBuilderLookup:
            # either we have no builder or the builder was removed in favour
            # of another builder that shares at least one table with the
            # removed one
            raise exception.UnsupportedError("table '%s'" + tableName \
                + " not provided, might be related to conflicting " \
                + "builders")

        return self._tableBuilderLookup[tableName]

    def isOptimizable(self):
        """
        Checks if the current database supports optimization.

        @rtype: boolean
        @return: True if optimizable, False otherwise
        """
        return self.db.engine.name in ['sqlite']

    def optimize(self):
        """
        Optimizes the current database.

        @raise Exception: if database does not support optimization
        @raise OperationalError: if optimization failed
        """
        if self.db.engine.name == 'sqlite':
            self.db.execute('VACUUM')
        else:
            raise Exception('Database does not seem to support optimization')

#{ Global methods

def warn(message):
    """
    Prints the given message to stderr with the system's default encoding.

    @type message: str
    @param message: message to print
    """
    print >> sys.stderr, message.encode(locale.getpreferredencoding(),
        'replace')
