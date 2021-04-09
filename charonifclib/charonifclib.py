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
############# IMPORTAZIONE MODULI STANDARD #####################################
################################################################################
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import platform
import subprocess
import datetime
import logging
import copy
from gettext import gettext as _
import xml.etree.ElementTree as ET
# retro-compatibility with Python 2.7
try:
    import configparser
except:
    import ConfigParser as configparser

################################################################################
############# IMPORTAZIONE MARKDOWN ############################################
################################################################################

import markdown

################################################################################
############# IMPORTAZIONE IFCOPENSHELL ########################################
################################################################################

is_64bits = sys.maxsize > 2**32
if is_64bits:
    x64="64 bit"
else:
    x64="32 bit"
python_version = float("{0}.{1}".format(sys.version_info[0], sys.version_info[1]))
# log a message to tell which python version we are using
logging.info("Using Python version{0} {1}".format(python_version, x64))

# try to import ifcopenshell if already installed on the system
try:
    import ifcopenshell
except ImportError:
    # try to guess the system configuration and import the correct library
    _platform = platform.system()
    # import different 'ifcopenshell' libraries depending on the system available
    if _platform == "Linux":
        if is_64bits:
            if python_version >= 2 and python_version < 3:
                import ifcopenshell27_x64 as ifcopenshell
            elif python_version >= 3:
                import ifcopenshell35_x64 as ifcopenshell
            else:
                raise ImportError
        else:
            if python_version >= 2 and python_version < 3:
                import ifcopenshell27 as ifcopenshell
            elif python_version >= 2 and python_version < 3:
                import ifcopenshell35 as ifcopenshell
            else:
                raise ImportError
    # Windows
    elif _platform == "Windows":
        import ifcopenshell35_win64 as ifcopenshell
    # MacOS
    elif _platform == "Darwin":
        import ifcopenshell35_mac as ifcopenshell
    else:
        raise ImportError

################################################################################
############# IMPORTAZIONE MODULI CUSTOM #######################################
################################################################################

# import helper function to manage project files
from . import get_data_path

# import the translation function
from .translator import word_translate, setup_language, get_language

# import preventa Lib module to create BOQ
from . import preventa_lib as Preventa

################################################################################
############# GLOBAL VARIABLES #################################################
################################################################################

UNDEFINED     = _("Undefined")
UNSET         = _("Unset")
DEFAULT_TITLE = _("Technical Specifications")
VERSION = "1.0"

################################################################################
############# CREATE A SET OF INTERNAL LIBRARY FROM OFFICIAL IFC DOC ###########
################################################################################

def SplitStr(stringa, pset=False):
    if stringa.startswith("Ifc"):
        stringa = stringa[3:]
    if stringa.endswith("Type"):
        stringa = stringa[:-4] + "s"
    elif stringa.startswith("Pset_"):
        stringa = stringa[5:] + "Properties"
    import re
    new_string = re.findall('[A-Z][^A-Z]*', stringa)
    return " ".join(new_string)

def importIFCdef(ifc4schemaFile, psdschema):
    #parse IFC schema
    tree = ET.parse(ifc4schemaFile)
    root = tree.getroot()
    IFCSchema = {"IfcTypes": list(),
                 "IfcObj": list(),
                 "DataType": list(), 
                 "UnitTypes": list()}
    for element in root:
        for key, value in element.items():
            if key == "name":
                if value.startswith("Ifc"):
                    if not value.endswith("Enum") and \
                       not value.endswith("-wrapper"):
                        if value.endswith("Type"):
                            if value not in IFCSchema["IfcTypes"]:
                                IFCSchema["IfcTypes"].append(value)
                            # also add its related IfcObject
                            objname = value[:-4]
                            if objname not in IFCSchema["IfcObj"]:
                                IFCSchema["IfcObj"].append(objname)
    # now parse PSD schema
    tree = ET.parse(psdschema)
    root = tree.getroot()
    # import DATA_TYPE from IFC schema
    for t in root[3][1][1][0]:
        IFCSchema["DataType"].append(list(t.attrib.values())[0])
    # import UNIT_TYPE from IFC schema
    for t in root[4][1][1][0]:
        IFCSchema["UnitTypes"].append(list(t.attrib.values())[0])
    return IFCSchema

def importIFCqto(ifc4schemaFile):
    IFCQto = dict()
    # open Qto files one by one
    for qto_file in os.listdir(ifc4schemaFile):
        # parse IFC schema
        tree = ET.parse(os.path.join(ifc4schemaFile, qto_file))
        root = tree.getroot()
        # get the IfcObj name
        IfcObject = root[4][0].text
        IFCQto[IfcObject] = list()
        # find alla associated quantity definition name
        QtoDefs = root.find("QtoDefs")
        QtoDef = QtoDefs.findall("QtoDef")
        for q in QtoDef:
            IFCQto[IfcObject].append(q.find("Name").text)
    return IFCQto

def importIFCpsd(ifc4schemaFile):
    IFCPset = dict()
    # open Qto files one by one
    for pset_file in os.listdir(ifc4schemaFile):
        # parse IFC schema
        tree = ET.parse(os.path.join(ifc4schemaFile, pset_file))
        root = tree.getroot()
        # get the IfcObj name
        IfcObject = root.find("Name").text
        IFCPset[IfcObject] = list()
        # find alla associated quantity definition name
        PropertyDefs = root.find("PropertyDefs")
        PropertyDef = PropertyDefs.findall("PropertyDef")
        for p in PropertyDef:
            IFCPset[IfcObject].append(p.find("Name").text)
    return IFCPset

# read the IFC4 schema and create a memory structure always accessible
IFCSCHEMA = importIFCdef(os.path.join(get_data_path(),'IFC4_ADD2.xsd'),
                         os.path.join(get_data_path(),'PSD_IFC4_TC1.xsd'))
IFCQTO  = importIFCqto(os.path.join(get_data_path(),'qto'))
IFCPSET = importIFCpsd(os.path.join(get_data_path(),'psd'))
################################################################################
############# PROJECT ERROR CLASS ##############################################
################################################################################

class CharonIfcError(Exception):
    """Classe per gestire le eccezioni della libreria IfcParser"""
    def __init__(self, message):
        date = datetime.datetime.now()
        self.message = "{0}: {1}".format(date, message)
        logging.error(self.message)

    def __str__(self):
        return repr(self.message)

################################################################################
############# Setup the Default Translation Language ###########################
################################################################################

def SetLanguage(lang):
    """This function setup the default language used to translate the 
    IFC documents"""
    # setup the translator module
    return setup_language(lang)

def GetLanguage():
    """Return the default language used to translate the IFC documents"""
    return get_language()

################################################################################
############# IfcParser MAIN CLASS #############################################
################################################################################

