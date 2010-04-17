:mod:`cjklib.build` --- Build database
======================================


.. automodule:: cjklib.build


Each table that needs to be created has to be implemented by subclassing a
:class:`~cjklib.build.builder.TableBuilder`. The
:class:`~cjklib.build.DatabaseBuilder` is the central instance for managing the
build process. As the creation of a table can depend on other tables the
DatabaseBuilder keeps track of dependencies to process a build in the correct
order.

Building is tested on the following storage methods:

- SQLite
- MySQL

Examples
^^^^^^^^
The following examples should give a quick view into how to use this
package.

- Create the DatabaseBuilder object with default settings (read from
  ``cjklib.conf`` or using ``cjklib.db`` in same directory as default):

    >>> from cjklib import build
    >>> dbBuilder = build.DatabaseBuilder(dataPath=['./cjklib/data/'])
    Removing conflicting builder(s) 'StrokeCountBuilder' in favour of 'CombinedStrokeCountBuilder'
    Removing conflicting builder(s) 'CharacterResidualStrokeCountBuilder' in favour of 'CombinedCharacterResidualStrokeCountBuilder'

- Build the table of Jyutping syllables from a csv file:

    >>> dbBuilder.build(['JyutpingSyllables'])
    building table 'JyutpingSyllables' with builder
    'JyutpingSyllablesBuilder'...
    Reading table definition from file './cjklib/data/jyutpingsyllables.sql'
    Reading table 'JyutpingSyllables' from file
    './cjklib/data/jyutpingsyllables.csv'

Functions
----------

.. autofunction:: warn




Classes
--------

.. autoclass:: DatabaseBuilder
   :show-inheritance:
   :members:
   :undoc-members:
   

