PinyinIPAConverter --- Hanyu Pinyin to IPA
==========================================

Specifics
---------

The standard conversion table is based on the source mentioned below.
Though depiction in IPA depends on many factors and therefore might highly
vary it seems this source is not error-free: final *-üan* written [yan]
should be similar to *-ian* [iɛn] and *-iong* written [yŋ] should be
similar to *-ong* [uŋ].

As IPA allows for a big range of different representations for the sounds
in a varying degree no conversion to Pinyin is offered.

Currently conversion of *Erhua sound* is not supported.

Features:

- Default tone sandhi handling for lower third tone and neutral tone,
- extensibility of tone sandhi handling,
- extensibility for general coarticulation effects.

Limitations:

- Tone sandhi needs special treatment depending on the user's needs,
- transcription of onomatopoeic words will be limited to the general
  syllable scheme,
- limited linking between syllables (e.g. for 啊、呕) will not be
  considered and
- stress, intonation and accented speech are not covered.

.. index::
   pair: tone; sandhi

Tone sandhi
^^^^^^^^^^^
Speech in tonal languages is generally subject to *tone sandhi*. For
example in Mandarin *bu4 cuo4* for 不错 will render to *bu2 cuo4*, or
*lao3shi1* (老师) with a tone contour of 214 for *lao3* and 55 for *shi1*
will render to a contour 21 for *lao3*.

When translating to IPA the system has to deal with these tone sandhis and
therefore provides an option ``'sandhiFunction'`` that can be set to the user
specified handler. PinyinIPAConverter will only provide a very basic handler
:meth:`~cjklib.reading.converter.PinyinIPAConverter.lowThirdAndNeutralToneRule`
which will apply the contour 21 for the
third tone when several syllables occur and needs the user to supply proper
tone information, e.g. *ke2yi3* (可以) instead of the normal rendering as
*ke3yi3* to indicate the tone sandhi for the first syllable.

Further support will be provided for varying stress on syllables in the
neutral tone. Following a first tone the weak syllable will have a half-low
pitch, following a second tone a middle, following a third tone a half-high
and following a forth tone a low pitch.

There a further occurrences of tone sandhis:

- pronunciations of 一 and 不 vary in different tones depending on their
  context,
- directional complements like 拿出来 *ná chu lai* under some
  circumstances loose their tone,
- in a three syllable group ABC the second syllable B changes from
  second tone to first tone when A is in the first or second tone and
  C is not in the neutral tone.

Coarticulation
^^^^^^^^^^^^^^
In most cases conversion from Pinyin to IPA is straightforward if one does
not take tone sandhi into account. There are case though (when leaving
aside tones), where phonetic realisation of a syllable depends on its
context. The converter allows for handling coarticulation effects by
adding a hook ``coarticulationFunction`` to which a user-implemented
function can be given. An example implementation is given with
:meth:`~cjklib.reading.converter.PinyinIPAConverter.finalECoarticulation`.

Pronunciation of final *e*
""""""""""""""""""""""""""
:meth:`~cjklib.reading.converter.PinyinIPAConverter.finalECoarticulation`
supports the following coarticulation occurrence:
The final *e* found in syllables *de*, *me* and others is
pronounced /ɤ/ in the general case (see source below) but if tonal
stress is missing it will be pronounced /ə/. This implementation will
take care of this for the fifth tone. If no tone is specified
(``'None'``) an :exc:`~cjklib.exception.ConversionError` will be raised for
the syllables affected.

Source: Hànyǔ Pǔtōnghuà Yǔyīn Biànzhèng (汉语普通话语音辨正). Page 15,
Běijīng Yǔyán Dàxué Chūbǎnshè (北京语言大学出版社), 2003,
ISBN 7-5619-0622-6.


Source
^^^^^^
- Hànyǔ Pǔtōnghuà Yǔyīn Biànzhèng (汉语普通话语音辨正). Page 15, Běijīng Yǔyán
    Dàxué Chūbǎnshè (北京语言大学出版社), 2003, ISBN 7-5619-0622-6.
- San Duanmu: The Phonology of Standard Chinese. Second edition, Oxford
    University Press, 2007, ISBN 978-0-19-921578-2, ISBN 978-0-19-921579-9.
- Yuen Ren Chao: A Grammar of Spoken Chinese. University of California
    Press, Berkeley, 1968, ISBN 0-520-00219-9.

.. seealso::

   `Mandarin tone sandhi <http://web.mit.edu/jinzhang/www/pinyin/tones/index.html>`_
       Article on Mandarin tones

   `IPA <http://en.wikipedia.org/wiki/International_Phonetic_Alphabet>`_
      Article on Wikipedia

   `The Phonology of Standard Chinese. First edition, 2000 <http://books.google.de/books?id=tG0-Ad9CrBcC>`_
      Preview on Google Books

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.PinyinIPAConverter
   :show-inheritance:
   :members:
   :undoc-members:
