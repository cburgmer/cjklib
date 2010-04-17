PinyinDialectConverter --- Hanyu Pinyin dialects
================================================

Specifics
---------

Examples
^^^^^^^^
The following examples show how to convert between different representations
of Pinyin.

- Create the Converter and convert from standard Pinyin to Pinyin with
  tones represented by numbers:

    >>> from cjklib.reading import *
    >>> targetOp = operator.PinyinOperator(toneMarkType='numbers')
    >>> pinyinConv = converter.PinyinDialectConverter(
    ...     targetOperators=[targetOp])
    >>> pinyinConv.convert(u'hànzì', 'Pinyin', 'Pinyin')
    u'han4zi4'

- Convert Pinyin written with numbers, the ü (u with umlaut) replaced
  by character v and omitted fifth tone to standard Pinyin:

    >>> sourceOp = operator.PinyinOperator(toneMarkType='numbers',
    ...    yVowel='v', missingToneMark='fifth')
    >>> pinyinConv = converter.PinyinDialectConverter(
    ...     sourceOperators=[sourceOp])
    >>> pinyinConv.convert('nv3hai2zi', 'Pinyin', 'Pinyin')
    u'nǚháizi'

- Or more elegantly:

    >>> f = ReadingFactory()
    >>> f.convert('nv3hai2zi', 'Pinyin', 'Pinyin',
    ...     sourceOptions={'toneMarkType': 'numbers', 'yVowel': 'v',
    ...     'missingToneMark': 'fifth'})
    u'nǚháizi'

- Decompose the reading of a dictionary entry from CEDICT into syllables
  and convert the ü-vowel and forms of *Erhua sound*:

    >>> pinyinFrom = operator.PinyinOperator(toneMarkType='numbers',
    ...     yVowel='u:', Erhua='oneSyllable')
    >>> syllables = pinyinFrom.decompose('sun1nu:r3')
    >>> print syllables
    ['sun1', 'nu:r3']
    >>> pinyinTo = operator.PinyinOperator(toneMarkType='numbers',
    ...     Erhua='twoSyllables')
    >>> pinyinConv = converter.PinyinDialectConverter(
    ...     sourceOperators=[pinyinFrom], targetOperators=[pinyinTo])
    >>> pinyinConv.convertEntities(syllables, 'Pinyin', 'Pinyin')
    [u'sun1', u'nü3', u'r5']

- Or more elegantly with entities already decomposed:

    >>> f.convertEntities(['sun1', 'nu:r3'], 'Pinyin', 'Pinyin',
    ...     sourceOptions={'toneMarkType': 'numbers', 'yVowel': 'u:',
    ...        'Erhua': 'oneSyllable'},
    ...     targetOptions={'toneMarkType': 'numbers',
    ...        'Erhua': 'twoSyllables'})
    [u'sun1', u'nü3', u'r5']

- Fix cosmetic errors in Pinyin input (note tone mark and apostrophe):

    >>> f.convert(u"Wǒ peí nǐ qù Xīān.", 'Pinyin', 'Pinyin')
    u"Wǒ péi nǐ qù Xī'ān."

- Fix more errors in Pinyin input (note diacritics):

    >>> string = u"Wŏ peí nĭ qù Xīān."
    >>> dialect = operator.PinyinOperator.guessReadingDialect(string)
    >>> f.convert(string, 'Pinyin', 'Pinyin', sourceOptions=dialect)
    u"Wǒ péi nǐ qù Xī'ān."


Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.PinyinDialectConverter
   :show-inheritance:
   :members:
   :undoc-members:
