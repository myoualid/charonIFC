#!/usr/bin/env python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011 <Davide Vescovini> <davide.vescovini@gmail.com>
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

from distutils.core import setup

# run the setup function from distutils
setup(name='charonifc',
      version='1.0',
      license='GPL-3',
      #requires = ["wx"],
      description="Extract information from IFC file to produce Technical Specifications and Bill of Quantities",
      long_description="""A library to extract information from an IFC file to produce Technical Documentation like Specifications and Bill of Quantities.
This program use the Open Source software IfcOpenShell, see <http://ifcopenshell.org/> an open source ([LGPL]) software library for working with the Industry Foundation Classes ([IFC]) file format.""",
      author='Davide Vescovini',
      author_email='davide.vescovini@gmail.com',
      url='https://launchpad.net/charonifc',
      packages =    ['charonifc',
                     'ifcopenshell27',
                     'ifcopenshell27_x64',
                     'ifcopenshell35',
                     'ifcopenshell35_x64', 
                     'ifcopenshell35_mac',
                     'ifcopenshell35_win64'],
      package_dir = {'charonifc':            "charonifclib",
                     'ifcopenshell27':       "ifcopenshell27",
                     'ifcopenshell27_x64':   "ifcopenshell27_x64",
                     'ifcopenshell35':       "ifcopenshell35",
                     'ifcopenshell35_x64':   "ifcopenshell35_x64",
                     'ifcopenshell35_mac':   "ifcopenshell35_mac",
                     'ifcopenshell35_win64': "ifcopenshell35_win64"},
      package_data= {'charonifc': ['data/*.*', 
                                   'data/psd/*.*',
                                   'data/qto/*.*',
                                   'locale/*/LC_MESSAGES/*']},
      data_files = [("", ["COPYING", "README.md"])],
      scripts= ['charonifc'],
      # setup classification for repository of Python apps
      classifiers=['Development Status :: 1.0 - Beta',
                   'Environment :: Console',
                   'Environment :: X11 Applications :: GTK',
                   'Intended Audience :: End Users/Desktop',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Operating System :: MacOS :: MacOS X',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python',
                   'Topic :: Office/Business',
                   'Topic :: Scientific/Engineering',
                   'Topic :: Utilities']
     )

