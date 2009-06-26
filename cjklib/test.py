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
Provides the library's unit tests.

@todo Impl: Much much more test cases.
"""
import unittest
import types
import re
import traceback

from cjklib.reading import *
from cjklib import characterlookup

from cjklib import exception

class ImmutableDict(dict):
    """A hashable dict."""
    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)
    def __setitem__(self, key, value):
        raise NotImplementedError, "dict is immutable"
    def __delitem__(self, key):
        raise NotImplementedError, "dict is immutable"
    def clear(self):
        raise NotImplementedError, "dict is immutable"
    def setdefault(self, k, default=None):
        raise NotImplementedError, "dict is immutable"
    def popitem(self):
        raise NotImplementedError, "dict is immutable"
    def update(self, other):
        raise NotImplementedError, "dict is immutable"
    def __hash__(self):
        return hash(tuple(self.iteritems()))


class ReadingOperatorTestCase(unittest.TestCase):
    """Base class for testing of L{ReadingOperator}s."""
    READING_DIALECTS = [('Pinyin', {'toneMarkType': 'Numbers'}),
        ('Pinyin', {'Erhua': 'oneSyllable'}),
        ('Pinyin', {'strictDiacriticPlacement': 'True'}),
        ('CantoneseYale', {'toneMarkType': 'Numbers'}),
        ('CantoneseYale', {'strictDiacriticPlacement': 'True'}),
        ('Jyutping', {'missingToneMark': 'ignore'}),
        ('MandarinBraille', {'missingToneMark': 'fifth'}),
        ]
    """Further reading dialect forms included in testing."""

    def setUp(self):
        self.readingOperator = {}
        for clss in self.getReadingOperatorClasses().values():
            self.readingOperator[(clss.READING_NAME, ImmutableDict({}))] \
                = clss()

        # get dialect forms
        f = ReadingFactory()
        for readingN, readingOptions in self.READING_DIALECTS:
            clss = f.getReadingOperatorClass(readingN)
            self.readingOperator[(clss.READING_NAME,
                ImmutableDict(readingOptions))] = clss(**readingOptions)

    @staticmethod
    def getReadingOperatorClasses():
        """
        Gets all classes from the reading module that implement
        L{ReadingOperator}.

        @rtype: dictionary of string class pairs
        @return: dictionary of all classes inheriting form
            L{ReadingOperator}
        """
        readingOperatorClasses = {}

        # get all non-abstract classes that inherit from ReadingOperator
        readingOperatorClasses = dict([(clss.__name__, clss) \
            for clss in operator.__dict__.values() \
            if type(clss) == types.TypeType \
            and issubclass(clss, operator.ReadingOperator) \
            and clss.READING_NAME])

        return readingOperatorClasses


class ReadingOperatorConsistencyTestCase(ReadingOperatorTestCase):
    """
    Runs consistency checks on ReadingOperators. These tests assure that
    different methods handle the same values in a consistent way. It does not
    assure though that these values are correct.
    """
    def testReadingNameUnique(self):
        """Test if only one ReadingOperator exists for each reading."""
        seenNames = set()

        for clss in self.getReadingOperatorClasses().values():
            self.assert_(clss.READING_NAME not in seenNames, "Seen '" \
                + clss.READING_NAME + "' already")
            seenNames.add(clss.READING_NAME)

    def testValidReadingEntitiesAccepted(self):
        """Test if all reading entities returned by C{getReadingEntities()} are accepted by C{isReadingEntity()}."""
        for key in self.readingOperator:
            reading, _ = key
            if hasattr(self.readingOperator[key], "getReadingEntities"):
                entities = self.readingOperator[key]\
                    .getReadingEntities()
                for entity in entities:
                    self.assert_(
                        self.readingOperator[key].isReadingEntity(entity),
                        "Entity " + repr(entity) + " not accepted for " \
                            "reading '"+ reading + "'")

    def testValidPlainReadingEntitiesAccepted(self):
        """Test if all plain reading entities returned by C{getPlainReadingEntities()} are accepted by C{isPlainReadingEntity()}."""
        for key in self.readingOperator:
            reading, _ = key
            if hasattr(self.readingOperator[key], "getReadingEntities"):
                plainEntities = self.readingOperator[key]\
                    .getPlainReadingEntities()
                for plainEntity in plainEntities:
                    self.assert_(self.readingOperator[key]\
                        .isPlainReadingEntity(plainEntity),
                        "Plain entity " + repr(plainEntity) \
                            + " not accepted for reading '" + reading + "'")

    def testDecomposeIsIdentityForSingleEntity(self):
        """Test if all reading entities returned by C{getReadingEntities()} are decomposed into the single entity again."""
        for key in self.readingOperator:
            reading, _ = key
            if hasattr(self.readingOperator[key], "getReadingEntities"):
                entities = self.readingOperator[key].getReadingEntities()
                for entity in entities:
                    try:
                        entities = self.readingOperator[key].decompose(entity)

                        self.assertEquals(entities, [entity],
                            "decompose on single entity " + repr(entity) \
                                + " doesn't return the entity for reading '" \
                                + reading + "': " + repr(entities))
                    except exception.AmbiguousDecompositonError:
                        self.assert_(True, "ambiguous decomposition for " \
                            + repr(entity) + " for reading '" + reading + "'")

    ##TODO Jyutping (missing tone marks) and CantoneseYale don't create strict
      ##compositions
    #def testDecomposeKeepsSyllablePairs(self):
        #"""Test if all pairs of reading entities returned by C{getReadingEntities()} are decomposed into the same pairs again."""
        #for key in self.readingOperator:
            #reading, _ = key
            #if not reading in ['Pinyin', 'WadeGiles']:
                #continue

            #if hasattr(self.readingOperator[key], "getReadingEntities"):
                #entities = self.readingOperator[key].getReadingEntities()
                #for entityA in entities:
                    #for entityB in entities:
                        #pair = [entityA, entityB]
                        #string = self.readingOperator[key].compose(pair)
                        #try:
                            #decomposition = self.readingOperator[key]\
                                #.decompose(string)

                            ## we allow spaces to be inserted
                            #while ' ' in decomposition:
                                #decomposition.remove(' ')

                            ## Pinyin compose adds apostrophes
                            #if reading == 'Pinyin':
                                #decomposition = self.readingOperator[key]\
                                    #.removeApostrophes(decomposition)
                            ## Pinyin compose adds hyphens
                            #if reading == 'WadeGiles':
                                #decomposition = self.readingOperator[key]\
                                    #.removeHyphens(decomposition)

                            #self.assertEquals(decomposition, pair,
                                #"decompose doesn't keep entity pair " \
                                    #+ repr(pair) + " for reading '" + reading \
                                    #+ "': " + repr(decomposition))
                        #except exception.DecompositionError:
                            #pass

    #def testPinyinCompositionIsStrict(self):
        #"""Tests if the PinyinOperator's C{compose()} method creates strict strings."""
        #for key in self.readingOperator:
            #reading, _ = key
            #if not reading in ['Pinyin']:
                #continue

            #if hasattr(self.readingOperator[key], "getReadingEntities"):
                #entities = self.readingOperator[key].getReadingEntities()
                #for entityA in entities:
                    #for entityB in entities:
                        #pair = [entityA, entityB]
                        #string = self.readingOperator[key].compose(pair)
                        #decomposition = self.readingOperator[key].decompose(
                            #string)
                        #self.assert_(self.readingOperator[key]\
                            #.isStrictDecomposition(decomposition), "Pair " \
                                #+ repr(pair) + " not strict for reading '" \
                                #+ reading + "': " + repr(string))

    def testGetTonalEntityOfSplitEntityToneIsIdentity(self):
        """Test if the composition of C{getTonalEntity()} and C{splitEntityTone()} returns the original value for all entities returned by C{getReadingEntities()}."""
        for key in self.readingOperator:
            reading, _ = key
            if hasattr(self.readingOperator[key], "getReadingEntities") \
                and hasattr(self.readingOperator[key],
                    "getPlainReadingEntities"):
                entities = self.readingOperator[key].getReadingEntities()
                for entity in entities:
                    try:
                        plainEntity, tone \
                            = self.readingOperator[key].splitEntityTone(entity)

                        self.assertEquals(
                            self.readingOperator[key].getTonalEntity(
                                plainEntity, tone), entity,
                            "Entity " + repr(entity) + " not preserved in " \
                                + "composition of getTonalEntity() and " \
                                + "splitEntityTone of reading '" + reading \
                                + "'")
                    except exception.UnsupportedError:
                        pass

    def testSplitEntityToneReturnsValidInformation(self):
        """Test if C{splitEntityTone()} returns a valid plain entity and a valid tone for all entities returned by C{getReadingEntities()}."""
        for key in self.readingOperator:
            reading, _ = key
            if hasattr(self.readingOperator[key], "getReadingEntities"):
                entities = self.readingOperator[key].getReadingEntities()
                for entity in entities:
                    try:
                        plainEntity, tone \
                            = self.readingOperator[key].splitEntityTone(entity)

                        self.assert_(self.readingOperator[key]\
                            .isPlainReadingEntity(plainEntity),
                            "Plain entity of " + repr(entity) \
                                + " not accepted " + "for reading '" \
                                + reading + "': " + repr(plainEntity))

                        self.assert_(tone \
                            in self.readingOperator[key].getTones(),
                            "Tone of entity " + repr(entity) + " not valid " \
                                + "for reading '" + reading + "': " \
                                + repr(tone))
                    except exception.UnsupportedError:
                        pass


class ReadingOperatorValueTestCase(ReadingOperatorTestCase):
    """
    Runs reference checks on ReadingOperators. These tests assure that the given
    values are returned correctly.
    """
    READING_DIALECTS = [('Pinyin', {'toneMarkType': 'Numbers'}),
        ('Pinyin', {'Erhua': 'oneSyllable'}),
        ('Pinyin', {'strictDiacriticPlacement': True}),
        ('CantoneseYale', {'toneMarkType': 'Numbers'}),
        ('CantoneseYale', {'strictDiacriticPlacement': True}),
        ('Jyutping', {'missingToneMark': 'ignore'}),
        ]

    DECOMPOSITION_VALUES = {
        ('Pinyin', ImmutableDict({})): [
            (u"tiān'ānmén", [u"tiān", "'", u"ān", u"mén"]),
            ("xian", ["xian"]),
            (u"xīān", [u"xī", u"ān"]),
            (u"lao3tou2r5", [u"lao3", u"tou2", u"r5"]),
            (u"peínǐ", [u'peí', u'nǐ']), # wrong placement of tone
            (u"hónglùo", [u'hóng', u'lùo']), # wrong placement of tone
            ],
        ('Pinyin', ImmutableDict({'toneMarkType': 'Numbers'})): [
            (u"tian1'an1men2", [u"tian1", "'", u"an1", u"men2"]),
            ("xian", ["xian"]),
            (u"xi1an1", [u"xi1", u"an1"]),
            ],
        ('Pinyin', ImmutableDict({'Erhua': 'oneSyllable'})): [
            (u"lao3tour2", [u"lao3", u"tour2"]),
            (u"er2hua4yin1", [u"er2", u"hua4", u"yin1"]),
            ],
        ('Pinyin', ImmutableDict({'strictDiacriticPlacement': True})): [
            (u"tiān'ānmén", [u"tiān", "'", u"ān", u"mén"]),
            ("xian", ["xian"]),
            (u"xīān", [u"xī", u"ān"]),
            (u"lao3tou2r5", [u"lao3", u"tou2", u"r5"]),
            (u"peínǐ", [u'peínǐ']), # wrong placement of tone
            (u"hónglùo", [u'hóng', u'lù', u'o']), # wrong placement of tone
            ],
        ('Hangul', ImmutableDict({})): [
            (u"한글은 한국어의 고유", [u"한", u"글", u"은", u" ",
                u"한", u"국", u"어", u"의", u" ", u"고", u"유"]),
            ],
        ('CantoneseYale', ImmutableDict({})): [
            (u'gwóngjàuwá', [u'gwóng', u'jàu', u'wá']),
            (u'yuhtyúh', [u'yuht', u'yúh']),
            (u'néihhóu', [u'néih', u'hóu']),
            (u'gwóngjaù', [u'gwóng', u'jaù']), # wrong placement of tone
            ],
        ('CantoneseYale', ImmutableDict({'toneMarkType': 'Numbers'})): [
            (u'gwong2jau1wa2', [u'gwong2', u'jau1', u'wa2']),
            (u'yut6yu5', [u'yut6', u'yu5']),
            (u'nei5hou2', [u'nei5', u'hou2']),
            ],
        ('CantoneseYale', ImmutableDict({'strictDiacriticPlacement': True})): [
            (u'gwóngjàuwá', [u'gwóng', u'jàu', u'wá']),
            (u'yuhtyúh', [u'yuht', u'yúh']),
            (u'néihhóu', [u'néih', u'hóu']),
            (u'gwóngjaù', [u'gwóngjaù']), # wrong placement of tone
            ],
        ('Jyutping', ImmutableDict({})): [
            (u'gwong2zau1waa2', [u'gwong2', u'zau1', u'waa2']),
            ],
        }

    COMPOSITION_VALUES = {
        ('Pinyin', ImmutableDict({})): [
            (u"tiān'ānmén", [u"tiān", u"ān", u"mén"]),
            ("xian", ["xian"]),
            (u"xī'ān", [u"xī", u"ān"]),
            ],
        }

    IS_READING_ENTITY_VALUES = {
        ('Pinyin', ImmutableDict({})): [
            (u"tiān", True),
            (u"ān", True),
            (u"mén", True),
            (u"lào", True),
            (u"xǐ", True),
            (u"xian", True),
            (u"ti\u0304an", True),
            (u"tia\u0304n", True),
            (u"laǒ", True),
            (u"tīan", True),
            (u"tīa", False),
            (u"tiā", False),
            ],
        ('Pinyin', ImmutableDict({'strictDiacriticPlacement': True})): [
            (u"tiān", True),
            (u"ān", True),
            (u"mén", True),
            (u"lào", True),
            (u"xǐ", True),
            (u"xian", True),
            (u"tia\u0304n", True),
            (u"ti\u0304an", False),
            (u"laǒ", False),
            (u"tīan", False),
            (u"tīa", False),
            (u"tiā", False),
            ],
        ('CantoneseYale', ImmutableDict({})): [
            (u'wā', True),
            (u'gwóng', True),
            (u'jàu', True),
            (u'wá', True),
            (u'néih', True),
            (u'yuht', True),
            (u'gwong', True),
            (u'wa\u0304', True),
            (u'jaù', True),
            (u'gwongh', True),
            (u'wáa', False),
            ],
        ('CantoneseYale', ImmutableDict({'strictDiacriticPlacement': True})): [
            (u'wā', True),
            (u'gwóng', True),
            (u'jàu', True),
            (u'wá', True),
            (u'néih', True),
            (u'yuht', True),
            (u'gwong', True),
            (u'wa\u0304', True),
            (u'jaù', False),
            (u'gwongh', False),
            (u'wáa', False),
            ],
        }

    def testDecompositionReferences(self):
        """Test if the given decomposition references are reached."""
        for key in self.DECOMPOSITION_VALUES:
            reading, _ = key
            for string, targetDecomp in self.DECOMPOSITION_VALUES[key]:
                decomposition = self.readingOperator[key].decompose(string)
                self.assertEquals(decomposition, targetDecomp,
                    "Decomposition " + repr(targetDecomp) + " of " \
                        + repr(string) + " not reached for reading '" \
                        + reading + "': " + repr(decomposition))

    def testCompositionReferences(self):
        """Test if the given composition references are reached."""
        for key in self.COMPOSITION_VALUES:
            reading, _ = key
            for targetStr, composition in self.COMPOSITION_VALUES[key]:
                string = self.readingOperator[key].compose(composition)
                self.assertEquals(string, targetStr,
                    "String " + repr(targetStr) + " of Composition " \
                        + repr(composition) + " not reached for reading '" \
                        + reading + "': " + repr(string))

    def testEntityReferences(self):
        """Test if the given entity references are accepted/rejected."""
        for key in self.IS_READING_ENTITY_VALUES:
            reading, dialectParams = key
            for entity, target in self.IS_READING_ENTITY_VALUES[key]:
                result = self.readingOperator[key].isReadingEntity(entity)
                self.assertEquals(result, target,
                    "Entity test for " + repr(entity) + " mismatches: " \
                        + repr(result) + " but should be " + repr(target) \
                        + " (" + reading + ", " + repr(dialectParams) + ")")


