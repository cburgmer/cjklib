JyutpingYaleConverter -- Jyutping to Cantonese Yale
===================================================

Specifics
---------

Upper- or lowercase will be transfered between syllables, no special
formatting according to anyhow defined standards will be guaranteed.
Upper-/lowercase will be identified according to three classes: either the
whole syllable is uppercase, only the initial letter is uppercase
(titlecase) or otherwise the whole syllable is assumed being lowercase. For
entities of single latin characters uppercase has precedence over titlecase,
e.g. *E5* will convert to *ÉH* in Cantonese Yale, not to *Éh*.

High Level vs. High Falling Tone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As described in :class:`~cjklib.reading.operator.CantoneseYaleOperator` the
Cantonese Yale romanisation system makes a distinction between the
high level tone and the high falling tone in general while Jyutping does not.
On conversion it is thus important to choose the correct mapping.
This can be configured by applying the option
``yaleFirstTone`` when construction the converter (or telling the
:class:`~cjklib.reading.ReadingFactory` which converter to use).

Example:

    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert(u'gwong2zau1waa2', 'Jyutping', 'CantoneseYale',
    ...     yaleFirstTone='1stToneFalling')
    u'gwóngjàuwá'

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.JyutpingYaleConverter
   :show-inheritance:
   :members:
   :undoc-members:
