#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of cjklib.
#
# Copyright (C) 2009, 2010 cjklib developers
# Copyright (C) 2009 Raymond Hettinger
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
Utilities.
"""

import sys
import re
import copy
import os.path
import platform
import ConfigParser
from optparse import Option, OptionValueError
import csv

from sqlalchemy.types import String, Text

#{ Configuration and file access

def locateProjectFile(relPath, projectName='cjklib'):
    """
    Locates a project file relative to the project's directory. Returns ``None``
    if module ``pkg_resources`` is not installed or package information is not
    available.

    :type relPath: str
    :param relPath: path relative to project directory
    :type projectName: str
    :param projectName: name of project which will be used as name of the
        config file
    """
    try:
        from pkg_resources import (Requirement, resource_filename,
            DistributionNotFound)
    except ImportError:
        return
    try:
        return resource_filename(Requirement.parse(projectName), relPath)
    except DistributionNotFound:
        pass

def getConfigSettings(section, projectName='cjklib'):
    """
    Reads the configuration from the given section of the project's config file.

    :type section: str
    :param section: section of the config file
    :type projectName: str
    :param projectName: name of project which will be used as name of the
        config file
    :rtype: dict
    :return: configuration settings for the given project
    """
    # don't convert to lowercase
    h = ConfigParser.SafeConfigParser.optionxform
    try:
        ConfigParser.SafeConfigParser.optionxform = lambda self, x: x
        config = ConfigParser.SafeConfigParser()
        homeDir = os.path.expanduser('~')

        configFiles = []
        # Library directory
        libdir = locateProjectFile(projectName, projectName)
        if not libdir:
            if projectName != 'cjklib':
                import warnings
                warnings.warn("Cannot locate packaged files for project '%s'"
                    % projectName)
            # fall back to the directory of this file, only works for cjklib
            libdir = os.path.dirname(os.path.abspath(__file__))
        configFiles.append(os.path.join(libdir, '%s.conf' % projectName))

        # Windows
        if 'APPDATA' in os.environ:
            configFiles += [
                os.path.join(os.environ["APPDATA"], projectName,
                    '%s.conf' % projectName),
                ]
        # OSX
        if platform.system() == 'Darwin':
            configFiles += [
                os.path.join("/Library", "Application Support", projectName,
                    '%s.conf' % projectName),
                os.path.join(homeDir, "Library", "Application Support",
                    projectName, '%s.conf' % projectName),
                ]
        # Unix
        configFiles += [
            os.path.join('/', 'etc', '%s.conf' % projectName),
            os.path.join(homeDir, '.%s.conf' % projectName),
            os.path.join(homeDir, '%s.conf' % projectName),
            ]

        config.read(configFiles)

        configuration = dict(config.items(section))
    except ConfigParser.NoSectionError:
        configuration = {}

    ConfigParser.SafeConfigParser.optionxform = h

    return configuration

def getSearchPaths(projectName='cjklib'):
    """
    Gets a list of search paths for the given project.

    :type projectName: str
    :param projectName: name of project
    :rtype: list
    :return: list of search paths
    """
    searchPath = [
        # personal directory
        os.path.join(os.path.expanduser('~'), '.%s' % projectName),
        os.path.join(os.path.expanduser('~'), '%s' % projectName),
        ]

    # Unix
    searchPath += [
        "/usr/local/share/%s/" % projectName,
        "/usr/share/%s/" % projectName,
        # for Maemo
        "/media/mmc1/%s/" % projectName,
        "/media/mmc2/%s/" % projectName,
        ]

    # Windows
    if 'APPDATA' in os.environ:
        searchPath += [os.path.join(os.environ['APPDATA'], projectName),
            r"C:\Python24\share\%s" % projectName,
            r"C:\Python25\share\%s" % projectName,
            r"C:\Python26\share\%s" % projectName,
            ]

    # OSX
    if platform.system() == 'Darwin':
        searchPath += [
            os.path.join(os.path.expanduser('~'), "Library",
                "Application Support", projectName),
            os.path.join("/Library", "Application Support", projectName),
            ]

    # Respect environment variable, e.g. CJKLIB_DB_PATH
    env = "%s_DB_PATH" % projectName.upper()

    if env in os.environ and os.environ[env].strip():
        searchPath += os.environ[env].strip().split(os.path.pathsep)

    # Library directory
    libdir = locateProjectFile(projectName, projectName)
    if not libdir:
        if projectName != 'cjklib':
            import warnings
            warnings.warn("Cannot locate packaged files for project '%s'"
                % projectName)
        # fall back to the directory of this file, only works for cjklib
        libdir = os.path.dirname(os.path.abspath(__file__))

    searchPath.append(libdir)

    return searchPath

def getDataPath():
    """
    Gets the path to packaged data.

    :rtype: str
    :return: path
    """
    dataDir = locateProjectFile('cjklib/data', 'cjklib')
    if not dataDir:
        buildModule = __import__("cjklib.build")
        buildModulePath = os.path.dirname(os.path.abspath(
            buildModule.__file__))
        dataDir = os.path.join(buildModulePath, 'data')

    return dataDir

#{ Unicode support enhancement

# define our own titlecase methods, as the Python implementation is currently
#   buggy (http://bugs.python.org/issue6412), see also
#   http://www.unicode.org/mail-arch/unicode-ml/y2009-m07/0066.html
_FIRST_NON_CASE_IGNORABLE = re.compile(ur"(?u)([.˳｡￮₀ₒ]?\W*)(\w)(.*)$")
"""
Regular expression matching the first alphabetic character. Include GR neutral
tone forms.
"""
def titlecase(strng):
    u"""
    Returns the string (without "word borders") in titlecase.

    This function is not designed to work for multi-entity strings in general
    but rather for syllables with apostrophes (e.g. ``'Ch’ien1'``) and combining
    diacritics (e.g. ``'Hm\\u0300h'``). It additionally needs to support cases
    where a multi-entity string can derive from a single entity as in the case
    for *GR* (e.g. ``'Shern.me'`` for ``'Sherm'``).

    :type strng: str
    :param strng:  a string
    :rtype: str
    :return: the given string in titlecase

    .. todo::
        * Impl: While this function is only needed as long as Python doesn't
          ship with a proper title casing algorithm as defined by Unicode, we
          need a proper handling for *Wade-Giles*, as *Pinyin* *Erhua* forms
          will convert to two entities being separated by a hyphen, which does
          not fall in to the Unicode title casing algorithm's definition of a
          case-ignorable character.
    """
    matchObj = _FIRST_NON_CASE_IGNORABLE.match(strng.lower())
    if matchObj:
        tonal, firstChar, rest = matchObj.groups()
        return tonal + firstChar.upper() + rest

def istitlecase(strng):
    """
    Checks if the given string is in titlecase.

    :type strng: str
    :param strng:  a string
    :rtype: bool
    :return: ``True`` if the given string is in titlecase according to
        L{titlecase()}.
    """
    return titlecase(strng) == strng

if sys.maxunicode < 0x10000:
    def fromCodepoint(codepoint):
        """
        Creates a character for a Unicode codepoint similar to ``unichr``.

        For Python narrow builds this function does not raise a
        ``ValueError`` for characters outside the BMP but returns a string
        with a UTF-16 surrogate pair of two characters.

        .. seealso::

            `PEP 261 <http://www.python.org/dev/peps/pep-0261/>`_
        """
        if codepoint >= 0x10000:
            hi, lo = divmod(codepoint - 0x10000, 0x400)
            return unichr(0xd800 + hi) + unichr(0xdc00 + lo)
        else:
            return unichr(codepoint)

    def toCodepoint(char):
        """
        Returns the Unicode codepoint for this character similar to ``ord``.

        This function can handle surrogate pairs as used by narrow builds.

        :raise ValueError: if the string is not a single char or not a valid
            surrogate pair
        """
        if len(char) == 2:
            if not isValidSurrogate(char):
                raise ValueError('invalid surrogate pair')
            hi, lo = char
            return 0x10000 + (ord(hi) - 0xd800) * 0x400 + ord(lo) - 0xdc00
        else:
            return ord(char)

    def isValidSurrogate(string):
        """
        Returns ``True`` if the given string is a single surrogate pair.

        Always returns ``False`` for wide builds.
        """
        return (len(string) == 2 and u'\ud800' < string[0] < u'\udbff'
            and u'\udc00' < string[1] < u'\udfff')

    def getCharacterList(string):
        """
        Split a string of characters into a list of single characters.
        Parse UTF-16 surrogate pairs.
        """
        charList = []
        i = 0
        while i < len(string):
            if isValidSurrogate(string[i:i+2]):
                charList.append(string[i:i+2])
                i += 2
            else:
                charList.append(string[i])
                i += 1
        return charList

else:
    def fromCodepoint(codepoint):
        """
        Creates a character for a Unicode codepoint similar to ``unichr``.

        For Python narrow builds this function does not raise a
        ``ValueError`` for characters outside the BMP but returns a string
        with a UTF-16 surrogate pair of two characters.

        .. seealso::

            `PEP 261 <http://www.python.org/dev/peps/pep-0261/>`_
        """
        return unichr(codepoint)

    def toCodepoint(char):
        """
        Returns the Unicode codepoint for this character similar to ``ord``.

        This function can handle surrogate pairs as used by narrow builds.

        :raise ValueError: if the string is not a single char or not a valid
            surrogate pair
        """
        return ord(char)

    def isValidSurrogate(string):
        """
        Returns ``True`` if the given string is a single surrogate pair.

        Always returns ``False`` for wide builds.
        """
        return False

    def getCharacterList(string):
        """
        Split a string of characters into a list of single characters.
        Parse UTF-16 surrogate pairs.
        """
        return list(string)

#{ Helper methods

def cross(*args):
    """
    Builds a cross product of the given lists.

    Example:
        >>> cross(['A', 'B'], [1, 2, 3])
        [['A', 1], ['A', 2], ['A', 3], ['B', 1], ['B', 2], ['B', 3]]
    """
    ans = [[]]
    for arg in args:
        ans = [x+[y] for x in ans for y in arg]
    return ans

def crossDict(*args):
    """Builds a cross product of the given dicts."""
    def joinDict(a, b):
        a = a.copy()
        a.update(y)
        return a

    ans = [{}]
    for arg in args:
        ans = [joinDict(x, y) for x in ans for y in arg]
    return ans

#{ Helper classes

class CharacterRangeIterator(object):
    """Iterates over a given set of codepoint ranges given in hex."""
    def __init__(self, ranges):
        self.ranges = ranges[:]
        self._curRange = self._popRange()
    def _popRange(self):
        if self.ranges:
            charRange = self.ranges[0]
            del self.ranges[0]
            if type(charRange) == type(()):
                rangeFrom, rangeTo = charRange
            else:
                rangeFrom, rangeTo = (charRange, charRange)
            return (int(rangeFrom, 16), int(rangeTo, 16))
        else:
            return []
    def __iter__(self):
        return self
    def next(self):
        if not self._curRange:
            raise StopIteration

        curIndex, toIndex = self._curRange
        if curIndex < toIndex:
            self._curRange = (curIndex + 1, toIndex)
        else:
            self._curRange = self._popRange()
        return fromCodepoint(curIndex)

#{ Library extensions

class UnicodeCSVFileIterator(object):
    """Provides a CSV file iterator supporting Unicode."""
    class DefaultDialect(csv.Dialect):
        """Defines a default dialect for the case sniffing fails."""
        quoting = csv.QUOTE_NONE
        delimiter = ','
        lineterminator = '\n'
        quotechar = "'"
        # the following are needed for Python 2.4
        escapechar = "\\"
        doublequote = True
        skipinitialspace = False

    def __init__(self, fileHandle):
        self.fileHandle = fileHandle

    def __iter__(self):
        return self

    def next(self):
        if not hasattr(self, '_csvReader'):
            self._csvReader = self._getCSVReader(self.fileHandle)

        return [unicode(cell, 'utf-8') for cell in self._csvReader.next()]

    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    @staticmethod
    def byte_string_dialect(dialect):
        class ByteStringDialect(csv.Dialect):
            def __init__(self, dialect):
                for attr in ["delimiter", "quotechar", "escapechar",
                    "lineterminator"]:
                    old = getattr(dialect, attr)
                    if old is not None:
                        setattr(self, attr, str(old))

                for attr in ["doublequote", "skipinitialspace", "quoting"]:
                    setattr(self, attr, getattr(dialect, attr))

                csv.Dialect.__init__(self)

        return ByteStringDialect(dialect)

    def _getCSVReader(self, fileHandle):
        """
        Returns a csv reader object for a given file name.

        The file can start with the character '#' to mark comments. These will
        be ignored. The first line after the leading comments will be used to
        guess the csv file's format.

        :type fileHandle: file
        :param fileHandle: file handle of the CSV file
        :rtype: instance
        :return: CSV reader object returning one entry per line
        """
        def prependLineGenerator(line, data):
            """
            The first line red for guessing format has to be reinserted.
            """
            yield line
            for nextLine in data:
                yield nextLine

        line = '#'
        try:
            while line.strip().startswith('#'):
                line = fileHandle.next()
        except StopIteration:
            return csv.reader(fileHandle)
        try:
            self.fileDialect = csv.Sniffer().sniff(line, ['\t', ','])
            # fix for Python 2.4
            if len(self.fileDialect.delimiter) == 0:
                raise csv.Error()
        except csv.Error:
            self.fileDialect = UnicodeCSVFileIterator.DefaultDialect()

        content = prependLineGenerator(line, fileHandle)
        return csv.reader(
            UnicodeCSVFileIterator.utf_8_encoder(content),
            dialect=UnicodeCSVFileIterator.byte_string_dialect(
                self.fileDialect))
        #return csv.reader(content, dialect=self.fileDialect) # TODO


class ExtendedOption(Option):
    """
    Extends optparse by adding:

    - bool type, boolean can be set by ``True`` or ``False``, no one-way
      setting
    - path type, a list of paths given in one string separated by a colon
      ``':'``
    - extend action that resets a default value for user specified options
    - append action that resets a default value for user specified options
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
        if not value:
            return []
        else:
            return value.split(':')

    TYPES = Option.TYPES + ("bool", "pathstring")
    TYPE_CHECKER = copy.copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["bool"] = check_bool
    TYPE_CHECKER["pathstring"] = check_pathstring

    ACTIONS = Option.ACTIONS + ("extendResetDefault", "appendResetDefault")
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extendResetDefault",
        "appendResetDefault")
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extendResetDefault",
        "appendResetDefault")
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extendResetDefault",
        "appendResetDefault")

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extendResetDefault":
            if not hasattr(self, 'resetDefault'):
                self.resetDefault = set()
            if dest not in self.resetDefault:
                del values.ensure_value(dest, [])[:]
                self.resetDefault.add(dest)
            values.ensure_value(dest, []).extend(value)
        elif action == "appendResetDefault":
            if not hasattr(self, 'resetDefault'):
                self.resetDefault = set()
            if dest not in self.resetDefault:
                del values.ensure_value(dest, [])[:]
                self.resetDefault.add(dest)
            values.ensure_value(dest, []).append(value)
        else:
            Option.take_action(
                self, action, dest, opt, value, values, parser)

#{ SQLAlchemy column types

class _CollationMixin(object):
    def __init__(self, collation=None, **kwargs):
        """
        :param collation: Optional, a column-level collation for this string
          value.
        """
        self.collation = kwargs.get('collate', collation)

    def _extend(self, spec):
        """
        Extend a string-type declaration with standard SQL COLLATE annotation.
        """

        if self.collation:
            collation = 'COLLATE %s' % self.collation
        else:
            collation = None

        return ' '.join([c for c in (spec, collation) if c is not None])

    def get_search_list(self):
        return tuple()

class CollationString(_CollationMixin, String):
    def __init__(self, length=None, collation=None, **kwargs):
        """
        Construct a VARCHAR.

        :param collation: Optional, a column-level collation for this string
          value.
        """
        String.__init__(self, length, kwargs.get('convert_unicode', False),
            kwargs.get('assert_unicode', None))
        _CollationMixin.__init__(self, collation, **kwargs)

    def get_col_spec(self):
        if self.length:
            return self._extend("VARCHAR(%d)" % self.length)
        else:
            return self._extend("VARCHAR")


class CollationText(_CollationMixin, Text):
    def __init__(self, length=None, collation=None, **kwargs):
        """
        Construct a TEXT.

        :param collation: Optional, a column-level collation for this string
          value.
        """
        Text.__init__(self, length, kwargs.get('convert_unicode', False),
            kwargs.get('assert_unicode', None))
        _CollationMixin.__init__(self, collation, **kwargs)

    def get_col_spec(self):
        if self.length:
            return self._extend("TEXT(%d)" % self.length)
        else:
            return self._extend("TEXT")

#{ Decorators

def cachedproperty(fget):
    """
    Decorates a property to memoize its value.
    """
    def fget_wrapper(self):
        name = '_%s_cached' % fget.__name__
        try: return getattr(self, name)
        except AttributeError:
            value = fget(self)
            setattr(self, name, value)
            return value
    def fdel(self):
        name = '_%s_cached' % fget.__name__
        try: delattr(self, name)
        except AttributeError: pass
    return property(fget_wrapper, fdel=fdel, doc=fget.__doc__)


if sys.version_info >= (2, 5):
    import functools
    class cachedmethod(object):
        """
        Decorate a method to memoize its return value. Only applicable for
        methods without arguments.
        """
        def __init__(self, fget):
            self.fget = fget
            self.__doc__ = fget.__doc__
            self.__name__ = fget.__name__

        def __get__(self, obj, cls):
            @functools.wraps(self.fget)
            def oneshot(*args, **kwargs):
                @functools.wraps(self.fget)
                def memo(*a, **k): return result
                result = self.fget(*args, **kwargs)
                # save to instance __dict__
                args[0].__dict__[self.__name__] = memo
                return result
            return oneshot.__get__(obj, cls)
else:
    class cachedmethod(object):
        """
        Decorate a method to memoize its return value. Only applicable for
        methods without arguments.
        """
        def __init__(self, fget, doc=None):
            self.fget = fget
            self.__doc__ = doc or fget.__doc__
            self.__name__ = fget.__name__

        def __get__(self, obj, cls):
            def oneshot(*args, **kwargs):
                result = self.fget(*args, **kwargs)
                memo = lambda *a, **k: result
                memo.__name__ = self.__name__
                memo.__doc__ = self.__doc__
                # save to instance __dict__
                args[0].__dict__[self.__name__] = memo
                return result
            oneshot.__name__ = self.__name__
            oneshot.__doc__ = self.__doc__
            return oneshot.__get__(obj, cls)


