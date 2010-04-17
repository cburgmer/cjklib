MandarinIPAOperator --- IPA for Cantonese
=========================================

:class:`cjklib.reading.operator.MandarinIPAOperator` is an implementation
of a transcription of Standard Mandarin into the
*International Phonetic Alphabet* (*IPA*).

Specifics
---------

Features:

- Tones can be marked either with tone numbers (1-4), tone contour
  numbers (e.g. 214), IPA tone bar characters or IPA diacritics,
- support for low third tone (1/2 third tone) with tone contour 21,
- four levels of the neutral tone for varying stress depending on the
  preceding syllable and
- splitting of syllables into onset and rhyme using method
  :meth:`~cjklib.reading.operator.MandarinIPAOperator.getOnsetRhyme`.

Tones
^^^^^
Tones in IPA can be expressed using different schemes. The following schemes
are implemented here:

- Numbers, regular tone numbers from 1 to 5 for first tone to fifth
  (qingsheng),
- ChaoDigits, numbers displaying the levels of tone contours, e.g.
  214 for the regular third tone,
- IPAToneBar, IPA modifying tone bar characters, e.g. ɕi˨˩˦,
- Diacritics, diacritical marks and finally
- None, no support for tone marks

Unlike other operators for Mandarin, distinction is made for six different
tonal occurrences. The third tone is affected by tone sandhi and basically
two different tone contours exist. Therefore
:meth:`~cjklib.reading.operator.MandarinIPAOperator.getTonalEntity` and
:meth:`~cjklib.reading.operator.MandarinIPAOperator.splitEntityTone`
work with string representations as tones defined in
:attr:`~cjklib.reading.operator.MandarinIPAOperator.TONES`.
Same behaviour as found in other operators for Mandarin can be
achieved by simply using the first character of the given string:

    >>> from cjklib.reading import operator
    >>> ipaOp = operator.MandarinIPAOperator(toneMarkType='ipaToneBar')
    >>> syllable, toneName = ipaOp.splitEntityTone(u'mən˧˥')
    >>> tone = int(toneName[0])

The implemented schemes render tone information differently. Mapping might
lose information so a full back-transformation can not be guaranteed.

Source
^^^^^^
- Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
  Press, Berkeley, 1968, ISBN 0-520-00219-9.


.. index::
   pair: Mandarin; IPA

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.MandarinIPAOperator
   :show-inheritance:
   :members:
   :undoc-members:
