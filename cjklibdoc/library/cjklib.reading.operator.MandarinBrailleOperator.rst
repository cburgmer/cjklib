MandarinBrailleOperator --- Braille for Mandarin
================================================

:class:`cjklib.reading.operator.MandarinBrailleOperator` is an
implementation for phonetically transcribing Mandarin using the Braille system.

Specifics
---------

In Braille the fifth tone of Mandarin Chinese is indicated without a tone
mark making a pure entity ambiguous if entities without tonal information
are mixed in. As by default Braille seems to be frequently written omitting
tone marks where unnecessary, the option ``missingToneMark`` controlling the
behaviour of absent tone marking is set to ``'extended'``, allowing the
mixing of entities with fifth and with no tone. If lossless conversion is
needed, this option should be set to ``'fifth'``, forbidding entities
without tonal information.

A small trick to get Braille output into an easily readable form on a normal
screen; do:

    >>> import unicodedata
    >>> input = u'⠅⠡ ⠝⠊ ⠙⠼ ⠊⠁⠓⠫⠰⠂'
    >>> [unicodedata.name(char).replace('BRAILLE PATTERN DOTS-', 'P') \\
    ...     for char in input]
    ['P13', 'P16', 'SPACE', 'P1345', 'P24', 'SPACE', 'P145', 'P3456', 'SPACE', 'P24', 'P1', 'P125', 'P1246', 'P56', 'P2']

.. index::
   pair: Mandarin; Braille

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.MandarinBrailleOperator
   :show-inheritance:
   :members:
   :undoc-members:
