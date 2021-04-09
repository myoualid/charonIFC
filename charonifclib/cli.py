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

################################################################################
############# IMPORTAZIONE MODULI ##############################################
################################################################################
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import argparse
import time

################################################################################
############# SETUP LOGGING ####################################################
################################################################################
import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
logger =logging.getLogger()

################################################################################
############# IMPORTAZIONE MODULI CUSTOM #######################################
################################################################################

from . import charonifclib

# import helper function to manage project files
from .helper import read_config_file, test_pandoc

# import function to translate IFC strings
from .translator import untranslated_word_log

################################################################################
############ SUPPORTO PER LA LOCALIZZAZIONE ####################################
################################################################################
import locale
locale.setlocale(locale.LC_ALL, '')
#get the current setup
current_locale, encoding = locale.getdefaultlocale()

################################################################################
############ SUPPORTO INTERNAZIONALIZZAZIONE ###################################
################################################################################
# get locale path
from . import get_locale_path, __gettextdomain__
# install gettext module and default system language
import gettext
default_lang = gettext.translation(__gettextdomain__, 
                                   localedir=get_locale_path(), 
                                   languages=[current_locale])
default_lang.install()

################################################################################
############# GLOBAL VARIABLES #################################################
################################################################################
DEFAULT_FORMAT = "odt"
DESCRIPTION = "CharonIfc is an IFC Parser Software by Davide Vescovini."
EPILOG = """Examples of usage:

To create an OpenDocument (.odt) listing all IFC TypeObjects, including 
Properties, from an IFC model:
    charonifc myfile.ifc

To create a Word (.docx) document from an IFC model:
    charonifc myfile.ifc -f docx

To create a CSV Bill of Quantity from an IFC model:
    charonifc myfile.ifc -b

To create a Primus (.pwe) Bill of Quantity from an IFC model:
    charonifc myfile.ifc -b --pwe"""

################################################################################
############# TIME FUNCTION TO WAIT UNTIL THE FILE HAS BEEN CREATED ############
################################################################################

def wait_for_file_creation(filename, mintime=60):
    # setup a time iterator and check if the file exists every 0.5 seconds
    time_iterator = 0
    while not os.path.isfile(filename):
        time.sleep(0.5)
        time_iterator += 1
        print (_("Creating output file, please wait..."))
        # if it takes more than 60 seconds there is something wrong
        if time_iterator > mintime:
            print (_("File not created. Exiting..."))
            raise IOError
    return True

################################################################################
############# ******* ##########################################################
################################################################################

def main():
    # test if pandoc is installed
    is_pandoc_present = test_pandoc()
    # create command options to parse later
    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG,
                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename',
                        type=argparse.FileType('r'),
                        nargs='+',
                        help='IFC file to open')
    parser.add_argument("-o", "--ouput", dest="output",
                        type=argparse.FileType('w'),
                        help="output file name")
    parser.add_argument("-f", "--format", dest="format",
                        type=str,
                        help="""choose the output file format (html, latex, 
                             odt, docx), default is latex""")
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="count", default=0,
                        help="increase the program output verbosity")
    parser.add_argument("-t", "--template", dest="template",
                        type=argparse.FileType('r'),
                        help="Template o file di stile per il documento")
    parser.add_argument("-c", "--config", dest="config_file",
                        type=argparse.FileType('r'),
                        help="The configuration file to load")
    parser.add_argument("-x", "--extract-properties", dest="ext_prop",
                        action="store_true", default=False,
                        help="""Create a document listing all the objects
                             with their associated properties (by using 
                             IfcRelDefinesByProperties).""")
    parser.add_argument("-b", "--boq", dest="boq",
                        action="store_true", default=False,
                        help="""Create a BOQ (bill of quantities) extracting
                             all the Ifc objects referenced by an IfcType
                             Please note this is not a standard BOQ.""")
    parser.add_argument('--select-by-property', dest="byprop",
                        metavar=('PROPERTY_NAME', 'VALUE'), 
                        type=str, default=None, nargs=2,
                        help="""Create document or BOQ selecting only IfcObjects
                             with the same Property Name and Value 
                             (e.g. "Manufacturer ABC" or "Satatus new").
                             To select all objects with a given Property Name 
                             regardless of its value use the wildcard "*" 
                             (e.g. Status "*"). """)
    parser.add_argument("--title", dest="title",
                        type=str,
                        help="set the document title")
    parser.add_argument("--pwe", dest="boqoutput",
                        action='store_const', const="pwe",
                        help="""While creating a BOQ (bill of quantities) the
                             output is a PWE file for exchange with Primus""")
    parser.add_argument("--xpwe", dest="boqoutput",
                        action='store_const', const="xpwe",
                        help="""While creating a BOQ (bill of quantities) the
                             output is a XPWE, XML exchange file for Primus""")
    parser.add_argument("--sql", dest="boqoutput",
                        action='store_const', const="sql",
                        help="""While creating a BOQ (bill of quantities) the
                             output is an SQL dump file for exchange with 
                             an SQL Database""")
    parser.add_argument("--plist", dest="epulist",
                        action='store_true', default=False,
                        help="""After creating a BOQ (bill of quantities)
                             create a file containing a list of unit price 
                             ready to associate tags from pre-made price lists
                             that can be read by the --assoprice <filename>
                             option.""")
    parser.add_argument("--assoprice", dest="assoprice",
                        type=str,
                        help="""After creating a BOQ (bill of quantities)
                             associate the unit price list creatrating the 
                             entries listed in the input file.""")
    parser.add_argument("--add-forms-rebars", dest="addrebars",
                        action="store_true", default=False,
                        help="""While creating the BOQ adds a tariff for each
                           IfcBeam, IfcSlab, IfcSlab, IfcWall, IfcStair. The 
                           default formula used for calculations are the 
                           following (but configurable from config file):
                           * Concrete's quantity (Cv)
                           a) For bearing wall, column, slab & beam:
                               Cv (m3) = IfcQuantityVolume value;
                           b) Stairs:
                               Cv (m3) = Number of Riser*Tread Length *Width*Actual Riser Height;
                           * Rebar's quantity (Rv)
                               Rv (kg) = Cv*Rebar's ratio of concrete;
                           * Form's quantity (Fv)
                               Fv (m2) = Cv*Form's ratio of concrete""")
    parser.add_argument("--sort-by-space", dest="sortbyspace",
                        action="store_true", default=False,
                        help="""While creating the BOQ sort the IfcObjects by 
                             Builging - Storey - Spaces. Without this option the
                             BOQ is sorted by Building - Storey and Type
                             (e.g. Alarms, Doors, Windows, Walls, etc.)""")
    parser.add_argument("--import-price-list", dest="importfile",
                        type=str, default=None,
                        help="""Before creating the BOQ import a Price List or
                             BOQ from Primus (PWE exchange format) or STR SIX 
                             format (XML).""")
    parser.add_argument("--aecosim", dest="aecosim",
                        action="store_true", default=False,
                        help="""Convert an IFC item to Aecosim DataGroup 
                        Catalog XML.""")
    parser.add_argument("--logfile", dest="logfile",
                        type=str,
                        help="""Output the log informations to file with
                             'logfile' name.""")
    parser.add_argument("--log-untranslated", dest="untranslated_logfile",
                        type=str, metavar='LOGFILE', 
                        #action="store_true", default=False,
                        help="""Log to a file a list of untranslated words.""")
    parser.add_argument("--language", dest="language",
                        type=str,
                        help="""Change the default system language, including
                        the translation of technical words, if available. 
                        Valid formats are: it_IT, fr_FR, es_ES, de_DE, ...""")
    parser.add_argument("--version", dest="version",
                        action="store_true", default=False,
                        help="""Show the IFC file schema version (2x3, 4, ...)
                             and quit.""")

    # parse the arguments
    args = parser.parse_args()
    # setup the logging level
    if args.verbose ==1:
        logger.setLevel(logging.WARNING)
        logger.warning("Log level set to INFO")
    elif args.verbose ==2:
        logger.setLevel(logging.INFO)
        logger.info("Log level set to INFO")
    elif args.verbose ==3:
        logger.setLevel(logging.DEBUG)
        logger.debug("Log level set to DEBUG")
    # setup the log information logfile if required
    if args.logfile is not None:
        hdlr = logging.FileHandler(args.logfile)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.info("Log saved to file '{0}'".format(args.logfile))
    # read the configuration files
    config = read_config_file(config_filename=args.config_file)
    # setup the default settings for charonifclib
    charonifclib.SetCalculationRules(config._sections["IFCOBJECT_CALCULATION_RULES"])
    #create the settings configuration
    settings = charonifclib.PrintSettings()
    # setup a different language if required
    if args.language is not None:
        nl = gettext.translation(__gettextdomain__, 
                                 localedir=get_locale_path(), 
                                 languages=[args.language])
        nl.install()
        # setup the document's language for translations
        charonifclib.SetLanguage(args.language)
    # show the schema version
    if args.version:
        for f in args.filename:
            IfcChk = charonifclib.IfcCheck(f.name)
            print(IfcChk.GetIfcSchema())
        return
    # setup the documents we want to print with default title and options
    if args.ext_prop:
        title = _("Property Extraction")
    elif args.boq:
        title = _("Bill of Quantities")
    else:
        title = _("Technical Specifications")
    # If the Create an output file with the teamplate and the chosen options
    if args.title is not None:
        title = args.title
    # use a template if required
    if args.template is not None:
        template = args.template.name
    else: template = None
    # setup the Property & IFC type Blacklist
    # Python 2.7 ConfigParser attribute error
    try:
        type_blacklist = config["BLACKLIST_IFCTYPE"].items()
        prop_blacklist = config["BLACKLIST_PROPERTY"].items()
    except AttributeError:
        type_blacklist = config.items("BLACKLIST_IFCTYPE")
        prop_blacklist = config.items("BLACKLIST_PROPERTY")
    # parse all files in args.filename
    for f in args.filename:
        print (_("Processing {0}").format(f.name))
        # setup the output file
        if args.output is not None:
           output_file = args.output.name
        else:
           output_file = f.name
        # create BOQ or Technical specification
        if args.boq:
            if args.assoprice is not None:
                logging.info(_("Associating prices from file: {}").format(
                             args.assoprice))
            boq = charonifclib.IfcBOQ(f.name, output=args.boqoutput,
                                      list_price=args.epulist,
                                      assolist=args.assoprice,
                                      add_concrete_rebars=args.addrebars,
                                      sort_by_space=args.sortbyspace,
                                      import_price_list=args.importfile,
                                      select_by_property=args.byprop)
            # wait until the file has been created
            wait_for_file_creation(boq.GetOutputFile())
            # if we create also a list of prices to associate
            if args.epulist:
                print(_("BOQ Price List '{}' created.").format(
                      boq.GetAssociationFile()))
            # print something and exit
            print(_("Done, BOQ '{}' created.").format(boq.GetOutputFile()))
        # create Technical Specifications
        else:
            # Create a memory structure for each IFC object
            IfcLib = charonifclib.IfcParser(f.name)
            # check if we need to create a list of items by property
            if args.byprop is not None:
                p_list = IfcLib.GetItemsByProperty(args.byprop[0], 
                                                   args.byprop[1])
            else:
                p_list = None
            # create a format agnostic markup text
            MarkedUpText = IfcLib.MarkUpText(title,
                                             type_blacklist,
                                             prop_blacklist,
                                             args.ext_prop,
                                             settings, p_list)
            # retrive the format from format param, default is latex
            if args.format is None:
                args.format = DEFAULT_FORMAT
            # use 'pandoc' software to output with the desired format
            if is_pandoc_present:
                ofn = charonifclib.PandocConverter(MarkedUpText, 
                                                   args.format, 
                                                   output_file, 
                                                   template)
            # if pandoc is not installed in the system output to plain text
            else:
                print ("""Pandoc program not found. (https://pandoc.org) """
                       """Install pandoc if you want to export """
                       """in a format other than simple text.""")
                ofn = charonifclib.HtmlConverter(MarkedUpText,
                                                 output_file)
            # wait until the file has been created
            wait_for_file_creation(ofn)
            # print something and exit
            print(_("Done, file '{}' created.").format(ofn))
            # if AECOsim option is used convert the IFC file to DataGroup entry
            if args.aecosim:
                datagroupfile = IfcLib.AecosimDataGroup()
                # check if the file has been created, print something and exit
                if os.path.isfile(datagroupfile):
                    print("AECOsim DataGroup file '{}' created.".format(
                           datagroupfile))
        # if needed print the untranslated word log
        if args.untranslated_logfile is not None:
            untranslated_word_log(args.untranslated_logfile)
            print("List of untranslated words saved to file: '{}'.".format(
                  args.untranslated_logfile))

################################################################################
############# MAIN PROGRAM START ###############################################
################################################################################

if __name__ == "__main__":
  # if the program is invoked without arguments open the CLI
  main()
