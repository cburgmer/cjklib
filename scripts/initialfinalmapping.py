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
Creates a mapping between two readings based on a mapping of initial and final
parts.

2008 Christoph Burgmer (cburgmer@ira.uka.de)

Pinyin
======
It is important to deal with forms zi, ci, si / zhi, chi, shi, ri and forms with
a single e as de, te, e and others.

Source:
    - Hànyǔ Pǔtōnghuà Yǔyīn Biànzhèng (汉语普通话语音辨正). Page 15, Běijīng Yǔyán
        Dàxué Chūbǎnshè (北京语言大学出版社), 2003, ISBN 7-5619-0622-6.

Jyutping to Cantonese Yale
==========================
Sources:
    - Stephen Matthews, Virginia Yip: Cantonese: A Comprehensive Grammar.
        Routledge, 1994, ISBN 0-415-08945-X.
    - Parker Po-fei Huang, Gerard P. Kok: Speak Cantonese (Book I). Revised
        Edition, Yale University, 1999, ISBN 0-88710-094-5:

Entries were derived from the JyutpingSyllable using the mapping defined in
"Cantonese: A Comprehensive Grammar" where a final is mentioned in the source
'Speak Cantonese'.

The following finals found in some references for the LSHK's Jyutping are not
listed in the source 'Speak Cantonese':
    - -eu
    - -em
    - -en
    - -ep
    - -et

'Cantonese: A Comprehensive Grammar' though mentions finals -em, -up, -et,
-en, -um for Cantonese Yale (p. 20, chapter 1.3.1).

Jyutping to IPA
===============
Source:
    - Robert S. Bauer, Paul K. Benedikt: Modern Cantonese Phonology
        (摩登廣州話語音學). Walter de Gruyter, 1997, ISBN 3-11-014893-5.


Pinyin to GR
============
Source:
    - Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
        Press, Berkeley, 1968, ISBN 0-520-00219-9.

