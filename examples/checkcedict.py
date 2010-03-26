#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Checks a CEDICT compatible dictionary against Unihan on valid Pinyin
pronunciations and character variant forms (traditional vs. Chinese simplified).

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

@todo Impl: Check for double entries with inconsistencies arising from mixing
    simplified with traditional forms, i.e. entries with same simplified form
    but similar though non equal meaning. Extend to tone independent checks.
    E.g.:

        关系/關係, guān xì, /Beziehung (u.E.) (S); Bsp.: 同事關系 同事关系 --
        Beziehung zu Arbeitskollegen /Einfluss (u.E.) (S); Bsp.: 這件事情關系太大。
        这件事情关系太大。 -- Dieses Ereignis hat weitreichenden Einfluss./
        Zusammenhang (u.E.) (S); Bsp.: 這兩件事情之間有著因果關系。
        这两件事情之间有着因果关系。 -- Es besteht ein ursächlicher Zusammenhang
        zwischen beiden Ereignissen./
        关系/關係, guān xi, /Bedeutung (u.E.) (S)/Beziehung(en), Verhältnis
        (u.E.) (S)/betreffen (u.E.) (V)/

        档案/檔案, dǎng àn, /Dokument (u.E.) (S)/File (u.E.) (S, EDV)/
        档案/檔案, dàng àn, /Akte (bei Gericht) (u.E.) (S)/Archiv, Dossier (u.E.)
        (S)/


"""
import locale
import re
import sys
import getopt

from sqlalchemy import select

from cjklib.dictionary import getDictionary
from cjklib.reading import ReadingFactory
from cjklib import characterlookup
from cjklib import exception

DICTIONARY_READING = {'HanDeDict': ('Pinyin', {'toneMarkType': 'numbers'}),
    'CEDICT': ('Pinyin', {'toneMarkType': 'numbers', 'yVowel': 'u:'})}
"""
A lookup table for supported dictionaries containing the database table name and
reading type.
"""

NON_PINYIN_MAPPING = {u'，': u' , ', u'・': u' · '}
"""Mapping of non-Pinyin entities regarded as correct."""

# get local language and output encoding
language, default_encoding = locale.getdefaultlocale()

_cjk = None
def getCJK():
    """
    Creates an instance of the L{CharacterLookup} object if needed and returns
    it.

    @rtype: object
    @return: an instance of the L{CharacterLookup} object
    """
    global _cjk
    if not _cjk:
        _cjk = characterlookup.CharacterLookup('T')
    return _cjk

def iterDictionary(dictionary):
    d = getDictionary(dictionary, columnFormatStrategies={'Reading': None})
    return d.getAll()

def getPlainSyllableSet(entityList, reading):
    plainEntityList = set()
    for entity in entityList:
        plainSyllable, _ = getReadingOperator(reading).splitEntityTone(entity)
        plainEntityList.add(plainSyllable)
    return plainEntityList

def hasReading(entity, readingList, readingName, ignoreFifthTone=False):
    # handle tone changes to fifth tone
    if ignoreFifthTone:
        plainSyllable, tone = getReadingOperator(readingName).splitEntityTone(
            entity)
        if tone == 5:
            if plainSyllable.lower() in getPlainSyllableSet(readingList,
                readingName):
                return True
            else:
                return False

    return entity.lower() in readingList

def getSimplifiedMapping(char):
    vVariants = []
    vVariants.extend(getCJK().getCharacterVariants(char, 'S'))
    if len(vVariants) == 0:
        vVariants.append(char)
    # add other variants
    otherVariants = []
    otherVariants.extend(getCJK().getCharacterVariants(char, 'M'))
    otherVariants.extend(getCJK().getCharacterVariants(char, 'P'))
    otherVariants.extend(getCJK().getCharacterVariants(char, 'Z'))
    simplifiedOthers = []
    for variant in otherVariants:
        simplifiedOthers.extend(getCJK().getCharacterVariants(variant, 'S'))
    vVariants.extend(otherVariants)
    vVariants.extend(simplifiedOthers)

    return set(vVariants)

_readingOperator = None
def getReadingOperator(readingName, readingOptions={}):
    global _readingOperator
    if not _readingOperator:
        readingFactory = ReadingFactory()
        _readingOperator = readingFactory.createReadingOperator(readingName,
            **readingOptions)
    return _readingOperator

def checkCharacterReading(dictionary, readingName, readingOptions={},
    ignoreFifthTone=False):
    for entry in iterDictionary(dictionary):
        if entry.HeadwordTraditional != entry.HeadwordSimplified:
            headword = "%s/%s" % (entry.HeadwordTraditional,
                entry.HeadwordSimplified)
        else:
            headword = entry.HeadwordTraditional

        try:
            operator = getReadingOperator(readingName, readingOptions)
            entities = operator.decompose(entry.Reading)
        except exception.DecompositionError:
            print ("WARNING: can't parse line '%s', '%s', '%s'"
                % (entry.HeadwordTraditional, entry.HeadwordSimplified,
                    entry.Reading)).encode(default_encoding)
            continue

        entitiesFiltered = []
        for entity in entities:
            if re.match(r"\s+$", entity):
                continue
            entitiesFiltered.append(entity)

        if (len(entitiesFiltered) != len(entry.HeadwordTraditional)) \
            or (len(entitiesFiltered) != len(entry.HeadwordSimplified)):
            print ("WARNING: can't parse line '%s', '%s', '%s'"
                % (entry.HeadwordTraditional, entry.HeadwordSimplified,
                    entry.Reading)).encode(default_encoding)
            continue

        for i, entity in enumerate(entitiesFiltered):
            if getReadingOperator(readingName).isReadingEntity(entity):
                if entry.HeadwordTraditional[i] != entry.HeadwordSimplified[i]:
                    charList = [entry.HeadwordTraditional[i],
                        entry.HeadwordSimplified[i]]
                else:
                    charList = [entry.HeadwordTraditional[i]]

                for char in charList:
                    validReading = True
                    try:
                        readingList = getCJK().getReadingForCharacter(char,
                            readingName, **readingOptions)

                        if readingList and not hasReading(entity, readingList,
                            readingName, ignoreFifthTone):
                            print (char + " " + entity + ", known readings: " \
                                + ', '.join(readingList) + "; for headword '" \
                                + headword + "'").encode(default_encoding)
                    except exception.NoInformationError:
                        pass
            else:
                # Check mapping of non-Pinyin entities. They either map
                #   to the same character again (e.g. ellipsis: ...) or have
                #   a different form described by table NON_PINYIN_MAPPING
                if entry.HeadwordTraditional[i] != entity \
                    and (entry.HeadwordTraditional[i] not in NON_PINYIN_MAPPING \
                    or NON_PINYIN_MAPPING[entry.HeadwordTraditional[i]] != entity):
                    print ("WARNING: invalid mapping of entity '" \
                        + entry.HeadwordTraditional[i] + "' to '" + entity \
                        + "'; for headword '" + headword + "'")\
                        .encode(default_encoding)
                elif entry.HeadwordSimplified[i] != entity \
                    and (entry.HeadwordSimplified[i] not in NON_PINYIN_MAPPING \
                    or NON_PINYIN_MAPPING[entry.HeadwordSimplified[i]] != entity):
                    print ("WARNING: invalid mapping of entity '" \
                        + entry.HeadwordSimplified[i] + "' to '" + entity \
                        + "'; for headword '" + headword + "'")\
                        .encode(default_encoding)

def checkCharacterVariants(dictionary):
    for entry in iterDictionary(dictionary):
        if len(entry.HeadwordTraditional) != len(entry.HeadwordSimplified):
            print ("WARNING: different string length '%s', '%s', '%s'"
                % (entry.HeadwordTraditional, entry.HeadwordSimplified,
                    entry.Reading)).encode(default_encoding)
            continue

        if entry.HeadwordTraditional == entry.HeadwordSimplified:
            continue

        for idx, char in enumerate(entry.HeadwordTraditional):
            mapping = getSimplifiedMapping(char)
            if entry.HeadwordSimplified[idx] not in mapping:
                headword = "%s/%s" % (entry.HeadwordTraditional,
                    entry.HeadwordSimplified)
                print (char + ", known mappings: " + ', '.join(mapping) \
                    + "; for headword '" + headword + "'").encode(
                        default_encoding)

def usage():
    """
    Prints the usage for this script.
    """
    print """Usage: checkcedict.py COMMAND
checkcedict.py provides a simple script to check the consistency of CEDICT
compatible dictionaries (CEDICT, HanDeDict).

General commands:
  -r, --reading              check on character to reading mapping
  -c, --character-variants   check on character variant mappings (traditional
                               to Chinese simplified mostly)
  -w, --set-dictionary=DICTIONARY
                             set dictionary
  --ignore-fifth             ignore inconsistent mapping if target reading has
                               fifth tone"""

def main():
    # parse command line parameters
    try:
        opts, args = getopt.getopt(sys.argv[1:],
            "w:rc", ["help", "pinyin", "character-variants", "set-dictionary=",
            "ignore-fifth"])
    except getopt.GetoptError:
        # print help information and exit
        usage()
        sys.exit(2)

    # get default dictionary
    dictionaryDic = {}
    for dictionary in DICTIONARY_READING.keys():
        dictionaryDic[dictionary.lower()] = dictionary

    dictionary = DICTIONARY_READING.keys()[0]
    ignoreFifthTone = False
    # if True, no error will be reported when tone shifts to neutral tone
    checkReading = False
    checkVariants = False

    # start to check parameters
    if len(opts) == 0:
        print "use parameter -h for a short summary on supported functions"
    for o, a in opts:
        a = a.decode(default_encoding)
        # help screen
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        # setting of dictionary
        elif o in ("-w", "--set-dictionary"):
            if a.lower() in dictionaryDic.keys():
                dictionary = a
            else:
                print "not a valid dictionary"
        # check reading
        elif o in ("--ignore-fifth"):
            ignoreFifthTone = True
        # check reading mapping
        elif o in ("-r", "--reading"):
            checkReading = True
        # check variant mapping
        elif o in ("-c", "--character-variants"):
            checkVariants = True

    if checkReading or checkVariants:
        print "Checking " + dictionary

    if checkReading:
        reading, readingOptions \
            = DICTIONARY_READING[dictionaryDic[dictionary.lower()]]
        checkCharacterReading(dictionary, reading,
            readingOptions, ignoreFifthTone)
    if checkVariants:
        checkCharacterVariants(dictionary)

if __name__ == "__main__":
    main()

