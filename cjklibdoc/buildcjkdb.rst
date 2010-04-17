buildcjkdb --- Build database
=============================

buildcjkdb builds the database for the cjklib library. Example:
``buildcjkdb build allAvail``.

Builders can be given specific options with format ``--BuilderName-option``
or ``--TableName-option``, e.g. ``--Unihan-wideBuild=yes``.

Options
-------

.. program:: buildcjkdb

.. cmdoption:: --version

   show program's version number and exit

.. cmdoption:: -h, --help

   show this help message and exit

.. cmdoption:: -r, --rebuild

   build tables even if they already exist

.. cmdoption:: -d, --keepDepending

   don't rebuild build-depends tables that are not given

.. cmdoption:: -p BUILDER, --prefer=BUILDER

   builder preferred where several provide the same table

.. cmdoption:: -q, --quiet

   don't print anything on stdout

.. cmdoption:: --database=URL

   database url

.. cmdoption:: --attach=URL

   attachable databases

.. cmdoption:: --registerUnicode=BOOL

   register own Unicode functions if no ICU support available

.. cmdoption:: --ignoreConfig

   ignore settings from cjklib.conf

Global builder options
^^^^^^^^^^^^^^^^^^^^^^

.. cmdoption:: --dataPath=VALUE

   path to data files

.. cmdoption:: --entrywise=BOOL

   insert entries one at a time (for debugging)

.. cmdoption:: --ignoreMissing=BOOL

   ignore missing Unihan column and build empty table

.. cmdoption:: --wideBuild=BOOL

   include characters outside the Unicode BMP

.. cmdoption:: --slimUnihanTable=BOOL

   limit keys of Unihan table

.. cmdoption:: --collation=VALUE

   collation for dictionary entries

.. cmdoption:: --enableFTS3=BOOL

   enable SQLite full text search (FTS3)

.. cmdoption:: --filePath=VALUE

   file path including file name, overrides searching

.. cmdoption:: --fileType=VALUE

   file extension, overrides file type guessing

.. cmdoption:: --useCollation=BOOL

   use collations for dictionary entries
