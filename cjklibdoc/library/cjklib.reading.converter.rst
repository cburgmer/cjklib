:mod:`cjklib.reading.converter` --- Conversion between character readings
=========================================================================


.. automodule:: cjklib.reading.converter


.. toctree::
   :hidden:

   cjklib.reading.converter.PinyinDialectConverter
   cjklib.reading.converter.WadeGilesDialectConverter
   cjklib.reading.converter.PinyinWadeGilesConverter
   cjklib.reading.converter.GRDialectConverter
   cjklib.reading.converter.GRPinyinConverter
   cjklib.reading.converter.PinyinIPAConverter
   cjklib.reading.converter.PinyinBrailleConverter
   cjklib.reading.converter.CantoneseYaleDialectConverter
   cjklib.reading.converter.JyutpingDialectConverter
   cjklib.reading.converter.JyutpingYaleConverter
   cjklib.reading.converter.ShanghaineseIPADialectConverter


Architecture
------------

The basic method is :meth:`~cjklib.reading.converter.ReadingConverter.convert`
which converts one input string from one reading to another.

The method :meth:`~cjklib.reading.converter.ReadingConverter.getDefaultOptions`
will return the conversion default settings.


What gets converted
^^^^^^^^^^^^^^^^^^^
The conversion process uses the
:class:`~cjklib.reading.operator.ReadingOperator` for the source reading to
decompose the given string into the single entities. The decomposition
contains reading entities and entities that don't represent any
pronunciation. While the goal is to convert included reading entities to the
target reading, some convertes might decide to also convert non-reading
entities. This can be for example delimiters like apostrophes that differ
between romanisations or punctuation marks that have a defined
representation in the target system, e.g. Braille.

Errors
""""""
By default conversion won't stop on entities that closely resemble other
reading entities but itself are not valid. Those will turn up unchanged in
the result and can cause a :exc:`~cjklib.exception.CompositionError`
when the target operator decideds that it is impossible to link a converted
entity with a non-converted one as it would make it impossible to later
determine the entity boundaries.
Most of those errors will probably result from bad input
that fails on conversion. This can be solved by telling the source operator
to be strict on decomposition (where supported) so that the error will
be reported beforehand. The followig example tries to convert *xiǎo tōu*
("thief"), misspelled as *\*xiǎo tō*:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> print f.convert(u'xiao3to1', 'Pinyin', 'GR',
    ...     sourceOptions={'toneMarkType': 'numbers'})
    Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    ...
    cjklib.exception.CompositionError: Unable to delimit non-reading entity 'to1'
    >>> print f.convert(u'xiao3to1', 'Pinyin', 'GR',
    ...     sourceOptions={'toneMarkType': 'numbers',
    ...         'strictSegmentation': True})
    Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    ...
    cjklib.exception.DecompositionError: Segmentation of 'to1' not possible or invalid syllable

Not being strict results in a lazy conversion, which might fail in some
cases as shown above. ``u'xiao3 to1'`` (with a space in between) though will
work for the lazy way (``'to1'`` not being converted), while the strict
version will still report the wrong *\*to1*.

Other errors that can arise:

- :exc:`~cjklib.exception.AmbiguousDecompositionError`,
  if the source string can not be decomposed unambigiuously,
- :exc:`~cjklib.exception.ConversionError`,
  e.g. if the target system doesn't support a feature given in the source
  string, and
- :exc:`~cjklib.exception.AmbiguousConversionError`, if a given entity can be
  mapped to more than one entity in the target reading.


.. index::
   pair: brige; reading

.. _readingbridge-label:

Bridge
^^^^^^

Conversions between two Readings can be made using a third reading
if no direct conversion is defined. This reading is called a
*bridge reading* and is implemented in
:class:`~cjklib.reading.converter.BridgeConverter`. Using the routines
from the :class:`~cjklib.reading.ReadingFactory` will automatically employ
bridges if needed.

Examples
--------
Convert a string from *Jyutping* to *Cantonese Yale*:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert('gwong2jau1waa2', 'Jyutping', 'CantoneseYale')
    u'gwóngyāuwá'

This is also possible creating a converter instance explicitly using the
factory:

    >>> jyc = f.createReadingConverter('GR', 'Pinyin')
    >>> jyc.convert('Woo.men tingshuo yeou "Yinnduhshyue", "Aijyishyue"')
    u'Wǒmen tīngshuō yǒu "Yìndùxué", "Āijíxué"'

Convert between different dialects of the same reading *Wade-Giles*:

    >>> f.convert(u'kuo3-yü2', 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'toneMarkType': 'numbers'},
    ...     targetOptions={'toneMarkType': 'superscriptNumbers'})
    u'kuo³-yü²'

See :class:`~cjklib.reading.converter.PinyinDialectConverter` for more examples.

Reading conversions
-------------------

- Mandarin Chinese

  * :doc:`cjklib.reading.converter.PinyinDialectConverter --- Hanyu Pinyin dialects <cjklib.reading.converter.PinyinDialectConverter>`
  * :doc:`cjklib.reading.converter.WadeGilesDialectConverter --- Wade-Giles dialects <cjklib.reading.converter.WadeGilesDialectConverter>`
  * :doc:`cjklib.reading.converter.PinyinWadeGilesConverter --- Hanyu Pinyin to Wade-Giles <cjklib.reading.converter.PinyinWadeGilesConverter>`
  * :doc:`cjklib.reading.converter.GRDialectConverter --- Gwoyeu Romatzyh dialects <cjklib.reading.converter.GRDialectConverter>`
  * :doc:`cjklib.reading.converter.GRPinyinConverter --- Gwoyeu Romatzyh to Pinyin <cjklib.reading.converter.GRPinyinConverter>`
  * :doc:`cjklib.reading.converter.PinyinIPAConverter --- Hanyu Pinyin to IPA <cjklib.reading.converter.PinyinIPAConverter>`
  * :doc:`cjklib.reading.converter.PinyinBrailleConverter --- Pinyin to Braille <cjklib.reading.converter.PinyinBrailleConverter>`

- Cantonese

  * :doc:`cjklib.reading.converter.CantoneseYaleDialectConverter --- Cantonese Yale dialects <cjklib.reading.converter.CantoneseYaleDialectConverter>`
  * :doc:`cjklib.reading.converter.JyutpingDialectConverter --- Jyutping dialects <cjklib.reading.converter.JyutpingDialectConverter>`
  * :doc:`cjklib.reading.converter.JyutpingYaleConverter --- Jyutping to Cantonese Yale <cjklib.reading.converter.JyutpingYaleConverter>`

- Shanghainese

  * :doc:`cjklib.reading.converter.ShanghaineseIPADialectConverter --- Shanghainese IPA dialects <cjklib.reading.converter.ShanghaineseIPADialectConverter>`


Base classes
------------

.. autoclass:: ReadingConverter
   :show-inheritance:
   :members:
   :undoc-members:


.. autoclass:: EntityWiseReadingConverter
   :show-inheritance:
   :members:
   :undoc-members:


.. autoclass:: DialectSupportReadingConverter
   :show-inheritance:
   :members:
   :undoc-members:


.. autoclass:: RomanisationConverter
   :show-inheritance:
   :members:
   :undoc-members:


.. autoclass:: BridgeConverter
   :show-inheritance:
   :members:
   :undoc-members:

