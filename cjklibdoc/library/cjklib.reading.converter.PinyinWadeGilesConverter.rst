PinyinWadeGilesConverter --- Hanyu Pinyin to Wade-Giles
=======================================================

Specifics
---------

Upper- or lowercase will be transfered between syllables, no special
formatting according to anyhow defined standards will be guaranteed.
Upper-/lowercase will be identified according to three classes: either the
whole syllable is uppercase, only the initial letter is uppercase
(titlecase) or otherwise the whole syllable is assumed being lowercase. For
entities of single latin characters uppercase has precedence over titlecase,
e.g. *R5* will convert to *ER5* when Erhua forms are "unroled", not to
*Er5*.

Conversion cannot in general be done in a one-to-one manner. Standard Pinyin
has no notion to explicitly specify missing tonal information while this is
in general given in Wade-Giles by just omitting the tone digits. This
implementation furthermore doesn't support explicit depiction of *Erhua* in
the Wade-Giles romanisation system thus failing when r-colourised syllables
are found.

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.PinyinWadeGilesConverter
   :show-inheritance:
   :members:
   :undoc-members:
