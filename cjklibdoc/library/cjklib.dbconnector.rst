:mod:`cjklib.dbconnector` --- SQL database access
=================================================


.. automodule:: cjklib.dbconnector

A DatabaseConnector connects to one or more SQL databases. It provides four
simple methods for retrieving scalars or rows of data:

1. :meth:`~cjklib.dbconnector.DatabaseConnector.selectScalar`:
   returns one single value
2. :meth:`~cjklib.dbconnector.DatabaseConnector.selectRow`:
   returns only one entry with several columns
3. :meth:`~cjklib.dbconnector.DatabaseConnector.selectScalars`:
   returns entries for a single column
4. :meth:`~cjklib.dbconnector.DatabaseConnector.selectRows`:
   returns multiple entries for multiple columns

This class takes care to load the correct database(s). It provides for
attaching further databases and gives any program that depends on cjklib the
possibility to easily add own data in databases outside cjklib extending the
library's information.

DatabaseConnector has a convenience function
:meth:`~cjklib.dbconnector.getDBConnector` that loads
an instance with the proper settings for the given project. By default
settings for project ``'cjklib'`` are chosen, but this behaviour can be
overwritten by passing a different project name:
``getDBConnector(projectName='My Project')``. Connection settings can also be
provided manually, omitting automatic searching. Multiple calls with the
same connection settings will return the same shared instance.

Example:

    >>> from cjklib import dbconnector
    >>> from sqlalchemy import select
    >>> db = dbconnector.getDBConnector()
    >>> db.selectScalar(select([db.tables['Strokes'].c.Name],
    ...     db.tables['Strokes'].c.StrokeAbbrev == 'T'))
    u'\u63d0'

DatabaseConnector is tested on SQLite and MySQL but should support most
other database systems through *SQLAlchemy*.

SQLite and Unicode
^^^^^^^^^^^^^^^^^^
SQLite be default only provides letter case folding for alphabetic
characters A-Z from ASCII. If SQLite is built against *ICU*, Unicode
methods are used instead for ``LIKE`` and ``upper()/lower()``. If *ICU* is
not compiled into the database system
:class:`~cjklib.dbconnector.DatabaseConnector` can register own
methods. As this has negative impact on performance, it is disabled by
default. Compatibility support can be enabled by setting option
``'registerUnicode'`` to ``True`` when given as configuration to ``__init__()``
or :meth:`~cjklib.dbconnector.getDBConnector` or alternatively can be
set as default in ``cjklib.conf``.

Multiple database support
^^^^^^^^^^^^^^^^^^^^^^^^^
A DatabaseConnector instance is attached to a main database. Further
databases can be attached at any time, providing further tables. Tables from
the main database will shadow any other table with a similar name. A table
not found in the main database will be chosen from a database in the order
of their attachment.

The :attr:`~cjklib.dbconnector.DatabaseConnector.tables` dictionary
allows simple lookup of table objects by short name, without the need of
knowing the full qualified name including the database specifier.
Existence of tables can be checked using
:meth:`~cjklib.dbconnector.DatabaseConnector.hasTable`;
:attr:`~cjklib.dbconnector.DatabaseConnector.tables` will only include
table information after the first access. All table names can be retrieved with
:meth:`~cjklib.dbconnector.DatabaseConnector.getTableNames`.

Table lookup is designed with a stable data set in mind. Moving tables between
databases is not specially supported and while operations through the
:mod:`cjklib.build` module will update any information in the
:attr:`~cjklib.dbconnector.DatabaseConnector.tables`
dictionary, manual creating and dropping of a table or changing its structure
will lead to the dictionary having obsolete information. This can be
circumvented by deleting keys forcing an update:

    >>> del db.tables['my table']

Example:

    >>> from cjklib.dbconnector import DatabaseConnector
    >>> db = DatabaseConnector({'url': 'sqlite:////tmp/mydata.db',
    ...     'attach': ['cjklib']})
    >>> db.tables['StrokeOrder'].fullname
    'cjklib_0.StrokeOrder'

Discovery of attachable databases
"""""""""""""""""""""""""""""""""
DatabaseConnector has the ability to discover databases attaching them to
the main database. Specifying databases can be done in three ways:

1. A full URL can be given denoting a single database, e.g.
   ``'sqlite:////tmp/mydata.db'``.
2. Giving a directory will add any .db file as SQLite database, e.g.
   ``'/usr/local/share/cjklib'``.
3. Giving a project name will prompt DatabaseConnector to check for
   a project config file and add databases specified there and/or scan
   that project's default directories, e.g. ``'cjklib'``.

Functions
---------

.. autofunction:: getDBConnector

.. autofunction:: getDefaultConfiguration


Classes
--------

.. currentmodule:: cjklib.dbconnector

.. autoclass:: DatabaseConnector
   :show-inheritance:
   :members:
   :undoc-members:

   .. autoattribute: attached
   .. autoattribute: compatibilityUnicodeSupport
   .. autoattribute: connection
   .. autoattribute: databaseUrl
   .. autoattribute: engine
   .. autoattribute: metadata
   .. autoattribute: DatabaseConnector.tables