class GRTestCase(unittest.TestCase):
    """Tests GR conversion methods."""

    # The following mappings are taken from the Pinyin-to-GR Conversion Tables
    # written/compiled by Richard Warmington,
    # http://home.iprimus.com.au/richwarm/gr/pygrconv.txt
    # and have been extended by rhoticised finals
    SPECIAL_MAPPING = """
zhi             jy      jyr     jyy     jyh
chi             chy     chyr    chyy    chyh
shi             shy     shyr    shyy    shyh
ri              ry      ryr     ryy     ryh
zi              tzy     tzyr    tzyy    tzyh
ci              tsy     tsyr    tsyy    tsyh
si              sy      syr     syy     syh

ju              jiu     jyu     jeu     jiuh
qu              chiu    chyu    cheu    chiuh
xu              shiu    shyu    sheu    shiuh

yi              i       yi      yii     yih
ya              ia      ya      yea     yah
yo              io      -       -       -
ye              ie      ye      yee     yeh
yai             iai     yai     -       -
yao             iau     yau     yeau    yaw
you             iou     you     yeou    yow
yan             ian     yan     yean    yann
yin             in      yn      yiin    yinn
yang            iang    yang    yeang   yanq
ying            ing     yng     yiing   yinq
yong            iong    yong    yeong   yonq

wu              u       wu      wuu     wuh
wa              ua      wa      woa     wah
wo              uo      wo      woo     woh
wai             uai     wai     woai    way
wei             uei     wei     woei    wey
wan             uan     wan     woan    wann
wen             uen     wen     woen    wenn
wang            uang    wang    woang   wanq
weng            ueng    -       woeng   wenq

yu              iu      yu      yeu     yuh
yue             iue     yue     yeue    yueh
yuan            iuan    yuan    yeuan   yuann
yun             iun     yun     yeun    yunn

er              el      erl     eel     ell

yir             iel     yel     yeel    yell
yar             ial     yal     yeal    yall
yer             ie'l    ye'l    yeel    yell
yair            -       yal     -       -
yaor            iaul    yaul    yeaul   yawl
your            ioul    youl    yeoul   yowl
yanr            ial     yal     yeal    yall
yinr            iel     yel     yeel    yell
yangr           iangl   yangl   yeangl  yanql
yingr           iengl   yengl   yeengl  yenql
yongr           iongl   yongl   yeongl  yonql

wur             ul      wul     wuul    wull
war             ual     wal     woal    wall
wor             uol     wol     wool    woll
wair            ual     wal     woal    wall
weir            uel     wel     woel    well
wanr            ual     wal     woal    wall
wenr            uel     wel     woel    well
wangr           uangl   wangl   woangl  wanql
wengr           uengl   -       woengl  wenql

yur             iuel    yuel    yeuel   yuell
yuer            iue'l   yue'l   -       yuell
yuanr           iual    yual    yeual   yuall
yunr            iuel    yuel    yeuel   yuell
"""

    # final mapping without line 'r'
    FINAL_MAPPING = """
a               a       ar      aa      ah              ha      a
o               o       or      oo      oh              ho      o
e               e       er      ee      eh              he      e
ai              ai      air     ae      ay              hai     ai
ei              ei      eir     eei     ey              hei     ei
ao              au      aur     ao      aw              hau     au
ou              ou      our     oou     ow              hou     ou
an              an      arn     aan     ann             han     an
en              en      ern     een     enn             hen     en
ang             ang     arng    aang    anq             hang    ang
eng             eng     erng    eeng    enq             heng    eng
ong             ong     orng    oong    onq             hong    ong

i               i       yi      ii      ih              hi      i
ia              ia      ya      ea      iah             hia     ia
io              io      -       -       -               hio     -
ie              ie      ye      iee     ieh             hie     ie
iai             iai     yai     -       -               hiai    iai
iao             iau     yau     eau     iaw             hiau    iau
iu              iou     you     eou     iow             hiou    iou
ian             ian     yan     ean     iann            hian    ian
in              in      yn      iin     inn             hin     in
iang            iang    yang    eang    ianq            hiang   iang
ing             ing     yng     iing    inq             hing    ing
iong            iong    yong    eong    ionq            hiong   iong

u               u       wu      uu      uh              hu      u
ua              ua      wa      oa      uah             hua     ua
uo              uo      wo      uoo     uoh             huo     uo
uai             uai     wai     oai     uay             huai    uai
ui              uei     wei     oei     uey             huei    uei
uan             uan     wan     oan     uann            huan    uan
un              uen     wen     oen     uenn            huen    uen
uang            uang    wang    oang    uanq            huang   uang

u:              iu      yu      eu      iuh             hiu     iu
u:e             iue     yue     eue     iueh            hiue    iue
u:an            iuan    yuan    euan    iuann           hiuan   iuan
u:n             iun     yun     eun     iunn            hiun    iun

ar              al      arl     aal     all             hal     al
or              ol      orl     ool     oll             hol     ol
er              e'l     er'l    ee'l    ehl             he'l    e'l
air             al      arl     aal     all             hal     al
eir             el      erl     eel     ell             hel     el
aor             aul     aurl    aol     awl             haul    aul
our             oul     ourl    ooul    owl             houl    oul
anr             al      arl     aal     all             hal     al
enr             el      erl     eel     ell             hel     el
angr            angl    arngl   aangl   anql            hangl   angl
engr            engl    erngl   eengl   enql            hengl   engl
ongr            ongl    orngl   oongl   onql            hongl   ongl

ir              iel     yel     ieel    iell            hiel    iel
iar             ial     yal     eal     iall            hial    ial
ier             ie'l    ye'l    ieel    iell            hie'l   ie'l
iair            -       yal     -        -              -       -
iaor            iaul    yaul    eaul    iawl            hiaul   iaul
iur             ioul    youl    eoul    iowl            hioul   ioul
ianr            ial     yal     eal     iall            hial    ial
inr             iel     yel     ieel    iell            hiel    iel
iangr           iangl   yangl   eangl   ianql           hiangl  iangl
ingr            iengl   yengl   ieengl  ienql           hiengl  iengl
iongr           iongl   yongl   eongl   ionql           hiongl   iongl

ur              ul      wul     uul     ull             hul     ul
uar             ual     wal     oal     uall            hual    ual
uor             uol     wol     uool    uoll            huol    uol
uair            ual     wal     oal     uall            hual    ual
uir             uel     wel     oel     uell            huel    uel
uanr            ual     wal     oal     uall            hual    ual
unr             uel     wel     oel     uell            huel    uel
uangr           uangl   wangl   oangl   uanql           huangl  uangl
uengr           uengl   -       -       -               huengl  uengl

u:r             iuel    yuel    euel    iuell           hiuel   iuel
u:er            iue'l   yue'l   euel    iuell           hiue'l  iue'l
u:anr           iual    yual    eual    iuall           hiual   iual
u:nr            iuel    yuel    euel    iuell           hiuel   iuel
"""

    PINYIN_FINAL_MAPPING = {'iu': 'iou', 'ui': 'uei', 'un': 'uen', 'u:': u'ü',
        'u:e': u'üe', 'u:an': u'üan', 'u:n': u'ün', 'iur': 'iour',
        'uir': 'ueir', 'unr': 'uenr', 'u:r': u'ür', 'u:er': u'üer',
        'u:anr': u'üanr', 'u:nr': u'ünr'}

    INITIAL_REGEX = re.compile('^(tz|ts|ch|sh|[bpmfdtnlsjrgkh])?')

    def setUp(self):
        self.readingFactory = ReadingFactory()
        self.conv = self.readingFactory.createReadingConverter('Pinyin', 'GR',
            sourceOptions={'Erhua': "oneSyllable"},
            targetOptions={'GRRhotacisedFinalApostrophe': "'"})
        self.py = operator.PinyinOperator(Erhua="oneSyllable")

        # read in plain text mappings

        self.grJunctionSpecialMapping = {}
        for line in self.SPECIAL_MAPPING.split("\n"):
            if line.strip() == "":
                continue
            matchObj = re.match(r"((?:\w|:)+)\s+((?:\w|')+|-)\s+" \
                + "((?:\w|')+|-)\s+((?:\w|')+|-)\s+((?:\w|')+|-)", line)
            if not matchObj:
                print line
            pinyinSyllable, gr1, gr2, gr3, gr4 = matchObj.groups()

            self.grJunctionSpecialMapping[pinyinSyllable] = {1: gr1, 2: gr2,
                3: gr3, 4: gr4}

        self.grJunctionFinalMapping = {}
        self.grJunctionFinalMNLRMapping = {}
        for line in self.FINAL_MAPPING.split("\n"):
            matchObj = re.match(r"((?:\w|\:)+)\s+((?:\w|')+|-)\s+" \
                + "((?:\w|')+|-)\s+((?:\w|')+|-)\s+((?:\w|')+|-)" \
                + "\s+((?:\w|')+|-)\s+((?:\w|')+|-)", line)
            if not matchObj:
                continue

            pinyinFinal, gr1, gr2, gr3, gr4, gr1_m, gr2_m = matchObj.groups()

            if pinyinFinal in self.PINYIN_FINAL_MAPPING:
                pinyinFinal = self.PINYIN_FINAL_MAPPING[pinyinFinal]

            self.grJunctionFinalMapping[pinyinFinal] = {1: gr1, 2: gr2, 3: gr3,
                4: gr4}
            self.grJunctionFinalMNLRMapping[pinyinFinal] = {1: gr1_m, 2: gr2_m}

    def testGRJunctionGeneralFinalTable(self):
        """Test if the conversion matches the general final table given by GR Junction."""
        # create general final mapping
        for pinyinPlainSyllable in self.py.getPlainReadingEntities():
            pinyinInitial, pinyinFinal \
                = self.py.getOnsetRhyme(pinyinPlainSyllable)
            if pinyinInitial not in ['m', 'n', 'l', 'r', 'z', 'c', 's', 'zh',
                'ch', 'sh', ''] and pinyinFinal not in ['m', 'ng', 'mr', 'ngr']:
                for tone in [1, 2, 3, 4]:
                    if self.grJunctionFinalMapping[pinyinFinal][tone] == '-':
                        continue

                    pinyinSyllable = self.py.getTonalEntity(pinyinPlainSyllable,
                        tone)
                    syllable = self.conv.convertEntities([pinyinSyllable])[0]

                    tonalFinal = self.INITIAL_REGEX.sub('', syllable)

                    self.assertEquals(tonalFinal,
                        self.grJunctionFinalMapping[pinyinFinal][tone],
                        "Wrong conversion " + repr(syllable) + " to GR" \
                            + " for Pinyin syllable " + repr(pinyinSyllable) \
                            + " with the target final being " \
                            + repr(
                                self.grJunctionFinalMapping[pinyinFinal][tone]))

    def testGRJunctionMNLRFinalTable(self):
        """Test if the conversion matches the m,n,l,r final table given by GR Junction."""
        # m, n, l, r mapping for 1st and 2nd tone
        for pinyinPlainSyllable in self.py.getPlainReadingEntities():
            pinyinInitial, pinyinFinal \
                = self.py.getOnsetRhyme(pinyinPlainSyllable)
            if pinyinInitial in ['m', 'n', 'l', 'r'] \
                and pinyinFinal[0] != u'ʅ':
                for tone in [1, 2]:
                    if self.grJunctionFinalMNLRMapping[pinyinFinal][tone] \
                        == '-':
                        continue

                    pinyinSyllable = self.py.getTonalEntity(pinyinPlainSyllable,
                        tone)
                    syllable = self.conv.convertEntities([pinyinSyllable])[0]

                    tonalFinal = self.INITIAL_REGEX.sub('', syllable)

                    self.assertEquals(tonalFinal,
                        self.grJunctionFinalMNLRMapping[pinyinFinal][tone],
                        "Wrong conversion " + repr(syllable) + " to GR" \
                            + " for Pinyin syllable " + repr(pinyinSyllable) \
                            + " with the target final being " \
                            + repr(self.grJunctionFinalMNLRMapping[pinyinFinal]\
                                [tone]))

    def testGRJunctionSpecialTable(self):
        """Test if the conversion matches the special syllable table given by GR Junction."""
        for pinyinPlainSyllable in self.py.getPlainReadingEntities():
            if pinyinPlainSyllable in ['zhi', 'chi', 'shi', 'zi', 'ci',
                'si', 'ju', 'qu', 'xu', 'er'] \
                or (pinyinPlainSyllable[0] in ['y', 'w'] \
                    and pinyinPlainSyllable not in ['yor']): # TODO yor, ri
                for tone in [1, 2, 3, 4]:
                    if self.grJunctionSpecialMapping\
                        [pinyinPlainSyllable][tone] == '-':
                        continue

                    pinyinSyllable = self.py.getTonalEntity(pinyinPlainSyllable,
                        tone)

                    syllable = self.conv.convertEntities([pinyinSyllable])[0]

                    self.assertEquals(syllable, self.grJunctionSpecialMapping\
                            [pinyinPlainSyllable][tone],
                        "Wrong conversion " + repr(syllable) + " to GR" \
                            + " for Pinyin syllable " + repr(pinyinSyllable) \
                            + " with the target being " \
                            + repr(self.grJunctionSpecialMapping\
                                [pinyinPlainSyllable][tone]))


