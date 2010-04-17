PinyinOperator --- Hanyu Pinyin
===============================

:class:`cjklib.reading.operator.PinyinOperator` is a complete implementation of
the standard Chinese Pinyin romanisation (*Hanyu Pinyin Fang'an*, 汉语拼音方案,
standardised in *ISO 7098*).

Features:

- tones marked by either diacritics or numbers,
- flexible handling of misplaced tone marks on input,
- flexible handling of wrong diacritics (e.g. breve instead of caron),
- correct placement of apostrophes to separate syllables,
- alternative representation of *ü*-character,
- alternatively shortend letters *ŋ*, *ẑ*, *ĉ*, *ŝ*,
- guessing of input form (*reading dialect*),
- support for Erhua and
- splitting of syllables into onset and rhyme.

Specifics
---------

.. index:: apostrophe

Apostrophes
^^^^^^^^^^^
Pinyin syllables need to be separated by an apostrophe in case their
decomposition will get ambiguous. A famous example might be the city
*Xi'an*, which if written *xian* would be read as one syllable, meaning
e.g. 'fresh'. Another example would be *Chang'an* which could be read
*chan'gan* if no delimiter is used in at least one of both cases.

Different rules exist where to place apostrophes. A simple yet sufficient
rule is implemented in
:meth:`~cjklib.reading.operator.PinyinOperator.aeoApostropheRule`
which is used as default in this class. Syllables starting with one of the
three vowels *a*, *e*, *o* will be separated. Remember that vowels
[i], [u], [y] are represented as *yi*, *wu*, *yu* respectively,
thus making syllable boundaries clear.
:meth:`~cjklib.reading.operator.PinyinOperator.compose`
will place apostrophes where required when composing the reading string.

An alternative rule can be specified to the constructor passing a function
as an option ``pinyinApostropheFunction``. A possible function could be a
rule separating all syllables by an apostrophe thus simplifying the reading
process for beginners.

On decomposition of strings it is important to check which of the possibly
several choices will be the one actually meant. E.g. syllable *xian* given
above should always be segmented into one syllable, solution *xi'an* is not
an option in this case. Therefore an alternative to
:meth:`~cjklib.reading.operator.PinyinOperator.aeoApostropheRule`
should make sure it guarantees proper decomposition, which is tested through
:meth:`~cjklib.reading.operator.PinyinOperator.isStrictDecomposition`.

Last but not least ``compose(decompose(string))`` will only be the identity
if apostrophes are applied properly according to the rule as wrongly
placed apostrophes will be kept when composing. Use
:meth:`~cjklib.reading.operator.PinyinOperator.removeApostrophes`
to remove separating apostrophes.

Example
"""""""

    >>> def noToneApostropheRule(opInst, precedingEntity, followingEntity):
    ...     return precedingEntity and precedingEntity[0].isalpha() \
    ...         and not precedingEntity[-1].isdigit() \
    ...         and followingEntity[0].isalpha()
    ...
    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert('an3ma5mi5ba5ni2mou1', 'Pinyin', 'Pinyin',
    ...     sourceOptions={'toneMarkType': 'numbers'},
    ...     targetOptions={'toneMarkType': 'numbers',
    ...         'missingToneMark': 'fifth',
    ...         'pinyinApostropheFunction': noToneApostropheRule})
    u"an3ma'mi'ba'ni2mou1"

.. index:: Erhua, R-colouring

R-colouring
^^^^^^^^^^^
The phenomenon Erhua (兒化音/儿化音, Erhua yin), i.e. the r-colouring of
syllables, is found in the northern Chinese dialects and results from
merging the formerly independent sound *er* with the preceding syllable. In
written form a word is followed by the character 兒/儿, e.g. 頭兒/头儿.

In Pinyin the Erhua sound is quite often expressed by appending a single
*r* to the syllable of the character preceding 兒/儿, e.g. *tóur* for
頭兒/头儿, to stress the monosyllabic nature and in contrast to words like
兒子/儿子 *ér'zi* where 兒/儿 *ér* constitutes a single syllable.

For decomposing syllables in Pinyin it is thus important to decide if the
*r* marking r-colouring should be an entity on its own account stressing
the representation in the character string with an own character or rather
stressing the monosyllabic nature and being part of a syllable of the
foregoing character. This can be configured at instantiation time. By
default the two-syllable form is chosen, which is more general as both
examples are allowed: ``banr`` and ``ban r`` (i.e. one without delimiter, one
with; both though being two entities in this representation).

Placement of tones
^^^^^^^^^^^^^^^^^^
Tone marks, if using the standard form with diacritics, are placed according
to official Pinyin rules. The PinyinOperator by default tries to work around
misplaced tone marks though, e.g. *\*tīan'ānmén* (correct: *tiān'ānmén*),
to ease handling of malformed input.
There are cases though, where this generous behaviour leads to a
different segmentation compared to the strict interpretation, as for
*\*hónglùo* which can fall into *hóng \*lùo* (correct: *hóng luò*) or
*hóng lù o* (also, using the first example, *tī an ān mén*). As the latter
result also stems from a wrong transcription, no means are implemented to
disambiguate between both solutions. The general behaviour is controlled
with option ``'strictDiacriticPlacement'``.

.. index::
   pair: shortened; letters

Shortened letters
^^^^^^^^^^^^^^^^^
Pinyin allows to shorten two-letter pairs *ng*, *zh*, *ch* and *sh* to
*ŋ*, *ẑ*, *ĉ* and *ŝ*. This behaviour can be controlled by option
``'shortenedLetters'``.

Source
^^^^^^
- Yǐn Bīnyōng (尹斌庸), Mary Felley (傅曼丽): Chinese romanization:
  Pronunciation and Orthography (汉语拼音和正词法). Sinolingua, Beijing,
  1990, ISBN 7-80052-148-6, ISBN 0-8351-1930-0.
- Ireneus László Legeza: Guide to transliterated Chinese in the modern
  Peking dialect. Conversion tables of the currently used international
  and European systems with comparative tables of initials and finals.
  E. J. Brill, Leiden, 1968.

.. seealso::

   `Where do the tone marks go? <http://www.pinyin.info/rules/where.html>`_
      Tone mark rules on pinyin.info.

   `Pinyin apostrophes <http://www.pinyin.info/romanization/hanyu/apostrophes.html>`_
      Apostrophe rules on pinyin.info.

   `Pinyin initals/finals <http://www.pinyin.info/rules/initials_finals.html>`_
      Initial/finals table on pinyin.info.

   `Erhua sound <http://en.wikipedia.org/wiki/Erhua>`_
      Article on Wikipedia.

   `The Unicode Consortium: The Unicode Standard, Version 5.0.0 <http://www.unicode.org/versions/Unicode5.0.0/>`_
      Chapter 7, European Alphabetic Scripts, 7.9 Combining Marks,
      defined by: The Unicode Standard, Version 5.0 (Boston, MA,
      Addison-Wesley, 2007. ISBN 0-321-48091-0)

   `Unicode: Combining Diacritical Marks <http://www.unicode.org/charts/PDF/U0300.pdf>`_
      Range: 0300-036F

   `Characters and Combining Marks <http://unicode.org/faq/char_combmark.html>`_
      Unicode: FAQ


.. index::
   pair: Pinyin; Hanyu

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.PinyinOperator
   :show-inheritance:
   :members:
   :undoc-members:
