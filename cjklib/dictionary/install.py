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

u"""
Installs dictionaries at runtime.

Example:

- Download and update a dictionary (here CFDICT):

    >>> from cjklib.dbconnector import getDBConnector
    >>> db = getDBConnector({'sqlalchemy.url': 'sqlite://',\
'attach': ['cjklib']})
    >>> from cjklib.dictionary.install import DictionaryInstaller
    >>> installer = DictionaryInstaller()
    >>> installer.install('CFDICT', dbConnectInst=db)
    >>> from cjklib.dictionary import CFDICT
    >>> CFDICT(dbConnectInst=db).getFor(u'朋友')
    [EntryTuple(HeadwordTraditional=u'\u670b\u53cb',\
HeadwordSimplified=u'\u670b\u53cb', Reading=u'p\xe9ng you',\
Translation=u'/ami (n.v.) (n)/')]

"""

__all__ = [
    # meta
    'getDownloaderClass', 'getDownloader',
    # downloader
    'EDICTDownloader', 'CEDICTDownloader', 'CEDICTGR', 'HanDeDict', 'CFDICT',
    # installer
    'DictionaryInstaller',
    ]

import sys
import re
import os
import types
import locale
import urllib
import urlparse
from datetime import datetime, date, time
from optparse import OptionParser, OptionGroup, Values
import ConfigParser

from sqlalchemy import select
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

import cjklib
from cjklib import dbconnector
from cjklib import build
from cjklib.util import cachedmethod, ExtendedOption, getConfigSettings

try:
    from progressbar import Percentage, Bar, ETA, FileTransferSpeed, ProgressBar
    def progress(i, chunkSize, total):
        global pbar
        if i == 0:
            widgets = [Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                FileTransferSpeed()]
            pbar = ProgressBar(widgets=widgets, maxval=total/chunkSize+1)
            pbar.start()
        pbar.update(min(i, total/chunkSize+1))

except ImportError:
    def progress(i, chunkSize, total):
        global progressTick
        terminalWidth = 80
        if i == 0:
            progressTick = 0
            tick = 0
        else:
            tick = min(int(terminalWidth * (i * chunkSize) / total),
                terminalWidth)
        while progressTick < tick:
            sys.stdout.write('#')
            progressTick += 1
        sys.stdout.flush()

def warn(message, endline=True):
    """
    Prints the given message to stderr with the system's default encoding.

    :type message: str
    :param message: message to print
    """
    print message.encode(locale.getpreferredencoding(), 'replace'),
    if endline: print

#{ Access methods

def getDownloaderClasses():
    """
    Gets all classes in module that implement
    :class:`~cjklib.dictionary.install.DownloaderBase`.

    :rtype: set
    :return: list of all classes inheriting form
        :class:`~cjklib.dictionary.install.DownloaderBase`
    """
    dictionaryModule = __import__("cjklib.dictionary.install")
    # get all classes that inherit from DownloaderBase
    return set([clss \
        for clss in dictionaryModule.dictionary.install.__dict__.values() \
        if type(clss) == types.TypeType \
        and issubclass(clss,
            dictionaryModule.dictionary.install.DownloaderBase) \
        and clss.PROVIDES])

_dictionaryMap = None
def getDownloaderClass(dictionaryName):
    """
    Get a dictionary downloader class by dictionary name.

    :type dictionaryName: str
    :param dictionaryName: dictionary name
    :rtype: type
    :return: downloader class
    """
    global _dictionaryMap
    if _dictionaryMap is None:
        _dictionaryMap = dict([(downloaderCls.PROVIDES, downloaderCls)
            for downloaderCls in getDownloaderClasses()])

    try:
        return _dictionaryMap[dictionaryName]
    except KeyError:
        raise ValueError("Unknown dictionary '%s'" % dictionaryName)

def getDownloader(dictionaryName, **options):
    """
    Get a dictionary downloader instance by dictionary name.

    :type dictionaryName: str
    :param dictionaryName: dictionary name
    :rtype: type
    :return: downloader instance
    """
    downloaderCls = getDownloaderClass(dictionaryName)
    return downloaderCls(**options)

#}
#{ Dictionary classes

class DownloaderBase(object):
    """Abstract class for downloading dictionaries."""
    PROVIDES = None

    def __init__(self, downloadFunc=None, quiet=True):
        self.quiet = quiet
        self.downloadFunc = downloadFunc

    def getDownloadLink(self):
        """
        Gets the download link for the online dictionary.

        Needs to be implemented by subclasses.
        """
        raise NotImplementedError()

    @cachedmethod
    def getVersion(self):
        """
        Version of the online available dictionary.
        """
        link = self.getDownloadLink()

        if not self.quiet: warn("Sending HEAD request to %s..." % link,
            endline=False)
        response = urllib.urlopen(link)
        lastModified = response.info().getheader('Last-Modified')
        if not self.quiet: warn("Done")
        if lastModified:
            return datetime.strptime(lastModified, '%a, %d %b %Y %H:%M:%S %Z')

    def download(self, **options):
        """
        Downloads the dictionary and returns the path to the local file.

        :param options: extra options
        :keyword targetName: target file name for downloaded file
        :keyword targetPath: target directory for downloaded file, file name
            will be used as provided online
        :keyword temporary: if ``True`` a temporary file will be created
            retaining the last extension (i.e. for .tar.gz only .gz will be
            guaranteed.
        :rtype: str
        :return: path to local file
        """
        if self.downloadFunc:
            return self.downloadFunc(**options)
        else:
            return self._download(**options)

    def _download(self, targetName=None, targetPath=None, temporary=False):
        link = self.getDownloadLink()

        _, _, onlinePath, _, _ = urlparse.urlsplit(link)
        originalFileName = os.path.basename(onlinePath)

        if temporary:
            fileName = None
        elif targetName:
            fileName = targetName
        elif targetPath:
            fileName = os.path.join(targetPath, originalFileName)
        else:
            fileName = originalFileName

        if not self.quiet:
            version = self.getVersion()
            if version:
                warn('Found version %s' % version)
            else:
                warn('Unable to determine version')
            warn("Downloading %s..." % link)
            path, _ = urllib.urlretrieve(link, fileName, progress)
            warn("Saved as %s" % path)
        else:
            path, _ = urllib.urlretrieve(link, fileName)

        return path


class EDICTDownloader(DownloaderBase):
    """Downloader for the EDICT dictionary."""
    PROVIDES = 'EDICT'
    DOWNLOAD_LINK = u'http://ftp.monash.edu.au/pub/nihongo/edict.gz'

    def getDownloadLink(self):
        return self.DOWNLOAD_LINK


class CEDICTGRDownloader(DownloaderBase):
    """Downloader for the Gwoyeu Romatzyh version of the CEDICT dictionary."""
    PROVIDES = 'CEDICTGR'
    DOWNLOAD_LINK = u'http://home.iprimus.com.au/richwarm/gr/cedictgr.zip'

    def getDownloadLink(self):
        return self.DOWNLOAD_LINK


class PageDownloaderBase(DownloaderBase):
    """
    Abstract class for downloading dictionaries by scraping the URL from a web
    page.
    """
    DEFAULT_DOWNLOAD_PAGE = None
    DOWNLOAD_REGEX = None
    DATE_REGEX = None
    DATE_FMT = None

    @cachedmethod
    def getDownloadPage(self):
        if not self.quiet: warn("Getting download page %s..."
            % self.DEFAULT_DOWNLOAD_PAGE, endline=False)
        f = urllib.urlopen(self.DEFAULT_DOWNLOAD_PAGE)
        downloadPage = f.read()
        f.close()
        if not self.quiet: warn("done")

        return downloadPage

    @cachedmethod
    def getDownloadLink(self):
        matchObj = self.DOWNLOAD_REGEX.search(self.getDownloadPage())
        if not matchObj:
            raise IOError("'Cannot read download page '%s'"
                % self.DEFAULT_DOWNLOAD_PAGE)

        baseUrl = matchObj.group(1)
        return urlparse.urljoin(self.DEFAULT_DOWNLOAD_PAGE, baseUrl)

    @cachedmethod
    def getVersion(self):
        matchObj = self.DATE_REGEX.search(self.getDownloadPage())
        if matchObj:
            return datetime.strptime(matchObj.group(1), self.DATE_FMT).date()