class ReadingConverterTestCase(unittest.TestCase):
    """Base class for testing of L{ReadingConverter}s."""

    def setUp(self):
        self.readingFactory = ReadingFactory()


class ReadingConverterValueTestCase(ReadingConverterTestCase):
    """
    Runs reference checks on ReadingConverters. These tests assure that the
    given values are returned correctly.
    @todo Fix: Include further GR test cases (uncomment)
    @todo Fix: Remodel to include cases like
        ('Jyutping', ImmutableDict({}), 'CantoneseYale', ImmutableDict({})): [
        (u'gwong2zau1waa2', u'gwóngjàuwá'),
        ],
        where conversion needs option 'YaleFirstTone': '1stToneFalling'
    """
    CONVERSION_VALUES = {
        # Extract from Y.R. Chao's Sayable Chinese quoted from English Wikipedia
        #   added concrete tone specifiers to "de", "men", "jing", "bu" and
        #   applied full form for g (.geh) choosing "always" neutral tone,
        #   removed hyphen in i-goong, changed the Pinyin transcript to not show
        #   tone sandhis, fixed punctuation marks in Pinyin
        ('GR', ImmutableDict({}), 'Pinyin', ImmutableDict({})): [
            (u'"Hannshyue" .de mingcheng duey Jonggwo yeou idean buhtzuenjinq .de yihwey. Woo.men tingshuo yeou "Yinnduhshyue", "Aijyishyue", "Hannshyue", erl meiyeou tingshuo yeou "Shilahshyue", "Luomaashyue", genq meiyeou tingshuo yeou "Inggwoshyue", "Meeigwoshyue". "Hannshyue" jey.geh mingcheng wanchyuan beaushyh Ou-Meei shyuejee duey nahshie yii.jing chernluen .de guulao-gwojia .de wenhuah .de ijoong chingkann .de tayduh.', u'"Hànxué" de míngchēng duì Zhōngguó yǒu yīdiǎn bùzūnjìng de yìwèi. Wǒmen tīngshuō yǒu "Yìndùxué", "Āijíxué", "Hànxué", ér méiyǒu tīngshuō yǒu "Xīlàxué", "Luómǎxué", gèng méiyǒu tīngshuō yǒu "Yīngguóxué", "Měiguóxué". "Hànxué" zhèige míngchēng wánquán biǎoshì Ōu-Měi xuézhě duì nàxiē yǐjing chénlún de gǔlǎo-guójiā de wénhuà de yīzhǒng qīngkàn de tàidù.'),
            #(u'hairtz', u'háizi'), (u'ig', u'yīgè'), (u'sherm', u'shénme'),
            #(u'sherm.me', u'shénme'), (u'tzeem.me', u'zěnme'),
            #(u'tzeem.me', u'zěnme'), (u'tzemm', u'zènme'),
            #(u'tzemm.me', u'zènme'), (u'jemm', u'zhème'),
            #(u'jemm.me', u'zhème'), (u'nemm', u'neme'), (u'nemm.me', u'neme'),
            #(u'.ne.me', u'neme'), (u'woom', u'wǒmen'), (u'shie.x', u'xièxie'),
            #(u'duey .le vx', u'duì le duì le'), (u'j-h-eh', u'zhè'),
            #(u"liibay’i", u'lǐbàiyī'), (u"san’g ren", u'sānge rén'),
            #(u"shyr’ell", u"shí'èr")
            ],
        ('WadeGiles', ImmutableDict({}), 'Pinyin', ImmutableDict({})): [
            (u'kuo', exception.AmbiguousConversionError),
            ],
        ('Jyutping', ImmutableDict({}), 'CantoneseYale', ImmutableDict({})): [
            (u'gwong2zau1waa2', u'gwóngjāuwá'),
            ],
        ('Jyutping', ImmutableDict({}), 'CantoneseYale', ImmutableDict({})): [
            (u'gwong2yau1waa2', u'gwóngyau1wá'),
            ],
        ('CantoneseYale', ImmutableDict({}), 'Jyutping', ImmutableDict({})): [
            (u'gwóngjāuwá', u'gwong2zau1waa2'),
            (u'gwóngjàuwá', u'gwong2zau1waa2'),
            ],
        ('CantoneseYale', ImmutableDict({}), 'CantoneseYale',
            ImmutableDict({'toneMarkType': 'Numbers'})): [
            (u'gwóngjāuwá', u'gwong2jau1wa2'),
            (u'gwóngjàuwá', u'gwong2jau1wa2'),
            ],
        ('CantoneseYale', ImmutableDict({'toneMarkType': 'Numbers'}),
            'CantoneseYale', ImmutableDict({})): [
            (u'gwong2jau1wa2', u'gwóngjāuwá'),
            (u'gwong2jauwa2', exception.ConversionError),
            ],
        ('CantoneseYale', ImmutableDict({'toneMarkType': 'Numbers',
            'YaleFirstTone': '1stToneFalling'}), 'CantoneseYale',
            ImmutableDict({})): [
            (u'gwong2jau1wa2', u'gwóngjàuwá'),
            ],
        #('CantoneseYale', ImmutableDict({'strictDiacriticPlacement': True}),
            #'CantoneseYale', ImmutableDict({'toneMarkType': 'Numbers'})): [
            #(u'gwóngjaùwá', exception.InvalidEntityError),
            #], # TODO see todo in CantoneseYaleOperator
        ('GR', ImmutableDict({'GRSyllableSeparatorApostrophe': "'"}),
            'GR', ImmutableDict({'GRRhotacisedFinalApostrophe': "'"})): [
            (u"tian'anmen", u'tian’anmen'),
            (u'jie’l', u"jie'l")
            ],
        ('WadeGiles', ImmutableDict({'toneMarkType': 'SuperscriptNumbers'}),
            'Pinyin', ImmutableDict({})): [
            (u'kuo³-yü²', u'guǒyú'),
            ],
        ('WadeGiles', ImmutableDict({}), 'Pinyin', ImmutableDict({})): [
            (u'kuo³-yü²', u'kuo³-yü²'),
            ],
        ('Pinyin', ImmutableDict({'toneMarkType': 'Numbers'}), 'MandarinIPA',
            ImmutableDict({})): [
            ('lao3shi1', u'lau˨˩.ʂʅ˥˥'),
            ],
        ('Pinyin', ImmutableDict({}), 'MandarinIPA', ImmutableDict({})): [
            ('lao3shi1', 'lao3shi1'),
            ],
        ('Pinyin', ImmutableDict({'toneMarkType': 'Numbers'}),
            'MandarinBraille', ImmutableDict({})): [
            ('lao3shi1', u'⠇⠖⠄⠱⠁'),
            ],
        ('Pinyin', ImmutableDict({}), 'MandarinBraille', ImmutableDict({})): [
            (u'lǎoshī', u'⠇⠖⠄⠱⠁'),
            ('lao3shi1', 'lao3shi1'),
            (u'mò', u'⠍⠢⠆'),
            (u'mè', u'⠍⠢⠆'),
            (u'gu', u'⠛⠥'),
            ],
        ('Pinyin', ImmutableDict({'toneMarkType': 'Numbers'}),
            'MandarinBraille', ImmutableDict({})): [
            (u'Qing ni deng yi1xia!', u'⠅⠡ ⠝⠊ ⠙⠼ ⠊⠁⠓⠫⠰⠂'),
            (u'mangwen shushe', u'⠍⠦⠒ ⠱⠥⠱⠢'),
            (u'shi4yong', u'⠱⠆⠹'),
            (u'yi1xia', u'⠊⠁⠓⠫'),
            (u'yi3xia', u'⠊⠄⠓⠫'),
            (u'gu', u'⠛⠥'),
            ],
        ('MandarinBraille', ImmutableDict({}), 'Pinyin',
            ImmutableDict({'toneMarkType': 'Numbers'})): [
            (u'⠍⠢⠆', exception.AmbiguousConversionError), # mo/me
            (u'⠇⠢⠆', exception.AmbiguousConversionError), # lo/le
            (u'⠢⠆', exception.AmbiguousConversionError),  # o/e
            (u'⠛⠥', u'gu5'),
            (u'⠛⠥⠁', u'gu1'),
            (u'⠛⠬', u'ju5'),
            ],
        ('Pinyin', ImmutableDict({'toneMarkType': 'Numbers'}),
            'MandarinBraille', ImmutableDict({'missingToneMark': 'fifth'})): [
            (u'gu', exception.ConversionError),
            (u'gu5', u'⠛⠥'),
            ],
        }

    def testConversionReferences(self):
        """Test if the given conversion references are reached."""
        for key in self.CONVERSION_VALUES:
            readingA, optionsA, readingB, optionsB = key
            for referenceSource, referenceTarget in self.CONVERSION_VALUES[key]:
                try:
                    string = self.readingFactory.convert(referenceSource,
                        readingA, readingB, sourceOptions=optionsA,
                        targetOptions=optionsB)
                except Exception, e:
                    string = e
                # if Exception raise, check if expected
                if isinstance(string, Exception):
                    if type(referenceTarget) not in [type(''), type(u'')] \
                        and not isinstance(e, referenceTarget):
                        self.assert_(False,
                            "Expected Exception " + repr(referenceTarget) \
                                + " but raised Exception" + repr(e) + ":\n" \
                                + traceback.format_exc())
                    elif type(referenceTarget) in [type(''), type(u'')]:
                        self.assert_(False,
                            "Expected " + repr(referenceTarget) \
                                + " but received Exception " + repr(e) + ":\n" \
                                + traceback.format_exc())
                else:
                    if type(referenceTarget) not in [type(''), type(u'')]:
                        self.assert_(False,
                            "Conversion should raise Exception " \
                                + repr(referenceTarget) + " but returned " \
                                + repr(string))
                    else:
                        self.assertEquals(string, referenceTarget,
                                "Conversion for reading '" + readingA \
                                    + "' to reading '" + readingB \
                                    + "' failed: \n" + repr(string) + "\n" \
                                    + repr(referenceTarget))


