GRPinyinConverter --- Gwoyeu Romatzyh to Pinyin
===============================================

Specifics
---------

Features:

- configurable mapping of options neutral tone when converting from GR,
- conversion of abbreviated forms of GR.

Upper- or lowercase will be transfered between syllables, no special
formatting according to anyhow defined standards will be guaranteed.
Upper-/lowercase will be identified according to three classes: either the
whole syllable is uppercase, only the initial letter is uppercase
(titlecase) or otherwise the whole syllable is assumed being lowercase. For
entities of single latin characters uppercase has precedence over titlecase,
e.g. *I* will convert to *YI* from Gwoyeu Romatzyh to Pinyin, not to
*Yi*.

Limitations
^^^^^^^^^^^
Conversion cannot in general be done in a one-to-one manner.
*Gwoyeu Romatzyh* (GR) gives the etymological tone for a syllable in
neutral tone while Pinyin doesn't. Thus converting neutral tone syllables
from Pinyin to GR will fail as the etymological tone is unknown to the
operator.

While tones in GR carry more information, *r-coloured* syllables
(*Erlhuah*) are rendered the way they are pronounced thus loosing
information about the underlying syllable. Converting those forms to Pinyin
is not always possible as for example *jieel* will raise an
L{AmbiguousConversionError} as it stems from *jǐ*, *jiě* and *jǐn*.
Having the original string in Chinese characters might help to disambiguate.

Neutral tone
""""""""""""
As described above, converting the neutral tone from Pinyin to GR fails.
Converting to Pinyin will lose knowledge about the etymological tone, and in
the case of *optional neutral tones* it has to be decided whether the
neutral tone version or the etymological tone is chosen, as Pinyin can only
display one. This can be controlled using option
``'grOptionalNeutralToneMapping'``.

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.GRPinyinConverter
   :show-inheritance:
   :members:
   :undoc-members:
