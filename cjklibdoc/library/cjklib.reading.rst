:mod:`cjklib.reading` --- Character reading based functions
===========================================================


.. automodule:: cjklib.reading

This includes
:class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>` used
to handle basic operations like decomposing strings written in a reading
into their basic entities (e.g. syllables) and for some languages
getting tonal information, syllable onset and rhyme and other features.
Furthermore it includes :class:`~cjklib.reading.converter.ReadingConverter`
classes which offer the conversion of strings from one reading to another.

All basic functionality can be accessed using the
:class:`~cjklib.reading.ReadingFactory` which provides factory methods
for creating instances of the supplied classes and also acts as a façade
for the functions defined there.

Examples
--------
The following examples should give a quick view into how to use this
package.

- Create the ReadingFactory object with default settings
  (read from cjklib.conf or using cjklib.db in module directory as default):

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()

- Create an operator for Mandarin romanisation Pinyin:

    >>> pinyinOp = f.createReadingOperator('Pinyin')

- Construct a Pinyin syllable with second tone:

    >>> pinyinOp.getTonalEntity(u'han', 2)
    u'hán'

- Segments the given Pinyin string into a list of syllables:

    >>> pinyinOp.decompose(u"tiān'ānmén")
    [u'tiān', u''', u'ān', u'mén']

- Do the same using the factory class as a façade to easily access functions
  provided by those classes in the background:

    >>> f.decompose(u"tiān'ānmén", 'Pinyin')
    [u'tiān', u''', u'ān', u'mén']

- Convert the given Gwoyeu Romatzyh syllables to their pronunciation in IPA:

    >>> f.convert('liow shu', 'GR', 'MandarinIPA')
    u'liəu˥˩ ʂu˥˥'

.. index::
   single: romanisation
   pair: character; reading

Readings
--------
Han-characters give only few visual hints about how they are pronounced. The big
number of homophones further increases the problem of deriving the character's
actual pronunciation from the given glyph. This module implements a framework
and desirable functionality to deal with the characteristics of
*character readings*.

From a programmatical view point readings in languages making use of Chinese
characters differ in many ways. Some use the Roman alphabet, some have tonal
information, some can be mapped character-wise, some map from one Chinese
character to a sequence of characters in the target system while some map only
to one character.

One mayor group in the topic of readings are *romanisations*, which are
transcriptions into the Roman alphabet (Cyrillic respectively). Romanisations
of tonal languages are a subgroup that ask for even more detailed functions. The
interface implemented here tries to grasp similar factors on different
abstraction levels while trying to maintain flexibility.

In the context of this library the term *reading* will refer to two things: the
realisation of expressing the pronunciation (e.g. the specific romanisation) on
the one hand, and the specific reading of a given character on the other hand.

Technical implementation
-------------------------
While module :mod:`cjklib.characterlookup` includes the functions for
mapping a character to its potential reading, module :mod:`cjklib.reading`
is specialised on all functionality that is primarily connected to
the reading of characters.

The main functions implemented here provide ways of handling text written in a
reading and converting between different readings.

Handling text written in a reading
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Text written in a *character reading* is special to other text, as it consists
of entities which map to corresponding Chinese characters. They can be deduced
from the text through breaking the whole string down into a sequence of single
entities. This functionality is provided by all operators on readings by
providing the interface :class:`~cjklib.reading.operator.ReadingOperator`.
The process of breaking input down (called decomposition) can be reversed by
composing the single entities to a string.

Many :class:`ReadingOperators <cjklib.reading.operator.ReadingOperator>`
provide additional functions, each depending on the characteristics of
the implemented reading.
For readings of tonal languages for example they might allow to question
the tone of the given reading of a character.

.. inheritance-diagram:: cjklib.reading.operator


Converting between readings
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The second part provided are means to provide support for conversion between
different readings.

What all CJK languages seem to have in common is their irreversibility of the
mapping from a character to its reading, as these languages are rich in
homophones. Thus the highest degree in information for a text is obtained by the
pair of characters and their reading (aside from the meaning).

If one has a text written in reading A and one wants to obtain the text written
in B instead then it is not feasible to obtain the reading from the
corresponding characters even if present, as many characters have several
pronunciations. Instead one wants to convert the reading through conversion from
A to B.

Simple means to convert between readings is provided by classes implementing
:class:`~cjklib.reading.converter.ReadingConverter`. This conversion might
neither be surjective nor injective, and several
:mod:`exceptions <cjklib.exception>` can occur.

.. inheritance-diagram:: cjklib.reading.converter

.. index::
   pair: reading; dialect, dialect; converter

Configurable reading dialect
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Many readings come in specific representations even if standardised. This may
start with simple difference in type setting (e.g. punctuation) or include
special entities and derivatives.

Instead of selecting one default form as a global standard cjklib lets the user
choose the preferred dialect, though still trying to offer good default values.
It does so by offering a wide range of options for handling and conversion of
readings. These options can be given optionally in many places and are handed
down by the system to the component knowing about this specific configuration
option. Furthermore each class implements a method that states which options it
uses by default.

A special notion of *dialect converters* is used for
:class:`~cjklib.reading.converter.ReadingConverter` classes that convert between
two different representations of the same reading. These allow flexible
switching between reading dialects.

Limitations of reading conversion
---------------------------------
While reading conversion allows for flexible handling of any reading, there are
corner cases and limitations that arise from the difference in the readings'
designs.
The following list tries to name limitations for some conversions, it is not
meant to be exhaustive though. The best way to be really sure about what can be
mapped and what not, it to actually try it out. Missing mappings for some
syllables will not be listed here.

- *Jyutping* to *Cantonese Yale*: Jyutping was designed for Cantonese as
  spoken in Hong Kong. While the high falling tone is lost there, it still
  exists in the area of Guangzhou. The first tone of Jyutping will either
  map to the high level tone (default) or the high falling tone.
- *Pinyin* to *Wade-Giles*: Wade-Giles distinguishes between finals *o*
  and *ê* while Pinyin only writes *e* (ê for the syllable itself). A
  mapping is thus ambiguous.
- *GR* to *Pinyin*: GR transcribes *Erhua* sound such that the
  etymological syllable gets lost. A mapping to Pinyin is thus ambiguous.
- *Pinyin* to *GR*: GR transcribes the etymological tone for a fifth tone,
  while Pinyin does not. A mapping cannot fill in the missing information.
- *IPA*: IPA for Mandarin and Cantonese needs to transcribe tonal changes
  and other co-articulation features, which most of the romanisations don't
  cover. A mapping is often either done as approximation, or is not possible
  at all.


Classes
--------

.. autoclass:: ReadingFactory
   :members:
   :undoc-members:
   