class CEDICTDownloader(PageDownloaderBase):
    """Downloader for the CEDICT dictionary."""
    PROVIDES = 'CEDICT'
    DEFAULT_DOWNLOAD_PAGE \
        = u'http://www.mdbg.net/chindict/chindict.php?page=cc-cedict'
    DOWNLOAD_REGEX = re.compile(
        u'<a href="(export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz)">')
    DATE_REGEX = re.compile(u'Latest release: <strong>([^<]+)</strong>')
    DATE_FMT = '%Y-%m-%d %H:%M:%S %Z'


class HanDeDictDownloader(PageDownloaderBase):
    """Downloader for the HanDeDict dictionary."""
    PROVIDES = 'HanDeDict'
    DEFAULT_DOWNLOAD_PAGE \
        = u'http://www.chinaboard.de/chinesisch_deutsch.php?mode=dl'
    DOWNLOAD_REGEX = re.compile(
        u'<a href="(handedict/handedict-(?:\d+).tar.bz2)">')
    DATE_REGEX = re.compile(u'<a href="handedict/handedict-(\d+).tar.bz2">')
    DATE_FMT = '%Y%m%d'


class CFDICTDownloader(PageDownloaderBase):
    """Downloader for the CFDICT dictionary."""
    PROVIDES = 'CFDICT'
    DEFAULT_DOWNLOAD_PAGE = u'http://www.chinaboard.de/cfdict.php?mode=dl'
    DOWNLOAD_REGEX = re.compile(u'<a href="(cfdict/cfdict-(?:\d+).tar.bz2)">')
    DATE_REGEX = re.compile(u'<a href="cfdict/cfdict-(\d+).tar.bz2">')
    DATE_FMT = '%Y%m%d'


