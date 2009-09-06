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
for character pronunciations, radicals, glyph components, stroke decomposition
and variant information.

Supported
=========
The following functions are supported by this library:
    - Character readings (pronunciation):
        - Pinyin, Gwoyeu Romatzyh, Wade-Giles, IPA, Braille (all Mandarin)
        - Jyutping, Cantonese Yale (both Cantonese)
        - Hangul (Korean)
        - Hiragana, Katakana (Japanese)
    - Conversion of readings from one into another
    - Mapping between character and reading
    - Mapping between character and Kangxi radical (radical mapping as defined
        by the Unihan database)
    - Mapping between character and multiple radical forms
    - Mapping between character and stroke sequence
    - Mapping between character and stroke count
    - Mapping between Kangxi radical forms, radical variant forms and equivalent
        characters
    - Character variant lookup (including mapping from traditional to Chinese
        simplified forms)

Tools
=====
The following tools come with this library:
    - cjknife, provides most functions from the library on the command line.
    - buildcjkdb, builds the database from source files.

Data
====
The library comes with its own set of sources on:
    - Pinyin syllables
    - Gwoyeu Romatzyh syllables including rhotacised forms and abbreviations
    - Wade-Giles syllables
    - Jyutping syllables
    - Cantonese Yale syllables
    - Pinyin to Gwoyeu Romatzyh mapping
    - Wade-Giles to Pinyin mapping
    - Pinyin to IPA mapping
    - Pinyin to Braille mapping
    - Jyutping to Cantonese Yale mapping
    - Jyutping to IPA mapping
    - mapping of Mandarin syllables to onset and rhyme
    - mapping of Cantonese syllables to onset and rhyme
    - Kangxi radical forms
    - stroke count and stroke order
    - stroke names
    - character decomposition

See the data files for comparison with other sources.

This project makes use of the X{Unicode Han database} provided by the Unicode
Consortium: Unicode Standard Annex #38 - Unicode Han database (X{Unihan}):
U{http://www.unicode.org/reports/tr38/tr38-5.html}, 28E{.}03E{.}2008E{.}

The following data is used:
    - Character Kangxi radical information (from kRSKangxi)
    - Radical residual stroke count (from kRSKangxi) and total stroke count
        (from KTotalStrokes)
    - Mandarin character readings in Pinyin (from kMandarin, kHanyuPinlu,
        kXHC1983, kHanyuPinyin)
    - Cantonese character readings in Jyutping (from kCantonese)
    - Korean character readings in Hangul (from kHangul)
    - Character variant forms (from kCompatibilityVariant, kSemanticVariant,
        kSimplifiedVariant, kSpecializedSemanticVariant, kTraditionalVariant,
        kZVariant)

This includes dictionary data from:
    - kXHC1983:  Xiàndài Hànyǔ Cídiǎn (现代汉语词典). Shāngwù Yìnshūguǎn, Beijing,
        1983.
    - kHanyuPinlu: Xiàndài Hànyǔ Pínlǜ Cídiǎn (現代漢語頻率詞典).
        北京語言學院語言教學研究所編著, First edition 1986/6, 2nd printing 1990/4,
        ISBN 7-5619-0094-5.
    - kHanyuPinyin: Hànyǔ Dà Zìdiǎn (漢語大字典).
        許力以主任，徐中舒主編，（漢語大字典工作委員會）。
        武漢：四川辭書出版社，湖北辭書出版社, 1986-1990. ISBN: 7-5403-0030-2/H.16.

Dependencies
============
cjklib is written in Python and is well tested on Python 2.5 and 2.6.
Apart from this dependency it needs a database back-end for most of its parts
and library SQLAlchemy.
Currently tested are:
    - SQLite, tested on SQLite 3
    - MySQL, tested on MySQL 5.1 (works only with characters from the Basic
        Multilingual Plane in Unicode, BMP)

@author: Christoph Burgmer <cburgmer@ira.uka.de>
@requires: Python 2.5+, SQLAlchemy 0.5+ and either SQLite 3+ or MySQL 5+ and
    MySQL-Python
@version: 0.1alpha

@copyright: Copyright (C) 2006-2009 Christoph Burgmer

    cjklib comes with absolutely no warranty; for details see B{License}.

    Parts of the data used by this library have their own copyright:
        - Copyright © 1991-2007 Unicode, Inc. All rights reserved. Distributed
            under the Terms of Use in U{http://www.unicode.org/copyright.html}.

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

@license: The library and all parts are distributed under the terms of the LGPL
Version 3, 29 June 2007 (U{http://www.gnu.org/licenses/lgpl.html}) if not
otherwise noted.
"""
__version__ = '0.1alpha'
"""The version of cjklib"""

__author__ = 'Christoph Burgmer <cburgmer@ira.uka.de>'
"""The primary author of cjklib"""

__url__ = 'http://code.google.com/p/cjklib/'
"""The URL for cjklib's homepage"""

__license__ = 'LGPL'
"""The license governing the use and distribution of cjklib"""