class IfcParser:
    """Main Parser class, with methods to read and enhance the data assets 
      See the example:
      http://www.buildingsmart-tech.org/ifc/IFC4/final/html/annex/annex-e/ifc/building_service_element_air-terminal.ifc.htm"""
    IfcSchema = None
      
    def __init__(self, filename):
        IfcParser.IfcSchema = IFCSCHEMA
        IfcParser.DataType = IFCSCHEMA["DataType"]
        self.filename = filename
        self.ifc_file = ifcopenshell.open(filename)
        self.ifc_objType  = IfcParser.IfcSchema["IfcTypes"]
        self.ifc_obj      = IfcParser.IfcSchema["IfcObj"]
        #################################################
        # data structure
        #################################################
        self.library = dict()
        self.objects_lib = dict()
        self.material_lib = dict()
        self.property_lib = dict()
        #################################################
        # parse the file and get the IFC version
        #################################################
        IfcSch = IfcCheck(filename)
        self.ifc_version = IfcSch.GetIfcSchema()
        logging.info("IFC file version: '{}'".format(self.ifc_version))
        if not IfcSch.IsSchemaCorrect():
            logging.error("""Attention IfcOpenShell schema '{0}' """
                          """doesn't match the IFC file schema '{1}'. """
                          """Errors may occour.""".format(self.ifc_version, 
                          IfcSch.GetIfcOpenShellSchema()))
        #################################################
        # parse the file for organizations
        #################################################
        self.organizations = list()
        try:
            org = self.ifc_file.by_type("IfcOrganization")
        except:
            logging.warning("No Organization found in the project.")
            org = None
        if org is not None:
            for o in org:
                self.organizations.append(o.Name)
        #################################################
        # Parse the Classification
        #################################################
        self.classification = None
        try:
            self.classification = self.ifc_file.by_type("IfcRelAssociatesClassification")
        except RuntimeError as err:
            raise CharonIfcError("{}: IfcRelAssociatesClassification".format(err))
        if len(self.classification) == 0 or self.classification is None:
            logging.warning("No Classification Available in the Project")
        #################################################
        # Create a list of objects and their related GUID
        #################################################
        for objname in self.ifc_obj:
            try:
                IfcRelDefines = self.ifc_file.by_type(objname)
            except RuntimeError as err:
                logging.debug("{0} {1}".format(objname,err))
            else:
                self.objects_lib[objname] = IfcRelDefines
        #################################################
        # Parse the file for object types to add
        #################################################
        IfcRelDefinesByType = self.ifc_file.by_type("IfcRelDefinesByType")
        if len(IfcRelDefinesByType) > 0:
            for elem in IfcRelDefinesByType:
                try:
                    RelatingType = elem.RelatingType
                except RuntimeError as err:
                    logging.error("{0} {1}".format(elem,err))
                else:
                    # create the new object
                    new_object = IfcObjectType(RelatingType)
                    # add the object classification
                    self.__obj_classification__(new_object)
                    # add the object to the memory structure
                    self.__add_object__(new_object)
        else:
            #if no IfcRelDefinesByType is defined look up directly IfcTypes
            logging.error("No IfcRelDefinesByType found.")
            logging.error("Trying to lookup other IfcTypes...")
            for ifctype in self.ifc_objType:
                try:
                    IfcByType = self.ifc_file.by_type(ifctype)
                    for IfcType in IfcByType:
                        new_object = IfcObjectType(IfcType)
                        # add the object classification
                        self.__obj_classification__(new_object)
                        # add the object to the memory structure
                        self.__add_object__(new_object)
                except RuntimeError as err:
                    logging.debug("{0} {1}".format(err,ifctype))
        #################################################
        # Add Defines By Properties properties if present
        #################################################
        try:
            IfcRelDefinesByProperties = self.ifc_file.by_type("IfcRelDefinesByProperties")
        except RuntimeError:
            logging.warning("IfcRelDefinesByProperties not found.")
        else:
            logging.debug("Extracting IfcRelDefinesByProperties.")
            # create a temporary memory structure to collect objects and their GUID
            listOfObj = dict()
            for DefProp in IfcRelDefinesByProperties:
                Name = DefProp.Name
                IfcPropertySetDefinition = DefProp.RelatingPropertyDefinition
                PropertySetName = IfcPropertySetDefinition.Name
                try:
                    RelatedObjects = DefProp.RelatedObjects
                except RuntimeError:
                    logging.warning("""No object has been associated to """
                                    """ {} Propery definition.""".format(Name))
                else:
                    if RelatedObjects is not None:
                       for obj in RelatedObjects:
                           #add object in a dictionary containing ids and obj
                           if obj.GlobalId not in listOfObj.keys():
                               listOfObj[obj.GlobalId] = (obj, [IfcPropertySetDefinition])
                           else:
                               listOfObj[obj.GlobalId][1].append(IfcPropertySetDefinition)
                           # get the complete list of associated properties
            # populate the array we will use to create the document
            for guid in listOfObj:
                ifcobj = listOfObj[guid][0]
                prop_list = listOfObj[guid][1]
                # create the new object
                new_object = IfcObject(ifcobj, prop_list)
                # add the object to the memory structure
                self.__add_object__(new_object,library=self.property_lib)
            # delete the temporary array
            del listOfObj
        
    def __add_object__(self, new_object, library=None):
        """Private method to add a new object in the library"""
        if library is None:
            library=self.library
        if new_object.type in library:
          list_p = library[new_object.type]
          list_p.append(new_object)
        else:
          library[new_object.type] = [new_object]
        return True

    def __obj_classification__(self, obj):
        """Private method to read and compile an array of classified objects"""
        if self.classification is None:
            logging.debug("No Classification Available for {}".format(obj))
        else:
            for prop in self.classification:
                name = prop.Name
                Description = prop.Description
                try:
                    RelatedObjects = prop.RelatedObjects
                except RuntimeError:
                    gid = prop.GlobalId
                    logging.debug("""Classification: RelatedObjects {} """
                                  """Entity not found.""".format(gid))
                else:
                    for item in RelatedObjects:
                        if item.GlobalId == obj.id:
                            RelatingClassification = prop.RelatingClassification
                            logging.debug("Classification Available: {0}".format(
                                         RelatingClassification))
                            code = RelatingClassification.ItemReference
                            desc = RelatingClassification.Name
                            obj.classification = IfcClassification(name, code, desc)

    def MarkUpText(self, title=None, 
                   type_blacklist=None, 
                   prop_blacklist=None,
                   ext_prop=False,
                   settings=None,
                   p_list=None):
        if p_list is None:
            if ext_prop:
                # Create a list of PROPERTIES and RELATED OBJECTS
                p_list = self.property_lib
            else:
                # Create the TECHNICAL SPECIFICATION
                p_list = self.library
        elif type(p_list) is not dict:
            raise CharonIfcError("p_list type is not a dictionary dict()")
        return str(CreateMarkUpText(p_list, title, type_blacklist,
                                    prop_blacklist, settings))
    
    def GetPropertiesList(self):
        return self.property_lib
        
    def GetSpecificationsList(self):
        return self.library
    
    def AecosimDataGroup(self, category_name=None):
        """Convert IFC files or Properties to AECOsim DataGroup items."""
        instanced_data = dict()
        # setup XML seed
        AecosimXMLseed = """<?xml version="1.0" encoding="Windows-1252"?>
                            <DataGroupSystem>
	                          <Version major="1" minor="0"/>
	                          <Units master="mm" sub="mm"/>
	                          <CatalogTypeExtensions></CatalogTypeExtensions>
	                          <CatalogItems></CatalogItems>
                            </DataGroupSystem>"""
        # setup the filename and write the new file
        filename = "{}.{}".format(os.path.splitext(self.filename)[0], "xml")
        with open(filename, "w") as f:
            f.writelines(AecosimXMLseed)
        tree = ET.parse(filename)
        root = tree.getroot()
        # get CatalogItems root
        CatalogItems = root.find("CatalogItems")
        # add catalogue extension items
        for tipologia in sorted(self.library.keys()):
            # setup the catalog Category name, if nothing is provided by
            # the user the program will try to set it up himself
            if category_name is None:
                cat_name = tipologia
                if cat_name.upper().startswith("IFC"):
                    cat_name = "{}".format(cat_name[3:])
                if cat_name.upper().endswith("TYPE"):
                    cat_name = "{}".format(cat_name[:-4])
            else:
               cat_name = str(category_name)
            for IfcOT in self.library[tipologia]:
                # Create sub-elements
                CatalogItem = ET.SubElement(CatalogItems, "CatalogItem")
                CatalogItem.set("type", cat_name)
                # setup the component name
                CatalogItem.set("name", IfcOT.name)
                Defaults = ET.SubElement(CatalogItem, "Defaults")
                # add each single object property
                if IfcOT.has_properties is not None:
                    for dfn, value in sorted(IfcOT.has_properties.items()):
                        # populate list of instance data definition to setup
                        # skip Pset_ definitions (Aecosim have them by default)
                        if not dfn.upper().startswith("PSET_"):
                            if cat_name in instanced_data.keys():
                                instanced_data[cat_name].append(dfn)
                            else:
                                instanced_data[cat_name] = [dfn]
                        # setup instance properties (Property definitions)
                        for prop in value:
                            (name, value, unit) = prop.print_property()
                            attr_dict = {"definition": dfn,
                                         "name":"{0}/@{1}".format(dfn,name),
                                         "value":value}
                            Property = ET.SubElement(Defaults, "Property", 
                                                     attrib=attr_dict)
        # get CatalogTypeExtensions root
        CatalogExtensions = root.find("CatalogTypeExtensions")
        # create the catalogue extensions
        for cat_n in instanced_data.keys():
            CatExt = ET.SubElement(CatalogExtensions,"CatalogTypeExtension")
            CatExt.set("type", cat_n)
            logging.warning("""Creating Instance Data Definitions required """
                            """for item: '{}'. These definitions will have """
                            """to be added to DataGroup Property Definition"""
                            """.""".format(cat_n))
            # finally create the instance data definitions
            for value in set(instanced_data[cat_n]):
                Instance = ET.SubElement(CatExt, "InstanceDataDefinition")
                Instance.set("definition", value)
                Instance.set("defType", "USER")
        # save the file
        tree.write(filename)
        return filename

    def GetItemsByProperty(self, prop_name, value):
        """Method to get a list of IFC Objects by proparty such as 
        "Manufacturer's name" or 'Description'."""
        objlist = list()
        logging.info("""Parsing IfCObjects to get a list of objects """
                     """with Property Name: '{}' and Value: '{}'""".format(
                     prop_name, value))
        # parse the library for all the objects
        for IfcObjectList in self.library.values():
            for IfcObject in IfcObjectList:
                if type(IfcObject.has_properties) is dict:
                    for PropertySet in IfcObject.has_properties.keys():
                        # check if property set has the prop we're looking for
                        for IfcProp in IfcObject.has_properties[PropertySet]:
                            p = IfcProp.print_property()
                            # wildcard '*' support
                            if value == "*": value = p[1]
                            # check property name and value
                            if p[0].upper() == prop_name.upper() and \
                               p[1].upper() == value.upper():
                                # add the object to the list
                                objlist.append(IfcObject)
                                logging.info("Found Object GID: {}".format(
                                              IfcObject.id))
        # create da dict with the list of objects and property as key
        d = {"{} - {}".format(prop_name, value): objlist}
        return d

################################################################################
############# BOQ CLASS ########################################################
################################################################################

class IfcBOQ:
    """Main Parser class, with methods to read and enhance the data assets 
      See the example:
      http://www.buildingsmart-tech.org/ifc/IFC4/final/html/annex/annex-e/ifc/building_service_element_air-terminal.ifc.htm"""
    IfcSchema = None
      
    def __init__(self, filename, output="csv", 
                 list_price=False, 
                 assolist=None,
                 add_concrete_rebars=False,
                 sort_by_space=False,
                 import_price_list=None,
                 select_by_property = None,
                 database_filename = None):
        global IFCSCHEMA
        IfcBOQ.IfcSchema = IFCSCHEMA
        IfcBOQ.DataType = IFCSCHEMA["DataType"]
        self.filename = filename
        self.ifc_file = ifcopenshell.open(filename)
        # open the database connection
        if database_filename is None:
            database_filename = ":memory:"
        self.boq = Preventa.Preventivo(database_filename)
        self.db = self.boq.get_database()
        # store the chosen options
        self.add_concrete_rebars = add_concrete_rebars
        self.sort_by_space = sort_by_space
        # if not None select a subsect of objects whose (proprety_name, value) 
        # match the chosen option
        if select_by_property is not None:
            if len(select_by_property) != 2:
                raise CharonIfcError("""select_by_property is not a tuple"""
                                     """ (property_name, value)""")
        self.select_by_property = select_by_property
        # import the price list
        self.import_price_list = import_price_list
        if import_price_list is not None:
            fileformat = os.path.splitext(import_price_list)[1]
            if os.path.exists(import_price_list):
                logging.info("Import file: '{}'".format(import_price_list))
                # import file
                if fileformat.upper() == ".PWE":
                    self.boq.import_from_primus_pwe(import_price_list)
                elif fileformat.upper() == ".XPWE":
                    pass
                elif fileformat.upper() == ".XML":
                    self.boq.import_XML(import_price_list)
                else:
                    logging.error("""Unable to import '{0}'. Unable to import"""
                                  """ file with extension '{1}' """.format(
                                  import_price_list, fileformat))
            else:
                raise IOError
        #create a list of types to use later
        (self.ifcTypes, self.listTypes) = self.__createListOfTypes__()
        # create a list of services and domains
        self.DomainNames = self.__listOfDomains__()
        # create a list of status types
        self.StatusNames = self.__listOfStatus__()
        # create a list of buildings
        (self.buildingName, self.objByBuilding) = self.__listOfObjBySpace__("IfcBuilding")
        # create a list of storey
        (self.storeyName, self.objByStorey) = self.__listOfObjBySpace__("IfcBuildingStorey")
        # create a list of spaces
        (self.spacesName, self.objBySpace) = self.__listOfObjBySpace__("IfcSpace")
        # create categories and chapters
        self.__createCategoriesAndChapters__()
        # create a list of objects to parse
        self.objList = self.__createListOfObj__()
        # if required update the BOQ with the tariff associations
        if assolist is not None:
            self.objList = self.__createBOQfromList__(assolist)
        # add the list of objects in the database
        self.boq.insert_articoli_computo(*self.objList)
        # if required create a list of associations
        self.__ofas__ = None
        if list_price:
            self.__ofas__ = self.__createListOfAssociations__()
        # create the BOQ by storey
        self.__ofln__ = self.__createBillOfQuantities__(output)
        # shut down database connection
        self.boq.connection_shutdown()

    def __createListOfTypes__(self):
        """create a list of IfcElementType Objects"""
        #create the array to store the data
        ifcTypes = dict()
        listTypes = dict()
        i = 1
        # Parse the file for object types to add
        IfcRelDefinesByType = self.ifc_file.by_type("IfcRelDefinesByType")
        for elem in IfcRelDefinesByType:
            try:
                RelatingType = elem.RelatingType
                RelatedObjects = elem.RelatedObjects
            except RuntimeError as err:
                logging.error("{0} {1}".format(elem,err))
            else:
                # create an array with unique number and IfcTypeName
                name = word_translate(RelatingType.is_a())
                if name not in ifcTypes.keys():
                    ifcTypes[name] = i
                    # advance the types index
                    i+=1
                # create an array with typeID and list of objects
                for IfcObject in RelatedObjects:
                    # add the object to the memory structure
                    if RelatingType.GlobalId in listTypes.keys():
                        listTypes[RelatingType.GlobalId].append(IfcObject)
                    else:
                        listTypes[RelatingType.GlobalId] = [IfcObject]
        ########################################################################
        # add the IfcProduct Objects categories to the list
        ########################################################################
        IfcProduct = self.ifc_file.by_type("IfcProduct")
        for IfcObject in IfcProduct:
            # create an array with unique number and IfcTypeName
            name = word_translate(IfcObject.is_a())
            if name not in ifcTypes.keys():
                ifcTypes[name] = i
                # advance the types index
                i+=1
            # create an array with typeID and list of objects
            if IfcObject.GlobalId in listTypes.keys():
                listTypes[IfcObject.GlobalId].append(IfcObject)
            else:
                listTypes[IfcObject.GlobalId] = [IfcObject]
        return (ifcTypes, listTypes)

    def __listOfDomains__(self):
        """create an array of atorey and their associated IfcObjects"""
        # for now we create a list of domains 'manually'
        DomainNames = {1: "Architectural",
                       2: "Structural",
                       3: "HVAC",
                       4: "Electric"}
        return DomainNames
    
    def __listOfStatus__(self):
        """..."""
        # for now we create a static list of Status types
        Status = {"NEW":       1,
                  "EXISTING":  2,
                  "DEMOLISH":  3,
                  "TEMPORARY": 4}
        return Status

    def __listOfObjBySpace__(self, space_type):
        """create an array of space types and their associated IfcObjects"""
        storeyName = dict()
        objByStorey = dict()
        s = 1 # storey or building index
        # create the BOQ by storey or building
        IfcByType = self.ifc_file.by_type(space_type)
        for SpaceType in IfcByType:
            storeyName[s] = SpaceType.Name
            for RelSpCon in SpaceType.ContainsElements:
                for element in RelSpCon.RelatedElements:
                    objByStorey[element] = s
            # advance the storey counter
            s+=1
        return (storeyName, objByStorey)

    def __createCategoriesAndChapters__(self):
        """Function o create categories and chapters in the BOQ database"""
        # superchapter: IfcDomain (Electrical, HVAC, etc.)
        for key, name in self.DomainNames.items():
            self.boq.insert_capitoli_categorie("Supercapitolo", name)
        # chapter: IfcTypes
        for name, key in self.ifcTypes.items():
            self.boq.insert_capitoli_categorie("Capitolo", name)
        # subchapter: Status
        InverseStatusDict = {v: k for k, v in self.StatusNames.items()}
        for key, name in sorted(InverseStatusDict.items()):
            self.boq.insert_capitoli_categorie("Subcapitolo", name)
        # create super categories: Building
        for key, name in self.buildingName.items():
            self.boq.insert_capitoli_categorie("Supercategoria", name)
        # create categories: storey
        for key, name in self.storeyName.items():
            self.boq.insert_capitoli_categorie("Categoria", name)
        # create subcategories: systems or spaces
        if self.sort_by_space:
            for key, name in self.spacesName.items():
                self.boq.insert_capitoli_categorie("Subcategoria", name)
        else:
            for system in self.ifcTypes.keys():
                self.boq.insert_capitoli_categorie("Subcategoria", system)
            # update the names
            for name, key in self.ifcTypes.items():
                self.boq.update_capitoli_categorie(key, "Subcategoria", name)
        # we're done, return
        return
          
    def __createListOfObj__(self):
        # create the array to store the data
        objList = list()
        IfcObj = self.ifc_file.by_type("IfcObject")
        for obj in IfcObj:
            if obj.is_a() == "IfcProject":
                continue
            elif obj.is_a() == "IfcSite":
                continue
            elif obj.is_a() == "IfcBuilding":
                continue
            elif obj.is_a() == "IfcBuildingStorey":
                continue
            elif obj.is_a() == "IfcSystem":
                continue
            else:
                # define base quantity and measure unit
                desc = str()
                IfcQuantityDict = dict()
                RelatingType = None
                Status = None
                # flag to skip obj addition to the list if we don'want to
                AddToList = True
                # check if all the objects have a RelatingType
                for RelDef in obj.IsDefinedBy:
                    if RelDef.is_a() == "IfcRelDefinesByType":
                        # create an article using the RelatingType definition
                        if RelDef.RelatingType.GlobalId in self.listTypes.keys():
                            RelatingType = RelDef.RelatingType
                        else:
                            logging.error("{} has no RelatingType".format(RelDef))
                    elif RelDef.is_a() == "IfcRelDefinesByProperties":
                        IfcPropertySetDef = RelDef.RelatingPropertyDefinition
                        # check if the obj has a related quantity set
                        if IfcPropertySetDef.is_a() == "IfcElementQuantity":
                            # extract quantities and volume
                            IfcQuantityDict = self.__get_quantity__(obj,
                                              IfcPropertySetDef.Quantities,
                                              IfcQuantityDict)
                        elif IfcPropertySetDef.is_a() == "IfcPropertySet":
                            # add properties to the article description
                            properties = ParsePropertySet(IfcBOQ.DataType,
                                                          IfcPropertySetDef)
                            # add each single object property
                            if len(properties.keys()) > 0:
                                for name, list_p in properties.items():
                                    # translate the info type 
                                    name = word_translate(name)
                                    desc += "".join(["\n",name,"\n"])
                                    for p in list_p:
                                        x = p.print_property()
                                        desc += "* {0}: {1} {2}{3}".format(
                                                 x[0], x[1], x[2], "\n")
                                        # check the status property
                                        if x[0].upper() == "STATUS":
                                            Status = x[1]
                                        # check if we are selectiong only the 
                                        # obj matching a property and skip it
                                        if self.select_by_property is not None:
                                            (n,v) = self.select_by_property
                                            if v == "*": v = x[1]
                                            if x[0].upper() == n.upper() \
                                               and x[1].upper() == v.upper():
                                                AddToList = True
                                            else:
                                                AddToList = False
                        # if no property is recognized rise an error
                        else:
                            raise CharonIfcError("""Unimplemented"""
                                  """ PropertySetDef: {}""".format(RelDef))
                    # if we have no IfcRelDefinesByType or IfcRelDefinesByProperties
                    # raise an error
                    else:
                        raise CharonIfcError("Unable to define {}".format(RelDef))
                # check if the item is flagged to be added
                if AddToList:
                    # select the right Quantity
                    logging.info("{0} GUID:{1} {2}".format(obj.is_a(),
                                                           obj.GlobalId, 
                                                           IfcQuantityDict))
                    (Q, UM) = self.SelectIfcQuantity(obj, IfcQuantityDict)
                    # create the article
                    art=self.__boqElement__(RelatingType,obj,Q,UM,desc,Status)
                    # append the object to the list
                    objList.append(art)
                    # for structural elements like IfcBeam, IfcWall, etc
                    # add one or more article to account for rebars
                    # and concrete forms
                    if self.add_concrete_rebars is True:
                        self.__concreteRebars__(objList, obj, RelatingType, 
                                               IfcQuantityDict, desc, Status)
                else:
                    logging.info("""Selecting IfCObjects with Property Name:"""
                                 """'{0}' and Value '{1}'. IfCObject GID:"""
                                 """: {2} skipped.""".format(
                                 self.select_by_property[0],
                                 self.select_by_property[1],
                                 obj.GlobalId))
        # return the object list
        return objList

    def __get_quantity__(self, obj, quantities, IfcQuantityDict):
        """Exctract quantities from the IfcElementQuantity"""
        # extract each single property
        for prop in quantities:
            name = prop.Name
            if prop.is_a() == "IfcQuantityLength":
                value = prop.LengthValue
                unit = "m"
            elif prop.is_a() == "IfcQuantityArea":
                value = prop.AreaValue
                unit = "m2"
            elif prop.is_a() == "IfcQuantityVolume":
                value = prop.VolumeValue
                unit = "m3"
            elif prop.is_a() == "IfcQuantityCount":
                value = prop.CountValue
                unit = "N"
            elif prop.is_a() == "IfcQuantityWeight":
                value = prop.WeightValue
                unit = "kg"
            elif prop.is_a() == "IfcQuantityTime":
                value = prop.TimeValue
                unit = "h"
            else:
               raise CharonIfcError ("Unknown Quantity Type {}".format(prop.is_a()))
            # add name, quantity and unit to the collection
            IfcQuantityDict[name] = (value, unit)
        return IfcQuantityDict
    
    def SelectIfcQuantity(self, obj, IfcQuantityDict):
        """Exctract quantities from the IfcElementQuantity"""
        # default values is 1 and default unit N
        formula, value, unit = (None, 1, "")
        # check if obj is a tring or an IfcObject
        if getattr(obj, "is_a", None) is not None:
            rule_name = obj.is_a()
        elif type(obj) is str:
            rule_name = obj
        else:
            raise CharonIfcError("SelectIfcQuantity {} is unknown type".format(obj))
        # transform IfcQuantityDict to uppercase for safer comparison
        # with user entered data
        UpperCaseDict = {k.upper(): v for k, v in IfcQuantityDict.items()}
        # function to parse string and tell if it is a number
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        # function to parse and evaluate equations
        def EvaluateFormula(t, unit):
            """This function provide an equation evaluator, so the user
            can enter arbitrary Quantities (Qto) formula and the program 
            will evaluate the calcualations (e.g. NetVolume * Lenght)"""
            eq = IfcObjectsCalculationRules[t]
            eq_list = IfcObjectsCalculationRules[t].replace(",", ".").split()
            for var in eq_list:
                # every word which is not a math operator is a variable
                # and its value will be looked up in IfcQuantityDict
                if var not in ["/","*","-","+"]:
                    # check if the variable is in IfcQuantityDict, uppercase
                    if var.upper() in UpperCaseDict.keys():
                        # if the variable is in calculation rules,
                        # then get the related IfcQuantity
                        (v, u) = UpperCaseDict[var.upper()]
                        logging.info("Var found: {} {} {}".format(var,v,u))
                        # execute the variable assignment
                        exec("{} = {}\n".format(var, str(v)), locals())
                        # add the unit to the global unit
                        unit += u
                    elif is_number(var):
                        pass # we will evaluate numbers later
                    else:
                        # the variable is not in IfcQuantity dict
                        # remove the broken variable and replace it with 1
                        # and reassign the new equation string
                        eq = eq.replace(var,"1")
                        logging.error("""Quantity: '{}' not available. The """
                                      """new equation to evaluate will be: """
                                      """'{}'""".format(var,eq))
                else:
                    # add the math operator to the units list
                    unit += var
            # finally evaluate the string and return the total
            f = eval(eq)
            logging.info("Evaluated string: {}".format(f))
            return (eq, f, unit)
        # if the Obj is in the dictionary exit the loop
        if rule_name in IfcObjectsCalculationRules.keys():
            formula, value, unit = EvaluateFormula(rule_name, unit)
        else:
            logging.info("{} not in Calculation Rules".format(rule_name))
        # check if the final unit is empty and provide a default unit
        if unit == "":
            unit = "N"
        # debug message
        logging.info("{}: Formula: '{}' Value:'{}' unit:'{}'".format(
                     rule_name, formula, value, unit))
        return (value, unit)

    def __boqElement__(self, IfcTypeObject, IfcObject, Q, UM, desc, status):
        """create an instance ArticoloComputo for the BOQ"""
        # if there is no IfcTypeObject related then the object has its own
        # article and we use IfcObject to define name, desc, type, etc.
        if IfcTypeObject is None:
            Obj = IfcObject
        else:
            Obj = IfcTypeObject
        # setup the tag
        tar = Obj.GlobalId
        # setup the object name
        name = Obj.Name
        ifctype = Obj.is_a()
        # setup the description
        if Obj.Description is None:
            desc = "{} - {}".format(name, desc)
        else:
            desc = "{} - {} - {}".format(name, Obj.Description, desc)
        ### EPU STRUCTURE ######################################################
        # setup chapter and categories
        supcap = 0
        if IsIfcElectricalDomain(ifctype):
            supcap = 4
        elif IsIfcHVACDomain(ifctype):
            supcap = 3
        elif IsIfcPlumbingFireProtectionDomain(ifctype):
            supcap = 3
        elif IsIfcBuildingControlDomain(ifctype):
            supcap = 4
        elif IsIfcStructuralElementsDomain(ifctype):
            supcap = 2
        elif IsIfcSharedBLDElementsDomain(ifctype):
            supcap = 1
        else:
            logging.debug("No Domain (super-chapter) found for {}".format(
                          ifctype))
        # setup the category (IfcTypeObject)
        cap = self.ifcTypes.get(word_translate(ifctype), 0)
        # setup the sub-category (Objects Status)
        subcap = 0
        if status is not None and status.upper() in self.StatusNames.keys():
            subcap = self.StatusNames[status.upper()]
        elif status is None:
            pass # no action required, but skip outputting a debug message
        else:
            logging.debug("Unknown Status (subcategory): {}".format(status))
        ### BOQ STRUCTURE ######################################################
        # find the the object's building number
        supcat = 0
        for key, building in self.objByBuilding.items():
            if IfcObject.GlobalId == key.GlobalId:
                supcat = building
        # find the the object's storey number
        cat = 0
        for key, storey in self.objByStorey.items():
            if IfcObject.GlobalId == key.GlobalId:
                cat = storey
        # choose between BOQ by system or by Space
        subcat = 0
        if self.sort_by_space:
            # find the correct match between space and object
            for key, space in self.objBySpace.items():
                if IfcObject.GlobalId == key.GlobalId:
                    subcat = space
        else: 
            # find the correct match between system and object
            subcat = self.ifcTypes.get(word_translate(ifctype), 0)
        ### CREATE BOQ OBJECT ##################################################
        # create a new article
        article = Preventa.ArticoloComputo(self.db, 
                                           supcap, #supercapitolo
                                           cap,    #capitolo
                                           subcap, #subcapitolo
                                           supcat, #supercategoria
                                           cat,    #categoria
                                           subcat, #subcategoria 
                                           tar,    #tariffa 
                                           descrizione_codice=name, 
                                           descrizione_voce=ifctype,
                                           descrizione_estesa=desc, 
                                           unita_misura=UM,
                                           quantita=Q)
        # setup measure annotation, adding the object GUID and name
        article.note = "{0} - GlobalID: {1}".format(IfcObject.Name,
                                                    IfcObject.GlobalId)
        # return the article
        return article

    def __concreteRebars__(self, objList, obj, RelatingType, 
                          IfcQuantityDict, desc, status):
        """This function adds concrete rebars and Concrete Forms to elements"""
        ifc_list = ['IfcBeam', 'IfcSlab', 'IfcSlab', 'IfcWall', 'IfcStair']
        if obj.is_a() in ifc_list:
            # * Rebar's quantity (Rv)
            #   Rv (kg) = Cv*Rebar's ratio of concrete
            (Q, UM) = self.SelectIfcQuantity("{}-Rebars".format(obj.is_a()),
                                             IfcQuantityDict)
            # create the article for rebars
            rebar = self.__boqElement__(RelatingType,obj,Q,UM,desc,status)
            rebar.tariffa += "Rebar"
            rebar.descrizione_estesa = _("Rebar {}").format(desc)
            rebar.note = _("Rebar for {}").format(rebar.note)
            # * Form's quantity (Fv)
            #   Fv (m2) = Cv*Form's ratio of concrete
            (Q, UM) = self.SelectIfcQuantity("{}-Forms".format(obj.is_a()),
                                             IfcQuantityDict)
            # create the article for concrete forms
            forms = self.__boqElement__(RelatingType,obj,Q,UM,desc,status)
            forms.tariffa += "ConcreteForms"
            forms.descrizione_estesa = _("Concrete Forms {}").format(desc)
            forms.note = _("Concrete Forms for {}").format(forms.note)
            # append objects to the list
            objList.append(rebar)
            objList.append(forms)
            logging.info("Added Rebars & Concrete Forms to {}".format(obj.GlobalId))

    def __createBillOfQuantities__(self, output):
        """create a BILL OF QUANTITIES from stored Data"""
        # setup the default filename
        filename = os.path.splitext(self.filename)[0]
        # export to CSV or PWE or SQL dumpfile
        if output == "pwe":
            filename = filename+".pwe"
            self.boq.export_to_primus_pwe(filename)
        elif output == "xpwe":
            filename = filename+".xpwe"
            self.boq.export_to_primus_xpwe(filename, 
                                           elenco_prezzi=self.import_price_list)
        elif output == "sql":
            filename = filename+".sql"
            self.boq.export_to_dumpfile(filename)
        else:
            filename = filename+".csv"
            self.boq.export_computo_to_csv(filename,
                                           stampa_descr_estesa =True, 
                                           stampa_descr_breve = True, 
                                           stampa_note = True)
        return filename
    
    def __createListOfAssociations__(self):
        """Create a CSV file outputting a list of prices ready to associate 
        a price list unit from an pre-made list of prices"""
        # setup the default filename
        filename = "{}.cfg".format(os.path.splitext(self.filename)[0])
        # get the list of prices
        price_list = self.boq.epu_rows_list()
        # create the format "container", inizializza il parser
        config = configparser.ConfigParser(allow_no_value=True)
        # make configparse case-sensitive
        config.optionxform = lambda option: option
        # check if the config file has the required sections
        for item in price_list:
            # create a section for each element and add a description
            # each section name will be: "IfcType@GlobalId
            # e.g. 'IfcLightingFixture@2J6eKsrBz0WAC986WWrkJt'
            section = "{0} {1}".format(item[5],item[0])
            # add the missing item
            config[section] = {"description":"{} ({})".format(item[4],item[5]),
                               "unit": item[7],
                               "cost": "0",
                               "tariffa1": "1"}
        # create a new parser with a sorted dictionary
        from collections import OrderedDict
        new_dict = OrderedDict(sorted(config.items(), key=lambda t: t[0]))
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.read_dict(new_dict)
        # save the "container" in a text file
        with open(filename, 'w') as configfile:
            # Write ini file
            parser.write(configfile)
        return filename

    def __createBOQfromList__(self, filename):
        """Create a BOQ file from a list of associated quantities elements"""
        # read the config file using configparser
        config = configparser.ConfigParser(allow_no_value=True)
        # make configparse case-sensitive
        config.optionxform = lambda option: option
        try:
            config.read(filename)
        except UnicodeDecodeError as err:
            print ("""Wrong format. Try to save the document"""
                   """ in UTF-8 format{}""".format(err))
        # create a list of GlobalID in the config file
        guid_list = dict()
        # for each section check if we have more than 1 key required
        for section in config.sections():
            try:
                ifctype, guid = section.split()
                # create a list of guid to check against each art in objList
                guid_list[guid] = ifctype
            except ValueError as err:
                logging.error("Section not recognized: {}".format(section))
                continue
        # create a new list of object to populate
        new_objlist = list()
        # parse the list of objects to check if there is an art to modify
        for i,art in enumerate(self.objList):
            # if the parsed element has tariffa == section name
            if art.tariffa in guid_list.keys():
                # find out the config parser section and get all the keys
                section = "{} {}".format(guid_list[art.tariffa], art.tariffa)
                # we check the unit of measure and update if needed
                try:
                    um = config[section]["unit"]
                    if um != art.unita_misura:
                        self.objList[i].unita_misura = um
                except KeyError as err:
                    logging.error(err)
                # update the cost if != 0
                try:
                    cost = ParseFloat(config[section]["cost"])
                    if cost != 0:
                        self.objList[i].costo = cost
                except KeyError as err:
                    logging.error(err)
                # parse all the other keys except 'unit or 'description'
                # and change the article in the original list self.objList
                for tar, quant in config[section].items():
                    if tar in ["unit", "description", "cost"]:
                        continue
                    logging.info("Parsing section {0} {1} {2}".format(
                                  section, tar, quant))
                    # transform quant in an integer or raise an error
                    quant = ParseFloat(quant)
                    # for each key we add a new article in new_objlist
                    # important: we need to do a deep copy of the object!
                    newart = copy.copy(self.objList[i])
                    newart.tariffa = tar
                    newart.quantita = self.objList[i].quantita*quant
                    # append to the list
                    new_objlist.append(newart)
                    logging.debug("Article ADDED, with Tariff: {0}, "
                                  "and Quantity: {1}".format(tar,quant))
            # if the article doesn't match we add it back unchanged
            else:
                # append to the list
                new_objlist.append(art)
                logging.debug("Article NOT CHANGED: {0}".format(art.tariffa))
        # return the BOQ filename 
        return new_objlist
        
    def GetOutputFile(self):
        """return the output filename"""
        return self.__ofln__

    def GetAssociationFile(self):
        """This function return a string with the filename used by
        CreateListOfAssociations function from IfcBOQ class. This function can 
        be called from a GUI in order to know the filename before it is created.
        (e.g. for example to check if already exist and avoid an override)."""
        return self.__ofas__

