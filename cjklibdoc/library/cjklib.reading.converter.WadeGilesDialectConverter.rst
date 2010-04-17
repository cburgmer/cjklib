WadeGilesDialectConverter --- Wade-Giles dialects
=================================================

Specifics
---------

Examples
^^^^^^^^
Convert to superscript numbers (default):
    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert(u'Ssŭ1ma3 Ch’ien1', 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'toneMarkType': 'numbers'})
    u'Ss\u016d\xb9-ma\xb3 Ch\u2019ien\xb9'

Convert form without diacritic to standard form:
    >>> f.convert(u'ch’eng', 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'diacriticE': 'e'})
    u'ch\u2019\xeang'

Convert forms with lost umlaut:
    >>> f.convert(u'hsu³-hun¹', 'WadeGiles', 'WadeGiles',
    ...     sourceOptions={'umlautU': 'u'})
    u'hs\xfc\xb3-hun\xb9'

See :class:`~cjklib.reading.operator.WadeGilesOperator` for more examples.

Class
-----

.. currentmodule:: cjklib.reading.converter

.. autoclass:: cjklib.reading.converter.WadeGilesDialectConverter
   :show-inheritance:
   :members:
   :undoc-members:
