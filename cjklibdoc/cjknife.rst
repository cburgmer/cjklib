cjknife --- Command Line Interface
==================================

cjknife exposes most functions of the library to the command line.

Examples
--------

Show character information::

    $ cjknife -i 周
    Information for character 周 (traditional locale, Unicode domain)
    Unicode codepoint: 0x5468 (21608, character form)
    Radical index: 30, radical form: ⼝
    Stroke count: 8
    Phonetic data (CantoneseYale): jāu
    Phonetic data (GR): jou
    Phonetic data (Hangul): 주
    Phonetic data (Jyutping): zau1
    Phonetic data (MandarinBraille): ⠌⠷⠁
    Phonetic data (MandarinIPA): tʂou˥˥
    Phonetic data (Pinyin): zhōu
    Phonetic data (ShanghaineseIPA): ʦɤ˥˧
    Phonetic data (WadeGiles): chou1
    Semantic variants: 週
    Glyph 0(*), stroke count: 8
    ⿵⺆⿱土口
    Stroke order: ㇓㇆㇐㇑㇐㇑㇕㇐ (SP-HZG H-S-H S-HZ-H)

Search the EDICT dictionary::

    $ cjknife -w EDICT -x "knowledge"
    ナレッジ /(n) knowledge/
    ノリッジ /(n) knowledge/
    ノレッジ /(n) knowledge/
    学 がく /(n) learning/scholarship/erudition/knowledge/(P)/
    学殖 がくしょく /(n) scholarship/learning/knowledge/
    学力 がくりょく /(n) scholarship/knowledge/literary ability/(P)/
    心得 こころえ /(n) knowledge/information/(P)/
    人智 じんち /(n) human intellect/knowledge/
    人知 じんち /(n) human intellect/knowledge/
    知見 ちけん /(n,vs) expertise/experience/knowledge/
    智識 ちしき /(n) knowledge/
    知識 ちしき /(n) knowledge/information/(P)/
    知得 ちとく /(n,vs) comprehension/knowledge/
    弁え わきまえ /(n) sense/discretion/knowledge/
    辨え わきまえ /(oK) (n) sense/discretion/knowledge/

.. seealso::

   `Screenshots <http://code.google.com/p/cjklib/wiki/Screenshots>`_
      Examples on the project's wiki.

Options
-------

.. program:: cjknife

.. cmdoption:: -i CHAR, --information=CHAR

   print information about the given char

.. cmdoption:: -a READING, --by-reading=READING

   prints a list of characters for the given reading

.. cmdoption:: -r CHARSTR, --get-reading=CHARSTR

   prints the reading for a given character string (for characters with multiple
   readings these are grouped in square brackets; shows the character itself if
   no reading information available)

.. cmdoption:: -f CHARSTR, --convert-form=CHARSTR

   converts the given characters from/to Chinese simplified/traditional form (if
   ambiguous multiple characters are grouped in brackets)

.. cmdoption:: -q CHARSTR

   performs commands -r and -f in one step

.. cmdoption:: -k RADICALIDX, --by-radicalidx=RADICALIDX

   get all characters for a radical given by its index

.. cmdoption:: -p CHARSTR, --by-components=CHARSTR

   get all characters that include all the chars contained in the given list as
   component

.. cmdoption:: -m READING, --convert-reading=READING

   converts the given reading from the input reading to the output reading
   (compatibility needed)

.. cmdoption:: -s SOURCE, --source-reading=SOURCE

   set given reading as input reading

.. cmdoption:: -t TARGET, --target-reading=TARGET

   set given reading as output reading

.. cmdoption:: -l LOCALE, --locale=LOCALE

   set locale, i.e. one character out of TCJKV

.. cmdoption:: -d DOMAIN, --domain=DOMAIN

   set character domain, e.g. 'GB2312'

.. cmdoption:: -L, --list-options

   list available options for parameters

.. cmdoption:: -V, --version

   print version number and exit

.. cmdoption:: -h, --help

   display this help and exit

.. cmdoption:: --database=DATABASEURL

   database url

.. cmdoption:: -x SEARCHSTR

   searches the dictionary (wildcards '_' and '%')

.. cmdoption:: -w DICTIONARY, --set-dictionary=DICTIONARY

   set dictionary
