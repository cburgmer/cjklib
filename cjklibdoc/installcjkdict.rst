installcjkdict --- Install dictionaries
=======================================

installcjkdict downloads and installs a dictionary.

Examples
--------

Download and install CEDICT to ``$HOME/cjklib/`` (Windows), ``$HOME/.cjklib/``
(Unix) or ``$HOME/Library/Application Support/`` (Mac OS X)::

    $ installcjkdict --local CEDICT

Download CFDICT::

    $ installcjkdict --download CFDICT
    Getting download page http://www.chinaboard.de/cfdict.php?mode=dl... done
    Found version 2009-11-30
    Downloading http://www.chinaboard.de/cfdict/cfdict-20091130.tar.bz2...
    100% |###############################################| Time: 00:00:00 193.85 B/s
    Saved as cfdict-20091130.tar.bz2

Options
-------

.. program:: installcjkdict

.. cmdoption:: --version

   show program's version number and exit 

.. cmdoption:: -h, --help

   show this help message and exit

.. cmdoption:: -f, --forceUpdate

   install dictionary even if the version is older or equal

.. cmdoption:: --prefix=PREFIX

   installation prefix

.. cmdoption:: --local

   install to user directory

.. cmdoption:: --download

   download only

.. cmdoption:: --targetName=TARGETNAME

   target name of downloaded file (only with --download)

.. cmdoption:: --targetPath=TARGETPATH

   target directory of downloaded file (only with --download)

.. cmdoption:: -q, --quiet

   don't print anything on stdout

.. cmdoption:: --database=URL

   database url

.. cmdoption:: --attach=URL

   attachable databases

.. cmdoption:: --registerUnicode=BOOL

   register own Unicode functions if no ICU support available

Global builder options
^^^^^^^^^^^^^^^^^^^^^^

.. cmdoption:: --collation=VALUE

   collation for dictionary entries

.. cmdoption:: --enableFTS3=BOOL

   enable SQLite full text search (FTS3)

.. cmdoption:: --useCollation=BOOL

   use collations for dictionary entries
