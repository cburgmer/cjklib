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
Checks the CJKRadicals.txt table from Unicode against the cjklib database.

It will print out entries from the table not included in the database and
entries from the database not included in the Unicode table:

    cat CJKRadicals.txt | python checkhanradicalfolding.py

2009 Christoph Burgmer (cburgmer@ira.uka.de)
"""
import re
import locale
import sys

from cjklib.characterlookup import CharacterLookup

# get local language and output encoding
language, default_encoding = locale.getdefaultlocale()

def main():
    cjk = CharacterLookup('T')
    cjkSimplified = CharacterLookup('C')

    fileEntryCount = 0
    databaseMissingEntryCount = 0
    noEntryCount = 0
    wrongEquivalentCount = 0
    seenRadicalFormIndices = set()
    seenRadicalVariantIndices = set()
    for line in sys.stdin:
        line = line.decode(default_encoding)

        if re.match(r'\s*#', line) or re.match(r'\s+$', line):
            continue
        else:
            fileEntryCount = fileEntryCount + 1

            matchObj = re.match(r"(\d{1,3})('?);\s+([1234567890ABCDEF]{4,5});" \
                + r"\s+([1234567890ABCDEF]{4,5})\s*$", line)
            if matchObj:
                index, variant, radicalCP, equivalentCP = matchObj.groups()
                radicalIdx = int(index)
                radicalForm = unichr(int(radicalCP, 16))
                equivalentForm = unichr(int(equivalentCP, 16))

                if variant:
                    seenRadicalVariantIndices.add(radicalIdx)
                else:
                    seenRadicalFormIndices.add(radicalIdx)
                # check radicalForm
                if not variant:
                    targetForms = set([cjk.getKangxiRadicalForm(radicalIdx)])
                else:
                    targetForms = set()
                    # add simplified form, if different
                    simplifiedForm = cjkSimplified.getKangxiRadicalForm(
                        radicalIdx)
                    if simplifiedForm != cjk.getKangxiRadicalForm(radicalIdx):
                        targetForms.add(simplifiedForm)
                    # add simplified variant
                    targetForms.update(
                        set(cjkSimplified.getKangxiRadicalVariantForms(
                            radicalIdx)) \
                        - set(cjk.getKangxiRadicalVariantForms(radicalIdx)))

                if radicalForm not in targetForms:
                    # cjklib is missing something
                    print ("No entry for radical form '%s' with index %d%s"
                        % (radicalForm, radicalIdx, variant))\
                        .encode(default_encoding)
                    databaseMissingEntryCount += 1
                if targetForms - set([radicalForm]):
                    # CJKRadicals.txt is missing something
                    for form in targetForms - set([radicalForm]):
                        print ("Database entry '%s' with radical index %d%s" \
                            % (form, radicalIdx, variant) \
                            + " not included in table")\
                            .encode(default_encoding)
                    noEntryCount += 1

                # check equivalentForm
                libraryEquivalentForm \
                    = cjk.getRadicalFormEquivalentCharacter(radicalForm)
                if libraryEquivalentForm != equivalentForm:
                    print ("Equivalent radical form '%s' with index %d%s"
                        % (libraryEquivalentForm, radicalIdx, variant) \
                        + " not backed by table: '%s'" % equivalentForm)\
                        .encode(default_encoding)
                    wrongEquivalentCount += 1

            else:
                print ("error reading line: '" + line + "'")\
                    .encode(default_encoding)


    for radicalIdx in set(range(1, 215)) - seenRadicalFormIndices:
        print ("No table entry for radical index %d" % radicalIdx)\
            .encode(default_encoding)
        noEntryCount += 1

    for radicalIdx in set(range(1, 215)) - seenRadicalVariantIndices:
        simplifiedForms = set()
        # add simplified form, if different
        simplifiedForm = cjkSimplified.getKangxiRadicalForm(
            radicalIdx)
        if simplifiedForm != cjk.getKangxiRadicalForm(radicalIdx):
            simplifiedForms.add(simplifiedForm)
        # add simplified variant
        simplifiedForms.update(
            set(cjkSimplified.getKangxiRadicalVariantForms(
                radicalIdx)) \
            - set(cjk.getKangxiRadicalVariantForms(radicalIdx)))
        for form in simplifiedForms:
            print ("No table entry for simplified radical %s with index %d'"
                % (form, radicalIdx)).encode(default_encoding)
            noEntryCount += 1

    for radicalIdx in range(1, 215):
        otherVariants = set(cjk.getKangxiRadicalVariantForms(radicalIdx)) \
            - set(cjkSimplified.getKangxiRadicalVariantForms(radicalIdx))
        for form in otherVariants:
            print ("No table entry for variant %s with index %d'"
                % (form, radicalIdx)).encode(default_encoding)
            noEntryCount += 1

    print "Total %d entries" % fileEntryCount \
        + ", %d missing from cjklib" % databaseMissingEntryCount \
        + ", %d mismatches in equivalent forms" % wrongEquivalentCount \
        + ", not found in source list: %d" % noEntryCount


if __name__ == "__main__":
    main()
