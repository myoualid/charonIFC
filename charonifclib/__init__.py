#!/usr/bin/env python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2017 <Davide Vescovini> <davide.vescovini@gmail.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE


###
# This program use the Open Source software IfcOpenShell
# see <http://ifcopenshell.org/> an open source ([LGPL]) software 
# library for working with the Industry Foundation Classes ([IFC]) 
# file format. 
# Currently supported IFC releases are [IFC2x3 TC1] and [IFC4 Add1].
# A pre-compiled version of this program is distributed with a copy of
# this software.
# For more information, see
# * [http://ifcopenshell.org](http://ifcopenshell.org)  
# * [http://academy.ifcopenshell.org](http://academy.ifcopenshell.org)
###

from __future__ import print_function

__all__ = ["charonifclib", "preventa_lib"]

# Data directory
__data_directory__ = 'data'
# Locale directory
__locale_directory__ = 'locale'
# gettext domain
__gettextdomain__ = 'charonifc'

################################################################################
############# IMPORTAZIONE MODULI ##############################################
################################################################################

import os

################################################################################
############# READ/WRITE CONFIGURATION FILES ###################################
################################################################################

def __get_path__(directory):
    """Common function to get a given path."""
    # Get pathname absolute or relative.
    path = os.path.join(os.path.dirname(__file__), directory)
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        print ("Path {} does not exist.".format(abs_path))
        raise IOError
    return abs_path

def get_data_path():
    """Retrieve data path
    This path is by default <*_lib_path>/../data/ in trunk
    and /usr/share/charonifc in an installed version but this path
    is specified at installation time.
    """
    return __get_path__(__data_directory__)

def get_locale_path():
    """Retrieve data path
    This path is by default <*_lib_path>/../locale/ in trunk
    and /usr/share/charonifc in an installed version but this path
    is specified at installation time.
    """
    return __get_path__(__locale_directory__)
