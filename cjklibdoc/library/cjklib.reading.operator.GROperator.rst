GROperator --- Gwoyeu Romatzyh
==============================

:class:`cjklib.reading.operator.GROperator` is a mature implementation of
the Chinese Gwoyeu Romatzyh romanisation (國語羅馬字, often abbreviated *GR*).
Gwoyeu Romatzyh is different from most other romanisation methods
as that it encodes Chinese tones using alphabetic characters
instead of diacritics or digits.

Features:

- support of abbreviated forms (*zh*, *j*, *g*, *sherm*, ...),
- conversion of abbreviated forms to full forms,
- placement of apostrophes before 0-initial syllables,
- support for different apostrophe characters,
- support for *r-coloured* syllables (*Erlhuah*),
- syllable repetition markers (*x*, *v*, *vx*) and
- guessing of input form (*reading dialect*).

Specifics
---------

.. index::
   triple: optional; neutral; tone

Tones
^^^^^
Tones are transcribed rigorously as syllables in the neutral tone
additionally carry the original (etymological) tone information. Y.R. Chao
also annotates the optional neutral tone (e.g. *buh jy˳daw*) which can
be pronounced with either the neutral tone or the etymological one. Compared
to other reading operators for Mandarin, special care has to be taken to
cope with these special requirements.

.. index:: Erhua, Erlhuah, R-colouring

R-colouring
^^^^^^^^^^^
Gwoyeu Romatzyh renders rhotacised syllables (Erlhuah) by trying to
give the actual pronunciation. As the effect of r-colouring loses the
information of the underlying etymological syllable conversion between the
r-coloured form back to the underlying form can not be done in an
unambiguous way. As furthermore finals *i*, *iu*, *in*, *iun* contrast
in the first and the second tone but not in the third and the forth tone
conversion between different tones (including the base form) cannot be made
in a general manner: 小鸡儿 *sheau-jiel* is different to 小街儿
*sheau-jie’l* but 几儿 *jieel* (from jǐ) equals 姐儿 *jieel* (from jiě),
see Chao.

Thus this ReadingOperator lacks the general handling of syllable renderings
and many methods narrow the range of syllables allowed. While original forms
can carry any tone (even though Mandarin doesn't make use of some
combinations), r-coloured forms for Erlhuah will currently be limited to
those given in the source by Y.R. Chao. Those not mentioned there will raise
an :exc:`~cjklib.exception.UnsupportedError`.

.. index::
   pair: abbreviated; form

Abbreviations
^^^^^^^^^^^^^
Yuen Ren Chao includes several abbreviated forms in his books (references
see below). For example 個/个 which would be fully transcribed as *.geh* or
*˳geh* is abbreviated as *g*. These forms can be accessed by
:meth:`~cjklib.reading.operator.GROperator.getAbbreviatedForms` and
:meth:`~cjklib.reading.operator.GROperator.getAbbreviatedFormData`, and
their usage can be contolled by option ``'abbreviations'``. Use the
:class:`~cjklib.reading.converter.GRDialectConverter`
to convert these abbreviations into their full forms:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert('Hairtz', 'GR', 'GR', breakUpAbbreviated='on')
    u'Hair.tzy'

.. index::
   pair: repetition; marker

Repetition markers
""""""""""""""""""
Special *abbreviated forms* are given in form of repetition markers.
These take the form *x* and *v* or a combination *vx* for repetition of
the last syllable/the second last syllable or both, e.g. *shie.x* for
*shie.shie*, *deengiv* for *deengideeng* and *duey .le vx* for
*duey .le duey .le*. Both forms can be preceded by a neutral tone mark,
e.g. *.x* or *˳v*.

Sources
^^^^^^^
- Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
  Press, Berkeley, 1968, ISBN 0-520-00219-9.
- Yuen Ren Chao: Mandarin Primer: an intensive course in spoken Chinese.
  Harvard University Press, Cambridge, 1948.

.. seealso::

   `GR Junction <http://home.iprimus.com.au/richwarm/gr/gr.htm>`_
      by Richard Warmington

   `A Guide to Gwoyeu Romatzyh Tonal Spelling of Chinese <http://eall.hawaii.edu/chn/chn451/03-Luomazi/GR.html>`_
      Overview article

   `Gwoyeu Romatzyh <http://en.wikipedia.org/wiki/Gwoyeu_Romatzyh>`_
      Article on the English Wikipedia

.. index:: GR, Gwoyeu_Romatzyh

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.GROperator
   :show-inheritance:
   :members:
   :undoc-members:
