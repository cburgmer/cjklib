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
Unit tests for :mod:`cjklib.build.builder`.
"""

# pylint: disable-msg=E1101
#  testcase attributes and methods are only available in concrete classes

import unittest
import types
import re
import os.path

from sqlalchemy import Table

from cjklib.build import DatabaseBuilder, builder
from cjklib import util

class TableBuilderTest:
    """
    Base class for testing of :class:`~cjklib.build.builder.TableBuilder`
    classes.
    """
    BUILDER = None
    """Builder class object."""

    PREFER_BUILDERS = []
    """Builders of depending tables to prefer."""

    DATABASES = [
        'sqlite://', # SQLite in-memory database
        #'mysql:///cjklib_unittest?charset=utf8', # see below
        ]
    """
    Databases to test.

    MySQL by default is disabled. Run the following as admin before you enable
    it:
    CREATE DATABASE cjklib_unittest DEFAULT CHARACTER SET utf8 COLLATE utf8_bin;
    You might need to give appropriate rights to the user:
    GRANT ALL ON cjklib_unittest.* TO 'user_name'@'host_name';
    """

    EXTERNAL_DATA_PATHS = []
    """Data paths for external files."""

    OPTIONS = []
    """Sets of options for the builder."""

    TABLE_DEPEND_OPTIONS = []
    """
    Tuples of options for other builders the current tested builder depends on.
    """

    def setUp(self):
        prefer = [self.BUILDER]
        prefer.extend(self.PREFER_BUILDERS)

        self.dataPath = self.EXTERNAL_DATA_PATHS[:]
        self.dataPath.append(util.getDataPath())
        self.dataPath.append(os.path.join('.', 'test'))
        self.dataPath.append(os.path.join('.', 'test', 'downloads'))

        self.dbInstances = {}
        for databasePath in self.DATABASES:
            self.dbInstances[databasePath] = DatabaseBuilder(quiet=True,
                databaseUrl=databasePath, dataPath=self.dataPath, prefer=prefer,
                rebuildExisting=True, noFail=False)
            # make sure we don't get a production db instance
            tables = self.dbInstances[databasePath].db.engine.table_names()
            assert len(tables) == 0, "Database is not empty: '%s'" \
                % "', '".join(tables)

    def tearDown(self):
        for databasePath in self.DATABASES:
            tables = self.dbInstances[databasePath].db.engine.table_names()
            for tableName in tables:
                table = Table(tableName,
                    self.dbInstances[databasePath].db.metadata)
                table.drop()

    def shortDescription(self):
        methodName = getattr(self, self.id().split('.')[-1])
        # get whole doc string and remove superfluous white spaces
        noWhitespaceDoc = re.sub('\s+', ' ', methodName.__doc__.strip())
        # remove markup for epytext format
        clearName = re.sub('[CL]\{([^\}]*)}', r'\1', noWhitespaceDoc)
        # add information about conversion direction
        return clearName + ' (for %s)' % self.BUILDER.__name__

    def testBuild(self):
        """Test if build finishes successfully."""
        optionSets = self.OPTIONS[:]
        for databasePath in self.dbInstances:
            for options in optionSets:
                myOptions = options.copy()
                if 'dataPath' not in myOptions:
                    myOptions['dataPath'] = self.dataPath
                assert('quiet' not in myOptions)
                myOptions['quiet'] = True
                self.dbInstances[databasePath].setBuilderOptions(self.BUILDER,
                    myOptions, exclusive=True)

                # set options for builders we depend on
                for builder, dependOptions in self.TABLE_DEPEND_OPTIONS:
                    self.dbInstances[databasePath].setBuilderOptions(builder,
                        dependOptions)

                # catch keyboard interrupt to cleanly close
                try:
                    self.dbInstances[databasePath].build(
                        [self.BUILDER.PROVIDES])

                    # make sure table exists (others might have been created)
                    tables = set(
                        self.dbInstances[databasePath].db.getTableNames())
                    self.assert_(self.BUILDER.PROVIDES in tables,
                        "Table '%s' not found in '%s'" \
                            % (self.BUILDER.PROVIDES, "', '".join(tables)))
                    # make sure depends are removed
                    self.assert_(len(tables & set(self.BUILDER.DEPENDS)) == 0)
                except KeyboardInterrupt:
                    try:
                        # remove temporary tables
                        self.dbInstances[databasePath].clearTemporary()
                        # remove built table
                        self.dbInstances[databasePath].remove(
                            [self.BUILDER.PROVIDES])
                    except KeyboardInterrupt:
                        import sys
                        print >> sys.stderr, \
                            "Interrupted while cleaning temporary tables"
                        raise
                    raise


                self.dbInstances[databasePath].remove(
                    [self.BUILDER.PROVIDES])

                tables = self.dbInstances[databasePath].db.getTableNames()
                self.assert_(len(tables) == 0)


#class TableBuilderTestCaseCheck(unittest.TestCase):
    #"""
    #Checks if every :class:`~cjklib.build.builder.TableBuilder` has its own
    #:class:`~cjklib.test.build.TableBuilderTest`.
    #"""
    #def testEveryBuilderHasTest(self):
        #"""
        #Check if every builder has a test case.
        #"""
        #testClasses = self.getTableBuilderTestClasses()
        #testClassBuilders = [clss.BUILDER for clss in testClasses]

        #for clss in DatabaseBuilder.getTableBuilderClasses(
            #resolveConflicts=False):
            #self.assert_(clss in testClassBuilders,
                #"'%s' has no TableBuilderTest" % clss.__name__)

    #@staticmethod
    #def getTableBuilderTestClasses():
        #"""
        #Gets all classes implementing :class:`~cjklib.test.build.TableBuilderTest`.

        #@rtype: list
        #@return: list of all classes inheriting form :class:`~cjklib.test.build.TableBuilderTest`
        #"""
        ## get all non-abstract classes that inherit from TableBuilderTest
        #testModule = __import__("cjklib.test.build")
        #testClasses = [clss for clss \
            #in testModule.test.build.__dict__.values() \
            #if type(clss) == types.TypeType \
            #and issubclass(clss, TableBuilderTest) \
            #and clss.BUILDER]

        #return testClasses


