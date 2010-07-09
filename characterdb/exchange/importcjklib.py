#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Imports a data set from cjklib to characterdb.cjklib.org and prints the
corresponding XML document to stdout. Use together with
<http://www.mediawiki.org/wiki/Extension:Data_Transfer>.
Copyright (c) 2010, Christoph Burgmer

Released unter the MIT License.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import sys
import types

from cjklib.characterlookup import CharacterLookup
from cjklib import exception

class ImporterBase(object):
    TEMPLATE = None
    FIELDS = []

    def __init__(self, title):
        self.title = title

    @classmethod
    def _characterLookup(cls):
        if not hasattr(cls, '_cjk'):
            cls._cjk = CharacterLookup('T', 'Unicode')
        return cls._cjk

    @classmethod
    def titleIterator(cls):
        return iter([])

    def toXml(self):
        fieldContents = []
        for field in self.FIELDS:
            content = getattr(self, 'get%s' % field)()
            if not content:
                # work around bug in Data Transfer extension
                content = ' '
            fieldContents.append((field, content))
        return ('<Page Title="%s">' % self.title
                + '<Template Name="%s">' % self.TEMPLATE
                + ''.join(('<Field Name="%s">%s</Field>' % fieldEntry)
                          for fieldEntry in fieldContents)
                + '</Template>'
                + '</Page>')


class CharacterImporter(ImporterBase):
    TEMPLATE = "Character"
    FIELDS = ['Radical', 'Pinyin', 'Jyutping','Hangul', 'SemanticVariants',
              'SpecializedSemanticVariants', 'ZVariants', 'SimplifiedVariants',
              'TraditionalVariants']

    @classmethod
    def titleIterator(cls):
        return cls._characterLookup().getDomainCharacterIterator()

    def getRadical(self):
        # TODO what about radical forms themselvers?
        cjk = self._characterLookup()
        try:
            index = cjk.getCharacterKangxiRadicalIndex(self.title)
            return cjk.getKangxiRadicalForm(index)
        except exception.NoInformationError:
            return ''

    def _getReading(self, readingName, **options):
        cjk = self._characterLookup()
        return ', '.join(cjk.getReadingForCharacter(self.title, readingName,
                                                    **options))

    def getPinyin(self):
        return self._getReading('Pinyin', toneMarkType='numbers')

    def getJyutping(self):
        return self._getReading('Jyutping')

    def getHangul(self):
        return self._getReading('Hangul')

    def _getVariants(self, variantType):
        cjk = self._characterLookup()
        return ', '.join(cjk.getCharacterVariants(self.title, variantType))

    def getSemanticVariants(self):
        return self._getVariants('M')

    def getSpecializedSemanticVariants(self):
        return self._getVariants('P')

    def getZVariants(self):
        return self._getVariants('Z')

    def getSimplifiedVariants(self):
        return self._getVariants('S')

    def getTraditionalVariants(self):
        return self._getVariants('T')


class GlyphImporter(ImporterBase):
    TEMPLATE = "Glyph"
    FIELDS = ['Character', 'ManualStrokeOrder', 'Locale', 'Decomposition']

    @classmethod
    def titleIterator(cls):
        class GlyphIterator(object):
            def __init__(self):
                self._cjk = CharacterLookup('T', 'Unicode')
                self.characterIterator = self._cjk.getDomainCharacterIterator()
                self.curChar = None
                self.glyphQueue = []

            def __iter__(self):
                return self

            def next(self):
                while not self.glyphQueue:
                    self.curChar = self.characterIterator.next()
                    try:
                        glyphs = self._cjk.getCharacterGlyphs(self.curChar)
                        self.glyphQueue.extend(glyphs)
                    except exception.NoInformationError:
                        pass

                return '%s/%d' % (self.curChar, self.glyphQueue.pop())

        return GlyphIterator()

    def getCharacter(self):
        return self.title[0]

    def getManualStrokeOrder(self):
        cjk = self._characterLookup()
        so = cjk._getStrokeOrderEntry(self.title[0], int(self.title[2]))
        if so:
            return so
        else:
            return ''

    def getLocale(self):
        cjk = self._characterLookup()
        glyphs = cjk.getCharacterGlyphs(self.title[0])
        if len(glyphs) == 1:
            # don't map to locale if only one exists
            return ''
        else:
            locales = []
            for locale_ in 'TCJKV':
                glyph = cjk.getLocaleDefaultGlyph(self.title[0], locale_)
                if glyph == int(self.title[2]):
                    locales.append(locale_)

            # if all locales have the same default glyph 0, ignore
            if ''.join(locales) == 'TCJKV' and int(self.title[2]) == 0:
                return ''

        return ', '.join(locales)

    def getDecomposition(self):
        cjk = self._characterLookup()
        decompositions = cjk.getDecompositionEntries(self.title[0],
                                                     int(self.title[2]))
        decompositionStrings = []
        for decomp in decompositions:
            entries = []
            for entry in decomp:
                if isinstance(entry, basestring):
                    entries.append(entry)
                else:
                    char, _ = entry
                    if char == u'？':
                        entries.append(char)
                    else:
                        entries.append('%s/%d' % entry)
            decompositionStrings.append(''.join(entries))

        return '\n'.join(decompositionStrings)


def main():
    importModule = __import__("importcjklib")
    classes = dict((clss.TEMPLATE.lower(), clss)
                   for clss in importModule.__dict__.values()
                   if (type(clss) == types.TypeType
                       and issubclass(clss, importModule.ImporterBase)
                       and clss.TEMPLATE))

    if len(sys.argv) < 2:
        print """usage: python importcjklib.py TEMPLATE [TITLE1 [TITLE2 ...]]
Imports a data set from cjklib to characterdb.cjklib.org and prints the
corresponding XML document to stdout.

Available templates:"""
        print "\n".join(('  ' + name) for name in classes.keys())
        sys.exit(1)

    template = sys.argv[1].lower()
    templateClass = classes[template]

    if len(sys.argv) > 2:
        titleList = (title.decode('utf8') for title in sys.argv[2:])
    else:
        titleList = templateClass.titleIterator()

    print "<Pages>"
    for a in titleList:
        print templateClass(a).toXml().encode('utf8')
    print "</Pages>"


if __name__ == "__main__":
    main()
