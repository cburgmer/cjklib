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
Character reading based functions (transliterations, romanizations, ...).
"""

__all__ = ['operator', 'converter', 'ReadingFactory']

import types

from cjklib.exception import UnsupportedError
from cjklib import dbconnector
from cjklib.reading import operator as readingoperator
from cjklib.reading import converter as readingconverter

class ReadingFactory(object):
    u"""
    Provides an abstract factory for creating
    :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>` and
    :class:`ReadingConverters <cjklib.reading.converter.ReadingConverter>`
    and a façade to directly access the methods offered by these classes.

    Instances of other classes are cached in the background and reused on later
    calls for methods accessed through the façade.
    :meth:`~cjklib.reading.ReadingFactory.createReadingOperator` and
    :meth:`~cjklib.reading.ReadingFactory.createReadingConverter` can be used to
    create new instances for use outside of the ReadingFactory.

    .. todo::
        * Impl: What about hiding of inner classes?
          :meth:`~cjklib.reading.ReadingFactory._checkSpecialOperators`
          method is called for internal converters and for external ones
          delivered by
          :meth:`~cjklib.reading.ReadingFactory.createReadingConverter`.
          Latter method doesn't return internal cached copies though, but
          creates new instances.
          :class:`~cjklib.reading.operator.ReadingOperator` also gets
          copies from ReadingFactory objects for internal instances.
          Sharing saves memory but changing one object
          will affect all other objects using this instance.
        * Impl: General reading options given for a converter with \*\*options
          need to be used on creating a operator. How to raise errors to save
          user of specifying an operator twice, one per options, one per
          concrete instance (similar to sourceOptions and targetOptions)?
    """
    @staticmethod
    def getReadingOperatorClasses():
        """
        Gets all classes implementing
        :class:`~cjklib.reading.operator.ReadingOperator` from module
        :mod:`cjklib.reading.operator`.

        :rtype: list
        :return: list of all classes inheriting form
            :class:`~cjklib.reading.operator.ReadingOperator`
        """
        # get all non-abstract classes that inherit from ReadingOperator
        readingOperatorClasses = [clss for clss \
            in readingoperator.__dict__.values() \
            if type(clss) == types.TypeType \
                and issubclass(clss, readingoperator.ReadingOperator) \
                and clss.READING_NAME]

        return readingOperatorClasses

    @staticmethod
    def getReadingConverterClasses():
        """
        Gets all classes implementing
        :class:`~cjklib.reading.converter.ReadingConverter` from module
        :mod:`cjklib.reading.converter`.

        :rtype: list
        :return: list of all classes inheriting form
            :class:`~cjklib.reading.converter.ReadingConverter`
        """
        # get all non-abstract classes that inherit from ReadingConverter
        readingConverterClasses = [clss \
            for clss in readingconverter.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, readingconverter.ReadingConverter) \
            and clss.CONVERSION_DIRECTIONS]

        return readingConverterClasses

    _sharedState = {'readingOperatorClasses': {}, 'readingConverterClasses': {}}
    """
    Dictionary holding global state information used by all instances of the
    ReadingFactory.
    """

    class SimpleReadingConverterAdaptor(object):
        """
        Defines a simple converter between two *character readings* that keeps
        the real converter doing the work in the background.

        The basic method is
        :meth:`~cjklib.reading.ReadingFactory.SimpleReadingConverterAdaptor.convert`
        which converts one input string from
        one reading to another. In contrast to a
        :class:`~cjklib.reading.converter.ReadingConverter` no source
        or target reading needs to be specified.
        """
        def __init__(self, converterInst, fromReading, toReading):
            """
            Creates an instance of the SimpleReadingConverterAdaptor.

            :type converterInst: instance
            :param converterInst:
                :class:`~cjklib.reading.converter.ReadingConverter` instance
                doing the actual conversion work.
            :type fromReading: str
            :param fromReading: name of reading converted from
            :type toReading: str
            :param toReading: name of reading converted to
            """
            self.converterInst = converterInst
            self.fromReading = fromReading
            self.toReading = toReading
            self.CONVERSION_DIRECTIONS = [(fromReading, toReading)]

        def convert(self, string, fromReading=None, toReading=None):
            """
            Converts a string in the source reading to the target reading.

            If parameters fromReading or toReading are not given the class's
            default values will be applied.

            :type string: str
            :param string: string written in the source reading
            :type fromReading: str
            :param fromReading: name of the source reading
            :type toReading: str
            :param toReading: name of the target reading
            :rtype: str
            :return: the input string converted to the ``toReading``
            :raise DecompositionError: if the string can not be decomposed into
                basic entities with regards to the source reading.
            :raise CompositionError: if the target reading's entities can not be
                composed.
            :raise ConversionError: on operations specific to the conversion
                between the two readings (e.g. error on converting entities).
            :raise UnsupportedError: if source or target reading not supported
                for conversion.
            """
            if not fromReading:
                fromReading = self.fromReading
            if not toReading:
                toReading = self.toReading
            return self.converterInst.convert(string, fromReading, toReading)

        def convertEntities(self, readingEntities, fromReading=None,
            toReading=None):
            """
            Converts a list of entities in the source reading to the target
            reading.

            If parameters fromReading or toReading are not given the class's
            default values will be applied.

            :type readingEntities: list of str
            :param readingEntities: list of entities written in source reading
            :type fromReading: str
            :param fromReading: name of the source reading
            :type toReading: str
            :param toReading: name of the target reading
            :rtype: list of str
            :return: list of entities written in target reading
            :raise ConversionError: on operations specific to the conversion
                between the two readings (e.g. error on converting entities).
            :raise UnsupportedError: if source or target reading is not
                supported for conversion.
            :raise InvalidEntityError: if an invalid entity is given.
            """
            if not fromReading:
                fromReading = self.fromReading
            if not toReading:
                toReading = self.toReading
            return self.converterInst.convertEntities(readingEntities,
                fromReading, toReading)

        def __getattr__(self, name):
            return getattr(self.converterInst, name)

    def __init__(self, databaseUrl=None, dbConnectInst=None):
        """
        Initialises the ReadingFactory.

        If no parameters are given default values are assumed for the connection
        to the database. The database connection parameters can be given in
        databaseUrl, or an instance of
        :class:`~cjklib.dbconnector.DatabaseConnector` can be passed in
        dbConnectInst, the latter one being preferred if both are specified.

        :type databaseUrl: str
        :param databaseUrl: database connection setting in the format
            ``driver://user:pass@host/database``.
        :type dbConnectInst: instance
        :param dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`
        """
        # get connector to database
        if dbConnectInst:
            self.db = dbConnectInst
        else:
            self.db = dbconnector.getDBConnector(databaseUrl)
        # create object instance cache if needed, shared with all factories
        #   using the same database connection
        if self.db not in self._sharedState:
            # clear also generates the structure
            self.clearCache()
        # publish default reading operators and converters
            for readingOperator in self.getReadingOperatorClasses():
                self.publishReadingOperator(readingOperator)
            for readingConverter in self.getReadingConverterClasses():
                self.publishReadingConverter(readingConverter)

    #{ Meta

    def clearCache(self):
        """Clears cached classes for the current database."""
        self._sharedState[self.db] = {}
        self._sharedState[self.db]['readingOperatorInstances'] = {}
        self._sharedState[self.db]['readingConverterInstances'] = {}

    def publishReadingOperator(self, readingOperator):
        """
        Publishes a :class:`~cjklib.reading.operator.ReadingOperator` to the
        list and thus makes it available for other methods in the library.

        :type readingOperator: classobj
        :param readingOperator: a new
            :class:`~cjklib.reading.operator.ReadingOperator` to be published
        """
        self._sharedState['readingOperatorClasses']\
            [readingOperator.READING_NAME] = readingOperator

    def getSupportedReadings(self):
        """
        Gets a list of all supported readings.

        :rtype: list of str
        :return: a list of readings a
            :class:`~cjklib.reading.operator.ReadingOperator` is available for
        """
        return self._sharedState['readingOperatorClasses'].keys()

    def getReadingOperatorClass(self, readingN):
        """
        Gets the :class:`~cjklib.reading.operator.ReadingOperator`'s class
        for the given reading.

        :type readingN: str
        :param readingN: name of a supported reading
        :rtype: classobj
        :return: a :class:`~cjklib.reading.operator.ReadingOperator` class
        :raise UnsupportedError: if the given reading is not supported.
        """
        if readingN not in self._sharedState['readingOperatorClasses']:
            raise UnsupportedError("reading '%s' not supported" % readingN)
        return self._sharedState['readingOperatorClasses'][readingN]

    def createReadingOperator(self, readingN, **options):
        """
        Creates an instance of a
        :class:`~cjklib.reading.operator.ReadingOperator` for the given reading.

        :type readingN: str
        :param readingN: name of a supported reading
        :param options: options for the created instance
        :rtype: instance
        :return: a :class:`~cjklib.reading.operator.ReadingOperator` instance
        :raise UnsupportedError: if the given reading is not supported.
        """
        operatorClass = self.getReadingOperatorClass(readingN)

        opt = options.copy()
        if 'dbConnectInst' not in opt:
            opt['dbConnectInst'] = self.db
        return operatorClass(**opt)

    def publishReadingConverter(self, readingConverter):
        """
        Publishes a :class:`~cjklib.reading.converter.ReadingConverter` to the
        list and thus makes it available for other methods in the library.

        :type readingConverter: classobj
        :param readingConverter: a new
            :class:`~cjklib.reading.converter.ReadingConverter` to be published
        """
        for fromReading, toReading in readingConverter.CONVERSION_DIRECTIONS:
            self._sharedState['readingConverterClasses']\
                [(fromReading, toReading)] = readingConverter

    def getReadingConverterClass(self, fromReading, toReading):
        """
        Gets the :class:`~cjklib.reading.converter.ReadingConverter`'s class
        for the given source and target reading.

        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :rtype: classobj
        :return: a :class:`~cjklib.reading.converter.ReadingConverter` class
        :raise UnsupportedError: if conversion for the given readings is not
            supported.
        """
        if not self.isReadingConversionSupported(fromReading, toReading):
            raise UnsupportedError(
                "conversion from '%s' to '%s' not supported"
                % (fromReading, toReading))
        return self._sharedState['readingConverterClasses']\
            [(fromReading, toReading)]

    def createReadingConverter(self, fromReading, toReading, *args, **options):
        """
        Creates an instance of a
        :class:`~cjklib.reading.converter.ReadingConverter` for the given
        source and target reading and returns it wrapped as a
        :class:`~cjklib.reading.ReadingFactory.SimpleReadingConverterAdaptor`.

        As
        :class:`ReadingConverters <cjklib.reading.converter.ReadingConverter>`
        generally support more than one conversion
        direction the user needs to specify which source and target reading is
        needed on a regular instance. Wrapping the created instance in the
        adaptor gives a simple convert() and convertEntities() routine, such
        that on conversion the source and target readings don't have to be
        specified. Other methods signatures remain unchanged.

        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :param args: optional list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            to use for handling source and target readings.
        :param options: options for the created instance
        :keyword hideComplexConverter: if true the
            :class:`~cjklib.reading.converter.ReadingConverter` is
            wrapped as a
            :class:`~cjklib.reading.ReadingFactory.SimpleReadingConverterAdaptor`
            (default).
        :keyword sourceOperators: list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings.
        :keyword targetOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            target readings.
        :keyword sourceOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings. If an
            operator for the source reading is explicitly specified, no options
            can be given.
        :keyword targetOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling target readings. If an
            operator for the target reading is explicitly specified, no options
            can be given.
        :rtype: instance
        :return: a
            :class:`~cjklib.reading.ReadingFactory.SimpleReadingConverterAdaptor`
            or :class:`~cjklib.reading.converter.ReadingConverter` instance
        :raise UnsupportedError: if conversion for the given readings is not
            supported.
        """
        converterClass = self.getReadingConverterClass(fromReading, toReading)

        self._checkSpecialOperators(fromReading, toReading, args, options)

        opt = options.copy()
        if 'dbConnectInst' not in opt:
            opt['dbConnectInst'] = self.db
        converterInst = converterClass(*args, **opt)
        if 'hideComplexConverter' not in options \
            or options['hideComplexConverter']:
            return ReadingFactory.SimpleReadingConverterAdaptor(
                converterInst=converterInst, fromReading=fromReading,
                toReading=toReading)
        else:
            return converterInst

    def isReadingConversionSupported(self, fromReading, toReading):
        """
        Checks if the conversion from reading A to reading B is supported.

        :rtype: bool
        :return: true if conversion is supported, false otherwise
        """
        return (fromReading, toReading) \
            in self._sharedState['readingConverterClasses']

    def isReadingOperationSupported(self, operation, readingN, **options):
        """
        Returns ``True`` if the given method is supported by the reading.

        :type operation: str
        :param operation: name of method
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: bool
        :return: ``True`` if method is supported, ``False`` otherwise.
        :raise ValueError: if the given method is not covered.
        """
        if not operation in ('decompose', 'compose', 'isReadingEntity',
            'isFormattingEntity',
            # romanisations
            'getDecompositions', 'segment', 'isStrictDecomposition',
            'getReadingEntities', 'getFormattingEntities',
            # Tonal fixed entities
            'getTones', 'getTonalEntity', 'splitEntityTone',
            'getPlainReadingEntities', 'isPlainReadingEntity'):
            raise ValueError("Operation '%s' is not a default reading operation"
                % operation)
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        return hasattr(readingOp, operation)

    def getDefaultOptions(self, *args):
        """
        Returns the default options for the
        :class:`~cjklib.reading.operator.ReadingOperator` or
        :class:`~cjklib.reading.converter.ReadingConverter` applied for
        the given reading name or names respectively.

        The keyword 'dbConnectInst' is not regarded a configuration option and
        is thus not included in the dict returned.

        :raise ValueError: if more than one or two reading names are given.
        :raise UnsupportedError: if no ReadingOperator or ReadingConverter
            exists for the given reading or readings respectively.
        """
        if len(args) == 1:
            return self.getReadingOperatorClass(args[0]).getDefaultOptions()
        elif len(args) == 2:
            return self.getReadingConverterClass(args[0], args[1])\
                .getDefaultOptions()
        else:
            raise ValueError("Wrong number of arguments")

    def _getReadingOperatorInstance(self, readingN, **options):
        """
        Returns an instance of a
        :class:`~cjklib.reading.operator.ReadingOperator` for the given
        reading from the internal cache and creates it if it doesn't exist yet.

        :type readingN: str
        :param readingN: name of a supported reading
        :param options: additional options for instance
        :rtype: instance
        :return: a :class:`~cjklib.reading.operator.ReadingOperator` instance
        :raise UnsupportedError: if the given reading is not supported.

        .. todo::
            * Impl: Get all options when calculating key for an instance and use
              the information on standard parameters thus minimising
              instances in cache. Same for
              :meth:`~cjklib.reading.ReadingFactory._getReadingConverterInstance`.
        """
        # construct key for lookup in cache
        cacheKey = (readingN, self._getHashableCopy(options))
        # get cache
        instanceCache = self._sharedState[self.db]['readingOperatorInstances']
        if cacheKey not in instanceCache:
            operatorInst = self.createReadingOperator(readingN, **options)
            instanceCache[cacheKey] = operatorInst
        return instanceCache[cacheKey]

    def _getReadingConverterInstance(self, fromReading, toReading, *args,
        **options):
        """
        Returns an instance of a
        :class:`~cjklib.reading.converter.ReadingConverter` for the given
        source and target reading from the internal cache and creates it
        if it doesn't exist yet.

        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :param args: optional list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            to use for handling source and target readings.
        :param options: additional options for instance
        :keyword sourceOperators: list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings.
        :keyword targetOperators: list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling target readings.
        :keyword sourceOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings. If an operator for the
            source reading is explicitly specified, no options can be given.
        :keyword targetOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling target readings. If an operator for the
            target reading is explicitly specified, no options can be given.
        :rtype: instance
        :return: an :class:`~cjklib.reading.converter.ReadingConverter` instance
        :raise UnsupportedError: if conversion for the given readings are not
            supported.

        .. todo::
            * Fix: Reusing of instances for other supported conversion
              directions isn't that efficient if a special ReadingOperator
              is specified for one direction, that doesn't affect others.
        """
        self._checkSpecialOperators(fromReading, toReading, args, options)

        # construct key for lookup in cache
        cacheKey = ((fromReading, toReading), self._getHashableCopy(options))
        # get cache
        instanceCache = self._sharedState[self.db]['readingConverterInstances']
        if cacheKey not in instanceCache:
            opt = options.copy()
            opt['hideComplexConverter'] = False
            converterInst = self.createReadingConverter(fromReading, toReading,
                *args, **options)
            # use instance for all supported conversion directions
            for convFromReading, convToReading \
                in converterInst.CONVERSION_DIRECTIONS:
                oCacheKey = ((convFromReading, convToReading),
                    self._getHashableCopy(options))
                if oCacheKey not in instanceCache:
                    instanceCache[oCacheKey] = converterInst
        return instanceCache[cacheKey]

    def _checkSpecialOperators(self, fromReading, toReading, args, options):
        """
        Checks for special operators requested for the given source and target
        reading.

        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :param args: optional list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            to use for handling source and target readings.
        :param options: additional options for handling the input
        :keyword sourceOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            source readings.
        :keyword targetOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            target readings.
        :keyword sourceOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings. If an
            operator for the source reading is explicitly specified, no options
            can be given.
        :keyword targetOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling target readings. If an
            operator for the target reading is explicitly specified, no options
            can be given.
        :raise ValueError: if options are given to create a specific
            ReadingOperator, but an instance is already given in ``args``.
        :raise UnsupportedError: if source or target reading is not supported.
        """
        # check options, don't overwrite existing operators
        for arg in args:
            if isinstance(arg, readingoperator.ReadingOperator):
                if arg.READING_NAME == fromReading \
                    and 'sourceOptions' in options:
                    raise ValueError(
                        "source reading operator options given, " \
                        + "but a source reading operator already exists")
                if arg.READING_NAME == toReading \
                    and 'targetOptions' in options:
                    raise ValueError(
                        "target reading operator options given, " \
                        + "but a target reading operator already exists")
        # create operators for options
        if 'sourceOptions' in options:
            readingOp = self._getReadingOperatorInstance(fromReading,
                **options['sourceOptions'])
            del options['sourceOptions']

            # add reading operator to converter
            if 'sourceOperators' not in options:
                options['sourceOperators'] = []
            options['sourceOperators'].append(readingOp)

        if 'targetOptions' in options:
            readingOp = self._getReadingOperatorInstance(toReading,
                **options['targetOptions'])
            del options['targetOptions']

            # add reading operator to converter
            if 'targetOperators' not in options:
                options['targetOperators'] = []
            options['targetOperators'].append(readingOp)

    @staticmethod
    def _getHashableCopy(data):
        """
        Constructs a unique hashable (partially deep-)copy for a given instance,
        replacing non-hashable datatypes ``set``, ``dict`` and ``list``
        recursively.

        :param data: non-hashable object
        :return: hashable object, ``set`` converted to a ``frozenset``, ``dict``
            converted to a ``frozenset`` of key-value-pairs (tuple), and ``list``
            converted to a ``tuple``.
        """
        if type(data) == type([]) or type(data) == type(()):
            newList = []
            for entry in data:
                newList.append(ReadingFactory._getHashableCopy(entry))
            return tuple(newList)
        elif type(data) == type(set([])):
            newSet = set([])
            for entry in data:
                newSet.add(ReadingFactory._getHashableCopy(entry))
            return frozenset(newSet)
        elif type(data) == type({}):
            newDict = {}
            for key in data:
                newDict[key] = ReadingFactory._getHashableCopy(data[key])
            return frozenset(newDict.items())
        else:
            return data

    #}
    #{ ReadingConverter methods

    def convert(self, readingStr, fromReading, toReading, *args, **options):
        """
        Converts the given string in the source reading to the given target
        reading.

        :type readingStr: str
        :param readingStr: string that needs to be converted
        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :param args: optional list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            to use for handling source and target readings.
        :param options: additional options for handling the input
        :keyword sourceOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            source readings.
        :keyword targetOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            target readings.
        :keyword sourceOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings. If an
            operator for the source reading is explicitly specified, no options
            can be given.
        :keyword targetOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling target readings. If an
            operator for the target reading is explicitly specified, no options
            can be given.
        :rtype: str
        :return: the converted string
        :raise DecompositionError: if the string can not be decomposed into
            basic entities with regards to the source reading or the given
            information is insufficient.
        :raise CompositionError: if the target reading's entities can not be
            composed.
        :raise ConversionError: on operations specific to the conversion between
            the two readings (e.g. error on converting entities).
        :raise UnsupportedError: if source or target reading is not supported
            for conversion.
        """
        readingConv = self._getReadingConverterInstance(fromReading, toReading,
            *args, **options)
        return readingConv.convert(readingStr, fromReading, toReading)

    def convertEntities(self, readingEntities, fromReading, toReading, *args,
        **options):
        """
        Converts a list of entities in the source reading to the given target
        reading.

        :type readingEntities: list of str
        :param readingEntities: list of entities written in source reading
        :type fromReading: str
        :param fromReading: name of the source reading
        :type toReading: str
        :param toReading: name of the target reading
        :param args: optional list of
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>` to use for
            handling source and target readings.
        :param options: additional options for handling the input
        :keyword sourceOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            source readings.
        :keyword targetOperators: list of :class:`ReadingOperators
            <cjklib.reading.operator.ReadingOperator>` used for handling
            target readings.
        :keyword sourceOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling source readings. If an
            operator for the source reading is explicitly specified, no options
            can be given.
        :keyword targetOptions: dictionary of options to configure the
            :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
            used for handling target readings. If an
            operator for the target reading is explicitly specified, no options
            can be given.
        :rtype: list of str
        :return: list of entities written in target reading
        :raise ConversionError: on operations specific to the conversion between
            the two readings (e.g. error on converting entities).
        :raise UnsupportedError: if source or target reading is not supported
            for conversion.
        :raise InvalidEntityError: if an invalid entity is given.
        """
        readingConv = self._getReadingConverterInstance(fromReading, toReading,
            *args, **options)
        return readingConv.convertEntities(readingEntities, fromReading,
            toReading)

    #}
    #{ ReadingOperator methods

    def decompose(self, string, readingN, **options):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each for the given reading.

        The given input string can contain other non reading characters, e.g.
        punctuation marks.

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        :type string: str
        :param string: reading string
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: list of str
        :return: a list of basic entities of the input string
        :raise DecompositionError: if the string can not be decomposed.
        :raise UnsupportedError: if the given reading is not supported.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        return readingOp.decompose(string)

    def compose(self, readingEntities, readingN, **options):
        """
        Composes the given list of basic entities to a string for the given
        reading.

        Composing entities can raise a :exc:`~cjklib.exception.CompositionError`
        if a non-reading entity is about to be joined with a reading entity
        and will result in a string that is impossible to decompose.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: str
        :return: composed entities
        :raise CompositionError: if the given entities can not be composed.
        :raise UnsupportedError: if the given reading is not supported.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        return readingOp.compose(readingEntities)

    def isReadingEntity(self, entity, readingN, **options):
        """
        Returns ``True`` if the given entity is a valid *reading entity*
        recognised by the reading operator, i.e. it will be returned by
        :meth:`~cjklib.reading.ReadingFactory.decompose`.

        :type entity: str
        :param entity: entity to check
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: bool
        :return: ``True`` if string is an entity of the reading, false otherwise.
        :raise UnsupportedError: if the given reading is not supported.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        return readingOp.isReadingEntity(entity)

    def isFormattingEntity(self, entity, readingN, **options):
        """
        Returns ``True`` if the given entity is a valid *formatting entity*
        recognised by the reading operator.

        :type entity: str
        :param entity: entity to check
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: bool
        :return: ``True`` if string is a formatting entity of the reading.
        :raise UnsupportedError: if the given reading is not supported.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        return readingOp.isFormattingEntity(entity)

    #}
    #{ RomanisationOperator methods

    def getDecompositions(self, string, readingN, **options):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each for ambiguous decompositions. It all possible
        decompositions. This method is a more general version of
        :meth:`~cjklib.reading.ReadingFactory.decompose`.

        The returned list construction consists of two entity types: entities of
        the romanisation and other strings.

        :type string: str
        :param string: reading string
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: list of list of str
        :return: a list of all possible decompositions consisting of basic
            entities.
        :raise DecompositionError: if the given string has a wrong format.
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'getDecompositions'):
            raise UnsupportedError("method 'getDecompositions' not supported")
        return readingOp.getDecompositions(string)

    def segment(self, string, readingN, **options):
        """
        Takes a string written in the romanisation and returns the possible
        segmentations as a list of syllables.

        In contrast to :meth:`~cjklib.reading.ReadingFactory.decompose`
        this method merely segments continuous entities of the romanisation.
        Characters not part of the romanisation will not be dealt with,
        this is the task of the more general decompose method.

        :type string: str
        :param string: reading string
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: list of list of str
        :return: a list of possible segmentations (several if ambiguous) into
            single syllables
        :raise DecompositionError: if the given string has an invalid format.
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'segment'):
            raise UnsupportedError("method 'segment' not supported")
        return readingOp.segment(string)

    def isStrictDecomposition(self, decomposition, readingN, **options):
        """
        Checks if the given decomposition follows the romanisation format
        strictly to allow unambiguous decomposition.

        The romanisation should offer a way/protocol to make an unambiguous
        decomposition into it's basic syllables possible as to make the process
        of appending syllables to a string reversible. The testing on compliance
        with this protocol has to be implemented here. Thus this method can only
        return true for one and only one possible decomposition for all strings.

        :type decomposition: list of str
        :param decomposition: decomposed reading string
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: bool
        :return: False, as this methods needs to be implemented by the sub class
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'isStrictDecomposition'):
            raise UnsupportedError(
                "method 'isStrictDecomposition' not supported")
        return readingOp.isStrictDecomposition(decomposition)

    def getReadingEntities(self, readingN, **options):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.

        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: set of str
        :return: set of supported *reading entities*
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'getReadingEntities'):
            raise UnsupportedError("method 'getReadingEntities' not supported")
        return readingOp.getReadingEntities()

    def getFormattingEntities(self, readingN, **options):
        """
        Gets a set of entities used by the reading to format
        *reading entities*.

        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: set of str
        :return: set of supported formatting entities
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'getFormattingEntities'):
            raise UnsupportedError(
                "method 'getFormattingEntities' not supported")
        return readingOp.getFormattingEntities()

    #}
    #{ TonalFixedEntityOperator methods

    def getTones(self, readingN, **options):
        """
        Returns a set of tones supported by the reading.

        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: list
        :return: list of supported tone marks.
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'getTones'):
            raise UnsupportedError("method 'getTones' not supported")
        return readingOp.getTones()

    def getTonalEntity(self, plainEntity, tone, readingN, **options):
        """
        Gets the entity with tone mark for the given plain entity and tone. The
        letter case of the given plain entity might not be fully conserved for
        mixed case strings.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :param tone: tone
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: str
        :return: entity with appropriate tone
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'getTonalEntity'):
            raise UnsupportedError("method 'getTonalEntity' not supported")
        return readingOp.getTonalEntity(plainEntity, tone)

    def splitEntityTone(self, entity, readingN, **options):
        """
        Splits the entity into an entity without tone mark (plain entity) and
        the entity's tone. The letter case of the given entity might not be
        fully conserved for mixed case strings.

        :type entity: str
        :param entity: entity with tonal information
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: tuple
        :return: plain entity without tone mark and entity's tone
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'splitEntityTone'):
            raise UnsupportedError("method 'splitEntityTone' not supported")
        return readingOp.splitEntityTone(entity)

    def getPlainReadingEntities(self, readingN, **options):
        """
        Gets the list of plain entities supported by this reading. Different to
        :meth:`~cjklib.reading.ReadingFactory.getReadingEntities`
        the entities will carry no tone mark.

        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: set of str
        :return: set of supported syllables
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'getPlainReadingEntities'):
            raise UnsupportedError(
                "method 'getPlainReadingEntities' not supported")
        return readingOp.getPlainReadingEntities()

    def isPlainReadingEntity(self, entity, readingN, **options):
        """
        Returns true if the given plain entity (without any tone mark) is
        recognised by the romanisation operator, i.e. it is a valid entity of
        the reading returned by the segmentation method.

        Reading entities will be handled as being case insensitive.

        :type entity: str
        :param entity: entity to check
        :type readingN: str
        :param readingN: name of reading
        :param options: additional options for handling the input
        :rtype: bool
        :return: ``True`` if string is an entity of the reading, ``False``
            otherwise.
        :raise UnsupportedError: if the given reading is not supported or the
            reading doesn't support the specified method.
        """
        readingOp = self._getReadingOperatorInstance(readingN, **options)
        if not hasattr(readingOp, 'isPlainReadingEntity'):
            raise UnsupportedError(
                "method 'isPlainReadingEntity' not supported")
        return readingOp.isPlainReadingEntity(entity)