class DictionaryInstaller(object):
    """
    Dictionary installer for downloading and installing a dictionary to a SQL
    database.
    """
    def __init__(self, quiet=True):
        self.quiet = quiet

    @classmethod
    def getDefaultDatabaseUrl(cls, dictionaryName, prefix=None, local=False,
        projectName='cjklib'):

        configuration = dbconnector.getDefaultConfiguration()
        if not configuration['sqlalchemy.url'].startswith('sqlite://'):
            # only know how to connect to this database
            return configuration['sqlalchemy.url']

        # for SQLite
        if sys.platform == 'win32':
            if local:
                path = os.path.join(os.path.expanduser('~'),
                    '%s' % projectName)
            elif 'APPDATA' in os.environ:
                path = os.path.join(os.environ['APPDATA'], projectName)
            else:
                major, minor = sys.version_info[0:2]
                path = "C:\Python%d%d\share\%s" % (major, minor, projectName)

        elif sys.platform == 'darwin':
            if local:
                path = os.path.join(os.path.expanduser('~'), "Library",
                    "Application Support", projectName)
            else:
                path = os.path.join("/Library", "Application Support",
                    projectName)

        else:
            if local:
                path = os.path.join(os.path.expanduser('~'),
                    '.%s' % projectName)
            else:
                prefix = prefix or '/usr/local'
                path = os.path.join(prefix, 'share', projectName)

        filePath = os.path.join(path, '%s.db' % dictionaryName.lower())
        return 'sqlite:///%s' % filePath

    def install(self, dictionaryName, **options):
        """
        Installs the given dictionary to a database.

        Different installation methods are possible:

        - by default a global installation is done, a single database file
            if installed for SQLite, for other engines the database is
            installed to the same database as cjklib's,
        - if ``local`` is set, the database file for SQLite is installed to
            the user's home directory,
        - ``databaseUrl`` can be speficied for a user defined database,
        - ``dbConnectInst`` can be given to write to an open database
            instance.

        :param options: extra options
        :keyword databaseUrl: database connection setting in the format
            ``driver://user:pass@host/database``.
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`
        :keyword local: if ``True`` the SQLite file will be installed in the
            user's home directory.
        :keyword prefix: installation prefix for a global install (Unix only).
        :keyword forceUpdate: dictionary will be installed even if a newer
            version already exists
        :keyword quiet: if ``True`` no status information will be printed to
            stdout
        """
        # get database connection
        configuration = {}

        local = options.pop('local', False)
        prefix = options.pop('prefix', None)
        configuration['sqlalchemy.url'] = options.pop('databaseUrl', None)

        if 'dbConnectInst' in options:
            db = options.pop('dbConnectInst')
        else:
            if not configuration['sqlalchemy.url']:
                configuration['sqlalchemy.url'] = self.getDefaultDatabaseUrl(
                    dictionaryName, local=local, prefix=prefix)

            # for sqlite check if directory exists
            url = make_url(configuration['sqlalchemy.url'])
            if url.drivername == 'sqlite':
                if url.database:
                    databaseFile = url.database
                    directory, _ = os.path.split(databaseFile)
                    if not os.path.exists(directory):
                        os.makedirs(directory)

            configuration['attach'] = options.pop('attach', [])
            if 'registerUnicode' in options:
                configuration['registerUnicode'] = options.pop(
                    'registerUnicode')

            db = dbconnector.DatabaseConnector(configuration)

        # download
        downloader = getDownloader(dictionaryName, quiet=self.quiet)

        # check if we already have newest version
        forceUpdate = options.pop('forceUpdate', False)
        if not forceUpdate and db.hasTable(dictionaryName):
            if db.hasTable('Version'):
                table = db.tables['Version']
                curVersion = db.selectScalar(select([table.c.ReleaseDate],
                    table.c.TableName==dictionaryName))

                newestVersion = downloader.getVersion()
                if isinstance(newestVersion, date):
                    newestVersion = datetime.combine(newestVersion, time(0))

                if newestVersion and curVersion and newestVersion <= curVersion:
                    if not self.quiet: warn("Newest version already installed")
                    return configuration['sqlalchemy.url']

        filePath = downloader.download(temporary=True)

        # create builder instance
        options['quiet'] = self.quiet
        dbBuilder = build.DatabaseBuilder(dbConnectInst=db, filePath=filePath,
            **options)

        try:
            tables = [dictionaryName]
            if not db.mainHasTable('Version'):
                tables.append('Version')
            dbBuilder.build(tables)

            table = db.tables['Version']
            db.execute(table.delete().where(
                table.c.TableName == dictionaryName))

            version = downloader.getVersion()
            if version:
                db.execute(table.insert().values(TableName=dictionaryName,
                    ReleaseDate=version))
        finally:
            # remove temporary tables
            dbBuilder.clearTemporary()

        return configuration['sqlalchemy.url']


