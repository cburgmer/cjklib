#!/usr/bin/python
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

"""
Checks the HanRadicalFolding.txt table from Unicode against the cjklib database.

It will print out entries from the table not included in the database and
entries from the database not included in the Unicode table:

    cat HanRadicalFolding.txt | python checkhanradicalfolding.py

2008 Christoph Burgmer (cburgmer@ira.uka.de)
"""
import re
import locale
import sys

from sqlalchemy import select

from cjklib import dbconnector
from cjklib import exception

# get local language and output encoding
language, default_encoding = locale.getdefaultlocale()

def main():
    # get cjklib database table
    databaseTable = {}
    db = dbconnector.getDBConnector()
    table = db.tables['RadicalEquivalentCharacter']
    entries = db.selectRows(
        select([table.c.Form, table.c.EquivalentForm, table.c.Locale]))
    for radicalForm, equivalentForm, locale in entries:
        databaseTable[(radicalForm, equivalentForm)] = locale

    fileEntryCount = 0
    one2oneEntryCount = 0
    noEntryCount = 0
    narrowLocaleCount = 0
    for line in sys.stdin:
        line = line.decode(default_encoding)

        if re.match(r'\s*#', line) or re.match(r'\s+$', line):
            continue
        else:
            fileEntryCount = fileEntryCount + 1

            matchObj = re.match(
                r'([1234567890ABCDEF]{4});\s+([1234567890ABCDEF]{4,5})\s+#',
                line)
            if matchObj:
                radicalForm = unichr(int(matchObj.group(1), 16))
                equivalentForm = unichr(int(matchObj.group(2), 16))
                if (radicalForm, equivalentForm) in databaseTable:
                    # entry included in database
                    if databaseTable[(radicalForm, equivalentForm)] != 'TCJKV':
                        # locale of entry is narrower, i.e. subset of TCJKV
                        print ("Narrowed locale for '" + radicalForm \
                            + "' (" + matchObj.group(1).lower() + "), '" \
                            + equivalentForm + "' (" \
                            + matchObj.group(2).lower() + "), locale " \
                            + databaseTable[(radicalForm, equivalentForm)])\
                            .encode(default_encoding)
                        narrowLocaleCount = narrowLocaleCount + 1
                    else:
                        one2oneEntryCount = one2oneEntryCount + 1
                    del databaseTable[(radicalForm, equivalentForm)]
                else:
                    print ("No entry for '" + radicalForm \
                        + "' (" + matchObj.group(1).lower() + "), '" \
                        + equivalentForm + "' (" + matchObj.group(2).lower() \
                        + ")").encode(default_encoding)
                    noEntryCount = noEntryCount + 1
            else:
                print ("error reading line: '" + line + "'")\
                    .encode(default_encoding)

    # database entries not included in table
    for radicalForm, equivalentForm in databaseTable:
        print ("Database entry not included in table: '" + radicalForm \
            + "' (" + hex(ord(radicalForm)).replace('0x', '') + "), '" \
            + equivalentForm + "' (" \
            + hex(ord(equivalentForm)).replace('0x', '') +"), locale " \
            + databaseTable[(radicalForm, equivalentForm)])\
            .encode(default_encoding)

    print "Total " + str(fileEntryCount) + " entries, " \
        + str(one2oneEntryCount) + " fully included in database, " \
        + str(noEntryCount) + " without entry, " \
        + str(narrowLocaleCount) + " with narrowed locale"

if __name__ == "__main__":
    main()

