================================
cjklib --- Han character library
================================

Cjklib provides language routines related to Han characters (characters based
on Chinese characters named Hanzi, Kanji, Hanja and chu Han respectively) used
in writing of the Chinese, the Japanese, infrequently the Korean and formerly
the Vietnamese language(s). Functionality is included for character
pronunciations, radicals, glyph components, stroke decomposition and variant
information.

This document is about version |version|, see http://cjklib.org/ for the newest
and http://cjklib.org/current for the current development version. The project
is hosted on http://code.google.com/p/cjklib. See http://characterdb.cjklib.org/
for a collaborative effort on gathering language data for cjklib.

Contents:

.. toctree::
   :maxdepth: 2

   installing.rst
   cli.rst
   library.rst
   todo.rst


Examples
========

Get characters by pronunciation (here: "국" in Korean):
    >>> from cjklib import characterlookup
    >>> cjk = characterlookup.CharacterLookup('T')
    >>> cjk.getCharactersForReading(u'국', 'Hangul')
    [u'匊', u'國', u'局', u'掬', u'菊', u'跼', u'鞠', u'鞫', u'麯', u'麴']

Get stroke order of characters:
    >>> cjk.getStrokeOrder(u'说')
    [u'㇔', u'㇊', u'㇔', u'㇒', u'㇑', u'㇕', u'㇐', u'㇓', u'㇟']

Convert pronunciation data (here from *Pinyin* to *IPA*):
    >>> from cjklib.reading import ReadingFactory
    >>> f = ReadingFactory()
    >>> f.convert(u'lǎoshī', 'Pinyin', 'MandarinIPA')
    u'lau˨˩.ʂʅ˥˥'

Access a dictionary (here using Jim Breen's EDICT):
    >>> from cjklib.dictionary import EDICT
    >>> d = EDICT()
    >>> d.getForTranslation('Tokyo')
    [EntryTuple(Headword=u'東京', Reading=u'とうきょう', Translation=u'/(n) Tokyo (current capital of Japan)/(P)/')]


Copyright & License
===================

Copyright (C) 2006-2010 cjklib developers

cjklib comes with absolutely no warranty; for details see License.

Parts of the data used by this library have their own copyright:

- Copyright © 1991-2009 Unicode, Inc. All rights reserved. Distributed
  under the Terms of Use in http://www.unicode.org/copyright.html.

  Permission is hereby granted, free of charge, to any person
  obtaining a copy of the Unicode data files and any associated
  documentation (the "Data Files") or Unicode software and any
  associated documentation (the "Software") to deal in the Data Files
  or Software without restriction, including without limitation the
  rights to use, copy, modify, merge, publish, distribute, and/or sell
  copies of the Data Files or Software, and to permit persons to whom
  the Data Files or Software are furnished to do so, provided that (a)
  the above copyright notice(s) and this permission notice appear with
  all copies of the Data Files or Software, (b) both the above
  copyright notice(s) and this permission notice appear in associated
  documentation, and (c) there is clear notice in each modified Data
  File or in the Software as well as in the documentation associated
  with the Data File(s) or Software that the data or software has been
  modified.
- Decomposition data Copyright 2009 by Gavin Grover
- Shanghainese pronunciation data Copyright 2010 by Kellen Parker and
  Allan Simon, http://www.sinoglot.com/wu/tools/data/.

The library and all parts are distributed under the terms of the LGPL
Version 3, 29 June 2007 (http://www.gnu.org/licenses/lgpl.html) if not
otherwise noted.


Contact
=======
For help or discussions on cjklib, join `cjklib-devel@googlegroups.com
<http://groups.google.com/group/cjklib-devel>`_.

Please report bugs to the `project's bug tracker
<http://code.google.com/p/cjklib/issues/list>`_.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

