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
Builds the library's database.
"""

__all__ = ["DatabaseBuilder"]

import types
import locale
import sys
import os.path

from sqlalchemy.exceptions import OperationalError

from cjklib import dbconnector
from cjklib import exception
from cjklib.util import locateProjectFile

class DatabaseBuilder:
    """
    DatabaseBuilder provides the main class for building up a database for the
    cjklib package.

    It contains all :class:`~cjklib.build.builder.TableBuilder` classes and a
    dependency graph to handle build requests.
    """
    def __init__(self, **options):
        """
        To modify the behaviour of :class:`~cjklib.build.builder.TableBuilder`
        instances, global or local options can be specified, see
        :meth:`~cjklib.build.builder.TableBuilder.getBuilderOptions`.

        :keyword databaseUrl: database connection setting in the format
            ``driver://user:pass@host/database``.
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`
        :keyword dataPath: optional list of paths to the data file(s)
        :keyword quiet: if ``True`` no status information will be printed to
            stderr
        :keyword rebuildDepending: if ``True`` existing tables that depend on
            updated tables will be dropped and built from scratch
        :keyword rebuildExisting: if ``True`` existing tables will be
            dropped and built from scratch
        :keyword noFail: if ``True`` build process won't terminate even if one
            table fails to build
        :keyword prefer: list of :class:`~cjklib.build.builder.TableBuilder`
            names to prefer in conflicting cases
        :keyword additionalBuilders: list of externally provided TableBuilders
        :raise ValueError: if two different options from two different builder
            collide.
        """
        if 'dataPath' not in options:
            # look for data underneath the build module
            projectDataPath = locateProjectFile('cjklib/data', 'cjklib')
            if not projectDataPath:
                projectDataPath = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), '../data')
            options['dataPath'] = [projectDataPath]

        elif isinstance(options['dataPath'], basestring):
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
            self.db = dbconnector.getDBConnector(
                {'sqlalchemy.url': databaseUrl})
            """:class:`~cjklib.dbconnector.DatabaseConnector` instance"""

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

        Options included are *global* options understood by the builder (e.g.
        ``'dataPath'``) or *local* options given in the formats
        ``'--BuilderClassName-option'`` or ``'--TableName-option'``. For
        example ``'--Unihan-wideBuild'`` sets the option ``'wideBuild'``
        for all builders providing the ``Unihan`` table.
        ``'--BuilderClassName-option'`` has precedence over
        ``'--TableName-option'``.

        :type builderClass: classobj
        :param builderClass: :class:`~cjklib.build.builder.TableBuilder` class
        :type ignoreUnknown: bool
        :param ignoreUnknown: if set to ``True`` unknown options will be
            ignored, otherwise a ValueError is raised.
        :rtype: dict
        :return: dictionary of options for the given table builder.
        :raise ValueError: if unknown option is specified and ignoreUnknown is
            ``False``
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

        :type builderClass: classobj
        :param builderClass: :class:`~cjklib.build.builder.TableBuilder` class
        :type options: dict
        :param options: dictionary of options for the given table builder.
        :type exclusive: bool
        :param exclusive: if set to ``True`` unspecified options will be set to
            the default value.
        :raise ValueError: if unknown option is specified
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

        :type tables: list
        :param tables: list of tables to build
        :raise IOError: if a table builder fails to read its data; only if
            :attr:`~cjklib.build.DatabaseBuilder.noFail` is set to ``False``
        """
        if type(tables) != type([]):
            tables = [tables]

        if not self.quiet:
            warn("Building database '%s'" % self.db.databaseUrl)
            if self.db.attached:
                warn("Reading from additional databases '%s'"
                    % "', '".join(self.db.attached.keys()))

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
            # report tables that should be updated but lie outside our scope
            if not self.quiet:
                externalDependingTables \
                    = self.getExternalRebuiltDependingTables(tables)
                if externalDependingTables:
                    warn("Ignoring tables with dependencies updated"
                        + " but belonging to attached databases: '" \
                        + "', '".join(externalDependingTables) + "'")

            dependingTables = self.getRebuiltDependingTables(tables)
            if dependingTables:
                if not self.quiet:
                    warn("Tables rebuilt because of dependencies updated: '" \
                        + "', '".join(dependingTables) + "'")
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
        self._instancesUnrequestedTable = set()
        while builderClasses:
            builder = builderClasses.pop()

            transaction = self.db.connection.begin()

            try:
                # get specific options given to the DatabaseBuilder
                options = self.getBuilderOptions(builder, ignoreUnknown=True)
                options['dbConnectInst'] = self.db
                instance = builder(**options)
                # mark tables as deletable if its only provided because of
                #   dependencies and the table doesn't exists yet
                if builder.PROVIDES in buildDependentTables \
                    and not self.db.mainHasTable(builder.PROVIDES):
                    self._instancesUnrequestedTable.add(instance)

                if self.db.mainHasTable(builder.PROVIDES):
                    # will only remove the table if found in the main database
                    if not self.quiet:
                        warn("Removing previously built table '%s'"
                            % builder.PROVIDES)
                    instance.remove()

                if not self.quiet:
                    warn("Building table '%s' with builder '%s'..."
                        % (builder.PROVIDES, builder.__name__))

                # remove old metadata
                if builder.PROVIDES in self.db.tables:
                    del self.db.tables[builder.PROVIDES]

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
                    if not self.quiet: warn("Error")
                    self.clearTemporary()
                    raise
            except Exception, e:
                transaction.rollback()
                if not self.quiet: warn("Error")
                self.clearTemporary()
                raise

        self.clearTemporary()

    def clearTemporary(self):
        """
        Removes all tables only built temporarily as to satisfy build
        dependencies. This method is called before
        :meth:`~cjklib.build.DatabaseBuilder.build` terminates. If the
        build process is interruptes (e.g. by the user pressing Ctrl+C), this
        method should be called as to make sure that these temporary tables are
        removed and not included in later builds.
        """
        # remove tables that where only created as build dependencies
        if hasattr(self, '_instancesUnrequestedTable'):
            for instance in self._instancesUnrequestedTable:
                if not self.quiet:
                    warn("Removing table '" + instance.PROVIDES \
                        + "' as it was only created to solve build " \
                        + "dependencies")
                try:
                    instance.remove()
                except OperationalError:
                    pass
                # remove old metadata
                if instance.PROVIDES in self.db.tables:
                    del self.db.tables[instance.PROVIDES]
            del self._instancesUnrequestedTable

    def remove(self, tables):
        """
        Removes the given tables from the main database.

        :type tables: list
        :param tables: list of tables to remove
        :raise UnsupportedError: if an unsupported table is given.
        :rtype: list
        :return: names of deleted tables, might be smaller than the actual list
        """
        if type(tables) != type([]):
            tables = [tables]

        tableBuilderClasses = []
        for table in set(tables):
            if table not in self._tableBuilderLookup:
                raise exception.UnsupportedError("Table '%s' not provided"
                    % table)
            tableBuilderClasses.append(self._tableBuilderLookup[table])

        removed = []
        for builder in tableBuilderClasses:
            if self.db.mainHasTable(builder.PROVIDES):
                if not self.quiet:
                    warn("Removing previously built table '%s'"
                        % builder.PROVIDES)

                # get specific options given to the DatabaseBuilder
                options = self.getBuilderOptions(builder, ignoreUnknown=True)
                options['dbConnectInst'] = self.db
                instance = builder(**options)
                instance.remove()
                removed.append(builder.PROVIDES)
                # remove old metadata
                if builder.PROVIDES in self.db.tables:
                    del self.db.tables[builder.PROVIDES]

        return removed

    def needsRebuild(self, tableName):
        """
        Returns ``True`` if either rebuild is turned on by default or the table
        does not exist yet in any of the databases.

        :type tableName: str
        :param tableName: table name
        :rtype: bool
        :return: ``True``, if table needs to be rebuilt
        """
        if self.rebuildExisting:
            return True
        else:
            return not self.db.hasTable(tableName)

    def getBuildDependentTables(self, tableNames):
        """
        Gets the name of the tables that needs to be built to resolve
        dependencies.

        :type tableNames: list of str
        :param tableNames: list of tables to build
        :rtype: list of str
        :return: names of tables needed to resolve dependencies
        """
        def solveDependencyRecursive(table):
            """
            Gets all tables on which the given table depends and that need to be
            rebuilt. Also will mark tables skipped which won't be rebuilt.

            Uses parent's variables to store data.

            :type table: str
            :param table: table name for which to solve dependencies
            """
            if table in tableNames:
                # don't add dependant tables if they are given explicitly
                return
            if self.db.hasTable(table):
                skippedTables.add(table)
                return

            dependedTablesNames.add(table)

            # add dependent tables if needed (recursively)
            if table not in self._tableBuilderLookup:
                # either we have no builder or the builder was removed in
                # favour of another builder that shares at least one table
                # with the removed one
                raise exception.UnsupportedError("Table '%s'" % table \
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

        :type tableNames: list of str
        :param tableNames: list of tables
        :rtype: list of str
        :return: names of tables that depend on given tables
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

        :type tableNames: list of str
        :param tableNames: list of tables
        :rtype: list of str
        :return: names of tables that need to be rebuilt because of dependencies
        """
        dependingTables = self.getDependingTables(tableNames)

        needRebuild = set()
        for tableName in dependingTables:
            if self.db.mainHasTable(tableName):
                needRebuild.add(tableName)
        return needRebuild

    def getExternalRebuiltDependingTables(self, tableNames):
        """
        Gets the name of the tables that depend on the given tables to be built
        and already exist similar to
        :meth:`~cjklib.build.DatabaseBuilder.getRebuiltDependingTables`
        but only for tables of attached databases.

        :type tableNames: list of str
        :param tableNames: list of tables
        :rtype: list of str
        :return: names of tables of attached databsaes that need to be rebuilt
            because of dependencies
        """
        dependingTables = self.getDependingTables(tableNames)

        needRebuild = set()
        for tableName in dependingTables:
            if (not self.db.mainHasTable(tableName)
                and self.db.hasTable(tableName)):
                needRebuild.add(tableName)
        return needRebuild

    def getClassesInBuildOrder(self, tableNames):
        """
        Gets the build order for the given table names.

        :type tableNames: list of str
        :param tableNames: list of names of tables to build
        :rtype: list of classobj
        :return: :class:`~cjklib.build.builder.TableBuilder` classes in build
            order
        :raise UnsupportedError: if an unsupported table is given.
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

        :type tableBuilderClasses: list of classobj
        :param tableBuilderClasses: list of
            :class:`~cjklib.build.builder.TableBuilder` classes
        :rtype: list of classobj
        :return: the given classes ordered in build dependency order
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
    def getTableBuilderClasses(preferClassNameSet=None, resolveConflicts=True,
        quiet=True, additionalBuilders=None):
        """
        Gets all classes in module that implement
        :class:`~cjklib.build.builder.TableBuilder`.

        :type preferClassNameSet: list of str
        :param preferClassNameSet: list of
            :class:`~cjklib.build.builder.TableBuilder` class names that will
            be preferred in conflicting cases, resolveConflicting must be
            ``True`` to take effect (default)
        :type resolveConflicts: bool
        :param resolveConflicts: if true conflicting builders will be removed
            so that only one builder is left per Table.
        :type quiet: bool
        :param quiet: if ``True`` no status information will be printed to
            stderr
        :type additionalBuilders: list of classobj
        :param additionalBuilders: list of externally provided TableBuilders
        :rtype: set
        :return: list of all classes inheriting form
            :class:`~cjklib.build.builder.TableBuilder` that
            provide a table (i.d. non abstract implementations), with its name
            as key
        :raise ValueError: if two builders are preferred that provide the same
            table, if two different options with the same name collide
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

        if resolveConflicts:
            tableBuilderClasses = DatabaseBuilder.resolveBuilderConflicts(
                tableBuilderClasses, preferClassNameSet, quiet=quiet)

        # check if all options are unique
        DatabaseBuilder._checkOptionUniqueness(tableBuilderClasses)

        return tableBuilderClasses

    @staticmethod
    def resolveBuilderConflicts(classList, preferClassNames=None, quiet=True):
        """
        Returns a subset of :class:`~cjklib.build.builder.TableBuilder`
        classes so that every buildable table is only represented by
        exactly one builder.

        :type classList: list of classobj
        :param classList: list of TableBuilders
        :type preferClassNames: list of classobj
        :param preferClassNames: list of
            :class:`~cjklib.build.builder.TableBuilder` class names that will
            be preferred in conflicting cases
        :type quiet: bool
        :param quiet: if ``True`` no status information will be printed to
            stderr
        :rtype: list of classobj
        :return: mapping of table names to builder classes that provide the
            given table
        :raise ValueError: if two builders are preferred that provide the same
            table
        """
        tableBuilderClasses = set(classList)

        preferClassNames = preferClassNames or []
        preferClassSet = set([clss for clss in tableBuilderClasses \
            if clss.__name__ in preferClassNames])

        # group table builders by provided tables
        tableToBuilderMapping = {}
        for clss in tableBuilderClasses:
            if clss.PROVIDES not in tableToBuilderMapping:
                tableToBuilderMapping[clss.PROVIDES] = set()

            tableToBuilderMapping[clss.PROVIDES].add(clss)

        # now check conflicting and choose preferred if given
        for tableName, builderClssSet in tableToBuilderMapping.items():
            preferredBuilders = builderClssSet & preferClassSet
            if preferredBuilders:
                if len(preferredBuilders) > 1:
                    # the user specified more than one preferred table that
                    # both provided one same table
                    raise ValueError("More than one TableBuilder preferred"
                        " for conflicting table '%s': '%s'"
                            % (tableName,
                                [b.__name__ for b in preferredBuilders]))
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

        return tableBuilderClasses

    @staticmethod
    def getSupportedTables():
        """
        Gets names of supported tables.

        :rtype: list of str
        :return: names of tables
        """
        classList = DatabaseBuilder.getTableBuilderClasses(
            resolveConflicts=False)
        return set([clss.PROVIDES for clss in classList])

    def getCurrentSupportedTables(self):
        """
        Gets names of tables supported by this instance of the database builder.

        This list can have more entries then
        :meth:`~cjklib.build.DatabaseBuilder.getSupportedTables` as
        additional external builders can be supplied on instantiation.

        :rtype: list of str
        :return: names of tables
        """
        return set(self._tableBuilderLookup.keys())

    def getTableBuilder(self, tableName):
        """
        Gets the :class:`~cjklib.build.builder.TableBuilder` used by
        this instance of the database builder to build the given table.

        :type tableName: str
        :param tableName: name of table
        :rtype: classobj
        :return: :class:`~cjklib.build.builder.TableBuilder` used to
            build the given table by this build instance.
        :raise UnsupportedError: if an unsupported table is given.
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

        :rtype: boolean
        :return: True if optimizable, False otherwise
        """
        return self.db.engine.name in ['sqlite']

    def optimize(self):
        """
        Optimizes the current database.

        :raise Exception: if database does not support optimization
        :raise OperationalError: if optimization failed
        """
        if self.db.engine.name == 'sqlite':
            self.db.execute('VACUUM')
        else:
            raise Exception('Database does not seem to support optimization')

#{ Global methods

def warn(message):
    """
    Prints the given message to stderr with the system's default encoding.

    :type message: str
    :param message: message to print
    """
    print >> sys.stderr, message.encode(locale.getpreferredencoding(),
        'replace')
