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

################################################################################
############# IMPORTAZIONE MODULI ##############################################
################################################################################

from __future__ import print_function

import os
import sys
import platform
import subprocess
import logging

# retro-compatibility with Python 2.6
try:
    import configparser
except:
    import ConfigParser as configparser

# Import predefined data from charonifclib
from .charonifclib import IfcObjectsCalculationRules as CalcRules

################################################################################
############# READ/WRITE CONFIGURATION FILES ###################################
################################################################################

# default dir name and configuration file name
__config_dir__ =  "charonifc"
__config_file__ = "charonifc.cfg"

# sections required in the configuration file
REQUIRED_CONFIG_SECTIONS = {"USERSETTINGS": None,
                            "BLACKLIST_PROPERTY": None,
                            "BLACKLIST_IFCTYPE": None,
                            "IFCOBJECT_CALCULATION_RULES": CalcRules}

def get_config_file():
    """Retrieve user configuration path: $HOME/$CONFIGURATION_PATH/"""
    _platform = platform.system()
    # Get pathname absolute or relative.
    if _platform == "Windows":
        # Windows code:
        config_path = os.path.join(os.getenv("APPDATA"), 
                                   __config_dir__,
                                   __config_file__)
    else:
        #Linux and Mac code:
        config_path = os.path.join(os.path.expanduser("~"),
                                   ".local",
                                   "share",
                                   __config_dir__,
                                   __config_file__)
    # if the folder does not exist create the file
    if os.path.exists(config_path):
        return config_path
    # look for the config path in the execution folder
    elif os.path.exists(os.path.join(os.getcwd(), __config_file__)):
        config_path = os.path.join(os.getcwd(), __config_file__)
    return config_path

def read_config_file(config_filename=None, check_required_sections=True):
    """legge il file di configurazione e ne ricava le impostazioni"""
    # inizializza il parser
    config = configparser.ConfigParser(allow_no_value=True)
    # make configparse case-sensitive
    config.optionxform = lambda option: option
    # setup a function to parse the config sections 
    def parse_section(settings, section):
        """Function to read the confic file and output an error if a section is missing"""
        if settings.has_section(section):
            return True
        else:
            return False
    # controllo se la verifica avviene su di un file temporaneo
    if config_filename is not None: 
        file_cfg = config_filename
    else:
        file_cfg = get_config_file()
    # verifico l'esistenza del file da leggere
    if not os.path.exists(file_cfg):
        logging.error("Configuration File '{0}' does not exist".format(file_cfg))
        # create a configuration file
        file_cfg = create_config_file(file_cfg, config)
        if not os.path.exists(file_cfg):
            raise IOError(file_cfg)
    # parsing del file di configurazione
    logging.debug("Parsing configuration file '{0}'".format(file_cfg))
    config.read(file_cfg)
    # check if the config file has the required sections, if required
    if not check_required_sections:
        return config
    for section in REQUIRED_CONFIG_SECTIONS.keys():
        if parse_section(config, section) is False:
            logging.warning("""Section {0} does not exist in configuration """
                            """file '{1}'. Adding the missing section!""".format(
                            section, file_cfg))
            # add the missing section
            config.add_section(section)
            # add default key to the sections
            if REQUIRED_CONFIG_SECTIONS[section] is not None:
                for key, value in REQUIRED_CONFIG_SECTIONS[section].items():
                    config.set(section, key, value)
            # write config file
            write_config_file(config, config_filename=file_cfg)
    # lettura dei valori e mappatura dei valori
    #logging.debug("Sections in the config file: {0}".format(config.sections()))
    return config

def write_config_file(config, config_filename=None):
    if config_filename is None:
        config_filename = get_config_file()
    # write the config file
    with open(config_filename, 'w') as configfile:
        config.write(configfile)
    return config_filename

def create_config_file(config_filename, config):
    """create the configuration file if does not exist"""
    directory = os.path.dirname(config_filename)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(config_filename, 'w') as configfile:
        config.write(configfile)
        # Close the connection to the file
        configfile.close()
    # parsing del file di configurazione
    logging.debug("Created configuration file '{0}'".format(config_filename))
    return config_filename

################################################################################
############# FUNCTION TO TEST THE PRESENCE OF PANDOC SOFTWARE #################
################################################################################

def test_pandoc():
    """Test if pandoc is installed in the system"""
    python_version = sys.version_info[0]
    try:
        if python_version > 2:
            subprocess.run(["pandoc", "-v"])
        else:
            subprocess.call(["pandoc", "-v"])
        return True
    except OSError:
        return False
    else:
        return True