class UnihanBuilderTest(TableBuilderTest, unittest.TestCase):
    # don't do a wide build for MySQL, which has no support for > BMP
    def removeMySQL(databaseUrls):
        return [url for url in databaseUrls if not url.startswith('mysql://')]

    BUILDER = builder.UnihanBuilder
    DATABASES = removeMySQL(TableBuilderTest.DATABASES)
    OPTIONS = [{'wideBuild': False}, {'wideBuild': True},
        {'slimUnihanTable': True}]


class MysqlUnihanBuilderTest(TableBuilderTest, unittest.TestCase):
    # don't do a wide build for MySQL, which has no support for > BMP
    def filterMySQL(databaseUrls):
        return [url for url in databaseUrls if url.startswith('mysql://')]

    BUILDER = builder.UnihanBuilder
    DATABASES = filterMySQL(TableBuilderTest.DATABASES)
    OPTIONS = [{'wideBuild': False, 'slimUnihanTable': True}]


class Kanjidic2BuilderTest(TableBuilderTest, unittest.TestCase):
    # don't do a wide build for MySQL, which has no support for > BMP
    def removeMySQL(databaseUrls):
        return [url for url in databaseUrls if not url.startswith('mysql://')]

    BUILDER = builder.Kanjidic2Builder
    DATABASES = removeMySQL(TableBuilderTest.DATABASES)
    OPTIONS = [{'wideBuild': False}, {'wideBuild': True}]


class MysqlKanjidic2BuilderTest(TableBuilderTest, unittest.TestCase):
    # don't do a wide build for MySQL, which has no support for > BMP
    def filterMySQL(databaseUrls):
        return [url for url in databaseUrls if url.startswith('mysql://')]

    BUILDER = builder.Kanjidic2Builder
    DATABASES = filterMySQL(TableBuilderTest.DATABASES)
    OPTIONS = [{'wideBuild': False}]


class CharacterVariantBuilderTest(TableBuilderTest, unittest.TestCase):
    # don't do a wide build for MySQL, which has no support for > BMP
    def removeMySQL(databaseUrls):
        return [url for url in databaseUrls if not url.startswith('mysql://')]

    BUILDER = builder.CharacterVariantBuilder
    DATABASES = removeMySQL(TableBuilderTest.DATABASES)
    OPTIONS = [{'wideBuild': False}, {'wideBuild': True}]


class MysqlCharacterVariantBuilderTest(TableBuilderTest, unittest.TestCase):
    # don't do a wide build for MySQL, which has no support for > BMP
    def filterMySQL(databaseUrls):
        return [url for url in databaseUrls if url.startswith('mysql://')]

    BUILDER = builder.CharacterVariantBuilder
    DATABASES = filterMySQL(TableBuilderTest.DATABASES)
    OPTIONS = [{'wideBuild': False}]
    TABLE_DEPEND_OPTIONS = [(builder.UnihanBuilder, {'wideBuild': False})]


class EDICTBuilderTest(TableBuilderTest, unittest.TestCase):
    BUILDER = builder.EDICTBuilder
    OPTIONS = [{'enableFTS3': False},
        {'filePath': './test/downloads/EDICT', 'fileType': '.gz'}]


class CEDICTBuilderTest(TableBuilderTest, unittest.TestCase):
    BUILDER = builder.CEDICTBuilder
    OPTIONS = [{'enableFTS3': False},
        {'filePath': './test/downloads/CEDICT', 'fileType': '.gz'}]


class CEDICTGRBuilderTest(TableBuilderTest, unittest.TestCase):
    BUILDER = builder.CEDICTGRBuilder
    OPTIONS = [{'enableFTS3': False},
        {'filePath': './test/downloads/CEDICTGR', 'fileType': '.zip'}]


class HanDeDictBuilderTest(TableBuilderTest, unittest.TestCase):
    BUILDER = builder.HanDeDictBuilder
    OPTIONS = [{'enableFTS3': False},
        {'filePath': './test/downloads/HanDeDict', 'fileType': '.tar.bz2'}]


class CFDICTBuilderTest(TableBuilderTest, unittest.TestCase):
    BUILDER = builder.CFDICTBuilder
    OPTIONS = [{'enableFTS3': False},
        {'filePath': './test/downloads/CFDICT', 'fileType': '.tar.bz2'}]


# Generate default test classes for TableBuilder without special definitions
for builderClass in DatabaseBuilder.getTableBuilderClasses(
    resolveConflicts=False):
    testClassName = '%sTest' % builderClass.__name__
    if testClassName not in globals():
        globals()[testClassName] = types.ClassType(testClassName,
            (TableBuilderTest, unittest.TestCase), {'BUILDER': builderClass})
    del testClassName