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
Command line interface (*CLI*) to the library's build functionality.

.. todo::
    * bug: "Prefer" system does not work for additional builders
"""

import sys
import os
import locale
from optparse import OptionParser, OptionGroup, Values
import ConfigParser
import warnings

from cjklib import build
from cjklib import exception
from cjklib import dbconnector
import cjklib
from cjklib.util import getConfigSettings, getDataPath, ExtendedOption

class CommandLineBuilder(object):
    """
    *Command line interface* (CLI) to the build functionality of cjklib.
    """
    DESCRIPTION = """Builds the database for the cjklib library.
The database is accessed according to the settings of cjklib in cjklib.conf.
Example: \"%prog build allAvail\". Builders can be given specific options with
format --BuilderName-option or --TableName-option, e.g.
\"--Unihan-wideBuild=yes\""""

    BUILD_GROUPS = {
        # source based
        'packaged': ['PinyinSyllables', 'WadeGilesSyllables',
            'WadeGilesPinyinMapping', 'PinyinIPAMapping', 'GRSyllables',
            'GRAbbreviation', 'GRRhotacisedFinals', 'PinyinGRMapping',
            'MandarinIPAInitialFinal', 'PinyinBrailleInitialMapping',
            'PinyinBrailleFinalMapping', 'PinyinInitialFinal',
            'WadeGilesInitialFinal', 'JyutpingSyllables',
            'JyutpingInitialFinal', 'CantoneseYaleSyllables',
            'CantoneseYaleInitialNucleusCoda', 'JyutpingYaleMapping',
            'JyutpingIPAMapping', 'CantoneseIPAInitialFinal',
            'CharacterShanghaineseIPA', 'ShanghaineseIPASyllables',
            'KangxiRadical',
            'KangxiRadicalIsolatedCharacter', 'RadicalEquivalentCharacter',
            'Strokes', 'StrokeOrder', 'CharacterDecomposition',
            'LocaleCharacterGlyph', 'StrokeCount', 'ComponentLookup',
            'CharacterRadicalResidualStrokeCount'],
        'UnihanCharacterSets': ['IICoreSet', 'GB2312Set', 'BIG5Set',
            'HKSCSSet', 'BIG5HKSCSSet', 'JISX0208Set', 'JISX0208_0213Set'],
        'UnihanData': ['UnihanCharacterSets', 'CharacterKangxiRadical',
            'CharacterPinyin', 'CharacterJyutping', 'CharacterHangul',
            'CharacterVietnamese', 'CharacterJapaneseKun',
            'CharacterJapaneseOn', 'CharacterKanWaRadical',
            'CharacterJapaneseRadical', 'CharacterKoreanRadical',
            'CharacterVariant', 'Glyphs'],
        # library based
        'Readings': ['PinyinSyllables', 'WadeGilesSyllables',
            'WadeGilesPinyinMapping', 'PinyinIPAMapping', 'GRSyllables',
            'GRAbbreviation', 'GRRhotacisedFinals', 'PinyinGRMapping',
            'MandarinIPAInitialFinal', 'PinyinBrailleInitialMapping',
            'PinyinBrailleFinalMapping', 'PinyinInitialFinal',
            'WadeGilesInitialFinal', 'JyutpingSyllables',
            'JyutpingInitialFinal', 'CantoneseYaleSyllables',
            'CantoneseYaleInitialNucleusCoda', 'JyutpingYaleMapping',
            'JyutpingIPAMapping', 'CantoneseIPAInitialFinal',
            'CharacterShanghaineseIPA', 'ShanghaineseIPASyllables'],
        'SupportedCharacterReadings': ['CharacterPinyin', 'CharacterJyutping',
            'CharacterHangul', 'CharacterShanghaineseIPA'],
        'KangxiRadicalData': ['CharacterKangxiRadical', 'KangxiRadical',
            'KangxiRadicalIsolatedCharacter', 'RadicalEquivalentCharacter',
            'CharacterRadicalResidualStrokeCount',
            'CharacterResidualStrokeCount'],
        'ShapeLookupData': ['Strokes', 'StrokeOrder', 'CharacterDecomposition',
            'LocaleCharacterGlyph', 'StrokeCount', 'ComponentLookup',
            'CharacterVariant', 'Glyphs'],
        'CharacterDomains': ['UnihanCharacterSets', 'GlyphInformationSet'],
        'cjklibData': ['Readings', 'SupportedCharacterReadings',
            'KangxiRadicalData', 'ShapeLookupData', 'CharacterDomains'],
        # language based
        'fullMandarin': ['KangxiRadicalData', 'ShapeLookupData',
            'CharacterPinyin', 'PinyinSyllables', 'WadeGilesSyllables',
            'WadeGilesPinyinMapping', 'GRSyllables', 'GRRhotacisedFinals',
            'GRAbbreviation', 'PinyinGRMapping', 'PinyinIPAMapping',
            'MandarinIPAInitialFinal', 'PinyinBrailleInitialMapping',
            'PinyinBrailleFinalMapping', 'PinyinInitialFinal',
            'WadeGilesInitialFinal', 'GB2312Set', 'BIG5Set'],
        'fullCantonese': ['KangxiRadicalData', 'ShapeLookupData',
            'CharacterShanghaineseIPA', 'ShanghaineseIPASyllables',
            'GB2312Set', 'BIG5Set'],
        'fullShanghainese': ['KangxiRadicalData', 'ShapeLookupData',
            'CharacterJyutping', 'JyutpingSyllables', 'CantoneseYaleSyllables',
            'CantoneseYaleInitialNucleusCoda', 'JyutpingYaleMapping',
            'JyutpingIPAMapping', 'CantoneseIPAInitialFinal',
            'JyutpingInitialFinal', 'GB2312Set', 'BIG5HKSCSSet'],
        'fullJapanese': ['KangxiRadicalData', 'ShapeLookupData', 'JISX0208Set',
            'JISX0208_0213Set'],
        'fullKorean': ['KangxiRadicalData', 'ShapeLookupData',
            'CharacterHangul', 'IICoreSet'], # TODO IICoreSet as long as no better source exists
        'fullVietnamese': ['KangxiRadicalData', 'ShapeLookupData', 'IICoreSet'], # TODO IICoreSet as long as no better source exists
        # additional data for cjknife
        'Dictionaries': ['CEDICT', 'CEDICTGR', 'HanDeDict', 'CFDICT', 'EDICT'],
        # TODO deprecated
        'fullDictionaries': ['fullCEDICT', 'fullCEDICTGR', 'fullHanDeDict',
            'fullCFDICT', 'fullEDICT'],
        'fullCEDICT': ['CEDICT'],
        'fullCEDICTGR': ['CEDICTGR'],
        'fullHanDeDict': ['HanDeDict'],
        'fullCFDICT': ['CFDICT'],
        'fullEDICT': ['EDICT'],
    }
    """
    Definition of build groups available to the user. Recursive definitions are
    not allowed and will lead to a lock up.
    """

    DB_PREFER_BUILDERS =  ['CombinedStrokeCountBuilder',
        'CombinedCharacterResidualStrokeCountBuilder']
    """Builders prefered for build process."""

    output_encoding \
        = (hasattr(sys.stdout, 'encoding') and sys.stdout.encoding) \
            or locale.getpreferredencoding() or 'ascii'

    def __init__(self, deprecated=None):
        self.deprecated = deprecated or []

    @classmethod
    def printFormattedLine(cls, outputString, lineLength=None,
        subsequentPrefix=''):
        """
        Formats the given input string to fit to a output with a limited line
        length and prints it to stdout with the systems encoding.

        :type outputString: str
        :param outputString: a string that is formated to fit to the screen
        :type lineLength: int
        :param lineLength: with of screen
        :type subsequentPrefix: str
        :param subsequentPrefix: prefix used after line break
        """
        if lineLength is None:
            try:
                lineLength = int(os.environ['COLUMNS'])
            except (KeyError, ValueError):
                lineLength = 80

        outputLines = []
        for line in outputString.split("\n"):
            outputEntityList = line.split()
            outputEntityList.reverse()
            column = 0
            output = ''
            while outputEntityList:
                entity = outputEntityList.pop()
                # if the next entity including one trailing space will
                # reach over, break the line
                if column > 0 and len(entity) + column >= lineLength:
                    output = output + "\n" + subsequentPrefix + entity
                    column = len(subsequentPrefix) + len(entity)
                else:
                    if column > 0:
                        output = output + ' '
                        column = column + 1
                    column = column + len(entity)
                    output = output + entity
                #if len(column) >= lineLength and outputEntityList:
                    #output = output + "\n" + subsequentPrefix
                    #column = len(subsequentPrefix)
            outputLines.append(output)

        print "\n".join(outputLines).encode(cls.output_encoding,
            'replace')

    @classmethod
    def getBuilderConfigSettings(cls):
        """
        Gets the builder settings from the section ``Builder`` from
        ```cjklib.conf```.

        :rtype: dict
        :return: dictionary of builder options
        """
        configOptions = getConfigSettings('Builder')
        # don't convert to lowercase
        ConfigParser.RawConfigParser.optionxform = lambda self, x: x
        config = ConfigParser.RawConfigParser(configOptions)

        options = {}
        for builder in build.DatabaseBuilder.getTableBuilderClasses(
            resolveConflicts=False):
            if not builder.PROVIDES:
                continue

            for option in builder.getDefaultOptions():
                try:
                    metadata = builder.getOptionMetaData(option)
                    optionType = metadata.get('type', None)
                except KeyError:
                    optionType = None

                for opt in [option, '--%s-%s' % (builder.__name__, option),
                    '--%s-%s' % (builder.PROVIDES, option)]:
                    if config.has_option(None, opt):
                        if optionType == 'bool':
                            value = config.getboolean(ConfigParser.DEFAULTSECT,
                                opt)
                        elif optionType == 'int':
                            value = config.getint(ConfigParser.DEFAULTSECT,
                                opt)
                        elif optionType == 'float':
                            value = config.getfloat(ConfigParser.DEFAULTSECT,
                                opt)
                        else:
                            value = config.get(ConfigParser.DEFAULTSECT, opt)

                        options[opt] = value

        return options

    @classmethod
    def getConnectionConfigSettings(cls):
        """
        Gets the connections settings from cjklib.conf.

        :rtype: dict
        :return: dictionary of connection options
        """
        options = {}
        config = dbconnector.getDefaultConfiguration()
        if 'sqlalchemy.url' in config:
            options['databaseUrl'] = config['sqlalchemy.url']
        if 'attach' in config:
            options['attach'] = config['attach']
        if 'registerUnicode' in config:
            options['registerUnicode'] = config['registerUnicode']
        return options

    @classmethod
    def getDefaultOptions(cls, includeConfig=True):
        """
        Gets default options that always overwrite those specified in the build
        module. Boolean options of the :class:`~cjklib.build.DatabaseBuilder`
        can not be changed here as they are hardcoded in the given command line
        options.
        """
        options = {}
        # dataPath
        options['dataPath'] = ['.', getDataPath()]
        # prefer
        options['prefer'] = cls.DB_PREFER_BUILDERS[:]

        if includeConfig:
            options.update(cls.getConnectionConfigSettings())
            options.update(cls.getBuilderConfigSettings())

        return options

    def buildParser(self):
        usage = "%prog [options] [list | build TABLE [TABLE_2 ...]]"
        description = self.DESCRIPTION
        version = """%%prog %s
Copyright (C) 2006-2010 cjklib developers

cjknife is part of cjklib.

cjklib is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version if not otherwise noted.
See the data files for their specific licenses.

cjklib is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with cjklib.  If not, see <http://www.gnu.org/licenses/>.""" \
            % str(cjklib.__version__)
        parser = OptionParser(usage=usage, description=description,
            version=version, option_class=ExtendedOption)

        defaults = self.getDefaultOptions()
        parser.add_option("-r", "--rebuild", action="store_true",
            dest="rebuildExisting", default=False,
            help="build tables even if they already exist")
        parser.add_option("-d", "--keepDepending", action="store_false",
            dest="rebuildDepending", default=True,
            help="don't rebuild build-depends tables that are not given")
        parser.add_option("-p", "--prefer", action="appendResetDefault",
            metavar="BUILDER", dest="prefer",
            help="builder preferred where several provide the same table" \
                + " [default: %s]" % defaults.get("prefer", []))
        parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
            default=False, help="don't print anything on stdout")
        parser.add_option("--database", action="store", metavar="URL",
            dest="databaseUrl", default=defaults.get("databaseUrl", None),
            help="database url [default: %default]")
        parser.add_option("--attach", action="appendResetDefault",
            metavar="URL", dest="attach",
            help="attachable databases [default: %s]"
                % defaults.get("attach", []))
        parser.add_option("--registerUnicode", action="store", type='bool',
            metavar="BOOL", dest="registerUnicode",
            help=("register own Unicode functions if no ICU support available"
                " [default: %s]" % defaults.get("registerUnicode", False)))
        parser.add_option("--ignoreConfig", action="store_true",
            dest="ignoreConfig", default=False,
            help="ignore settings from cjklib.conf")

        optionSet = set(['rebuildExisting', 'rebuildDepending', 'quiet',
            'databaseUrl', 'attach', 'prefer'])
        globalBuilderGroup = OptionGroup(parser, "Global builder commands")
        localBuilderGroup = OptionGroup(parser, "Local builder commands")
        for builder in build.DatabaseBuilder.getTableBuilderClasses():
            if not builder.PROVIDES:
                continue

            for option, defaultValue in sorted(
                builder.getDefaultOptions().items()):
                try:
                    metadata = builder.getOptionMetaData(option)
                except KeyError:
                    continue

                includeOptions = {'action': 'action', 'type': 'type',
                    'metavar': 'metavar', 'choices': 'choices',
                        'description': 'help'}
                options = dict([(includeOptions[key], value) for key, value \
                    in metadata.items() if key in includeOptions])

                if 'metavar' not in options:
                    if 'type' in options and options['type'] == 'bool':
                        options['metavar'] = 'BOOL'
                    else:
                        options['metavar'] = 'VALUE'

                if 'help' not in options:
                    options['help'] = ''

                default = defaults.get(option, defaultValue)
                if default == []:
                    options['help'] += ' [default: ""]'
                elif default is not None:
                    options['help'] += ' [default: %s]' % default

                # global option, only need to add it once, DatabaseBuilder makes
                #   sure option is consistent between builder
                options['dest'] = option
                if option not in optionSet:
                    globalBuilderGroup.add_option('--' + option, **options)
                    optionSet.add(option)

                # local options
                #options['help'] = optparse.SUPPRESS_HELP
                localBuilderOption = '--%s-%s' % (builder.__name__, option)
                options['dest'] = localBuilderOption
                localBuilderGroup.add_option(localBuilderOption, **options)

                localTableOption = '--%s-%s' % (builder.PROVIDES, option)
                options['dest'] = localTableOption
                localBuilderGroup.add_option(localTableOption, **options)

        parser.add_option_group(globalBuilderGroup)
        #parser.add_option_group(localBuilderGroup)

        return parser

    def listBuildGroups(self):
        self.printFormattedLine("Generic groups:\n" \
            + "all, for all tables understood by the build script\n" \
            + "allAvail, for all data available to the build script\n")
        self.printFormattedLine("Standard groups:")
        groupList = self.BUILD_GROUPS.keys()
        groupList.sort()
        deprecated = self._getDeprecated()
        for groupName in groupList:
            if groupName in deprecated:
                continue

            content = []
            # get group content, add apostrophes for "sub"groups
            for member in self.BUILD_GROUPS[groupName]:
                if member in deprecated:
                    continue

                if self.BUILD_GROUPS.has_key(member):
                    content.append("'" + member + "'")
                else:
                    content.append(member)
            self.printFormattedLine(groupName + ": " + ', '.join(content),
                subsequentPrefix='  ')
        self.printFormattedLine("\nBoth group names and table names can be "
            "given to the build process.")

    def _getDeprecated(self):
        deprecated = set()
        for entry in self.deprecated:
            if entry in self.BUILD_GROUPS:
                # group
                deprecated.add(entry)
                deprecated.update(self.BUILD_GROUPS[entry])
            else:
                # single table
                for groupEntries in self.BUILD_GROUPS.values():
                    if entry in groupEntries:
                        deprecated.add(entry)

        return deprecated

    def _combinePreferred(self, preferred, otherPreferred):
        """
        Combine two lists of preferred builders, by giving classes from the
        first list precedence.
        """
        builderClasses = build.DatabaseBuilder.getTableBuilderClasses(
            resolveConflicts=False)
        preferredBuilders = preferred + otherPreferred
        dbPreferClasses = [clss for clss in builderClasses
            if clss.__name__ in (preferred + otherPreferred)]

        # sort out the default preferred if they collide with user's choice
        dbPreferClasses = build.DatabaseBuilder.resolveBuilderConflicts(
            dbPreferClasses, preferred)

        return [clss.__name__ for clss in dbPreferClasses]

    def runBuild(self, buildGroupList, options):
        if not buildGroupList:
            return
        buildGroupList = set(buildGroupList)
        # by default fail if a table couldn't be built
        options['noFail'] = False
        if 'all' in buildGroupList or 'allAvail' in buildGroupList:
            if 'allAvail' in buildGroupList:
                if len(buildGroupList) == 1:
                    # don't fail on non available
                    options['noFail'] = True
                else:
                    # allAvail not compatible with others, as allAvail means not
                    # failing if build fails, but others will need failing when
                    # explicitly named
                    raise ValueError("group 'allAvail' can't be specified " \
                        + "together with other groups.")
            # if generic group given get list
            buildGroupList = build.DatabaseBuilder.getSupportedTables()

        deprecatedGroups = self._getDeprecated() & set(buildGroupList)
        if deprecatedGroups:
            warnings.warn("Group(s) '%s' is (are) deprecated"
                    % "', '".join(deprecatedGroups)
                + " and will disappear from future versions.",
                category=DeprecationWarning)

        # unpack groups
        groups = []
        while len(buildGroupList) != 0:
            group = buildGroupList.pop()
            if self.BUILD_GROUPS.has_key(group):
                buildGroupList.update(self.BUILD_GROUPS[group])
            else:
                groups.append(group)

        # re-add builders preferred by default, in case overwritten by user
        preferredBuilderNames = options.get('prefer', [])
        if preferredBuilderNames:
            options['prefer'] = self._combinePreferred(preferredBuilderNames,
                self.DB_PREFER_BUILDERS)

        # get database connection
        configuration = dbconnector.getDefaultConfiguration()
        configuration['sqlalchemy.url'] = options.pop('databaseUrl',
            configuration['sqlalchemy.url'])
        configuration['attach'] = [attach for attach in
            options.pop('attach', configuration.get('attach', [])) if attach]
        if 'registerUnicode' in options:
            configuration['registerUnicode'] = options.pop('registerUnicode')
        try:
            db = dbconnector.DatabaseConnector(configuration)
        except ValueError, e:
            print >> sys.stderr, "Error: %s" % e
            return False

        # create builder instance
        dbBuilder = build.DatabaseBuilder(dbConnectInst=db, **options)

        try:
            dbBuilder.build(groups)

            print "finished"
        except exception.UnsupportedError, e:
            print >> sys.stderr, \
                "Error building local tables, some names do not exist: %s" % e
            return False
        except KeyboardInterrupt:
            print >> sys.stderr, "Keyboard interrupt."
            try:
                # remove temporary tables
                dbBuilder.clearTemporary()
            except KeyboardInterrupt:
                print >> sys.stderr, \
                    "Interrupted while cleaning temporary tables"
            return False

        return True

    def run(self):
        """
        Runs the builder
        """
        # parse command line parameters
        parser = self.buildParser()
        (opts, args) = parser.parse_args()

        if len(args) == 0:
            parser.error("incorrect number of arguments")

        command = args[0]
        if command.lower() == 'list':
            self.listBuildGroups()
            return True
        elif command.lower() == 'build':
            if not args[1:]:
                parser.error("no build groups specified")

            options = self.getDefaultOptions(
                includeConfig=not opts.ignoreConfig)
            # convert the Values object to a dict, not too nice, but oh well
            options.update(dict([(option, getattr(opts, option)) for option \
                in dir(opts) if not hasattr(Values(), option) \
                    and getattr(opts, option) != None]))

            return self.runBuild(args[1:], options)
        else:
            parser.error("unknown command '%s'" % command)

        return False


def main():
    if not CommandLineBuilder(deprecated=['fullDictionaries']).run():
        sys.exit(1)

if __name__ == "__main__":
    main()