class CharacterLookupTestCase(unittest.TestCase):
    """Base class for testing the L{characterlookup.CharacterLookup} class."""
    def setUp(self):
        self.characterLookup = characterlookup.CharacterLookup('T')


class CharacterLookupReadingMethodsTestCase(CharacterLookupTestCase,
    ReadingOperatorTestCase):
    """
    Runs consistency checks on the reading methods of the
    L{characterlookup.CharacterLookup} class.
    """
    def setUp(self):
        CharacterLookupTestCase.setUp(self)
        ReadingOperatorTestCase.setUp(self)

    #def testGetCharactersForReadingAcceptsAllEntities(self):
        #"""Test if C{getCharactersForReading} accepts all reading entities."""
        #for reading, readingOptions in self.readingOperator:
            #if hasattr(self.readingOperator[reading], "getReadingEntities"):
                #entities = self.readingOperator[reading].getReadingEntities()
                #for entity in entities:
                    #try:
                        #self.assert_(type(self.characterLookup\
                            #.getCharactersForReading(entity, reading)) \
                                #== type([]),
                            #"Method getCharactersForReading() doesn't return" \
                                #+ " a list with entity " + repr(entity) \
                                #+ " for reading '"+ reading + "'")
                    #except exception.UnsupportedError:
                        #pass
                    #except exception.ConversionError:
                        #pass


if __name__ == '__main__':
    unittest.main()
