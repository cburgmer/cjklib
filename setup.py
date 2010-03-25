#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup
import re
import cjklib

VERSION = str(cjklib.__version__)
(AUTHOR, EMAIL) = re.match('^(.*?)\s*<(.*)>$', cjklib.__author__).groups()
URL = cjklib.__url__
LICENSE = cjklib.__license__

setup(name='cjklib',
    version=VERSION,
    description='Han character library for CJKV languages',
    long_description=open('README').read(),
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=['cjklib', 'cjklib.reading', 'cjklib.dictionary', 'cjklib.build',
        'cjklib.test'],
    package_dir={'cjklib': 'cjklib'},
    package_data={'cjklib': ['data/*.csv', 'data/*.sql', 'cjklib.db',
        'cjklib.conf']},
    entry_points={
        'console_scripts': [
            'buildcjkdb = cjklib.build.cli:main',
            'installcjkdict = cjklib.dictionary.install:main',
            'cjknife = cjklib.cjknife:main',
        ],
    },
    install_requires="SQLAlchemy >= 0.4.8",
    license=LICENSE,
    classifiers=['Topic :: Text Processing :: Linguistic',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: Chinese (Simplified)',
        'Natural Language :: Chinese (Traditional)',
        'Natural Language :: Japanese',
        'Natural Language :: Korean',
        'Natural Language :: Vietnamese',
        ])
