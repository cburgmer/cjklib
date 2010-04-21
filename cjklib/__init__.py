# -*- coding: utf-8 -*-
# This file is part of cjklib.
#
# cjklib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cjklib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cjklib.  If not, see <http://www.gnu.org/licenses/>.

u"""
Han character library. Cjklib provides language routines related to Han
characters (characters based on Chinese characters named Hanzi, Kanji, Hanja and
chu Han respectively) used in writing of the Chinese, the Japanese, infrequently
the Korean and formerly the Vietnamese language(s). Functionality is included
for character pronunciations, radicals, glyph components, stroke decomposition,
variant information and dictionary access.

Examples
========
    - Get characters by pronunciation (here: "국" in Korean):

        >>> from cjklib import characterlookup
        >>> cjk = characterlookup.CharacterLookup('T')
        >>> cjk.getCharactersForReading(u'국', 'Hangul')
        [u'匊', u'國', u'局', u'掬', u'菊', u'跼', u'鞠', u'鞫', u'麯', u'麴']

    - Get characters by components (yielding glyphs):

        >>> cjk.getCharactersForComponents([u'门', u'⼉'])
        [(u'\u9605', 0), (u'\u960b', 0)]

    - Get stroke order of characters:

        >>> cjk.getStrokeOrder(u'说')
        [u'\u31d4', u'\u31ca', u'\u31d4', u'\u31d2', u'\u31d1', u'\u31d5', \
u'\u31d0', u'\u31d3', u'\u31df']

    - Convert pronunciation data (here from *Pinyin* to *IPA*):

        >>> from cjklib.reading import ReadingFactory
        >>> f = ReadingFactory()
        >>> f.convert(u'l\u01ceosh\u012b', 'Pinyin', 'MandarinIPA')
        u'lau\u02e8\u02e9.\u0282\u0285\u02e5\u02e5'

    - Access a dictionary (here using Jim Breen's EDICT):

        >>> from cjklib.dictionary import EDICT
        >>> d = EDICT()
        >>> d.getForTranslation('Tokyo')
        [EntryTuple(Headword=u'\u6771\u4eac',\
 Reading=u'\u3068\u3046\u304d\u3087\u3046', Translation=u'/(n) Tokyo (current\
 capital of Japan)/(P)/')]

Copyright
=========

Copyright (C) 2006-2010 cjklib developers

cjklib comes with absolutely no warranty; for details see B{License}.

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
"""
__version__ = '0.3'
"""The version of cjklib"""

__author__ = 'Christoph Burgmer <cburgmer@ira.uka.de>'
"""The primary author of cjklib"""

__url__ = 'http://cjklib.org'
"""The URL for cjklib's homepage"""

__license__ = 'LGPL'
"""The license governing the use and distribution of cjklib"""