@todo Lang: Support for Erhua.
"""

import sys
import locale
from cjklib.reading import ReadingFactory

# TABLE 1
INITIAL_RULES = {('Jyutping', 'CantoneseYale'): {'': '', 'b': 'b', 'p': 'p',
        'm': 'm', 'f': 'f', 'd': 'd', 't': 't', 'l': 'l', 'n': 'n', 'z': 'j',
        'c': 'ch', 's': 's', 'g': 'g', 'k': 'k', 'h': 'h', 'ng': 'ng',
        'gw': 'gw', 'kw': 'kw', 'j': 'y', 'w': 'w'},
    ('Pinyin', 'MandarinIPA'): {u'': u'', u'b': u'p', u'p': u'p‘', u'm': u'm',
        u'f': u'f', u'd': u't', u't': u't‘', u'n': u'n', u'l': u'l',
        u'z': u'ts', u'c': u'ts‘', u's': u's', u'zh': u'tʂ', u'ch': u'tʂ‘',
        u'sh': u'ʂ', u'r': u'ʐ', u'j': u'tɕ', u'q': u'tɕ‘', u'x': u'ɕ',
        u'g': u'k', u'k': u'k‘', u'h': u'x'},
    ('Jyutping', 'CantoneseIPA'): {'': '', 'b': 'p', 'p': u'pʰ', 'd': 't',
        't': u'tʰ', 'g': 'k', 'k': u'kʰ', 'gw': u'kʷ', 'kw': u'kʰʷ', 'm': 'm',
        'n': 'n', 'ng': u'ŋ', 'f': 'f', 's': 's', 'h': 'h', 'z': 'ts',
        'c': u'tsʰ', 'w': 'w', 'l': 'l', 'j': 'j'},
    ('Pinyin', 'GR'): {'': '', 'b': 'b', 'p': 'p', 'm': 'm', 'f': 'f', 'd': 'd',
        't': 't', 'n': 'n', 'l': 'l', 'g': 'g', 'k': 'k', 'h': 'h', 'j': 'j',
        'r': 'r', 's': 's', 'zh': 'j', 'q': 'ch', 'x': 'sh', 'z': 'tz',
        'c': 'ts', 'ch': 'ch', 'sh': 'sh'},
    ('Pinyin', 'WadeGiles'): {'': '', 'b': 'p', 'p': u'p’', 'm': 'm', 'f': 'f',
        'd': 't', 't': u't’', 'n': 'n', 'l': 'l', 'g': 'k', 'k': u'k’',
        'h': 'h', 'j': 'ch', 'q': u'ch’', 'x': 'hs', 'zh': 'ch', 'ch': u'ch’',
        'sh': 'sh', 'r': 'j', 'z': {u'-ŭ': 'ts', u'ŭ': 'tz'},
        'c': {u'-ŭ': u'ts’', u'ŭ': u'tz’'},
        's': {u'-ŭ': 's', u'ŭ': 'ss'}},
    }
"""
Mapping of syllable initials.
For ambiguous pronunciations a non-injective mapping can be achieved by giving a
dictionary of possibilities, the key giving the name of the feature.
"""

# TABLE 1
FINAL_RULES = {('Jyutping', 'CantoneseYale'): {'aa': ('a', ''),
        'aai': ('aa', 'i'), 'aau': ('aa', 'u'), 'aam': ('aa', 'm'),
        'aan': ('aa', 'n'), 'aang': ('aa', 'ng'), 'aap': ('aa', 'p'),
        'aat': ('aa', 't'), 'aak': ('aa', 'k'), 'ai': ('a', 'i'),
        'au': ('a', 'u'), 'am': ('a', 'm'), 'an': ('a', 'n'),
        'ang': ('a', 'ng'), 'ap': ('a', 'p'), 'at': ('a', 't'),
        'ak': ('a', 'k'), 'e': ('e', ''), 'eng': ('e', 'ng'), 'ek': ('e', 'k'),
        'ei': ('e', 'i'), 'oe': ('eu', ''), 'oeng': ('eu', 'ng'),
        'oek': ('eu', 'k'), 'eoi': ('eu', 'i'), 'eon': ('eu', 'n'),
        'eot': ('eu', 't'), 'i': ('i', ''), 'iu': ('i', 'u'), 'im': ('i', 'm'),
        'in': ('i', 'n'), 'ip': ('i', 'p'), 'it': ('i', 't'),
        'ing': ('i', 'ng'), 'ik': ('i', 'k'), 'o': ('o', ''), 'oi': ('o', 'i'),
        'on': ('o', 'n'), 'ong': ('o', 'ng'), 'ot': ('o', 't'),
        'ok': ('o', 'k'), 'ou': ('o', 'u'), 'u': ('u', ''), 'ui': ('u', 'i'),
        'un': ('u', 'n'), 'ut': ('u', 't'), 'ung': ('u', 'ng'),
        'uk': ('u', 'k'), 'yu': ('yu', ''), 'yun': ('yu', 'n'),
        'yut': ('yu', 't'), 'm': ('', 'm'), 'ng': ('', 'ng')},
    ('Pinyin', 'MandarinIPA'): {u'a': u'a', u'o': u'o',
        u'e': {'Default': u'ɤ', '5thTone': u'ə'}, u'ê': u'ɛ', u'er': u'ər',
        u'ai': u'ai', u'ei': u'ei', u'ao': u'au', u'ou': u'ou', u'an': u'an',
        u'en': u'ən', u'ang': u'aŋ', u'eng': u'əŋ', u'ong': u'uŋ', u'i': u'i',
        u'ia': u'ia', u'iao': u'iau', u'ie': u'iɛ', u'iou': u'iəu',
        u'ian': u'iɛn', u'in': u'in', u'iang': u'iɑŋ', u'ing': u'iŋ',
        u'iong': u'yŋ', u'u': u'u', u'ua': u'ua', u'uo': u'uo', u'uai': u'uai',
        u'uei': u'uei', u'uan': u'uan', u'uen': u'uən', u'uang': u'uaŋ',
        u'ueng': u'uəŋ', u'ü': u'y', u'üe': u'yɛ', u'üan': u'yan', u'ün': u'yn',
        u'ɿ': u'ɿ', u'ʅ': u'ʅ'},
    ('Jyutping', 'CantoneseIPA'): {'i': u'iː', 'iu': u'iːw', 'im': u'iːm',
        'in': u'iːn', 'ip': u'iːp̚', 'it': u'iːt̚', 'yu': u'yː', 'yun': u'yːn',
        'yut': u'yːt̚', 'ei': u'ej', 'ing': u'eʲŋ', 'ik': u'eʲk̚', 'e': u'ɛː',
        'eu': u'ɛːw', 'em': u'ɛːm', 'en': u'ɛːn', 'eng': u'ɛːŋ', 'ep': u'ɛːp̚',
        'et': u'ɛːt̚', 'ek': u'ɛːk̚', 'oe': u'œː', 'oeng': u'œːŋ',
        'oek': u'œːk̚', 'eoi': u'ɵy', 'eon': u'ɵn', 'eot': u'ɵt̚', 'ai': u'ɐj',
        'au': u'ɐw', 'am': u'ɐm', 'an': u'ɐn', 'ang': u'ɐŋ', 'ap': u'ɐp̚',
        'at': u'ɐt̚', 'ak': u'ɐk̚', 'aa': u'aː', 'aai': u'aːj', 'aau': u'aːw',
        'aam': u'aːm', 'aan': u'aːn', 'aang': u'aːŋ', 'aap': u'aːp̚',
        'aat': u'aːt̚', 'aak': u'aːk̚', 'u': u'uː', 'ui': u'uːj', 'un': u'uːn',
        'ut': u'uːt̚', 'ou': u'ow', 'ung': u'oʷŋ', 'uk': u'oʷk̚', 'o': u'ɔː',
        'oi': u'ɔːj', 'on': u'ɔːn', 'ong': u'ɔːŋ', 'ot': u'ɔːt̚', 'ok': u'ɔːk̚',
        'm': u'm̩', 'ng': u'ŋ̩'},
    ('Pinyin', 'GR'): {u'a': 'a', u'o': 'o', u'e': 'e', u'ai': 'ai',
        u'ei': 'ei', u'ao': 'au', u'ou': 'ou', u'an': 'an', u'en': 'en',
        u'ang': 'ang', u'eng': 'eng', u'ong': 'ong', u'er': 'el', u'i': 'i',
        u'ia': 'ia', u'ie': 'ie', u'iai': 'iai', u'iao': 'iau', u'iou': 'iou',
        u'ian': 'ian', u'in': 'in', u'iang': 'iang', u'ing': 'ing',
        u'iong': 'iong', u'u': 'u', u'ua': 'ua', u'uo': 'uo', u'uai': 'uai',
        u'uei': 'uei', u'uan': 'uan', u'uen': 'uen', u'uang': 'uang',
        u'ü': 'iu', u'üe': 'iue', u'üan': 'iuan', u'ün': 'iun', u'ɿ': 'y',
        u'ʅ': 'y', u'ueng': 'ueng'},
    ('Pinyin', 'WadeGiles'): {'a': 'a', 'ai': 'ai', 'an': 'an', 'ang': 'ang',
        'ao': 'ao', 'e': {'all_1': u'ê', u'k/k’/h': 'o'},
        u'ê': {'all_1': u'ê', 'all_2': 'o'}, 'ei': 'ei',
        'en': u'ên', 'eng': u'êng', 'er': u'êrh', u'ʅ': 'ih', u'ɿ': u'ŭ',
        'i': 'i', 'ia': 'ia', 'ian': 'ien', 'iang': 'iang', 'iao': 'iao',
        'ie': 'ieh', 'in': 'in', 'ing': 'ing', 'iong': 'iung', 'iou': 'iu',
        'o': 'o', 'ong': 'ung', 'ou': 'ou', 'u': 'u', 'ua': 'ua', 'uai': 'uai',
        'uan': 'uan', 'uang': 'uang', 'uei': {u'-k/k’/': 'ui', u'k/k’/': 'uei'},
        'uen': 'un', 'uo': {u'k/k’/h/sh/': 'uo', u'-k/k’/h/sh/': 'o'},
        u'ü': u'ü', u'üan': u'üan', u'üe': u'üeh', u'ün': u'ün'},
    }
"""
Mapping of syllable finals.
For ambiguous pronunciations a non-injective mapping can be achieved by giving a
dictionary of possibilities, the key giving the name of the feature.

