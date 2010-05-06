:mod:`cjklib.characterlookup` --- Chinese character based functions
===================================================================


.. automodule:: cjklib.characterlookup

CharacterLookup
---------------
:class:`CharacterLookup` provides access to lookup methods related to Han
characters.

The real system of CharacterLookup lies in the database beneath where all
relevant data is stored. So for nearly all methods this class needs access
to a database. Thus on initialisation of the object a connection to a
database is established, the logic for this provided by the
:class:`~cjklib.dbconnector.DatabaseConnector`.

See the :class:`DatabaseConnector` for supported database systems.

CharacterLookup will try to read the config file from the user's home folder as
``cjklib.conf`` or ``.cjklib.conf`` or ``/etc/cjklib.conf`` (Unix),
``%APPDATA%/cjklib/cjklib.conf`` (Windows), or
``/Library/Application Support/cjklib/`` and ``$HOME/Library/Application
Support/cjklib/cjklib.conf`` (Mac OS X). If none is present it will try to open
a SQLite database stored as ``cjklib.db`` in the same folder by default. You can
override this behaviour by specifying additional parameters on creation of the
object.

Examples
^^^^^^^^
The following examples should give a quick view into how to use this
package.

- Create the CharacterLookup object with default settings (read from
  ``cjklib.conf`` or ``cjklib.db`` in same directory as default) and set the
  character locale to traditional:

    >>> from cjklib import characterlookup
    >>> cjk = characterlookup.CharacterLookup('T')

- Get a list of characters, that are pronounced "국" in Korean:

    >>> cjk.getCharactersForReading(u'국', 'Hangul')
    [u'匊', u'國', u'局', u'掬', u'菊', u'跼', u'鞠', u'鞫', u'麯', u'麴']

- Check if a character is included in another character as a component:

    >>> cjk.isComponentInCharacter(u'玉', u'宝')
    True

- Get all Kangxi radical variants for Radical 184 (⾷) (under the traditional
  locale):

    >>> cjk.getKangxiRadicalVariantForms(184)
    [u'⻞', u'⻟']


.. index::
   pair: character; locale

Character locale
^^^^^^^^^^^^^^^^
During the development of characters in the different cultures character
appearances changed over time to that extent, that the handling of radicals,
character components and strokes needs to be distinguished, depending on the
locale.

To deal with this circumstance *CharacterLookup* works with a
*character locale*. Most of the methods of this class need a locale context.
In these cases the output of the method depends on the specified locale.

For example in the traditional locale 这 has 8 strokes, but in
simplified Chinese it has only 7, as the radical ⻌ has different stroke
counts, depending on the locale.

.. index:: glyph

Glyphs
^^^^^^
One feature of Chinese characters is the *glyph* form describing the visual
representation. This feature doesn't need to be unique and so many
characters can be found in different writing variants e.g. character 福
(English: luck) which has numerous forms.

The Unicode Consortium does not include same characters of different
actual shape in the Unicode standard (called *Z-variants*), except a few
"double" entries which are included as to maintain backward compatibility.
In fact a code point represents an abstract character not defining any
visual representation. Thus a distinct appearance description including
strokes and stroke order cannot be simply assigned to a code point but one
needs to deal with the notion of *glyphs*, each representing a distinct
appearance to which a visual description can be applied.

Cjklib tries to offer a simple approach to handle different *glyphs*. As
character components, strokes and the stroke order depend on this variant,
methods dealing with this kind will ask for a *glyph* value to be
specified. In these cases the output of the method depends on the specified
shape.

Glyphs and character locales
""""""""""""""""""""""""""""
Varying stroke count, stroke order or decomposition into character
components for different *character locales* is implemented using different
*glyphs*. For the example given above the entry 这 has two glyphs, one with
8 strokes, one with 7 strokes.

In most cases one might only be interested in a single visual appearance,
the "standard" one. This would be the one generally used in the specific
locale.

Instead of specifying a certain glyph most functions will allow for
passing of a character locale. Giving the locale will apply the default
glyph given by the mapping defined in the database which can be obtained
by calling :meth:`~cjklib.characterlookup.CharacterLookup.getDefaultGlyph`.

More complex relations as which of several glyphs for a given character
are used in a given locale are not covered.

.. index::
   pair: equivalent; character
   triple: Unicode; radical; form, Unicode; radical; variant
   triple: isolated; radical; character

Kangxi radical functions
^^^^^^^^^^^^^^^^^^^^^^^^
Using the Unihan database queries about the Kangxi radical of characters can
be made.
It is possible to get a Kangxi radical for a character or lookup all
characters for a given radical.

Unicode has extra code points for radical forms (e.g. ⾔), here called
*Unicode radical forms*, and radical variant forms (e.g. ⻈), here called
*Unicode radical variants*. These characters should be used when explicitly
referring to their function as radicals.
For most of the radicals and variants their exist complementary character
forms which have the same appearance (e.g. 言 and 讠) and which shall be
called *equivalent characters* here.

Mapping from one to another side is not trivially possible, as some forms
only exist as radical forms, some only as character forms, but from their
meaning used in the radical context (called *isolated radical characters*
here, e.g. 訁 for Kangxi radical 149).

Additionally a one to one mapping can't be guaranteed, as some forms have
two or more equivalent forms in another domain, and mapping is highly
dependant on the locale.

CharacterLookup provides methods for dealing with this different kinds of
characters and the mapping between them.

.. index::
   simple: IDS
   pair: character; decomposition
   pair: IDS; operator
   pair: minimal; component
   triple: Ideographic; Description; Sequence
   triple: binary; IDS; operator
   triple: trinary; IDS; operator

Character decomposition
^^^^^^^^^^^^^^^^^^^^^^^
Many characters can be decomposed into two or more components, that again
are Chinese characters. This fact can be used in many ways, including
character lookup, finding patterns for font design or studying characters.
Even the stroke order and stroke count can be deduced from the stroke
information of the character's components.

A character decomposition is depends on the appearance of the
character, a *glyph*, so a *glyph index* needs to be given (will by default be
chosen following the current *character locale*) when looking at a
decomposition into components.

More points render this task more complex: decomposition into one set of
components is not distinct, some characters can be broken down into
different sets. Furthermore sometimes one component can be given, but the
other component will not be encoded as a character in its own right.

These components again might be characters that contain further components
(again not distinct ones), thus a complex decomposition in several steps is
possible.

The basis for the character decomposition lies in the database, where all
decompositions are stored, using *Ideographic Description Sequences*
(*IDS*). These sequences consist of Unicode *IDS operators* and characters
to describe the structure of the character. There are
*binary IDS operators* to describe decomposition into two components (e.g.
⿰ for one component left, one right as in 好: ⿰女子) or
*trinary IDS operators* for decomposition into three components (e.g. ⿲
for three components from left to right as in 辨: ⿲⾟刂⾟). Using
*IDS operators* it is possible to give a basic structural information, that
for example is sufficient in many cases to derive an overall stroke order
from two single sets of stroke orders, namely that of the components.
Further more it is possible to look for redundant information in different
entries and thus helps to keep the definition data clean.

This class provides methods for retrieving the basic partition entries,
lookup of characters by components and decomposing as a tree from the
character as a root down to the *minimal components* as leaf nodes.

.. seealso::

   `Character decomposition guidelines <http://code.google.com/p/cjklib/wiki/Decomposition>`_
      Discussion on the project's wiki.

.. index::
   pair: stroke; count, stroke; order

Strokes
^^^^^^^
Chinese characters consist of different strokes as basic parts. These
strokes are written in a mostly distinct order called the *stroke order*
and have a distinct *stroke count*.

The *stroke order* in the writing of Chinese characters is important e.g.
for calligraphy or students learning new characters and is normally fixed as
there is only one possible stroke order for each character. Further more
there is a fixed set of possible strokes and these strokes carry names.

As with *character decomposition* the *stroke order* and *stroke count*
depends on the actual rendering of the character, the *glyph*. If no
specific glyph is specified, it will be deduced from the current
*character locale*.

The set of strokes as defined by Unicode in block 31C0-31EF is supported.
Simplifying subsets might be supported in the future.

TODO: About the different classifications of strokes

.. index::
   pair: stroke; name
   triple: abbreviated; stroke; name

Stroke names and abbreviated names
""""""""""""""""""""""""""""""""""
Additionally to the encoded stroke forms, *stroke names* and
*abbreviated stroke names* can be used to conveniently refer to strokes.
Currently supported are Mandarin names (following Unicode), and
*abbreviated stroke names* are built by taking the first character of the
*Pinyin* spelling of each syllable, e.g. ``HZZZG`` for ``橫折折折鉤`` (i.e.
``㇡``, U+31E1).