if sys.version_info >= (2, 5):
    import warnings
    import functools

    def deprecated(func):
        """
        Decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used.
        """
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warnings.warn("Call to deprecated function %s." % func.__name__,
                category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return new_func
else:
    import warnings

    def deprecated(func):
        """
        Decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used.
        """
        def new_func(*args, **kwargs):
            warnings.warn("Call to deprecated function %s." % func.__name__,
                category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        new_func.__name__ = func.__name__
        new_func.__doc__ = func.__doc__
        new_func.__dict__.update(func.__dict__)
        return new_func

#{ Collection classes

if sys.version_info >= (2, 5):
    class LazyDict(dict):
        """A dict that will load entries on-demand."""
        def __init__(self, creator, *args):
            dict.__init__(self, *args)
            self.creator = creator

        def __missing__(self, key):
            self[key] = value = self.creator(key)
            return value
else:
    class LazyDict(dict):
        """A dict that will load entries on-demand."""
        def __init__(self, creator):
            dict.__init__(self, *args)
            self.creator = creator

        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                self[key] = value = self.creator(key)
                return value

if sys.version_info >= (2, 6):
    from collections import MutableMapping

    class OrderedDict(dict, MutableMapping):

        # Methods with direct access to underlying attributes

        def __init__(self, *args, **kwds):
            if len(args) > 1:
                raise TypeError('expected at 1 argument, got %d', len(args))
            if not hasattr(self, '_keys'):
                self._keys = []
            self.update(*args, **kwds)

        def clear(self):
            del self._keys[:]
            dict.clear(self)

        def __setitem__(self, key, value):
            if key not in self:
                self._keys.append(key)
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            self._keys.remove(key)

        def __iter__(self):
            return iter(self._keys)

        def __reversed__(self):
            return reversed(self._keys)

        def popitem(self):
            if not self:
                raise KeyError
            key = self._keys.pop()
            value = dict.pop(self, key)
            return key, value

        def __reduce__(self):
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            inst_dict.pop('_keys', None)
            return (self.__class__, (items,), inst_dict)

        # Methods with indirect access via the above methods

        setdefault = MutableMapping.setdefault
        update = MutableMapping.update
        pop = MutableMapping.pop
        keys = MutableMapping.keys
        values = MutableMapping.values
        items = MutableMapping.items

        def __repr__(self):
            pairs = ', '.join(map('%r: %r'.__mod__, self.items()))
            return '%s({%s})' % (self.__class__.__name__, pairs)

        def copy(self):
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            d = cls()
            for key in iterable:
                d[key] = value
            return d

else:
    from UserDict import DictMixin

    class OrderedDict(dict, DictMixin):

        def __init__(self, *args, **kwds):
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d'
                    % len(args))
            try:
                self.__end
            except AttributeError:
                self.clear()
            self.update(*args, **kwds)

        def clear(self):
            self.__end = end = []
            end += [None, end, end]      # sentinel node for doubly linked list
            self.__map = {}              # key --> [key, prev, next]
            dict.clear(self)

        def __setitem__(self, key, value):
            if key not in self:
                end = self.__end
                curr = end[1]
                curr[2] = end[1] = self.__map[key] = [key, curr, end]
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            key, prev, next = self.__map.pop(key)
            prev[2] = next
            next[1] = prev

        def __iter__(self):
            end = self.__end
            curr = end[2]
            while curr is not end:
                yield curr[0]
                curr = curr[2]

        def __reversed__(self):
            end = self.__end
            curr = end[1]
            while curr is not end:
                yield curr[0]
                curr = curr[1]

        def popitem(self, last=True):
            if not self:
                raise KeyError('dictionary is empty')
            if last:
                key = reversed(self).next()
            else:
                key = iter(self).next()
            value = self.pop(key)
            return key, value

        def __reduce__(self):
            items = [[k, self[k]] for k in self]
            tmp = self.__map, self.__end
            del self.__map, self.__end
            inst_dict = vars(self).copy()
            self.__map, self.__end = tmp
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def keys(self):
            return list(self)

        setdefault = DictMixin.setdefault
        update = DictMixin.update
        pop = DictMixin.pop
        values = DictMixin.values
        items = DictMixin.items
        iterkeys = DictMixin.iterkeys
        itervalues = DictMixin.itervalues
        iteritems = DictMixin.iteritems

        def __repr__(self):
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())

        def copy(self):
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            if isinstance(other, OrderedDict):
                return len(self)==len(other) and \
                    all(p==q for p, q in  zip(self.items(), other.items()))
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

