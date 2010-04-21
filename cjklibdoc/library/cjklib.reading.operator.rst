:mod:`cjklib.reading.operator` --- Operation on character readings
==================================================================

.. automodule:: cjklib.reading.operator

.. toctree::
   :hidden:

   cjklib.reading.operator.PinyinOperator
   cjklib.reading.operator.WadeGilesOperator
   cjklib.reading.operator.GROperator
   cjklib.reading.operator.MandarinIPAOperator
   cjklib.reading.operator.MandarinBrailleOperator
   cjklib.reading.operator.CantoneseYaleOperator
   cjklib.reading.operator.JyutpingOperator
   cjklib.reading.operator.CantoneseIPAOperator
   cjklib.reading.operator.ShanghaineseIPAOperator
   cjklib.reading.operator.HangulOperator
   cjklib.reading.operator.KanaOperator
   cjklib.reading.operator.KatakanaOperator
   cjklib.reading.operator.HiraganaOperator

.. index::
   single: syllable
   pair: basic; entity, reading; entity, formatting; entity

Architecture
------------

A :class:`~cjklib.reading.operator.ReadingOperator` supports basic operations
on string written in a character reading:

- :meth:`~cjklib.reading.operator.ReadingOperator.decompose` breaks down
  a text into the basic entities of that reading (additional non reading
  substrings are also accepted).
- :meth:`~cjklib.reading.operator.ReadingOperator.compose` joins these entities
  together and might apply formatting rules needed by the reading.
- :meth:`~cjklib.reading.operator.ReadingOperator.isReadingEntity` and
  :meth:`~cjklib.reading.operator.ReadingOperator.isFormattingEntity` are
  provided to check which of the strings returned by
  :meth:`~cjklib.reading.operator.ReadingOperator.decompose` are
  supported entities for the given reading. While a *reading entity*
  expresses an entity of the language (in most cases a *syllable*), a
  *formatting entity* merely exists for the convenience of the written form,
  e.g. punctuation marks or syllable separators.
- :meth:`~cjklib.reading.operator.ReadingOperator.getDefaultOptions`
  will return the default *reading dialect*.

Many child classes add many more reading specific methods.

.. index:: romanisation

Romanisation
^^^^^^^^^^^^
Additional to :meth:`~cjklib.reading.operator.ReadingOperator.decompose`
provided by the class :class:`~cjklib.reading.operator.ReadingOperator` a
:class:`~cjklib.reading.operator.RomanisationOperator` offers a method
:meth:`~cjklib.reading.operator.RomanisationOperator.getDecompositions`
that returns several possible decompositions in an ambiguous case. Also,
as Romanisations have a fixed set of entities, a method
:meth:`~cjklib.reading.operator.RomanisationOperator.getReadingEntities`
offers access to a list of all accepted *reading entities*.

.. index::
   pair: strict; decomposition, ambiguous; decomposition, letter; case
   pair: unambiguous; decomposition

Decomposition
"""""""""""""
Transcriptions into the Latin (or Cyrilic) alphabet generate the problem that
syllable boundaries or boundaries of entities belonging to single
Chinese characters aren't clear anymore once entities are grouped together.

Therefore it is important to have methods at hand to separate strings
and to split those into single entities. This though cannot always be done
in a clear and unambiguous way as several different decompositions might be
possible thus leading to the general case of *ambiguous decompositions*.

