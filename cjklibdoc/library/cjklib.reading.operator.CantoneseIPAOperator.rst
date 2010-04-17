CantoneseIPAOperator --- IPA for Cantonese
==========================================

:class:`cjklib.reading.operator.CantoneseIPAOperator` is an experimental
implementation of a transcription of Cantonese into the
*International Phonetic Alphabet* (*IPA*).

.. index::
   pair: stop; tones

Features:

- Tones can be marked either with tone numbers (1-6), tone contour
  numbers (e.g. 55), IPA tone bar characters or IPA diacritics,
- choice between high level and high falling tone for number marks,
- flexible set of tones,
- support for stop tones,
- handling of variable vowel length for tone contours of stop tone
  syllables and
- splitting of syllables into onset and rhyme.

Specifics
---------

CantonteseIPAOperator does not supply the same closed set of syllables as
other ReadingOperators as IPA provides different ways to represent
pronunciation. Because of that a user defined IPA syllable will not easily
map to another transcription system and thus only basic support is provided
for this direction.

This operator supplies an additional method
:meth:`~cjklib.reading.operator.CantoneseIPAOperator.getOnsetRhyme` which allows
breaking down syllables into their onset and rhyme.

Tones
^^^^^
Tones in IPA can be expressed using different schemes. The following schemes
are implemented here:

- Numbers, tone numbers for the six-tone scheme,
- ChaoDigits, numbers displaying the levels of tone contours, e.g.
  55 for the high level tone,
- IPAToneBar, IPA modifying tone bar characters, e.g. ɛw˥˥,
- None, no support for tone marks

Implementational details
^^^^^^^^^^^^^^^^^^^^^^^^
The operator comes with three different set of tones to accommodate the user
but at the same time handle all different tone types. This setting is
controlled by option ``'stopTones'``, where ``'none'`` will force the set of 7
basic tones, ``'general'`` will add the three stop tones found in
:attr:`~cjklib.reading.operator.CantoneseIPAOperator.STOP_TONES`,
and ``'explicit'`` will add one stop tone for each possible
vowel length i.e. *short* and *long*, making up the maximum count of 13.
Internally the set with explicit stop tones is used.

Sources
^^^^^^^
- Robert S. Bauer, Paul K. Benedikt: Modern Cantonese Phonology
    (摩登廣州話語音學). Walter de Gruyter, 1997, ISBN 3-11-014893-5.
- Robert S. Bauer: Hong Kong Cantonese Tone Contours. In: Studies in
    Cantonese Linguistics. Linguistic Society of Hong Kong, 1998,
    ISBN 962-7578-04-5.

.. seealso::

   `Modern Cantonese Phonology <http://books.google.de/books?id=QWNj5Yj6_CgC>`_
      Preview on Google Books.

.. index::
   pair: Cantonese; IPA

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.CantoneseIPAOperator
   :show-inheritance:
   :members:
   :undoc-members:
