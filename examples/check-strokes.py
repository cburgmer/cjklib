#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Checks which characters have stroke support and which don't. Prints a list of
components that given stroke data could help increase stroke support manifold.

2010 Christoph Burgmer (cburgmer@ira.uka.de)

License: MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import locale
from optparse import OptionParser

from cjklib.characterlookup import CharacterLookup
from cjklib.exception import NoInformationError

class StrokeChecker(object):
    ALLOWED_COMPONENT_STRUCTURE = [u'⿰', u'⿱', u'⿵', u'⿶', u'⿸', u'⿹', u'⿺',
        u'⿲', u'⿳']
    """
    Component structures that allow derivation of stroke order from components.
    """

    MIN_COMPONENT_PRODUCTIVITY = 2
    """
    Min productivity when reporting out-domain components that could help boost
    the in-domain set.
    """

    def __init__(self, options, args):
        self._locale = options.locale
        self._characterDomain = options.characterDomain

        self._cjk = CharacterLookup(self._locale, self._characterDomain)

    def run(self):
        charCount = 0
        charFullCount = 0

        missingCharsDict = {}
        missingSingleCharacters = []
        # iterate through all characters of the character set
        for char in self._cjk.getDomainCharacterIterator():
        #for char in iter([u'亄', u'乿', u'仜', u'伳']): # DEBUG
            charCount += 1
            if charCount % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()

            hasFullOrder, missingChars = self.checkStrokeOrder(char)

            if hasFullOrder:
                charFullCount += 1
            else:
                if missingChars:
                    # list components that can help us build this transform.
                    for missing in missingChars:
                        if missing not in missingCharsDict:
                            missingCharsDict[missing] = []
                        missingCharsDict[missing].append(char)
                else:
                    missingSingleCharacters.append(char)

        sys.stdout.write('\n')

        output_encoding = sys.stdout.encoding or locale.getpreferredencoding() \
            or 'ascii'

        print 'Total characters: %d' % charCount
        print 'Characters with full stroke data: %d (%d%%)' % (charFullCount,
            100 * charFullCount / charCount)


        # missing single characters
        # Extend by those with components, that have a component with low
        #   productivity.
        inDomainComponents = set(
            self._cjk.filterDomainCharacters(missingCharsDict.keys()))

        lowProductivityComponentChars = []
        for component, chars in missingCharsDict.items():
            if component not in inDomainComponents \
                and len(chars) < self.MIN_COMPONENT_PRODUCTIVITY:
                lowProductivityComponentChars.extend(chars)
                del missingCharsDict[component]
        missingSingleCharacters.extend(lowProductivityComponentChars)

        print 'Missing single characters:',
        print ''.join(missingSingleCharacters).encode(output_encoding,
            'replace')

        # remove characters that we already placed in "single"
        _missingSingleCharacters = set(missingSingleCharacters)
        for component, chars in missingCharsDict.items():
            missingCharsDict[component] = list(
                set(chars) - _missingSingleCharacters)
            if not missingCharsDict[component]:
                del missingCharsDict[component]

        # missing components

        missingComponents = sorted(missingCharsDict.items(),
            key=lambda (x,y): len(y))
        missingComponents.reverse()

        inDomainComponentList = [(component, chars) \
            for component, chars in missingComponents \
            if component in inDomainComponents]
        # only show "out-domain" components if they have productivity > 1
        outDomainComponentList = [(component, chars) \
            for component, chars in missingComponents \
            if component not in inDomainComponents and len(chars) > 1]

        print 'Missing components: %d' % (len(inDomainComponentList) \
            + len(outDomainComponentList))
        print 'Missing in-domain components:',
        print ', '.join(['%s (%s)' % (component, ''.join(chars)) \
            for component, chars in inDomainComponentList])\
            .encode(output_encoding, 'replace')
        print 'Missing out-domain components:',
        print ', '.join(['%s (%s)' % (component, ''.join(chars)) \
            for component, chars in outDomainComponentList])\
            .encode(output_encoding, 'replace')

    def checkStrokeOrder(self, char, glyph=None):
        try:
            self._cjk.getStrokeOrder(char, glyph)
            return True, []
        except NoInformationError:
            pass

        # add decompositions, limit to upper bound max_samples
        missingChars = []
        decompositions = self._cjk.getDecompositionEntries(char, glyph)
        for decomposition in decompositions:
            hasFullOrder, _, missing = self._checkStrokeOrderFromDecomposition(
                decomposition)
            assert not hasFullOrder
            missingChars.extend(missing)

        return False, missingChars

    def _checkStrokeOrderFromDecomposition(self, decomposition, index=0):
        """Goes through a decomposition"""
        if type(decomposition[index]) != type(()):
            # IDS operator
            character = decomposition[index]
            missingChars = []
            hasFullOrder = True
            if CharacterLookup.isBinaryIDSOperator(character):
                # check for IDS operators we can't make any order
                # assumption about
                if character not in self.ALLOWED_COMPONENT_STRUCTURE:
                    return False, index, []
                else:
                    # Get stroke order for both components
                    for _ in range(0, 2):
                        fullOrder, index, missing \
                            = self._checkStrokeOrderFromDecomposition(
                                decomposition, index+1)
                        if not fullOrder:
                            missingChars.extend(missing)

                        hasFullOrder = hasFullOrder and fullOrder

            elif CharacterLookup.isTrinaryIDSOperator(character):
                # Get stroke order for three components
                for _ in range(0, 3):
                    fullOrder, index, missing \
                        = self._checkStrokeOrderFromDecomposition(
                            decomposition, index+1)
                    if not fullOrder:
                        missingChars.extend(missing)

                    hasFullOrder = hasFullOrder and fullOrder
            else:
                assert False, 'not an IDS character'

            return hasFullOrder, index, missingChars
        else:
            # no IDS operator but character
            char, glyph = decomposition[index]
            # if the character is unknown or there is none raise
            if char == u'？':
                return False, index, []
            else:
                # recursion
                fullOrder, missingChars = self.checkStrokeOrder(char, glyph)
                if not fullOrder and not missingChars:
                    missingChars = [char]
                return fullOrder, index, missingChars

        assert False


parser = OptionParser(usage="usage: %prog [options] [output-path]")

parser.add_option("-l", "--locale",
                  type="string", dest="locale",
                  default='T',
                  help="Character locale of target characters")
parser.add_option("-d", "--domain",
                  type="string", dest="characterDomain",
                  default='Unicode',
                  help="Character domain of target characters")

(options, args) = parser.parse_args()

#try:
StrokeChecker(options, args).run()
#except Exception, e:
    #sys.stderr.write(unicode(e) + "\n\n")
    #parser.print_help()
    #sys.exit(1)
