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
Entry factories for dictionaries.
"""

__all__ = [
    # entry factories
    "Tuple", "NamedTuple", "UnifiedHeadword",
    ]

from itertools import imap

#{ Entry factories

class Tuple(object):
    """Basic entry factory, returning a tuple of columns."""
    def getEntries(self, results):
        """
        Returns the dictionary results as lists.
        """
        return results


class NamedTuple(object):
    """
    Factory returning tuple entries with attribute-style access.
    """
    def _getNamedTuple(self):
        if not hasattr(self, '_namedTuple'):
            self._namedTuple = self._createNamedTuple('EntryTuple',
                self.columnNames)
        return self._namedTuple

    @staticmethod
    def _createNamedTuple(typename, fieldNames):
        # needed for Python 2.4 and 2.5
        try:
            from collections import namedtuple
        except ImportError:
            # Code from Raymond Hettinger under MIT licence,
            #   http://code.activestate.com/recipes/500261/
            from operator import itemgetter as _itemgetter
            from keyword import iskeyword as _iskeyword
            import sys as _sys

            def namedtuple(typename, field_names, verbose=False, rename=False):
                """Returns a new subclass of tuple with named fields.

                >>> Point = namedtuple('Point', 'x y')
                >>> Point.__doc__                   # docstring for the new class
                'Point(x, y)'
                >>> p = Point(11, y=22)             # instantiate with positional args or keywords
                >>> p[0] + p[1]                     # indexable like a plain tuple
                33
                >>> x, y = p                        # unpack like a regular tuple
                >>> x, y
                (11, 22)
                >>> p.x + p.y                       # fields also accessable by name
                33
                >>> d = p._asdict()                 # convert to a dictionary
                >>> d['x']
                11
                >>> Point(**d)                      # convert from a dictionary
                Point(x=11, y=22)
                >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
                Point(x=100, y=22)

                """

                # Parse and validate the field names.  Validation serves two purposes,
                # generating informative error messages and preventing template injection attacks.
                if isinstance(field_names, basestring):
                    field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
                field_names = tuple(map(str, field_names))
                if rename:
                    names = list(field_names)
                    seen = set()
                    for i, name in enumerate(names):
                        if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                            or not name or name[0].isdigit() or name.startswith('_')
                            or name in seen):
                                names[i] = '_%d' % i
                        seen.add(name)
                    field_names = tuple(names)
                for name in (typename,) + field_names:
                    if not min(c.isalnum() or c=='_' for c in name):
                        raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
                    if _iskeyword(name):
                        raise ValueError('Type names and field names cannot be a keyword: %r' % name)
                    if name[0].isdigit():
                        raise ValueError('Type names and field names cannot start with a number: %r' % name)
                seen_names = set()
                for name in field_names:
                    if name.startswith('_') and not rename:
                        raise ValueError('Field names cannot start with an underscore: %r' % name)
                    if name in seen_names:
                        raise ValueError('Encountered duplicate field name: %r' % name)
                    seen_names.add(name)

                # Create and fill-in the class template
                numfields = len(field_names)
                argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
                reprtxt = ', '.join('%s=%%r' % name for name in field_names)
                template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
                for i, name in enumerate(field_names):
                    template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
                if verbose:
                    print template

                # Execute the template string in a temporary namespace
                namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                                _property=property, _tuple=tuple)
                try:
                    exec template in namespace
                except SyntaxError, e:
                    raise SyntaxError(e.message + ':\n' + template)
                result = namespace[typename]

                # For pickling to work, the __module__ variable needs to be set to the frame
                # where the named tuple is created.  Bypass this step in enviroments where
                # sys._getframe is not defined (Jython for example) or sys._getframe is not
                # defined for arguments greater than 0 (IronPython).
                try:
                    result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
                except (AttributeError, ValueError):
                    pass

                return result

        return namedtuple(typename, fieldNames)

    def setDictionaryInstance(self, dictInstance):
        if not hasattr(dictInstance, 'COLUMNS'):
            raise ValueError('Incompatible dictionary')

        self.columnNames = dictInstance.COLUMNS

    def getEntries(self, results):
        """
        Returns the dictionary results as named tuples.
        """
        EntryTuple = self._getNamedTuple()
        return imap(EntryTuple._make, results)


class UnifiedHeadword(NamedTuple):
    """
    Factory adding a simple *Headword* key for CEDICT style dictionaries to
    provide results compatible with EDICT. An alternative headword is given in
    brackets if two different headword instances are provided in the entry.
    """
    def __init__(self, headword='s'):
        NamedTuple.__init__(self)
        if headword in ('s', 't'):
            self.headword = headword
        else:
            raise ValueError("Invalid type for headword '%s'."
                % headword \
                + " Allowed values 's'implified or 't'raditional")

    def _unifyHeadwords(self, entry):
        entry = list(entry)
        if self.headword == 's':
            headwords = (entry[0], entry[1])
        else:
            headwords = (entry[1], entry[0])

        if headwords[0] == headwords[1]:
            entry.append(headwords[0])
        else:
            entry.append(u'%s（%s）' % headwords)
        return entry

    def getEntries(self, results):
        """
        Returns the dictionary results as named tuples.
        """
        def augmentedEntry(entry):
            entry = self._unifyHeadwords(entry)
            return EntryTuple._make(entry)

        EntryTuple = self._getNamedTuple()
        return imap(augmentedEntry, results)

    def setDictionaryInstance(self, dictInstance):
        super(UnifiedHeadword, self).setDictionaryInstance(
            dictInstance)
        if not hasattr(dictInstance, 'COLUMNS'):
            raise ValueError('Incompatible dictionary')

        self.columnNames = dictInstance.COLUMNS + ['Headword']
