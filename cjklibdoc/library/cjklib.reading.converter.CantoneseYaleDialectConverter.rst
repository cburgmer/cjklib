CantoneseYaleDialectConverter --- Cantonese Yale dialects
=========================================================

Specifics
---------

.. index::
   triple: high; level; tone
   triple: high; falling; tone

High Level vs. High Falling Tone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As described in :class:`~cjklib.reading.operator.CantoneseYaleOperator`
the abbreviated form of the Cantonese Yale romanisation system which uses
numbers as tone marks makes no distinction between the high level tone and
the high falling tone. On conversion to the form with diacritical marks it
is thus important to choose the correct mapping. This can be configured by
applying a special instance of a
:class:`~cjklib.reading.operator.CantoneseYaleOperator`
(or telling the :class:`~cjklib.reading.ReadingFactory` which operator to use).

Example:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert(u'gwong2jau1wa2', 'CantoneseYale', 'CantoneseYale',
    ...     sourceOptions={'toneMarkType': 'numbers',
    ...         'yaleFirstTone': '1stToneFalling'})
    u'gwóngjàuwá'

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.CantoneseYaleDialectConverter
   :show-inheritance:
   :members:
   :undoc-members:
