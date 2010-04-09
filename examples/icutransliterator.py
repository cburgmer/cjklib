#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Exposes the reading conversion methods of cjklib to ICU as Transliterator
(L{http://icu-project.org/apiref/icu4c/classTransliterator.html}).

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
import urllib
import PyICU as icu

from cjklib.reading import ReadingFactory

class ReadingTransliterator(icu.Transliterator):
    def __init__(self, fromReading, toReading, variant=None, **options):
        self.id = '%s-%s' % (fromReading, toReading)

        if variant: self.id += '/' + variant

        icu.Transliterator.__init__(self, self.id)

        self._conv = ReadingFactory().createReadingConverter(fromReading,
            toReading, **options)

    def handleTransliterate(self, text, position, complete):
        substring = unicode(text[position.start:position.limit])

        converted = self._conv.convert(substring)
        text[position.start:position.limit] = converted

        lenDiff = len(substring) - len(converted)
        position.limit -= lenDiff
        position.contextLimit -= lenDiff

        position.start = position.limit

    @staticmethod
    def register(fromReading, toReading, variant=None, registerInverse=False,
        **options):
        trans = ReadingTransliterator(fromReading, toReading, variant=variant,
            **options)
        icu.Transliterator.registerInstance(trans)

        if registerInverse:
            inverseOptions = options.copy()
            inverseOptions['targetOptions'] = options.get('sourceOptions', {})
            inverseOptions['sourceOptions'] = options.get('targetOptions', {})

            invTrans = ReadingTransliterator(toReading, fromReading,
                variant=variant, **inverseOptions)
            icu.Transliterator.registerInstance(invTrans)

        return trans.id


def main():
    encoding = sys.stdout.encoding or locale.getpreferredencoding() or 'ascii'

    if len(sys.argv) > 1:
        text = sys.argv[1].decode(encoding)
    else:
        text = 'hoeng1gong2 fo1gei6 daai6hok6'

    _id = ReadingTransliterator.register('Jyutping', 'CantoneseYale',
        variant='highfalling', yaleFirstTone='1stToneFalling',
        registerInverse=True)
    print "Registered transform %s" % _id

    #r = icu.Transliterator.createInstance("NumericPinyin-Latin",
    r = icu.Transliterator.createInstance(_id,
        icu.UTransDirection.UTRANS_FORWARD)

    print ("In:  %s" % text).encode(encoding)
    print ("Out: %s" % r.transliterate(text)).encode(encoding)

    #text = u'hèunggóng fògeih daaihhohk'
    #print r.createInverse().transliterate(text).encode(encoding)

if __name__ == "__main__":
    main()
