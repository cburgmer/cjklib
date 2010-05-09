Downloading & Installing
========================

cjklib has the following dependencies:

- Python_ 2.4 or above (currently no support for Python3)
- SQLite_ 3+
- SQLAlchemy_ 0.4.8+
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

Windows
-------
Download the ``.exe`` installer from the
`Python package index <http://pypi.python.org/pypi/cjklib/>`_ and run it.

Three scripts ``cjknife.exe``, ``buildcjkdb.exe``, and ``installcjkdict.exe``
will be added to the Python ``Scripts`` sub-directory. Make sure this directory
is included in your ``PATH`` environment variable to access these programs from
the command line.

CJK dictionaries are not included by default. If you want to install any of
those run the following (with an Internet connection)::

    $ installcjkdict CEDICT

This will download CEDICT, create a SQLite database file and install it under
the directory given by the ``APPDATA`` environment variable, e.g.
``C:\windows\profiles\MY_USER\Application Data\cjklib``. Just substitute
``CEDICT`` for any other supported dictionary (i.e. EDICT, CEDICT, HanDeDict,
CFDICT, CEDICTGR).

DEB or RPM based systems
------------------------
Packages are available from the
`project page <http://code.google.com/p/cjklib/downloads/list>`_. An Ubuntu
package is available from a
`personal package archive <https://launchpad.net/~cburgmer/+archive/ppa>`_.
Install from the provided .deb or .rpm package. See below for installing
dictionaries.

Linux
-----
Get the source package from the
`Python package index <http://pypi.python.org/pypi/cjklib/>`_ and deploy the
library on your system::

    $ sudo python setup.py install

CJK dictionaries are not included by default. If you want to install any of
those run the following (with an Internet connection)::

    $ sudo installcjkdict CEDICT

This will download CEDICT, create a SQLite database file and install it to
``/usr/local/share/cjklib``. Just substitute ``CEDICT`` for any other supported
dictionary (i.e. EDICT, CEDICT, HanDeDict, CFDICT, CEDICTGR).

Development version
-------------------

The development version is available from svn::

    $ svn checkout http://cjklib.googlecode.com/svn/trunk/ cjklib

You now need to generate the database. Download the Unihan database and call
the build CLI (which is not yet installed as executable)::

    $ cd cjklib
    $ wget ftp://ftp.unicode.org/Public/UNIDATA/Unihan.zip
    $ python -m cjklib.build.cli build cjklibData --attach= \
        --database=sqlite:///cjklib/cjklib.db
    $ sqlite3 cjklib/cjklib.db "VACUUM"

The last step is optional but will help to optimize the database file.

Install by running::

    $ sudo python setup.py install

Database
--------
Packaged versions of the library will ship with a pre-built SQLite database
file. You can however easily rebuild the database yourself.

First download the newest Unihan file::

    $ wget ftp://ftp.unicode.org/Public/UNIDATA/Unihan.zip

Then start the build process::

    $ sudo buildcjkdb -r build cjklibData

SQLite
^^^^^^
SQLite by default has no Unicode support for string operations. Optionally the
ICU library can be compiled in for handling alphabetic non-ASCII characters.
Cjklib can register own Unicode functions if ICU support is missing. Queries
with ``LIKE`` will then use function ``lower()``. This compatibility mode has
negative impact on performance and as it is not needed for dictionaries like
EDICT or CEDICT it is disabled by default. See :file:`cjklib.conf` for enabling.

MySQL
^^^^^
With MySQL 5 the following ``CREATE`` command creates a database with ``utf8``
as character set using the general Unicode collation
(MySQL from 5.5.3 on will support full Unicode given character set
``utf8mb4`` and collation ``utf8mb4_bin``)::

    CREATE DATABASE cjklib DEFAULT CHARACTER SET utf8 COLLATE utf8_bin;

You might need to set access rights, too (substitute ``user_name`` and
``host_name``)::

    GRANT ALL ON cjklib.* TO 'user_name'@'host_name';

Now update the settings in :file:`cjklib.conf`.

MySQL < 5.5 doesn't support full UTF-8, and uses a version with max 3 bytes, so
characters outside the Basic Multilingual Plane (BMP) can't be encoded. Building
the Unihan database thus might result in warnings, characters above U+FFFF
can't be built at all. You need to disable building the full character range
by setting ``wideBuild`` to ``False`` in ``cjklib.conf`` before building.
Alternatively pass ``--wideBuild=False`` to ``buildcjkdb``.

