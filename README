===========================
Installing and Using Cjklib
===========================

.. contents::

Introduction
============
Cjklib provides language routines related to Han characters (characters based
on Chinese characters named Hanzi, Kanji, Hanja and chu Han respectively) used
in writing of the Chinese, the Japanese, infrequently the Korean and formerly
the Vietnamese language(s). Functionality is included for character
pronunciations, radicals, glyph components, stroke decomposition and variant
information.

Dependencies
============
- Python_ 2.4 or above (currently no support for Python3)
- SQLite_ 3+
- SQLAlchemy_ 0.5+
- pysqlite2_ (already ships with Python 2.5 and above)

Alternatively for MySQL as backend:

- MySQL_ 5+
- MySQL-Python_

.. _Python: http://www.python.org/download/
.. _SQLite: http://www.sqlite.org/download.html
.. _MySQL: http://www.mysql.com/downloads/mysql/
.. _SQLAlchemy: http://www.sqlalchemy.org/download.html
.. _pysqlite2: http://code.google.com/p/pysqlite/downloads/list
.. _MySQL-Python: http://sourceforge.net/projects/mysql-python/

Installing
==========

Windows
-------
Install cjklib using the provided ``.exe`` installer. Make sure above
dependencies are satisfied.

Three scripts ``cjknife.exe``, ``buildcjkdb.exe``, and ``installcjkdict.exe``
will be added to the Python ``Scripts`` sub-directory. Make sure this directory
is included in your ``PATH`` environment variable to access these programs from
the command line.

CJK dictionaries are not included by default. If you want to install any of
those run the following (with an Internet connection) from the root directory
of the source package::

    $ installcjkdict CEDICT

This will download CEDICT, create a SQLite database file and install it under
the directory given by the ``APPDATA`` environment variable, e.g.
``C:\windows\profiles\MY_USER\Application Data\cjklib``. Just substitute
``CEDICT`` for any other supported dictionary (i.e. EDICT, CEDICT, HanDeDict,
CFDICT, CEDICTGR).

Unix
----
If you are installing from the source package you need to deploy the library on
your system::

    $ sudo python setup.py install

Also make sure above dependencies are satisfied. CJK dictionaries are not
included by default. If you want to install any of those run the following
(with an Internet connection)::

    $ sudo installcjkdict CEDICT

This will download CEDICT, create a SQLite database file and install it to
``/usr/local/share/cjklib``. Just substitute ``CEDICT`` for any other supported
dictionary (i.e. EDICT, CEDICT, HanDeDict, CFDICT, CEDICTGR).


Documentation & Usage
=====================
Documentation_ is available online. Also see the `project page`_ and its wiki.
There is a small command line tool ``cjknife`` that offers some of the library's
functions. See ``cjknife --help`` for an overview.

.. _Documentation: http://cjklib.org/
.. _project page: http://code.google.com/p/cjklib/

Examples
--------

- Get stroke order of characters::

    >>> from cjklib import characterlookup
    >>> cjk = characterlookup.CharacterLookup('C')
    >>> cjk.getStrokeOrder(u'说')
    [u'㇔', u'㇊', u'㇔', u'㇒', u'㇑', u'㇕', u'㇐', u'㇓', u'㇟']

- Access a dictionary (here using Jim Breen's EDICT)::

    >>> from cjklib.dictionary import EDICT
    >>> d = EDICT()
    >>> d.getForTranslation('Tokyo')
    [EntryTuple(Headword=u'東京', Reading=u'とうきょう',
    Translation=u'/(n) Tokyo (current capital of Japan)/(P)/')]


Database
========
Packaged versions of the library will ship with a pre-built SQLite database
file. You can however easily rebuild the database yourself.

First download the newest Unihan file::

    $ wget ftp://ftp.unicode.org/Public/UNIDATA/Unihan.zip

Then start the build process::

    $ sudo buildcjkdb -r build cjklibData

SQLite
------
SQLite by default has no Unicode support for string operations. Optionally the
ICU library can be compiled in for handling alphabetic non-ASCII characters.
Cjklib can register own Unicode functions if ICU support is missing. Queries
with ``LIKE`` will then use function ``lower()``. This compatibility mode has
negative impact on performance and as it is not needed for dictionaries like
EDICT or CEDICT it is disabled by default. See ``cjklib.conf`` for enabling.

MySQL
-----
With MySQL 5 the following ``CREATE`` command creates a database with ``utf8``
as character set using the general Unicode collation
(MySQL from 5.5.3 on will support full Unicode given character set
``utf8mb4`` and collation ``utf8mb4_bin``)::

    CREATE DATABASE cjklib DEFAULT CHARACTER SET utf8 COLLATE utf8_bin;

You might need to set access rights, too (substitute ``user_name`` and
``host_name``)::

    GRANT ALL ON cjklib.* TO 'user_name'@'host_name';

Now update the settings in  ``cjklib.conf``.

MySQL < 5.5 doesn't support full UTF-8, and uses a version with max 3 bytes, so
characters outside the Basic Multilingual Plane (BMP) can't be encoded. Building
the Unihan database thus might result in warnings, characters above U+FFFF
can't be built at all. You need to disable building the full character range
by setting ``wideBuild`` to ``False`` in ``cjklib.conf`` before building.
Alternatively pass ``--wideBuild=False`` to ``buildcjkdb``.


Contact
=======
For help or discussions on cjklib, join `cjklib-devel@googlegroups.com
<http://groups.google.com/group/cjklib-devel>`_.

Please report bugs to the `project's bug tracker
<http://code.google.com/p/cjklib/issues/list>`_.