These finals included here don't necessarily represent the actual rendering, as
they might depend on the initial they combine with.
"""

# TABLE 1
EXTRA_SYLLABLES = {('Jyutping', 'CantoneseYale'): {'om': None, 'pet': None,
        'deu': None, 'lem': None, 'loet': None, 'loei': None, 'gep': None,
        'kep': None},
    ('Pinyin', 'MandarinIPA'): {u'yai': None, u'yo': None, u'm': None,
        u'n': None, u'ng': None, u'hm': None, u'hng': None},
    ('Jyutping', 'CantoneseIPA'): {'loet': None, 'loei': None, 'om': None,
        'zi': (u'tʃ', u'iː'), 'ci': (u'tʃʰ', u'iː'), 'zit': (u'tʃ', u'iːt̚'),
        'cit': (u'tʃʰ', u'iːt̚'), 'ziu': (u'tʃ', u'iːw'),
        'ciu': (u'tʃʰ', u'iːw'), 'zim': (u'tʃ', u'iːm'),
        'cim': (u'tʃʰ', u'iːm'), 'zin': (u'tʃ', u'iːn'),
        'cin': (u'tʃʰ', u'iːn'), 'zip': (u'tʃ', u'iːp̚'),
        'cip': (u'tʃʰ', u'iːp̚'), 'syu': (u'ʃ', u'yː'), 'zyu': (u'tʃ', u'yː'),
        'cyu': (u'tʃʰ', u'yː'), 'syun': (u'ʃ', u'yːn'), 'zyun': (u'tʃ', u'yːn'),
        'cyun': (u'tʃʰ', u'yːn'), 'syut': (u'ʃ', u'yːt̚'),
        'zyut': (u'tʃ', u'yːt̚'), 'cyut': (u'tʃʰ', u'yːt̚'),
        'zoe': (u'tʃ', u'œː'), 'zoek': (u'tʃ', u'œːk̚'),
        'coek': (u'tʃʰ', u'œːk̚'), 'zoeng': (u'tʃ', u'œːŋ'),
        'coeng': (u'tʃʰ', u'œːŋ'), 'zeoi': (u'tʃ', u'ɵy'),
        'ceoi': (u'tʃʰ', u'ɵy'), 'zeot': (u'tʃ', u'ɵt̚'),
        'ceot': (u'tʃʰ', u'ɵt̚'), 'zeon': (u'tʃ', u'ɵn'),
        'ceon': (u'tʃʰ', u'ɵn')},
    ('Pinyin', 'GR'): {u'm': None, u'n': None, u'ng': None, u'hm': None,
        u'hng': None, u'ê': None, 'yo': None},
    ('Pinyin', 'WadeGiles'): {u'wen': ('', u'uên'), 'weng': ('', u'uêng'),
        'yi': ({'exceptSemiVowel': '', 'all_1': ''}, u'i'),
        u'm': None, u'n': None, u'ng': None, u'hm': None, u'hng': None,
        'yai': None, 'yo': None},
    }
"""
Mapping for syllables with either no initial/final rules or with non standard
translation. Each entry consists of the syllable and a tuple of
initial and final if a mapping exists, else "None". For ambiguous pronunciations
a non-injective mapping can be achieved by giving a dictionary of possibilities,
the key giving the name of the feature.
"""

def getYaleSyllable(initial, final):
    nucleus, coda = final

    # syllable rule
    if initial == 'y' and nucleus.startswith('y'):
        # out of convenience Yale initial y and nucleus yu* are merged
        #   conventionally
        return nucleus + coda
    else:
        return initial + nucleus + coda

def makeYaleInitialNucleusCodaEntry(jyutpingSyllable, initial, final,
    initialFeature=None, finalFeature=None):
    yaleSyllable = getYaleSyllable(initial, final)
    nucleus, coda = final

    return "'" + yaleSyllable + "','" + initial + "','" + nucleus \
        + "','" + coda + "'"

def makeJyutpingYaleEntry(jyutpingSyllable, initial, final,
    initialFeature=None, finalFeature=None):
    yaleSyllable = getYaleSyllable(initial, final)

    return "'" + jyutpingSyllable + "','" + yaleSyllable + "'"

def getWadeGilesSyllable(initial, final):
    # syllable rule
    if not initial and final in ['i', 'in', 'ing']:
        return 'y' + final
    elif not initial and final.startswith('i') and final != 'i':
        return 'y' + final[1:]
    elif not initial and final == 'u':
        return 'w' + final
    elif not initial and final.startswith('u'):
        return 'w' + final[1:]
    elif not initial and final == u'ü':
        return 'y' + final
    elif not initial and final.startswith(u'ü'):
        return 'y' + final
    else:
        return initial + final

def checkFeature(syllablePart, feature):
    """
    Checks if the given initial or final fits to the given feature.

    E.g. if a final entry is given as {u'-k/k’/': 'ui', u'k/k’/': 'uei'},
    then the first feature is u'-k/k’/' which represents all finals except 'k',
    'k’' and '', so that e.g. checkFeature('d', u'-k/k’/') will return true and
    generate form 'dui'.
    """
    if feature:
        negative = False
        if feature.startswith('-'):
            feature = feature[1:]
            negative = True
        if feature.startswith('all_'):
            # all carry this
            return True
        mappings = feature.split('/')
        return (syllablePart in mappings and not negative) \
            or (syllablePart not in mappings and negative)
    return True

def makePinyinWadeGilesEntry(pinyinSyllable, initial, final,
    initialFeature=None, finalFeature=None):
    if initialFeature == 'exceptSemiVowel' and not initial:
        wadeGilesSyllable = final

        return "'" + pinyinSyllable + "','" + wadeGilesSyllable + "'"
    elif checkFeature(final, initialFeature) \
        and checkFeature(initial, finalFeature):
        # only generate entry if initial/final fits to features
        wadeGilesSyllable = getWadeGilesSyllable(initial, final)

        return "'" + pinyinSyllable + "','" + wadeGilesSyllable + "'"

def makeWadeGilesInitialFinalEntry(pinyinSyllable, initial, final,
    initialFeature=None, finalFeature=None):
    if initialFeature == 'exceptSemiVowel' and not initial:
        wadeGilesSyllable = final

        return "'" + wadeGilesSyllable + "','" + initial + "','" + final + "'"
    elif checkFeature(final, initialFeature) \
        and checkFeature(initial, finalFeature):
        # only generate entry if initial/final fits to features
        wadeGilesSyllable = getWadeGilesSyllable(initial, final)

        return "'" + wadeGilesSyllable + "','" + initial + "','" + final + "'"

def makeTargetInitialFinalEntry(sourceSyllable, initial, final,
    initialFeature=None, finalFeature=None):
    return "'" + initial + final + "','" + initial + "','" + final + "'"

def makeSourceTargetEntry(sourceSyllable, initial, final, initialFeature=None,
    finalFeature=None):
    targetSyllable = initial + final

    features = []
    if initialFeature:
        features.append(initialFeature)
    if finalFeature:
        features.append(finalFeature)

    if features:
        return "'" + sourceSyllable + "','" + targetSyllable + "','" \
            + ','.join(features) + "'"
    else:
        return "'" + sourceSyllable + "','" + targetSyllable + "',"

modi = {'YaleInitialFinal':('Jyutping', 'CantoneseYale',
        makeYaleInitialNucleusCodaEntry, {'toneMarkType': 'none'}),
    'JyutpingYaleMapping': ('Jyutping', 'CantoneseYale',
        makeJyutpingYaleEntry, {'toneMarkType': 'none'}),
    'MandarinIPAInitialFinal': ('Pinyin', 'MandarinIPA',
        makeTargetInitialFinalEntry, {'erhua': 'ignore',
            'toneMarkType': 'none'}),
    'PinyinIPAMapping': ('Pinyin', 'MandarinIPA', makeSourceTargetEntry,
        {'erhua': 'ignore', 'toneMarkType': 'none'}),
    'CantoneseIPAInitialFinal': ('Jyutping', 'CantoneseIPA',
        makeTargetInitialFinalEntry, {'toneMarkType': 'None'}),
    'JyutpingIPAMapping': ('Jyutping', 'CantoneseIPA', makeSourceTargetEntry,
        {'toneMarkType': 'none'}),
    'PinyinGRMapping': ('Pinyin', 'GR', makeSourceTargetEntry,
        {'erhua': 'ignore', 'toneMarkType': 'none'}),
    'PinyinWadeGilesMapping': ('Pinyin', 'WadeGiles', makePinyinWadeGilesEntry,
        {'erhua': 'ignore', 'toneMarkType': 'none'}),
    'WadeGilesInitialFinal': ('Pinyin', 'WadeGiles',
        makeWadeGilesInitialFinalEntry,
        {'erhua': 'ignore', 'toneMarkType': 'none'}),
    }

def main():
    language, output_encoding = locale.getdefaultlocale()

    if len(sys.argv) == 2:
        modus = sys.argv[1]
        if modus not in modi:
            print "invalid modus, choose one out of: " + ", ".join(modi.keys())
            sys.exit(1)
    else:
        print "give a modus, choose one out of: " + ", ".join(modi.keys())
        sys.exit(1)

    fromReading, toReading, entryFunc, readingOpt = modi[modus]

    initialRules = INITIAL_RULES[(fromReading, toReading)]
    finialRules = FINAL_RULES[(fromReading, toReading)]
    extraSyllables = EXTRA_SYLLABLES[(fromReading, toReading)]

    # entry set
    global entrySet
    entrySet = set()
    # build table and use scheme with almost perfect grouping according to
    #   pronunciation, then use headers to get the initial's and final's
    #   pronunciation.
    op = ReadingFactory().createReadingOperator(fromReading, **readingOpt)

    # get splitted syllables, finals in first row, initials in first column
    for syllable in op.getReadingEntities():
        initial, final = op.getOnsetRhyme(syllable)
        # only apply rules if syllable isn't given an extra mapping in
        #   EXTRA_SYLLABLES
        if not syllable in extraSyllables:
            # check if we have rules
            if initialRules[initial] != None and finialRules[final] != None:
                # check for ambiguous mappings
                if type(initialRules[initial]) == type({}):
                    initialFeatures = initialRules[initial].keys()
                else:
                    initialFeatures = [None]
                if type(finialRules[final]) == type({}):
                    finalFeatures = finialRules[final].keys()
                else:
                    finalFeatures = [None]

                # go through all mappings
                for initialFeature in initialFeatures:
                    for finalFeature in finalFeatures:
                        if initialFeature:
                            targetInitial \
                                = initialRules[initial][initialFeature]
                        else:
                            targetInitial = initialRules[initial]

                        if finalFeature:
                            targetFinal = finialRules[final][finalFeature]
                        else:
                            targetFinal = finialRules[final]

                        entry = entryFunc(syllable, targetInitial, targetFinal,
                            initialFeature, finalFeature)
                        if entry != None:
                            entrySet.add(entry)
            else:
                print >> sys.stderr, ("missing rule(s) for syllable '" \
                    + syllable + "' with initial/final '" + initial + "'/'" \
                    + final + "'").encode(output_encoding)

    # print extra syllables
    for syllable in extraSyllables:
        if extraSyllables[syllable]:
            initialRule, finalRule = extraSyllables[syllable]
            # check for ambiguous mappings
            if type(initialRule) == type({}):
                initialFeatures = initialRule.keys()
            else:
                initialFeatures = [None]
            if type(finalRule) == type({}):
                finalFeatures = finalRule.keys()
            else:
                finalFeatures = [None]

            # go through all mappings
            for initialFeature in initialFeatures:
                for finalFeature in finalFeatures:
                    if initialFeature:
                        targetInitial = initialRule[initialFeature]
                    else:
                        targetInitial = initialRule

                    if finalFeature:
                        targetFinal = finalRule[finalFeature]
                    else:
                        targetFinal = finalRule

                    entry = entryFunc(syllable, targetInitial, targetFinal,
                        initialFeature, finalFeature)
                    if entry != None:
                        entrySet.add(entry)

    notIncludedSyllables = [syllable for syllable in extraSyllables \
        if not extraSyllables[syllable]]
    if notIncludedSyllables:
        print >> sys.stderr, ("Syllables not included in table: '" \
            + "', '".join(sorted(notIncludedSyllables)) + "'")\
            .encode(output_encoding)

    entryList = list(entrySet)
    entryList.sort()
    print "\n".join(entryList).encode(output_encoding)

if __name__ == "__main__":
    main()