class CommandLineInstaller(object):
    """Command line dictionary installer."""
    DB_PREFER_BUILDERS = []

    DESCRIPTION = """Downloads and installs a dictionary for the cjklib library.
Example: \"%prog --local CEDICT\"."""

    def run(self):
        """
        Runs the builder
        """
        # parse command line parameters
        parser = self.buildParser()
        (opts, args) = parser.parse_args()

        if len(args) == 0:
            parser.error("incorrect number of arguments")

        # download only
        if opts.download:
            if len(args) > 1 and opts.targetName:
                parser.error(
                    "option --targetName only allowed for a single dictionary"
                    " but %d dictionaries given" % len(args))
            for dictionary in args:
                downloader = getDownloader(dictionary, quiet=opts.quiet)

                downloader.download(targetName=opts.targetName,
                    targetPath=opts.targetPath)

            return True

        options = dict([(option, getattr(opts, option)) for option
            in dir(opts) if not hasattr(Values(), option)
                and getattr(opts, option) != None])

        installer = DictionaryInstaller(quiet=opts.quiet)
        for dictionary in args:
            try:
                installer.install(dictionary, **options)
            except OperationalError, e:
                if not opts.quiet:
                    warn("Error writing to database: %s" % e)
                    if not opts.local:
                        warn("Try choosing --local for installing into HOME")
                return False

        return True

    @classmethod
    def getBuilderConfigSettings(cls):
        """
        Gets the builder settings from the section ``Builder`` from cjklib.conf.

        :rtype: dict
        :return: dictionary of builder options

        .. todo::
            * Impl: Refactor, shares a lot of code with :mod:`cjklib.build.cli`
        """
        configOptions = getConfigSettings('Builder')
        # don't convert to lowercase
        ConfigParser.RawConfigParser.optionxform = lambda self, x: x
        config = ConfigParser.RawConfigParser(configOptions)

        dictionaryTables = [clss.PROVIDES for clss in getDownloaderClasses()]

        options = {}
        for builder in build.DatabaseBuilder.getTableBuilderClasses(
            resolveConflicts=False):
            if builder.PROVIDES not in dictionaryTables:
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
        options = {}
        # prefer
        options['prefer'] = cls.DB_PREFER_BUILDERS[:]

        options['attach'] = []

        config = dbconnector.getDefaultConfiguration()
        if 'registerUnicode' in config:
            options['registerUnicode'] = config['registerUnicode']

        # build specific options
        options.update(cls.getBuilderConfigSettings())
        return options

    def buildParser(self):
        """
        .. todo:
            * Impl: Refactor, shares a lot of code with :mod:`cjklib.build.cli`
        """
        usage = "%prog [options] DICTIONARY"
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
        parser.add_option("-f", "--forceUpdate", action="store_true",
            dest="forceUpdate", default=False,
            help="install dictionary even if the version is older or equal")
        parser.add_option("--prefix", action="store",
            metavar="PREFIX", dest="prefix", default=None,
            help="installation prefix")
        parser.add_option("--local", action="store_true",
            dest="local", default=False,
            help="install to user directory")
        parser.add_option("--download", action="store_true",
            dest="download", default=False,
            help="download only")
        parser.add_option("--targetName", action="store",
            dest="targetName", default=None,
            help="target name of downloaded file (only with --download)")
        parser.add_option("--targetPath", action="store",
            dest="targetPath", default=None,
            help="target directory of downloaded file (only with --download)")
        parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
            default=False, help="don't print anything on stdout")
        parser.add_option("--database", action="store", metavar="URL",
            dest="databaseUrl", default=None,
            help="database url")
        parser.add_option("--attach", action="appendResetDefault",
            metavar="URL", dest="attach", default=defaults.get("attach", []),
            help="attachable databases [default: %default]")
        parser.add_option("--registerUnicode", action="store", type='bool',
            metavar="BOOL", dest="registerUnicode",
            default=defaults.get("registerUnicode", False),
            help=("register own Unicode functions if no ICU support available"
                " [default: %default]"))

        dictionaryTables = [clss.PROVIDES for clss in getDownloaderClasses()]
        ignoreOptions = ['dataPath', 'filePath', 'fileType']

        optionSet = set(['rebuildExisting', 'rebuildDepending', 'quiet',
            'databaseUrl', 'attach', 'prefer'])
        globalBuilderGroup = OptionGroup(parser, "Global builder commands")
        localBuilderGroup = OptionGroup(parser, "Local builder commands")
        for builder in build.DatabaseBuilder.getTableBuilderClasses():
            if builder.PROVIDES not in dictionaryTables:
                continue

            for option, defaultValue in sorted(
                builder.getDefaultOptions().items()):
                if option in ignoreOptions:
                    continue
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


def main():
    try:
        if not CommandLineInstaller().run():
            sys.exit(1)
    except KeyboardInterrupt:
        print >> sys.stderr, "Keyboard interrupt."
        sys.exit(1)

if __name__ == "__main__":
    main()