Inconsistencies
"""""""""""""""
The *stroke order* of some characters is disputed in academic fields. A
current workaround would be adding another glyph definition, showing the
alternative order.

TODO: About plans of cjklib how to support different views on the stroke
order

Readings
^^^^^^^^
See module :mod:`cjklib.reading` for a detailed introduction into
*character readings*.

:class:`CharacterLookup` provides to methods for accessing character readings:
:meth:`CharacterLookup.getReadingForCharacter` will return all readings known
for the given character. :meth:`CharacterLookup.getCharactersForReading` will
return all characters known to have the given reading.

The database offers mappings for the following readings:

* :doc:`Hanyu Pinyin <cjklib.reading.operator.PinyinOperator>`
* :doc:`Jyutping <cjklib.reading.operator.JyutpingOperator>`
* :doc:`IPA for Shanghainese <cjklib.reading.operator.ShanghaineseIPAOperator>`
* :doc:`Hangul <cjklib.reading.operator.HangulOperator>`

Most other readings are available by using one of the above readings as
:ref:`bridge <readingbridge-label>`.

.. index::
   pair: character; domain

Character domains
^^^^^^^^^^^^^^^^^
Unicode encodes Chinese characters for all languages that make use of them,
but neither of those writing system make use of the whole spectrum encoded.
While it is difficult, if not impossible, to make a clear distinction which
characters are used in on system and which not, there exist authorative
character sets that are widely used. Following one of those character sets
can decrease the amount of characters in question and focus on those
actually used in the given context.

In cjklib this concept is implemented as *character domain* and if a
:class:`~cjklib.characterlookup.CharacterLookup` instance is given a
*character domain*, then its reported results are limited to the
characters therein.

For example limit results to the character encoding BIG5, which encodes
traditional Chinese characters:

    >>> from cjklib import characterlookup
    >>> cjk = characterlookup.CharacterLookup('T', 'BIG5')

Available *character domains* can be checked via
:meth:`~cjklib.characterlookup.CharacterLookup.getAvailableCharacterDomains`.
Special character domain ``Unicode`` represents the whole set of
Chinese characters encoded in Unicode.

.. seealso::

   `Radicals <http://en.wikipedia.org/wiki/Radical_(Chinese_character)>`_
       Wikipedia on radicals.

   `Z-variants <http://www.unicode.org/reports/tr38/tr38-5.html#N10211>`_
      Unicode Standard Annex #38, Unicode Han Database (Unihan), 3.7 Variants

.. index::
   pair: surrogate; pair
   pair: narrow; build
   simple: BMP
   triple: Basic; Multilingual; Plane

Surrogate pairs
^^^^^^^^^^^^^^^
Python supports UCS-2 and UCS-4 for Unicode strings. The former is a 2-byte
implementation called `narrow build`, while the latter uses 4 bytes to store
Unicode characters and is called a `wide build` respectively. The latter can
directly store any character encoded by Unicode, while UCS-2 only supports
the 16-bit range called the `Basic Multilingual Plane` (`BMP`). By default
Python is compiled with UCS-2 support only and some versions, e.g. the one for
Windows, have no publicly available version supporting UCS-4.

To circumvent the fact of only being able to represent the first 65536
codepoints of Unicode Python `narrow builds` support `surrogate pairs` as
found in UTF-16 to represent characters above the 0xFFFF codepoint. Here a
logical character from a codepoint above 0xFFFF is represented by two
physical characters. The most significant surrogate lies between 0xD800
and 0xDBFF while the least significant surrogate lies between 0xDC00
and 0xDFFF. Cjklib supports `surrogate pairs` and will return a string of
length 2 for characters outside the BMP for `narrow builds`. Users need
to notice that the assertion ``len(char) == 1`` doesn't hold here anymore.

.. seealso::

   `PEP 261 <http://www.python.org/dev/peps/pep-0261/>`_
      Support for "wide" Unicode characters

   `Encoding of characters outside the BMP <http://en.wikipedia.org/wiki/UTF-16/UCS-2#Encoding_of_characters_outside_the_BMP>`_
      Wikipedia on UTF16/UCS-2.

Classes
-------

.. currentmodule:: cjklib.characterlookup

.. autoclass:: CharacterLookup
   :show-inheritance:
   :members:
   :undoc-members:
   



