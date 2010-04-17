:mod:`cjklib.dictionary` --- High level dictionary access
=========================================================

.. versionadded:: 0.3

.. automodule:: cjklib.dictionary

This module provides classes for easy access to well known CJK dictionaries.
Queries can be done using a headword, reading or translation.

Dictionary sources yield less structured information compared to other data
sources exposed in this library. Owing to this fact, a flexible system is
provided to the user.

.. inheritance-diagram:: cjklib.dictionary

Examples
--------
Examples how to use this module:

- Create a dictionary instance:

    >>> from cjklib.dictionary import CEDICT
    >>> d = CEDICT()

- Get dictionary entries by reading:

    >>> [e.HeadwordSimplified for e in
    ...     d.getForReading('zhi dao', reading='Pinyin', toneMarkType='numbers')]
    [u'制导', u'执导', u'指导', u'直到', u'直捣', u'知道']

- Change a search strategy (here search for a reading without tones):

    >>> d = CEDICT(readingSearchStrategy=search.SimpleWildcardReading())
    >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
    []
    >>> d = CEDICT(readingSearchStrategy=search.TonelessWildcardReading())
    >>> d.getForReading('nihao', reading='Pinyin', toneMarkType='numbers')
    [EntryTuple(HeadwordTraditional=u'你好', HeadwordSimplified=u'你好', Reading=u'nǐ hǎo', Translation=u'/hello/hi/how are you?/')]

- Apply a formatting strategy to remove all initial and final slashes on
  CEDICT translations:

    >>> from cjklib.dictionary import *
    >>> class TranslationFormatStrategy(format.Base):
    ...     def format(self, string):
    ...         return string.strip('/')
    ...
    >>> d = CEDICT(
    ...     columnFormatStrategies={'Translation': TranslationFormatStrategy()})
    >>> d.getFor(u'东京')
    [EntryTuple(HeadwordTraditional=u'東京', HeadwordSimplified=u'东京', Reading=u'Dōng jīng', Translation=u'Tōkyō, capital of Japan')]

- A simple dictionary lookup tool:

    >>> from cjklib.dictionary import *
    >>> from cjklib.reading import ReadingFactory
    >>> def search(string, reading=None, dictionary='CEDICT'):
    ...     # guess reading dialect
    ...     options = {}
    ...     if reading:
    ...         f = ReadingFactory()
    ...         opClass = f.getReadingOperatorClass(reading)
    ...         if hasattr(opClass, 'guessReadingDialect'):
    ...             options = opClass.guessReadingDialect(string)
    ...     # search
    ...     d = getDictionary(dictionary, entryFactory=entry.UnifiedHeadword())
    ...     result = d.getFor(string, reading=reading, **options)
    ...     # print
    ...     for e in result:
    ...         print e.Headword, e.Reading, e.Translation
    ...
    >>> search('_taijiu', 'Pinyin')
    茅台酒（茅臺酒） máo tái jiǔ /maotai (a Chinese liquor)/CL:杯[bei1],瓶[ping2]/

.. index::
   pair: entry; factory

Entry factories
---------------
Similar to SQL interfaces, entries can be returned in different fashion. An
*entry factory* takes care of preparing the output. For this predefined
factories exist: :class:`cjklib.dictionary.entry.Tuple`, which is very basic,
will return each entry as a tuple of its columns while the mostly used
:class:`cjklib.dictionary.entry.NamedTuple` will return tuple objects
that are accessible by attribute also.

.. index::
   pair: formatting; strategy

Formatting strategies
---------------------
As reading formattings vary and many readings can be converted into each other,
a *formatting strategy* can be applied to return the expected format.
:class:`cjklib.dictionary.format.ReadingConversion` provides an easy way
to convert the reading given by the dictionary into the user defined reading.
Other columns can also be formatted by applying a strategy,
see the example above.

A hybrid approach makes it possible to apply strategies on single cells, giving
a mapping from the cell name to the strategy, or a strategy that operates on the
entire result entry, by giving a mapping from ``None`` to the strategy. In the
latter case the formatting strategy needs to deal with the dictionary specific
entry structure:

    >>> from cjklib.dictionary import *
    >>> d = CEDICT(columnFormatStrategies={
    ...     'Translation': format.TranslationFormatStrategy()})
    >>> d = CEDICT(columnFormatStrategies={
    ...     None: format.NonReadingEntityWhitespace()})

Formatting strategies can be chained together using the
:class:`cjklib.dictionary.format.Chain` class.

.. index::
   pair: search; strategy

Search strategies
-----------------
Searching in natural language data is a difficult process and highly depends on
the use case at hand. This task is provided by *search strategies* which
account for the more complex parts of this module. Strategies exist for the
three main parts of dictionary entries: headword, reading and translation.
Additionally mixed searching for a headword partially expressed by reading
information is supported and can augment the basic reading search. Several
instances of search strategies exist offering basic or more sophisticated
routines. For example wildcard searching is offered on top of many basic
strategies offering by default placeholders ``'_'`` for a single character, and
``'%'`` for a match of zero to many characters.

.. inheritance-diagram:: cjklib.dictionary.search

.. index::
   triple: headword; search; strategy

Headword search strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^
Searching for headwords is the most simple among the three. Exact searches are
provided by class :class:`cjklib.dictionary.search.Exact`. By default class
:class:`cjklib.dictionary.search.Wildcard` is employed which offers
wildcard searches.

.. index::
   triple: reading; search; strategy

Reading search strategies
^^^^^^^^^^^^^^^^^^^^^^^^^
Readings have more complex and unique representations. Several classes are
provided here: :class:`cjklib.dictionary.search.Exact` again can be used
for exact matches, and :class:`cjklib.dictionary.search.Wildcard`
for wildcard searches. :class:`cjklib.dictionary.search.SimpleReading`
and :class:`cjklib.dictionary.search.SimpleWildcardReading` provide
similar searching for transcriptions as found e.g. in CEDICT.
A more complex search is provided by
:class:`cjklib.dictionary.search.TonelessWildcardReading`
which offers search for readings missing tonal information.

.. index::
   triple: translation; search; strategy

Translation search strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A basic search is provided by
:class:`cjklib.dictionary.search.SingleEntryTranslation` which
finds an exact entry in a list of entries separated by slashes ('``/``'). More
flexible searching is provided by
:class:`cjklib.dictionary.search.SimpleTranslation` and
:class:`cjklib.dictionary.search.SimpleWildcardTranslation` which take
into account additional information placed in parantheses.
These classes have even more special implementations adapted to formats
found in dictionaries *CEDICT* and *HanDeDict*.

More complex ones can be implemented on the basis of extending the underlying
table in the database, e.g. using *full text search* capabilities of the
database server. One popular way is using stemming algorithms for copying with
inflections by reducing a word to its root form.

.. index::
   triple: mixed; reading; search
   triple: mixed; search; strategy

Mixed reading search strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Special support for a string with mixed reading and headword entities is
provided by *mixed reading search strategies*. For example ``'dui4 不 qi3'``
will find all entries with headwords whose middle character out of three is
``'不'`` and whose left character is read ``'dui4'`` while the right character is
read ``'qi3'``.

Case insensitivity & Collations
-------------------------------
Case insensitive searching is done through collations in the underlying database
system and for databases without collation support by employing function
``lower()``. A default case independent collation is chosen in the appropriate
build method in :mod:`cjklib.build.builder`.

*SQLite* by default has no Unicode support for string operations. Optionally
the *ICU* library can be compiled in for handling alphabetic non-ASCII
characters. The *DatabaseConnector* can register own Unicode functions if ICU
support is missing. Queries with ``LIKE`` will then use function ``lower()``. This
compatibility mode has a negative impact on performance and as it is not needed
for dictionaries like EDICT or CEDICT it is disabled by default.


Functions
----------

.. autofunction:: getAvailableDictionaries

.. autofunction:: getDictionary

.. autofunction:: getDictionaryClass

.. autofunction:: getDictionaryClasses



Classes
--------

.. autoclass:: BaseDictionary
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: CEDICT
   :show-inheritance:
   :members:
   :undoc-members:
   

   Get dictionary entries with reading IPA:

        >>> from cjklib.dictionary import *
        >>> d = CEDICT(
        ...     readingFormatStrategy=format.ReadingConversion('MandarinIPA'))
        >>> print ', '.join([l['Reading'] for l in d.getForHeadword(u'行')])
        xaŋ˧˥, ɕiŋ˧˥, ɕiŋ˥˩


.. autoclass:: CEDICTGR
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: CFDICT
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: EDICT
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: EDICTStyleDictionary
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: EDICTStyleEnhancedReadingDictionary
   :show-inheritance:
   :members:
   :undoc-members:
   

.. autoclass:: HanDeDict
   :show-inheritance:
   :members:
   :undoc-members:
   
