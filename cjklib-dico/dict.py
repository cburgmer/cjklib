# -*- coding: utf-8 -*-
#
# This file is part of GNU Dico.
# Copyright (C) 2008 Wojciech Polak
# 
# GNU Dico is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Dico is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Dico.  If not, see <http://www.gnu.org/licenses/>.

import dico

import sys

from cjklib.dictionary import *
from cjklib.reading import ReadingFactory

debug = 1

class DicoModule:

    def __init__ (self, *argv):
	if argv:
	    self._dictionaryName = argv[0]

    def open (self, dbname):
        """Open the database."""
        self.dbname = dbname
        if not hasattr(self, '_dictionaryName'):
	    self._dictionaryName = dbname
        try:
            self._dictInst = getDictionary(self._dictionaryName,
		entryFactory=entry.UnifiedHeadword())
        except ValueError, e:
            if debug: print >> sys.stderr, e
            return False

	if self._dictInst.READING:
	    f = ReadingFactory()
	    opClass = f.getReadingOperatorClass(self._dictInst.READING)
	    if hasattr(opClass, 'guessReadingDialect'):
		self._opClass = opClass

        return True

    def close (self):
        """Close the database."""
        return True

    def descr (self):
        """Return a short description of the database."""
        return "DEBUG"

    def info (self):
        """Return a full information about the database."""
        return "DEBUG"

    def lang (self):
        """Optional. Return supported languages (src, dst)."""
        return ("zh", "en")

    def define_word (self, word):
        """Define a word."""
        entries = self._dictInst.getForHeadword(word.decode('utf8'))
        results = ['define']
        for e in entries:
            entry = "%s, %s, %s" % (e.Headword, e.Reading, e.Translation)
            results.append(entry.encode('utf8'))

	options = {}
	if hasattr(self, '_opClass'):
	    options = self._opClass.guessReadingDialect(word.decode('utf8'))
	entries = self._dictInst.getForReading(word.decode('utf8'), **options)
        for e in entries:
            entry = "%s, %s, %s" % (e.Headword, e.Reading, e.Translation)
            results.append(entry.encode('utf8'))
	if len(results) > 1:
	    return results
        return False

    def match_word (self, strat, word):
        """Look up a word in the database."""
        print >> sys.stderr, "MATCH", strat, word
        return "DEBUG"
        return False

    def output (self, rh, n):
        """Output Nth result from the result set."""
        if rh[0] == 'define' :
            print rh[1]
            return True
        else:
            return False

    def result_count (self, rh):
        """Return the number of elements in the result set."""
        if rh[0] == 'define' :
            return 1
        else :
            return 0

    def compare_count (self, rh):
        """Return the number of comparisons performed
        when constructing the result set."""
        return 1

    def result_headers (self, rh, hdr):
        """Optional. Return a dictionary of MIME headers."""
        return hdr

    def free_result (self, rh):
        """Free any resources used by the result set."""
        pass
