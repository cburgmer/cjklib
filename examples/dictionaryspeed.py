#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Gives timing statistics for dictionary access methods.

Checks timing for SQLite backend under the following conditions::

    Run | Own Unicode function | NOCASE | INDEX ON
    --------------------------------------------------
    1   |          -           |   -    | plain column
    2   |          -           |   X    | plain column
    3   |          -           |   X    | on NOCASE
    4   |          X           |   X    | plain column
    5   |          X           |   X    | on NOCASE

This tests can be run separately for ICU support compiled into SQLite and the
default version without.

Create the four databases:
    - For run 1:

        buildcjkdb -r build EDICT CEDICT CEDICTGR HanDeDict CFDICT\
 --database=sqlite:///plain.db --useCollation=False --registerUnicode=False

    - For runs 2 and 4:

        buildcjkdb -r build EDICT CEDICT CEDICTGR HanDeDict CFDICT\
 --database=sqlite:///nocase.db --useCollation=True --registerUnicode=False

    - For runs 3:

        cp /tmp/nocase.db /tmp/nocaseindex.db
        python examples/dictionaryspeed.py reindex nocaseindex.db

    - For run 5:

        cp /tmp/nocase.db /tmp/unicodeindex.db
        python examples/dictionaryspeed.py reindex unicodeindex.db\
 --registerUnicode

    - compact files:

        sqlite3 plain.db "VACUUM;"
        sqlite3 nocase.db "VACUUM;"
        sqlite3 nocaseindex.db "VACUUM;"
        sqlite3 unicodeindex.db "VACUUM;"

2010 Christoph Burgmer (cburgmer@ira.uka.de)

License: MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import imp
import sys
from timeit import Timer
from optparse import OptionParser, OptionGroup, Values

from sqlalchemy.sql import text
from sqlalchemy.exc import OperationalError

import cjklib
from cjklib import dictionary
from cjklib.reading import ReadingFactory
from cjklib import dbconnector

# Several example search requests, spanning headwords, readings and translations
SEARCH_REQUESTS = ['Beijing', '%Beijing%', 'Bei3jing1', 'Tokyo', 'Tiananmen',
                   'to run', 'dui_qi', u'南京', u'TÜTE', u'とうきょう', u'%國hua',
                   'zhishi', 'knowledge']

def runRequest(dictInstance, requestList, method='getFor'):
    for request, options in requestList:
        getattr(dictInstance, method)(request, **options)

def runTests(tests, databases, registerUnicode, iteration=10):
    f = ReadingFactory()

    timing = {}
    for no in tests:
        print "Running test %d (reading from %s)..." % (no, databases[no])

        connection = {'sqlalchemy.url': 'sqlite:///%s' % databases[no],
                      'attach': ['cjklib'],
                      'registerUnicode': registerUnicode[no]}
        db = dbconnector.getDBConnector(connection)
        availableDicts = [dictClass.DICTIONARY_TABLE for dictClass
                          in dictionary.BaseDictionary\
                             .getAvailableDictionaries(db)]
        dictionaries = list(set(availableDicts)
                            & set(db.engine.table_names(schema=db._mainSchema)))
        if not dictionaries:
            raise ValueError("No dictionaries found")

        print "Found dictionaries '%s'" % "', '".join(dictionaries)

        runTime = {}
        for dictName in dictionaries:
            dictClass = dictionary.BaseDictionary.getDictionaryClass(dictName)
            dictInstance = dictClass(dbConnectInst=db)

            opClass = (dictClass.READING
                       and f.getReadingOperatorClass(dictClass.READING))
            if hasattr(opClass, 'guessReadingDialect'):
                requestList = []
                for request in SEARCH_REQUESTS:
                    options = opClass.guessReadingDialect(request)
                    requestList.append((request, options))
            else:
                requestList = [(request, {}) for request in SEARCH_REQUESTS]

            mod = imp.new_module('timeit_runmod')
            mod.runRequest = runRequest
            mod.dictInstance = dictInstance
            mod.requestList = requestList

            sys.modules['timeit_runmod'] = mod

            methodTime = {}
            for method in ('getFor', 'getForHeadword', 'getForReading',
                           'getForTranslation'):
                t = Timer("""timeit_runmod.runRequest(
                                timeit_runmod.dictInstance,
                                timeit_runmod.requestList,
                                method='%s')
                          """ % method,
                          "import timeit_runmod")
                methodTime[method] = t.timeit(iteration)
            runTime[dictName] = methodTime

        timing[no] = runTime

    return timing