def ParseFloat(value):
    # get the quantity or raise an exception
    try:
        return float(value)
    except ValueError:
        raise CharonIfcError("Cannot convert to float Value {}".format(value))

################################################################################
############# IfcCheck MAIN CLASS ##############################################
################################################################################

class IfcCheck:
    """Check an IFC file against IfcOpenShell schema and tell wether they
    match or differ."""
    
    def __init__(self, filename):
        self.ifc_version = str()
        self.schema = ifcopenshell.schema_identifier
        # parse the file and get the IFC version
        self.ifc_version = ''
        with open(filename, "r") as f:
            # check if we fing a string atarting with "FILE_SCHEMA"
            for line in f.readlines():
                if line.startswith("FILE_SCHEMA"):
                    for v in line.split("'"):
                        if v.upper().startswith("IFC"):
                            self.ifc_version = v
                    break
        # if searching return nothing log an error
        if self.ifc_version == '':
            logging.error("Unable to detect IFC file version.")
        
    def GetIfcSchema(self):
        return self.ifc_version
        
    def GetIfcOpenShellSchema(self):
        return self.schema
        
    def IsSchemaCorrect(self):
        return self.ifc_version.upper() == self.schema.upper()

################################################################################
############# FUNCTION TO GET/SET AN OBJECT TYPE DOMAIN ########################
################################################################################

def SetCalculationRules(ifctypedict):
    """Setup the Ifc Objects Calculation Rules"""
    global IfcObjectsCalculationRules
    IfcObjectsCalculationRules = ifctypedict

def IsIfcBuildingControlDomain(IfcTypeObject):
    """Check if the IfcType is in Building Control Domain list"""
    return IfcTypeObject in IfcBuildingControlDomain

def SetIfcBuildingControlDomain(ifctype):
    """Setup the Building control Domain"""
    global IfcBuildingControlDomain
    IfcBuildingControlDomain = ifctype

def IsIfcElectricalDomain(IfcTypeObject):
    """Check if the IfcType is in Electrical Domain list"""
    return IfcTypeObject in IfcElectricalDomain

def SetIfcElectricalDomain(ifctype):
    """Setup the Electrical Domain"""
    global IfcElectricalDomain
    IfcElectricalDomain = ifctype

def IsIfcHVACDomain(IfcTypeObject):
    """Check if the IfcType is in HVAC Domain list"""
    return IfcTypeObject in IfcHVACDomain

def SetIfcHVACDomain(ifctype):
    """Setup the HVAC Domain"""
    global IfcHVACDomain
    IfcHVACDomain = ifctype

def IsIfcPlumbingFireProtectionDomain(IfcTypeObject):
    """Check if the IfcType is in Plumbing Fire Protection Domain list"""
    return IfcTypeObject in IfcPlumbingFireProtectionDomain

def SetIfcPlumbingFireProtectionDomain(ifctype):
    """Setup the Plumbing Fire Protection Domain"""
    global IfcPlumbingFireProtectionDomain
    IfcPlumbingFireProtectionDomain = ifctype

def IsIfcStructuralElementsDomain(IfcTypeObject):
    """Check if the IfcType is in Structural Elements Domain list"""
    return IfcTypeObject in IfcStructuralElementsDomain

def SetIfcStructuralElementsDomain(ifctype):
    """Setup the Structural Elements Domain"""
    global IfcStructuralElementsDomain
    IfcStructuralElementsDomain = ifctype

def IsIfcSharedBLDElementsDomain(IfcTypeObject):
    """Check if the IfcType is in Shared Elements Domain list"""
    return IfcTypeObject in IfcSharedBLDElementsDomain

def SetIfcSharedBLDElementsDomain(ifctype):
    """Setup the Shared Elements Domain"""
    global IfcSharedBLDElementsDomain
    IfcSharedBLDElementsDomain = ifctype

################################################################################
############# IfcObjectType CLASS ##############################################
################################################################################

class IfcObjectType(IfcParser):
    """Classe per gestire gli oggetti contenuti in un file IFC"""
    def __init__(self, objtype):
        self.objtype = objtype
        self.type = objtype.is_a()
        # ENTITY IfcRoot
        # unicode conversion for Python 2.6 compatibility
        self.name = UnicodeTest(objtype.Name)
        # to avoid errors later name cannot be NoneType
        if self.name is None:
            self.name = UNDEFINED
        # unicode conversion for Python 2.6 compatibility
        self.id = UnicodeTest(objtype.GlobalId) #the product Global identification number
        self.owner = objtype.OwnerHistory
        # unicode conversion for Python 2.6 compatibility
        self.description = UnicodeTest(objtype.Description)
        if self.description is None:
            self.description = "-"
        # ENTITY IfcType
        if hasattr(objtype, "PredefinedType"):
            self.predefined_type = UnicodeTest(objtype.PredefinedType)
        else:
            self.predefined_type = None
        if self.predefined_type is None:
            self.predefined_type = UNSET
        # ENTITY IfcTypeObject
        self.applicable_occurrence = objtype.ApplicableOccurrence
        # add property list to the object
        PropertySets = objtype.HasPropertySets
        if PropertySets is not None:
            self.has_properties = ParsePropertySet(IfcParser.DataType,
                                                   *PropertySets)
        else:
            #display a warning if no property is set
            logging.warning("ObjectType {0} Id {1} has no properties set.".format(
                            self.name, self.id))
            self.has_properties = None
        # ENTITY IfcTypeProduct
        self.representation_maps = objtype.RepresentationMaps
        self.tag = UnicodeTest(objtype.Tag)
        if self.tag is None:
            self.tag = str()
        # ENTITY IfcElementType
        if hasattr(objtype, "ElementType"):
            self.element_type = objtype.ElementType
        else:
            self.element_type = None
        #ENTITY IfcObjectType
        # Object Uniformat classification
        self.classification = None
        # ENTITY INVERSE IfcObjectDefinition
        #add associated properties to the object
        self.has_associations = self.get_associations()

    def add_property(self, pset, key, value):
        """method to add a property in a PropertySet"""
        single_prop = IfcProperty(key)
        single_prop.nominalvalue = value
        if pset in self.has_properties.keys():
            self.has_properties[pset].append(single_prop)
        else:
            self.has_properties[pset] = [single_prop]

    def property_exist(self, pset, key):
        """method to detect if a property already exist in a PropertySet"""
        if len(self.has_properties.keys()) > 0:
            for existing_pset in self.has_properties.keys():
                # parse each single property stored and check against key value
                for single_property in self.has_properties[existing_pset]:
                    if single_property.name.upper() == key.upper():
                        return True
                    else:
                        continue
        # if the obj has no properties then return false
        else:
            return False
  
    def get_associations(self):
        """method to lookup and add associated properties to the IfcObjectType"""
        asso_prop = dict()
        # the HasAssociations inverse attribut allow to access the 
        # IfcRelAssociatesMaterial to access the Materials associated to the object
        try:
            HasAssociations = self.objtype.HasAssociations
        except RuntimeError:
            gid = self.objtype.GlobalId
            logging.error("HasAssociations {} Entity not found".format(gid))
            return None
        for associate_property in HasAssociations:
            GlobalId = associate_property.GlobalId
            OwnerHistory = associate_property.OwnerHistory
            Name = associate_property.Name
            Description = associate_property.Description
            RelatedObjects = associate_property.RelatedObjects
            if associate_property.is_a("IfcRelAssociatesApproval"):
                RelatingLibrary = associate_property.RelatingApproval
            elif associate_property.is_a("IfcRelAssociatesClassification"):
                RelatingLibrary = associate_property.RelatingClassification
                asso_prop["IfcClassificationReference"] = list()
            elif associate_property.is_a("IfcRelAssociatesConstraint"):
                RelatingLibrary = associate_property.RelatingConstraint
            elif associate_property.is_a("IfcRelAssociatesDocument"):
                RelatingLibrary = associate_property.RelatingDocument
            elif associate_property.is_a("IfcRelAssociatesLibrary"):
                RelatingLibrary = associate_property.RelatingLibrary
                asso_prop["IfcLibraryReference"] = list()
            elif associate_property.is_a("IfcRelAssociatesMaterial"):
                RelatingLibrary = associate_property.RelatingMaterial
                asso_prop["IfcMaterialList"] = list()
            else:
                RelatingLibrary = None
                logging.error("Associate porperty '{}' of unknown type.".format(Name))
            # get properties associated to RelatingLibrary
            if RelatingLibrary is not None:
                if RelatingLibrary.is_a() == "IfcMaterial":
                    asso_prop["IfcMaterialList"].append(RelatingLibrary.Name)
                elif RelatingLibrary.is_a() == "IfcMaterialList":
                    for Mat in RelatingLibrary.Materials:
                        # add the materials name to the list of properties
                        asso_prop["IfcMaterialList"].append(Mat.Name)
                elif RelatingLibrary.is_a() == "IfcMaterialLayerSetUsage":
                    pass # ignored for now
                elif RelatingLibrary.is_a() == "IfcMaterialLayerSet":
                    for MaterialLayer in RelatingLibrary.MaterialLayers:
                        Mat = MaterialLayer.Material
                        # add the materials name to the list of properties
                        asso_prop["IfcMaterialList"].append(Mat.Name)
                    asso_prop["IfcMaterialList"].append(Mat.Name)
                elif RelatingLibrary.is_a() == "IfcMaterialLayer":
                    Mat = RelatingLibrary.Material
                    # add the materials name to the list of properties
                    asso_prop["IfcMaterialList"].append(Mat.Name)
                elif RelatingLibrary.is_a() == "IfcLibraryReference":
                    loc = RelatingLibrary.Location
                    ir = RelatingLibrary.ItemReference
                    Name = RelatingLibrary.Name
                    lib = "{0}, {1} ({2})".format(ir, Name, loc)
                    # add the library name to the list of properties
                    asso_prop["IfcLibraryReference"].append(lib)
                elif RelatingLibrary.is_a() == "IfcClassificationReference":
                    loc = RelatingLibrary.Location
                    ir = RelatingLibrary.ItemReference
                    Name = RelatingLibrary.Name
                    cls = "{0}, {1} ({2})".format(ir, Name, loc)
                    asso_prop["IfcClassificationReference"].append(cls)
                else:
                    logging.error("{} is not a IfcMaterial".format(RelatingLibrary))
        return asso_prop

################################################################################
############# IfcObject CLASS ##################################################
################################################################################

class IfcObject(IfcParser):
    """Classe per gestire gli oggetti contenuti in un file IFC"""
    def __init__(self, obj, PropertySets=None):
        self.objtype = obj
        self.type = obj.is_a()
        # ENTITY IfcRoot
        # unicode conversion for Python 2.6 compatibility
        self.name = UnicodeTest(obj.Name)
        # to avoid errors later name cannot be NoneType
        if self.name is None:
            self.name = UNDEFINED
        # unicode conversion for Python 2.6 compatibility
        self.id = UnicodeTest(obj.GlobalId) #the product Global ID
        self.owner = obj.OwnerHistory
        # unicode conversion for Python 2.6 compatibility
        self.description = UnicodeTest(obj.Description)
        if self.description is None:
            self.description = "-"
        # ENTITY IfcType
        self.predefined_type = UnicodeTest(obj.ObjectType)
        if self.predefined_type is None:
            self.predefined_type = UNSET
        # Object Uniformat classification
        self.classification = None
        # add property list to the object
        if PropertySets is not None:
            self.has_properties = ParsePropertySet(IfcParser.DataType,
                                                   *PropertySets)
        else:
            # display a warning if no property is set
            logging.warning("Object: {0} Id {1} has no properties set.".format(
                            self.name, self.id))
            self.has_properties = None
        # ENTITY INVERSE IfcObjectDefinition
        # add associated properties to the object
        self.has_associations = self.get_associations()
        # properties not mapped: IsDecomposedBy, Phase, HasAssignments, Decomposes
        
    def get_associations(self):
        """method to lookup and add associated properties to the IfcObject"""
        return IfcObjectType.get_associations(self)
        
################################################################################
############# IfcProperty CLASS ################################################
################################################################################

class IfcProperty:
    """Classe per memorizzare le proprietà IFC"""
    def __init__(self, name):
        self.name = name
        self.description = None
        self.nominalvalue = None
        self.unit = None
        self.upper_bound = None
        self.lower_bound = None
        self.EnumerationValues = list()
        self.EnumerationReference = None
        self.type = None

    def print_property (self):
        value = str()
        unit = str()
        name = word_translate(self.name)
        # setup the unit
        if self.unit is not None:
            unit = word_translate(self.unit)
        # setup the property value for 4 cases:
        # 1 - IfcPropertySingleValue
        # 2 - IfcPropertyBoundedValue
        # 3 - IfcPropertyEnumeratedValue
        # 4 - IfcPropertyTableValue
        if self.nominalvalue is not None:
            value = self.nominalvalue
        elif (self.upper_bound is not None) or (self.lower_bound is not None):
            (UB, LB) = (str(), str())
            if self.upper_bound is not None:
                UB = self.upper_bound
            if self.lower_bound is not None:
                LB = self.lower_bound
            value = "{0}{1}".format(LB, UB)
        elif len(self.EnumerationValues) > 0:
            for x in self.EnumerationValues:
                value += "{}, ".format(x)
            value = value.rstrip(", ")
            # EnumerationReference is not needed for now, skip it
            if self.EnumerationReference is not None:
                pass
        # setup the description and the final string if a description exists
        # unicode conversion for Python 2.6 compatibility
        try: 
           name = "{0}".format(name)
        except UnicodeEncodeError:
           name = name.encode('utf8', 'replace')
        try: 
           value = "{0}".format(value)
        except UnicodeEncodeError:
           value = value.encode('utf8', 'replace')
        try: 
           unit = "{0}".format(unit)
        except UnicodeEncodeError:
           unit = unit.encode('utf8', 'replace')
        # create the final string
        return [name, value, unit]

################################################################################
############# IfcClassification CLASS ##########################################
################################################################################

class IfcClassification:
    """Classe per memorizzare la classificazione Uniformat"""
    def __init__(self, name, code, description):
        self.name = name
        if code is not None:
            self.code = code
        else:
            self.code = UNDEFINED
        if description is not None:
            self.desc = description
        else:
            self.desc = str()
        
    def __str__(self):
        return repr(self.name, self.code, self.descr)

################################################################################
############# PropertySet Parser ###############################################
################################################################################

