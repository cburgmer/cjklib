WadeGilesOperator -- Wade-Giles
===============================

:class:`cjklib.reading.operator.WadeGilesOperator` is an implementation
of the Mandarin Chinese romanisation Wade-Giles. It was in common use before
being replaced by :doc:`Pinyin <cjklib.reading.operator.PinyinOperator>`.

Features:

- tones marked by either superscript or plain digits,
- flexibility with derived writing, e.g. *szu* instead of *ssu*,
- alternative representation of characters *ŭ* and *ê*,
- handling of omissions of umlaut *ü* with resulting ambiguity,
- alternative marking of neutral tone (qingsheng) with either no mark
  or digits zero or five,
- configurable apostrophe for marking aspiration,
- placement of hyphens between syllables and
- guessing of input form (*reading dialect*).

Specifics
---------

Alterations
^^^^^^^^^^^
While the Wade-Giles romanisation system itself is a modification by H. A.
Giles, some further alterations exist, requiring an adaptable solution to
parse transliterated text.

Diacritics
""""""""""
While non-retroflex zero final syllables *tzŭ*, *tz’ŭ* and *ssŭ* carry a
breve on top of the *u* in the standard realization of Wade-Giles, it is
often left out while creating no ambiguity. In the same fashion finals
*-ê*, *-ên* and *-êng*, also syllable *êrh*, carry a circumflex over the
*e* which often is not written, and no ambiguity arises as no equivalent
forms with a plain *e* exist. These forms can be handled by setting options
``'zeroFinal'`` to ``'u'`` and ``'diacriticE'`` to ``'e'``.

Different to that, leaving out the umlaut on the *u* for finals *-ü*,
*-üan*, *-üeh* and *-ün* does create forms where back-conversion for some
cases is not possible as an equivalent vowel *u* form exists. Unambiguous
forms consist of initial *hs-* and *y-* (exception *yu*) and/or finals
*-üeh* and *-üo*, the latter being dialect forms not in use today. So
while for example *hsu* can be unambiguously converted back to its correct
form *hsü*, it is not clear if *ch’uan* is the wanted form or if it stems
from *ch’üan*, its diacritics being mangled. This reporting is done by
:meth:`~cjklib.reading.operator.WadeGilesOperator.checkPlainEntity`.
The omission of the umlaut can be controlled by setting
``'umlautU'`` to ``'u'``.

Others
""""""
For the non-retroflex zero final forms *tzŭ*, *tz’ŭ* and *ssŭ* the latter
is sometimes changed to *szŭ*. The operator can be configured by setting
the Boolean option ``'useInitialSz'``.

The neutral tone by default is not marked. As sometimes the digits zero or
five are used, they can be set by option ``'neutralToneMark'``.

The apostrophe marking aspiration can be set by ``'wadeGilesApostrophe'``.

Tones are by default marked with superscript characters. This can be
controlled by option ``'toneMarkType'``.

Recovering omitted apostrophes for aspiration is not possible as for all
cases there exists ambiguity. No means are provided to warn for possible
missing apostrophes. In case of uncertainty check for initials *p-*, *t-*,
*k-*, *ch-*, *ts* and *tz*.

Examples
""""""""
The :class:`~cjklib.reading.converter.WadeGilesDialectConverter` allows
conversion between said forms.

Restore diacritics:
    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert(u"K’ung³-tzu³", 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'zeroFinal': 'u'})
    u'K\u2019ung\xb3-tz\u016d\xb3'
    >>> f.convert(u"k’ai¹-men²-chien⁴-shan¹", 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'diacriticE': 'e'})
    u'k\u2019ai\xb9-m\xean\xb2-chien\u2074-shan\xb9'
    >>> f.convert(u"hsueh²", 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'umlautU': 'u'})
    u'hs\xfceh\xb2'

But:
    >>> f.convert(u"hsu⁴-ch’u³", 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'umlautU': 'u'})
    Traceback (most recent call last):
    ...
    cjklib.exception.AmbiguousConversionError: conversion for entity 'ch’u³' is ambiguous: ch’u³, ch’ü³

Guess non-standard form:
    >>> from cjklib.reading import operator
    >>> operator.WadeGilesOperator.guessReadingDialect(
    ...     u"k'ai1-men2-chien4-shan1")
    {'zeroFinal': u'\u016d', 'diacriticE': u'e', 'umlautU': u'\xfc', 'toneMarkType': 'numbers', 'useInitialSz': False, 'neutralToneMark': 'none', 'wadeGilesApostrophe': "'"}


.. index:: Wade-Giles

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.WadeGilesOperator
   :show-inheritance:
   :members:
   :undoc-members:
