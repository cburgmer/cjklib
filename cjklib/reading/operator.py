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
Operation on character readings.
"""

# pylint: disable-msg=E1101
#  member variables are set by setattr()

__all__ = [
    # abstract
    "ReadingOperator", "RomanisationOperator", "TonalFixedEntityOperator",
    "TonalRomanisationOperator", "TonalIPAOperator", "SimpleEntityOperator",
    # specific
    "HangulOperator", "HiraganaOperator", "KatakanaOperator", "KanaOperator",
    "PinyinOperator", "WadeGilesOperator", "GROperator", "MandarinIPAOperator",
    "MandarinBrailleOperator", "JyutpingOperator", "CantoneseYaleOperator",
    "CantoneseIPAOperator"
    ]

import re
import string
import unicodedata
import copy
import types

from sqlalchemy import select
from sqlalchemy.sql import or_

from cjklib.exception import (DecompositionError, AmbiguousDecompositionError,
    InvalidEntityError, CompositionError, UnsupportedError,
    AmbiguousConversionError)
from cjklib import dbconnector
from cjklib.util import (titlecase, istitlecase, cross, cachedmethod,
    cachedproperty)

class ReadingOperator(object):
    """
    Defines an abstract operator on text written in a *character reading*.
    """
    READING_NAME = None
    """Unique name of reading"""

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        """
        if 'dbConnectInst' in options:
            self.db = options['dbConnectInst']
        else:
            self.db = dbconnector.getDBConnector()

        for option, defaultValue in self.getDefaultOptions().items():
            optionValue = options.get(option, defaultValue)
            if not hasattr(optionValue, '__call__'):
                setattr(self, option, copy.deepcopy(optionValue))
            else:
                setattr(self, option, optionValue)

    @classmethod
    def getDefaultOptions(cls):
        """
        Returns the reading operator's default options.

        The base class' implementation returns an empty dictionary. The keyword
        'dbConnectInst' is not regarded a configuration option of the operator
        and is thus not included in the dict returned.

        :rtype: dict
        :return: the reading operator's default options.
        """
        return {}

    def decompose(self, readingString):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each (exceptions possible).

        The given input string can contain other non reading characters, e.g.
        punctuation marks.

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        The base class' implementation will raise a NotImplementedError.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of str
        :return: a list of basic entities of the input string
        :raise DecompositionError: if the string can not be decomposed.
        """
        raise NotImplementedError

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string.

        Composing entities can raise a :exc:`~cjklib.exception.CompositionError`
        if a non-reading entity is about to be joined with a reading entity
        and will result in a string that is impossible to decompose.

        The base class' implementation will raise a NotImplementedError.

        :type readingEntities: list of str
        :param readingEntities: list of basic entities or other content
        :rtype: str
        :return: composed entities
        :raise CompositionError: if the given entities can not be composed.
        """
        raise NotImplementedError

    def isReadingEntity(self, entity):
        """
        Returns ``True`` if the given entity is a valid *reading entity*
        recognised by the reading operator, i.e. it will be returned by
        :meth:`~cjklib.reading.operator.ReadingOperator.decompose`.

        The base class' implementation will raise a NotImplementedError.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if string is an entity of the reading, false
            otherwise.
        """
        raise NotImplementedError

    def isFormattingEntity(self, entity):
        """
        Returns ``True`` if the given entity is a valid *formatting entity*
        recognised by the reading operator.

        The base class' implementation will always return False.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if string is a formatting entity of the reading.
        """
        return False


class RomanisationOperator(ReadingOperator):
    """
    Defines an abstract :class:`~cjklib.reading.operator.ReadingOperator` on
    text written in a *romanisation*, i.e. text written in the Latin alphabet
    or written in the Cyrillic alphabet.

    .. todo::
        * Impl: Optimise decompose() as to incorporate segment() and prune the
          tree while it is created. Does this though yield significant
          improvement? Would at least be O(n).
    """
    _readingEntityRegex = re.compile(u"([A-Za-z]+)")
    """Regular Expression for finding romanisation entities in input."""

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~cjklib.reading.operator.RomanisationOperator.segment`)
            and thus decomposition (using
            :meth:`~cjklib.reading.operator.RomanisationOperator.decompose`)
            will raise an exception if an alphabetic string is parsed which
            can not be segmented into single reading entities. If ``False``
            the aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will be
            supported.
        """
        super(RomanisationOperator, self).__init__(**options)

        if self.case not in ['lower', 'both']:
            raise ValueError("Invalid option %s for keyword 'case'"
                % repr(self.case))

    @classmethod
    def getDefaultOptions(cls):
        options = super(RomanisationOperator, cls).getDefaultOptions()
        options.update({'strictSegmentation': False, 'case': 'both'})

        return options

    @cachedmethod
    def getReadingCharacters(self):
        """
        Gets a list of characters parsed by this reading operator as reading
        entities. For alphabetic characters, lower case is returned.

        Separators like the apostrophe (``'``) in Pinyin are not part of reading
        entities and as such not included.

        :rtype: set
        :return: set of characters parsed by the reading operator
        """
        return frozenset(string.ascii_lowercase)

    def decompose(self, readingString):
        """
        Decomposes the given string into basic entities on a one-to-one mapping
        level to Chinese characters. Decomposing can be ambiguous and there are
        two assumptions made to solve this problem: If two subsequent entities
        together make up a longer valid entity, then the decomposition with the
        shorter entities can be disregarded. Furthermore it is assumed that the
        reading provides rules to mark entity borders and that these rules can
        be checked, so that the decomposition that abides by this rules will be
        prefered. This check is done by calling
        :meth:`~cjklib.reading.operator.RomanisationOperator.isStrictDecomposition`.

        The given input string can contain other characters not supported by the
        reading, e.g. punctuation marks. The returned list then contains a mix
        of basic reading entities and other characters e.g. spaces and
        punctuation marks.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of str
        :return: a list of basic entities of the input string
        :raise AmbiguousDecompositionError: if decomposition is ambiguous.
        :raise DecompositionError: if the given string has a wrong format.
        """
        decompositionParts = self.getDecompositionTree(readingString)

        strictDecomposition = []
        for segment in decompositionParts:
            if len(segment) == 1:
            # only one possible decomposition, don't care if strict or not
                strictDecomposition.extend(segment[0])
            else:
                # check for decompositions with syllables that together make up
                #   a syllable again, don't take these into account for the
                #   unique decomposition
                nonMergeableParts = []
                for decomposition in segment:
                    if not self._hasMergeableEntities(decomposition):
                        nonMergeableParts.append(decomposition)
                if len(nonMergeableParts) == 1:
                    strictDecomposition.extend(nonMergeableParts[0])
                else:
                    # get strict decomposition
                    for decomposition in nonMergeableParts:
                        if self.isStrictDecomposition(decomposition):
                            # there should be only one unambiguous
                            #   decomposition, so take this match
                            strictDecomposition.extend(decomposition)
                            break
                    else:
                        raise AmbiguousDecompositionError(
                            "decomposition of '%s' ambiguous: '%s'" \
                                % (readingString, ''.join(decomposition)))

        return strictDecomposition

    def getDecompositionTree(self, readingString):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each for all possible decompositions and returns
        the possible decompositions as a lattice.

        :type readingString: str
        :param readingString: reading string
        :rtype: list
        :return: a list of all possible decompositions consisting of basic
            entities as a lattice construct.
        :raise DecompositionError: if the given string has a wrong format.
        """
        # break string into pieces with alphabet and non alphabet parts
        decompositionParts = []
        # get partial segmentations
        for part in self._readingEntityRegex.split(readingString):
            if part == '':
                continue
            if not self._readingEntityRegex.match(part):
                # non-reading entity
                decompositionParts.append([[part]])
            else:
                segmentations = self.segment(part)
                decompositionParts.append(segmentations)

        return decompositionParts

    def getDecompositions(self, readingString):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each for all possible decompositions. This method
        is a more general version of
        :meth:`~cjklib.reading.operator.RomanisationOperator.decompose`.

        The returned list construction consists of two entity types: entities of
        the romanisation and other strings.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of list of str
        :return: a list of all possible decompositions consisting of basic
            entities.
        :raise DecompositionError: if the given string has a wrong format.
        """
        decompositionParts = self.getDecompositionTree(readingString)
        # merge segmentations to decomposition
        decompCrossProd = cross(*decompositionParts)

        decompositionList = []
        for line in decompCrossProd:
            resultList = []
            for entry in line:
                resultList.extend(entry)
            decompositionList.append(resultList)

        return decompositionList

    def segment(self, readingString):
        """
        Takes a string written in the romanisation and returns the possible
        segmentations as a list of syllables.

        In contrast to
        :meth:`~cjklib.reading.operator.RomanisationOperator.decompose` this
        method merely segments continuous
        entities of the romanisation. Characters not part of the romanisation
        will not be dealt with, this is the task of the more general decompose
        method.

        Option ``'strictSegmentation'`` controls the behaviour of this method
        for strings that cannot be parsed. If set to ``True`` segmentation will
        raise an exception, if set to ``False`` the given string will be
        returned unsegmented.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of list of str
        :return: a list of possible segmentations (several if ambiguous) into
            single syllables
        :raise DecompositionError: if the given string has an invalid format.
        """
        segmentationTree = self._recursiveSegmentation(readingString)
        if readingString != '' and len(segmentationTree) == 0:
            if self.strictSegmentation:
                raise DecompositionError(
                    u"Segmentation of '%s' not possible or invalid syllable" \
                        % readingString)
            else:
                return [[readingString]]
        resultList = []
        for entry in segmentationTree:
            resultList.extend(self._treeToList(entry))
        return resultList

    def _recursiveSegmentation(self, readingString):
        """
        Takes a string written in the romanisation and returns the possible
        segmentations as a tree of syllables.

        The tree is represented by tuples ``(syllable, subtree)``.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of tuple
        :return: a tree of possible segmentations (if ambiguous) into single
            syllables
        """
        segmentationParts = []
        substringIndex = 1
        while substringIndex <= len(readingString) \
            and self._hasEntitySubstring(
                readingString[0:substringIndex].lower()):

            entity = readingString[0:substringIndex]
            if self.isReadingEntity(entity) or self.isFormattingEntity(entity):
                remaining = readingString[substringIndex:]
                if remaining != '':
                    remainingParts = self._recursiveSegmentation(remaining)
                    if remainingParts != []:
                        segmentationParts.append((entity, remainingParts))
                else:
                    segmentationParts.append((entity, None))
            substringIndex = substringIndex + 1
        return segmentationParts

    def _hasMergeableEntities(self, decomposition):
        """
        Checks if the given decomposition has two or more following entities
        which together make up a new entity.

        Segmentation can give several results with some possible syllables being
        even further subdivided (e.g. *tian* to *ti'an* in Pinyin). These
        segmentations are only secondary and the segmentation with the longer
        syllables will be the one to take.

        :type decomposition: list of str
        :param decomposition: decomposed reading string
        :rtype: bool
        :return: True if following syllables make up a syllable
        """
        for startIndex in range(0, len(decomposition)-1):
            endIndex = startIndex + 2
            subDecomp = "".join(decomposition[startIndex:endIndex]).lower()
            while endIndex <= len(decomposition) and \
                self._hasEntitySubstring(subDecomp):
                if self.isReadingEntity(subDecomp):
                    return True
                endIndex = endIndex + 1
                subDecomp = "".join(decomposition[startIndex:endIndex]).lower()
        return False

    def isStrictDecomposition(self, decomposition):
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
        :rtype: bool
        :return: False, as this methods needs to be implemented by the sub class
        """
        return False

    @cachedproperty
    def _substringTable(self):
        """Set of entity substrings."""
        substrings = []
        entities = self.getReadingEntities() | self.getFormattingEntities()
        for entity in entities:
            for i in range(len(entity)):
                substrings.append(entity[0:i+1])
        return frozenset(substrings)

    def _hasEntitySubstring(self, readingString):
        """
        Checks if the given string is a entity supported by this romanisation
        or a substring of one.

        :type readingString: str
        :param readingString: reading string
        :rtype: bool
        :return: ``True`` if this string is *reading entity*,
            *formatting entity* or substring
        """
        return readingString in self._substringTable

    def isReadingEntity(self, entity):
        """
        Returns true if the given entity is recognised by the romanisation
        operator, i.e. it is a valid entity of the reading returned by the
        segmentation method.

        Letter case of characters will be handled depending on the setting for
        option ``'case'``.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if string is an entity of the reading, ``False``
            otherwise.
        """
        # check capitalisation
        if self.case == 'lower' and not entity.islower():
            return False

        return entity.lower() in self.getReadingEntities()

    @cachedmethod
    def getReadingEntities(self):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.
        The base class' implementation will raise a NotImplementedError.

        Returned entities are in lowercase.

        :rtype: set of str
        :return: set of supported *reading entities*
        """
        raise NotImplementedError

    def isFormattingEntity(self, entity):
        """
        Returns ``True`` if the given entity is a valid *formatting entity*
        recognised by the romanisation operator.

        Letter case of characters will be handled depending on the setting for
        option ``'case'``.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if string is a formatting entity of the reading.
        """
        # check capitalisation
        if self.case == 'lower' and entity.lower() != entity:
            return False

        return entity.lower() in self.getFormattingEntities()

    @cachedmethod
    def getFormattingEntities(self):
        """
        Gets a set of entities used by the reading to format
        *reading entities*.

        The base class' implementation will return an empty set.

        :rtype: set of str
        :return: set of supported *formatting entities*
        """
        return frozenset()

    @staticmethod
    def _treeToList(tupleTree):
        """
        Converts a tree to a list containing all full paths from root to leaf
        node.

        The tree is given by tuples ``(leaf node element, subtree)``.

        Example:
            >>> RomanisationOperator._treeToList(
            ...     ('A', [('B', None), ('C', [('D', None), ('E', None)])]))
            [['A', 'B'], ['A', 'C', 'D'], ['A', 'C', 'E']]

        :type tupleTree: tuple
        :param tupleTree: a tree realised through a tuple of a node and a
            subtree
        :rtype: list of list
        :return: a list of all paths contained by the given tree
        """
        resultList = []
        root, pathList = tupleTree
        if not pathList:
            return [[root]]
        for path in pathList:
            subList = RomanisationOperator._treeToList(path)
            for entry in subList:
                newEntry = [root]
                newEntry.extend(entry)
                resultList.append(newEntry)
        return resultList


class TonalFixedEntityOperator(ReadingOperator):
    """
    Provides an abstract :class:`~cjklib.reading.operator.ReadingOperator`
    for tonal languages for a reading based on a fixed set of reading entities.
    """
    def __init__(self, **options):
        """
        :param options: extra options
        """
        super(TonalFixedEntityOperator, self).__init__(**options)

    @cachedmethod
    def getTones(self):
        """
        Returns a set of tones supported by the reading. These tones don't
        necessarily reflect the tones of the underlying language but may defer
        to reflect notational or other features.

        The base class' implementation will raise a NotImplementedError.

        :rtype: list
        :return: list of supported tone marks.
        """
        raise NotImplementedError

    def getTonalEntity(self, plainEntity, tone):
        """
        Gets the entity with tone mark for the given plain entity and tone. The
        letter case of the given plain entity might not be fully conserved for
        mixed case strings.

        The base class' implementation will raise a NotImplementedError.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :param tone: tone
        :rtype: str
        :return: entity with appropriate tone
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the operation is not supported for the given
            form.
        """
        raise NotImplementedError

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark (plain entity) and
        the entity's tone. The letter case of the given entity might not be
        fully conserved for mixed case strings.

        The base class' implementation will raise a NotImplementedError.

        :type entity: str
        :param entity: entity with tonal information
        :rtype: tuple
        :return: plain entity without tone mark and entity's tone
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the operation is not supported for the given
            form.
        """
        raise NotImplementedError

    @cachedmethod
    def getReadingEntities(self):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.

        :rtype: list of str
        :return: list of supported syllables
        """
        syllables = []
        tones = self.getTones()
        for syllable in self.getPlainReadingEntities():
            for tone in tones:
                try:
                    syllables.append(self.getTonalEntity(syllable, tone))
                except InvalidEntityError:
                    # not all combinations of entities and tones are valid
                    pass
        return frozenset(syllables)

    @cachedmethod
    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. Different to
        :meth:`~TonalFixedEntityOperator.getReadingEntities`
        these entities will carry no tone mark.

        The base class' implementation will raise a NotImplementedError.

        :rtype: set of str
        :return: set of supported syllables
        """
        raise NotImplementedError

    def isPlainReadingEntity(self, entity):
        """
        Returns true if the given plain entity (without any tone mark) is
        recognised by the romanisation operator, i.e. it is a valid entity of
        the reading returned by the segmentation method.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if string is an entity of the reading, ``False``
            otherwise.
        """
        return entity in self.getPlainReadingEntities()

    def isReadingEntity(self, entity):
        # reimplement to keep memory footprint small
        # remove tone mark form and check plain entity
        try:
            plainEntity, tone = self.splitEntityTone(entity)
            return self.isPlainReadingEntity(plainEntity) \
                and tone in self.getTones()
        except InvalidEntityError:
            return False


class TonalRomanisationOperator(RomanisationOperator, TonalFixedEntityOperator):
    """
    Provides an abstract :class:`~cjklib.reading.operator.RomanisationOperator`
    for tonal languages incorporating methods from
    :class:`~cjklib.reading.operator.TonalFixedEntityOperator`.
    """
    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~cjklib.reading.operator.RomanisationOperator.segment`)
            and thus decomposition (using
            :meth:`~cjklib.reading.operator.RomanisationOperator.decompose`)
            will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If ``False`` the
            aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will be
            supported.
        """
        super(TonalRomanisationOperator, self).__init__(**options)

    @cachedmethod
    def getReadingEntities(self):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.

        Returned entities are in lowercase.

        :rtype: list of str
        :return: list of supported syllables
        """
        return TonalFixedEntityOperator.getReadingEntities(self)

    def isPlainReadingEntity(self, entity):
        """
        Returns true if the given plain entity (without any tone mark) is
        recognised by the romanisation operator, i.e. it is a valid entity of
        the reading returned by the segmentation method.

        Case of characters will be handled depending on the setting for option
        ``'case'``.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if string is an entity of the reading, ``False``
            otherwise.
        """
        # check for special capitalisation
        if self.case == 'lower' and not entity.islower():
            return False

        return TonalFixedEntityOperator.isPlainReadingEntity(self,
            entity.lower())

    def isReadingEntity(self, entity):
        return TonalFixedEntityOperator.isReadingEntity(self, entity)


