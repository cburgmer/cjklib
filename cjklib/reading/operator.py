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
Provides L{ReadingOperator}s, classes to handle strings written in a character
reading.

Examples
========
Decompose a reading string in I{Gwoyeu Romatzyh} into single entities:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.decompose('"Hannshyue" .de mingcheng duey Jonggwo [...]', 'GR')
    ['"', 'Hann', 'shyue', '" ', '.de', ' ', 'ming', 'cheng', ' ', 'duey',
    ' ', 'Jong', 'gwo', ' [...]']

The same can be done by directly using the operator's instance:

    >>> from cjklib.reading import operator
    >>> cy = operator.CantoneseYaleOperator()
    >>> cy.decompose('gwóngjàuwá')
    [u'gw\xf3ng', u'j\xe0u', u'w\xe1']

Composing will reverse the process, using a I{Pinyin} string:

    >>> f.compose([u'xī', u'ān'], 'Pinyin')
    u"x\u012b'\u0101n"

For more complex operators, see L{PinyinOperator} or L{MandarinIPAOperator}.
"""
import re
import unicodedata
import copy

from cjklib.exception import (AmbiguousConversionError, DecompositionError,
    AmbiguousDecompositonError, InvalidEntityError, UnsupportedError)
from cjklib.dbconnector import DatabaseConnector

class ReadingOperator(object):
    """
    Defines an abstract operator on text written in a I{character reading}.

    The two basic methods are L{decompose()} and L{compose()}. L{decompose()}
    breaks down a text into the basic entities of that reading (additional non
    reading substrings are accepted though). L{compose()} joins these entities
    together again and applies formating rules needed by the reading.
    Additionally the method L{isReadingEntity()} is provided to check which of
    the strings returned by L{decompose()} are supported entities for the given
    reading.

    The methods L{getDefaultOptions()} and L{getOption()} provide means to
    handle the I{reading dialect}'s specific settings.

    The class itself can't be used directly, it has to be subclassed and its
    methods need to be extended.
    """
    READING_NAME = None
    """Unique name of reading"""

    def __init__(self, **options):
        """
        Creates an instance of the ReadingOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        """
        if 'dbConnectInst' in options:
            self.db = options['dbConnectInst']
        else:
            self.db = DatabaseConnector.getDBConnector()

        self.optionValue = {}
        defaultOptions = self.getDefaultOptions()
        for option in defaultOptions:
            if type(defaultOptions[option]) in [type(()), type([]), type({})]:
                self.optionValue[option] = copy.deepcopy(defaultOptions[option])
            else:
                self.optionValue[option] = defaultOptions[option]

    @classmethod
    def getDefaultOptions(cls):
        """
        Returns the reading operator's default options.

        The default implementation returns an empty dictionary. The keyword
        'dbConnectInst' is not regarded a configuration option of the operator
        and is thus not included in the dict returned.

        @rtype: dict
        @return: the reading operator's default options.
        """
        return {}

    def getOption(self, option):
        """
        Returns the value of the reading operator's option.

        @return: the value of the given reading operator's option.
        """
        return self.optionValue[option]

    def decompose(self, string):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each (exceptions possible).

        The given input string can contain other non reading characters, e.g.
        punctuation marks.

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        The default implementation will raise a NotImplementedError.

        @type string: str
        @param string: reading string
        @rtype: list of str
        @return: a list of basic entities of the input string
        @raise DecompositionError: if the string can not be decomposed.
        """
        raise NotImplementedError

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string.

        The default implementation will raise a NotImplementedError.

        @type readingEntities: list of str
        @param readingEntities: list of basic entities or other content
        @rtype: str
        @return: composed entities
        """
        raise NotImplementedError

    def isReadingEntity(self, entity):
        """
        Returns true if the given entity is recognised by the reading
        operator, i.e. it is a valid entity of the reading returned by
        L{decompose()}.

        The default implementation will raise a NotImplementedError.

        @type entity: str
        @param entity: entity to check
        @rtype: bool
        @return: true if string is an entity of the reading, false otherwise.
        """
        raise NotImplementedError


class RomanisationOperator(ReadingOperator):
    """
    Defines an abstract L{ReadingOperator} on text written in a I{romanisation},
    i.e. text written in the Latin alphabet or written in the Cyrillic alphabet.

    Additional to L{decompose()} provided by the class L{ReadingOperator} this
    class offers a method L{getDecompositions()} that returns several possible
    decompositions in an ambiguous case.

    This class itself can't be used directly, it has to be subclassed and
    extended.

    X{Decomposition}
    ================
    Transcriptions into the Latin alphabet generate the problem that syllable
    boundaries or boundaries of entities belonging to single Chinese characters
    aren't clear anymore once entities are grouped together.

    Therefore it is important to have methods at hand to separate this strings
    and to split them into single entities. This though cannot always be done
    in a clear and unambiguous way as several different decompositions might be
    possible thus leading to the general case of X{ambiguous decomposition}s.

    Many romanisations do provide a way to tackle this problem. Pinyin for
    example requires the use of an apostrophe (C{'}) when the reverse process
    of splitting the string into syllables gets ambiguous. The Wade-Giles
    romanisation in its strict implementation asks for a hyphen used between all
    syllables. The LSHK's Jyutping when written with tone marks will always be
    clearly decomposable.

    The method L{isStrictDecomposition()} can be implemented to check if one
    possible decomposition is the X{strict decomposition} offered by the
    romanisation's protocol. This method should guarantee that under all
    circumstances only one decomposed version will be regarded as strict.

    If no strict version is yielded and different decompositions exist an
    X{unambiguous decomposition} can not be made. These decompositions can be
    accessed through method L{getDecompositions()}, even in a cases where a
    strict decomposition exists.
    @todo Impl: Optimise decompose() as to incorporate segment() and prune the
        tree while it is created. Does this though yield significant
        improvement? Would at least be O(n).
    """
    readingEntityRegex = re.compile(u"([A-Za-z]+)")
    """Regular Expression for finding romanisation entities in input."""

    def __init__(self, **options):
        """
        Creates an instance of the RomanisationOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        @keyword case: if set to C{'lower'}/C{'upper'}, only lower/upper
            case will be supported, respectively, if set to C{'both'} both upper
            and lower case will be supported.
        """
        super(RomanisationOperator, self).__init__(**options)

        if 'strictSegmentation' in options:
            self.optionValue['strictSegmentation'] \
                = options['strictSegmentation']

        if 'case' in options:
            self.optionValue['case'] = options['case']

        self.syllableTable = None
        self.substringSet = None

    @classmethod
    def getDefaultOptions(cls):
        options = super(RomanisationOperator, cls).getDefaultOptions()
        options.update({'strictSegmentation': False, 'case': 'both'})

        return options

    def decompose(self, string):
        """
        Decomposes the given string into basic entities on a one-to-one mapping
        level to Chinese characters. Decomposing can be ambiguous and there are
        two assumptions made to solve this problem: If two subsequent entities
        together make up a longer valid entity, then the decomposition with the
        shorter entities can be disregarded. Furthermore it is assumed that the
        reading provides rules to mark entity borders and that these rules can
        be checked, so that the decomposition that abides by this rules will be
        prefered. This check is done by calling L{isStrictDecomposition()}.

        The given input string can contain other characters not supported by the
        reading, e.g. punctuation marks. The returned list then contains a mix
        of basic reading entities and other characters e.g. spaces and
        punctuation marks.

        @type string: str
        @param string: reading string
        @rtype: list of str
        @return: a list of basic entities of the input string
        @raise AmbiguousDecompositonError: if decomposition is ambiguous.
        @raise DecompositionError: if the given string has a wrong format.
        """
        decompositionParts = self.getDecompositionTree(string)

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
                    if not self._hasMergeableSyllables(decomposition):
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
                        raise AmbiguousDecompositonError("decomposition of '" \
                            + string + "' ambiguous: '" \
                            + ''.join(decomposition) + "'")

        return strictDecomposition

    def getDecompositionTree(self, string):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each for all possible decompositions and returns
        the possible decompositions as a lattice.

        @type string: str
        @param string: reading string
        @rtype: list
        @return: a list of all possible decompositions consisting of basic
            entities as a lattice construct.
        @raise DecompositionError: if the given string has a wrong format.
        """
        # break string into pieces with alphabet and non alphabet parts
        decompositionParts = []
        # get partial segmentations
        for part in self.readingEntityRegex.split(string):
            if part == '':
                continue
            if not self.readingEntityRegex.match(part):
                # non-reading entity
                decompositionParts.append([[part]])
            else:
                segmentations = self.segment(part)
                decompositionParts.append(segmentations)

        return decompositionParts

    def getDecompositions(self, string):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each for all possible decompositions. This method
        is a more general version of L{decompose()}.

        The returned list construction consists of two entity types: entities of
        the romanisation and other strings.

        @type string: str
        @param string: reading string
        @rtype: list of list of str
        @return: a list of all possible decompositions consisting of basic
            entities.
        @raise DecompositionError: if the given string has a wrong format.
        """
        decompositionParts = self.getDecompositionTree(string)
        # merge segmentations to decomposition
        decompCrossProd = self._crossProduct(decompositionParts)

        decompositionList = []
        for line in decompCrossProd:
            resultList = []
            for entry in line:
                resultList.extend(entry)
            decompositionList.append(resultList)

        return decompositionList

    def segment(self, string):
        """
        Takes a string written in the romanisation and returns the possible
        segmentations as a list of syllables.

        In contrast to L{decompose()} this method merely segments continuous
        entities of the romanisation. Characters not part of the romanisation
        will not be dealt with, this is the task of the more general decompose
        method.

        @type string: str
        @param string: reading string
        @rtype: list of list of str
        @return: a list of possible segmentations (several if ambiguous) into
            single syllables
        @raise DecompositionError: if the given string has an invalid format.
        """
        segmentationTree = self._recursiveSegmentation(string)
        if string != '' and len(segmentationTree) == 0:
            if self.getOption('strictSegmentation'):
                raise DecompositionError(u"Segmentation of '" + string \
                    + "' not possible or invalid syllable")
            else:
                return [[string]]
        resultList = []
        for entry in segmentationTree:
            resultList.extend(self._treeToList(entry))
        return resultList

    def _recursiveSegmentation(self, string):
        """
        Takes a string written in the romanisation and returns the possible
        segmentations as a tree of syllables.

        The tree is represented by tuples C{(syllable, subtree)}.

        @type string: str
        @param string: reading string
        @rtype: list of tuple
        @return: a tree of possible segmentations (if ambiguous) into single
            syllables
        """
        segmentationParts = []
        substringIndex = 1
        while substringIndex <= len(string) and \
            self._hasSyllableSubstring(string[0:substringIndex].lower()):
            syllable = string[0:substringIndex]
            if self.isReadingEntity(syllable):
                remaining = string[substringIndex:]
                if remaining != '':
                    remainingParts = self._recursiveSegmentation(remaining)
                    if remainingParts != []:
                        segmentationParts.append((syllable, remainingParts))
                else:
                    segmentationParts.append((syllable, None))
            substringIndex = substringIndex + 1
        return segmentationParts

    def _hasMergeableSyllables(self, decomposition):
        """
        Checks if the given decomposition has two or more following syllables
        which together make up a new syllable.

        Segmentation can give several results with some possible syllables being
        even further subdivided (e.g. I{tian} to I{ti'an} in Pinyin). These
        segmentations are only secondary and the segmentation with the longer
        syllables will be the one to take.

        @type decomposition: list of str
        @param decomposition: decomposed reading string
        @rtype: bool
        @return: True if following syllables make up a syllable
        """
        for startIndex in range(0, len(decomposition)-1):
            endIndex = startIndex + 2
            subDecomp = "".join(decomposition[startIndex:endIndex]).lower()
            while endIndex <= len(decomposition) and \
                self._hasSyllableSubstring(subDecomp):
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

        @type decomposition: list of str
        @param decomposition: decomposed reading string
        @rtype: bool
        @return: False, as this methods needs to be implemented by the sub class
        """
        return False

    def _hasSyllableSubstring(self, string):
        """
        Checks if the given string is a syllable supported by this romanisation
        or a substring of one.

        @type string: str
        @param string: romanisation syllable or substring
        @rtype: bool
        @return: true if this string is a substring of a syllable, false
            otherwise
        """
        if self.substringSet == None:
            # build index as called for the first time
            self.substringSet = set()
            for syllable in self.getReadingEntities():
                for i in range(len(syllable)):
                    self.substringSet.add(syllable[0:i+1])
        return string in self.substringSet

    def isReadingEntity(self, entity):
        """
        Returns true if the given entity is recognised by the romanisation
        operator, i.e. it is a valid entity of the reading returned by the
        segmentation method.

        Reading entities will be handled as being case insensitive.

        @type entity: str
        @param entity: entity to check
        @rtype: bool
        @return: C{True} if string is an entity of the reading, C{False}
            otherwise.
        """
        # check capitalisation
        if self.getOption('case') == 'lower' and entity.lower() != entity:
            return False
        elif self.getOption('case') == 'upper' and entity.upper() != entity:
            return False

        if self.syllableTable == None:
            # set used syllables
            self.syllableTable = self.getReadingEntities()
        return entity.lower() in self.syllableTable

    def getReadingEntities(self):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.
        The default implementation will raise a NotImplementedError.

        @rtype: set of str
        @return: set of supported syllables
        """
        raise NotImplementedError

    @staticmethod
    def _crossProduct(singleLists):
        """
        Calculates the cross product (aka Cartesian product) of sets given as
        lists.

        Example:
            >>> RomanisationOperator._crossProduct([['A', 'B'], [1, 2, 3]])
            [['A', 1], ['A', 2], ['A', 3], ['B', 1], ['B', 2], ['B', 3]]

        @type singleLists: list of list
        @param singleLists: a list of list entries containing various elements
        @rtype: list of list
        @return: the cross product of the given sets
        """
        # get repeat index for whole set
        lastRepeat = 1
        repeatSet = []
        for elem in singleLists:
            repeatSet.append(lastRepeat)
            lastRepeat = lastRepeat * len(elem)
        repeatEntry = []
        # get dimension of Cartesian product and dimensions of parts
        newListLength = 1
        for i in range(0, len(singleLists)):
            elem = singleLists[len(singleLists) - i - 1]
            repeatEntry.append(newListLength)
            newListLength = newListLength * len(elem)
        repeatEntry.reverse()
        # create product
        newList = [[] for i in range(0, newListLength)]
        lastSetLen = 1
        for i, listElem in enumerate(singleLists):
            for j in range(0, repeatSet[i]):
                for k, elem in enumerate(listElem):
                    for l in range(0, repeatEntry[i]):
                        newList[j * lastSetLen + k*repeatEntry[i] \
                            + l].append(elem)
            lastSetLen = repeatEntry[i]
        return newList

    @staticmethod
    def _treeToList(tupleTree):
        """
        Converts a tree to a list containing all full paths from root to leaf
        node.

        The tree is given by tuples C{(leaf node element, subtree)}.

        Example:
            >>> RomanisationOperator._treeToList(
            ...     ('A', [('B', None), ('C', [('D', None), ('E', None)])]))
            [['A', 'B'], ['A', 'C', 'D'], ['A', 'C', 'E']]

        @type tupleTree: tuple
        @param tupleTree: a tree realised through a tuple of a node and a
            subtree
        @rtype: list of list
        @return: a list of all paths contained by the given tree
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
    Provides an abstract L{ReadingOperator} for tonal languages for a reading
    based on a fixed set of reading entities.

    It provides two methods L{getTonalEntity()} and L{splitEntityTone()} to
    cope with tonal information in text.

    The class itself can't be used directly, it has to be subclassed and its
    methods need to be extended.
    """
    def __init__(self, **options):
        """
        Creates an instance of the TonalFixedEntityOperator.

        @param options: extra options
        """
        super(TonalFixedEntityOperator, self).__init__(**options)

        self.plainEntityTable = None

    def getTones(self):
        """
        Returns a set of tones supported by the reading. These tones don't
        necessarily reflect the tones of the underlying language but may defer
        to reflect notational or other features.

        The default implementation will raise a NotImplementedError.

        @rtype: list
        @return: list of supported tone marks.
        """
        raise NotImplementedError

    def getTonalEntity(self, plainEntity, tone):
        """
        Gets the entity with tone mark for the given plain entity and tone.

        The default implementation will raise a NotImplementedError.

        @type plainEntity: str
        @param plainEntity: entity without tonal information
        @param tone: tone
        @rtype: str
        @return: entity with appropriate tone
        @raise InvalidEntityError: if the entity is invalid.
        @raise UnsupportedError: if the operation is not supported for the given
            form.
        """
        raise NotImplementedError

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark (plain entity) and
        the entity's tone.

        The default implementation will raise a NotImplementedError.

        @type entity: str
        @param entity: entity with tonal information
        @rtype: tuple
        @return: plain entity without tone mark and entity's tone
        @raise InvalidEntityError: if the entity is invalid.
        @raise UnsupportedError: if the operation is not supported for the given
            form.
        """
        raise NotImplementedError

    def getReadingEntities(self):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.

        @rtype: list of str
        @return: list of supported syllables
        """
        syllableSet = set()
        for syllable in self.getPlainReadingEntities():
            for tone in self.getTones():
                syllableSet.add(self.getTonalEntity(syllable, tone))
        return syllableSet

    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. Different to
        L{getReadingEntities()} the entities will carry no tone mark.

        The default implementation will raise a NotImplementedError.

        @rtype: set of str
        @return: set of supported syllables
        """
        raise NotImplementedError

    def isPlainReadingEntity(self, entity):
        """
        Returns true if the given plain entity (without any tone mark) is
        recognised by the romanisation operator, i.e. it is a valid entity of
        the reading returned by the segmentation method.

        @type entity: str
        @param entity: entity to check
        @rtype: bool
        @return: C{True} if string is an entity of the reading, C{False}
            otherwise.
        """
        if self.plainEntityTable == None:
            # set used syllables
            self.plainEntityTable = self.getPlainReadingEntities()
        return entity in self.plainEntityTable

    def isReadingEntity(self, entity):
        # reimplement to keep memory footprint small
        # remove tone mark form and check plain entity
        try:
            plainEntity, _ = self.splitEntityTone(entity)
            return self.isPlainReadingEntity(plainEntity)
        except InvalidEntityError:
            return False



class TonalRomanisationOperator(RomanisationOperator, TonalFixedEntityOperator):
    """
    Provides an abstract L{RomanisationOperator} for tonal languages
    incorporating methods from L{TonalFixedEntityOperator}.

    It provides two methods L{getTonalEntity()} and L{splitEntityTone()} to
    cope with tonal information in text.

    The class itself can't be used directly, it has to be subclassed and its
    methods need to be extended.
    """
    def __init__(self, **options):
        """
        Creates an instance of the TonalRomanisationOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        """
        super(TonalRomanisationOperator, self).__init__(**options)

    def getReadingEntities(self):
        """
        Gets a set of all entities supported by the reading.

        The list is used in the segmentation process to find entity boundaries.

        @rtype: list of str
        @return: list of supported syllables
        """
        return TonalFixedEntityOperator.getReadingEntities(self)

    def isPlainReadingEntity(self, entity):
        """
        Returns true if the given plain entity (without any tone mark) is
        recognised by the romanisation operator, i.e. it is a valid entity of
        the reading returned by the segmentation method.

        Reading entities will be handled as being case insensitive.

        @type entity: str
        @param entity: entity to check
        @rtype: bool
        @return: C{True} if string is an entity of the reading, C{False}
            otherwise.
        """
        # check for special capitalisation
        if self.getOption('case') == 'lower' and entity.lower() != entity:
            return False
        elif self.getOption('case') == 'upper' and entity.upper() != entity:
            return False

        return TonalFixedEntityOperator.isPlainReadingEntity(self,
            entity.lower())

    def isReadingEntity(self, entity):
        return TonalFixedEntityOperator.isReadingEntity(self, entity)


class TonalIPAOperator(TonalFixedEntityOperator):
    u"""
    Defines an operator on strings of a tonal language written in the
    X{International Phonetic Alphabet} (X{IPA}).

    TonalIPAOperator does not supply the same closed set of syllables as
    other L{ReadingOperator}s as IPA provides different ways to represent
    pronunciation. Because of that a user defined IPA syllable will not easily
    map to another transcription system and thus only basic support is provided
    for this direction.

    Tones
    =====
    Tones in IPA can be expressed using different schemes. The following schemes
    are implemented here:
        - Numbers, tone numbers ,
        - ChaoDigits, numbers displaying the levels of Chao tone contours,
        - IPAToneBar, IPA modifying tone bar characters, e.g. ɛw˥˧,
        - Diacritics, diacritical marks and finally
        - None, no support for tone marks

    @todo Lang: Shed more light on representations of tones in IPA.
    @todo Fix:  Get all diacritics used in IPA as tones for L{TONE_MARK_REGEX}.
    """
    TONE_MARK_REGEX = {'Numbers': re.compile(r'(\d)$'),
        'ChaoDigits': re.compile(r'(12345+)$'),
        'IPAToneBar': re.compile(ur'([˥˦˧˨˩꜈꜉꜊꜋꜌]+)$'),
        'Diacritics': re.compile(ur'([\u0300\u0301\u0302\u0303\u030c]+)')
        }

    DEFAULT_TONE_MARK_TYPE = 'IPAToneBar'
    """Tone mark type to select by default."""

    TONES = []
    """List of tone names. Needs to be implemented in child class."""

    TONE_MARK_PREFER = {'Numbers': {}, 'ChaoDigits': {}, 'IPAToneBar': {},
        'Diacritics': {}}
    """
    Mapping of tone marks to tone name which will be preferred on ambiguous
    mappings. Needs to be implemented in child classes.
    """

    TONE_MARK_MAPPING = {'Numbers': {}, 'ChaoDigits': {}, 'IPAToneBar': {},
        'Diacritics': {}}
    """
    Mapping of tone names to tone mark for each tone mark type. Needs to be
    implemented in child classes.
    """

    def __init__(self, **options):
        """
        Creates an instance of the TonalIPAOperator.

        By default no tone marks will be shown.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword toneMarkType: type of tone marks, one out of C{'Numbers'},
            C{'ChaoDigits'}, C{'IPAToneBar'}, C{'Diacritics'}, C{'None'}
        @keyword missingToneMark: if set to C{'noinfo'} no tone information
            will be deduced when no tone mark is found (takes on value C{None}),
            if set to C{'ignore'} this entity will not be valid.
        """
        super(TonalIPAOperator, self).__init__(**options)

        if 'toneMarkType' in options:
            if options['toneMarkType'] not in ['Numbers', 'ChaoDigits',
                'IPAToneBar', 'Diacritics', 'None']:
                raise ValueError("Invalid option '" \
                    + str(options['toneMarkType']) \
                    + "' for keyword 'toneMarkType'")
            self.optionValue['toneMarkType'] = options['toneMarkType']

        # check if we have to be strict on tones, i.e. report missing tone info
        if 'missingToneMark' in options:
            if options['missingToneMark'] not in ['noinfo', 'ignore']:
                raise ValueError("Invalid option '" \
                    + str(options['missingToneMark']) \
                    + "' for keyword 'missingToneMark'")
            self.optionValue['missingToneMark'] = options['missingToneMark']

        self.toneMarkLookup = None

        # split regex
        self.splitRegex = re.compile('([\.\s]+)')

    @classmethod
    def getDefaultOptions(cls):
        options = super(TonalIPAOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': cls.DEFAULT_TONE_MARK_TYPE,
            'missingToneMark': 'noinfo', 'preferTone': cls.TONE_MARK_PREFER})

        return options

    def getTones(self):
        tones = self.TONES[:]
        if self.getOption('missingToneMark') == 'noinfo' \
            or self.getOption('toneMarkType') == 'None':
            tones.append(None)

        return tones

    def decompose(self, string):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each (exceptions possible).

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        Single syllables can only be found if distinguished by a period or
        whitespace, such as L{compose()} would return.

        @type string: str
        @param string: reading string
        @rtype: list of str
        @return: a list of basic entities of the input string
        """
        return self.splitRegex.split(string)

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string. IPA syllables are
        separated by a period.

        @type readingEntities: list of str
        @param readingEntities: list of basic entities or other content
        @rtype: str
        @return: composed entities
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
        I{Normalization Form C} (NFC, see
        U{http://www.unicode.org/reports/tr15/}).

        @type plainEntity: str
        @param plainEntity: entity without tonal information
        @type tone: str
        @param tone: tone
        @rtype: str
        @return: entity with appropriate tone
        @raise InvalidEntityError: if the entity is invalid.
        @todo Impl: Place diacritics on main vowel, derive from IPA
            representation.
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")
        if self.getOption('toneMarkType') == "None" or tone == None:
            entity = plainEntity
        else:
            entity = plainEntity \
                + self.TONE_MARK_MAPPING[self.getOption('toneMarkType')][tone]
        return unicodedata.normalize("NFC", entity)

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the name of the
        entity's tone.

        The plain entity returned will always be in Unicode's
        I{Normalization Form C} (NFC, see
        U{http://www.unicode.org/reports/tr15/}).

        @type entity: str
        @param entity: entity with tonal information
        @rtype: tuple
        @return: plain entity without tone mark and additionally the tone
        @raise InvalidEntityError: if the entity is invalid.
        """
        # get decomposed Unicode string, e.g. C{'â'} to C{'u\u0302'}
        entity = unicodedata.normalize("NFD", unicode(entity))

        toneMarkType = self.getOption('toneMarkType')
        if toneMarkType == 'None':
            return unicodedata.normalize("NFC", entity), None
        else:
            matchObj = self.TONE_MARK_REGEX[toneMarkType].search(entity)
            if matchObj:
                toneMark = matchObj.group(1)
                tone = self.getToneForToneMark(toneMark)

                # strip off tone mark
                plainEntity = entity.replace(toneMark, '')
                return unicodedata.normalize("NFC", plainEntity), tone
            elif self.getOption('missingToneMark') == 'noinfo':
                return unicodedata.normalize("NFC", entity), None

        raise InvalidEntityError("Invalid entity given for '" + entity + "'")

    def getToneForToneMark(self, toneMark):
        """
        Gets the tone for the given tone mark.

        @type toneMark: str
        @param toneMark: tone mark representation of the tone
        @rtype: str
        @return: tone
        @raise InvalidEntityError: if the toneMark does not exist.
        """
        if self.toneMarkLookup == None:
            toneMarkType = self.getOption('toneMarkType')
            # create lookup dict
            self.toneMarkLookup = {}
            for tone in self.getTones():
                if tone == None:
                    continue
                toneMark = self.TONE_MARK_MAPPING[toneMarkType][tone]
                if toneMark not in self.toneMarkLookup \
                    or (toneMark in self.TONE_MARK_PREFER[toneMarkType] \
                    and self.TONE_MARK_PREFER[toneMarkType][toneMark] \
                        == tone):
                    self.toneMarkLookup[toneMark] = tone

        if toneMark in self.toneMarkLookup:
            return self.toneMarkLookup[toneMark]
        else:
            raise InvalidEntityError("Invalid tone mark given with '" \
                + toneMark + "'")


class SimpleEntityOperator(ReadingOperator):
    """Provides an operator on readings with a single character per entity."""
    def decompose(self, string):
        readingEntities = []
        i = 0
        while i < len(string):
            # look for non-entity characters first
            oldIndex = i
            while i < len(string) and not self.isReadingEntity(string[i]):
                i = i + 1
            if oldIndex != i:
                readingEntities.append(string[oldIndex:i])
            # if we didn't reach the end of the input we have a entity char
            if i < len(string):
                readingEntities.append(string[i])
            i = i + 1
        return readingEntities

    def compose(self, readingEntities):
        return ''.join(readingEntities)

    def isReadingEntity(self, entity):
        raise NotImplemented()


class HangulOperator(SimpleEntityOperator):
    """Provides an operator on Korean text written in X{Hangul}."""
    READING_NAME = "Hangul"

    def isReadingEntity(self, entity):
        return (entity >= u'가') and (entity <= u'힣')


class HiraganaOperator(SimpleEntityOperator):
    """Provides an operator on Japanese text written in X{Hiragana}."""
    READING_NAME = "Hiragana"

    def isReadingEntity(self, entity):
        return (entity >= u'ぁ') and (entity <= u'ゟ')


class KatakanaOperator(SimpleEntityOperator):
    """Provides an operator on Japanese text written in X{Katakana}."""
    READING_NAME = "Katakana"

    def isReadingEntity(self, entity):
        return (entity >= u'゠') and (entity <= u'ヿ')


class KanaOperator(SimpleEntityOperator):
    """
    Provides an operator on Japanese text written in a mix of X{Hiragana} and
    X{Katakana}.
    """
    READING_NAME = "Kana"

    def isReadingEntity(self, entity):
        return ((entity >= u'ぁ') and (entity <= u'ヿ'))


class PinyinOperator(TonalRomanisationOperator):
    ur"""
    Provides an operator for the Mandarin romanisation X{Hanyu Pinyin}.
    It can be configured to cope with different representations (I{"dialects"})
    of X{Pinyin}. For conversion between different representations the
    L{PinyinDialectConverter} can be used.

    Features:
        - tones marked by either diacritics or numbers,
        - alternative representation of I{ü}-character,
        - correct placement of apostrophes,
        - guessing of input form (I{reading dialect}),
        - support for Erhua and
        - splitting of syllables into onset and rhyme.

    Apostrophes
    ===========
    Pinyin syllables need to be separated by an X{apostrophe} in case their
    decomposition will get ambiguous. A famous example might be the city
    I{Xi'an}, which if written I{xian} would be read as one syllable, meaning
    e.g. 'fresh'. Another example would be I{Chang'an} which could be read
    I{chan'gan} if no delimiter is used in at least one of both cases.

    Different rules exist where to place apostrophes. A simple yet sufficient
    rule is implemented in L{aeoApostropheRule()} which is used as default in
    this class. Syllables starting with one of the three vowels I{a}, I{e}, I{o}
    will be separated. Remember that vowels [i], [u], [y] are represented as
    I{yi}, I{wu}, I{yu} respectively, thus making syllable boundaries clear.
    L{compose()} will place apostrophes where required when composing the
    reading string.

    An alternative rule can be specified to the constructor passing a function
    as an option C{PinyinApostropheFunction}. A possible function could be a
    rule separating all syllables by an apostrophe thus simplifying the reading
    process for beginners.

    On decomposition of strings it is important to check which of the possibly
    several choices will be the one actually meant. E.g. syllable I{xian} given
    above should always be segmented into one syllable, solution I{xi'an} is not
    an option in this case. Therefore an alternative to L{aeoApostropheRule()}
    should make sure it guarantees proper decomposition, which is tested through
    L{isStrictDecomposition()}.

    Last but not least C{compose(decompose(string))} will only be the identity
    if apostrophes are applied properly according to the rule as wrongly
    placed apostrophes will be kept when composing. Use L{removeApostrophes()}
    to remove separating apostrophes.

    Example
    -------

        >>> def noToneApostropheRule(precedingEntity, followingEntity):
        ...     return precedingEntity and precedingEntity[0].isalpha() \
        ...         and not precedingEntity[-1].isdigit() \
        ...         and followingEntity[0].isalpha()
        ...
        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert('an3ma5mi5ba5ni2mou1', 'Pinyin', 'Pinyin',
        ...     sourceOptions={'toneMarkType': 'Numbers'},
        ...     targetOptions={'toneMarkType': 'Numbers',
        ...         'missingToneMark': 'fifth',
        ...         'PinyinApostropheFunction': noToneApostropheRule})
        u"an3ma'mi'ba'ni2mou1"

    R-colouring
    ===========
    The phenomenon X{Erhua} (兒化音/儿化音, Erhua yin), i.e. the X{r-colouring} of
    syllables, is found in the northern Chinese dialects and results from
    merging the formerly independent sound I{er} with the preceding syllable. In
    written form a word is followed by the character 兒/儿, e.g. 頭兒/头儿.

    In Pinyin the Erhua sound is quite often expressed by appending a single
    I{r} to the syllable of the character preceding 兒/儿, e.g. I{tóur} for
    頭兒/头儿, to stress the monosyllabic nature and in contrast to words like
    兒子/儿子 I{ér'zi} where 兒/儿 I{ér} constitutes a single syllable.

    For decomposing syllables in Pinyin it is thus important to decide if the
    I{r} marking r-colouring should be an entity on its own account stressing
    the representation in the character string with an own character or rather
    stressing the monosyllabic nature and being part of a syllable of the
    foregoing character. This can be configured once instantiation.

    Source
    ======
    - Yǐn Bīnyōng (尹斌庸), Mary Felley (傅曼丽): Chinese romanization:
        Pronunciation and Orthography (汉语拼音和正词法). Sinolingua, Beijing,
        1990, ISBN 7-80052-148-6, ISBN 0-8351-1930-0.

    @see:
        - Pinyin: U{http://www.pinyin.info/rules/where.html},
            U{http://www.pinyin.info/romanization/hanyu/apostrophes.html},
            U{http://www.pinyin.info/rules/initials_finals.html}
        - Erhua sound: U{http://en.wikipedia.org/wiki/Erhua}

    @todo Impl: ISO 7098 asks for conversion of C{。、·「」} to C{.,-«»}. What
        about C{，？《》：－}? Implement a method for conversion to be optionally
        used.
    @todo Impl: Strict testing of tone mark placement. Currently it doesn't
        matter where tones are placed. All combinations are recognised.
    @todo Impl: Special marker for neutral tone: 'mȧ' (u'm\u0227', reported by
        Ching-song Gene Hsiao: A Manual of Transcription Systems For Chinese,
        中文拼音手册. Far Eastern Publications, Yale University, New Haven,
        Connecticut, 1985, ISBN 0-88710-141-0.), and '·ma' (u'\xb7ma', check!:
        现代汉语词典（第5版）[Xiàndài Hànyǔ Cídiǎn 5. Edition]. 商务印书馆
        [Shāngwù Yìnshūguǎn], Beijing, 2005, ISBN 7-100-04385-9.)
    """
    READING_NAME = 'Pinyin'

    TONEMARK_VOWELS = [u'a', u'e', u'i', u'o', u'u', u'ü', u'n', u'm', u'r',
        u'ê']
    """
    List of characters of the nucleus possibly carrying the tone mark. I{n} is
    included in standalone syllables I{n} and I{ng}. I{r} is used for supporting
    I{Erhua} in a two syllable form.
    """
    TONEMARK_MAP = {u'\u0304': 1, u'\u0301': 2, u'\u030c': 3, u'\u0300': 4}
    """
    Mapping of I{Combining Diacritical Marks} to their Pinyin tone index.

    @see:
        - The Unicode Consortium: The Unicode Standard, Version 5.0.0,
            Chapter 7, European Alphabetic Scripts, 7.9 Combining Marks,
            defined by: The Unicode Standard, Version 5.0 (Boston, MA,
            Addison-Wesley, 2007. ISBN 0-321-48091-0),
            U{http://www.unicode.org/versions/Unicode5.0.0/}
        - Unicode: X{Combining Diacritical Marks}, Range: 0300-036F:
            U{http://www.unicode.org/charts/PDF/U0300.pdf}
        - Unicode: FAQ - Characters and Combining Marks:
            U{http://unicode.org/faq/char_combmark.html}
    """

    PINYIN_SOUND_REGEX \
        = re.compile(u'(?i)^([^aeiuoü]*)([aeiuoü]*)([^aeiuoü]*)$')
    """
    Regular Expression matching onset, nucleus and coda. Syllables 'n', 'ng',
    'r' (for Erhua) and 'ê' have to be handled separately.
    """
    toneMarkRegex = re.compile(u'[' + re.escape(''.join(TONEMARK_MAP.keys())) \
        + ']')
    """Regular Expression matching the Pinyin tone marks."""
    tonemarkMapReverse = dict([(TONEMARK_MAP[mark], mark) \
        for mark in TONEMARK_MAP.keys()])
    del mark
    """Reverse lookup of tone marks for tones provided by TONEMARK_MAP."""

    def __init__(self, **options):
        u"""
        Creates an instance of the PinyinOperator.

        The class instance can be configured by different optional options given
        as keywords.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        @keyword toneMarkType: if set to C{'Diacritics'} tones will be marked
            using diacritic marks, if set to C{'Numbers'} appended numbers from
            1 to 5 will be used to mark tones, if set to C{'None'} no tone marks
            will be used and no tonal information will be supplied at all.
        @keyword missingToneMark: if set to C{'fifth'} no tone mark is set to
            indicate the fifth tone (I{qingsheng}, e.g. C{'wo3men'} stands for
            C{'wo3men5'}), if set to C{'noinfo'}, no tone information will be
            deduced when no tone mark is found (takes on value C{None}), if set
            to C{'ignore'} this entity will not be valid and for segmentation
            the behaviour defined by C{'strictSegmentation'} will take affect.
            This option is only valid for the tone mark type C{'Numbers'}.
        @keyword yVowel: a character (or string) that is taken as alternative
            for I{ü} which depicts (among others) the close front rounded vowel
            [y] (IPA) in Pinyin and includes an umlaut. Changes forms of
            syllables I{nü, nüe, lü, lüe}. This option is not valid for the
            tone mark type C{'Diacritics'}.
        @keyword PinyinApostrophe: an alternate apostrophe that is taken instead
            of the default one.
        @keyword PinyinApostropheFunction: a function that indicates when a
            syllable combination needs to be split by an I{apostrophe}, see
            L{aeoApostropheRule()} for the default implementation.
        @keyword Erhua: if set to C{'ignore'} no special support will be
            provided for retroflex -r at syllable end (I{Erhua}), i.e. I{zher}
            will raise an exception. If set to C{'twoSyllables'} syllables with
            an append r are given/will be segmented into two syllables, the -r
            suffix making up one syllable itself as C{'r'}. If set to
            C{'oneSyllable'} syllables with an appended r are given/will be
            segmented into one syllable only.
        """
        super(PinyinOperator, self).__init__(**options)

        # check which tone marks to use
        if 'toneMarkType' in options:
            if options['toneMarkType'] not in ['Diacritics', 'Numbers', 'None']:
                raise ValueError("Invalid option '" \
                    + str(options['toneMarkType']) \
                    + "' for keyword 'toneMarkType'")
            self.optionValue['toneMarkType'] = options['toneMarkType']

        # check if we have to be strict on tones, i.e. report missing tone info
        if 'missingToneMark' in options:
            if self.getOption('toneMarkType') != 'Numbers':
                raise ValueError("keyword 'missingToneMark' is only valid if" \
                    + " tone mark type is set to 'Numbers'")

            if options['missingToneMark'] not in ['fifth', 'noinfo', 'ignore']:
                raise ValueError("Invalid option '" \
                    + str(options['missingToneMark']) \
                    + "' for keyword 'missingToneMark'")
            self.optionValue['missingToneMark'] = options['missingToneMark']

        # set alternative ü vowel if given
        if 'yVowel' in options:
            if self.getOption('toneMarkType') == 'Diacritics' \
                and options['yVowel'] != u'ü':
                raise ValueError("keyword 'yVowel' is not valid for tone mark" \
                    + " type 'Diacritics'")

            self.optionValue['yVowel'] = options['yVowel']

        # set alternative apostrophe if given
        if 'PinyinApostrophe' in options:
            self.optionValue['PinyinApostrophe'] = options['PinyinApostrophe']

        # set apostrophe function if given
        if 'PinyinApostropheFunction' in options:
            self.optionValue['PinyinApostropheFunction'] \
                = options['PinyinApostropheFunction']

        # check if we support Erhua
        if 'Erhua' in options:
            if options['Erhua'] not in ['ignore', 'twoSyllables',
                'oneSyllable']:
                raise ValueError("Invalid option '" + str(options['Erhua']) \
                    + "' for keyword 'Erhua'")
            self.optionValue['Erhua'] = options['Erhua']

        # set split regular expression, works for all 3 main dialects, get at
        #   least the whole alphabet to have a conservative recognition
        self.readingEntityRegex = re.compile(u'(?i)((?:' \
            + '|'.join([re.escape(v) for v in self._getDiacriticVowels()]) \
            + '|' + re.escape(self.getOption('yVowel')) \
            + u'|[a-zêü])+[12345]?)')

    @classmethod
    def getDefaultOptions(cls):
        options = super(PinyinOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'Diacritics',
            'missingToneMark': 'noinfo', 'yVowel': u'ü',
            'PinyinApostrophe': "'", 'Erhua': 'twoSyllables',
            'PinyinApostropheFunction': cls.aeoApostropheRule})

        return options

    @staticmethod
    def _getDiacriticVowels():
        u"""
        Gets a list of Pinyin vowels with diacritical marks for tones.

        The alternative for vowel ü does not need diacritical forms as the
        standard form doesn't allow changing the vowel.

        @rtype: list of str
        @return: list of Pinyin vowels with diacritical marks
        """
        vowelList = []
        for vowel in PinyinOperator.TONEMARK_VOWELS:
            for mark in PinyinOperator.TONEMARK_MAP.keys():
                vowelList.append(unicodedata.normalize("NFC", vowel + mark))
        return vowelList

    @classmethod
    def guessReadingDialect(cls, string, includeToneless=False):
        u"""
        Takes a string written in Pinyin and guesses the reading dialect.

        The basic options C{'toneMarkType'}, C{'yVowel'} and C{'Erhua'} are
        guessed. Unless C{'includeToneless'} is set to C{True} only the
        tone mark types C{'Diacritics'} and C{'Numbers'} are considered as the
        latter one can also represent the state of missing tones. Strings tested
        for C{'yVowel'} are C{ü}, C{v} and C{u:}. C{'Erhua'} is set to
        C{'twoSyllables'} by default and only tested when C{'toneMarkType'} is
        assumed to be set to C{'Numbers'}.

        @type string: str
        @param string: Pinyin string
        @rtype: dict
        @return: dictionary of basic keyword settings
        """
        Y_VOWEL_LIST = [u'ü', 'v', 'u:']
        APOSTROPHE_LIST = ["'", u'’', u'´', u'‘', u'`', u'ʼ', u'ˈ', u'′', u'ʻ']
        readingStr = unicodedata.normalize("NFC", unicode(string))

        diacriticVowels = PinyinOperator._getDiacriticVowels()
        # split regex for all dialect forms
        entities = re.findall(u'(?i)((?:' + '|'.join(diacriticVowels) \
            + '|'.join(Y_VOWEL_LIST) + u'|[a-uw-zê])+[12345]?)', readingStr)

        # guess one of main dialects: tone mark type
        diacriticEntityCount = 0
        numberEntityCount = 0
        for entity in entities:
            # take entity (which can be several connected syllables) and check
            if entity[-1] in '12345':
                numberEntityCount = numberEntityCount + 1
            else:
                for vowel in diacriticVowels:
                    if vowel in entity:
                        diacriticEntityCount = diacriticEntityCount + 1
                        break
        # compare statistics
        if includeToneless \
            and (1.0 * max(diacriticEntityCount, numberEntityCount) \
                / len(entities)) < 0.1:
            # less than 1/10 units carry some possible tone mark, so decide
            #   for toneless
            toneMarkType = 'None'
        else:
            if diacriticEntityCount > numberEntityCount:
                toneMarkType = 'Diacritics'
            else:
                toneMarkType = 'Numbers'

        # guess ü vowel
        if toneMarkType == 'Diacritics':
            yVowel = u'ü'
        else:
            for vowel in Y_VOWEL_LIST:
                if vowel in readingStr:
                    yVowel = vowel
                    break
            else:
                yVowel = u'ü'

        # guess apostrophe vowel
        for apostrophe in APOSTROPHE_LIST:
            if apostrophe in readingStr:
                PinyinApostrophe = apostrophe
                break
        else:
            PinyinApostrophe = "'"

        # guess Erhua
        Erhua = 'twoSyllables'
        if toneMarkType == 'Numbers':
            lastIndex = 0
            while lastIndex != -1:
                lastIndex = readingStr.find('r', lastIndex+1)
                if lastIndex > 1:
                    if len(readingStr) > lastIndex + 1 \
                        and readingStr[lastIndex + 1] in '12345':
                        if readingStr[lastIndex - 1] in '12345':
                            # found a preceding number that should be a tone
                            #   mark for another syllable, thus r5 is isolated
                            break
                        else:
                            # found trailing r
                            Erhua = 'oneSyllable'

        return {'toneMarkType': toneMarkType, 'yVowel': yVowel,
            'PinyinApostrophe': PinyinApostrophe, 'Erhua': Erhua}

    def getTones(self):
        tones = range(1, 6)
        if self.getOption('toneMarkType') == 'None' \
            or (self.getOption('missingToneMark') == 'noinfo' \
            and self.getOption('toneMarkType') == 'Numbers'):
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string. Applies an
        apostrophe between syllables if needed using default implementation
        L{aeoApostropheRule()}.

        @type readingEntities: list of str
        @param readingEntities: list of basic syllables or other content
        @rtype: str
        @return: composed entities
        """
        newReadingEntities = []
        precedingEntity = None
        for entity in readingEntities:
            if self.getOption('PinyinApostropheFunction')(self, precedingEntity,
                entity):
                newReadingEntities.append(self.getOption('PinyinApostrophe'))

            newReadingEntities.append(entity)
            precedingEntity = entity
        return ''.join(newReadingEntities)

    def removeApostrophes(self, readingEntities):
        """
        Removes apostrophes between two syllables for a given decomposition.

        @type readingEntities: list of str
        @param readingEntities: list of basic syllables or other content
        @rtype: list of str
        @return: the given entity list without separating apostrophes
        """
        if len(readingEntities) == 0:
            return []
        elif len(readingEntities) > 2 \
            and readingEntities[1] == self.getOption('PinyinApostrophe') \
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

    def aeoApostropheRule(self, precedingEntity, followingEntity):
        """
        Checks if the given entities need to be separated by an apostrophe.

        Returns true for syllables starting with one of the three vowels I{a},
        I{e}, I{o} having a preceding syllable. Additionally forms I{n} and
        I{ng} are separated from preceding syllables. Furthermore corner case
        I{e'r} will handled to distinguish from I{er}.

        This function serves as the default apostrophe rule.

        @type precedingEntity: str
        @param precedingEntity: the preceding syllable or any other content
        @type followingEntity: str
        @param followingEntity: the following syllable or any other content
        @rtype: bool
        @return: true if the syllables need to be separated, false otherwise
        """
        # if both following entities are syllables they have to be separated if
        # the following syllable's first character is one of the vowels a, e, o,
        # or the syllable is n or ng
        if precedingEntity and self.isReadingEntity(precedingEntity) \
            and self.isReadingEntity(followingEntity):
                plainSyllable, tone = self.splitEntityTone(followingEntity)

                # take care of corner case Erhua form e'r, that needs to be
                #   distinguished from er
                if plainSyllable == 'r':
                    precedingPlainSyllable, _ \
                        = self.splitEntityTone(precedingEntity)
                    return precedingPlainSyllable == 'e'

                return plainSyllable[0] in ['a', 'e', 'o'] \
                    or plainSyllable in ['n', 'ng', 'nr', 'ngr']
        return False

    def isStrictDecomposition(self, readingEntities):
        """
        Checks if the given decomposition follows the Pinyin format
        strictly for unambiguous decomposition: syllables have to be preceded by
        an apostrophe if the decomposition would be ambiguous otherwise.

        The function stored given as option C{'PinyinApostropheFunction'} is
        used to check if a apostrophe should have been placed.

        @type readingEntities: list of str
        @param readingEntities: decomposed reading string
        @rtype: bool
        @return: true if decomposition is strict, false otherwise
        """
        precedingEntity = None
        for entity in readingEntities:
            if self.isReadingEntity(entity):
                # Pinyin syllable
                if self.getOption('PinyinApostropheFunction')(self,
                    precedingEntity, entity):
                    return False

                precedingEntity = entity
            else:
                # other content, treat next entity as first (start)
                precedingEntity = None

        return True

    def getTonalEntity(self, plainEntity, tone):
        # get normalised Unicode string, e.g. C{'e\u0302'} to C{'ê'}
        plainEntity = unicodedata.normalize("NFC", unicode(plainEntity))

        if tone != None:
            tone = int(tone)
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")

        if self.getOption('toneMarkType') == 'None':
            return plainEntity

        elif self.getOption('toneMarkType') == 'Numbers':
            if tone == None or (tone == 5 \
                and self.getOption('missingToneMark') == 'fifth'):
                return plainEntity
            else:
                return plainEntity + str(tone)

        elif self.getOption('toneMarkType') == 'Diacritics':
            # split syllable into onset, nucleus and coda, handle nasal and ê
            #   syllables independently
            if plainEntity.lower() in ['n', 'ng', 'm', 'r', u'ê', 'nr', 'ngr',
                'mr', u'êr']:
                onset, nucleus, coda = ('', plainEntity[0], plainEntity[1:])
            elif plainEntity.lower() in ['hm', 'hng', 'hmr', 'hngr']:
                onset, nucleus, coda = (plainEntity[0], plainEntity[1],
                    plainEntity[2:])
            else:
                matchObj = self.PINYIN_SOUND_REGEX.match(plainEntity)
                onset, nucleus, coda = matchObj.group(1, 2, 3)
            if not nucleus:
                raise InvalidEntityError("no nucleus found for '" \
                    + plainEntity + "'")
            # place tone mark
            tonalNucleus = self._placeNucleusToneMark(nucleus, tone)
            return onset + tonalNucleus + coda

    def _placeNucleusToneMark(self, nucleus, tone):
        """
        Places a tone mark on the given syllable nucleus according to the rules
        of the Pinyin standard.

        @see: Pinyin.info - Where do the tone marks go?,
            U{http://www.pinyin.info/rules/where.html}.

        @type nucleus: str
        @param nucleus: syllable nucleus
        @type tone: int
        @param tone: tone index (starting with 1)
        @rtype: str
        @return: nucleus with appropriate tone
        """
        # only tone mark to place for tones 0 - 3
        if tone != 5:
            if len(nucleus) == 1:
                # only one character in nucleus, place tone mark there
                tonalNucleus = nucleus + self.tonemarkMapReverse[tone]
            elif nucleus[0].lower() in ('a', 'e', 'o'):
                # if several vowels place on a, e, o...
                tonalNucleus = nucleus[0] + self.tonemarkMapReverse[tone] \
                    + nucleus[1:]
            else:
                # ...otherwise on second vowel (see Pinyin rules)
                tonalNucleus = nucleus[0] + nucleus[1] \
                    + self.tonemarkMapReverse[tone] + nucleus[2:]
        else:
            tonalNucleus = nucleus
        # get normalised Unicode string,
        return unicodedata.normalize("NFC", tonalNucleus)

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the
        entity's tone index.

        The plain entity returned will always be in Unicode's
        I{Normalization Form C} (NFC, see
        U{http://www.unicode.org/reports/tr15/}).

        @type entity: str
        @param entity: entity with tonal information
        @rtype: tuple
        @return: plain entity without tone mark and entity's tone index
            (starting with 1)
        """
        # get decomposed Unicode string, e.g. C{'ū'} to C{'u\u0304'}
        entity = unicodedata.normalize("NFD", unicode(entity))
        if self.getOption('toneMarkType') == 'None':
            plainEntity = entity
            tone = None

        elif self.getOption('toneMarkType') == 'Numbers':
            matchObj = re.search(u"[12345]$", entity)
            if matchObj:
                plainEntity = entity[0:len(entity)-1]
                tone = int(matchObj.group(0))
            else:
                if self.getOption('missingToneMark') == 'fifth':
                    plainEntity = entity
                    tone = 5
                elif self.getOption('missingToneMark') == 'ignore':
                    raise InvalidEntityError("No tone information given for '" \
                        + entity + "'")
                else:
                    plainEntity = entity
                    tone = None

        elif self.getOption('toneMarkType') == 'Diacritics':
            # find character with tone marker
            matchObj = self.toneMarkRegex.search(entity)
            if matchObj:
                diacriticalMark = matchObj.group(0)
                tone = self.TONEMARK_MAP[diacriticalMark]
                # strip off diacritical mark
                plainEntity = entity.replace(diacriticalMark, '')
            else:
                # fifth tone doesn't have any marker
                plainEntity = entity
                tone = 5
        # compose Unicode string (used for ê) and return with tone
        return unicodedata.normalize("NFC", plainEntity), tone

    def getPlainReadingEntities(self):
        u"""
        Gets the list of plain entities supported by this reading. Different to
        L{getReadingEntities()} the entities will carry no tone mark.

        Depending on the type of Erhua support either additional syllables with
        an ending -r are added, or a single I{r} is included. The user specified
        character for vowel I{ü} will be used.

        @rtype: set of str
        @return: set of supported syllables
        """
        # set used syllables
        plainSyllables = set(self.db.selectSoleValue("PinyinSyllables",
            "Pinyin"))
        # support for Erhua if needed
        if self.getOption('Erhua') == 'twoSyllables':
            # single 'r' for patterns like 'tóur'
            plainSyllables.add('r')
        elif self.getOption('Erhua') == 'oneSyllable':
            # add a -r form for all syllables except e and er
            for syllable in plainSyllables.copy():
                if syllable not in ['e', 'er']:
                    plainSyllables.add(syllable + 'r')

        # add alternative forms for replacement of ü
        if self.getOption('yVowel') != u'ü':
            for syllable in plainSyllables.copy():
                if syllable.find(u'ü') != -1:
                    syllable = syllable.replace(u'ü', self.getOption('yVowel'))
                    if syllable in plainSyllables:
                        # check if through conversion we collide with an already
                        #   existing syllable
                        raise ValueError("syllable '" + syllable \
                            + "' included more than once, " \
                            + u"probably bad substitute for 'ü'")
                    plainSyllables.add(syllable)
        return plainSyllables

    def getReadingEntities(self):
        # overwrite default implementation to specify a special tone mark for
        #   syllable 'r' used to support two syllable Erhua.
        syllables = self.getPlainReadingEntities()
        syllableSet = set()
        for syllable in syllables:
            if syllable == 'r':
                # r is included to support Erhua and is marked with the
                #   fifth tone as it is not pronounced separetly.
                tones = [5]
                if None in self.getTones():
                    tones.append(None)
            else:
                tones = self.getTones()
            # check if we accept syllables without tone mark
            for tone in tones:
                syllableSet.add(self.getTonalEntity(syllable, tone))
        return syllableSet

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        Pinyin can't be separated into onset and rhyme clearly within its own
        system. There are syllables with same finals written differently (e.g.
        I{wei} and I{dui} both ending in a final that can be described by
        I{uei}) and reduction of vowels (same example: I{dui} which is
        pronounced with vowels I{uei}). This method will use three forms not
        found as substrings in Pinyin (I{uei}, {uen} and I{iou}) and substitutes
        (pseudo) initials I{w} and I{y} with its vowel equivalents.

        Furthermore final I{i} will be distinguished in three forms given by
        the following three examples: I{yi}, I{zhi} and I{zi} to express
        phonological difference.

        @type plainSyllable: str
        @param plainSyllable: syllable without tone marks
        @rtype: tuple of str
        @return: tuple of entity onset and rhyme
        @raise InvalidEntityError: if the entity is invalid.
        @raise UnsupportedError: for entity I{r} when Erhua is handled as
            separate entity.
        """
        erhuaForm = False
        if self.getOption('Erhua') == 'oneSyllable' \
            and plainSyllable.endswith('r') and plainSyllable != 'er':
                plainSyllable = plainSyllable[:-1]
                erhuaForm = True

        elif plainSyllable == 'r' and self.getOption('Erhua') == 'twoSyllables':
            raise UnsupportedError("Not supported for '" + plainSyllable + "'")

        entry = self.db.selectSingleEntry("PinyinInitialFinal",
            ["PinyinInitial", "PinyinFinal"], {"Pinyin": plainSyllable.lower()})
        if not entry:
            raise InvalidEntityError("'" + plainSyllable \
                + "' not a valid plain Pinyin syllable'")

        if erhuaForm:
            return (entry[0], entry[1] + 'r')
        else:
            return (entry[0], entry[1])


class WadeGilesOperator(TonalRomanisationOperator):
    u"""
    Provides an operator for the Mandarin X{Wade-Giles} romanisation.

    Features:
        - tones marked by either standard numbers or subscripts,
        - configurable apostrophe for marking aspiration and
        - placement of hyphens between syllables.

    @todo Lang: Get a good source for the syllables used. See also
        L{PinyinWadeGilesConverter}.
    @todo Lang: Respect mangled Wade-Giles writings. Possible steps: a)
        Warn/Error on syllables which are ambiguous when asume apostrophe are
        omitted. b) 'hsu' is no valid syllable but can be viewed as 'hsü'.
        Compare to different 'implementations' of the Wade-Giles romanisation.
    """
    READING_NAME = 'WadeGiles'

    DB_ASPIRATION_APOSTROPHE = u"‘"
    """Default apostrophe used by Wade-Giles syllable data in database."""

    TO_SUPERSCRIPT = {1: u'¹', 2: u'²', 3: u'³', 4: u'⁴', 5: u'⁵'}
    """Mapping of tone numbers to superscript numbers."""
    FROM_SUPERSCRIPT = dict([(value, key) \
        for key, value in TO_SUPERSCRIPT.iteritems()])
    """Mapping of superscript numbers to tone numbers."""
    del value
    del key

    def __init__(self, **options):
        """
        Creates an instance of the WadeGilesOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        @keyword WadeGilesApostrophe: an alternate apostrophe that is taken
            instead of the default one.
        @keyword toneMarkType: if set to C{'Numbers'} appended numbers from 1 to
            5 will be used to mark tones, if set to C{'SuperscriptNumbers'}
            appended superscript numbers from 1 to 5 will be used to mark tones,
            if set to C{'None'} no tone marks will be used and no tonal
            information will be supplied at all.
        @keyword missingToneMark: if set to C{'fifth'} no tone mark is set to
            indicate the fifth tone (I{qingsheng}, e.g. C{'tsan2-men'} stands
            for C{'tsan2-men5'}), if set to C{'noinfo'}, no tone information
            will be deduced when no tone mark is found (takes on value C{None}),
            if set to C{'ignore'} this entity will not be valid and for
            segmentation the behaviour defined by C{'strictSegmentation'} will
            take affect.
        """
        super(WadeGilesOperator, self).__init__(**options)
        # set alternate apostrophe if given
        if 'WadeGilesApostrophe' in options:
            self.optionValue['WadeGilesApostrophe'] \
                 = options['WadeGilesApostrophe']
        self.readingEntityRegex = re.compile(u"((?:" \
            + re.escape(self.getOption('WadeGilesApostrophe')) \
            + u"|[A-ZÜa-zü])+[12345¹²³⁴⁵]?)")

        # check which tone marks to use
        if 'toneMarkType' in options:
            if options['toneMarkType'] not in ['Numbers', 'SuperscriptNumbers',
                'None']:
                raise ValueError("Invalid option '" \
                    + str(options['toneMarkType']) \
                    + "' for keyword 'toneMarkType'")
            self.optionValue['toneMarkType'] = options['toneMarkType']

        # check behaviour on missing tone info
        if 'missingToneMark' in options:
            if self.getOption('toneMarkType') not in ['Numbers',
                'SuperscriptNumbers']:
                raise ValueError("keyword 'missingToneMark' is only valid if" \
                    + " tone mark type is set to 'Numbers' or " \
                    + "'SuperscriptNumbers'")

            if options['missingToneMark'] not in ['fifth', 'noinfo', 'ignore']:
                raise ValueError("Invalid option '" \
                    + str(options['missingToneMark']) \
                    + "' for keyword 'missingToneMark'")
            self.optionValue['missingToneMark'] = options['missingToneMark']

    @classmethod
    def getDefaultOptions(cls):
        options = super(WadeGilesOperator, cls).getDefaultOptions()
        options.update({
            'WadeGilesApostrophe': WadeGilesOperator.DB_ASPIRATION_APOSTROPHE,
            'toneMarkType': 'Numbers', 'missingToneMark': u'noinfo'})

        return options

    def getTones(self):
        if self.getOption('missingToneMark') == 'fifth':
            tones = [1, 2, 3, 4, None]
        else:
            tones = range(1, 6)
            if self.getOption('toneMarkType') == 'None' \
                or self.getOption('missingToneMark') == 'noinfo':
                tones.append(None)
        return tones

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string by applying a
        hyphen between syllables.

        @type readingEntities: list of str
        @param readingEntities: list of basic syllables or other content
        @rtype: str
        @return: composed entities
        """
        newReadingEntities = []
        precedingEntity = None
        for entity in readingEntities:
            # check if we have to syllables
            if precedingEntity and self.isReadingEntity(precedingEntity) and \
                self.isReadingEntity(entity):
                # syllables are separated by a hyphen in the strict
                #   interpretation of Wade-Giles
                newReadingEntities.append("-")
            newReadingEntities.append(entity)
            precedingEntity = entity
        return ''.join(newReadingEntities)

    def removeHyphens(self, readingEntities):
        """
        Removes hyphens between two syllables for a given decomposition.

        @type readingEntities: list of str
        @param readingEntities: list of basic syllables or other content
        @rtype: list of str
        @return: the given entity list without separating hyphens
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
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")

        if self.getOption('toneMarkType') == 'None':
            return plainEntity

        if tone == None or (tone == 5 \
            and self.getOption('missingToneMark') == 'fifth'):
            return plainEntity
        else:
            if self.getOption('toneMarkType') == 'Numbers':
                return plainEntity + str(tone)
            elif self.getOption('toneMarkType') == 'SuperscriptNumbers':
                return plainEntity + self.TO_SUPERSCRIPT[tone]
        assert False

    def splitEntityTone(self, entity):
        if self.getOption('toneMarkType') == 'None':
            plainEntity = entity
            tone = None

        else:
            tone = None
            if self.getOption('toneMarkType') == 'Numbers':
                matchObj = re.search(u"[12345]$", entity)
                if matchObj:
                    tone = int(matchObj.group(0))
            elif self.getOption('toneMarkType') == 'SuperscriptNumbers':
                matchObj = re.search(u"[¹²³⁴⁵]$", entity)
                if matchObj:
                    tone = self.FROM_SUPERSCRIPT[matchObj.group(0)]

            if tone:
                plainEntity = entity[0:len(entity)-1]
            else:
                if self.getOption('missingToneMark') == 'fifth':
                    plainEntity = entity
                    tone = 5
                elif self.getOption('missingToneMark') == 'ignore':
                    raise InvalidEntityError("No tone information given for '" \
                        + entity + "'")
                else:
                    plainEntity = entity

        return plainEntity, tone

    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. Different to
        L{getReadingEntities()} the entities will carry no tone mark.

        Syllables will use the user specified apostrophe to mark aspiration.

        @rtype: set of str
        @return: set of supported syllables
        """
        plainSyllables = set(self.db.selectSoleValue("WadeGilesSyllables",
            "WadeGiles"))
        # use selected apostrophe
        if self.getOption('WadeGilesApostrophe') \
            == self.DB_ASPIRATION_APOSTROPHE:
            return plainSyllables
        else:
            translatedSyllables = set()
            for syllable in plainSyllables:
                syllable = syllable.replace(self.DB_ASPIRATION_APOSTROPHE,
                    self.getOption('WadeGilesApostrophe'))
                translatedSyllables.add(syllable)
            return translatedSyllables


class GROperator(TonalRomanisationOperator):
    u"""
    Provides an operator for the Mandarin X{Gwoyeu Romatzyh} romanisation.

    Features:
        - support of abbreviated forms (zh, j, g),
        - conversion of abbreviated forms to full forms,
        - placement of apostrophes before 0-initial syllables,
        - support for different apostrophe characters,
        - support for I{r-coloured} syllables (I{Erlhuah}) and
        - guessing of input form (I{reading dialect}).

    Limitations:
        - abbreviated forms for multiple syllables are not supported,
        - syllable repetition markers as reported by some will currently not be
          parsed.

    R-colouring
    ===========
    Gwoyeu Romatzyh renders X{rhotacised} syllables (X{Erlhuah}) by trying to
    give the actual pronunciation. As the effect of r-colouring looses the
    information of the underlying etymological syllable conversion between the
    r-coloured form back to the underlying form can not be done in an
    unambiguous way. As furthermore finals I{i}, I{iu}, I{in}, I{iun} contrast
    in the first and the second tone but not in the third and the forth tone
    conversion between different tones (including the base form) cannot be made
    in a general manner: 小鸡儿 I{sheau-jiel} is different to 小街儿
    I{sheau-jie’l} but 几儿 I{jieel} equals 姐儿 I{jieel} (see Chao).

    Thus this ReadingOperator lacks the general handling of syllable renderings
    and many methods narrow the range of syllables allowed. Unlike the original
    forms without r-colouring for Erlhuah forms the combination of a plain
    syllable with a specific tone is limited to the data given in the source, so
    operations involving tones may return with an L{UnsupportedError} if the
    given syllable isn't found with that tone.

    Sources
    =======
    - Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
        Press, Berkeley, 1968, ISBN 0-520-00219-9.

    @see:
        - GR Junction by Richard Warmington:
            U{http://home.iprimus.com.au/richwarm/gr/gr.htm}
        - Article about Gwoyeu Romatzyh on the English Wikipedia:
            U{http://en.wikipedia.org/wiki/Gwoyeu_Romatzyh}

    @todo Impl: Initial, medial, head, ending (ending1, ending2=l?)
    @todo Lang: Which character to use for optional neutral tone: C{'ₒ'} ?
    @todo Impl: Implement Erhua forms as stated in W. Simon: A Beginner's
        Chinese-English Dictionary.
    @todo Impl: Implement repetition markers as stated in W. Simon: A Beginner's
        Chinese-English Dictionary.
    @todo Impl: Implement a GRIPAConverter once IPA values are obtained for
        the PinyinIPAConverter. GRIPAConverter can work around missing Erhua
        conversion to Pinyin.
    @todo Lang: Special rule for non-Chinese names with initial r- to be
        transcribed with an r- cited by Ching-song Gene Hsiao: A Manual of
        Transcription Systems For Chinese, 中文拼音手册. Far Eastern Publications,
        Yale University, New Haven, Connecticut, 1985, ISBN 0-88710-141-0.
    """
    READING_NAME = 'GR'

    TONES = ['1stTone', '2ndTone', '3rdTone', '4thTone',
        '5thToneEtymological1st', '5thToneEtymological2nd',
        '5thToneEtymological3rd', '5thToneEtymological4th',
        '1stToneOptional5th', '2ndToneOptional5th', '3rdToneOptional5th',
        '4thToneOptional5th']

    SYLLABLE_STRUCTURE = re.compile(r"^((?:tz|ts|ch|sh|[bpmfdtnlsjrgkh])?)" \
        + "([aeiouy]+)((?:ngl|ng|n|l)?)$")
    """Regular expression describing the syllable structure in GR (C,V,C)."""

    _syllableToneLookup = None
    """Holds the tonal syllable to plain syllable & tone lookup table."""

    _abbrConversionLookup = None
    """Holds the abbreviated entity lookup table."""

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

    def __init__(self, **options):
        u"""
        Creates an instance of the GROperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        @keyword abbreviations: if set to C{True} abbreviated spellings will be
            supported.
        @keyword GRRhotacisedFinalApostrophe: an alternate apostrophe that is
            taken instead of the default one for marking a longer and back vowel
            in rhotacised finals.
        @keyword GRSyllableSeparatorApostrophe: an alternate apostrophe that is
            taken instead of the default one for separating 0-initial syllables
            from preceding ones.
        """
        super(GROperator, self).__init__(**options)

        if 'abbreviations' in options:
            self.optionValue['abbreviations'] = options['abbreviations']

        if 'GRRhotacisedFinalApostrophe' in options:
            self.optionValue['GRRhotacisedFinalApostrophe'] \
                = options['GRRhotacisedFinalApostrophe']

        if 'GRSyllableSeparatorApostrophe' in options:
            self.optionValue['GRSyllableSeparatorApostrophe'] \
                = options['GRSyllableSeparatorApostrophe']

        self.readingEntityRegex = re.compile(u"([\.ₒ]?(?:" \
            + re.escape(self.getOption('GRRhotacisedFinalApostrophe')) \
            + "|[A-Za-z])+)")


    @classmethod
    def getDefaultOptions(cls):
        options = super(GROperator, cls).getDefaultOptions()
        options.update({'abbreviations': True,
            'GRRhotacisedFinalApostrophe': u"’",
            'GRSyllableSeparatorApostrophe': u"’"})

        return options

    @classmethod
    def guessReadingDialect(cls, string, includeToneless=False):
        u"""
        Takes a string written in GR and guesses the reading dialect.

        The options C{'GRRhotacisedFinalApostrophe'} and
        C{'GRSyllableSeparatorApostrophe'} are guessed. Both will be set to the
        same value which derives from a list of different apostrophes and
        similar characters.

        @type string: str
        @param string: GR string
        @rtype: dict
        @return: dictionary of basic keyword settings
        """
        APOSTROPHE_LIST = ["'", u'’', u'´', u'‘', u'`', u'ʼ', u'ˈ', u'′', u'ʻ']
        readingStr = unicodedata.normalize("NFC", unicode(string))

        # guess apostrophe vowel
        for apostrophe in APOSTROPHE_LIST:
            if apostrophe in readingStr:
                break
        else:
            apostrophe = "'"

        return {'GRRhotacisedFinalApostrophe': apostrophe,
            'GRSyllableSeparatorApostrophe': apostrophe}

    def getTones(self):
        return self.TONES[:]

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string. Applies an
        apostrophe between syllables if the second syllable has a zero-initial.

        @type readingEntities: list of str
        @param readingEntities: list of basic syllables or other content
        @rtype: str
        @return: composed entities
        """
        newReadingEntities = []
        precedingEntity = None

        for entity in readingEntities:
            if precedingEntity and self.isReadingEntity(precedingEntity) \
                and self.isReadingEntity(entity):

                if entity[0] in ['a', 'e', 'i', 'o', 'u']:
                    newReadingEntities.append(
                        self.getOption('GRSyllableSeparatorApostrophe'))

            newReadingEntities.append(entity)
            precedingEntity = entity

        return ''.join(newReadingEntities)

    def isStrictDecomposition(self, readingEntities):
        precedingEntity = None
        for entity in readingEntities:
            if precedingEntity and self.isReadingEntity(precedingEntity) \
                and self.isReadingEntity(entity):

                if entity[0] in ['a', 'e', 'i', 'o', 'u']:
                    return False

            precedingEntity = entity

        return True

    def _recursiveSegmentation(self, string):
        # overwrite method to deal with the apostrophe that can be both a part
        #   of a syllable and a separator between syllables
        segmentationParts = []
        substringIndex = 1
        while substringIndex <= len(string) and \
            (self._hasSyllableSubstring(string[0:substringIndex].lower()) \
                or string[0:substringIndex] == "'"):
            syllable = string[0:substringIndex]
            if self.isReadingEntity(syllable) or syllable == "'":
                remaining = string[substringIndex:]
                if remaining != '':
                    remainingParts = self._recursiveSegmentation(remaining)
                    if remainingParts != []:
                        segmentationParts.append((syllable, remainingParts))
                else:
                    segmentationParts.append((syllable, None))
            substringIndex = substringIndex + 1
        return segmentationParts

    def removeApostrophes(self, readingEntities):
        """
        Removes apostrophes between two syllables for a given decomposition.

        @type readingEntities: list of str
        @param readingEntities: list of basic syllables or other content
        @rtype: list of str
        @return: the given entity list without separating apostrophes
        """
        if len(readingEntities) == 0:
            return []
        elif len(readingEntities) > 2 and readingEntities[1] == "'" \
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

        @type tone: str
        @param tone: tone
        @rtype: int
        @return: base tone number
        @raise InvalidEntityError: if an invalid tone is passed.
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + unicode(tone) + "'")

        if tone.startswith("5thToneEtymological"):
            return int(tone[-3])
        else:
            return int(tone[0])

    def splitPlainSyllableCVC(self, plainSyllable):
        """
        Splits the given plain syllable into consonants-vowels-consonants.

        @type plainSyllable: str
        @param plainSyllable: entity without tonal information
        @rtype: tuple of str
        @return: syllable CVC triple
        @raise InvalidEntityError: if the entity is invalid.
        """
        # split syllable into CVC parts
        matchObj = self.SYLLABLE_STRUCTURE.match(plainSyllable)
        if not matchObj:
            print plainSyllable
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
        different syllables. Use L{getRhotacisedTonalEntity()} to get the tonal
        entity for a given etymological (base) syllable.

        @type plainEntity: str
        @param plainEntity: entity without tonal information
        @type tone: str
        @param tone: tone
        @rtype: str
        @return: entity with appropriate tone
        @raise InvalidEntityError: if the entity is invalid.
        @raise UnsupportedError: if the given entity is an Erlhuah form.
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + unicode(tone) + "'")

        if plainEntity.endswith('l') and plainEntity != 'el' \
            and self.isPlainReadingEntity(plainEntity[:-1]):
            raise UnsupportedError("Not supported for '" + plainEntity + "'")

        # split syllable into CVC parts
        c1, v, c2 = self.splitPlainSyllableCVC(plainEntity)
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
            tonalEntity = u'ₒ' + tonalEntity

        return tonalEntity

    def splitEntityTone(self, entity):
        if self._syllableToneLookup == None:
            self._syllableToneLookup = {}
            for plainEntity in self.getPlainReadingEntities():
                for tone in self.getTones():
                    tonalEntity = self.getTonalEntity(plainEntity, tone)
                    self._syllableToneLookup[tonalEntity] = (plainEntity, tone)

        if entity not in self._syllableToneLookup:
            # don't work for Erlhuah forms
            if self.isReadingEntity(entity):
                raise UnsupportedError("Not supported for '" + entity + "'")
            else:
                raise InvalidEntityError("Invalid entity given for '" \
                    + entity + "'")

        return self._syllableToneLookup[entity]

    def getRhotacisedTonalEntity(self, plainEntity, tone):
        """
        Gets the r-coloured entity (Erlhuah form) with tone mark for the given
        plain entity and tone. Not all entity-tone combinations are supported.

        @type plainEntity: str
        @param plainEntity: entity without tonal information
        @type tone: str
        @param tone: tone
        @rtype: str
        @return: entity with appropriate tone
        @raise InvalidEntityError: if the entity is invalid.
        @raise UnsupportedError: if the given entity is an Erlhuah form or the
            syllable is not supported in this given tone.
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + unicode(tone) + "'")

        if plainEntity.endswith('l') \
            and self.isPlainReadingEntity(plainEntity[:-1]):
            raise UnsupportedError("Not supported for '" + plainEntity + "'")

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

        tonalFinal = self.db.selectSingleEntrySoleValue("GRRhotacisedFinals",
            column, {'GRFinal': v + c2})
        if not tonalFinal:
            raise UnsupportedError("No Erlhuah form for '" \
                + plainEntity + "' and tone '" + tone + "'")


        # use selected apostrophe
        if self.getOption('GRRhotacisedFinalApostrophe') \
            != self.DB_RHOTACISED_FINAL_APOSTROPHE:
            tonalFinal = tonalFinal.replace(self.DB_RHOTACISED_FINAL_APOSTROPHE,
                    self.getOption('GRRhotacisedFinalApostrophe'))

        tonalEntity = c1 + tonalFinal

        if tone.startswith('5'):
            tonalEntity = '.' + tonalEntity
        elif tone.endswith('Optional5th'):
            tonalEntity = u'ₒ' + tonalEntity

        return tonalEntity

    def _getAbbreviatedLookup(self):
        """
        Gets the abbreviated form lookup table.

        @rtype: dict
        @return: lookup table of abbreviated forms
        """
        if self._abbrConversionLookup == None:
            self._abbrConversionLookup = {}

            fullEntities = self.getFullReadingEntities()

            result = self.db.select("GRAbbreviation", ["GR", "GRAbbreviation"],
                distinctValues=True)
            for originalEntity, abbreviatedEntity in result:
                # don't convert proper entities
                if abbreviatedEntity in fullEntities:
                    continue

                if abbreviatedEntity in self._abbrConversionLookup:
                    # ambiguous mapping
                    self._abbrConversionLookup[abbreviatedEntity] = None

                self._abbrConversionLookup[abbreviatedEntity] = originalEntity

        return self._abbrConversionLookup

    def getAbbreviatedEntities(self):
        """
        Gets a list of abbreviated GR spellings.

        @rtype: list
        @return: list of abbreviated GR forms
        """
        return self._getAbbreviatedLookup().keys()

    def isAbbreviatedEntity(self, entity):
        """
        Returns true if the given entity is an abbreviated spelling.

        Reading entities will be handled as being case insensitive.

        @type entity: str
        @param entity: entity to check
        @rtype: bool
        @return: C{True} if entity is an abbreviated form.
        """
        return entity in self._getAbbreviatedLookup()

    def convertAbbreviatedEntity(self, entity):
        """
        Converts the given abbreviated GR spelling to the original form.
        Non-abbreviated forms will returned unchanged. Takes care of
        capitalisation.

        @type entity: str
        @param entity: reading entity.
        @rtype: str
        @return: original entity
        @raise AmbiguousConversionError: if conversion is ambiguous.
        @todo Fix: Move this method to the Converter, AmbiguousConversionError
            not needed for import here then
        """
        if self.isAbbreviatedEntity(entity):
            if self._getAbbreviatedLookup()[entity] == None:
                raise AmbiguousConversionError("conversion for entity '" \
                    + entity + "' is ambiguous")

            originalEntity = self._getAbbreviatedLookup()[entity]
            if entity.isupper():
                originalEntity = originalEntity.upper()
            elif entity.istitle():
                originalEntity = originalEntity.capitalize()

            return originalEntity
        else:
            return entity

    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading without
        r-coloured forms (Erlhuah forms). Different to L{getReadingEntities()}
        the entities will carry no tone mark.

        @rtype: set of str
        @return: set of supported syllables
        """
        return set(self.db.selectSoleValue("GRSyllables", "GR"))

    def getFullReadingEntities(self):
        """
        Gets a set of full entities supported by the reading excluding
        abbreviated forms.

        @rtype: set of str
        @return: set of supported syllables
        """
        plainSyllables = self.getPlainReadingEntities()

        syllableSet = set()
        for syllable in plainSyllables:
            for tone in self.getTones():
                syllableSet.add(self.getTonalEntity(syllable, tone))

        # Erlhuah
        for syllable in plainSyllables:
            for tone in self.getTones():
                try:
                    erlhuahSyllable = self.getRhotacisedTonalEntity(syllable,
                        tone)
                    syllableSet.add(erlhuahSyllable)
                except UnsupportedError:
                    # ignore errors about tone combinations that don't exist
                    pass

        return syllableSet

    def getReadingEntities(self):
        syllableSet = self.getFullReadingEntities()
        syllableSet.update(self.getAbbreviatedEntities())

        return syllableSet

    def isReadingEntity(self, entity):
        # overwrite default method, use lookup dictionary
        return RomanisationOperator.isReadingEntity(self, entity)


class MandarinIPAOperator(TonalIPAOperator):
    u"""
    Provides an operator on strings in Mandarin Chinese written in the
    I{International Phonetic Alphabet} (I{IPA}).

    Features:
        - Tones can be marked either with tone numbers (1-4), tone contour
            numbers (e.g. 214), IPA tone bar characters or IPA diacritics,
        - support for low third tone (1/2 third tone) with tone contour 21,
        - four levels of the neutral tone for varying stress depending on the
            preceding syllable and
        - splitting of syllables into onset and rhyme using method
            L{getOnsetRhyme()}.

    Tones
    =====
    Tones in IPA can be expressed using different schemes. The following schemes
    are implemented here:
        - Numbers, regular tone numbers from 1 to 5 for first tone to fifth
            (qingsheng),
        - ChaoDigits, numbers displaying the levels of tone contours, e.g.
            214 for the regular third tone,
        - IPAToneBar, IPA modifying tone bar characters, e.g. ɕi˨˩˦,
        - Diacritics, diacritical marks and finally
        - None, no support for tone marks

    Unlike other operators for Mandarin, distinction is made for six different
    tonal occurrences. The third tone is affected by tone sandhi and basically
    two different tone contours exist. Therefore L{getTonalEntity()} and
    L{splitEntityTone()} work with string representations as tones defined in
    L{TONES}. Same behaviour as found in other operators for Mandarin can be
    achieved by simply using the first character of the given string:

        >>> from cjklib.reading import operator
        >>> ipaOp = operator.MandarinIPAOperator(toneMarkType='IPAToneBar')
        >>> syllable, toneName = ipaOp.splitEntityTone(u'mən˧˥')
        >>> tone = int(toneName[0])

    The implemented schemes render tone information differently. Mapping might
    lose information so a full back-transformation can not be guaranteed.

    Source
    ======
    - Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
        Press, Berkeley, 1968, ISBN 0-520-00219-9.
    """
    READING_NAME = "MandarinIPA"

    TONE_MARK_PREFER = {'Numbers': {'3': '3rdToneRegular', '5': '5thTone'},
        'ChaoDigits': {}, 'IPAToneBar': {}, 'Diacritics': {}}

    TONES = ['1stTone', '2ndTone', '3rdToneRegular', '3rdToneLow',
        '4thTone', '5thTone', '5thToneHalfHigh', '5thToneMiddle',
        '5thToneHalfLow', '5thToneLow']

    TONE_MARK_MAPPING = {'Numbers': {'1stTone': '1', '2ndTone': '2',
            '3rdToneRegular': '3', '3rdToneLow': '3', '4thTone': '4',
            '5thTone':'5', '5thToneHalfHigh': '5', '5thToneMiddle': '5',
            '5thToneHalfLow': '5', '5thToneLow': '5'},
        'ChaoDigits': {'1stTone': '55', '2ndTone': '35',
            '3rdToneRegular': '214', '3rdToneLow': '21', '4thTone': '51',
            '5thTone':'', '5thToneHalfHigh': '', '5thToneMiddle': '',
            '5thToneHalfLow': '', '5thToneLow': ''},
        'IPAToneBar': {'1stTone': u'˥˥', '2ndTone': u'˧˥',
            '3rdToneRegular': u'˨˩˦', '3rdToneLow': u'˨˩', '4thTone': u'˥˩',
            '5thTone':'', '5thToneHalfHigh': u'꜉', '5thToneMiddle': u'꜊',
            '5thToneHalfLow': u'꜋', '5thToneLow': u'꜌'},
        # TODO
        #'Diacritics': {'1stTone': u'\u0301', '2ndTone': u'\u030c',
            #'3rdToneRegular': u'\u0301\u0300\u0301', '3rdToneLow': u'\u0300',
            #'4thTone': u'\u0302', '5thTone': u'', '5thToneHalfHigh': '',
            #'5thToneMiddle': '', '5thToneHalfLow': '', '5thToneLow': ''}
        }

    def getPlainReadingEntities(self):
        """
        Gets the list of plain entities supported by this reading. These
        entities will carry no tone mark.

        @rtype: set of str
        @return: set of supported syllables
        """
        return set(self.db.selectSoleValue("MandarinIPAInitialFinal", "IPA"))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        @type plainSyllable: str
        @param plainSyllable: syllable in IPA without tone marks
        @rtype: tuple of str
        @return: tuple of syllable onset and rhyme
        @raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).
        """
        entry = self.db.selectSingleEntry("MandarinIPAInitialFinal",
            ["IPAInitial", "IPAFinal"], {"IPA": plainSyllable})
        if not entry:
            raise InvalidEntityError("'" + plainSyllable \
                + "' not a valid IPA form in this system'")
        return (entry[0], entry[1])


class MandarinBrailleOperator(ReadingOperator):
    u"""
    Provides an operator on strings written in the X{Braille} system.
    """
    READING_NAME = "MandarinBraille"

    TONEMARKS = [u'⠁', u'⠂', u'⠄', u'⠆', '']

    def __init__(self, **options):
        """
        Creates an instance of the MandarinBrailleOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        """
        super(MandarinBrailleOperator, self).__init__(**options)

        # split regex
        initials = ''.join(self.db.selectSoleValue(
            'PinyinBrailleInitialMapping', 'Braille', distinctValues=True))
        finals = ''.join(self.db.selectSoleValue(
            'PinyinBrailleFinalMapping', 'Braille', distinctValues=True))
        # initial and final optional (but at least one), tone optional
        self.splitRegex = re.compile(ur'((?:(?:[' + re.escape(initials) \
            + '][' + re.escape(finals) + ']?)|['+ re.escape(finals) \
            + u'])[' + re.escape(''.join(self.TONEMARKS)) + ']?)')
        self.brailleRegex = re.compile(ur'([⠀-⣿]+|[^⠀-⣿]+)')

    def getTones(self):
        """
        Returns a set of tones supported by the reading.

        @rtype: set
        @return: set of supported tone marks.
        """
        return range(1, 6)

    def decompose(self, string):
        """
        Decomposes the given string into basic entities that can be mapped to
        one Chinese character each (exceptions possible).

        The given input string can contain other non reading characters, e.g.
        punctuation marks.

        The returned list contains a mix of basic reading entities and other
        characters e.g. spaces and punctuation marks.

        @type string: str
        @param string: reading string
        @rtype: list of str
        @return: a list of basic entities of the input string
        """
        def buildList(entityList):
            # further splitting of Braille and non-Braille parts/removing empty
            #   strings
            newList = self.brailleRegex.findall(entityList[0])

            if len(entityList) > 1:
                newList.extend(buildList(entityList[1:]))

            return newList

        return buildList(self.splitRegex.split(string))

    def compose(self, readingEntities):
        """
        Composes the given list of basic entities to a string.

        No special treatment is given for subsequent Braille entities. Use
        L{getSpaceSeparatedEntities()} to insert spaces between two Braille
        syllables.

        @type readingEntities: list of str
        @param readingEntities: list of basic entities or other content
        @rtype: str
        @return: composed entities
        """
        return "".join(readingEntities)

    def getSpaceSeparatedEntities(self, readingEntities):
        """
        Inserts spaces between to Braille entities for a given list of reading
        entities.

        Spaces in the Braille system are applied between words. This is not
        reflected here and instead a space will be added between single
        syllables.

        @type readingEntities: list of str
        @param readingEntities: list of basic entities or other content
        @rtype: list of str
        @return: entities with spaces inserted between Braille sequences
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

        @type plainEntity: str
        @param plainEntity: entity without tonal information
        @type tone: str
        @param tone: tone
        @rtype: str
        @return: entity with appropriate tone
        @raise InvalidEntityError: if the entity is invalid.
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")
        return plainEntity + self.TONEMARKS[tone-1]

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the name of the
        entity's tone.

        @type entity: str
        @param entity: entity with tonal information
        @rtype: tuple
        @return: plain entity without tone mark and additionally the tone
        @raise InvalidEntityError: if the entity is invalid.
        """
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

            if final and self.db.selectSingleEntrySoleValue(
                'PinyinBrailleFinalMapping', 'Braille', {'Braille': final},
                distinctValues=True) == None:
                return False
            if initial and self.db.selectSingleEntrySoleValue(
                'PinyinBrailleInitialMapping', 'Braille', {'Braille': initial},
                distinctValues=True) == None:
                return False

            return True
        except InvalidEntityError:
            return False

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        @type plainSyllable: str
        @param plainSyllable: syllable without tone marks
        @rtype: tuple of str
        @return: tuple of syllable onset and rhyme
        @raise InvalidEntityError: if the entity is invalid.
        """
        if len(plainSyllable) == 1:
            if plainSyllable and self.db.selectSingleEntrySoleValue(
                'PinyinBrailleFinalMapping', 'Braille',
                {'Braille': plainSyllable}, distinctValues=True) != None:
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
    Provides an operator for the Cantonese romanisation X{Jyutping} made by the
    X{Linguistic Society of Hong Kong} (X{LSHK}).

    @see:
        - The Linguistic Society of Hong Kong Cantonese Romanization Scheme:
            U{http://lshk.ctl.cityu.edu.hk/cantonese.php}
    """
    READING_NAME = 'Jyutping'
    readingEntityRegex = re.compile(u"([A-Za-z]+[123456]?)")

    def __init__(self, **options):
        """
        Creates an instance of the JyutpingOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        @keyword toneMarkType: if set to C{'Numbers'} the default form of
            appended numbers from 1 to 6 will be used to mark tones, if set to
            C{'None'} no tone marks will be used and no tonal information will
            be supplied at all.
        @keyword missingToneMark: if set to C{'noinfo'} no tone information
            will be deduced when no tone mark is found (takes on value C{None}),
            if set to C{'ignore'} this entity will not be valid and for
            segmentation the behaviour defined by C{'strictSegmentation'} will
            take affect.
        """
        super(JyutpingOperator, self).__init__(**options)

        # check which tone marks to use
        if 'toneMarkType' in options:
            if options['toneMarkType'] not in ['Numbers', 'None']:
                raise ValueError("Invalid option '" \
                    + str(options['toneMarkType']) \
                    + "' for keyword 'toneMarkType'")
            self.optionValue['toneMarkType'] = options['toneMarkType']

        # check if we have to be strict on tones, i.e. report missing tone info
        if 'missingToneMark' in options:
            if options['missingToneMark'] not in ['noinfo', 'ignore']:
                raise ValueError("Invalid option '" \
                    + str(options['missingToneMark']) \
                    + "' for keyword 'missingToneMark'")
            self.optionValue['missingToneMark'] = options['missingToneMark']

    @classmethod
    def getDefaultOptions(cls):
        options = super(JyutpingOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'Numbers', 'missingToneMark': 'noinfo'})

        return options

    def getTones(self):
        tones = range(1, 7)
        if self.getOption('missingToneMark') != 'ignore' \
            or self.getOption('toneMarkType') == 'None':
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        return "".join(readingEntities)

    def getTonalEntity(self, plainEntity, tone):
        if self.getOption('toneMarkType') == 'None':
            return plainEntity

        if tone != None:
            tone = int(tone)
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")
        if tone == None:
            return plainEntity
        return plainEntity + str(tone)

    def splitEntityTone(self, entity):
        if self.getOption('toneMarkType') == 'None':
            return entity, None

        matchObj = re.search(u"[123456]$", entity)
        if matchObj:
            tone = int(matchObj.group(0))
            return entity[0:len(entity)-1], tone
        else:
            if self.getOption('missingToneMark') == 'ignore':
                raise InvalidEntityError("No tone information given for '" \
                    + entity + "'")
            else:
                return entity, None

    def getPlainReadingEntities(self):
        return set(self.db.selectSoleValue("JyutpingSyllables", "Jyutping"))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        The syllabic nasals I{m}, I{ng} will be regarded as being finals.

        @type plainSyllable: str
        @param plainSyllable: syllable without tone marks
        @rtype: tuple of str
        @return: tuple of entity onset and rhyme
        @raise InvalidEntityError: if the entity is invalid.
        @todo Impl: Finals I{ing, ik, ung, uk} differ from other finals with
            same vowels. What semantics/view do we want to provide on the
            syllable parts?
        """
        entry = self.db.selectSingleEntry("JyutpingInitialFinal",
            ["JyutpingInitial", "JyutpingFinal"],
            {"Jyutping": plainSyllable.lower()})
        if not entry:
            raise InvalidEntityError("'" + plainSyllable \
                + "' not a valid plain Jyutping syllable'")
        return (entry[0], entry[1])


class CantoneseYaleOperator(TonalRomanisationOperator):
    u"""
    Provides an operator for the X{Cantonese Yale} romanisation.

    Features:
        - tones marked by either diacritics or numbers,
        - choice between high level and high falling tone for number marks,
        - guessing of input form (reading dialect) and
        - splitting of syllables into onset, nucleus and coda.

    High Level vs. High Falling Tone
    ================================
    Yale distinguishes two tones often subsumed under one: the high level tone
    with tone contour 55 as given in the commonly used pitch model by Yuen Ren
    Chao and the high falling tone given as pitch 53 (as by Chao), 52 or 51
    (Bauer and Benedikt, chapter 2.1.1 pp. 115).
    Many sources state that these two tones aren't distinguishable anymore in
    modern Hong Kong Cantonese and thus are subsumed under one tone in some
    romanisation systems for Cantonese.

    In the abbreviated form of the Yale romanisation that uses numbers to
    represent tones this distinction is not made. The mapping of the tone number
    C{1} to either the high level or the high falling tone can be given by the
    user and is important when conversion is done involving this abbreviated
    form of the Yale romanisation. By default the the high level tone will be
    used as this primary use is indicated in the given sources.

    Sources
    =======
    - Stephen Matthews, Virginia Yip: Cantonese: A Comprehensive Grammar.
        Routledge, 1994, ISBN 0-415-08945-X.
    - Robert S. Bauer, Paul K. Benedikt: Modern Cantonese Phonology
        (摩登廣州話語音學). Walter de Gruyter, 1997, ISBN 3-11-014893-5.

    @see:
        - Cantonese: A Comprehensive Grammar (Preview):
            U{http://books.google.de/books?id=czbGJLu59S0C}
        - Modern Cantonese Phonology (Preview):
            U{http://books.google.de/books?id=QWNj5Yj6_CgC}
    """
    READING_NAME = 'CantoneseYale'

    TONES = ['1stToneLevel', '1stToneFalling', '2ndTone', '3rdTone', '4thTone',
        '5thTone', '6thTone']
    """Names of tones used in the romanisation."""
    TONE_MARK_MAPPING = {'Numbers': {'1stToneLevel': ('1', ''),
            '1stToneFalling': ('1', ''), '2ndTone': ('2', ''),
            '3rdTone': ('3', ''), '4thTone': ('4', ''), '5thTone': ('5', ''),
            '6thTone': ('6', ''), None: ('', '')},
        'Diacritics': {'1stToneLevel': (u'\u0304', ''),
            '1stToneFalling': (u'\u0300', ''),
            '2ndTone': (u'\u0301', ''), '3rdTone': (u'', ''),
            '4thTone': (u'\u0300', 'h'), '5thTone': (u'\u0301', 'h'),
            '6thTone': (u'', 'h')},
        'Internal': {'1stToneLevel': ('0', ''),
            '1stToneFalling': ('1', ''), '2ndTone': ('2', ''),
            '3rdTone': ('3', ''), '4thTone': ('4', ''), '5thTone': ('5', ''),
            '6thTone': ('6', ''), None: ('', '')}}
    """
    Mapping of tone name to representation per tone mark type. Representations
    includes a diacritic mark and optional the letter 'h' marking a low tone.

    The C{'Internal'} dialect is used for conversion between different forms of
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
        Creates an instance of the CantoneseYaleOperator.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword strictSegmentation: if C{True} segmentation (using
            L{segment()}) and thus decomposition (using L{decompose()}) will
            raise an exception if an alphabetic string is parsed which can not
            be segmented into single reading entities. If C{False} the aforesaid
            string will be returned unsegmented.
        @keyword toneMarkType: if set to C{'Diacritics'} tones will be marked
            using diacritic marks and the character I{h} for low tones, if set
            to C{'Numbers'} appended numbers from 1 to 6 will be used to mark
            tones, if set to C{'None'} no tone marks will be used and no tonal
            information will be supplied at all.
        @keyword missingToneMark: if set to C{'noinfo'} no tone information
            will be deduced when no tone mark is found (takes on value C{None}),
            if set to C{'ignore'} this entity will not be valid and for
            segmentation the behaviour defined by C{'strictSegmentation'} will
            take affect. This option is only valid if the value C{'Numbers'} is
            given for the option I{toneMarkType}.
        @keyword YaleFirstTone: tone in Yale which the first tone for tone marks
            with numbers should be mapped to. Value can be C{'1stToneLevel'} to
            map to the level tone with contour 55 or C{'1stToneFalling'} to map
            to the falling tone with contour 53.
        """
        super(CantoneseYaleOperator, self).__init__(**options)

        # check which tone marks to use
        if 'toneMarkType' in options:
            if options['toneMarkType'] not in ['Diacritics', 'Numbers', 'None',
                'Internal']:
                raise ValueError("Invalid option '" \
                    + str(options['toneMarkType']) \
                    + "' for keyword 'toneMarkType'")
            self.optionValue['toneMarkType'] = options['toneMarkType']

        # check if we have to be strict on tones, i.e. report missing tone info
        if 'missingToneMark' in options:
            if option['toneMarkType'] not in ['Numbers', 'Internal', 'None']:
                raise ValueError("keyword 'missingToneMark' is only valid if" \
                    + " tone mark type is set to 'Numbers', 'Internal' and "\
                    + "'None'")

            if options['missingToneMark'] not in ['noinfo', 'ignore']:
                raise ValueError("Invalid option '" \
                    + str(options['missingToneMark']) \
                    + "' for keyword 'missingToneMark'")
            self.optionValue['missingToneMark'] = options['missingToneMark']

        # set the YaleFirstTone for handling ambiguous conversion of first
        #   tone in Cantonese that has two different representations in Yale
        if 'YaleFirstTone' in options:
            if options['YaleFirstTone'] not in ['1stToneLevel',
                '1stToneFalling', 'None']:
                raise ValueError("Invalid option '" \
                    + unicode(options['YaleFirstTone']) \
                    + "' for keyword 'YaleFirstTone'")
            self.optionValue['YaleFirstTone'] = options['YaleFirstTone']

        # create lookup dict
        if self.getOption('toneMarkType') != 'None':
            # create lookup dicts
            self.toneMarkLookup = {}
            for tone in self.getTones():
                toneMarks = self.TONE_MARK_MAPPING[
                    self.getOption('toneMarkType')][tone]
                self.toneMarkLookup[toneMarks] = tone
            if self.getOption('toneMarkType') == 'Numbers':
                # first tone ambiguous for tone mark as numbers, set user
                #   selected tone
                self.toneMarkLookup[('1', '')] = self.getOption('YaleFirstTone')

        # create tone regex
        if self.getOption('toneMarkType') != 'None':
            self.primaryToneRegex = re.compile(r"(?i)^[a-z]+([" \
                + r"".join(set([re.escape(toneMark) for toneMark, hChar \
                    in self.TONE_MARK_MAPPING[self.getOption('toneMarkType')]\
                        .values()])) \
                + r"]?)")
            self.hCharRegex = re.compile(r"^.*(?:[aeiou]|m|ng)(h)")

        # set split regular expression, works for all tone marks
        self.readingEntityRegex = re.compile(u'(?i)((?:' \
            + '|'.join([re.escape(v) for v in self._getDiacriticVowels()]) \
            + u'|[a-z])+[0123456]?)')

    @classmethod
    def getDefaultOptions(cls):
        options = super(CantoneseYaleOperator, cls).getDefaultOptions()
        options.update({'toneMarkType': 'Diacritics',
            'missingToneMark': 'noinfo', 'YaleFirstTone': '1stToneLevel'})

        return options

    @staticmethod
    def _getDiacriticVowels():
        """
        Gets a list of Cantonese Yale vowels with diacritical marks for tones.

        The list includes characters I{m}, I{n} and I{h} for nasal forms.

        @rtype: list of str
        @return: list of Cantonese Yale vowels with diacritical marks
        """
        vowelList = set([])
        for nucleusFirstChar in 'aeioumnh':
            for toneMark, hChar in \
                CantoneseYaleOperator.TONE_MARK_MAPPING['Diacritics'].values():
                if toneMark:
                    vowelList.add(unicodedata.normalize("NFC",
                        nucleusFirstChar + toneMark))
        return vowelList

    @classmethod
    def guessReadingDialect(cls, string, includeToneless=False):
        """
        Takes a string written in Cantonese Yale and guesses the reading
        dialect.

        Currently only the option C{'toneMarkType'} is guessed. Unless
        C{'includeToneless'} is set to C{True} only the tone mark types
        C{'Diacritics'} and C{'Numbers'} are considered as the latter one can
        also represent the state of missing tones.

        @type string: str
        @param string: Cantonese Yale string
        @rtype: dict
        @return: dictionary of basic keyword settings
        """
        # split into entities using a simple regex for all dialect forms
        entities = cls.syllableRegex.findall(
            unicodedata.normalize("NFD", unicode(string)))

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
            toneMarkType = 'None'
        else:
            if diacriticEntityCount > numberEntityCount:
                toneMarkType = 'Diacritics'
            else:
                toneMarkType = 'Numbers'

        return {'toneMarkType': toneMarkType}

    def getTones(self):
        tones = self.TONES[:]
        if (self.getOption('missingToneMark') == 'noinfo' \
            and self.getOption('toneMarkType') in ['Numbers', 'Internal']) \
            or self.getOption('toneMarkType') == 'None':
            tones.append(None)
        return tones

    def compose(self, readingEntities):
        return "".join(readingEntities)

    def getTonalEntity(self, plainEntity, tone):
        """
        @todo Lang: Place the tone mark on the first character of the nucleus?
        """
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + unicode(tone) + "'")

        if self.getOption('toneMarkType') == 'None':
            return plainEntity

        toneMark, hChar = self.TONE_MARK_MAPPING[
            self.getOption('toneMarkType')][tone]

        if self.getOption('toneMarkType') == 'Diacritics':
            # split entity into vowel (aeiou) and non-vowel part for placing
            #   marks
            matchObj = re.match('(?i)^([^aeiou]*?)([aeiou]*)([^aeiou]*)$',
                plainEntity)
            if not matchObj:
                raise InvalidEntityError("Invalid entity given for '" \
                    + plainEntity + "'")

            nonVowelH, vowels, nonVowelT = matchObj.groups()
            # place 'h' after vowel (or after syllable for syllabic nasal) and
            #   diacritic on first vowel/first character for syllabic nasal
            if vowels:
                vowels = unicodedata.normalize("NFC", vowels[0] + toneMark \
                    + vowels[1:] + hChar)
            else:
                nonVowelT = unicodedata.normalize("NFC", nonVowelT[0] \
                    + toneMark + nonVowelT[1:] + hChar)

            return nonVowelH + vowels + nonVowelT
        elif self.getOption('toneMarkType') in ['Numbers', 'Internal']:
            return plainEntity + toneMark

    def splitEntityTone(self, entity):
        """
        Splits the entity into an entity without tone mark and the
        entity's tone index.

        The plain entity returned will always be in Unicode's
        I{Normalization Form C} (NFC, see
        U{http://www.unicode.org/reports/tr15/}).

        @type entity: str
        @param entity: entity with tonal information
        @rtype: tuple
        @return: plain entity without tone mark and entity's tone index
            (starting with 1)
        """
        # get decomposed Unicode string, e.g. C{'ū'} to C{'u\u0304'}
        entity = unicodedata.normalize("NFD", unicode(entity))
        if self.getOption('toneMarkType') == 'None':
            return unicodedata.normalize("NFC", entity), None

        # find primary tone mark
        matchObj = self.primaryToneRegex.search(entity)
        if not matchObj:
            raise InvalidEntityError("Invalid entity or no tone information " \
                "given for '" + entity + "'")
        toneMark = matchObj.group(1)
        plainEntity = entity[0:matchObj.start(1)] + entity[matchObj.end(1):]

        # find lower tone mark 'h' character
        matchObj = self.hCharRegex.search(plainEntity)
        if matchObj:
            hChar = matchObj.group(1)
            plainEntity = plainEntity[0:matchObj.start(1)] \
                + plainEntity[matchObj.end(1):]
        else:
            hChar = ''

        try:
            tone = self.toneMarkLookup[(toneMark, hChar)]
        except KeyError:
            raise InvalidEntityError("Invalid entity or no tone information " \
                "given for '" + entity + "'")

        return unicodedata.normalize("NFC", plainEntity), tone

    def getPlainReadingEntities(self):
        return set(self.db.selectSoleValue("CantoneseYaleSyllables",
            "CantoneseYale"))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        The syllabic nasals I{m}, I{ng} will be returned as final. Syllables yu,
        yun, yut will fall into (y, yu, ), (y, yu, n) and (y, yu, t).

        @type plainSyllable: str
        @param plainSyllable: syllable without tone marks
        @rtype: tuple of str
        @return: tuple of entity onset and rhyme
        @raise InvalidEntityError: if the entity is invalid.
        """
        onset, nucleus, coda = self.getOnsetNucleusCoda(plainSyllable)
        return onset, nucleus + coda

    def getOnsetNucleusCoda(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial), nucleus and coda,
        the latter building the rhyme (final).

        The syllabic nasals I{m}, I{ng} will be returned as coda. Syllables yu,
        yun, yut will fall into (y, yu, ), (y, yu, n) and (y, yu, t).

        @type plainSyllable: str
        @param plainSyllable: syllable in the Yale romanisation system without
            tone marks
        @rtype: tuple of str
        @return: tuple of syllable onset, nucleus and coda
        @raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).
        @todo Impl: Finals I{ing, ik, ung, uk, eun, eut, a} differ from other
            finals with same vowels. What semantics/view do we want to provide
            on the syllable parts?
        """
        # if tone mark exist, split off
        entry = self.db.selectSingleEntry("CantoneseYaleInitialNucleusCoda",
            ["CantoneseYaleInitial", "CantoneseYaleNucleus",
            "CantoneseYaleCoda"], {"CantoneseYale": plainSyllable.lower()})
        if not entry:
            raise InvalidEntityError("'" + plainSyllable \
                + "' not a valid plain Cantonese Yale syllable'")

        return (entry[0], entry[1], entry[2])


class CantoneseIPAOperator(TonalIPAOperator):
    u"""
    Provides an operator on strings of the Cantonese language written in the
    I{International Phonetic Alphabet} (I{IPA}).

    CantonteseIPAOperator does not supply the same closed set of syllables as
    other L{ReadingOperator}s as IPA provides different ways to represent
    pronunciation. Because of that a user defined IPA syllable will not easily
    map to another transcription system and thus only basic support is provided
    for this direction.

    This operator supplies an additional method L{getOnsetRhyme()} which allows
    breaking down syllables into their onset and rhyme.

    Features:
        - Tones can be marked either with tone numbers (1-6), tone contour
            numbers (e.g. 55), IPA tone bar characters or IPA diacritics,
        - choice between high level and high falling tone for number marks,
        - flexible set of tones,
        - support for stop tones,
        - handling of variable vowel length for tone contours of stop tone
            syllables and
        - splitting of syllables into onset and rhyme.

    Tones
    =====
    Tones in IPA can be expressed using different schemes. The following schemes
    are implemented here:
        - Numbers, tone numbers for the six-tone scheme,
        - ChaoDigits, numbers displaying the levels of tone contours, e.g.
            55 for the high level tone,
        - IPAToneBar, IPA modifying tone bar characters, e.g. ɛw˥˥,
        - None, no support for tone marks

    Sources
    =======
    - Robert S. Bauer, Paul K. Benedikt: Modern Cantonese Phonology
        (摩登廣州話語音學). Walter de Gruyter, 1997, ISBN 3-11-014893-5.
    - Robert S. Bauer: Hong Kong Cantonese Tone Contours. In: Studies in
        Cantonese Linguistics. Linguistic Society of Hong Kong, 1998,
        ISBN 962-7578-04-5.

    @see:
        - Modern Cantonese Phonology (Preview):
            U{http://books.google.de/books?id=QWNj5Yj6_CgC}

    @todo Lang: Shed more light on tone sandhi in Cantonese language.
    @todo Impl: Implement diacritics for Cantonese Tones. On which part of the
        syllable should they be placed. Document.
    @todo Lang: Binyām 變音
    @todo Impl: What are the semantics of non-level tones given for unreleased
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

    TONE_MARK_PREFER = {'Numbers': {'1': 'HighLevel'},
        'ChaoDigits': {}, 'IPAToneBar': {}, 'Diacritics': {}}

    TONE_MARK_MAPPING = {'Numbers': {'HighLevel': '1', 'MidLevel': '3',
            'MidLowLevel': '6', 'HighRising': '2', 'MidLowRising': '5',
            'MidLowFalling': '4', 'HighFalling': '1', 'HighStopped_Short': '1',
            'MidStopped_Short': '3', 'MidLowStopped_Short': '6',
            'HighStopped_Long': '1', 'MidStopped_Long': '3',
            'MidLowStopped_Long': '6'},
        'ChaoDigits': {'HighLevel': '55', 'MidLevel': '33',
            'MidLowLevel': '22', 'HighRising': '25', 'MidLowRising': '23',
            'MidLowFalling': '21', 'HighFalling': '52',
            'HighStopped_Short': '5', 'MidStopped_Short': '3',
            'MidLowStopped_Short': '2', 'HighStopped_Long': '55',
            'MidStopped_Long': '33', 'MidLowStopped_Long': '22'},
        'IPAToneBar': {'HighLevel': u'˥˥', 'MidLevel': u'˧˧',
            'MidLowLevel': u'˨˨', 'HighRising': u'˨˥', 'MidLowRising': u'˨˧',
            'MidLowFalling': u'˨˩', 'HighFalling': u'˥˨',
            'HighStopped_Short': u'˥', 'MidStopped_Short': u'˧',
            'MidLowStopped_Short': u'˨', 'HighStopped_Long': u'˥˥',
            'MidStopped_Long': u'˧˧', 'MidLowStopped_Long': u'˨˨'},
        #'Diacritics': {}
        }

    def __init__(self, **options):
        """
        Creates an instance of the CantoneseIPAOperator.

        By default no tone marks will be shown.

        @param options: extra options
        @keyword dbConnectInst: instance of a L{DatabaseConnector}, if none is
            given, default settings will be assumed.
        @keyword toneMarkType: type of tone marks, one out of C{'Numbers'},
            C{'ChaoDigits'}, C{'IPAToneBar'}, C{'Diacritics'}, C{'None'}
        @keyword 1stToneName: tone for mark 1 under tone mark type C{'Numbers'},
            either I{'HighLevel'} or I{'HighFalling'}.
        @keyword stopTones: if set to C{'none'} the basic 6 (7) tones will be
            used and stop tones will be reported as one of them, if set to
            C{'general'} the three stop tones will be included, if set to
            C{'explicit'} the short and long forms will be explicitly supported.
        """
        super(CantoneseIPAOperator, self).__init__(**options)

        if self.getOption('toneMarkType') == 'Diacritics':
            raise NotImplementedError() # TODO

        if '1stToneName' in options:
            if self.getOption('toneMarkType') != 'Numbers':
                raise ValueError("keyword '1stToneName' is only valid if" \
                    + " tone mark type is set to 'Numbers'")
            if options['1stToneName'] not in self.TONES:
                raise ValueError("Invalid option '" \
                    + str(options['1stToneName']) \
                    + "' for keyword '1stToneName'")

            self.optionValue['toneMarkPrefer']['1'] = options['1stToneName']

        if 'stopTones' in options:
            if options['stopTones'] not in ['none', 'general', 'explicit']:
                raise ValueError("Invalid option '" \
                    + str(options['stopTones']) + "' for keyword 'stopTones'")

            self.optionValue['stopTones'] = options['stopTones']

        # lookup base tone to explicit stop tone
        self.stopToneLookup = {}
        for stopTone in self.STOP_TONES_EXPLICIT:
            baseTone, vowelLength = self.STOP_TONES_EXPLICIT[stopTone]
            if not baseTone in self.stopToneLookup:
                self.stopToneLookup[baseTone] = {}
            self.stopToneLookup[baseTone][vowelLength] = stopTone
        # add general stop tones
        for stopTone in self.STOP_TONES:
            self.stopToneLookup[stopTone] \
                = self.stopToneLookup[self.STOP_TONES[stopTone]]

    @classmethod
    def getDefaultOptions(cls):
        options = super(CantoneseIPAOperator, cls).getDefaultOptions()
        options.update({'stopTones': 'none'})

        return options

    def getTones(self):
        tones = self.TONES[:]
        if self.getOption('stopTones') == 'general':
            tones.extend(self.STOP_TONES.keys())
        elif self.getOption('stopTones') == 'explicit':
            tones.extend(self.STOP_EXPLICIT.keys())
        if self.getOption('missingToneMark') == 'noinfo' \
            or self.getOption('toneMarkType') == 'None':
            tones.append(None)

        return tones

    def getPlainReadingEntities(self):
        return set(self.db.selectSoleValue("CantoneseIPAInitialFinal", "IPA"))

    def getOnsetRhyme(self, plainSyllable):
        """
        Splits the given plain syllable into onset (initial) and rhyme (final).

        @type plainSyllable: str
        @param plainSyllable: syllable in IPA without tone marks
        @rtype: tuple of str
        @return: tuple of syllable onset and rhyme
        @raise InvalidEntityError: if the entity is invalid (e.g. syllable
            nucleus or tone invalid).
        """
        entry = self.db.selectSingleEntry("CantoneseIPAInitialFinal",
            ["IPAInitial", "IPAFinal"], {"IPA": plainSyllable})
        if not entry:
            raise InvalidEntityError("'" + plainSyllable \
                + "' not a valid IPA form in this system'")
        return (entry[0], entry[1])

    def getTonalEntity(self, plainEntity, tone):
        if tone not in self.getTones():
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")
        if self.getOption('toneMarkType') == "None" or tone == None:
            entity = plainEntity
        else:
            # find explicit form
            tone = self.getExplicitTone(plainEntity, tone)

            entity = plainEntity \
                + self.TONE_MARK_MAPPING[self.getOption('toneMarkType')][tone]
        return unicodedata.normalize("NFC", entity)

    def splitEntityTone(self, entity):
        # get decomposed Unicode string, e.g. C{'â'} to C{'u\u0302'}
        entity = unicodedata.normalize("NFD", unicode(entity))

        toneMarkType = self.getOption('toneMarkType')
        if toneMarkType == 'None':
            return unicodedata.normalize("NFC", entity), None
        else:
            matchObj = self.TONE_MARK_REGEX[toneMarkType].search(entity)
            if matchObj:
                toneMark = matchObj.group(1)
                # strip off tone mark
                plainEntity = entity.replace(toneMark, '')

                baseTone = self.getBaseToneForToneMark(toneMark)

                return unicodedata.normalize("NFC", plainEntity), baseTone
            elif self.getOption('missingToneMark') == 'noinfo':
                return unicodedata.normalize("NFC", entity), None

        raise InvalidEntityError("Invalid entity given for '" + entity + "'")

    def getExplicitTone(self, plainSyllable, baseTone):
        """
        Gets the explicit tone for the given plain syllable and base tone.

        In case the 6 (7) base tones are used, the stop tone value can be
        deduced from the given syllable. The stop tone returned will be even
        more precise in denoting the vowel length that influences the tone
        contour.

        @type plainSyllable: str
        @param plainSyllable: syllable without tonal information
        @type baseTone: str
        @param baseTone: tone
        @rtype: str
        @return: explicit tone
        @raise InvalidEntityError: if the entity is invalid.
        """
        # only need explicit tones
        if baseTone in self.stopToneLookup:
            # check if we have an unreleased final consonant
            unreleasedFinal, vowelLength = self.db.selectSingleEntry(
                "CantoneseIPAInitialFinal", ["UnreleasedFinal", "VowelLength"],
                {"IPA": plainSyllable})
            if unreleasedFinal:
                return self.stopToneLookup[baseTone][vowelLength]

        if baseTone in self.STOP_TONES:
            # general stop tone that couldn't be dealt with
            raise InvalidEntityError("Invalid tone information given for '" \
                + plainEntity + "': '" + str(tone) + "'")

        return baseTone

    def getBaseToneForToneMark(self, toneMark):
        """
        Gets the base tone (one of the 6/7 general tones) for the given tone
        mark.

        @type toneMark: str
        @param toneMark: tone mark representation of the tone
        @rtype: str
        @return: base tone
        @raise InvalidEntityError: if the toneMark does not exist.
        """
        if self.toneMarkLookup == None:
            # create lookup dict
            self.toneMarkLookup = {}
            toneMarkType = self.getOption('toneMarkType')
            for tone in self.TONE_MARK_MAPPING[toneMarkType]:
                mark = self.TONE_MARK_MAPPING[toneMarkType][tone]

                # get base tone
                reportTone = tone
                if reportTone not in self.TONES:
                    if self.getOption('stopTones') == 'general':
                        reportTone = self.STOP_TONES[tone]
                    elif self.getOption('stopTones') == 'none':
                        reportTone, _ = self.STOP_TONES_EXPLICIT[tone]

                if mark not in self.toneMarkLookup \
                    or (mark in self.TONE_MARK_PREFER[toneMarkType] \
                    and self.TONE_MARK_PREFER[toneMarkType][mark] == tone):
                    self.toneMarkLookup[mark] = reportTone

        if toneMark in self.toneMarkLookup:
            return self.toneMarkLookup[toneMark]
        else:
            raise InvalidEntityError("Invalid tone mark given with '" \
                + toneMark + "'")