def printResults(timing):
    # check that all results use the same dictionaries
    assert timing and all((timing.values()[0].keys() == runTime.keys())
                          for runTime in timing.values())

    methods = sorted(timing.values()[0].values()[0].keys())
    # check that all used methods are the same
    assert timing and all(all((methods == sorted(methodTime.keys()))
                              for methodTime in runTime.values())
                          for runTime in timing.values())

    print '   ' + '\t'.join(methods)
    for testNo in sorted(timing.keys()):
        runTime = timing[testNo]

        results = []
        for method in methods:
            results.append(sum(methodTime[method]
                               for methodTime in runTime.values()))

        print "%d: %s" % (testNo, '\t'.join(("%f" % t) for t in results))

def buildParser():
    usage = "%prog [options]\n%prog reindex DB_FILE [--registerUnicode]"
    description = "Gives timing statistics for dictionary access methods."
    version = "%%prog %s" % str(cjklib.__version__)
    parser = OptionParser(usage=usage, description=description, version=version)

    # databases
    parser.add_option("-p", "--plainDB", action="store", dest="plainDB",
                      default="plain.db",
                      help="Database with plain tables for run 1")
    parser.add_option("-n", "--nocaseDB", action="store", dest="nocaseDB",
                      default="nocase.db",
                      help="Database with NOCASE collation for runs 2 and 4")
    parser.add_option("-i", "--nocaseindexDB", action="store",
                      dest="nocaseindexDB", default="nocaseindex.db",
                      help=("Database with NOCASE collation and INDEX on"
                            " collation for run 3"))
    parser.add_option("-u", "--unicodeindexDB", action="store",
                      dest="unicodeindexDB", default="unicodeindex.db",
                      help=("Database with Unicode functions and INDEX on"
                            " collation for run 5"))

    parser.add_option("-a", "--all", action="store_true", dest="runAll",
                      default=False, help="Run all tests")
    for no, testNo in enumerate(['first', 'second', 'third', 'fourth',
                                 'fifth']):
        parser.add_option("-%d" % (no + 1), "--%s" % testNo,
                          action="store_true", dest="run%d" % (no + 1),
                          default=False, help="Run %s test" % testNo)

    parser.add_option("-c", "--iterations", action="store", type="int",
                      dest="iterations", default=10,
                      help=("Iterations of test routine [default: %default]"))

    parser.add_option("-r", "--registerUnicode", action="store_true",
                      dest="registerUnicode", default=False,
                      help="Register Unicode functions when re-indexing")

    return parser

def recreateIndex(database, registerUnicode=False):
    connection = {'sqlalchemy.url': 'sqlite:///%s' % database,
                  'attach': ['cjklib'], 'registerUnicode': registerUnicode}
    db = dbconnector.getDBConnector(connection)
    availableDicts = [dictClass.DICTIONARY_TABLE for dictClass
                        in dictionary.BaseDictionary\
                            .getAvailableDictionaries(db)]
    dictionaries = (set(availableDicts)
                    & set(db.engine.table_names(schema=db._mainSchema)))

    for dictName in ['CEDICT', 'CEDICTGR', 'HanDeDict', 'CFDICT']:
        if dictName in dictionaries:
            print "Recreating index for '%s'" % dictName
            try:
                db.execute(text("DROP INDEX %s__Reading" % dictName))
            except OperationalError:
                pass
            db.execute(text(("CREATE INDEX %(dict)s__Reading ON %(dict)s"
                             " ('READING' COLLATE NOCASE)")
                            % {'dict': dictName}))

def main():
    parser = buildParser()
    (opts, args) = parser.parse_args()

    if len(args) == 2:
        cmd, dbFile = args
        if cmd == 'reindex':
            recreateIndex(dbFile, registerUnicode=opts.registerUnicode)
        else:
            parser.error("invalid command")
    elif len(args) != 0:
        parser.error("wrong number of arguments")

    if opts.runAll:
        tests = range(1, 6)
    else:
        tests = []
        for no in range(1, 6):
            if getattr(opts, "run%d" % no):
                tests.append(no)

    testDBMap = {1: 'plainDB', 2: 'nocaseDB', 3: 'nocaseindexDB',
                 4: 'nocaseDB', 5: 'unicodeindexDB'}
    databases = dict((no, getattr(opts, testDBMap[no])) for no in tests)
    registerUnicode = {1: False, 2: False, 3: False, 4: True, 5: True}
    timing = runTests(tests, databases, registerUnicode,
                      iteration=opts.iterations)

    printResults(timing)

if __name__ == "__main__":
    main()
