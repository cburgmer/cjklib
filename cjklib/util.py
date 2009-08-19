#!/usr/bin/python
# -*- coding: utf-8 -*-
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
Provides utilities.
"""

import os.path
import ConfigParser

def getConfigSettings(section, projectName='cjklib'):
    """
    Reads the configuration from the given section of the project's config file.

    @type section: str
    @param section: section of the config file
    @type projectName: str
    @param projectName: name of project which will be used as name of the
        config file
    @rtype: dict
    @return: configuration settings for the given project
    """
    # don't convert to lowercase
    h = ConfigParser.SafeConfigParser.optionxform
    try:
        ConfigParser.SafeConfigParser.optionxform = lambda self, x: x
        config = ConfigParser.SafeConfigParser()
        config.read([os.path.join(os.path.expanduser('~'),
            '.%s.conf' % projectName),
            os.path.join('/', 'etc', '%s.conf' % projectName)])

        configuration = dict(config.items(section))
    except ConfigParser.NoSectionError:
        configuration = {}

    ConfigParser.SafeConfigParser.optionxform = h

    return configuration
