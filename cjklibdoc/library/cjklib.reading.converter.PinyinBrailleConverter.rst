PinyinBrailleConverter -- Hanyu Pinyin to Braille
=================================================

Specifics
---------

Conversion from Braille to Pinyin is ambiguous. The syllable pairs mo/me,
e/o and le/lo will yield an :exc:`~cjklib.exception.AmbiguousConversionError`.
Furthermore conversion from Pinyin to Braille is lossy if tones are omitted,
which seems to be frequent in writing Braille for Chinese.
Braille doesn't mark the fifth tone, so converting back to Pinyin will
give syllables without a tone mark the fifth tone, changing originally unknown
ones. See :class:`~cjklib.reading.operator.MandarinBrailleOperator`.

Examples
^^^^^^^^
Convert from Pinyin to Braille using the
:class:`~cjklib.reading.ReadingFactory`:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert(u'Qǐng nǐ děng yīxià!', 'Pinyin', 'MandarinBraille',
    ...     targetOptions={'toneMarkType': 'None'})
    u'\u2805\u2821 \u281d\u280a \u2819\u283c \u280a\u2813\u282b\u2830\u2802'

.. seealso::

   `How is Chinese written in Braille? <http://www.braille.ch/pschin-e.htm>`_
      Rules

   `Chinese Braille <http://en.wikipedia.org/wiki/Chinese_braille>`_
      Article on Wikipedia

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.PinyinBrailleConverter
   :show-inheritance:
   :members:
   :undoc-members:
