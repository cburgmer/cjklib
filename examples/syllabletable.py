#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Provides a class to create a syllable table with initial and final sounds of a
romanisation drawn on the axis.

Example
=======

Generate a table for Pinyin following the ISO 7098 Annex A table::
    >>> import syllabletable
    >>> gen = syllabletable.SyllableTableBuilder()
    >>> table, notIncluded = gen.build('ISO 7098')

Write an HTML table:
    >>> import codecs
    >>> def s(c): return c if c else ''
    ... 
    >>> table, notIncluded = gen.buildWithHead('ISO 7098')
    >>> f = codecs.open('/tmp/table.html', 'w', 'utf8')
    >>> print >> f, "<html><body><table>"
    >>> print >> f, "\n".join(("<tr>%s</tr>" % ''.join(
    ...     ('<td>%s</td>' % s(c)) for c in row)) for row in table)
    >>> print >> f, "</table>"
    >>> print >> f, "Not included are %s" % ", ".join(notIncluded.keys())
    >>> print >> f, "</body></html>"
    >>> f.close()

2008 Christoph Burgmer (cburgmer@ira.uka.de)

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

@todo Impl: Generalise for readings without tones.
"""

from cjklib import reading

class InitialFinalIterator:
    """Base class for placement rules."""
    def __init__(self, initialFinalIterator):
        self.initialFinalIterator = initialFinalIterator

class PinyinYeIterator(InitialFinalIterator):
    u"""
    Converts Pinyin syllable I{ye} to I{yê} (points out pronunciation [ɛ]).
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final == u'e' and initial == u'y':
                yield(u'y', u'ê', syllable)
            else:
                yield(initial, final, syllable)

class PinyinRemoveSpecialEIterator(InitialFinalIterator):
    u"""
    Removes special syllable I{ê}. This is useful when it collides with I{e} in
    the case where it points out exceptional pronunciation [ɛ].
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final == u'ê' and initial == u'':
                yield(u'', u'', syllable)
            else:
                yield(initial, final, syllable)

class PinyinEVowelIterator(InitialFinalIterator):
    u"""
    Adds a second form I{ê} for I{e} (points out exceptional pronunciation [ɛ]).
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final == u'e' and initial == u'':
                yield(u'', u'e', syllable)
                yield(u'', u'ê', syllable)
            else:
                yield(initial, final, syllable)

class PinyinIExtendedVowelIterator(InitialFinalIterator):
    u"""
    Converts Pinyin finals for I{'zi'}, I{'ci'}, I{'si'}, I{'zhi'}, I{'chi'},
    I{'shi'} and I{ri} to I{ɿ} and I{ʅ} to separate them from finals
    pronounced equal to I{yi}.
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final == u'i' and initial in [u'z', u'c', u's']:
                yield(initial, u'ɿ', syllable)
            elif final == u'i' and initial in [u'zh', u'ch', u'sh', u'r']:
                yield(initial, u'ʅ', syllable)
            else:
                yield(initial, final, syllable)

class PinyinIVowelIterator(InitialFinalIterator):
    """
    Converts Pinyin finals for I{'zi'}, I{'ci'}, I{'si'}, I{'zhi'}, I{'chi'},
    I{'shi'} and I{ri} to I{-i} to separate them from finals pronounced equal to
    I{yi}.
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final == u'i' and initial in [u'z', u'c', u's', u'zh', u'ch',
                u'sh', u'r']:
                yield(initial, u'-i', syllable)
            else:
                yield(initial, final, syllable)

class PinyinVVowelIterator(InitialFinalIterator):
    u"""
    Converts Pinyin finals which coda includes the I{ü} (IPA [y]) vowel but is
    written I{u} to a representation with I{ü}.
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final in [u'u', u'ue', u'uan', u'un'] \
                and initial in  [u'y', u'j', u'q', u'x']:
                final = u'ü' + final[1:]
                yield(initial, final, syllable)
            else:
                yield(initial, final, syllable)

class PinyinOEFinalIterator(InitialFinalIterator):
    u"""
    Merges finals I{o} and I{e} together to final I{o/e}, omitting zero initial
    I{o} and all other syllables with final I{o} with initial not in I{b}, I{p},
    I{m}, I{f}. In return syllables with initials I{b}, I{p}, I{m}, I{f} and
    final I{e} remain unchanged.
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if (final == u'o' and initial in ['b', 'p', 'm', 'f']) \
                or (final == u'e' and initial not in ['b', 'p', 'm', 'f']):
                yield(initial, 'o/e', syllable)
            else:
                yield(initial, final, syllable)

class PinyinUnpronouncedInitialsIterator(InitialFinalIterator):
    """
    Converts Pinyin forms with initials I{y} and I{w} to initial-less forms.
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if initial in [u'y', u'w'] and (final[0] in [u'i', u'u', u'ü']):
                yield(u'', final, syllable)
            elif initial == u'y' and final == u'ou':
                yield(u'', u'iu', syllable)
            elif initial == u'w' and final == u'en':
                yield(u'', u'un', syllable)
            elif initial == u'w' and final == u'ei':
                yield(u'', u'ui', syllable)
            elif initial == u'y':
                yield(u'', u'i' + final, syllable)
            elif initial == u'w':
                yield(u'', u'u' + final, syllable)
            else:
                yield(initial, final, syllable)

class RemoveSyllabicDiacriticIterator(InitialFinalIterator):
    u"""
    Removes a syllabic indicator in form of the combining diacritic U+0329.
    """
    def __iter__(self):
        for initial, final, syllable in self.initialFinalIterator:
            if final == '':
                yield(initial.replace(u'\u0329', ''), final, syllable)
            else:
                yield(initial, final, syllable)

class SyllableTableBuilder:
    """
    Builds a table of syllables with initials and finals on the axis.
    """
    INITIAL_MAPPING = {'Pinyin': [u'b', u'p', u'm', u'f', u'd', u't', u'n',
            u'l', u'z', u'c', u's', u'zh', u'ch', u'sh', u'r', u'j', u'q', u'x',
            u'g', u'k', u'h', u'w', u'y', u''],
        'Jyutping': [u'', u'b', u'p', u'm', u'f', u'd', u't', u'n', u'l', u'g',
            u'k', u'ng', u'h', u'gw', u'kw', u'w', u'z', u'c', u's', u'j'],
        'ShanghaineseIPA': [u'ŋ', u'b', u'd', u'ɲ', u'ɕ', u'ʥ', u'ʑ', u'ɦ',
            u'ʦ', u'ʦʰ', u'ʨʰ', u'ʨ', u'f', u'g', u'h', u'k', u'kʰ', u'l',
            u'm', u'm\u0329', u'n', u'p', u'pʰ', u's', u't', u'tʰ', u'v', u'z',
            u'']}
    FINAL_MAPPING = {'Pinyin': [u'a', u'ao', u'ai', u'an', u'ang', u'o', u'ou',
            u'ong', u'u', u'ü', u'ua', u'uai', u'uan', u'uang', u'ue', u'üe',
            u'un', u'uo', u'ui', u'e', u'er', u'ei', u'en', u'eng', u'i', u'ia',
            u'iao', u'iu', u'ie', u'ian', u'in', u'iang', u'ing', u'iong', u'n',
            u'ng', u'm', u'ê'],
        'Jyutping': [u'i', u'ip', u'it', u'ik', u'im', u'in', u'ing', u'iu',
            u'yu', u'yut', u'yun', u'u', u'up', u'ut', u'uk', u'um', u'un',
            u'ung', u'ui', u'e', u'ep', u'et', u'ek', u'em', u'en', u'eng',
            u'ei', u'eu', u'eot', u'eon', u'eoi', u'oe', u'oet', u'oek',
            u'oeng', u'oei', u'o', u'ot', u'ok', u'om', u'on', u'ong', u'oi',
            u'ou', u'ap', u'at', u'ak', u'am', u'an', u'ang', u'ai', u'au',
            u'aa', u'aap', u'aat', u'aak', u'aam', u'aan', u'aang', u'aai',
            u'aau', u'm', u'ng'],
        'ShanghaineseIPA': [u'', u'a', u'ã', u'aˀ', u'ø', u'ɿ', u'ɤ', u'ɑ',
            u'ɔ', u'ə', u'ɛ', u'əŋ', u'ɑˀ', u'ɔˀ', u'əˀ', u'ɑ̃', u'əl',
            u'en', u'ən', u'i', u'ia', u'iɤ', u'iɑ', u'iɔ',
            u'iɪˀ', u'iɑˀ', u'iɑ̃', u'in', u'ioŋ', u'ioˀ', u'o', u'oŋ',
            u'oˀ', u'u', u'uɑ', u'uɛ', u'uən', u'uɑˀ', u'uəˀ',
            u'uɑ̃', u'y', u'yø', u'yɪˀ', u'yəˀ', u'yn']}

    SCHEME_MAPPING = {'ISO 7098': ('Pinyin', [u'', u'y', u'w', u'b', u'p', u'm',
            u'f', u'd', u't', u'n', u'l', u'z', u'c', u's', u'zh', u'ch', u'sh',
            u'r', u'j', u'q', u'x', u'g', u'k', u'h'],
            [u'a', u'o', u'e' , u'ê', u'-i', u'er', u'ai', u'ei', u'ao', u'ou',
            u'an', u'en', u'ang', u'eng', u'ong', u'i', u'ia', u'iao', u'ie',
            u'iu', u'ian', u'in', u'iang', u'ing', u'iong', u'u', u'ua', u'uo',
            u'uai', u'ui', u'uan', u'un', u'uang', u'ü', u'üe', u'üan', u'ün'],
            [PinyinRemoveSpecialEIterator, PinyinYeIterator,
            PinyinEVowelIterator, PinyinIVowelIterator, PinyinVVowelIterator]),
        'Praktisches Chinesisch': ('Pinyin', [u'', u'b', u'p', u'm', u'f', u'd',
            u't', u'n', u'l', u'z', u'c', u's', u'zh', u'ch', u'sh', u'r', u'j',
            u'q', u'x', u'g', u'k', u'h'],
            [u'a', u'o', u'e' , u'ê', u'-i', u'er', u'ai', u'ei', u'ao', u'ou',
            u'an', u'en', u'ang', u'eng', u'ong', u'i', u'ia', u'iao', u'ie',
            u'iu', u'ian', u'in', u'iang', u'ing', u'iong', u'u', u'ua', u'uo',
            u'uai', u'ui', u'uan', u'un', u'uang', u'ueng', u'ü', u'üe', u'üan',
            u'ün'],
            [PinyinRemoveSpecialEIterator, PinyinEVowelIterator,
            PinyinIVowelIterator, PinyinVVowelIterator,
            PinyinUnpronouncedInitialsIterator]),
        'Pinyin.info': ('Pinyin', [u'b', u'p', u'm', u'f', u'd',
            u't', u'n', u'l', u'g', u'k', u'h', u'z', u'c', u's', u'zh', u'ch',
            u'sh', u'r', u'j', u'q', u'x', u'', ],
            [u'a', u'o', u'e', u'ai', u'ei', u'ao', u'ou', u'an', u'ang', u'en',
            u'eng', u'ong', u'u', u'ua', u'uo', u'uai', u'ui', u'uan', u'uang',
            u'un', u'ueng', u'i', u'ia', u'ie', u'iao', u'iu', u'ian', u'in',
            u'ing', u'iang', u'iong', u'ü', u'üe', u'üan', u'ün'],
            [PinyinVVowelIterator, PinyinUnpronouncedInitialsIterator]),
        'Pinyin dewiki': ('Pinyin', [u'b', u'p', u'm', u'f', u'd', u't', u'n',
            u'l', u'z', u'c', u's', u'zh', u'ch', u'sh', u'r', u'j', u'q', u'x',
            u'g', u'k', u'h', u'w', u'y', u''],
            [u'a', u'ao', u'ai', u'an', u'ang', u'o', u'ou', u'ong', u'u', u'ü',
            u'ua', u'uai', u'uan', u'uang', u'ue', u'üe', u'un', u'uo', u'ui',
            u'e', u'er', u'ei', u'en', u'eng', u'i', u'ia', u'iao', u'iu',
            u'ie', u'ian', u'in', u'iang', u'ing', u'iong'],
            []),
        'PinyinExtendedScheme': ('Pinyin', [u'', u'b', u'p', u'm', u'f', u'd',
            u't', u'n', u'l', u'z', u'c', u's', u'zh', u'ch', u'sh', u'r', u'j',
            u'q', u'x', u'g', u'k', u'h'],
            [u'a', u'o', u'e' , u'ê', u'ɿ', u'ʅ', u'er', u'ai', u'ei', u'ao',
            u'ou', u'an', u'en', u'ang', u'eng', u'ong', u'i', u'ia', u'iao',
            u'ie', u'iu', u'iai', u'ian', u'in', u'iang', u'ing', u'io',
            u'iong', u'u', u'ua', u'uo', u'uai', u'ui', u'uan', u'un', u'uang',
            u'ueng', u'ü', u'üe', u'üan', u'ün', u'm', u'n', u'ng'],
            [PinyinIExtendedVowelIterator, PinyinVVowelIterator,
            PinyinUnpronouncedInitialsIterator]),
        'Introduction1972': ('Pinyin', [u'', u'b', u'p', u'm', u'f', u'z',
            u'c', u's', u'd', u't', u'n', u'l', u'zh', u'ch', u'sh', u'r', u'j',
            u'q', u'x', u'g', u'k', u'h'],
            [u'a', u'ai', u'an', u'ang', u'ao', u'o/e' , u'ei', u'en', u'eng',
            u'ou', u'er', u'ɿ', u'ʅ', u'i', u'ia', u'ian', u'iang', u'iao',
            u'ie', u'in', u'ing', u'iu', u'u', u'ua', u'uai', u'uan', u'uang',
            u'uo', u'ui', u'un', u'ong', u'ü', u'üan', u'üe', u'ün', u'iong'],
            [PinyinIExtendedVowelIterator, PinyinVVowelIterator,
            PinyinUnpronouncedInitialsIterator, PinyinOEFinalIterator]),
        'CUHK': ('Jyutping', [u'', u'b', u'p', u'm', u'f', u'd', u't', u'n',
            u'l', u'g', u'k', u'ng', u'h', u'gw', u'kw', u'w', u'z', u'c', u's',
            u'j'],
            [u'i', u'ip', u'it', u'ik', u'im', u'in', u'ing', u'iu', u'yu',
            u'yut', u'yun', u'u', u'up', u'ut', u'uk', u'um', u'un', u'ung',
            u'ui', u'e', u'ep', u'et', u'ek', u'em', u'en', u'eng', u'ei',
            u'eu', u'eot', u'eon', u'eoi', u'oe', u'oet', u'oek', u'oeng', u'o',
            u'ot', u'ok', u'on', u'ong', u'oi', u'ou', u'ap', u'at', u'ak',
            u'am', u'an', u'ang', u'ai', u'au', u'aa', u'aap', u'aat', u'aak',
            u'aam', u'aan', u'aang', u'aai', u'aau', u'm', u'ng'],
            []),
        'CUHK extended': ('Jyutping', [u'', u'b', u'p', u'm', u'f', u'd', u't',
            u'n', u'l', u'g', u'k', u'ng', u'h', u'gw', u'kw', u'w', u'z', u'c',
            u's', u'j'],
            [u'i', u'ip', u'it', u'ik', u'im', u'in', u'ing', u'iu', u'yu',
            u'yut', u'yun', u'u', u'up', u'ut', u'uk', u'um', u'un', u'ung',
            u'ui', u'e', u'ep', u'et', u'ek', u'em', u'en', u'eng', u'ei',
            u'eu', u'eot', u'eon', u'eoi', u'oe', u'oet', u'oek', u'oeng',
            u'oei', u'o', u'ot', u'ok', u'om', u'on', u'ong', u'oi', u'ou',
            u'ap', u'at', u'ak', u'am', u'an', u'ang', u'ai', u'au', u'aa',
            u'aap', u'aat', u'aak', u'aam', u'aan', u'aang', u'aai', u'aau',
            u'm', u'ng'],
            []),
        'FullShanghainese': ('ShanghaineseIPA', ['',
            u'ɦ', u'h',
            u'ŋ', u'k', u'kʰ', u'g',
            u'ɲ', u'ʨ', u'ʨʰ', u'ʥ', u'ɕ', u'ʑ',
            u'm', u'b', u'p', u'pʰ',
            u'l',
            u'n', u't', u'tʰ', u'd', u'ʦ', u'ʦʰ', u's', u'z',
            u'f', u'v'],
            [u'', u'ɑ', u'ɑ̃', u'ã', u'ɑˀ',
            u'ɛ', u'əˀ', u'ən', u'əl', u'ɿ', u'ɤ',
            u'i', u'iɑ', u'iɑ̃', u'iɑˀ', u'iɤ', u'iɔ', u'iɪˀ', u'in',
            u'ioˀ', u'ioŋ',
            u'o', u'oˀ', u'oŋ', u'ø', u'ɔ', u'ɔˀ',
            u'u', u'uɑ̃', u'uɑ', u'uɑˀ', u'uɛ', u'uəˀ', u'uən',
            u'y', u'yn', u'yø', u'yɪˀ', u'yəˀ'],
            [RemoveSyllabicDiacriticIterator])}
    u"""
    Predefined schemes based on:
        - ISO 7098, the Pinyin syllable table given in Annex A.
        - Praktisches Chinesisch, Band I, Kommerzieller Verlag, Beijing 2001,
            ISBN 7-100-01675-4.
        - Pinyin.info, Mark Swofford: Combinations of initials and finals,
            Pinyin.info, U{http://www.pinyin.info/rules/initials_finals.html}.
        - Pinyin dewiki, table from Wikipedia article
            U{http://de.wikipedia.org/wiki/Pinyin}.
        - PinyinExtendedScheme, based on "Praktisches Chinesisch", extended to
            include all syllables, distinction between -i in zi and zhi.
        - Introduction1972, based on "An Introduction to the Pronunciation of
            Chinese". Francis D.M. Dow, Edinburgh, 1972, missing finals 'm',
            'n', 'ng', 'ê', 'iai', 'io', 'ueng'.
        - CUHK, Research Centre for Humanities Computing of the Research
            Institute for the Humanities (RIH), Faculty of Arts, The Chinese
            University of Hong Kong - 粵音節表 (Table of Cantonese Syllables):
            U{http://humanum.arts.cuhk.edu.hk/Lexis/Canton2/syllabary/}.
        - CUHK extended, same as CUHK except finals I{oei} and I{om} being
            added.
    """

    class SyllableIterator:
        """Defines a simple Iterator for a given syllable list."""
        def __init__(self, syllableList, initialSet, finalSet):
            self.syllableList = syllableList
            self.initialSet = initialSet
            self.finalSet = finalSet
            self.unresolvedSyllables = set()

        def __iter__(self):
            for syllable in self.syllableList:
                syllableResolved = False
                for i in range(0, len(syllable)+1):
                    initial = syllable[0:i]
                    final = syllable[i:]
                    if initial in self.initialSet and final in self.finalSet:
                        yield(initial, final, syllable)
                        syllableResolved = True
                if not syllableResolved:
                    self.unresolvedSyllables.add(syllable)

        def getUnresolvedSyllables(self):
            """
            Returns a set of unresolved syllables.

            During iteration some syllables might not be resolved, due to
            missing initial of final values. These syllables are returned by
            this method.
            """
            return self.unresolvedSyllables

    def __init__(self, databaseSettings={}, dbConnectInst=None):
        """
        Initialises the SyllableTableBuilder.

        If no parameters are given default values are assumed for the connection
        to the database. Other options can be either passed as dictionary to
        databaseSettings, or as an instantiated L{DatabaseConnector} given to
        dbConnectInst, the latter one will be preferred.

        @type databaseSettings: dictionary
        @param databaseSettings: database settings passed to the
            L{DatabaseConnector}, see there for feasible values
        @type dbConnectInst: object
        @param dbConnectInst: instance of a L{DatabaseConnector}
        """
        # get reading factory
        self.readingFactory = reading.ReadingFactory(databaseSettings,
            dbConnectInst)
        self.initialMapping = {}
        self.finalMapping = {}
        for romanisation in self.INITIAL_MAPPING:
            self.setInitials(romanisation, self.INITIAL_MAPPING[romanisation])
        for romanisation in self.FINAL_MAPPING:
            self.setFinals(romanisation, self.FINAL_MAPPING[romanisation])

    def setInitials(self, romanisation, initialList):
        """
        Adds a list of initials for the given romanisation used in
        decomposition.

        @type romanisation: string
        @param romanisation: name of romanisation according to L{cjklib} naming
        @type initialList: list of strings
        @param initialList: list of syllable initials
        """
        self.initialMapping[romanisation] = initialList

    def setFinals(self, romanisation, finalList):
        """
        Adds a list of finals for the given romanisation used in decomposition.

        @type romanisation: string
        @param romanisation: name of romanisation according to L{cjklib} naming
        @type finalList: list of strings
        @param finalList: list of syllable finals
        """
        self.finalMapping[romanisation] = finalList

    def addScheme(self, romanisation, schemeName, initialList, finalList,
        ruleList):
        """
        Adds a table scheme to the builder.

        @type romanisation: string
        @param romanisation: name of romanisation according to L{cjklib} naming
        @type schemeName: string
        @param schemeName: name of new Scheme
        @type initialList: list of strings
        @param initialList: list of syllable initials
        @type finalList: list of strings
        @param finalList: list of syllable finals
        @type ruleList: list of functions
        @param ruleList: rules to process the syllables from database
        """
        if self.SCHEME_MAPPING.has_key(schemeName):
            raise ValueError("Scheme '" + schemeName + "' already exists")
        self.SCHEME_MAPPING[schemeName] = (romanisation, initialList, finalList,
            ruleList)

    def removeScheme(self, schemeName):
        """
        Removes a table scheme from the builder.

        @type schemeName: string
        @param schemeName: name of new Scheme
        """
        del self.SCHEME_MAPPING[schemeName]

    def build(self, schemeName):
        """
        Builds a table for all available syllables where different initials are
        grouped per row and finals grouped by column.

        @type schemeName: string
        @param schemeName: name of new Scheme
        @rtype: tuple (list of list of strings, dict)
        @return: two-dimensional table with initials in rows and finals in
            columns and dict of syllables including initial/finals that couldn't
            be inserted into the table.
        """
        romanisation, initialList, finalList, ruleList = \
            self.SCHEME_MAPPING[schemeName]
        # get syllables
        op = self.readingFactory.createReadingOperator(romanisation)
        baseIterator = SyllableTableBuilder.SyllableIterator(\
            op.getPlainReadingEntities(),
            set(self.initialMapping[romanisation]),
            set(self.finalMapping[romanisation]))
        ifIterator = baseIterator
        # stack up rules
        for classObj in ruleList:
            ifIterator = classObj(ifIterator)
        # build table
        table = [[None for final in finalList] for initial in initialList]
        notIncludedSyllables = {}
        for initial, final, syllable in ifIterator:
            try:
                initialIdx = initialList.index(initial)
                finalIdx = finalList.index(final)
            except ValueError:
                notIncludedSyllables[syllable] = (initial, final)
                continue
            if table[initialIdx][finalIdx] \
                and table[initialIdx][finalIdx] != syllable:
                raise ValueError("several syllables at cell '" + initial \
                    + "', '" + final + "' (initial, final) with '" \
                    + table[initialIdx][finalIdx] + "' and '" \
                    + syllable + "'")
            table[initialIdx][finalIdx] = syllable
        # get unresolved syllables
        for syllable in baseIterator.getUnresolvedSyllables():
            notIncludedSyllables[syllable] = None
        return table, notIncludedSyllables

    def buildWithHead(self, schemeName):
        """
        Builds a table for all available syllables where different initials are
        grouped per row and finals grouped by column including table header.

        @type schemeName: string
        @param schemeName: name of new Scheme
        @rtype: tuple (list of list of strings, list of strings)
        @return: two-dimensional table with initials in rows and finals in
            columns and dict of syllables including initial/finals that couldn't
            be inserted into the table.
        """
        table, notIncludedSyllables = self.build(schemeName)
        romanisation, initialList, finalList, ruleList = \
            self.SCHEME_MAPPING[schemeName]
        # add finals to first row
        firstRow = ['']
        firstRow.extend(finalList)
        headTable = [firstRow]
        for i, initial in enumerate(initialList):
            nextRow = [initial]
            nextRow.extend(table[i])
            headTable.append(nextRow)
        return headTable, notIncludedSyllables

def transposeTable(table):
    """Transposes the given table."""
    tableT = []
    for idx in range(0, len(table[0])):
        newLine = []
        for line in table:
            newLine.append(line[idx])
        tableT.append(newLine)
    return tableT
