#!/usr/bin/python
# -*- coding: utf8 -*-
# This file is part of cjklib.
#
# cjklib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cjklib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cjklib.  If not, see <http://www.gnu.org/licenses/>.

"""
runtest.py runs the cjklib's unit tests.

@copyright: Copyright (C) 2006-2008 Christoph Burgmer. See the library for
    the copyright on incorporated data.
"""

import unittest

from cjklib import test

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(test)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