def ParsePropertySet (DataType, *propertyset):
    """This funtion parse an IfcPropertySet and return a dictionary with 
       PropertySet.Name as a key and a list of IfcProperty class"""
    def get_IfcString(value):
        """function to extract the proprty text and return a string"""
        # check the data type and try to extract the value
        if type(value) is str:
            return value
        elif type(value) is int:
            return str(value)
        elif type(value) is float:
            return str(value)
        elif value is None:
            return None
        elif isinstance(value, ifcopenshell.entity_instance) is True:
            if value.is_a() == "IfcCalendarDate":
                return "{0}/{1}/{2}".format(
                       value.DayComponent, 
                       value.MonthComponent,
                       value.YearComponent)
            elif value.is_a() in DataType:
                if isinstance(value.wrappedValue, int):
                    val = str(value.wrappedValue)
                elif isinstance(value.wrappedValue, float):
                    val = str(value.wrappedValue)
                else:
                    # retro-compatibility for Python 2.7 unicode error
                    try:
                        val = "{0}".format(value.wrappedValue)
                    except UnicodeEncodeError:
                        val = "{0}".format(value.wrappedValue.encode('utf-8'))
                return val
            elif value.is_a() == "IfcSIUnit":
                # retro-compatibility for Python 2.7 unicode error
                try:
                    val = "{0}".format(value.Name)
                    if value.Prefix is not None:
                        prefix = "{0}".format(value.Prefix)
                except UnicodeEncodeError:
                    val = "{0}".format(value.Name.encode('utf-8'))
                    if value.Prefix is not None:
                        prefix = "{0}".format(value.Prefix.encode('utf-8'))
                # for now we don't need value.UnitType so we skip it
                if value.Prefix is None:
                    return val
                else:
                    return "{0} {1}".format(prefix, val)
            elif value.is_a() == "IfcPropertyEnumeration":
                # retro-compatibility for Python 2.7 unicode error
                try:
                    name = value.Name
                    enum = value.EnumerationValues
                    unit = value.Unit
                except UnicodeEncodeError:
                    name = value.Name.encode('utf-8')
                    enum = value.EnumerationValues.encode('utf-8')
                    unit = value.Unit.encode('utf-8')
                finally:
                    if value.Unit is None: unit = ""
                    val = "{0} {1} {2}".format(name, enum, unit)
                return val
            elif value.is_a() == "IfcDerivedUnit":
                return value.UnitType
            elif value.is_a() == "IfcConversionBasedUnit":
                return value.UnitType
            elif value.is_a() == "IfcContextDependentUnit":
                return value.UnitType
            else:
                try:
                    val = "{0}".format(value.wrappedValue)
                # for python 2.7 unicode retro-compatibility
                except UnicodeEncodeError:
                    val = "{0}".format(value.wrappedValue.encode('utf-8'))
                except:
                    val = None
                    raise CharonIfcError(value.is_a())
                finally:
                    return val
        else:
            # if value is unknown raise an error
            raise CharonIfcError("get_IfcString: no value has been returned")
    ############################################################################
    # Parse the property
    ############################################################################
    has_properties = dict()
    for pset in propertyset:
        #initialize the property list
        single_prop_list = list()
        # extract and store the property list
        property_type = UnicodeTest(pset.Name)
        try:
            if pset.is_a() == "IfcPropertySet":
                propery_list = pset.HasProperties
            elif pset.is_a() == "IfcElementQuantity":
                propery_list = pset.Quantities
            else:
                propery_list = [pset]
            logging.debug("Property type {0}: {1}".format(
                          property_type, propery_list))
        except AttributeError as err:
            # add debug information
            logging.error("Property type {0}: {1}".format(
                          property_type, err))
            continue
        except RuntimeError as err:
            # add debug information
            logging.error("Property type {0}: {1}".format(
                          property_type, err))
            continue
        # add the property set to the list
        for ifcproperty in propery_list:
          # set the property name
          SP = IfcProperty(ifcproperty.Name)
          # set the property description
          SP.description = get_IfcString(ifcproperty.Description)
          # set the Unit, for 2x3 schema it's optional, check if it's available
          if hasattr(ifcproperty, "Unit"):
              SP.unit = get_IfcString(ifcproperty.Unit)
          else:
              SP.unit = None
          # setup the property values, depending on the type
          if ifcproperty.is_a() == "IfcPropertySingleValue":
            # NominalValue optional in the 2x3 schema, check if it's available
            try:
                SP.nominalvalue = get_IfcString(ifcproperty.NominalValue)
            except RuntimeError as err:
                SP.nominalvalue = None
                logging.error("{} {}".format(ifcproperty,err))
          elif ifcproperty.is_a() == "IfcPropertyEnumeratedValue":
            SP.EnumerationReference = get_IfcString(ifcproperty.EnumerationReference)
            if ifcproperty.EnumerationValues is not None:
              for value in ifcproperty.EnumerationValues:
                 SP.EnumerationValues.append(get_IfcString(value))
          elif ifcproperty.is_a() == "IfcPropertyBoundedValue":
            SP.upper_bound = get_IfcString(ifcproperty.UpperBoundValue)
            SP.lower_bound = get_IfcString(ifcproperty.LowerBoundValue)
          elif ifcproperty.is_a() == "IfcPropertyTableValue":
            SP.description = get_IfcString(ifcproperty.Expression)
            # store the values somehow
            DefiningValues = get_IfcString(ifcproperty.DefiningValues)
            DefinedValues = get_IfcString(ifcproperty.DefinedValues)
            DefiningUnit = get_IfcString(ifcproperty.DefiningUnit)
            DefinedUnit = get_IfcString(ifcproperty.DefinedUnit)
            SP.unit = None
            i=0
            if DefiningValues is not None:
                for value1 in DefiningValues:
                     value2 = DefinedValues[i]
                     a="{}{}".format(get_IfcString(value1),DefiningUnit)
                     b="{}{}".format(get_IfcString(value2),DefinedUnit)
                     SP.EnumerationValues.append("{}-{}".format(a,b))
                     i+=1
          elif ifcproperty.is_a() == "IfcPropertyReferenceValue":
            SP.nominalvalue = get_IfcString(ifcproperty.PropertyReference)
          elif ifcproperty.is_a() == "IfcPropertyListValue":
            if ifcproperty.ListValues is not None:
                for value in ifcproperty.ListValues:
                    SP.EnumerationValues.append(get_IfcString(value))
            SP.unit = get_IfcString(ifcproperty.Unit)
            raise CharonIfcError("IfcPropertyListValue not defined.")
          elif ifcproperty.is_a() == "IfcQuantityLength":
            SP.nominalvalue = get_IfcString(ifcproperty.LengthValue)
          elif ifcproperty.is_a() == "IfcQuantityArea":
            SP.nominalvalue = get_IfcString(ifcproperty.AreaValue)
          elif ifcproperty.is_a() == "IfcQuantityVolume":
            SP.nominalvalue = get_IfcString(ifcproperty.VolumeValue)
          elif ifcproperty.is_a() == "IfcQuantityCount":
            SP.nominalvalue = get_IfcString(ifcproperty.CountValue)
          elif ifcproperty.is_a() == "IfcQuantityWeight":
            SP.nominalvalue = get_IfcString(ifcproperty.WeightValue)
          elif ifcproperty.is_a() == "IfcQuantityTime":
            SP.nominalvalue = get_IfcString(ifcproperty.TimeValue)
          # specific properties
          elif ifcproperty.is_a() == "IfcDoorLiningProperties":
            SP.nominalvalue = ", ".join([
            "{}: {}".format(word_translate("LiningDepth"), 
                            get_IfcString(ifcproperty.LiningDepth)),
            "{}: {}".format(word_translate("ThresholdDepth"),
                            get_IfcString(ifcproperty.ThresholdDepth)),
            "{}: {}".format(word_translate("ThresholdThickness"),
                            get_IfcString(ifcproperty.ThresholdThickness)),
            "{}: {}".format(word_translate("TransomThickness"),
                            get_IfcString(ifcproperty.TransomThickness)),
            "{}: {}".format(word_translate("TransomOffset"),
                            get_IfcString(ifcproperty.TransomOffset)),
            "{}: {}".format(word_translate("LiningOffset"),
                            get_IfcString(ifcproperty.LiningOffset)),
            "{}: {}".format(word_translate("ThresholdOffset"),
                            get_IfcString(ifcproperty.ThresholdOffset)),
            "{}: {}".format(word_translate("CasingThickness"),
                            get_IfcString(ifcproperty.CasingThickness)),
            "{}: {}".format(word_translate("CasingDepth"),
                            get_IfcString(ifcproperty.CasingDepth))])
          elif ifcproperty.is_a() == "IfcDoorPanelProperties":
            SP.nominalvalue = ", ".join([
            "{}: {}".format(word_translate("PanelDepth"), 
                            get_IfcString(ifcproperty.PanelDepth)),
            "{}: {}".format(word_translate("PanelOperation"),
                            get_IfcString(ifcproperty.PanelOperation)),
            "{}: {}".format(word_translate("PanelWidth"),
                            get_IfcString(ifcproperty.PanelWidth)),
            "{}: {}".format(word_translate("PanelPosition"),
                            get_IfcString(ifcproperty.PanelPosition))])
          elif ifcproperty.is_a() == "IfcWindowLiningProperties":
            SP.nominalvalue = ", ".join([
            "{}: {}".format(word_translate("LiningDepth"), 
                            get_IfcString(ifcproperty.LiningDepth)),
            "{}: {}".format(word_translate("LiningThickness"),
                            get_IfcString(ifcproperty.LiningThickness)),
            "{}: {}".format(word_translate("TransomThickness"),
                            get_IfcString(ifcproperty.TransomThickness)),
            "{}: {}".format(word_translate("MullionThickness"),
                            get_IfcString(ifcproperty.MullionThickness)),
            "{}: {}".format(word_translate("FirstTransomOffset"),
                            get_IfcString(ifcproperty.FirstTransomOffset)),
            "{}: {}".format(word_translate("SecondTransomOffset"),
                            get_IfcString(ifcproperty.SecondTransomOffset)),
            "{}: {}".format(word_translate("FirstMullionOffset"),
                            get_IfcString(ifcproperty.FirstMullionOffset)),
            "{}: {}".format(word_translate("SecondMullionOffset"),
                            get_IfcString(ifcproperty.SecondMullionOffset))])
          elif ifcproperty.is_a() == "IfcWindowPanelProperties":
            SP.nominalvalue = ", ".join([
            "{}: {}".format(word_translate("OperationType"), 
                            get_IfcString(ifcproperty.OperationType)),
            "{}: {}".format(word_translate("PanelPosition"),
                            get_IfcString(ifcproperty.PanelPosition)),
            "{}: {}".format(word_translate("FrameDepth"),
                            get_IfcString(ifcproperty.FrameDepth)),
            "{}: {}".format(word_translate("FrameThickness"),
                            get_IfcString(ifcproperty.FrameThickness))])
          else:
            raise CharonIfcError("IfcProperty '{0}' of Unknown type.".format(ifcproperty))
          # add the property to the list
          single_prop_list.append(SP)
        #add the list of single properties to the dictionary
        has_properties[property_type] = single_prop_list
    return has_properties

################################################################################
############# PrintSettings CLASS ##############################################
################################################################################

class PrintSettings:
   """Class to store print settings"""
   def __init__(self, bolt=True):
       self.attribute_bolt = bolt
       self.name_bolt = bolt

   def SetAttributeBolt(self, val=True):
       self.attribute_bolt = val

   def IsAttributeBolt(self):
       return self.attribute_bolt

   def SetNameBolt(self, val=True):
       self.name_bolt = val

   def IsNameBolt(self, val=True):
       return self.name_bolt

################################################################################
############# CREATE MARKUP FILE ###############################################
################################################################################
class CreateMarkUpText:
    """Class to create a markup document from a IfcParser library. 
       Create a markup text readable by 'pandoc' program"""
      
    def __init__(self, p_list,
                 title=None, 
                 type_blacklist=None, 
                 prop_blacklist=None,
                 settings=None,
                 add_associations=True):
        # setup title
        self.title = title
        if self.title is None:
            self.title = DEFAULT_TITLE
        # setup the blacklists
        self.type_blacklist = type_blacklist
        if self.type_blacklist is None:
            self.type_blacklist = list()
        self.prop_blacklist = prop_blacklist
        if self.prop_blacklist is None:
            self.prop_blacklist = list()
        #setup carriage return and other constants
        cr = "\n \n"
        # setup the document class and size
        if settings is None:
            settings = PrintSettings()
        # make attribute name bolt
        if settings.IsAttributeBolt():
            self.attr = "**"
            logging.info("Object attributes set to BOLT.")
        else:
            self.attr = ""
        # make attribute name bolt
        if settings.IsNameBolt():
            self.nmb = "*"
            logging.info("Object names set to BOLT.")
        else:
            self.nmb = ""
        # add associated elements
        self.add_asso = add_associations
        #setup the list of objects
        self.obj_list = list()
        # create the section
        self.obj_list = self.CreateSection(p_list)

    def __str__(self):
        #convert list to string
        try:
           # workaround for Python 2.7 unicode UnicodeDecodeError
           MarkedUpText = ''.join(self.obj_list)
        except UnicodeDecodeError:
           MarkedUpText = ''
           for txt in self.obj_list:
               a = str(txt)
               MarkedUpText += a
        return MarkedUpText

    def ElementFilter(self, elem, blacklisted_section):
        """This function filter the properties and avoid printing them
        if they are blacklisted in the config file blacklist section"""
        #retro-compatibility with python 2.6 module ConfigParser
        try:
            blacklist = list(blacklisted_section.items())
        except AttributeError:
            blacklist = list(blacklisted_section)
        # if no property is blacklisted exit
        if len(blacklist) == 0:
            logging.debug("Blacklist {} is empty!".format(blacklisted_section))
            return True
        # setup the variable names to be lowercase
        p = (elem.lower(), None)
        w = (word_translate(elem).lower(), None)
        # check if the word is blacklisted
        if p in blacklist or w in blacklist:
            logging.debug("Item '{0}' filtered!".format(p))
            return False
        else:
            logging.debug("Item '{0}' NOT filtered!".format(p))
            return True

    def CreateSection(self, library, obj_list=list()):
        #setup carriage return and other constants
        cr    = "\n \n"
        tag   = _("Tag")
        gid   = _("GlobalID")
        name  = _("Name")
        desc  = _("Description")
        ptype = _("Predefined Type")
        #setup the file header
        obj_list.append("% {0} {1}".format(self.title,cr))
        #extract the list from library
        for tipologia in sorted(library.keys()):
            if self.ElementFilter(tipologia, self.type_blacklist) is True:
                #translate the name
                chapter_name = word_translate(tipologia)
                # create CHAPTERS
                obj_list.append("# "+chapter_name+" #"+cr+cr)
                for item in library[tipologia]:
                    # create SECTIONS
                    obj_list.append(cr)
                    obj_list.append("## "+item.name+" ##")
                    obj_list.append(cr)
                    # print name tag and then properties
                    if hasattr(item, 'tag'): 
                        ItemTag = item.tag
                        ident=tag
                    else: 
                        ItemTag = item.id
                        ident=gid
                    obj_list.append("".join([self.nmb,ident,":",self.nmb, " ",
                                    ItemTag, cr]))
                    obj_list.append("".join([self.nmb,name, ":",self.nmb, " ",
                                    item.name, cr]))
                    obj_list.append("".join([self.nmb,desc, ":",self.nmb, " ",
                                    item.description, cr]))
                    obj_list.append("".join([self.nmb,ptype,":",self.nmb, " ",
                                    item.predefined_type, cr]))
                    #add Uniformat or OmniClass classification if it exists
                    if item.classification is not None:
                        obj_list.append("".join([self.attr, 
                                             item.classification.name, 
                                             ":", 
                                             self.attr, " ",
                                             item.classification.code, 
                                             item.classification.desc,
                                             cr]))
                    # add each single object property
                    if item.has_properties is not None:
                        for key in sorted(item.has_properties.keys()):
                          if self.ElementFilter(key,self.prop_blacklist) is True:
                              attributes = item.has_properties[key]
                              # translate the property name and create PARAGRAPH
                              obj_list.append("".join(["+ ",self.attr,
                                                      word_translate(key),
                                                      self.attr,cr]))
                              for elem in attributes:
                                  x = elem.print_property()
                                  obj_list.append("    -   {0}: {1} {2}{3}".format(
                                                  x[0], x[1], x[2], cr))
                    # add associated properties
                    if item.has_associations is not None and self.add_asso:
                        for key in sorted(item.has_associations.keys()):
                          if self.ElementFilter(key,self.prop_blacklist) is True:
                              attributes = item.has_associations[key]
                              # translate the property name and create PARAGRAPH
                              obj_list.append("".join(["+ ",self.attr,
                                                      word_translate(key),
                                                      self.attr,cr]))
                              if attributes is None:
                                  continue
                              for x in attributes:
                                  obj_list.append("    -   {0}{1}".format(x,cr))
            else:
                pass
        # return the list to print
        return obj_list

################################################################################
############# UNICODE-DECODER ##################################################
################################################################################

def UnicodeTest(text): #TODO remove this function?
    """This is a function for python 2.7 retro-compatibility.
    the function test if the string is unicode and then convert the string
    only if needed"""
    if text is None:
        return text
    #if we get a NameError exception, then we're using python ver. >3, exit
    try: 
        if isinstance(text, unicode):
            text = text.encode("utf8")
    except NameError:
        return text
    # if we get a UnicodeEncodeError we're using python2.x and we have to encode
    try:
        t="{}".format(text)
    except UnicodeEncodeError:
        text = text.encode("utf8")
    finally:
        return text

################################################################################
############# PANDOC CONVERTER #################################################
################################################################################

#this function use pandoc to convert several other outputs
#see pando documentation: https://pandoc.org/MANUAL.html

def PandocConverter(stdinput, fformat, outputfile, template=None):
    """Function to create the sys command to run the pandoc program"""
    options = "--standalone"
    #if a template is required:
    if template is not None:
        if os.path.isfile(template): 
            options = options + "--template={0}".format(template)
        else:
            logging.error("'{0}' file does not exist.".format(template))
    #create the correct output filename
    if fformat == "latex":
        fformat = "tex"
    elif fformat == "mediawiki":
        fformat = "html"
    pandocfile = "{}.{}".format(os.path.splitext(outputfile)[0], fformat)
    # use subprocess to run 'pandoc' program
    try:
        if python_version > 2:
            subprocess.run(["pandoc", options, "-o", pandocfile],
                           input=bytes(stdinput, "utf-8"),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           check=True)
        # support for python 2
        else:
            subprocess.call(["pandoc", options, "-o", pandocfile],
                           input=bytes(stdinput, "utf-8"),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        logging.error("Pandoc error: {}".format(err))
        # try to create a simple TXT output
        pandocfile = outputfile+".txt"
        with open(pandocfile, 'w') as txtfile:
            txtfile.write(stdinput)
        logging.error("""Error converting document, a simple text file """
                      """ '{}' was created instead!""".format(pandocfile))
    except FileNotFoundError:
        raise CharonIfcError("""'pandoc' program not found. Please Install """
                             """pandoc (https://pandoc.org)""")
    return pandocfile

################################################################################
############# TEXT CONVERTER ###################################################
################################################################################

def TxtConverter(stdinput, outputfile):
    """Simple text output function to use in case pandoc is not installed i
    in the system and so PandocConverter function cannot be used."""
    filename = "{}.{}".format(os.path.splitext(outputfile)[0], "txt")
    with open(txtfile, 'w') as t:
        t.write(stdinput)
    return filename

################################################################################
############# HTML CONVERTER ###################################################
################################################################################

def HtmlConverter(stdinput, outputfile, template=None):
    """Simple HTML output function to use in case pandoc is not installed i
    in the system and so PandocConverter function cannot be used."""
    filename = "{}.{}".format(os.path.splitext(outputfile)[0], "html")
    stdinput = markdown.markdown(stdinput, output_format="html5")
    with open(txtfile, 'w') as t:
        t.write(stdinput)
    return filename

################################################################################
############# LIBRARY DEFAULT DATA #############################################
################################################################################

IfcObjectsCalculationRules = {"IfcBeam": "NetVolume",
                              "IfcBeam-Rebars":"NetWeight * 0.5",
                              "IfcBeam-Forms":"OuterSurfaceArea * Length",
                              "IfcColumn":"NetVolume",
                              "IfcColumn-Rebars":"NetWeight * 0.5",
                              "IfcColumn-Forms":"OuterSurfaceArea * Length",
                              "IfcSlab":"NetVolume",
                              "IfcSlab-Rebars":"NetWeight * 0.5",
                              "IfcSlab-Forms":"NetArea * Width",
                              "IfcStair":"NetVolume",
                              "IfcStair-Rebars":"NetWeight * 0.5",
                              "IfcStair-Forms":"OuterSurfaceArea * Length",
                              "IfcWall":"NetVolume",
                              "IfcWall-Rebars":"NetWeight * 0.5",
                              "IfcWall-Forms":"OuterSurfaceArea * Length"
                             }

IfcBuildingControlDomain = (
              "IfcActuatorType",
              "IfcAlarmType",
              "IfcControllerType",
              "IfcFlowInstrumentType",
              "IfcSensorType")

IfcElectricalDomain = (
              "IfcCableCarrierFittingType",
              "IfcCableCarrierSegmentType",
              "IfcCableSegmentType",
              "IfcElectricApplianceType",
              "IfcElectricDistributionPoint",
              "IfcElectricFlowStorageDeviceType",
              "IfcElectricGeneratorType",
              "IfcElectricHeaterType",
              "IfcElectricMotorType",
              "IfcElectricTimeControlType",
              "IfcElectricalCircuit",
              "IfcJunctionBoxType",
              "IfcLampType",
              "IfcLightFixtureType",
              "IfcMotorConnectionType",
              "IfcOutletType",
              "IfcProtectiveDeviceType",
              "IfcSwitchingDeviceType",
              "IfcTransformerType")

IfcHVACDomain = ("IfcAirTerminalBoxType",
              "IfcAirTerminalType",
              "IfcAirToAirHeatRecoveryType",
              "IfcBoilerType",
              "IfcChillerType",
              "IfcCoilType",
              "IfcCompressorType",
              "IfcCondenserType",
              "IfcCooledBeamType",
              "IfcCoolingTowerType",
              "IfcDamperType",
              "IfcDuctFittingType",
              "IfcDuctSegmentType",
              "IfcDuctSilencerType",
              "IfcEvaporativeCoolerType",
              "IfcEvaporatorType",
              "IfcFanType",
              "IfcFilterType",
              "IfcFlowMeterType",
              "IfcGasTerminalType",
              "IfcHeatExchangerType",
              "IfcHumidifierType",
              "IfcPipeFittingType",
              "IfcPipeSegmentType",
              "IfcPumpType",
              "IfcSpaceHeaterType",
              "IfcTankType",
              "IfcTubeBundleType",
              "IfcValveType",
              "IfcVibrationIsolatorType")

IfcPlumbingFireProtectionDomain = (
              "IfcFireSuppressionTerminalType",
              "IfcSanitaryTerminalType",
              "IfcStackTerminalType",
              "IfcWasteTerminalType")

IfcSharedBLDElementsDomain = (
              "IfcBeam",
              "IfcBeamType",
              "IfcBuildingElementProxyType",
              "IfcColumn",
              "IfcColumnType",
              "IfcCurtainWall",
              "IfcCurtainWallType",
              "IfcDoor",
              "IfcDoorLiningProperties",
              "IfcDoorPanelProperties",
              "IfcDoorStyle",
              "IfcFurnitureType",
              "IfcMember",
              "IfcMemberType",
              "IfcPlate",
              "IfcPlateType",
              "IfcRailing",
              "IfcRailingType",
              "IfcRamp",
              "IfcRampFlight",
              "IfcRampFlightType",
              "IfcRelConnectsPathElements",
              "IfcRoof",
              "IfcSlab",
              "IfcSlabType",
              "IfcStair",
              "IfcStairFlight",
              "IfcStairFlightType",
              "IfcWall",
              "IfcWallStandardCase",
              "IfcWallType",
              "IfcWindow",
              "IfcWindowLiningProperties",
              "IfcWindowPanelProperties",
              "IfcWindowStyle")

IfcStructuralElementsDomain = ("IfcBuildingElementComponent",
              "IfcBuildingElementPart",
              "IfcFooting",
              "IfcPile",
              "IfcReinforcementDefinitionProperties",
              "IfcReinforcingBar",
              "IfcReinforcingElement",
              "IfcReinforcingMesh",
              "IfcTendon",
              "IfcTendonAnchor")