Many romanisations do provide a way to tackle this problem. *Pinyin* for
example requires the use of an apostrophe (``'``) when the reverse process
of splitting the string into syllables gets ambiguous. The *Wade-Giles*
romanisation in its strict implementation asks for a hyphen used between all
syllables. The *LSHK's* *Jyutping* when written with tone marks will always be
clearly decomposable as the digits mark syllable borders.

The method
:meth:`~cjklib.reading.operator.RomanisationOperator.isStrictDecomposition`
can be implemented to check if one possible decomposition is the
*strict decomposition* offered by the romanisation's protocol.
This method should guarantee that under all
circumstances only one decomposed version will be regarded as strict.

If no strict version is yielded and different decompositions exist an
*unambiguous decomposition* can not be made. These decompositions can be
accessed through method
:meth:`~cjklib.reading.operator.RomanisationOperator.getDecompositions`,
even in a cases where a strict decomposition exists.

Letter case
"""""""""""
Romanisations are special to other readings as their entities can be written
in upper or lower *case*, or in a mix of them. By default operators will
recognise both, this behaviour can be changed with option ``'case'`` which
can alternatively be changed to ``'lower'``. Upper case is not explicitly
supported. If such a writing is needed, this behaviour can be implemented
by choosing lower case and converting strings to and from the operator
manually. Method
:meth:`~cjklib.reading.operator.RomanisationOperator.getReadingEntities`
will by default return lower case entities.

.. index:: tone

Tonal readings
^^^^^^^^^^^^^^
Tonal readings are supported with class
:class:`~cjklib.reading.operator.TonalFixedEntityOperator`.
It provides two methods
:meth:`~cjklib.reading.operator.TonalFixedEntityOperator.getTonalEntity` and
:meth:`~cjklib.reading.operator.TonalFixedEntityOperator.splitEntityTone`
to cope with tonal information in text.

Tones
"""""
Operators are free to handle tones according to their needs. No data type
constraint is given so that some will handle tones as integers, while others
will handle strings. Even the count of tones between different operators for
the same language may vary as one system might be more specific about tonal
features.

.. index::
   pair: plain; entity

Plain entities
""""""""""""""
While some operators have a fixed set of accepted entities, the more
specific subgroup for tonal languages has a set of basic entities, such
entity here being called *plain entity*, which can be annotated with tonal
information to yield a regular reading entity. Some *plain entities* might
themselves be normal reading entities, while others might be not. No
requirements are made that the set of plain entity in cross product with
the set of tones will fully span the set of reading entities.



Examples
--------
Decompose a reading string in *Gwoyeu Romatzyh* into single entities:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.decompose('"Hannshyue" .de mingcheng duey Jonggwo [...]', 'GR')
    ['"', 'Hann', 'shyue', '" ', '.de', ' ', 'ming', 'cheng', ' ', 'duey', ' ', 'Jong', 'gwo', ' [...]']

The same can be done by directly using the operator's instance:

    >>> from cjklib.reading import operator
    >>> cy = operator.CantoneseYaleOperator()
    >>> cy.decompose(u'gwóngjàuwá')
    [u'gwóng', u'jàu', u'wá']

Composing will reverse the process, using a *Pinyin* string:

    >>> f.compose([u'xī', u'ān'], 'Pinyin')
    u"xī'ān"

For more complex operators, see 
:class:`~cjklib.reading.operator.PinyinOperator`
or :class:`~cjklib.reading.operator.MandarinIPAOperator`.


Readings
--------

- Mandarin Chinese

  * :doc:`cjklib.reading.operator.PinyinOperator --- Hanyu Pinyin <cjklib.reading.operator.PinyinOperator>`
  * :doc:`cjklib.reading.operator.WadeGilesOperator --- Wade-Giles <cjklib.reading.operator.WadeGilesOperator>`
  * :doc:`cjklib.reading.operator.GROperator --- Gwoyeu Romatzyh <cjklib.reading.operator.GROperator>`
  * :doc:`cjklib.reading.operator.MandarinIPAOperator --- IPA for Mandarin <cjklib.reading.operator.MandarinIPAOperator>`
  * :doc:`cjklib.reading.operator.MandarinBrailleOperator --- Braille for Mandarin <cjklib.reading.operator.MandarinBrailleOperator>`

- Cantonese

  * :doc:`cjklib.reading.operator.CantoneseYaleOperator --- Cantonese Yale <cjklib.reading.operator.CantoneseYaleOperator>`
  * :doc:`cjklib.reading.operator.JyutpingOperator --- Jyutping <cjklib.reading.operator.JyutpingOperator>`
  * :doc:`cjklib.reading.operator.CantoneseIPAOperator --- IPA for Cantonese <cjklib.reading.operator.CantoneseIPAOperator>`

- Shanghainese

  * :doc:`cjklib.reading.operator.ShanghaineseIPAOperator --- IPA for Shanghainese <cjklib.reading.operator.ShanghaineseIPAOperator>`

- Korean

  * :doc:`cjklib.reading.operator.HangulOperator --- Hangul <cjklib.reading.operator.HangulOperator>`

- Japanese

  * :doc:`cjklib.reading.operator.KanaOperator --- Kana <cjklib.reading.operator.KanaOperator>`
  * :doc:`cjklib.reading.operator.KatakanaOperator --- Katakana <cjklib.reading.operator.KatakanaOperator>`
  * :doc:`cjklib.reading.operator.HiraganaOperator --- Hiragana <cjklib.reading.operator.HiraganaOperator>`

Base classes
------------

.. autoclass:: ReadingOperator
   :members:
   :undoc-members:

.. autoclass:: RomanisationOperator
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: SimpleEntityOperator
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: TonalFixedEntityOperator
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: TonalIPAOperator
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: TonalRomanisationOperator
   :show-inheritance:
   :members:
   :undoc-members:
   
