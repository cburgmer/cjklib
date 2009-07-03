#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
import re
import glob
import cjklib

VERSION = str(cjklib.__version__)
(AUTHOR, EMAIL) = re.match('^(.*?)\s*<(.*)>$', cjklib.__author__).groups()
URL = cjklib.__url__
LICENSE = cjklib.__license__

setup(name='cjklib',
    version=VERSION,
    description='Han character related methods for CJKV languages',
    long_description="Cjklib provides language routines related to Han characters (characters based on Chinese characters named Hanzi, Kanji, Hanja and chu Han respectively) used in writing of the Chinese, the Japanese, infrequently the Korean and formerly the Vietnamese language(s). Functionality is included for character pronunciations, radicals, glyph components, stroke decomposition and variant information.",
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=['cjklib', 'cjklib.reading'],
    package_dir={'cjklib': 'cjklib'},
    package_data={'cjklib': ['data/*.csv', 'data/*.sql']},
    scripts=['cjknife', 'buildcjkdb'],
    data_files=[('/etc', ['cjklib.conf']),
        ('/var/lib/cjklib', ['cjklib.db']),
        ('share/doc/python-cjklib/examples', glob.glob("examples/*.py")),
        ('share/doc/python-cjklib/scripts', glob.glob("scripts/*.py")),
        ('share/doc/python-cjklib/', ['README', 'changelog', 'COPYING',
            'DEVELOPMENT'])],
    license=LICENSE,
    classifiers=['Topic :: Text Processing :: Linguistic',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',])
