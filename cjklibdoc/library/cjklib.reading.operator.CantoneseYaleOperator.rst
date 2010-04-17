CantoneseYaleOperator --- Cantonese Yale
========================================

:class:`cjklib.reading.operator.CantoneseYaleOperator` is a mature
implementation of the Yale transcription for Cantonese. It's one of the major
romanisations used for Cantonese and frequently found in education.

Features:

- tones marked by either diacritics or numbers,
- choice between high level and high falling tone for number marks,
- guessing of input form (reading dialect) and
- splitting of syllables into onset, nucleus and coda.

Specifics
---------

High Level vs. High Falling Tone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Yale distinguishes two tones often subsumed under one: the high level tone
with tone contour 55 as given in the commonly used pitch model by Yuen Ren
Chao and the high falling tone given as pitch 53 (as by Chao), 52 or 51
(Bauer and Benedikt, chapter 2.1.1 pp. 115).
Many sources state that these two tones aren't distinguishable anymore in
modern Hong Kong Cantonese and thus are subsumed under one tone in some
romanisation systems for Cantonese.

In the abbreviated form of the Yale romanisation that uses numbers to
represent tones this distinction is not made. The mapping of the tone number
``1`` to either the high level or the high falling tone can be given by the
user and is important when conversion is done involving this abbreviated
form of the Yale romanisation. By default the high level tone will be used
as this primary use is indicated in the given sources.

Placement of tones
^^^^^^^^^^^^^^^^^^
Tone marks, if using the standard form with diacritics, are placed according
to Cantonese Yale rules (see
:meth:`~cjklib.reading.operator.CantoneseYaleOperator.getTonalEntity`).
The CantoneseYaleOperator by default tries to work around misplaced
tone marks though to ease handling of malformed input.
There are cases, where this generous behaviour leads to
a different segmentation compared to the strict interpretation. No means are
implemented to disambiguate between both solutions. The general behaviour is
controlled with option ``'strictDiacriticPlacement'``.

Sources
^^^^^^^
- Stephen Matthews, Virginia Yip: Cantonese: A Comprehensive Grammar.
  Routledge, 1994, ISBN 0-415-08945-X.
- Robert S. Bauer, Paul K. Benedikt: Modern Cantonese Phonology
  (摩登廣州話語音學). Walter de Gruyter, 1997, ISBN 3-11-014893-5.

.. seealso::

   `Cantonese: A Comprehensive Grammar <http://books.google.de/books?id=czbGJLu59S0C>`_
      Preview on Google Books.

   `Modern Cantonese Phonology <http://books.google.de/books?id=QWNj5Yj6_CgC>`_
      Preview on Google Books.

.. index::
   pair: Cantonese; Yale

Class
-----

.. currentmodule:: cjklib.reading.operator

.. autoclass:: cjklib.reading.operator.CantoneseYaleOperator
   :show-inheritance:
   :members:
   :undoc-members:
