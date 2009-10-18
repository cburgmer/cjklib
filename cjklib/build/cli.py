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
Provides a command line interface (I{CLI}) to the build functionality of cjklib.
"""

import sys
import os
import locale
import copy
from optparse import OptionParser, OptionGroup, Option, OptionValueError, Values
import ConfigParser

from cjklib import build
from cjklib import exception
from cjklib.dbconnector import DatabaseConnector
import cjklib
from cjklib.util import getConfigSettings

class ExtendedOption(Option):
    """
    Add support for "bool" to optparse, and offer special handling of PATH
    strings.
    """
    # taken from ConfigParser.RawConfigParser
    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}
    def check_bool(option, opt, value):
        if value.lower() in ExtendedOption._boolean_states:
            return ExtendedOption._boolean_states[value.lower()]
        else:
            raise OptionValueError(
                "option %s: invalid bool value: %r" % (opt, value))

    def check_pathstring(option, opt, value):
        return value.split(':')

    TYPES = Option.TYPES + ("bool", "pathstring")
    TYPE_CHECKER = copy.copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["bool"] = check_bool
    TYPE_CHECKER["pathstring"] = check_pathstring

    ACTIONS = Option.ACTIONS + ("extendResetDefault",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extendResetDefault",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extendResetDefault",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extendResetDefault",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extendResetDefault":
            if not hasattr(self, 'resetDefault'):
                self.resetDefault = set()
            if dest not in self.resetDefault:
                del values.ensure_value(dest, [])[:]
                self.resetDefault.add(dest)
            values.ensure_value(dest, []).extend(value)
        else:
            Option.take_action(
                self, action, dest, opt, value, values, parser)

class CommandLineBuilder:
    """
    I{Command line interface} (X{CLI}) to the build functionality of cjklib.
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
            'JyutpingIPAMapping', 'CantoneseIPAInitialFinal', 'KangxiRadical',
            'KangxiRadicalIsolatedCharacter', 'RadicalEquivalentCharacter',
            'Strokes', 'StrokeOrder', 'CharacterDecomposition',
            'LocaleCharacterGlyph', 'StrokeCount', 'ComponentLookup',
            'CharacterRadicalResidualStrokeCount'],
        'UnihanCharacterSets': ['IICoreSet', 'GB2312Set', 'BIG5Set'],
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
            'JyutpingIPAMapping', 'CantoneseIPAInitialFinal'],
        'SupportedCharacterReadings': ['CharacterPinyin', 'CharacterJyutping',
            'CharacterHangul'],
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
            'CharacterJyutping', 'JyutpingSyllables', 'CantoneseYaleSyllables',
            'CantoneseYaleInitialNucleusCoda', 'JyutpingYaleMapping',
            'JyutpingIPAMapping', 'CantoneseIPAInitialFinal',
            'JyutpingInitialFinal', 'IICoreSet'],
        'fullJapanese': ['KangxiRadicalData', 'ShapeLookupData', 'IICoreSet'], # TODO IICoreSet as long as no better source exists
        'fullKorean': ['KangxiRadicalData', 'ShapeLookupData',
            'CharacterHangul', 'IICoreSet'], # TODO IICoreSet as long as no better source exists
        'fullVietnamese': ['KangxiRadicalData', 'ShapeLookupData', 'IICoreSet'], # TODO IICoreSet as long as no better source exists
        # additional data for cjknife
        'fullDictionaries': ['fullCEDICT', 'fullCEDICTGR', 'fullHanDeDict',
            'fullCFDICT', 'fullEDICT'],
        'fullCEDICT': ['CEDICT', 'CEDICT_Words'],
        'fullCEDICTGR': ['CEDICTGR', 'CEDICTGR_Words'],
        'fullHanDeDict': ['HanDeDict', 'HanDeDict_Words'],
        'fullCFDICT': ['CFDICT', 'CFDICT_Words'],
        'fullEDICT': ['EDICT', 'EDICT_Words'],
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

    @classmethod
    def printFormattedLine(cls, outputString, lineLength=None,
        subsequentPrefix=''):
        """
        Formats the given input string to fit to a output with a limited line
        length and prints it to stdout with the systems encoding.

        @type outputString: str
        @param outputString: a string that is formated to fit to the screen
        @type lineLength: int
        @param lineLength: with of screen
        @type subsequentPrefix: str
        @param subsequentPrefix: prefix used after line break
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
                # if the next entity including one trailing space will reach over,
                # break the line
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
        Gets the builder settings from the section C{Builder} from cjklib.conf.

        @rtype: dict
        @return: dictionary of builder options
        """
        configOptions = getConfigSettings('Builder')
        # don't convert to lowercase
        ConfigParser.RawConfigParser.optionxform = lambda self, x: x
        config = ConfigParser.RawConfigParser(configOptions)

        options = {}
        for builder in build.DatabaseBuilder.getTableBuilderClasses():
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
    def getDefaultOptions(cls):
        """
        Gets default options that always overwrite those specified in the build
        module.
        Boolean options of the L{DatabaseBuilder} can not be changed here as
        they are hardcoded in the given command line options.
        """
        options = {}
        # dataPath
        options['dataPath'] = ['.']
        buildModule = __import__("cjklib.build")

        from pkg_resources import Requirement, resource_filename
        options['dataPath'].append(
            resource_filename(Requirement.parse("cjklib"), "cjklib/data"))
        # prefer
        options['prefer'] = cls.DB_PREFER_BUILDERS
        # databaseUrl
        config = getConfigSettings('Connection')
        if 'url' in config:
            options['databaseUrl'] = config['url']
        # build specific options
        options.update(cls.getBuilderConfigSettings())
        return options

    def buildParser(self):
        usage = "%prog [options] [build | list]"
        description = self.DESCRIPTION
        version = """%%prog %s
Copyright (C) 2006-2009 Christoph Burgmer
The library and all parts are distributed under the terms of the LGPL
Version 2.1, February 1999 (http://www.fsf.org/licensing/licenses/lgpl.html)
if not otherwise noted. See the data files for their specific licenses.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" \
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
        parser.add_option("-p", "--prefer", action="append", metavar="BUILDER",
            dest="prefer", default=defaults.get("prefer", []),
            help="builder preferred where several provide the same table" \
                + " [default: %default]")
        parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
            default=False, help="don't print anything on stdout")
        parser.add_option("--database", action="store", metavar="URL",
            dest="databaseUrl", default=defaults.get("databaseUrl", None),
            help="database url [default: %default]")

        optionSet = set(['rebuildExisting', 'rebuildDepending', 'quiet',
            'databaseUrl', 'prefer'])
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
                options['default'] = defaults.get(option, None)
                if option not in optionSet:
                    globalBuilderGroup.add_option('--' + option, **options)
                    optionSet.add(option)

                # local options
                #options['help'] = optparse.SUPPRESS_HELP
                localBuilderOption = '--%s-%s' % (builder.__name__, option)
                options['dest'] = localBuilderOption
                options['default'] = defaults.get(localBuilderOption, None)
                localBuilderGroup.add_option(localBuilderOption, **options)

                localTableOption = '--%s-%s' % (builder.PROVIDES, option)
                options['dest'] = localTableOption
                options['default'] = defaults.get(localTableOption, None)
                localBuilderGroup.add_option(localTableOption, **options)

        parser.add_option_group(globalBuilderGroup)
        #parser.add_option_group(localBuilderGroup)

        return parser

    @classmethod
    def listBuildGroups(cls):
        cls.printFormattedLine("Generic groups:\n" \
            + "all, for all tables understood by the build script\n" \
            + "allAvail, for all data available to the build script\n")
        cls.printFormattedLine("Standard groups:")
        groupList = cls.BUILD_GROUPS.keys()
        groupList.sort()
        for groupName in groupList:
            content = []
            # get group content, add apostrophes for "sub"groups
            for member in cls.BUILD_GROUPS[groupName]:
                if cls.BUILD_GROUPS.has_key(member):
                    content.append("'" + member + "'")
                else:
                    content.append(member)
            cls.printFormattedLine(groupName + ": " + ', '.join(content),
                subsequentPrefix='  ')
        cls.printFormattedLine("\nBoth Group names and table names can be " \
            "given to the build process.")

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

        # unpack groups
        groups = []
        while len(buildGroupList) != 0:
            group = buildGroupList.pop()
            if self.BUILD_GROUPS.has_key(group):
                buildGroupList.update(self.BUILD_GROUPS[group])
            else:
                groups.append(group)

        # TODO only set 'slim' if table doesn't already exist
        if 'slimUnihanTable' not in options:
            options['slimUnihanTable'] = 'Unihan' not in groups

        # create builder instance
        dbBuilder = build.DatabaseBuilder(**options)

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

            options = self.getDefaultOptions()
            # convert the Values object to a dict, not too nice, but oh well
            options.update(dict([(option, getattr(opts, option)) for option \
                in dir(opts) if not hasattr(Values(), option) \
                    and getattr(opts, option) != None]))

            return self.runBuild(args[1:], options)
        else:
            parser.error("unknown command '%s'" % command)

        return False


def main():
    if not CommandLineBuilder().run():
        sys.exit(1)

if __name__ == "__main__":
    main()