class TonalIPAOperator(TonalFixedEntityOperator):
    u"""
    Defines an operator on strings of a tonal language written in the
    *International Phonetic Alphabet* (*IPA*).

    TonalIPAOperator does not supply the same closed set of syllables as
    other :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
    as IPA provides different ways to represent pronunciation.
    Because of that a user defined IPA syllable will not easily map
    to another transcription system and thus only basic support is provided
    for this direction.

    Tones in IPA can be expressed using different schemes. The following schemes
    are implemented here:

    - Numbers, tone numbers ,
    - ChaoDigits, numbers displaying the levels of Chao tone contours,
    - IPAToneBar, IPA modifying tone bar characters, e.g. ɛw˥˧,
    - Diacritics, diacritical marks and finally
    - None, no support for tone marks

    .. todo::
        * Lang: Shed more light on representations of tones in IPA.
        * Impl: Get all diacritics used in IPA as tones for
          :attr:`~cjklib.reading.operator.TonalIPAOperator.TONE_MARK_REGEX`.
        * Fix: What about CompositionError? All romanisations raise it, but
          they have a distinct set of characters that belong to the reading.
    """
    TONE_MARK_REGEX = {'numbers': re.compile(r'(?<!\d)(\d)$'),
        'superscriptNumbers': re.compile(ur'(?<![⁰¹²³⁴⁵⁶⁷⁸⁹])([⁰¹²³⁴⁵⁶⁷⁸⁹])$'),
        'chaoDigits': re.compile(r'([12345]+)$'),
        'superscriptChaoDigits': re.compile(ur'([¹²³⁴⁵]+)$'),
        'ipaToneBar': re.compile(ur'([˥˦˧˨˩꜈꜉꜊꜋꜌]+)$'),
        'diacritics': re.compile(ur'([\u0300\u0301\u0302\u0303\u030c]+)')
        }

    DEFAULT_TONE_MARK_TYPE = 'ipaToneBar'
    """Tone mark type to select by default."""

    TONES = []
    """List of tone names. Needs to be implemented in child class."""

    TONE_MARK_PREFER = {'numbers': {}, 'superscriptNumbers': {},
        'chaoDigits': {}, 'superscriptChaoDigits': {}, 'ipaToneBar': {},
        'diacritics': {}}
    """
    Mapping of tone marks to tone name which will be preferred on ambiguous
    mappings. Needs to be implemented in child classes.
    """

    TONE_MARK_MAPPING = {
        #'numbers': {}, 'chaoDigits': {}, 'ipaToneBar': {}, 'diacritics': {}
        }
    """
    Mapping of tone names to tone mark for each tone mark type. Needs to be
    implemented in child classes.
    """

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword toneMarkType: type of tone marks, one out of ``'numbers'``,
            ``'superscriptNumbers'``, ``'chaoDigits'``,
            ``'superscriptChaoDigits'``, ``'ipaToneBar'``, ``'diacritics'``,
            ``'none'``
        :keyword missingToneMark: if set to ``'noinfo'`` no tone information
            will be deduced when no tone mark is found (takes on value
            ``None``), if set to ``'ignore'`` this entity will not be valid.
            Either behaviour only becomes effective if the chosen
            ``'toneMarkType'`` makes no use of empty tone marks.
        """
        super(TonalIPAOperator, self).__init__(**options)

        assert (self.DEFAULT_TONE_MARK_TYPE in self.TONE_MARK_MAPPING
            or self.DEFAULT_TONE_MARK_TYPE == 'none')

        if (self.toneMarkType not in self.TONE_MARK_MAPPING
            and self.toneMarkType != 'none'):
            raise ValueError(
                "Option %r for keyword 'toneMarkType' not supported"
                % self.toneMarkType)

        assert (self.toneMarkType in self.TONE_MARK_REGEX
            or self.toneMarkType == 'none')
        assert (self.toneMarkType in self.TONE_MARK_PREFER
            or self.toneMarkType == 'none')

        # check if we have to be strict on tones, i.e. report missing tone info
        if self.missingToneMark not in ['noinfo', 'ignore']:
            raise ValueError("Invalid option %s for keyword 'missingToneMark'"
                % repr(self.missingToneMark))

        # split regex
        self._splitRegex = re.compile('([\.\s]+)')

    @classmethod
    def getDefaultOptions(cls):
        options = super(TonalIPAOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': cls.DEFAULT_TONE_MARK_TYPE,
            'missingToneMark': 'noinfo'})

        return options

    @classmethod
    def guessReadingDialect(cls, readingString, includeToneless=False):
        u"""
        Takes a string written in IPA and guesses the reading dialect.

        Supports option ``'toneMarkType'``.

        :type readingString: str
        :param readingString: IPA string
        :rtype: dict
        :return: dictionary of basic keyword settings
        """
        readingStr = unicodedata.normalize("NFC", unicode(readingString))

        toneMarkCount = dict((toneMarkType, 0)
            for toneMarkType in cls.TONE_MARK_REGEX)
        # guess tone mark type
        for entity in re.split('[ .]', readingStr):
            for toneMarkType in cls.TONE_MARK_REGEX:
                matchObj = cls.TONE_MARK_REGEX[toneMarkType].search(entity)
                if matchObj:
                    toneMarkCount[toneMarkType] += 1

        # chose tone mark tpye with max frequency in string
        maxCount = max(toneMarkCount.values())
        maxToneMarks = [toneMarkType for toneMarkType, count
            in toneMarkCount.items() if count == maxCount]
        # prefer the following in this order
        #   prefer numbers over toneMarkType as any single digit also false
        #   in to the latter
        for toneMarkType in ('ipaToneBar', 'diacritics', 'numbers'):
            if toneMarkType in maxToneMarks:
                break
        else:
            toneMarkType = maxToneMarks[0]

        return {'toneMarkType': toneMarkType}

    @cachedmethod
    def getTones(self):
        tones = self.TONES[:]
        if self.missingToneMark == 'noinfo' or self.toneMarkType == 'none':
            tones.append(None)

        return tones

    def decompose(self, readingString):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each (exceptions possible).

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        Single syllables can only be found if distinguished by a period or
        whitespace, such as
        :meth:`~cjklib.reading.operator.TonalIPAOperator.compose` would return.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of str
        :return: a list of basic entities of the input string
        """
        return self._splitRegex.split(readingString)

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string. IPA syllables are
        separated by a period.

        :type readingEntities: list of str
        :param readingEntities: list of basic entities or other content
        :rtype: str
        :return: composed entities
        """
        newReadingEntities = []
        if len(readingEntities) > 0:
            newReadingEntities.append(readingEntities[0])
            # separate two following entities in IPA with a dot to mark syllable
            #   boundary
            lastIsReadingEntity = self.isReadingEntity(readingEntities[0])
            for entity in readingEntities[1:]:
                isReadingEntity = self.isReadingEntity(entity)

                if lastIsReadingEntity and isReadingEntity:
                    newReadingEntities.append(u'.')
                newReadingEntities.append(entity)

                lastIsReadingEntity = isReadingEntity

        return "".join(newReadingEntities)

    def getTonalEntity(self, plainEntity, tone):
        """
        Gets the entity with tone mark for the given plain entity and tone.

        The plain entity returned will always be in Unicode's
        *Normalization Form C* (NFC, see http://www.unicode.org/reports/tr15/).

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: str
        :return: entity with appropriate tone
        :raise InvalidEntityError: if the entity is invalid.

        .. todo::
            * Impl: Place diacritics on main vowel, derive from IPA
              representation.
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'"
                    % (plainEntity, unicode(tone)))

        if self.toneMarkType == 'none' or tone == None:
            entity = plainEntity
        else:
            entity = plainEntity \
                + self.TONE_MARK_MAPPING[self.toneMarkType][tone]
        return unicodedata.normalize("NFC", entity)

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the name of the
        entity's tone.

        The plain entity returned will always be in Unicode's
        *Normalization Form C* (NFC, see http://www.unicode.org/reports/tr15/).

        :type entity: str
        :param entity: entity with tonal information
        :rtype: tuple
        :return: plain entity without tone mark and additionally the tone
        :raise InvalidEntityError: if the entity is invalid.
        """
        # get decomposed Unicode string, e.g. ``'â'`` to ``'u\u0302'``
        entity = unicodedata.normalize("NFD", unicode(entity))

        if self.toneMarkType == 'none':
            return unicodedata.normalize("NFC", entity), None
        else:
            matchObj = self.TONE_MARK_REGEX[self.toneMarkType].search(entity)
            if matchObj:
                toneMark = matchObj.group(1)
            else:
                toneMark = ''

            tone = self.getToneForToneMark(toneMark)

            if tone in self.getTones():
                # strip off tone mark
                plainEntity = entity.replace(toneMark, '')
                return unicodedata.normalize("NFC", plainEntity), tone

        raise InvalidEntityError("Invalid entity given for '" + entity + "'")

    @cachedproperty
    def _toneMarkLookup(self):
        """Returns a mapping of tone marks to tone."""
        toneMarkLookup = {}
        for tone in self.TONE_MARK_MAPPING[self.toneMarkType]:
            if tone == None:
                continue
            mark = self.TONE_MARK_MAPPING[self.toneMarkType][tone]
            # fill lookup with tone mark, overwrite if another tone mark
            #   was already entered but the current tone mark is prefered
            if mark not in toneMarkLookup \
                or (mark in self.TONE_MARK_PREFER[self.toneMarkType] \
                and self.TONE_MARK_PREFER[self.toneMarkType][mark] == tone):
                toneMarkLookup[mark] = tone
            elif mark not in self.TONE_MARK_PREFER[self.toneMarkType]:
                # not specifying a preference mapping for more than two
                #   possible tones will result in undefined mapping
                raise Exception(
                    "Ambiguous tone mark '%s' found" % mark \
                    + ", but no preference mapping defined.")
        return toneMarkLookup

    def getToneForToneMark(self, toneMark):
        """
        Gets the tone for the given tone mark.

        :type toneMark: str
        :param toneMark: tone mark representation of the tone
        :rtype: str
        :return: tone
        :raise InvalidEntityError: if the toneMark does not exist.
        """
        # get outside try block, will be evaluated on first call
        toneMarkLookup = self._toneMarkLookup
        try:
            return toneMarkLookup[toneMark]
        except KeyError:
            if toneMark == '' and self.missingToneMark == 'noinfo':
                return None
            else:
                raise InvalidEntityError("Invalid tone mark given with '%s'"
                    % toneMark)


class SimpleEntityOperator(ReadingOperator):
    """Provides an operator on readings with a single character per entity."""
    def decompose(self, readingString):
        readingEntities = []
        i = 0
        while i < len(readingString):
            # look for non-entity characters first
            oldIndex = i
            while i < len(readingString) \
                and not self.isReadingEntity(readingString[i]):
                i = i + 1
            if oldIndex != i:
                readingEntities.append(readingString[oldIndex:i])
            # if we didn't reach the end of the input we have a entity char
            if i < len(readingString):
                readingEntities.append(readingString[i])
            i = i + 1
        return readingEntities

    def compose(self, readingEntities):
        return ''.join(readingEntities)


class HangulOperator(SimpleEntityOperator):
    """Provides an operator on Korean text written in *Hangul*."""
    READING_NAME = "Hangul"

    def isReadingEntity(self, entity):
        return (entity >= u'가') and (entity <= u'힣')


class HiraganaOperator(SimpleEntityOperator):
    """Provides an operator on Japanese text written in *Hiragana*."""
    READING_NAME = "Hiragana"

    def isReadingEntity(self, entity):
        return (entity >= u'ぁ') and (entity <= u'ゟ')


class KatakanaOperator(SimpleEntityOperator):
    """Provides an operator on Japanese text written in *Katakana*."""
    READING_NAME = "Katakana"

    def isReadingEntity(self, entity):
        return (entity >= u'゠') and (entity <= u'ヿ')


class KanaOperator(SimpleEntityOperator):
    """
    Provides an operator on Japanese text written in a mix of *Hiragana* and
    *Katakana*.
    """
    READING_NAME = "Kana"

    def isReadingEntity(self, entity):
        return ((entity >= u'ぁ') and (entity <= u'ヿ'))


class PinyinOperator(TonalRomanisationOperator):
    ur"""
    Provides an operator for the Mandarin romanisation Hanyu Pinyin.
    It can be configured to cope with different representations (*"dialects"*)
    of Pinyin. For conversion between different representations the
    :class:`~cjklib.reading.converter.PinyinDialectConverter` can be used.

    .. todo::
        * Impl: ISO 7098 asks for conversion of ``。、·「」`` to ``.,-«»``. What
          about ``，？《》：－``? Implement a method for conversion to be
          optionally used.
        * Impl: Special marker for neutral tone: 'mȧ' (u'm\\u0227', reported by
          Ching-song Gene Hsiao: A Manual of Transcription Systems For
          Chinese, 中文拼音手册. Far Eastern Publications, Yale University,
          New Haven, Connecticut, 1985, ISBN 0-88710-141-0. Seems like
          left over from Pinjin, 1956), and '·ma' (u'\\xb7ma', check!:
          现代汉语词典（第5版）[Xiàndài Hànyǔ Cídiǎn 5. Edition].
          商务印书馆 [Shāngwù Yìnshūguǎn], Beijing, 2005, ISBN 7-100-04385-9.)
        * Impl: Consider handling ``\*nue`` and ``\*lue``.
    """
    READING_NAME = 'Pinyin'

    TONEMARK_VOWELS = [u'a', u'e', u'i', u'o', u'u', u'ü', u'n', u'm', u'r',
        u'ê', u'ŋ']
    """
    List of characters of the nucleus possibly carrying the tone mark. *n* is
    included in standalone syllables *n* and *ng*. *r* is used for supporting
    *Erhua* in a two syllable form, *ŋ* is the shortened form of *ng*.
    """

    PINYIN_SOUND_REGEX \
        = re.compile(u'^([^aeiuoü]*)([aeiuoü]*)([^aeiuoü]*)$',
            re.IGNORECASE | re.UNICODE)
    """
    Regular Expression matching onset, nucleus and coda. Syllables 'n', 'ng',
    'r' (for Erhua) and 'ê' have to be handled separately.
    """

    Y_VOWEL_LIST = [u'ü', 'v', 'u:', 'uu']
    """List of vowels for [y] after initials n/l used in guessing routine."""

    DIACRITICS_LIST = {1: [u'\u0304'], 2: [u'\u0301'],
        3: [u'\u030c', u'\u0306', u'\u0302'], 4: [u'\u0300']}
    """
    Dictionary of diacritics per tone used in guessing routine.
    Only diacritics with *canonical combining class* 230 supported
    (unicodedata.combining() == 230, see Unicode 3.11, or
    http://unicode.org/Public/UNIDATA/UCD.html#Canonical_Combining_Class_Values),
    due to implementation of how ü and ê, ẑ, ĉ, ŝ are handled.
    """

    APOSTROPHE_LIST = ["'", u'’', u'´', u'‘', u'`', u'ʼ', u'ˈ', u'′', u'ʻ']
    """List of apostrophes used in guessing routine."""

    def __init__(self, **options):
        u"""
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~PinyinOperator.segment`) and thus decomposition (using
            :meth:`~PinyinOperator.decompose`) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If ``False`` the
            aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will be
            supported.
        :keyword toneMarkType: if set to ``'diacritics'`` tones will be marked
            using diacritic marks, if set to ``'numbers'`` appended numbers from
            1 to 5 will be used to mark tones, if set to ``'none'`` no tone
            marks will be used and no tonal information will be supplied at all.
        :keyword missingToneMark: if set to ``'fifth'`` no tone mark is set to
            indicate the fifth tone (*qingsheng*, e.g. ``'wo3men'`` stands for
            ``'wo3men5'``), if set to ``'noinfo'``, no tone information will be
            deduced when no tone mark is found (takes on value ``None``), if set
            to ``'ignore'`` this entity will not be valid and for segmentation
            the behaviour defined by ``'strictSegmentation'`` will take affect.
            This option only has effect for the tone mark type ``'numbers'``.
        :keyword strictDiacriticPlacement: if set to ``True`` syllables have to
            follow the diacritic placement rule of Pinyin strictly.
            Wrong placement will result in
            :meth:`~PinyinOperator.splitEntityTone` raising an
            :exc:`~cjklib.exception.InvalidEntityError`. Defaults to
            ``False``. In either way, diacritics must be placed on one of the
            vowels (nasal semi-vowels being an exception).
        :keyword pinyinDiacritics: a 4-tuple of diacritic marks for tones one
            to for. If a circumflex (U+0302) is contained as diacritic mark,
            special vowel *ê* will not be supported and the given string will
            be interpreted as tonal version of vowel *e*.
        :keyword yVowel: a character (or string) that is taken as alternative
            for *ü* which depicts (among others) the close front rounded vowel
            [y] (IPA) in Pinyin and includes an umlaut. Changes forms of
            syllables *nü, nüe, lü, lüe*. This option is not valid for the
            tone mark type ``'diacritics'``.
        :keyword shortenedLetters: if set to ``True`` final letter *ng* will be
            shortend to *ŋ*, and initial letters *zh*, *ch*, *sh* will be
            shortend to *ẑ*, *ĉ*, *ŝ*.
        :keyword pinyinApostrophe: an alternate apostrophe that is taken instead
            of the default one.
        :keyword pinyinApostropheFunction: a function that indicates when a
            syllable combination needs to be split by an *apostrophe*, see
            :meth:`~PinyinOperator.aeoApostropheRule` for the default
            implementation.
        :keyword erhua: if set to ``'ignore'`` no special support will be
            provided for retroflex -r at syllable end (*Erhua*), i.e. *zher*
            will raise an exception. If set to ``'twoSyllables'`` syllables with
            an append r are given/will be segmented into two syllables, the -r
            suffix making up one syllable itself as ``'r'``. If set to
            ``'oneSyllable'`` syllables with an appended r are given/will be
            segmented into one syllable only.
        """
        super(PinyinOperator, self).__init__(**options)

        # check tone marks
        if self.toneMarkType not in ['diacritics', 'numbers', 'none']:
            raise ValueError("Invalid option %s for keyword 'toneMarkType'"
                % repr(self.toneMarkType))

        # check strictness on tones, i.e. report missing tone info
        if self.missingToneMark not in ['fifth', 'noinfo', 'ignore']:
            raise ValueError("Invalid option %s for keyword 'missingToneMark'"
                % repr(self.missingToneMark))

        self.pinyinDiacritics = tuple(self.pinyinDiacritics)
        # check diacritics
        if len(self.pinyinDiacritics) != 4:
            raise ValueError("Invalid value %s for keyword 'pinyinDiacritics'"
                % repr(self.pinyinDiacritics))
        elif len(set(self.pinyinDiacritics)) != 4:
            raise ValueError(
                "Non-injective value %s for keyword 'pinyinDiacritics'"
                    % repr(self.pinyinDiacritics))

        # Lookup of tone marks for tones
        self._tonemarkMap = dict([(diacritic, idx + 1) for idx, diacritic \
            in enumerate(self.pinyinDiacritics)])
        self._tonemarkMapReverse = dict([(idx + 1, diacritic) \
            for idx, diacritic in enumerate(self.pinyinDiacritics)])

        # Regular Expression matching the Pinyin tone marks.
        tonemarkVowels = set(self.TONEMARK_VOWELS)
        if u'\u0302' in self.pinyinDiacritics:
            # if circumflex is included, disable vowel ê
            tonemarkVowels.remove(u'ê')
        tonemarkVowelsNFD = sorted([unicodedata.normalize("NFD", vowel) \
            for vowel in tonemarkVowels], reverse=True)
        diacriticsSorted = sorted(self.pinyinDiacritics, reverse=True)
        self._toneMarkRegex = re.compile(u'((?:%s)+)(%s)' \
            % ('|'.join([re.escape(vowel) for vowel in tonemarkVowelsNFD]),
                '|'.join([re.escape(d) for d in diacriticsSorted])),
            re.IGNORECASE | re.UNICODE)

        # check alternative ü vowel
        self.yVowel = self.yVowel.lower()
        if self.toneMarkType == 'diacritics' and self.yVowel != u'ü':
            raise ValueError(
                "Keyword 'yVowel' is not valid for tone mark type 'diacritics'")

        # check apostrophe function
        if not hasattr(self.pinyinApostropheFunction, '__call__'):
            raise ValueError("Non-callable object %s" \
                    % repr(self.pinyinApostropheFunction)
                + " for keyword 'pinyinApostropheFunction'")

        # check Erhua support
        if self.erhua not in ['ignore', 'twoSyllables', 'oneSyllable']:
            raise ValueError("Invalid option %s for keyword 'erhua'"
                % repr(self.erhua))

        # set split regular expression, works for all 3 main dialects, get at
        #   least the whole alphabet to have a conservative recognition
        self._readingEntityRegex = re.compile(u'((?:' \
            + '|'.join([re.escape(v) for v in self._getDiacriticVowels()]) \
            + '|' + re.escape(self.yVowel) \
            + u'|[a-zêüŋẑĉŝ])+[12345]?)', re.IGNORECASE | re.UNICODE)

    @classmethod
    def getDefaultOptions(cls):
        options = super(PinyinOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'diacritics',
            'missingToneMark': 'noinfo', 'strictDiacriticPlacement': False,
            'pinyinDiacritics': (u'\u0304', u'\u0301', u'\u030c', u'\u0300'),
            'yVowel': u'ü', 'shortenedLetters': False, 'pinyinApostrophe': "'",
            'erhua': 'twoSyllables',
            'pinyinApostropheFunction': PinyinOperator.aeoApostropheRule})

        return options

    def _getDiacriticVowels(self):
        u"""
        Gets a list of Pinyin vowels with diacritical marks for tones.

        The alternative for vowel *ü* does not need diacritical forms as the
        standard form doesn't allow changing the vowel.

        :rtype: list of str
        :return: list of Pinyin vowels with diacritical marks
        """
        # no need to take care of user specified ü, as this is not possible for
        #   tone mark type 'diacritics' by convention
        vowelList = []
        for vowel in PinyinOperator.TONEMARK_VOWELS:
            for mark in self.pinyinDiacritics:
                vowelList.append(unicodedata.normalize("NFC", vowel + mark))
        return vowelList

    @classmethod
    def guessReadingDialect(cls, readingString, includeToneless=False):
        u"""
        Takes a string written in Pinyin and guesses the reading dialect.

        The basic options ``'toneMarkType'``, ``'pinyinDiacritics'``,
        ``'yVowel'``, ``'erhua'``, ``'pinyinApostrophe'`` and
        ``'shortenedLetters'`` are guessed.
        Unless ``'includeToneless'`` is set to ``True`` only the tone mark types
        ``'diacritics'`` and ``'numbers'`` are considered as the latter one can
        also represent the state of missing tones. Strings tested for
        ``'yVowel'`` are ``ü``, ``v`` and ``u:``. ``'erhua'`` is set to
        ``'twoSyllables'`` by default and only tested when ``'toneMarkType'`` is
        assumed to be set to ``'numbers'``.

        :type readingString: str
        :param readingString: Pinyin string
        :type includeToneless: bool
        :param includeToneless: if set to ``True`` option ``'toneMarkType'`` can
            take on value ``'none'``, but by default (i.e. set to ``False``) is
            covered by tone mark type set to ``'numbers'``.
        :rtype: dict
        :return: dictionary of basic keyword settings
        """
        readingStr = unicodedata.normalize("NFC", unicode(readingString))

        diacriticVowels = []
        for vowel in cls.TONEMARK_VOWELS:
            for tone in cls.DIACRITICS_LIST:
                for mark in cls.DIACRITICS_LIST[tone]:
                    diacriticVowels.append(
                        unicodedata.normalize("NFC", vowel + mark))
        # split regex for all dialect forms
        entities = re.findall(u'((?:' + '|'.join(diacriticVowels) \
            + '|'.join(cls.Y_VOWEL_LIST) + u'|[a-uw-zêŋẑĉŝ])+[12345]?)',
            readingStr, re.IGNORECASE | re.UNICODE)

        # guess one of main dialects: tone mark type
        diacriticEntityCount = 0
        numberEntityCount = 0
        for entity in entities:
            # take entity (which can be several connected syllables) and check
            if entity[-1] in '12345':
                numberEntityCount = numberEntityCount + 1
            else:
                for vowel in diacriticVowels:
                    # don't count ê which is a possible form of bad diacritics
                    if vowel in entity.lower() and vowel != u'ê':
                        diacriticEntityCount = diacriticEntityCount + 1
                        break
        # compare statistics
        if includeToneless \
            and (1.0 * max(diacriticEntityCount, numberEntityCount) \
                / len(entities)) < 0.1:
            # less than 1/10 units carry some possible tone mark, so decide
            #   for toneless
            toneMarkType = 'none'
        else:
            if diacriticEntityCount > numberEntityCount:
                toneMarkType = 'diacritics'
            else:
                # even if equal prefer numbers, as in case of missing tone marks
                #   we rather asume tone 'none' which is possible here
                toneMarkType = 'numbers'

        # guess diacritic marks
        diacritics = list(cls.getDefaultOptions()['pinyinDiacritics'])
        if toneMarkType == 'diacritics':
            readingStrNFD = unicodedata.normalize("NFD", readingStr)
            # remove non-tonal diacritics
            readingStrNFDClear = re.compile(ur'([ezcs]\u0302|u\u0308)',
                re.IGNORECASE | re.UNICODE).sub('', readingStrNFD)

            for tone in cls.DIACRITICS_LIST:
                if diacritics[tone-1] not in readingStrNFDClear:
                    for mark in cls.DIACRITICS_LIST[tone]:
                        if mark in readingStrNFDClear:
                            diacritics[tone-1] = mark
                            break

        # guess ü vowel
        if toneMarkType == 'diacritics':
            yVowel = u'ü'
        else:
            for vowel in cls.Y_VOWEL_LIST:
                if vowel in readingStr.lower():
                    yVowel = vowel
                    break
            else:
                yVowel = u'ü'

        # guess apostrophe
        for apostrophe in cls.APOSTROPHE_LIST:
            if apostrophe in readingStr:
                pinyinApostrophe = apostrophe
                break
        else:
            pinyinApostrophe = "'"

        # guess Erhua, if r found surrounded by non-alpha assume twoSyllables
        erhua = 'twoSyllables'
        if toneMarkType == 'numbers':
            lastIndex = 0
            while lastIndex != -1:
                # find all instances of 'r' with following non-alpha
                lastIndex = readingStr.lower().find('r', lastIndex+1)
                if lastIndex > 1:
                    if len(readingStr) > lastIndex + 1 \
                        and not readingStr[lastIndex + 1].isalpha():
                        if not readingStr[lastIndex - 1].isalpha():
                            # found a preceding number that should be a tone
                            #   mark for another syllable, thus r5 is isolated
                            break
                        else:
                            # found trailing r
                            erhua = 'oneSyllable'

        # guess shortenedLetters
        for char in u'ŋẑĉŝ':
            if char in readingStr.lower():
                shortenedLetters = True
                break
        else:
            shortenedLetters = False

        return {'toneMarkType': toneMarkType,
            'pinyinDiacritics': tuple(diacritics), 'yVowel': yVowel,
            'pinyinApostrophe': pinyinApostrophe, 'erhua': erhua,
            'shortenedLetters': shortenedLetters}

    @cachedmethod
    def getReadingCharacters(self):
        characters = set(string.ascii_lowercase + u'üêŋẑĉŝ')
        characters.update(list(self.yVowel))
        # NFD combining diacritics
        for char in list(u'üêŋẑĉŝ') + list(self.yVowel):
            characters.update(unicodedata.normalize('NFD', unicode(char)))
        # add NFC vowels, strip off combining diacritical marks
        for char in self._getDiacriticVowels():
            characters.update(list(char))
        # tones
        characters.update(['1', '2', '3', '4', '5'])
        for diacritic in self.pinyinDiacritics:
            # make sure that combinations of two and more diacritics work
            characters.update(list(diacritic))
        return frozenset(characters)

    @cachedmethod
    def getTones(self):
        tones = range(1, 6)
        if self.toneMarkType == 'none' \
            or (self.missingToneMark == 'noinfo' \
                and self.toneMarkType == 'numbers'):
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string. Applies an
        apostrophe between syllables if needed using default implementation
        :meth:`~PinyinOperator.aeoApostropheRule`.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :rtype: str
        :return: composed entities
        """
        readingCharacters = self.getReadingCharacters()

        newReadingEntities = []
        precedingEntity = None

        for entity in readingEntities:
            if self.pinyinApostropheFunction(self, precedingEntity, entity):
                newReadingEntities.append(self.pinyinApostrophe)
            elif precedingEntity and entity:
                # check if composition won't combine reading and non-reading e.
                precedingEntityIsReading = self.isReadingEntity(precedingEntity)
                entityIsReading = self.isReadingEntity(entity)
                # allow tone digits to separate
                if precedingEntity[-1] not in ['1', '2', '3', '4', '5'] \
                    and ((precedingEntityIsReading and not entityIsReading \
                        and entity[0] in readingCharacters) \
                    or (not precedingEntityIsReading and entityIsReading \
                        and precedingEntity[-1] in readingCharacters)):

                    if precedingEntityIsReading:
                        offendingEntity = entity
                    else:
                        offendingEntity = precedingEntity
                    raise CompositionError(
                        "Unable to delimit non-reading entity '%s'" \
                            % offendingEntity)

            newReadingEntities.append(entity)
            precedingEntity = entity
        return ''.join(newReadingEntities)

    def removeApostrophes(self, readingEntities):
        """
        Removes apostrophes between two syllables for a given decomposition.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :rtype: list of str
        :return: the given entity list without separating apostrophes
        """
        if len(readingEntities) == 0:
            return []
        elif len(readingEntities) > 2 \
            and readingEntities[1] == self.pinyinApostrophe \
            and self.isReadingEntity(readingEntities[0]) \
            and self.isReadingEntity(readingEntities[2]):
            # apostrophe on pos #1 preceded and followed by a syllable
            newReadingEntities = [readingEntities[0]]
            newReadingEntities.extend(self.removeApostrophes(
                readingEntities[2:]))
            return newReadingEntities
        else:
            newReadingEntities = [readingEntities[0]]
            newReadingEntities.extend(self.removeApostrophes(
                readingEntities[1:]))
            return newReadingEntities

    @staticmethod
    def aeoApostropheRule(operatorInst, precedingEntity, followingEntity):
        """
        Checks if the given entities need to be separated by an apostrophe.

        Returns true for syllables starting with one of the three vowels *a*,
        *e*, *o* having a preceding syllable. Additionally forms *n* and
        *ng* are separated from preceding syllables. Furthermore corner case
        *e'r* will handled to distinguish from *er*.

        This function serves as the default apostrophe rule.

        :type operatorInst: instance
        :param operatorInst: instance of the Pinyin operator
        :type precedingEntity: str
        :param precedingEntity: the preceding syllable or any other content
        :type followingEntity: str
        :param followingEntity: the following syllable or any other content
        :rtype: bool
        :return: true if the syllables need to be separated, false otherwise
        """
        # if both following entities are syllables they have to be separated if
        # the following syllable's first character is one of the vowels a, e, o,
        # or the syllable is n or ng
        if precedingEntity and operatorInst.isReadingEntity(precedingEntity) \
            and operatorInst.isReadingEntity(followingEntity):

            plainSyllable, _ = operatorInst.splitEntityTone(followingEntity)

            # take care of corner case Erhua form e'r, that needs to be
            #   distinguished from er
            if plainSyllable.lower() == 'r':
                precedingPlainSyllable, _ = operatorInst.splitEntityTone(
                    precedingEntity)
                return precedingPlainSyllable.lower() == 'e'

            return plainSyllable[0].lower() in ['a', 'e', 'o'] \
                or plainSyllable.lower() in ['n', 'ng', 'nr', 'ngr', u'ê', u'ŋ',
                    u'ŋr']
        return False

    def isStrictDecomposition(self, readingEntities):
        """
        Checks if the given decomposition follows the Pinyin format
        strictly for unambiguous decomposition: syllables have to be preceded by
        an apostrophe if the decomposition would be ambiguous otherwise.

        The function stored given as option ``'pinyinApostropheFunction'`` is
        used to check if a apostrophe should have been placed.

        :type readingEntities: list of str
        :param readingEntities: decomposed reading string
        :rtype: bool
        :return: true if decomposition is strict, false otherwise
        """
        precedingEntity = None

        for entity in readingEntities:
            if self.isReadingEntity(entity):
                # Pinyin syllable
                if self.pinyinApostropheFunction(self, precedingEntity, entity):
                    return False

                precedingEntity = entity
            else:
                # other content, treat next entity as first (start)
                precedingEntity = None

        return True

    @cachedproperty
    def _plainSubstringTable(self):
        """Returns a set of plain entity substrings."""
        entities = self.getPlainReadingEntities()

        substrings = []
        for syllable in entities:
            for i in range(len(syllable)):
                substrings.append(syllable[0:i+1])
        return frozenset(substrings)

    def _hasEntitySubstring(self, readingString):
        # reimplement to allow for misplaced tone marks
        def stripDiacritic(strng):
            """Strip one tonal diacritic mark off string."""
            strng = unicodedata.normalize("NFD", unicode(strng))
            strng = self._toneMarkRegex.sub(r'\1', strng, 1)

            return unicodedata.normalize("NFC", unicode(strng))

        if self.toneMarkType == 'diacritics':
            # We remove diacritics, so plain entities suffice
            return stripDiacritic(readingString) in self._plainSubstringTable
        else:
            return super(PinyinOperator, self)._hasEntitySubstring(
                readingString)

    def getTonalEntity(self, plainEntity, tone):
        # get normalised Unicode string, e.g. ``'e\u0302'`` to ``'ê'``
        plainEntity = unicodedata.normalize("NFC", unicode(plainEntity))

        if tone != None:
            tone = int(tone)
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': %s"
                    % (plainEntity, unicode(tone)))

        if self.toneMarkType == 'none':
            return plainEntity

        elif self.toneMarkType == 'numbers':
            if tone == None or (tone == 5 and self.missingToneMark == 'fifth'):
                return plainEntity
            else:
                return plainEntity + str(tone)

        elif self.toneMarkType == 'diacritics':
            # split syllable into onset, nucleus and coda, handle nasal and ê
            #   syllables independently
            if plainEntity.lower() in ['n', 'ng', 'm', 'r', u'ê', 'nr', 'ngr',
                'mr', u'êr', u'ŋ', u'ŋr']:
                onset, nucleus, coda = ('', plainEntity[0], plainEntity[1:])
            elif plainEntity.lower() in ['hm', 'hng', 'hmr', 'hngr', u'hŋ',
                u'hŋr']:
                onset, nucleus, coda = (plainEntity[0], plainEntity[1],
                    plainEntity[2:])
            else:
                matchObj = self.PINYIN_SOUND_REGEX.match(plainEntity)
                onset, nucleus, coda = matchObj.group(1, 2, 3)
            if not nucleus:
                raise InvalidEntityError("no nucleus found for '%s'"
                    % plainEntity)
            # place tone mark
            tonalNucleus = self._placeNucleusToneMark(nucleus, tone)
            return onset + tonalNucleus + coda

    def _placeNucleusToneMark(self, nucleus, tone):
        """
        Places a tone mark on the given syllable nucleus according to the rules
        of the Pinyin standard.

        :type nucleus: str
        :param nucleus: syllable nucleus
        :type tone: int
        :param tone: tone index (starting with 1)
        :rtype: str
        :return: nucleus with appropriate tone
        """
        # only tone mark to place for tones 0 - 3
        if tone != 5:
            if len(nucleus) == 1:
                # only one character in nucleus, place tone mark there
                tonalNucleus = nucleus + self._tonemarkMapReverse[tone]
            elif nucleus[0].lower() in ('a', 'e', 'o'):
                # if several vowels place on a, e, o...
                tonalNucleus = nucleus[0] + self._tonemarkMapReverse[tone] \
                    + nucleus[1:]
            else:
                # ...otherwise on second vowel (see Pinyin rules)
                tonalNucleus = nucleus[0] + nucleus[1] \
                    + self._tonemarkMapReverse[tone] + nucleus[2:]
        else:
            tonalNucleus = nucleus
        # get normalised Unicode string,
        return unicodedata.normalize("NFC", tonalNucleus)

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the
        entity's tone index.

        The plain entity returned will always be in Unicode's
        *Normalization Form C* (NFC, see http://www.unicode.org/reports/tr15/).

        :type entity: str
        :param entity: entity with tonal information
        :rtype: tuple
        :return: plain entity without tone mark and entity's tone index
            (starting with 1)
        """
        # get decomposed Unicode string, e.g. ``'ū'`` to ``'u\u0304'``
        entity = unicodedata.normalize("NFD", unicode(entity))
        if self.toneMarkType == 'none':
            plainEntity = entity
            tone = None

        elif self.toneMarkType == 'numbers':
            matchObj = re.search(u"[12345]$", entity)
            if matchObj:
                plainEntity = entity[0:len(entity)-1]
                tone = int(matchObj.group(0))
            else:
                if self.missingToneMark == 'fifth':
                    plainEntity = entity
                    tone = 5
                elif self.missingToneMark == 'ignore':
                    raise InvalidEntityError(
                        "No tone information given for '%s'" % entity)
                else:
                    plainEntity = entity
                    tone = None

        elif self.toneMarkType == 'diacritics':
            # find character with tone marker
            matchObj = self._toneMarkRegex.search(entity)
            if matchObj:
                diacriticalMark = matchObj.group(2)
                tone = self._tonemarkMap[diacriticalMark]
                # strip off diacritical mark, don't overwrite shortendLetters
                plainEntity = self._toneMarkRegex.sub(r'\1', entity, 1)
            else:
                # fifth tone doesn't have any marker
                plainEntity = entity
                tone = 5
            # check if placement of dicritic is correct
            if self.strictDiacriticPlacement:
                nfcEntity = unicodedata.normalize("NFC", unicode(entity))
                if nfcEntity != self.getTonalEntity(plainEntity, tone):
                    raise InvalidEntityError("Wrong placement of diacritic " \
                        + "for '%s' while strict checking enforced" % entity)
        # compose Unicode string (used for ê) and return with tone
        return unicodedata.normalize("NFC", plainEntity), tone

    @cachedmethod
    def getPlainReadingEntities(self):
        u"""
        Gets the list of plain entities supported by this reading. Different to
        :meth:`~PinyinOperator.getReadingEntities` the entities will carry no
        tone mark.

        Depending on the type of Erhua support either additional syllables with
        an ending -r are added, or a single *r* is included. The user specified
        character for vowel *ü* will be used.

        :rtype: set of str
        :return: set of supported syllables

        .. todo::
            * Fix: don't raise an ValueError here (delayed), raise an Exception
              directly in the constructor. See also WadeGilesOperator.
        """
        # set used syllables
        plainSyllables = set(self.db.selectScalars(
            select([self.db.tables['PinyinSyllables'].c.Pinyin])))
        if u'\u0302' in self.pinyinDiacritics:
            # if circumflex is included, disable vowel ê
            plainSyllables.remove(u'ê')
        # support for Erhua if needed
        if self.erhua == 'twoSyllables':
            # single 'r' for patterns like 'tóur'
            plainSyllables.add('r')
        elif self.erhua == 'oneSyllable':
            # add a -r form for all syllables except e and er
            for syllable in plainSyllables.copy():
                if syllable not in ['e', 'er']:
                    plainSyllables.add(syllable + 'r')

        # change forms for alternative ü
        if self.yVowel != u'ü':
            translatedSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace(u'ü', self.yVowel)
                if syllable in translatedSyllables:
                    # check if through conversion we collide with an already
                    #   existing syllable
                    raise ValueError("syllable '" + syllable \
                        + "' included more than once, " \
                        + u"probably bad substitute for 'ü'")
                translatedSyllables.add(syllable)

            plainSyllables = translatedSyllables

        if self.shortenedLetters:
            initialDict = {'zh': u'ẑ', 'ch': u'ĉ', 'sh': u'ŝ'}
            shortendSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace('ng', u'ŋ')
                if syllable[:2] in initialDict:
                    shortendSyllables.add(syllable.replace(syllable[:2],
                        initialDict[syllable[:2]]))
                else:
                    shortendSyllables.add(syllable)

            plainSyllables = shortendSyllables

        return frozenset(plainSyllables)

    @cachedmethod
    def getReadingEntities(self):
        # overwrite default implementation to specify a special tone mark for
        #   syllable 'r' used to support two syllable Erhua.
        syllables = self.getPlainReadingEntities()
        syllableSet = set()
        allTones = self.getTones()
        for syllable in syllables:
            if syllable == 'r':
                # r is included to support Erhua and is marked with the
                #   fifth tone as it is not pronounced separetly.
                tones = [5]
                if None in allTones:
                    tones.append(None)
            else:
                tones = allTones
            # check if we accept syllables without tone mark
            for tone in tones:
                syllableSet.add(self.getTonalEntity(syllable, tone))
        return frozenset(syllableSet)

    def isReadingEntity(self, entity):
        # overwrite to check tone of entity 'r' (Erhua)
        try:
            plainEntity, tone = self.splitEntityTone(entity)
            if plainEntity.lower() == 'r' and tone not in [5, None]:
                # shallow test
                return False
            return self.isPlainReadingEntity(plainEntity) \
                and tone in self.getTones()
        except InvalidEntityError:
            return False

    @cachedmethod
    def getFormattingEntities(self):
        return frozenset([self.pinyinApostrophe])

    def convertPlainEntity(self, plainEntity, targetOptions=None):
        """
        Converts the alternative syllable representation from the current
        dialect to the given target, or by default to the standard
        representation. Erhua forms will not be converted.

        Use the :class:`~cjklib.reading.converter.PinyinDialectConverter` for
        conversions in general.

        :type plainEntity: str
        :param plainEntity: plain syllable in the current reading
        :type targetOptions: dict
        :param targetOptions: target reading options
        :rtype: str
        :return: converted entity
        """
        initialShortendDict = {'zh': u'ẑ', 'ch': u'ĉ', 'sh': u'ŝ'}
        reverseShortendDict = {u'ẑ': 'zh', u'ĉ': 'ch', u'ŝ': 'sh'}

        targetOptions = targetOptions or {}
        defaultTargetOptions = PinyinOperator.getDefaultOptions()
        # convert shortenedLetters
        toShortenedLetters = targetOptions.get('shortenedLetters',
            defaultTargetOptions['shortenedLetters'])
        if self.shortenedLetters and not toShortenedLetters:

            plainEntity = plainEntity.replace(u'ŋ', 'ng')
            # upper- / titlecase
            if plainEntity.istitle():
                # only for full forms 'ng', 'ngr'
                plainEntity = plainEntity.replace(u'Ŋ', 'Ng')
            else:
                plainEntity = plainEntity.replace(u'Ŋ', 'NG')
            if plainEntity[0].lower() in reverseShortendDict:
                shortend = plainEntity[0].lower()
                full = reverseShortendDict[shortend]
                plainEntity = plainEntity.replace(shortend, full)
                # upper- vs. titlecase
                if plainEntity.isupper():
                    plainEntity = plainEntity.replace(
                        shortend.upper(), full.upper())
                elif plainEntity.istitle():
                    plainEntity = plainEntity.replace(
                        shortend.upper(), full.title())

        elif not self.shortenedLetters and toShortenedLetters:

            # final ng
            matchObj = re.search('(?i)ng', plainEntity)
            if matchObj:
                ngForm = matchObj.group(0)
                shortend = u'ŋ'
                # letter case
                if plainEntity.isupper() \
                    or (plainEntity.istitle() \
                        and plainEntity.startswith(ngForm)):
                    shortend = shortend.upper()

                plainEntity = plainEntity.replace(ngForm, shortend)

            # initials zh, ch, sh
            matchObj = re.match('(?i)[zcs]h', plainEntity)
            if matchObj:
                form = matchObj.group(0)
                shortend = initialShortendDict[form.lower()]
                # letter case
                if plainEntity.isupper() or plainEntity.istitle():
                    shortend = shortend.upper()

                plainEntity = plainEntity.replace(form, shortend)

        # check for special vowel for ü on input
        toYVowel = targetOptions.get('yVowel', defaultTargetOptions['yVowel'])
        if self.yVowel != toYVowel:
            plainEntity = plainEntity.replace(self.yVowel, toYVowel)\
                .replace(self.yVowel.upper(), toYVowel.upper())

        return plainEntity

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        Pinyin can't be separated into onset and rhyme clearly within its own
        system. There are syllables with same finals written differently (e.g.
        *wei* and *dui* both ending in a final that can be described by
        *uei*) and reduction of vowels (same example: *dui* which is
        pronounced with vowels *uei*). This method will use three forms not
        found as substrings in Pinyin (*uei*, *uen* and *iou*) and
        substitutes (pseudo) initials *w* and *y* with its vowel equivalents.

        Furthermore final *i* will be distinguished in three forms given by
        the following three examples: *yi*, *zhi* and *zi* to express
        phonological difference.

        Returned strings will be lowercase.

        :type plainSyllable: str
        :param plainSyllable: syllable without tone marks
        :rtype: tuple of str
        :return: tuple of entity onset and rhyme
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: for entity *r* when Erhua is handled as
            separate entity.
        """
        erhuaForm = False
        standardPlainSyllable = plainSyllable.lower()
        if self.erhua == 'oneSyllable' \
            and standardPlainSyllable.endswith('r') \
            and standardPlainSyllable != 'er':

            standardPlainSyllable = standardPlainSyllable[:-1]
            erhuaForm = True

        elif plainSyllable.lower() == 'r' \
            and self.erhua == 'twoSyllables':

            raise UnsupportedError("Not supported for '%s'" % plainSyllable)

        standardPlainSyllable = self.convertPlainEntity(standardPlainSyllable)

        table = self.db.tables['PinyinInitialFinal']
        entry = self.db.selectRow(
            select([table.c.PinyinInitial, table.c.PinyinFinal],
                table.c.Pinyin == standardPlainSyllable))
        if not entry:
            raise InvalidEntityError("'%s' not a valid plain Pinyin syllable'"
                % plainSyllable)

        if erhuaForm:
            return (entry[0], entry[1] + 'r')
        else:
            return (entry[0], entry[1])


class WadeGilesOperator(TonalRomanisationOperator):
    u"""
    Provides an operator for the Mandarin *Wade-Giles* romanisation.

    .. todo::
        * Lang: Asterisk (\*) marking the entering tone (入聲): e.g. *chio²\**
          and *chüeh²\** for 覺 used by Giles (A Chinese-English Dictionary,
          second edition, 1912).
    """
    READING_NAME = 'WadeGiles'

    DB_ASPIRATION_APOSTROPHE = u'’'
    """Apostrophe used by Wade-Giles syllable data in database."""

    TO_SUPERSCRIPT = {1: u'¹', 2: u'²', 3: u'³', 4: u'⁴', 5: u'⁵', 0: u'⁰'}
    """Mapping of tone numbers to superscript numbers."""
    FROM_SUPERSCRIPT = dict([(value, key) \
        for key, value in TO_SUPERSCRIPT.iteritems()])
    """Mapping of superscript numbers to tone numbers."""
    del value
    del key

    APOSTROPHE_LIST = ["'", u'’', u'´', u'‘', u'`', u'ʼ', u'ˈ', u'′', u'ʻ']
    """List of apostrophes used in guessing routine."""

    ZERO_FINAL_LIST = [u'ŭ', u'ǔ', u'u']
    """
    List of characters for zero final used in guessing routine.
    Except 'u' no other values are allowed that intersect with WG vowels as they
    can cause ambiguous forms.
    """

    DIACRICTIC_E_LIST = [u'ê', u'ě', u'e']
    """
    List of characters for diacritic e used in guessing routine.
    Except 'e' no other values are allowed that intersect with WG vowels as they
    can cause ambiguous forms.
    """

    UMLAUT_U_LIST = [u'ü', u'u']
    """
    List of characters used for u-umlaut in guessing routine.
    Except 'u' no other values are allowed that intersect with WG vowels. Vowel
    'u' will generate ambiguous forms, so that the guessing routine has to take
    care of only chosing this on forms that have no "natural" 'u' counterpart.
    For all other vowels this is not guaranteed, so they are not allowed as
    values.
    """

    ALLOWED_VOWEL_SUBST = {'diacriticE': 'e', 'zeroFinal': 'u', 'umlautU': 'u'}
    """
    Regular Wade-Giles-vowels that the given options can be substituted with.
    Other regular vowels are not allowed for substitution as of ambiguity.
    """

    syllableRegex = re.compile(ur'(' \
        + u'(?:(?:ch|hs|sh|ts|tz|ss|sz|[pmftnlkhjyw])' \
        + u'(?:' + '|'.join([re.escape(a) for a in APOSTROPHE_LIST]) + ')?)?'
        + u'(?:' + '|'.join([re.escape(a) for a \
            in (ZERO_FINAL_LIST + DIACRICTIC_E_LIST + UMLAUT_U_LIST)]) \
        + u'|[aeiou])+' \
        + u'(?:ng|n|rh|h)?[012345⁰¹²³⁴⁵]?)', re.IGNORECASE | re.UNICODE)
    """
    Regex to split a string into several syllables in a crude way.
    It consists of:

    - Initial consonants,
    - apostrophe for aspiration,
    - vowels,
    - final consonants n/ng and rh (for êrh), h (for -ih, -üeh),
    - tone numbers.
    """
    del a

    def __init__(self, **options):
        u"""
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~WadeGilesOperator.segment()`) and thus decomposition (using
            :meth:`~WadeGilesOperator.decompose()`) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If ``False`` the
            aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will be
            supported.
        :keyword wadeGilesApostrophe: an alternate apostrophe that is taken
            instead of the default one.
        :keyword toneMarkType: if set to ``'numbers'`` appended numbers from
            1 to 5 will be used to mark tones, if set to
            ``'superscriptNumbers'`` appended superscript numbers from
            1 to 5 will be used to mark tones, if set to ``'none'`` no
            tone marks will be used and no tonal information will be
            supplied at all.
        :keyword neutralToneMark: if set to ``'none'`` no tone mark is set to
            indicate the fifth tone (*qingsheng*, e.g. ``'chih¹tao'``, if set
            to ``'zero'`` the number zero is used, e.g. ``'chih¹tao⁰'`` and
            if set to ``'five'`` the number five is used, e.g. ``'chih¹-tao⁵'``.
        :keyword missingToneMark: if set to ``'noinfo'``, no tone information
            will be deduced when no tone mark is found (takes on
            value ``None``), if set to ``'ignore'`` this entity will not
            be valid and for segmentation the behaviour defined by
            ``'strictSegmentation'`` will take affect.
            This options only has effect for tone mark type ``'numbers'``
            and ``'superscriptNumbers'``. This option is only valid
            if ``'neutralToneMark'`` is set to something other than ``'none'``.
        :keyword diacriticE: character used instead of *ê*. ``'e'`` is a
            possible alternative, no ambiguities arise.
        :keyword zeroFinal: character used instead of *ŭ*. ``'u'`` is a
            possible alternative, no ambiguities arise.
        :keyword umlautU: character used instead of *ü*. ``'u'`` is a
            allowed, but ambiguities are possible.
        :keyword useInitialSz: if set to ``True`` syllable form *szŭ* is used
            instead of the standard *ssŭ*.

        .. todo::
            * Impl: Raise value error on invalid values for diacriticE,
              zeroFinal, umlautU
        """
        super(WadeGilesOperator, self).__init__(**options)

        # check tone mark for neutral tone
        if self.neutralToneMark not in ['none', 'zero', 'five']:
            raise ValueError("Invalid option %s for keyword 'neutralToneMark'"
                % repr(self.neutralToneMark))

        # check which tone marks to use
        if self.toneMarkType not in ['numbers', 'superscriptNumbers', 'none']:
            raise ValueError("Invalid option %s for keyword 'toneMarkType'"
                % repr(self.toneMarkType))

        # check behaviour on missing tone info
        if self.missingToneMark not in ['noinfo', 'ignore']:
            raise ValueError("Invalid option %s for keyword 'missingToneMark'"
                % repr(self.missingToneMark))

        self._readingEntityRegex = re.compile(u"((?:" \
            + re.escape(self.wadeGilesApostrophe) \
            + "|" + re.escape(self.diacriticE) \
            + "|" + re.escape(self.zeroFinal) \
            + "|" + re.escape(self.umlautU) \
            + u"|[a-züêŭ])+[012345⁰¹²³⁴⁵]?)", re.IGNORECASE | re.UNICODE)

    @classmethod
    def getDefaultOptions(cls):
        options = super(WadeGilesOperator, cls).getDefaultOptions()
        options.update({
            'diacriticE': u'ê', 'zeroFinal': u'ŭ', 'umlautU': u'ü',
            'useInitialSz': False, 'wadeGilesApostrophe': u'’',
            'neutralToneMark': 'none', 'toneMarkType': 'superscriptNumbers',
            'missingToneMark': u'noinfo'})

        return options

    @classmethod
    def guessReadingDialect(cls, readingString):
        u"""
        Takes a string written in Wade-Giles and guesses the reading dialect.

        The following options are tested:

        - ``'toneMarkType'``
        - ``'wadeGilesApostrophe'``
        - ``'neutralToneMark'``
        - ``'diacriticE'``
        - ``'zeroFinal'``
        - ``'umlautU'``
        - ``'useInitialSz'``

        :type readingString: str
        :param readingString: Wade-Giles string
        :rtype: dict
        :return: dictionary of basic keyword settings
        """
        # split regex for all dialect forms
        readingString = readingString.lower()
        entities = cls.syllableRegex.findall(
            unicodedata.normalize('NFC', unicode(readingString)))

        # guess vowels and initial sz-, prefer defaults
        useInitialSz = False
        zeroFinal = None
        diacriticE = None
        umlautU = None

        if u'ŭ' in readingString:
            zeroFinal = u'ŭ'
        if u'ê' in readingString:
            diacriticE = u'ê'
        if u'ü' in readingString:
            umlautU = u'ü'

        for entity in entities:
            # initial sz-
            if entity.startswith('sz'):
                useInitialSz = True
            # ŭ
            if not zeroFinal:
                matchObj = re.compile('(?:tz|ss|sz)' \
                    + u'(?:' + '|'.join([re.escape(a) for a \
                        in cls.APOSTROPHE_LIST]) + ')?' \
                    + u'(' + '|'.join([re.escape(a) for a \
                        in cls.ZERO_FINAL_LIST]) + ')',
                    re.IGNORECASE | re.UNICODE).match(entity)
                if matchObj:
                    zeroFinal = matchObj.group(1)

            # ê
            if not diacriticE:
                matchObj = re.compile(u'(?:(?:ch|hs|sh|ts|[pmftnlkhjyw])' \
                    + u'(?:' + '|'.join([re.escape(a) for a \
                        in cls.APOSTROPHE_LIST]) + ')?)?'
                    + u'(' + '|'.join([re.escape(a) for a \
                        in cls.DIACRICTIC_E_LIST]) + ')' \
                    + u'(?:ng|n|rh)?', re.IGNORECASE | re.UNICODE).match(entity)
                if matchObj:
                    diacriticE = matchObj.group(1)

            # ü
            if not umlautU:
                matchObj = re.compile(ur'(?:ch|hs|[nly])' \
                    + u'(?:' + '|'.join([re.escape(a) for a \
                        in cls.APOSTROPHE_LIST]) + ')?'
                    + u'(' + '|'.join([re.escape(a) for a \
                        in cls.UMLAUT_U_LIST]) + '|)[ae]?' \
                    + u'(?:n|h)?', re.IGNORECASE | re.UNICODE).match(entity)
                if matchObj:
                    # check for special case 'u'
                    if matchObj.group(1) == 'u':
                        s = matchObj.group(0)
                        # only let syllables overwrite default 'ü' if they
                        #   are not valid u-vowel forms, like *hsu (hsü)
                        if s.startswith('hs') \
                            or (s.startswith('y') and not s.startswith('yu')) \
                            or s.endswith(u'ueh') or s.endswith(u'uo'):
                            umlautU = matchObj.group(1)
                    else:
                        umlautU = matchObj.group(1)

        if not zeroFinal:
            zeroFinal = u'ŭ'
        if not diacriticE:
            diacriticE = u'ê'
        if not umlautU:
            umlautU = u'ü'

        # guess tone mark type
        superscriptEntityCount = 0
        digitEntityCount = 0
        for entity in entities:
            # take entity (which can be several connected syllables) and check
            if entity[-1] in '012345':
                digitEntityCount += 1
            elif entity[-1] in u'⁰¹²³⁴⁵':
                superscriptEntityCount += 1

        # compare statistics
        if digitEntityCount > superscriptEntityCount:
            toneMarkType = 'numbers'
        else:
            toneMarkType = 'superscriptNumbers'

        if digitEntityCount > 0 or superscriptEntityCount > 0:
            # guess neutral tone mark
            zeroToneMarkCount = 0
            fiveToneMarkCount = 0
            for entity in entities:
                if entity[-1] in u'⁰0':
                    zeroToneMarkCount += 1
                elif entity[-1] in u'⁵5':
                    fiveToneMarkCount += 1

            if zeroToneMarkCount > fiveToneMarkCount:
                neutralToneMark = 'zero'
            elif zeroToneMarkCount <= fiveToneMarkCount \
                and fiveToneMarkCount != 0:
                neutralToneMark = 'five'
            else:
                neutralToneMark = 'none'
        else:
            # no tones at all specified, so map tones to None and for that, we
            #   need to set the neutral tone mark to something diff than none.
            neutralToneMark = 'zero'

        # guess apostrophe
        for apostrophe in cls.APOSTROPHE_LIST:
            if apostrophe in readingString:
                wadeGilesApostrophe = apostrophe
                break
        else:
            wadeGilesApostrophe = u'’'

        return {'wadeGilesApostrophe': wadeGilesApostrophe,
            'toneMarkType': toneMarkType, 'neutralToneMark': neutralToneMark,
            'diacriticE': diacriticE, 'zeroFinal': zeroFinal,
            'umlautU': umlautU, 'useInitialSz': useInitialSz}

    @cachedmethod
    def getReadingCharacters(self):
        characters = set(string.ascii_lowercase + u'üêŭ')
        userSpecified = [self.diacriticE, self.zeroFinal, self.umlautU]
        characters.update(userSpecified)
        # NFD combining diacritics
        for char in list(u'üêŭ') + userSpecified:
            characters.update(unicodedata.normalize('NFD', unicode(char)))

        characters.update(['0', '1', '2', '3', '4', '5', u'⁰', u'¹', u'²', u'³',
            u'⁴', u'⁵'])
        characters.add(self.wadeGilesApostrophe)
        return frozenset(characters)

    @cachedmethod
    def getTones(self):
        tones = range(1, 6)
        if self.toneMarkType == 'none' \
            or (self.neutralToneMark != 'none' \
                and self.missingToneMark == 'noinfo'):
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string by applying a
        hyphen between syllables.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :rtype: str
        :return: composed entities
        """
        readingCharacters = self.getReadingCharacters()

        newReadingEntities = []
        precedingEntity = None

        for entity in readingEntities:
            if precedingEntity and entity:
                precedingEntityIsReading = self.isReadingEntity(precedingEntity)
                entityIsReading = self.isReadingEntity(entity)

                # check if we have to syllables
                if precedingEntityIsReading and entityIsReading:
                    # syllables are separated by a hyphen in the strict
                    #   interpretation of Wade-Giles
                    newReadingEntities.append("-")
                else:
                    # check if composition won't combine reading and non-reading
                    #   entities, allow tone digits to separate
                    #   also disallow cases like ['t', u'‘', 'ung1']
                    if precedingEntity[-1] not in ['1', '2', '3', '4', '5',
                            u'¹', u'²', u'³', u'⁴', u'⁵'] \
                        and ((precedingEntityIsReading and not entityIsReading \
                            and entity[0] in readingCharacters) \
                        or (not precedingEntityIsReading and entityIsReading \
                            and precedingEntity[-1] in readingCharacters) \
                        or (precedingEntity == self.wadeGilesApostrophe \
                            and entity[0] in readingCharacters \
                            and precedingEntity != entity)):

                        if precedingEntityIsReading:
                            offendingEntity = entity
                        else:
                            offendingEntity = precedingEntity
                        raise CompositionError(
                            "Unable to delimit non-reading entity '%s'" \
                                % offendingEntity)
            newReadingEntities.append(entity)
            precedingEntity = entity
        return ''.join(newReadingEntities)

    def removeHyphens(self, readingEntities):
        """
        Removes hyphens between two syllables for a given decomposition.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :rtype: list of str
        :return: the given entity list without separating hyphens
        """
        if len(readingEntities) == 0:
            return []
        elif len(readingEntities) > 2 and readingEntities[1] == "-" \
            and self.isReadingEntity(readingEntities[0]) \
            and self.isReadingEntity(readingEntities[2]):
            # hyphen on pos #1 preceded and followed by a syllable
            newReadingEntities = [readingEntities[0]]
            newReadingEntities.extend(self.removeHyphens(readingEntities[2:]))
            return newReadingEntities
        else:
            newReadingEntities = [readingEntities[0]]
            newReadingEntities.extend(self.removeHyphens(readingEntities[1:]))
            return newReadingEntities

    def getTonalEntity(self, plainEntity, tone):
        if tone != None:
            tone = int(tone)
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'" \
                    % (plainEntity, unicode(tone)))

        if self.toneMarkType == 'none':
            return plainEntity

        if tone == None or (tone == 5 and self.neutralToneMark == 'none'):
            return plainEntity
        else:
            if tone == 5 and self.neutralToneMark == 'zero':
                if self.toneMarkType == 'numbers':
                    toneMark = '0'
                else:
                    toneMark = self.TO_SUPERSCRIPT[0]
            elif self.toneMarkType == 'numbers':
                toneMark = str(tone)
            elif self.toneMarkType == 'superscriptNumbers':
                toneMark = self.TO_SUPERSCRIPT[tone]

            return plainEntity + toneMark

        assert False

    def splitEntityTone(self, entity):
        if self.toneMarkType == 'none':
            plainEntity = entity
            tone = None

        else:
            tone = None
            if self.toneMarkType == 'numbers':
                matchObj = re.search(u"[012345]$", entity)
                if matchObj:
                    tone = int(matchObj.group(0))
            elif self.toneMarkType == 'superscriptNumbers':
                matchObj = re.search(u"[⁰¹²³⁴⁵]$", entity)
                if matchObj:
                    tone = self.FROM_SUPERSCRIPT[matchObj.group(0)]

            # only allow 0 and 5 for the correct setting
            if self.neutralToneMark == 'none' and tone in [0, 5] \
                or self.neutralToneMark == 'zero' and tone == 5 \
                or self.neutralToneMark == 'five' and tone == 0:
                raise InvalidEntityError(
                    "Invalid tone information given for '%s'" % entity)

            # fix tone 0
            if tone == 0:
                tone = 5

            if tone:
                plainEntity = entity[0:len(entity)-1]
            else:
                if self.neutralToneMark == 'none':
                    plainEntity = entity
                    tone = 5
                elif self.missingToneMark == 'noinfo':
                    plainEntity = entity
                else:
                    raise InvalidEntityError(
                        "No tone information given for '%s'" % entity)

        return plainEntity, tone

    @cachedmethod
    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. Different to
        :meth:`~WadeGilesOperator.getReadingEntities` the entities will carry
        no tone mark.

        Syllables will use the user specified apostrophe to mark aspiration.

        :rtype: set of str
        :return: set of supported syllables
        """
        plainSyllables = set(self.db.selectScalars(
            select([self.db.tables['WadeGilesSyllables'].c.WadeGiles])))
        # use selected apostrophe
        if self.wadeGilesApostrophe != self.DB_ASPIRATION_APOSTROPHE:
            translatedSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace(self.DB_ASPIRATION_APOSTROPHE,
                    self.wadeGilesApostrophe)
                translatedSyllables.add(syllable)

            plainSyllables = translatedSyllables

        if self.diacriticE != u'ê':
            translatedSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace(u'ê', self.diacriticE)
                translatedSyllables.add(syllable)

            plainSyllables = translatedSyllables

        if self.zeroFinal != u'ŭ':
            translatedSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace(u'ŭ', self.zeroFinal)
                translatedSyllables.add(syllable)

            plainSyllables = translatedSyllables

        if self.useInitialSz:
            translatedSyllables = set()
            for syllable in plainSyllables:
                if syllable.startswith('ss'):
                    syllable = 'sz' + syllable[2:]
                translatedSyllables.add(syllable)

            plainSyllables = translatedSyllables

        if self.umlautU:
            translatedSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace(u'ü', self.umlautU)
                translatedSyllables.add(syllable)

            plainSyllables = translatedSyllables

        return frozenset(plainSyllables)

    def checkPlainEntity(self, plainEntity, option):
        u"""
        Checks if the given plain entity with is a form with lost diacritics or
        an ambiguous case.

        Examples:
        While form *\*erh* can be clearly traced to *êrh*, form *kuei* has
        no equivalent part with diacritcs. The former is a case of a ``'lost'``
        vowel, the second of a ``'strict'`` form. Syllable *ch’u* though is an
        ``'ambiguous'`` case as both *ch’u* and *ch’ü* are valid.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type option: str
        :param option: one option out of ``'diacriticE'``, ``'zeroFinal'``
            or ``'umlautU'``
        :rtype: str
        :return: ``'strict'`` if the given form is a strict Wade-Giles form with
            vowel u, ``'lost'`` if the given form is a mangled vowel form,
            ``'ambiguous'`` if two forms exist with vowels (i.e. u and ü) each
        :raise ValueError: if plain entity doesn't include the ambiguous vowel
            in question
        """
        plainEntity = unicodedata.normalize("NFC", unicode(plainEntity))
        if option not in self.ALLOWED_VOWEL_SUBST:
            raise ValueError("Invalid option '%s'" % option)

        vowel = self.ALLOWED_VOWEL_SUBST[option]
        originalVowel = self.getDefaultOptions()[option]

        if not plainEntity or not vowel in plainEntity.lower() \
            or not (self.isPlainReadingEntity(plainEntity.lower()) \
                or self.isPlainReadingEntity(
                    plainEntity.lower().replace(vowel, originalVowel))):
            raise ValueError(
                u"Not a plain reading entity or no vowel '%s': '%s'"
                    % (vowel, plainEntity))

        plainEntity = plainEntity.lower()
        # convert orthogonal options
        plainForm = plainEntity.replace(self.wadeGilesApostrophe,
            self.DB_ASPIRATION_APOSTROPHE)
        if plainForm.startswith('sz'):
            plainForm = 'ss' + plainForm[2:]

        table = self.db.tables['WadeGilesSyllables']
        result = self.db.selectScalars(select([table.c.WadeGiles],
                table.c.WadeGiles.in_([plainForm,
                    plainForm.replace(vowel, originalVowel)])))
        assert(len(result) <= 2)
        if len(result) == 2:
            return 'ambiguous'
        if not result or vowel in result[0]:
            return 'strict'
        else:
            return 'lost'

    @cachedmethod
    def getFormattingEntities(self):
        return frozenset(['-'])

    def convertPlainEntity(self, plainEntity, targetOptions=None):
        """
        Converts the alternative syllable representation from the current
        dialect to the given target, or by default to the standard
        representation.

        Use the :class:`~cjklib.reading.converter.WadeGilesDialectConverter`
        for conversions in general.

        :type plainEntity: str
        :param plainEntity: plain syllable in the current reading in lower
            case letters
        :type targetOptions: dict
        :param targetOptions: target reading options
        :rtype: str
        :return: converted entity
        :raise AmbiguousConversionError: if conversion is ambiguous.
        """
        convertedEntity = plainEntity.lower()
        targetOptions = targetOptions or {}
        defaultTargetOptions = WadeGilesOperator.getDefaultOptions()
        # forms with possibly lost diacritics
        for option in ['diacriticE', 'zeroFinal', 'umlautU']:
            fromSubstr = getattr(self, option)
            toSubstr = targetOptions.get(option, defaultTargetOptions[option])
            if fromSubstr != toSubstr:
                if fromSubstr == WadeGilesOperator.ALLOWED_VOWEL_SUBST[option] \
                    and fromSubstr in convertedEntity:
                    # A normally diacritical vowel lost its diacritic and now
                    #   overlaps with a standard vowel. We need to check the
                    #   full syllable to find out which case we have.
                    res = self.checkPlainEntity(convertedEntity, option)
                    # the 'u' for 'ü' can be ambiguous
                    if res == 'ambiguous':
                        lostForm = convertedEntity.replace(fromSubstr, toSubstr)
                        raise AmbiguousConversionError(
                            "conversion for entity '%s' is ambiguous: %s, %s" \
                                % (convertedEntity, convertedEntity, lostForm))
                    elif res == 'lost':
                        # this form lost its diacritics
                        convertedEntity = convertedEntity.replace(fromSubstr,
                            toSubstr)
                else:
                    # All other characters may not overlap, so we can safely
                    #  substitute
                    convertedEntity = convertedEntity.replace(fromSubstr,
                        toSubstr)

        # other special forms
        for option in ['wadeGilesApostrophe']:
            fromSubstr = getattr(self, option)
            toSubstr = targetOptions.get(option, defaultTargetOptions[option])
            if fromSubstr != toSubstr:
                convertedEntity = convertedEntity.replace(fromSubstr, toSubstr)

        # useInitialSz
        targetUseInitialSz = targetOptions.get('useInitialSz',
            defaultTargetOptions['useInitialSz'])
        if self.useInitialSz and convertedEntity.startswith('sz') \
            or not self.useInitialSz and convertedEntity.startswith('ss'):
            if targetUseInitialSz:
                initial = 'sz'
            else:
                initial = 'ss'
            convertedEntity = initial + convertedEntity[2:]

        # fix letter case
        if plainEntity.isupper():
            convertedEntity = convertedEntity.upper()
        elif istitlecase(plainEntity):
            convertedEntity = titlecase(convertedEntity)

        return convertedEntity

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        Semivowels *w-* and *y-* will be treated specially and an empty
        initial will be returned, while the final will be extended with vowel
        *i* or *u*.

        Old forms are not supported and will raise an
        :class:`~cjklib.exception.UnsupportedError`. For the dialect with
        missing diacritics on the *ü* an
        :class:`~cjklib.exception.UnsupportedError` is also raised, as it is
        unclear which syllable is meant.

        Returned strings will be lowercase.

        :type plainSyllable: str
        :param plainSyllable: syllable without tone marks
        :rtype: tuple of str
        :return: tuple of entity onset and rhyme
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the given entity is not supported
        """
        if not self.isPlainReadingEntity(plainSyllable):
            raise InvalidEntityError(
                "'%s' not a valid plain Wade-Giles syllable'" % plainSyllable)

        try:
            standardPlainSyllable = self.convertPlainEntity(
                plainSyllable.lower())
        except AmbiguousConversionError, e:
            raise UnsupportedError(*e.args)

        table = self.db.tables['WadeGilesInitialFinal']
        entry = self.db.selectRow(
            select([table.c.WadeGilesInitial, table.c.WadeGilesFinal],
                table.c.WadeGiles == standardPlainSyllable))
        if not entry:
            raise UnsupportedError("Not supported for '%s'" % plainSyllable)

        return (entry[0], entry[1])


class GROperator(TonalRomanisationOperator):
    u"""
    Provides an operator for the Mandarin *Gwoyeu Romatzyh* romanisation.

    .. todo::
        * Impl: Initial, medial, head, ending (ending1, ending2=l?)
        * Lang: Y.R. Chao uses particle and interjection ㄝ è. For more see
          'Mandarin Primer', Vocabulary and Index, pp. 301.
        * Impl: Implement Erhua forms as stated in W. Simon: A Beginner's
          Chinese-English Dictionary.
        * Impl: Implement a GRIPAConverter once IPA values are obtained for
          the PinyinIPAConverter. GRIPAConverter can work around missing Erhua
          conversion to Pinyin.
        * Lang: Special rule for non-Chinese names with initial r- to be
          transcribed with an r- cited by Ching-song Gene Hsiao: A Manual of
          Transcription Systems For Chinese, 中文拼音手册. Far Eastern
          Publications, Yale University, New Haven, Connecticut, 1985,
          ISBN 0-88710-141-0.
    """
    READING_NAME = 'GR'

    TONES = ['1stTone', '2ndTone', '3rdTone', '4thTone',
        '5thToneEtymological1st', '5thToneEtymological2nd',
        '5thToneEtymological3rd', '5thToneEtymological4th',
        '1stToneOptional5th', '2ndToneOptional5th', '3rdToneOptional5th',
        '4thToneOptional5th']

    SYLLABLE_STRUCTURE = re.compile(r"^((?:tz|ts|ch|sh|[bpmfdtnlsjrgkh])?)" \
        + "([aeiouy]+)((?:ngl|ng|n|l)?)$")
    """
    Regular expression describing the plain syllable structure in GR (C,V,C).
    """

    DB_RHOTACISED_FINAL_MAPPING = {1: 'GRFinal_T1', 2: 'GRFinal_T2',
        3: 'GRFinal_T3', 4: 'GRFinal_T4'}
    """Database fields for tonal Erlhuah syllables."""
    DB_RHOTACISED_FINAL_MAPPING_ZEROINITIAL = {1: 'GRFinal_T1', 2: 'GRFinal_T2',
        3: 'GRFinal_T3_ZEROINITIAL', 4: 'GRFinal_T4_ZEROINITIAL'}
    """Database fields for tonal Erlhuah syllables with i, u and iu medials."""

    DB_RHOTACISED_FINAL_APOSTROPHE = "'"
    """
    Default apostrophe used by GR syllable data in database for marking the
    longer and back vowel in rhotacised finals.
    """

    APOSTROPHE_LIST = ["'", u'’', u'´', u'‘', u'`', u'ʼ', u'ˈ', u'′', u'ʻ']
    """List of apostrophes used in guessing routine."""

    OPTIONAL_NEUTRAL_TONE_MARKERS = [u'˳', u'｡', u'￮', u'₀', u'ₒ']
    """
    List of allowed optional neutral tone markers:
    ˳ (U+02F3), ｡ (U+FF61), ￮ (U+FFEE), ₀ (U+2080), ₒ (U+2092)
    """

    def __init__(self, **options):
        u"""
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~GROperator.segment`) and thus decomposition (using
            :meth:`~GROperator.decompose`) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If ``False`` the
            aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will be
            supported.
        :keyword abbreviations: if set to ``True`` abbreviated spellings will be
            supported.
        :keyword grRhotacisedFinalApostrophe: an alternate apostrophe that is
            taken instead of the default one for marking a longer and back vowel
            in rhotacised finals.
        :keyword grSyllableSeparatorApostrophe: an alternate apostrophe that is
            taken instead of the default one for separating 0-initial syllables
            from preceding ones.
        :keyword optionalNeutralToneMarker: character to use for marking the
            optional neutral tone. Only values given in
            :attr:`~GROperator.OPTIONAL_NEUTRAL_TONE_MARKERS`
            are allowed.
        """
        super(GROperator, self).__init__(**options)

        if self.optionalNeutralToneMarker \
            not in self.OPTIONAL_NEUTRAL_TONE_MARKERS:
            raise ValueError(
                "Invalid value %s for keyword 'optionalNeutralToneMarker'"
                % repr(self.optionalNeutralToneMarker))

        self._readingEntityRegex = re.compile(u"( |" \
            + re.escape(self.grSyllableSeparatorApostrophe) \
            + u"|[\.%s]?(?:" % self.optionalNeutralToneMarker \
            + re.escape(self.grRhotacisedFinalApostrophe) + "|[A-Za-z])+)")

    @classmethod
    def getDefaultOptions(cls):
        options = super(GROperator, cls).getDefaultOptions()
        options.update({'abbreviations': True,
            'grRhotacisedFinalApostrophe': u"’",
            'grSyllableSeparatorApostrophe': u"’",
            'optionalNeutralToneMarker': u'˳'})

        return options

    @classmethod
    def guessReadingDialect(cls, readingString):
        u"""
        Takes a string written in GR and guesses the reading dialect.

        The options ``'grRhotacisedFinalApostrophe'`` and
        ``'grSyllableSeparatorApostrophe'`` are guessed. Both will be set to the
        same value which derives from a list of different apostrophes and
        similar characters.

        :type readingString: str
        :param readingString: GR string
        :rtype: dict
        :return: dictionary of basic keyword settings

        .. todo::
            * Impl: Both options ``'grRhotacisedFinalApostrophe'`` and
              ``'grSyllableSeparatorApostrophe'`` can be set independantly as
              the former one should only be found before an ``l`` and the
              latter mostly before vowels.
        """
        readingStr = unicodedata.normalize("NFC", unicode(readingString))

        # guess apostrophe
        apostrophe = "'"
        for a in cls.APOSTROPHE_LIST:
            if a in readingStr:
                apostrophe = a
                break

        # guess optional neutral tone marker
        for marker in cls.OPTIONAL_NEUTRAL_TONE_MARKERS:
            if marker in readingStr:
                optionalNeutralToneMarker = marker
                break
        else:
            optionalNeutralToneMarker \
                = cls.getDefaultOptions()['optionalNeutralToneMarker']

        return {'grRhotacisedFinalApostrophe': apostrophe,
            'grSyllableSeparatorApostrophe': apostrophe,
            'optionalNeutralToneMarker': optionalNeutralToneMarker}

    @cachedmethod
    def getReadingCharacters(self):
        characters = set(string.ascii_lowercase)
        characters.update([u'.', self.optionalNeutralToneMarker])
        characters.add(self.grRhotacisedFinalApostrophe)
        return frozenset(characters)

    @cachedmethod
    def getTones(self):
        return self.TONES[:]

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string. Applies an
        apostrophe between syllables if the second syllable has a zero-initial.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :rtype: str
        :return: composed entities
        """
        readingCharacters = self.getReadingCharacters()

        newReadingEntities = []
        precedingEntity = None

        for entity in readingEntities:
            if precedingEntity and entity:
                precedingEntityIsReading = self.isReadingEntity(precedingEntity)
                entityIsReading = self.isReadingEntity(entity)
                separator = self.grSyllableSeparatorApostrophe

                if precedingEntityIsReading and entityIsReading \
                    and (entity[0].lower() in ['a', 'e', 'i', 'o', 'u'] \
                        or (entity == 'g' and precedingEntity.endswith('n'))):
                    # "A Grammar of Spoken Chinese, p. xxii, p. 511"
                    newReadingEntities.append(separator)
                # check if composition won't combine reading and non-reading e.
                #   also disallow cases like ['jie', "'", 'l']
                elif ((precedingEntityIsReading and not entityIsReading \
                        and entity[0] in readingCharacters \
                        and entity != separator) \
                    or (not precedingEntityIsReading and entityIsReading \
                        and precedingEntity[-1] in readingCharacters \
                        and precedingEntity != separator) \
                    or (precedingEntity == self.grRhotacisedFinalApostrophe \
                        and not entityIsReading and entity[0] == 'l')):

                    if precedingEntityIsReading:
                        offendingEntity = entity
                    else:
                        offendingEntity = precedingEntity
                    raise CompositionError(
                        "Unable to delimit non-reading entity '%s'" \
                            % offendingEntity)

            newReadingEntities.append(entity)
            precedingEntity = entity

        return ''.join(newReadingEntities)

    def isStrictDecomposition(self, readingEntities):
        precedingEntity = None
        for entity in readingEntities:
            if precedingEntity and self.isReadingEntity(precedingEntity) \
                and self.isReadingEntity(entity):

                if entity[0].lower() in ['a', 'e', 'i', 'o', 'u']:
                    return False

            precedingEntity = entity

        return True

    def removeApostrophes(self, readingEntities):
        """
        Removes apostrophes between two syllables for a given decomposition.

        :type readingEntities: list of str
        :param readingEntities: list of basic syllables or other content
        :rtype: list of str
        :return: the given entity list without separating apostrophes
        """
        if len(readingEntities) == 0:
            return []
        elif len(readingEntities) > 2 \
            and readingEntities[1] == self.grSyllableSeparatorApostrophe \
            and self.isReadingEntity(readingEntities[0]) \
            and self.isReadingEntity(readingEntities[2]):
            # apostrophe on pos #1 preceded and followed by a syllable
            newReadingEntities = [readingEntities[0]]
            newReadingEntities.extend(self.removeApostrophes(
                readingEntities[2:]))
            return newReadingEntities
        else:
            newReadingEntities = [readingEntities[0]]
            newReadingEntities.extend(self.removeApostrophes(
                readingEntities[1:]))
            return newReadingEntities

    def getBaseTone(self, tone):
        """
        Gets the tone number of the tone or the etymological tone if it is a
        neutral or optional neutral tone.

        :type tone: str
        :param tone: tone
        :rtype: int
        :return: base tone number
        :raise InvalidEntityError: if an invalid tone is passed.
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given: '%s'"
                    % unicode(tone))

        if tone.startswith("5thToneEtymological"):
            return int(tone[-3])
        else:
            return int(tone[0])

    def splitPlainSyllableCVC(self, plainSyllable):
        """
        Splits the given plain syllable into consonants-vowels-consonants.

        :type plainSyllable: str
        :param plainSyllable: entity without tonal information
        :rtype: tuple of str
        :return: syllable CVC triple
        :raise InvalidEntityError: if the entity is invalid.
        """
        # split syllable into CVC parts
        matchObj = self.SYLLABLE_STRUCTURE.match(plainSyllable)
        if not matchObj:
            raise InvalidEntityError("Invalid entity given for '" \
                + plainSyllable + "'")

        c1, v, c2 = matchObj.groups()
        return c1, v, c2

    def getTonalEntity(self, plainEntity, tone):
        """
        Gets the entity with tone mark for the given plain entity and tone. This
        method only works for plain syllables that are not r-coloured (Erlhuah
        forms) as due to the depiction of Erlhuah in GR the information about
        the base syllable is lost and pronunciation partly varies between
        different syllables. Use :meth:`~GROperator.getRhotacisedTonalEntity`
        to get the tonal entity for a given etymological (base) syllable.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: str
        :return: entity with appropriate tone
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the given entity is an Erlhuah form.
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'"
                    % (plainEntity, unicode(tone)))

        # catch basic Erlhuah forms (don't raise for tonal 'el' even if invalid)
        if self.isRhotacisedReadingEntity(plainEntity):
            raise UnsupportedError("Not supported for '" + plainEntity + "'")

        # split syllable into CVC parts
        c1, v, c2 = self.splitPlainSyllableCVC(plainEntity.lower())
        # get tonal of etymological syllable
        baseTone = self.getBaseTone(tone)

        # Follow rules of "A Grammar of Spoken Chinese", pp. 29
        if baseTone == 1:
            if c1 not in ['m', 'n', 'l', 'r']:
                # Rule 1
                tonalEntity = plainEntity
            else:
                # Rule 7
                tonalEntity = c1 + 'h' + v + c2

        elif baseTone == 2:
            if c1 not in ['m', 'n', 'l', 'r']:
                # Rule 3
                if v == 'i' and not c2:
                    tonalEntity = c1 + 'y' + v
                elif v[0] == 'i':
                    # for rows 'i' and 'iu'
                    tonalEntity = c1 + 'y' + v[1:] + c2
                elif v == 'u' and not c2:
                    tonalEntity = c1 + 'w' + v
                elif v[0] == 'u':
                    tonalEntity = c1 + 'w' + v[1:] + c2
                else:
                    tonalEntity = c1 + v + 'r' + c2
            else:
                # Rule 7
                tonalEntity = plainEntity

        elif baseTone == 3:
            # Rule 4
            if len(v) == 1:
                tonalEntity = c1 + v + v + c2
            elif v in ['ie', 'ei']:
                tonalEntity = c1 + v[0] + 'e' + v[1] + c2
            elif v in ['ou', 'uo']:
                tonalEntity = c1 + v[0] + 'o' + v[1] + c2
            # Rule 5
            elif v[0] == 'i':
                # for rows 'i' and 'iu', and final i
                tonalEntity = c1 + 'e' + v[1:] + c2
            elif v[0] == 'u':
                tonalEntity = c1 + 'o' + v[1:] + c2
            elif ('i' in v) or ('u' in v):
                tonalEntity = c1 + v.replace('i', 'e', 1).replace('u', 'o', 1) \
                    + c2

            # Rule 8
            if not c1:
                if tonalEntity == 'iee':
                    tonalEntity = 'yee'
                elif tonalEntity == 'uoo':
                    tonalEntity = 'woo'
                elif v[0] == 'i':
                    # for rows 'i' and 'iu'
                    tonalEntity = 'y' + tonalEntity
                elif v[0] == 'u':
                    tonalEntity = 'w' + tonalEntity

        elif baseTone == 4:
            # Rule 6
            if not c2:
                if v in ['i', 'iu', 'u']:
                    tonalEntity = c1 + v + c2 + 'h'
                elif v.endswith('i'):
                    tonalEntity = c1 + v[:-1] + 'y' + c2
                elif v.endswith('u'):
                    tonalEntity = c1 + v[:-1] + 'w' + c2
                else:
                    tonalEntity = c1 + v + c2 + 'h'
            elif c2 == 'n':
                tonalEntity = c1 + v + 'nn'
            elif c2 == 'ng':
                tonalEntity = c1 + v + 'nq'
            elif c2 == 'l':
                tonalEntity = c1 + v + 'll'

            # Rule 9
            if not c1:
                if tonalEntity == 'ih':
                    tonalEntity = 'yih'
                elif tonalEntity == 'uh':
                    tonalEntity = 'wuh'
                elif tonalEntity == 'inn':
                    tonalEntity = 'yinn'
                elif tonalEntity == 'inq':
                    tonalEntity = 'yinq'
                elif v[0] == 'i':
                    # for rows 'i' and 'iu'
                    tonalEntity = 'y' + tonalEntity[1:]
                elif v[0] == 'u':
                    tonalEntity = 'w' + tonalEntity[1:]

        if tone.startswith('5'):
            tonalEntity = '.' + tonalEntity
        elif tone.endswith('Optional5th'):
            tonalEntity = self.optionalNeutralToneMarker + tonalEntity

        if plainEntity.isupper(): tonalEntity = tonalEntity.upper()
        elif plainEntity.istitle(): tonalEntity = tonalEntity.title()

        return tonalEntity

    @cachedproperty
    def _syllableToneLookup(self):
        """Mapping of tonal entities to plain entities and tone."""
        syllableToneLookup = {}
        allTones = self.getTones()
        for plainEntity in self.getPlainReadingEntities():
            for tone in allTones:
                tonalEntity = self.getTonalEntity(plainEntity, tone)
                syllableToneLookup[tonalEntity] = (plainEntity, tone)
        return syllableToneLookup

    def splitEntityTone(self, entity):
        syllableToneLookup = self._syllableToneLookup
        try:
            plainEntity, tone = syllableToneLookup[entity.lower()]
        except KeyError:
            # don't work for Erlhuah forms
            if self.isReadingEntity(entity):
                raise UnsupportedError("Not supported for '%s'" % entity)
            else:
                raise InvalidEntityError("Invalid entity given for '%s'"
                    % entity)

        if entity.isupper(): plainEntity = plainEntity.upper()
        elif entity.istitle(): plainEntity = plainEntity.title()

        return plainEntity, tone

    def isRhotacisedReadingEntity(self, entity):
        """
        Checks if the given entity is a r-coloured entity (Erlhuah form).

        :type entity: str
        :param entity: reading entity
        :rtype: bool
        :return: ``True`` if the given entity is a r-coloured entity, ``False``
            otherwise.
        """
        return entity.endswith('l') \
            and entity not in ['el', 'erl', 'eel', 'ell'] \
            and self.isReadingEntity(entity)

    @cachedproperty
    def _rhotacisedFinals(self):
        """Mapping of entity final to rhotacised final."""
        table = self.db.tables['GRRhotacisedFinals']

        finalTypes = [column.name for column in table.c \
            if column.name != 'GRFinal']

        rhotacisedFinals = dict([(final, {}) for final in finalTypes])

        columns = [table.c.GRFinal]
        columns.extend([table.c[final] for final in finalTypes])
        for row in self.db.selectRows(select(columns)):
            nonRhotacisedFinal = row[0]
            for idx, column in enumerate(finalTypes):
                if row[idx + 1]:
                    rhotacisedFinals[column][nonRhotacisedFinal] = row[idx + 1]

        return rhotacisedFinals

    def getRhotacisedTonalEntity(self, plainEntity, tone):
        """
        Gets the r-coloured entity (Erlhuah form) with tone mark for the given
        plain entity and tone. Not all entity-tone combinations are supported.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: str
        :return: entity with appropriate tone
        :raise InvalidEntityError: if the entity is invalid.
        :raise UnsupportedError: if the given entity is an Erlhuah form or the
            syllable is not supported in this given tone.
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'"
                    % (plainEntity, unicode(tone)))

        # no Erlhuah for e and er
        if plainEntity in ['e', 'el']:
            raise UnsupportedError("Not supported for '%s'" % plainEntity)

        # split syllable into CVC parts
        c1, v, c2 = self.splitPlainSyllableCVC(plainEntity)
        baseTone = self.getBaseTone(tone)

        # apply Rule 7 which is not included in the table
        if c1 in ['m', 'n', 'l', 'r']:
            if baseTone == 1:
                c1 = c1 + 'h'
            elif baseTone == 2:
                # use base form
                baseTone = 1

        # for i-, u-, iu- rows use the zero initial mapping
        if not c1 and v[0] in ['i', 'u']:
            column = self.DB_RHOTACISED_FINAL_MAPPING_ZEROINITIAL[baseTone]
        else:
            column = self.DB_RHOTACISED_FINAL_MAPPING[baseTone]

        rhotacisedFinals = self._rhotacisedFinals

        if v + c2 not in rhotacisedFinals[column]:
            raise UnsupportedError(
                "No Erlhuah form for '%s' and tone '%s'" % (plainEntity, tone))
        tonalFinal = rhotacisedFinals[column][v + c2]

        # use selected apostrophe
        if self.grRhotacisedFinalApostrophe \
            != self.DB_RHOTACISED_FINAL_APOSTROPHE:
            tonalFinal = tonalFinal.replace(self.DB_RHOTACISED_FINAL_APOSTROPHE,
                    self.grRhotacisedFinalApostrophe)

        tonalEntity = c1 + tonalFinal

        if tone.startswith('5'):
            tonalEntity = '.' + tonalEntity
        elif tone.endswith('Optional5th'):
            tonalEntity = self.optionalNeutralToneMarker + tonalEntity

        return tonalEntity

    @cachedproperty
    def _rhotacisedColumnToneLookup(self):
        """Mapping of rhotacised to base form."""
        rhotacisedColumnToneLookup = {}

        columnList = self.DB_RHOTACISED_FINAL_MAPPING_ZEROINITIAL.items()
        columnList.extend(self.DB_RHOTACISED_FINAL_MAPPING.items())
        for tone, columnName in columnList:
            if columnName in rhotacisedColumnToneLookup:
                assert(rhotacisedColumnToneLookup[columnName] == tone)
            rhotacisedColumnToneLookup[columnName] = tone
        return rhotacisedColumnToneLookup

    def getBaseEntitiesForRhotacised(self, tonalEntity):
        """
        Gets a list of base entities as plain entity/tone pair for a given
        r-coloured entity (Erlhuah form).

        This is the counterpart of :meth:`~GROperator.getRhotacisedTonalEntity`
        and as different syllables can have a similar rhotacised form, the back
        transformation is not injective.

        :type tonalEntity: str
        :param tonalEntity: r-coloured entity
        :rtype: set of tuple
        :return: list of plain entities with tone
        :raise InvalidEntityError: if the entity is invalid.
        """
        if tonalEntity.startswith('.'):
            baseTone = '5th'
            baseTonalEntity = tonalEntity[1:]
        elif tonalEntity.startswith(self.optionalNeutralToneMarker):
            baseTone = 'Optional5th'
            baseTonalEntity = tonalEntity[1:]
        else:
            baseTone = ''
            baseTonalEntity = tonalEntity

        # transform to DB apostrophe
        baseTonalEntity = baseTonalEntity.replace(
            self.grRhotacisedFinalApostrophe,
            self.DB_RHOTACISED_FINAL_APOSTROPHE)

        # match initials and rest, grab tonal 'h' for mnlr
        matchObj = re.match(r'((?:[mnlr])|h|(?:[^wyaeiou]*))(h?)(.*)$',
            baseTonalEntity)
        initial, h, baseTonalFinal = matchObj.groups()

        toneMapping = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}

        entityList = set()

        # lookup table data
        table = self.db.tables['GRRhotacisedFinals']

        finalTypes = [column.name for column in table.c \
            if column.name != 'GRFinal']

        columns = [table.c.GRFinal]
        finalTypeColumns = [table.c[final] for final in finalTypes]
        columns.extend(finalTypeColumns)

        results = self.db.selectRows(select(columns,
            or_(*[column == baseTonalFinal for column in finalTypeColumns])))
        if not results:
            raise InvalidEntityError(
                "Invalid rhotacised entity given for '%s'" % tonalEntity)

        rhotacisedColumnToneLookup = self._rhotacisedColumnToneLookup

        for row in results:
            nonRhotacisedFinal = row[0]
            # match tone
            for idx, col in enumerate(row[1:]):
                if col == baseTonalFinal:
                    column = finalTypes[idx]
                    toneIndex = rhotacisedColumnToneLookup[column]
                    break
            else:
                assert(False)

            # special case
            if initial in ['m', 'n', 'l', 'r'] and toneIndex == 1 and not h:
                toneIndex = 2

            if baseTone == '5th':
                tone = '5thToneEtymological' + toneMapping[toneIndex]
            elif baseTone == 'Optional5th':
                tone = toneMapping[toneIndex] + 'ToneOptional5th'
            else:
                tone = toneMapping[toneIndex] + 'Tone'

            plainEntity = initial + nonRhotacisedFinal
            # check if form exists
            if self.isPlainReadingEntity(plainEntity):
                entityList.add((plainEntity, tone))

        return entityList

    @cachedmethod
    def getAbbreviatedEntities(self):
        """
        Gets a list of abbreviated GR entities. This returns single entities
        from :meth:`~GROperator.getAbbreviatedForms` and only returns those
        that don't also exist as full forms. Includes repetition markers
        *x* and *v*.

        Returned entities are in lowercase.

        :rtype: list
        :return: list of abbreviated GR forms
        """
        abbreviatedEntites = set()
        for entities in self.getAbbreviatedForms():
            abbreviatedEntites.update(entities)
        abbreviatedEntites = abbreviatedEntites - self.getFullReadingEntities()
        abbreviatedEntites.update(['x', 'v', '.x', '.v',
            self.optionalNeutralToneMarker + u'x',
            self.optionalNeutralToneMarker + u'v'])
        return frozenset(abbreviatedEntites)

    def isAbbreviatedEntity(self, entity):
        """
        Returns true if the given entity is an abbreviated spelling.

        Case of characters will be handled depending on the setting for option
        ``'case'``.

        :type entity: str
        :param entity: entity to check
        :rtype: bool
        :return: ``True`` if entity is an abbreviated form.
        """
        # check capitalisation
        if self.case == 'lower' and not entity.islower():
            return False

        return entity.lower() in self.getAbbreviatedEntities()

    @cachedmethod
    def getAbbreviatedForms(self):
        """
        Gets a list of abbreviated forms used in GR.

        The returned list consists of a tuple of one or more possibly
        abbreviated reading entites in lowercase. See
        :meth:`~GROperator.getAbbreviatedFormData` on how to get more
        information on these forms.

        :rtype: list
        :return: a list of abbreviated forms
        """
        return frozenset(self._abbreviatedLookup.keys())

    def getAbbreviatedFormData(self, entities):
        u"""
        Gets table of abbreviated entities including the traditional Chinese
        characters, original spelling and specialised information.

        Some abbreviated syllables come with additional information:

        - ``'T'``, the abbreviated form shortens the tonal information,
        - ``'S'``, the abbreviated form shows a tone sandhi,
        - ``'I'``, the full spelling is a non-standard pronunciation, or
          another mapping, that can be ignored,
        - ``'F'``, the abbreviated entity or entities also exist(s) as a full
          form (as full forms).

        Example:
            >>> from cjklib.reading import operator
            >>> gr = operator.GROperator()
            >>> gr.getAbbreviatedEntityData(['yi'])
            [(u'\u4e00', [u'i'], set([u'S', u'T']))]

        :type entities: list of str
        :param entities: entities abbreviated form for which information is
            returned
        :rtype: list
        :return: list full spellings, Chinese character string and specialised
            information

        .. todo::
            * Lang: *tz* is currently mapped to *.tzy*. Character 子 though
              generally has 3rd tone, which then should be *tzyy* or
              *.tzyy*. See 'A Grammar of Spoken Chinese', p. 36
              ("-.tzy (which we abbreviate as -tz)") and p. 55
              ("suffix -tz (<tzyy)")
        """
        entities = tuple([entity.lower() for entity in entities])
        if entities not in self._abbreviatedLookup:
            raise ValueError('Given entities %s are not an abbreviated form' \
                % repr(entities))

        # return copy
        return self._abbreviatedLookup[entities][:]

    @cachedproperty
    def _abbreviatedLookup(self):
        """Abbreviated form lookup table."""
        abbrConversionLookup = {}

        fullEntities = self.getFullReadingEntities()

        table = self.db.tables['GRAbbreviation']
        result = self.db.selectRows(
            select([table.c.TraditionalChinese, table.c.GR,
                table.c.GRAbbreviation, table.c.Specialised]))
        for chars, original, abbreviated, specialised in result:
            specialisedInformation = set(specialised)

            abbreviatedEntities = tuple(abbreviated.split(' '))
            for entity in abbreviatedEntities:
                if entity not in fullEntities:
                    break
            else:
                specialisedInformation.add('F') # is full entity/-ies

            originalEntities = original.split(' ')
            if abbreviatedEntities not in abbrConversionLookup:
                abbrConversionLookup[abbreviatedEntities] = []

            abbrConversionLookup[abbreviatedEntities].append(
                (chars, originalEntities, specialisedInformation))

        return abbrConversionLookup

    @cachedmethod
    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading without
        r-coloured forms (Erlhuah forms). Different to
        :meth:`~GROperator.getReadingEntities` the entities will carry no
        tone mark.

        :rtype: set of str
        :return: set of supported syllables
        """
        table = self.db.tables['GRSyllables']
        return frozenset(self.db.selectScalars(select([table.c.GR])))

    @cachedmethod
    def getFullReadingEntities(self):
        """
        Gets a set of full entities supported by the reading excluding
        abbreviated forms.

        :rtype: set of str
        :return: set of supported syllables
        """
        plainSyllables = self.getPlainReadingEntities()

        fullReadingEntities = set()
        allTones = self.getTones()
        for syllable in plainSyllables:
            for tone in allTones:
                fullReadingEntities.add(self.getTonalEntity(syllable, tone))

        # Erlhuah
        for syllable in plainSyllables:
            for tone in allTones:
                try:
                    erlhuahSyllable = self.getRhotacisedTonalEntity(
                        syllable, tone)
                    fullReadingEntities.add(erlhuahSyllable)
                except UnsupportedError:
                    # ignore errors about tone combinations that don't exist
                    pass
        return frozenset(fullReadingEntities)

    @cachedmethod
    def getReadingEntities(self):
        syllableSet = set(self.getFullReadingEntities())
        if self.abbreviations:
            syllableSet.update(self.getAbbreviatedEntities())

        return frozenset(syllableSet)

    def isReadingEntity(self, entity):
        # overwrite default method, use lookup dictionary, otherwise we would
        #   end up in a recursive call
        return RomanisationOperator.isReadingEntity(self, entity)

    @cachedmethod
    def getFormattingEntities(self):
        # Include space as repetition markers can be separated by whitespace
        #   from their target syllable.
        return frozenset([self.grSyllableSeparatorApostrophe, ' '])


class MandarinIPAOperator(TonalIPAOperator):
    u"""
    Provides an operator on strings in Mandarin Chinese written in the
    *International Phonetic Alphabet* (*IPA*).
    """
    READING_NAME = "MandarinIPA"

    TONE_MARK_PREFER = {'numbers': {'3': '3rdToneRegular', '5': '5thTone'},
        'chaoDigits': {'': '5thTone'}, 'ipaToneBar': {}, 'diacritics': {}}

    TONES = ['1stTone', '2ndTone', '3rdToneRegular', '3rdToneLow',
        '4thTone', '5thTone', '5thToneHalfHigh', '5thToneMiddle',
        '5thToneHalfLow', '5thToneLow']

    TONE_MARK_MAPPING = {'numbers': {'1stTone': '1', '2ndTone': '2',
            '3rdToneRegular': '3', '3rdToneLow': '3', '4thTone': '4',
            '5thTone':'5', '5thToneHalfHigh': '5', '5thToneMiddle': '5',
            '5thToneHalfLow': '5', '5thToneLow': '5'},
        'chaoDigits': {'1stTone': '55', '2ndTone': '35',
            '3rdToneRegular': '214', '3rdToneLow': '21', '4thTone': '51',
            '5thTone':'', '5thToneHalfHigh': '', '5thToneMiddle': '',
            '5thToneHalfLow': '', '5thToneLow': ''},
        'ipaToneBar': {'1stTone': u'˥˥', '2ndTone': u'˧˥',
            '3rdToneRegular': u'˨˩˦', '3rdToneLow': u'˨˩', '4thTone': u'˥˩',
            '5thTone':'', '5thToneHalfHigh': u'꜉', '5thToneMiddle': u'꜊',
            '5thToneHalfLow': u'꜋', '5thToneLow': u'꜌'},
        # TODO
        #'diacritics': {'1stTone': u'\u0301', '2ndTone': u'\u030c',
            #'3rdToneRegular': u'\u0301\u0300\u0301', '3rdToneLow': u'\u0300',
            #'4thTone': u'\u0302', '5thTone': u'', '5thToneHalfHigh': '',
            #'5thToneMiddle': '', '5thToneHalfLow': '', '5thToneLow': ''}
        }

    @cachedmethod
    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. These
        entities will carry no tone mark.

        :rtype: set of str
        :return: set of supported syllables
        """
        table = self.db.tables['MandarinIPAInitialFinal']
        return frozenset(self.db.selectScalars(select([table.c.IPA])))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        :type plainSyllable: str
        :param plainSyllable: syllable in IPA without tone marks
        :rtype: tuple of str
        :return: tuple of syllable onset and rhyme
        :raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).
        """
        table = self.db.tables['MandarinIPAInitialFinal']
        entry = self.db.selectRow(
            select([table.c.IPAInitial, table.c.IPAFinal],
                table.c.IPA == plainSyllable))
        if not entry:
            raise InvalidEntityError(
                "Entity '%s' is no valid IPA form in this system'"
                    % plainSyllable)
        return (entry[0], entry[1])


class MandarinBrailleOperator(ReadingOperator):
    u"""
    Provides an operator on strings written in the *Braille* system for
    Mandarin.

    .. todo::
        * Impl: Punctuation marks in isFormattingEntity() and
          getFormattingEntities(). Then change
          PinyinBrailleConverter.convertEntitySequence() to use these methods.
    """
    READING_NAME = "MandarinBraille"

    TONEMARKS = [u'⠁', u'⠂', u'⠄', u'⠆', '']

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword toneMarkType: if set to ``'braille'`` tones will be marked
            (using the Braille characters ), if set to ``'none'`` no tone marks
            will be used and no tonal information will be supplied at all.
        :keyword missingToneMark: if set to ``'fifth'`` missing tone marks are
            interpreted as fifth tone (which by default lack a tone mark), if
            set to ``'extended'`` missing tonal information is allowed and takes
            on the same form as fifth tone, rendering conversion processes
            lossy.
        """
        super(MandarinBrailleOperator, self).__init__(**options)

        # check tone marks
        if self.toneMarkType not in ['braille', 'none']:
            raise ValueError("Invalid option %s for keyword 'toneMarkType'"
                % repr(self.toneMarkType))

        # check strictness on tones, i.e. report missing tone info
        if self.missingToneMark not in ['fifth', 'extended']:
            raise ValueError("Invalid option %s for keyword 'missingToneMark'"
                % repr(self.missingToneMark))

        # split regex
        initials = ''.join(self.db.selectScalars(
            select([self.db.tables['PinyinBrailleInitialMapping'].c.Braille],
                distinct=True)))
        finals = ''.join(self.db.selectScalars(
            select([self.db.tables['PinyinBrailleFinalMapping'].c.Braille],
                distinct=True)))
        # initial and final optional (but at least one), tone optional
        self._splitRegex = re.compile(ur'((?:(?:[' + re.escape(initials) \
            + '][' + re.escape(finals) + ']?)|['+ re.escape(finals) \
            + u'])[' + re.escape(''.join(self.TONEMARKS)) + ']?)')
        self._brailleRegex = re.compile(ur'([⠀-⣿]+|[^⠀-⣿]+)')

    @classmethod
    def getDefaultOptions(cls):
        options = super(MandarinBrailleOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'braille',
            'missingToneMark': 'extended'})

        return options

    @cachedmethod
    def getTones(self):
        """
        Returns a set of tones supported by the reading.

        :rtype: set
        :return: set of supported tone marks.
        """
        tones = range(1, 6)
        if self.missingToneMark == 'extended' or self.toneMarkType == 'none':
            tones.append(None)

        return tones

    def decompose(self, readingString):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each (exceptions possible).

        The given input string can contain other non reading characters, e.g.
        punctuation marks.

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        :type readingString: str
        :param readingString: reading string
        :rtype: list of str
        :return: a list of basic entities of the input string
        """
        def buildList(entityList):
            # further splitting of Braille and non-Braille parts/removing empty
            #   strings
            newList = self._brailleRegex.findall(entityList[0])

            if len(entityList) > 1:
                newList.extend(buildList(entityList[1:]))

            return newList

        return buildList(self._splitRegex.split(readingString))

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string.

        No special treatment is given for subsequent Braille entities. Use
        :meth:`~cjklib.reading.operator.MandarinBrailleOperator.getSpaceSeparatedEntities`
        to insert spaces between two Braille syllables.

        :type readingEntities: list of str
        :param readingEntities: list of basic entities or other content
        :rtype: str
        :return: composed entities
        """
        return "".join(readingEntities)

    def getSpaceSeparatedEntities(self, readingEntities):
        """
        Inserts spaces between two Braille entities for a given list of reading
        entities.

        Spaces in the Braille system are applied between words. This is not
        reflected here and instead a space will be added between single
        syllables.

        :type readingEntities: list of str
        :param readingEntities: list of basic entities or other content
        :rtype: list of str
        :return: entities with spaces inserted between Braille sequences
        """
        def isBrailleChar(char):
            return char >= u'⠀' and char <= u'⣿'

        newReadingEntities = []
        if len(readingEntities) > 0:
            lastIsBraille = False
            for entity in readingEntities:
                isBraille = len(entity) > 0 and isBrailleChar(entity[0])
                # separate two following entities with a space
                if lastIsBraille and isBraille:
                    newReadingEntities.append(u' ')
                newReadingEntities.append(entity)
                lastIsBraille = isBraille
        return newReadingEntities

    def getTonalEntity(self, plainEntity, tone):
        """
        Gets the entity with tone mark for the given plain entity and tone.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: str
        :return: entity with appropriate tone
        :raise InvalidEntityError: if the entity is invalid.
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'"
                    % (plainEntity, unicode(tone)))

        if self.toneMarkType == 'none' or tone == None:
            return plainEntity
        else:
            return plainEntity + self.TONEMARKS[tone-1]

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the name of the
        entity's tone.

        :type entity: str
        :param entity: entity with tonal information
        :rtype: tuple
        :return: plain entity without tone mark and additionally the tone
        :raise InvalidEntityError: if the entity is invalid.
        """
        if self.toneMarkType == 'none':
            return entity, None
        else:
            if entity[-1] in self.TONEMARKS:
                return entity[:-1], self.TONEMARKS.index(entity[-1]) + 1
            else:
                return entity, 5

    def isReadingEntity(self, entity):
        if not entity:
            return False

        try:
            plainEntity, _ = self.splitEntityTone(entity)
            if not plainEntity:
                return False

            initial, final = self.getOnsetRhyme(plainEntity)

            finalTable = self.db.tables['PinyinBrailleFinalMapping']
            if final and self.db.selectScalar(select([finalTable.c['Braille']],
                finalTable.c['Braille'] == final, distinct=True)) == None:
                return False

            initialTable = self.db.tables['PinyinBrailleInitialMapping']
            if initial and self.db.selectScalar(select(
                [initialTable.c['Braille']],
                initialTable.c['Braille'] == initial, distinct=True)) == None:
                return False

            return True
        except InvalidEntityError:
            return False

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        :type plainSyllable: str
        :param plainSyllable: syllable without tone marks
        :rtype: tuple of str
        :return: tuple of syllable onset and rhyme
        :raise InvalidEntityError: if the entity is invalid.
        """
        if len(plainSyllable) == 1:
            finalTable = self.db.tables['PinyinBrailleFinalMapping']
            if plainSyllable and self.db.selectScalar(
                select([finalTable.c.Braille],
                    finalTable.c.Braille == plainSyllable,
                    distinct=True)) != None:
                return '', plainSyllable
            else:
                return plainSyllable, ''
        elif len(plainSyllable) == 2:
            return plainSyllable[0], plainSyllable[1]
        else:
            raise InvalidEntityError("Invalid plain entity given with '" \
                + plainSyllable + "'")


class JyutpingOperator(TonalRomanisationOperator):
    """
    Provides an operator for the Cantonese romanisation *Jyutping* made by the
    *Linguistic Society of Hong Kong* (*LSHK*).
    """
    READING_NAME = 'Jyutping'
    _readingEntityRegex = re.compile(u"([A-Za-z]+[123456]?)")

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~JyutpingOperator.segment`) and thus decomposition (using
            :meth:`~JyutpingOperator.decompose`) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If ``False``
            the aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will
            be supported.
        :keyword toneMarkType: if set to ``'numbers'`` the default form of
            appended numbers from 1 to 6 will be used to mark tones, if set to
            ``'none'`` no tone marks will be used and no tonal information will
            be supplied at all.
        :keyword missingToneMark: if set to ``'noinfo'`` no tone information
            will be deduced when no tone mark is found (takes on value
            ``None``), if set to ``'ignore'`` this entity will not be valid
            and for segmentation the behaviour defined by
            ``'strictSegmentation'`` will take affect.
        """
        super(JyutpingOperator, self).__init__(**options)

        # check tone marks
        if self.toneMarkType not in ['numbers', 'none']:
            raise ValueError("Invalid option %s for keyword 'toneMarkType'"
                % repr(self.toneMarkType))

        # check strictness on tones, i.e. report missing tone info
        if self.missingToneMark not in ['noinfo', 'ignore']:
            raise ValueError("Invalid option %s for keyword 'missingToneMark'"
                % repr(self.missingToneMark))

    @classmethod
    def getDefaultOptions(cls):
        options = super(JyutpingOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'numbers', 'missingToneMark': 'noinfo'})

        return options

    @cachedmethod
    def getReadingCharacters(self):
        characters = (list(string.ascii_lowercase)
            + ['1', '2', '3', '4', '5', '6'])
        return frozenset(characters)

    @cachedmethod
    def getTones(self):
        tones = range(1, 7)
        if self.missingToneMark != 'ignore' or self.toneMarkType == 'none':
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        readingCharacters = self.getReadingCharacters()

        # check if composition won't combine reading and non-reading entities
        precedingEntity = None
        for entity in readingEntities:
            if precedingEntity and entity:
                precedingEntityIsReading = self.isReadingEntity(precedingEntity)
                entityIsReading = self.isReadingEntity(entity)

                # allow tone digits to separate
                if precedingEntity[-1] not in ['1', '2', '3', '4', '5'] \
                    and ((precedingEntityIsReading and not entityIsReading \
                        and entity[0] in readingCharacters) \
                    or (not precedingEntityIsReading and entityIsReading \
                        and precedingEntity[-1] in readingCharacters)):

                    if precedingEntityIsReading:
                        offendingEntity = entity
                    else:
                        offendingEntity = precedingEntity
                    raise CompositionError(
                        "Unable to delimit non-reading entity '%s'" \
                            % offendingEntity)

            precedingEntity = entity

        return "".join(readingEntities)

    def getTonalEntity(self, plainEntity, tone):
        if tone != None:
            tone = int(tone)
        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        if self.toneMarkType == 'none' or tone == None:
            return plainEntity

        return plainEntity + str(tone)

    def splitEntityTone(self, entity):
        if self.toneMarkType == 'none':
            return entity, None

        matchObj = re.search(u"[123456]$", entity)
        if matchObj:
            tone = int(matchObj.group(0))
            plainEntity = entity[0:len(entity)-1]

            if not self.isToneValid(plainEntity, tone):
                raise InvalidEntityError(
                    "Syllable '%s' can not occur with tone '%s'" \
                        % (plainEntity, str(tone)))
            return plainEntity, tone
        else:
            if self.missingToneMark == 'ignore':
                raise InvalidEntityError("No tone information given for '" \
                    + entity + "'")
            else:
                return entity, None

    def isToneValid(self, plainEntity, tone):
        """
        Checks if the given plain entity and tone combination is valid.

        Only syllables with unreleased finals occur with stop tones, other forms
        must not (see
        :meth:`~cjklib.reading.operator.JyutpingOperator.hasStopTone`).

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: bool
        :return: ``True`` if given combination is valid, ``False`` otherwise
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'" \
                    % (plainEntity, str(tone)))

        return not self.hasStopTone(plainEntity) or tone in [1, 3, 6, None]

    @cachedmethod
    def getPlainReadingEntities(self):
        return frozenset(self.db.selectScalars(
            select([self.db.tables['JyutpingSyllables'].c.Jyutping])))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        The syllabic nasals *m*, *ng* will be regarded as being finals.

        Returned strings will be lowercase.

        :type plainSyllable: str
        :param plainSyllable: syllable without tone marks
        :rtype: tuple of str
        :return: tuple of entity onset and rhyme
        :raise InvalidEntityError: if the entity is invalid.

        .. todo::
            * Impl: Finals *ing, ik, ung, uk* differ from other finals with
              same vowels. What semantics/view do we want to provide on the
              syllable parts?
        """
        # get outside try block, will be evaluated on first call
        syllableData = self._syllableData
        try:
            return syllableData[plainSyllable.lower()]
        except KeyError:
            raise InvalidEntityError(
                "'%s' not a valid plain Jyutping syllable'"
                    % plainSyllable)

    def hasStopTone(self, plainEntity):
        """
        Checks if the given plain syllable can occur with stop tones which is
        the case for syllables with unreleased finals.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :rtype: bool
        :return: ``True`` if given syllable can occur with stop tones, ``False``
            otherwise
        """
        _, final = self.getOnsetRhyme(plainEntity)
        return final and final[-1] in ['p', 't', 'k']

    @cachedproperty
    def _syllableData(self):
        """Syllable structure information"""
        table = self.db.tables['JyutpingInitialFinal']
        result = self.db.selectRows(
            select([table.c.Jyutping, table.c.JyutpingInitial,
                table.c.JyutpingFinal]))

        return dict([(s, (i, f)) for s, i, f in result])


class CantoneseYaleOperator(TonalRomanisationOperator):
    u"""
    Provides an operator for the Cantonese Yale romanisation. For conversion
    between different representations the
    :class:`~cjklib.reading.converter.CantoneseYaleDialectConverter` can be
    used.
    """
    READING_NAME = 'CantoneseYale'

    TONES = ['1stToneLevel', '1stToneFalling', '2ndTone', '3rdTone', '4thTone',
        '5thTone', '6thTone']
    """Names of tones used in the romanisation."""
    TONE_MARK_MAPPING = {'numbers': {'1stToneLevel': ('1', ''),
            '1stToneFalling': ('1', ''), '2ndTone': ('2', ''),
            '3rdTone': ('3', ''), '4thTone': ('4', ''), '5thTone': ('5', ''),
            '6thTone': ('6', ''), None: ('', '')},
        'diacritics': {'1stToneLevel': (u'\u0304', ''),
            '1stToneFalling': (u'\u0300', ''),
            '2ndTone': (u'\u0301', ''), '3rdTone': (u'', ''),
            '4thTone': (u'\u0300', 'h'), '5thTone': (u'\u0301', 'h'),
            '6thTone': (u'', 'h')},
        'internal': {'1stToneLevel': ('0', ''),
            '1stToneFalling': ('1', ''), '2ndTone': ('2', ''),
            '3rdTone': ('3', ''), '4thTone': ('4', 'h'), '5thTone': ('5', 'h'),
            '6thTone': ('6', 'h'), None: ('', '')}}
    """
    Mapping of tone name to representation per tone mark type. Representations
    includes a diacritic mark and optional the letter 'h' marking a low tone.

    The ``'internal'`` dialect is used for conversion between different forms of
    Cantonese Yale. As conversion to the other dialects can lose information
    (Diacritics: missing tone, Numbers: distinction between high level and high
    rising, None: no tones at all) conversion to this dialect can retain all
    information and thus can be used as a standard target reading.
    """

    syllableRegex = re.compile(ur'((?:m|ng|h|' \
        + u'(?:[bcdfghjklmnpqrstvwxyz]*' \
        + u'(?:(?:[aeiou]|[\u0304\u0301\u0300])+|yu[\u0304\u0301\u0300]?)))' \
        + u'(?:h(?!(?:[aeiou]|yu)))?' \
        + '(?:[mnptk]|ng)?[0123456]?)')
    """
    Regex to split a string in NFD into several syllables in a crude way.
    The regular expressions works for both, diacritical and number tone marks.
    It consists of:

    - Nasal syllables,
    - Initial consonants,
    - vowels including diacritics,
    - tone mark h,
    - final consonants,
    - tone numbers.
    """

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword strictSegmentation: if ``True`` segmentation (using
            :meth:`~cjklib.reading.operator.RomanisationOperator.segment`)
            and thus decomposition (using
            :meth:`~cjklib.reading.operator.RomanisationOperator.decompose`)
            will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If ``False``
            the aforesaid string will be returned unsegmented.
        :keyword case: if set to ``'lower'``, only lower case will be supported,
            if set to ``'both'`` a mix of upper and lower case will be
            supported.
        :keyword toneMarkType: if set to ``'diacritics'`` tones will be marked
            using diacritic marks and the character *h* for low tones, if set
            to ``'numbers'`` appended numbers from 1 to 6 will be used to mark
            tones, if set to ``'none'`` no tone marks will be used and no tonal
            information will be supplied at all.
        :keyword missingToneMark: if set to ``'noinfo'`` no tone information
            will be deduced when no tone mark is found (takes on value
            ``None``), if set to ``'ignore'`` this entity will not be valid
            and for segmentation the behaviour defined by
            ``'strictSegmentation'`` will take effect. This option only has
            effect if the value ``'numbers'`` is given for the option
            *toneMarkType*.
        :keyword strictDiacriticPlacement: if set to ``True`` syllables have to
            follow the diacritic placement rule of Cantonese Yale strictly (see
            :meth:`~cjklib.reading.operator.CantoneseYaleOperator.getTonalEntity`).
            Wrong placement will result in
            :meth:`~cjklib.reading.operator.CantoneseYaleOperator.splitEntityTone`
            raising an :class:`~cjklib.exception.InvalidEntityError`.
            Defaults to ``False``.
        :keyword yaleFirstTone: tone in Yale which the first tone for tone marks
            with numbers should be mapped to. Value can be ``'1stToneLevel'`` to
            map to the level tone with contour 55 or ``'1stToneFalling'`` to map
            to the falling tone with contour 53. This option can only be used
            for tone mark type ``'numbers'``.
        """
        super(CantoneseYaleOperator, self).__init__(**options)

        # check tone marks
        if self.toneMarkType not in ['diacritics', 'numbers', 'none',
            'internal']:
            raise ValueError("Invalid option %s for keyword 'toneMarkType'"
                % repr(self.toneMarkType))

        # check strictness on tones, i.e. report missing tone info
        if self.missingToneMark not in ['noinfo', 'ignore']:
            raise ValueError("Invalid option %s for keyword 'missingToneMark'"
                % repr(self.missingToneMark))

        # check yaleFirstTone for handling ambiguous conversion of first
        #   tone in Cantonese that has two different representations in Yale
        if self.yaleFirstTone not in ['1stToneLevel', '1stToneFalling']:
            raise ValueError("Invalid option %s for keyword 'yaleFirstTone'"
                % repr(self.yaleFirstTone))

        # create lookup dict
        if self.toneMarkType != 'none':
            # create lookup dicts
            self._toneMarkLookup = {}
            for tone in self.getTones():
                toneMarks = self.TONE_MARK_MAPPING[self.toneMarkType][tone]
                self._toneMarkLookup[toneMarks] = tone
            if self.toneMarkType == 'numbers':
                # first tone ambiguous for tone mark as numbers, set user
                #   selected tone
                self._toneMarkLookup[('1', '')] = self.yaleFirstTone

        # create tone regex
        if self.toneMarkType != 'none':
            self._primaryToneRegex = re.compile(r"^[a-z]+([" \
                + r"".join(set([re.escape(toneMark) for toneMark, _ \
                    in self.TONE_MARK_MAPPING[self.toneMarkType].values()])) \
                + r"]?)", re.IGNORECASE | re.UNICODE)
            self._hCharRegex = re.compile(r"(?i)^.*(?:[aeiou]|m|ng)(h)")

        # set split regular expression, works for all tone marks
        self._readingEntityRegex = re.compile(u'((?:' \
            + '|'.join([re.escape(v) for v in self._getDiacriticVowels()]) \
            + u'|[a-z])+[0123456]?)', re.IGNORECASE | re.UNICODE)

    @classmethod
    def getDefaultOptions(cls):
        options = super(CantoneseYaleOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'diacritics',
            'missingToneMark': 'noinfo', 'strictDiacriticPlacement': False,
            'yaleFirstTone': '1stToneLevel'})

        return options

    @staticmethod
    def _getDiacriticVowels():
        """
        Gets a list of Cantonese Yale vowels with diacritical marks for tones.

        The list includes characters *m*, *n* and *h* for nasal forms.

        :rtype: list of str
        :return: list of Cantonese Yale vowels with diacritical marks
        """
        vowelList = set([])
        for nucleusFirstChar in 'aeioumnh':
            for toneMark, _ in \
                CantoneseYaleOperator.TONE_MARK_MAPPING['diacritics'].values():
                if toneMark:
                    vowelList.add(unicodedata.normalize("NFC",
                        nucleusFirstChar + toneMark))
        return vowelList

    @classmethod
    def guessReadingDialect(cls, readingString, includeToneless=False):
        """
        Takes a string written in Cantonese Yale and guesses the reading
        dialect.

        Currently only the option ``'toneMarkType'`` is guessed. Unless
        ``'includeToneless'`` is set to ``True`` only the tone mark types
        ``'diacritics'`` and ``'numbers'`` are considered as the latter one can
        also represent the state of missing tones.

        :type readingString: str
        :param readingString: Cantonese Yale string
        :type includeToneless: bool
        :param includeToneless: if set to ``True`` option ``'toneMarkType'`` can
            take on value ``'none'``, but by default (i.e. set to ``False``) is
            covered by tone mark type set to ``'numbers'``.
        :rtype: dict
        :return: dictionary of basic keyword settings
        """
        # split into entities using a simple regex for all dialect forms
        entities = cls.syllableRegex.findall(
            unicodedata.normalize("NFD", unicode(readingString.lower())))

        # guess tone mark type
        diacriticEntityCount = 0
        numberEntityCount = 0

        for entity in entities:
            # take entity (which can be several connected syllables) and check
            if entity[-1] in '123456':
                numberEntityCount = numberEntityCount + 1
            elif 'h' in entity[1:]:
                # tone mark character 'h' for low tone only used with diacritics
                diacriticEntityCount = diacriticEntityCount + 1
            else:
                for diacriticMarc in [u'\u0304', u'\u0301', u'\u0300']:
                    if diacriticMarc in entity:
                        diacriticEntityCount = diacriticEntityCount + 1
                        break
        # compare statistics
        if includeToneless \
            and (1.0 * max(diacriticEntityCount, numberEntityCount) \
                / len(entities)) < 0.1:
            # less than 1/10 units carry some possible tone mark, so decide
            #   for toneless
            toneMarkType = 'none'
        else:
            if diacriticEntityCount > numberEntityCount:
                toneMarkType = 'diacritics'
            else:
                # even if equal prefer numbers, as in case of missing tone marks
                #   we rather asume tone 'none' which is possible here
                toneMarkType = 'numbers'

        return {'toneMarkType': toneMarkType}

    @cachedmethod
    def getReadingCharacters(self):
        characters = set(string.ascii_lowercase)
        # add NFC vowels, strip off combining diacritical marks
        characters.update([c for c in self._getDiacriticVowels() \
            if len(c) == 1])
        characters.update([u'\u0304', u'\u0301', u'\u0300'])
        characters.update(['0', '1', '2', '3', '4', '5', '6'])
        return frozenset(characters)

    @cachedmethod
    def getTones(self):
        tones = self.TONES[:]
        if (self.missingToneMark == 'noinfo' \
            and self.toneMarkType in ['numbers', 'internal']) \
            or self.toneMarkType == 'none':
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        readingCharacters = self.getReadingCharacters()

        # check if composition won't combine reading and non-reading entities
        precedingEntity = None
        for entity in readingEntities:
            if precedingEntity and entity:
                precedingEntityIsReading = self.isReadingEntity(precedingEntity)
                entityIsReading = self.isReadingEntity(entity)

                # allow tone digits to separate
                if precedingEntity[-1] not in ['1', '2', '3', '4', '5'] \
                    and ((precedingEntityIsReading and not entityIsReading \
                        and entity[0] in readingCharacters) \
                    or (not precedingEntityIsReading and entityIsReading \
                        and precedingEntity[-1] in readingCharacters)):

                    if precedingEntityIsReading:
                        offendingEntity = entity
                    else:
                        offendingEntity = precedingEntity
                    raise CompositionError(
                        "Unable to delimit non-reading entity '%s'" \
                            % offendingEntity)

            precedingEntity = entity

        return "".join(readingEntities)

    @cachedproperty
    def _plainSubstringTable(self):
        """Set of plain entity substrings."""
        plainEntities = self.getPlainReadingEntities()
        # Extend with low tone indicator 'h'.
        entities = list(plainEntities)
        for entity in plainEntities:
            entities.append(self.getTonalEntity(entity, '6thTone'))

        substrings = []
        for syllable in entities:
            for i in range(len(syllable)):
                substrings.append(syllable[0:i+1])
        return frozenset(substrings)

    def _hasEntitySubstring(self, readingString):
        # reimplement to allow for misplaced tone marks
        def stripDiacritic(strng):
            """Strip one tonal diacritic mark off string."""
            strng = unicodedata.normalize("NFD", unicode(strng))
            for toneMark, _ in self.TONE_MARK_MAPPING['diacritics'].values():
                index = strng.find(toneMark)
                if toneMark and index >= 0:
                    # only remove one occurence so that multi-entity strings are
                    #   not merged to one, e.g. xīān (for Pinyin)
                    strng = strng.replace(toneMark, '', 1)
                    break

            return unicodedata.normalize("NFC", strng)

        if self.toneMarkType == 'diacritics':
            # We remove diacritics, so plain entities suffice.
            return stripDiacritic(readingString) in self._plainSubstringTable
        else:
            return super(CantoneseYaleOperator, self)._hasEntitySubstring(
                readingString)

    def getTonalEntity(self, plainEntity, tone):
        """
        .. todo::
            * Lang: Place the tone mark on the first character of the nucleus?
        """
        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        if self.toneMarkType == 'none':
            return plainEntity

        toneMark, hChar = self.TONE_MARK_MAPPING[self.toneMarkType][tone]

        if hChar or self.toneMarkType == 'diacritics':
            # split entity into vowel (aeiou) and non-vowel part for placing
            #   marks, h only for initial
            matchObj = re.match('(?i)^([^aeiou]*?)([aeiou]*)([^haeiou]*)$',
                plainEntity)
            if not matchObj:
                raise InvalidEntityError("Invalid entity given for '" \
                    + plainEntity + "'")

            nonVowelH, vowels, nonVowelT = matchObj.groups()
            # place 'h' after vowel (or after syllable for syllabic nasal) and
            #   diacritic on first vowel/first character for syllabic nasal
            if plainEntity.isupper():
                # make 'h' upper case if entity is upper case
                hChar = hChar.upper()

            if self.toneMarkType == 'diacritics':
                if vowels:
                    vowels = unicodedata.normalize("NFC", vowels[0] + toneMark \
                        + vowels[1:] + hChar)
                else:
                    nonVowelT = unicodedata.normalize("NFC", nonVowelT[0] \
                        + toneMark + nonVowelT[1:] + hChar)

                return nonVowelH + vowels + nonVowelT
            else:
                if vowels:
                    vowels += hChar
                else:
                    nonVowelT += hChar

                return nonVowelH + vowels + nonVowelT + toneMark

        elif self.toneMarkType in ['numbers', 'internal']:
            return plainEntity + toneMark

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the
        entity's tone index.

        The plain entity returned will always be in Unicode's
        *Normalization Form C* (NFC, see http://www.unicode.org/reports/tr15/).

        :type entity: str
        :param entity: entity with tonal information
        :rtype: tuple
        :return: plain entity without tone mark and entity's tone index
            (starting with 1)
        """
        # get decomposed Unicode string, e.g. ``'ū'`` to ``'u\u0304'``
        entity = unicodedata.normalize("NFD", unicode(entity))
        if self.toneMarkType == 'none':
            return unicodedata.normalize("NFC", entity), None

        # find primary tone mark
        matchObj = self._primaryToneRegex.search(entity)
        if not matchObj:
            raise InvalidEntityError("Invalid entity or no tone information " \
                "given for '" + entity + "'")
        toneMark = matchObj.group(1)
        plainEntity = entity[0:matchObj.start(1)] + entity[matchObj.end(1):]

        # find lower tone mark 'h' character
        matchObj = self._hCharRegex.search(plainEntity)
        if matchObj:
            hChar = matchObj.group(1)
            plainEntity = unicodedata.normalize("NFC",
                plainEntity[0:matchObj.start(1)] \
                    + plainEntity[matchObj.end(1):])
        else:
            hChar = ''

        try:
            tone = self._toneMarkLookup[(toneMark, hChar.lower())]
            # make sure stop tones always have the level tone, for diacritics
            if self.hasStopTone(plainEntity) and tone == '1stToneFalling' \
                and self.toneMarkType == 'numbers':
                tone = '1stToneLevel'
        except KeyError:
            raise InvalidEntityError(
                "Invalid entity or no tone information given for '%s'"
                    % entity)

        # check if placement of dicritic is correct
        if self.strictDiacriticPlacement:
            nfcEntity = unicodedata.normalize("NFC", unicode(entity))
            if nfcEntity != self.getTonalEntity(plainEntity, tone):
                raise InvalidEntityError(
                    "Wrong placement of diacritic for '%s'" \
                        % entity \
                    + " while strict checking enforced")

        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        return plainEntity, tone

    def isToneValid(self, plainEntity, tone):
        """
        Checks if the given plain entity and tone combination is valid.

        Only syllables with unreleased finals occur with stop tones, other forms
        must not (see
        :meth:`~cjklib.reading.operator.CantoneseYaleOperator.hasStopTone`).

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: bool
        :return: ``True`` if given combination is valid, ``False`` otherwise
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'" \
                    % (plainEntity, str(tone)))

        return not self.hasStopTone(plainEntity) or tone in ['1stToneLevel',
            '3rdTone', '6thTone', None]

    @cachedmethod
    def getPlainReadingEntities(self):
        return frozenset(self.db.selectScalars(select(
            [self.db.tables['CantoneseYaleSyllables'].c.CantoneseYale])))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        The syllabic nasals *m*, *ng* will be returned as final. Syllables yu,
        yun, yut will fall into (y, yu, ), (y, yu, n) and (y, yu, t).

        Returned strings will be lowercase.

        :type plainSyllable: str
        :param plainSyllable: syllable without tone marks
        :rtype: tuple of str
        :return: tuple of entity onset and rhyme
        :raise InvalidEntityError: if the entity is invalid.
        """
        onset, nucleus, coda = self.getOnsetNucleusCoda(plainSyllable)
        return onset, nucleus + coda

    def getOnsetNucleusCoda(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial), nucleus and coda,
        the latter building the rhyme (final).

        The syllabic nasals *m*, *ng* will be returned as coda. Syllables yu,
        yun, yut will fall into (y, yu, ), (y, yu, n) and (y, yu, t).

        Returned strings will be lowercase.

        :type plainSyllable: str
        :param plainSyllable: syllable in the Yale romanisation system without
            tone marks
        :rtype: tuple of str
        :return: tuple of syllable onset, nucleus and coda
        :raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).

        .. todo::
            * Impl: Finals *ing, ik, ung, uk, eun, eut, a* differ from other
              finals with same vowels. What semantics/view do we want to
              provide on the syllable parts?
        """
        # get outside try block, will be evaluated on first call
        syllableData = self._syllableData
        try:
            return syllableData[plainSyllable.lower()]
        except KeyError:
            raise InvalidEntityError(
                "'%s' not a valid plain Cantonese Yale syllable'"
                    % plainSyllable)

    def hasStopTone(self, plainEntity):
        """
        Checks if the given plain syllable can occur with stop tones which is
        the case for syllables with unreleased finals.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :rtype: bool
        :return: ``True`` if given syllable can occur with stop tones, ``False``
            otherwise
        """
        _, _, coda = self.getOnsetNucleusCoda(plainEntity)
        return coda in ['p', 't', 'k']

    @cachedproperty
    def _syllableData(self):
        """Table information about syllable structure from the database."""
        table = self.db.tables['CantoneseYaleInitialNucleusCoda']
        result = self.db.selectRows(select([table.c.CantoneseYale,
            table.c.CantoneseYaleInitial, table.c.CantoneseYaleNucleus,
            table.c.CantoneseYaleCoda]))

        return dict([(s, (i, n, c)) for s, i, n, c in result])


class CantoneseIPAOperator(TonalIPAOperator):
    u"""
    Provides an operator on strings of the Cantonese language written in the
    *International Phonetic Alphabet* (*IPA*).

    .. todo::
        * Lang: Shed more light on tone sandhi in Cantonese language.
        * Impl: Implement diacritics for Cantonese Tones. On which part of the
          syllable should they be placed. Document.
        * Lang: Binyām 變音
        * Impl: What are the semantics of non-level tones given for unreleased
          stop finals? Take high rising Binyam into account.
    """
    READING_NAME = "CantoneseIPA"

    TONES = ['HighLevel', 'MidLevel', 'MidLowLevel', 'HighRising',
        'MidLowRising', 'MidLowFalling', 'HighFalling']

    STOP_TONES = {'HighStopped': 'HighLevel', 'MidStopped': 'MidLevel',
        'MidLowStopped': 'MidLowLevel'}
    """Cantonese stop tone mapping to general level tones."""

    STOP_TONES_EXPLICIT = {'HighStopped_Short': ('HighLevel', 'S'),
        'MidStopped_Short': ('MidLevel', 'S'),
        'MidLowStopped_Short': ('MidLowLevel', 'S'),
        'HighStopped_Long': ('HighLevel', 'L'),
        'MidStopped_Long': ('MidLevel', 'L'),
        'MidLowStopped_Long': ('MidLowLevel', 'L')}
    """
    Cantonese stop tone mapping to general level tones with stop tones realised
    for explicit marking short/long pronunciation.
    """

    TONE_MARK_PREFER = {'numbers': {'1': 'HighLevel', '3': 'MidLevel',
            '6': 'MidLowLevel'},
        'chaoDigits': {'55': 'HighLevel', '33': 'MidLevel',
            '22': 'MidLowLevel'},
        'ipaToneBar': {u'˥˥': 'HighLevel', u'˧˧': 'MidLevel',
            u'˨˨': 'MidLowLevel'},
        'diacritics': {}}

    TONE_MARK_MAPPING = {'numbers': {'HighLevel': '1', 'MidLevel': '3',
            'MidLowLevel': '6', 'HighRising': '2', 'MidLowRising': '5',
            'MidLowFalling': '4', 'HighFalling': '1', 'HighStopped_Short': '1',
            'MidStopped_Short': '3', 'MidLowStopped_Short': '6',
            'HighStopped_Long': '1', 'MidStopped_Long': '3',
            'MidLowStopped_Long': '6'},
        'chaoDigits': {'HighLevel': '55', 'MidLevel': '33',
            'MidLowLevel': '22', 'HighRising': '25', 'MidLowRising': '23',
            'MidLowFalling': '21', 'HighFalling': '52',
            'HighStopped_Short': '5', 'MidStopped_Short': '3',
            'MidLowStopped_Short': '2', 'HighStopped_Long': '55',
            'MidStopped_Long': '33', 'MidLowStopped_Long': '22'},
        'ipaToneBar': {'HighLevel': u'˥˥', 'MidLevel': u'˧˧',
            'MidLowLevel': u'˨˨', 'HighRising': u'˨˥', 'MidLowRising': u'˨˧',
            'MidLowFalling': u'˨˩', 'HighFalling': u'˥˨',
            'HighStopped_Short': u'˥', 'MidStopped_Short': u'˧',
            'MidLowStopped_Short': u'˨', 'HighStopped_Long': u'˥˥',
            'MidStopped_Long': u'˧˧', 'MidLowStopped_Long': u'˨˨'},
        #'diacritics': {}
        }
    # The mapping is injective for the restriction on the seven basic tones,
    #   and together with TONE_MARK_PREFER getToneForToneMark() knows what to
    #   return for each tone mark

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword toneMarkType: type of tone marks, one out of ``'numbers'``,
            ``'chaoDigits'``, ``'ipaToneBar'``, ``'diacritics'``, ``'none'``
        :keyword missingToneMark: if set to ``'noinfo'`` no tone information
            will be deduced when no tone mark is found (takes on value
            ``None``), if set to ``'ignore'`` this entity will not be valid.
        :keyword firstToneName: tone for mark ``'1'`` under tone mark type
            ``'numbers'`` for ambiguous mapping between tones *'HighLevel'* or
            *'HighFalling'* under syllables without stop tones. For the latter
            tone mark ``'1'`` will still resolve to *'HighLevel'*,
            *'HighStopped'* or *'HighStopped_Short'* and *'HighStopped_Long'*
            depending on the value of option ``'stopTones'``.
        :keyword stopTones: if set to ``'none'`` the basic 6 (7) tones will be
            used and stop tones will be reported as one of them, if set to
            ``'general'`` the three stop tones will be included, if set to
            ``'explicit'`` the short and long forms will be explicitly
            supported.
        """
        super(CantoneseIPAOperator, self).__init__(**options)

        if self.toneMarkType == 'diacritics':
            raise NotImplementedError() # TODO

        if self.firstToneName not in self.TONES:
            raise ValueError("Invalid tone %s for keyword 'firstToneName'"
                % repr(self.firstToneName))

        if self.stopTones not in ['none', 'general', 'explicit']:
            raise ValueError("Invalid option %s for keyword 'stopTones'"
                % repr(self.stopTones))

        # lookup base tone to explicit stop tone
        self._stopToneLookup = {}
        for stopTone in self.STOP_TONES_EXPLICIT:
            baseTone, vowelLength = self.STOP_TONES_EXPLICIT[stopTone]
            if not baseTone in self._stopToneLookup:
                self._stopToneLookup[baseTone] = {}
            self._stopToneLookup[baseTone][vowelLength] = stopTone
        # add general stop tones
        for stopTone in self.STOP_TONES:
            self._stopToneLookup[stopTone] \
                = self._stopToneLookup[self.STOP_TONES[stopTone]]

    @classmethod
    def getDefaultOptions(cls):
        options = super(CantoneseIPAOperator, cls).getDefaultOptions()
        options.update({'stopTones': 'none', 'firstToneName': 'HighLevel'})

        return options

    @cachedmethod
    def getTones(self):
        tones = self.TONES[:]
        if self.stopTones == 'general':
            tones.extend(self.STOP_TONES.keys())
        elif self.stopTones == 'explicit':
            tones.extend(self.STOP_TONES_EXPLICIT.keys())
        if self.missingToneMark == 'noinfo' \
            or self.toneMarkType == 'none':
            tones.append(None)

        return tones

    @cachedmethod
    def getPlainReadingEntities(self):
        return frozenset(self.db.selectScalars(select(
            [self.db.tables['CantoneseIPAInitialFinal'].c.IPA])))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        :type plainSyllable: str
        :param plainSyllable: syllable in IPA without tone marks
        :rtype: tuple of str
        :return: tuple of syllable onset and rhyme
        :raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).
        """
        table = self.db.tables['CantoneseIPAInitialFinal']
        entry = self.db.selectRow(
            select([table.c.IPAInitial, table.c.IPAFinal],
                table.c.IPA == plainSyllable))
        if not entry:
            raise InvalidEntityError("'" + plainSyllable \
                + "' not a valid IPA form in this system'")
        return (entry[0], entry[1])

    def getTonalEntity(self, plainEntity, tone):
        # reimplement to work with variable tone count
        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        # find explicit form
        explicitTone = self.getExplicitTone(plainEntity, tone)

        if self.toneMarkType == 'none' or explicitTone == None:
            entity = plainEntity
        else:
            entity = plainEntity \
                + self.TONE_MARK_MAPPING[self.toneMarkType][explicitTone]
        return unicodedata.normalize("NFC", entity)

    def splitEntityTone(self, entity):
        # encapsulate parent class' method to work with variable tone count
        plainEntity, baseTone \
            = super(CantoneseIPAOperator, self).splitEntityTone(entity)

        if self.toneMarkType == 'numbers' \
            and baseTone == 'HighLevel' \
            and not self.hasStopTone(plainEntity):
            # for tone mark type 'numbers' use user preference with 1st tone
            baseTone = self.firstToneName

        # convert base tone to dialect setting
        if self.stopTones == 'none' or baseTone == None:
            tone = baseTone
        else:
            explicitTone = self.getExplicitTone(plainEntity, baseTone)

            if explicitTone in self.TONES or self.stopTones == 'explicit':
                tone = explicitTone
            elif self.stopTones == 'general':
                tone, _ = explicitTone.split('_')

        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        return plainEntity, tone

    def isToneValid(self, plainEntity, tone):
        """
        Checks if the given plain entity and tone combination is valid.

        Only syllables with unreleased finals occur with stop tones, other forms
        must not (see
        :meth:`~cjklib.reading.operator.CantoneseIPAOperator.hasStopTone`).

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: bool
        :return: ``True`` if given combination is valid, ``False`` otherwise
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'" \
                    % (plainEntity, str(tone)))

        if self.hasStopTone(plainEntity):
            if self.stopTones == 'none':
                # stop tones are realised with base tones
                return tone in ['HighLevel', 'MidLevel', 'MidLowLevel', None]
            else:
                if self.stopTones == 'general':
                    # general stop tones
                    return tone not in self.TONES
                else:
                    if tone == None:
                        return True
                    elif tone not in self.STOP_TONES_EXPLICIT:
                        return False
                    # we need to check the syllable length
                    _, length = self.STOP_TONES_EXPLICIT[tone]
                    return length == self._unreleasedFinalData[plainEntity]
        else:
            return tone == None or tone in self.TONES

    def hasStopTone(self, plainEntity):
        """
        Checks if the given plain syllable can occur with stop tones which is
        the case for syllables with unreleased finals.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :rtype: bool
        :return: ``True`` if given syllable can occur with stop tones, ``False``
            otherwise
        """
        return plainEntity in self._unreleasedFinalData

    @classmethod
    def getBaseTone(cls, tone):
        """
        Gets the base tone for stop tones. The returned tone is one out of
        :attr:`~cjklib.reading.operator.CantoneseIPAOperator.TONES`.

        :type tone: str
        :param tone: tone
        :rtype: str
        :return: base tone
        """
        if tone == None or tone in cls.TONES:
            return tone
        elif tone in cls.STOP_TONES:
            return cls.STOP_TONES[tone]
        else:
            baseTone, _ = cls.STOP_TONES_EXPLICIT[tone]
            return baseTone

    def getExplicitTone(self, plainEntity, baseTone):
        """
        Gets the explicit tone for the given plain syllable and base tone.

        In case the 6 (7) base tones are used, the stop tone value can be
        deduced from the given syllable. The stop tone returned will be even
        more precise in denoting the vowel length that influences the tone
        contour.

        :type plainEntity: str
        :param plainEntity: syllable without tonal information
        :type baseTone: str
        :param baseTone: tone
        :rtype: str
        :return: explicit tone
        :raise InvalidEntityError: if the entity is invalid.
        """
        # only need explicit tones
        if baseTone in self._stopToneLookup:
            # check if we have an unreleased final consonant
            if self.hasStopTone(plainEntity):
                vowelLength = self._unreleasedFinalData[plainEntity]
                return self._stopToneLookup[baseTone][vowelLength]
            elif baseTone in self.STOP_TONES:
                # baseTone is a general stop tone but entity doesn't support
                #   stop tones
                raise InvalidEntityError(
                    "Invalid tone information given for '%s': '%s'" \
                        % (plainEntity, str(baseTone)))

        return baseTone

    def getToneForToneMark(self, toneMark):
        """
        Gets the base tone for the given tone mark.

        :type toneMark: str
        :param toneMark: tone mark representation of the tone
        :rtype: str
        :return: tone
        :raise InvalidEntityError: if the toneMark does not exist.
        """
        tone = super(CantoneseIPAOperator, self).getToneForToneMark(toneMark)
        # tone might be a explicit tone
        return self.getBaseTone(tone)

    @cachedproperty
    def _unreleasedFinalData(self):
        """Table information about unreleased finals from the database."""
        table = self.db.tables['CantoneseIPAInitialFinal']
        return dict(self.db.selectRows(
            select([table.c.IPA, table.c.VowelLength],
                table.c.UnreleasedFinal == 'U')))


class ShanghaineseIPAOperator(TonalIPAOperator):
    u"""
    Provides an operator on strings in Shanghainese (Chinese Wu as spoken in
    Shanghai) written in the *International Phonetic Alphabet* (*IPA*).
    """
    READING_NAME = "ShanghaineseIPA"

    TONES = ['YinPing', 'YinQu', 'YangQu', 'YinRu', 'YangRu']

    TONE_MARK_MAPPING = {
        #'numbers': {}, 'superscriptNumbers': {},
        'chaoDigits': {'YinPing': '53', 'YinQu': '34',
            'YangQu': '23', 'YinRu': '55', 'YangRu': '12'},
        'superscriptChaoDigits': {'YinPing': u'⁵³', 'YinQu': u'³⁴',
            'YangQu': u'²³', 'YinRu': u'⁵⁵', 'YangRu': u'¹²'},
        'ipaToneBar': {'YinPing': u'˥˧', 'YinQu': u'˧˦',
            'YangQu': u'˨˧', 'YinRu': u'˥˥', 'YangRu': u'˩˨'},
        # TODO
        #'diacritics': {}
        }

    def __init__(self, **options):
        """
        :param options: extra options
        :keyword dbConnectInst: instance of a
            :class:`~cjklib.dbconnector.DatabaseConnector`, if none is
            given, default settings will be assumed.
        :keyword toneMarkType: type of tone marks, one out of ``'numbers'``,
            ``'chaoDigits'``, ``'ipaToneBar'``, ``'diacritics'``, ``'none'``
        :keyword missingToneMark: if set to ``'noinfo'`` no tone information
            will be deduced when no tone mark is found (takes on value
            ``None``), if set to ``'ignore'`` this entity will not be valid.
            Either behaviour only becomes effective if the chosen
            ``'toneMarkType'`` makes no use of empty tone marks.
        :keyword constrainEntering: if set to ``True`` entering tones will only
            occur for syllables with glottal stop ``/ʔ/``.
        :keyword constrainToneCategories: if set to ``True`` *Yin tones* will
            only occur with voiceless and *Yang tones* only with voiced
            initials.
        """
        super(ShanghaineseIPAOperator, self).__init__(**options)

    @classmethod
    def getDefaultOptions(cls):
        options = super(ShanghaineseIPAOperator, cls).getDefaultOptions()
        options.update({'constrainEntering': False,
            'constrainToneCategories': False})

        return options

    def getTonalEntity(self, plainEntity, tone):
        # reimplement to work with variable tones
        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        return super(ShanghaineseIPAOperator, self).getTonalEntity(plainEntity,
            tone)

    def splitEntityTone(self, entity):
        # encapsulate parent class' method to work with variable tones
        plainEntity, tone \
            = super(ShanghaineseIPAOperator, self).splitEntityTone(entity)

        if not self.isToneValid(plainEntity, tone):
            raise InvalidEntityError(
                "Syllable '%s' can not occur with tone '%s'" \
                    % (plainEntity, str(tone)))

        return plainEntity, tone

    def isToneValid(self, plainEntity, tone):
        """
        Checks if the given plain entity and tone combination is valid.

        This method will always return ``True`` by default. If option
        ``'constrainEntering'`` is set entering tone are only accepted for
        syllables with glottal stop ``/ʔ/`. If option
        ``'constrainToneCategories'`` is set *Yin tones* will are only accepted
        with voiceless and *Yang tones* only with voiced initials.

        :type plainEntity: str
        :param plainEntity: entity without tonal information
        :type tone: str
        :param tone: tone
        :rtype: bool
        :return: ``True`` if given combination is valid, ``False`` otherwise
        """
        if tone not in self.getTones():
            raise InvalidEntityError(
                "Invalid tone information given for '%s': '%s'" \
                    % (plainEntity, str(tone)))
        if not self.constrainEntering and not self.constrainToneCategories:
            return True

        if plainEntity not in self._syllableData:
            raise InvalidEntityError("Invalid entity given for '%s'"
                % plainEntity)

        if (self.constrainEntering
            and ((tone in ('YinRu', 'YangRu')
                and 'G' not in self._syllableData[plainEntity])
                or (tone not in ('YinRu', 'YangRu')
                and 'G' in self._syllableData[plainEntity]))):
            return False

        if self.constrainToneCategories:
            if (tone in ('YangQu', 'YangRu')
                and 'U' in self._syllableData[plainEntity]):
                return False

            elif (tone in ('YinPing', 'YinQu', 'YinRu')
                and 'V' in self._syllableData[plainEntity]):
                return False

        return True

    @cachedmethod
    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. These
        entities will carry no tone mark.

        :rtype: set of str
        :return: set of supported syllables
        """
        table = self.db.tables['ShanghaineseIPASyllables']
        return frozenset(self.db.selectScalars(select([table.c.IPA])))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        :type plainSyllable: str
        :param plainSyllable: syllable in IPA without tone marks
        :rtype: tuple of str
        :return: tuple of syllable onset and rhyme
        :raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).
        """
        table = self.db.tables['ShanghaineseIPASyllables']
        entry = self.db.selectRow(
            select([table.c.IPAInitial, table.c.IPAFinal],
                table.c.IPA == plainSyllable))
        if not entry:
            raise InvalidEntityError("'%s' not a valid IPA form in this system'"
                % plainSyllable)
        return (entry[0], entry[1])

    @cachedproperty
    def _syllableData(self):
        """
        Table information on initial status voiced/unvoiced and glotal stop
        of final.
        """
        table = self.db.tables['ShanghaineseIPASyllables']
        return dict(self.db.selectRows(
            select([table.c.IPA, table.c.Flags])))
