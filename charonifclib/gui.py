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

from __future__ import print_function
from __future__ import unicode_literals

import os
import wx
import webbrowser

################################################################################
############# SETUP LOGGING ####################################################
################################################################################
import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
logger =logging.getLogger()

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
############# IMPORTAZIONE MODULI CUSTOM #######################################
################################################################################

from . import charonifclib

# import helper function to manage project files
from . import get_data_path
from .helper import read_config_file, write_config_file, test_pandoc

################################################################################
############ GLOBAL VARIABLES ##################################################
################################################################################
IFCfile = None
MIN_SIZE = (800,600)

################################################################################
############ MAIN CLASS ########################################################
################################################################################

class CharonIfcFrame(wx.Frame):
    """
    A Frame for CharonIfc App
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(CharonIfcFrame, self).__init__(*args, **kw)

        # check if 'pandoc' is installed
        self.CheckPandoc()
        # configuration file
        self.config = read_config_file()
        # setup the default settings for charonifclib from config file
        charonifclib.SetCalculationRules(self.config._sections[
                                         "IFCOBJECT_CALCULATION_RULES"])
        # setup the documents language for translations
        #charonifclib.SetLanguage(current_locale)
        # setup the log level
        self.log_level = GetConfig(self.config, 'loglevel', is_int=True)
        if self.log_level is not None:
            logger.setLevel(self.log_level)
        
        # setup the IFC bitmap
        IFC_iconfile = os.path.join(get_data_path(), "IFC_icon.ico")
        IFC_bmp = wx.Bitmap(IFC_iconfile, wx.BITMAP_TYPE_ANY)
        # setup IFC icon
        # wx 4.0 compatibulity issue, EmptyIcon deprecated, use wx.Icon()
        try:
            self.icon = wx.Icon()
        except TypeError:
            self.icon = wx.EmptyIcon()
        self.icon.CopyFromBitmap(IFC_bmp)
        self.SetIcon(self.icon)
        
        # create a panel in the frame
        pnl = wx.Panel(self)

        # set a background image
        background = os.path.join(get_data_path(), "background.png")
        bmp1 = wx.Image(background, wx.BITMAP_TYPE_ANY).ConvertToBitmap()# setup the background
        #self.bitmap1 = wx.StaticBitmap(pnl, -1, bmp1, (0, 0))
        
        # and put some welcome text on it
        st = wx.StaticText(pnl, 
                           label=_("Welcome to CharonIfC, please select "
                                   "an IFC model!"))
        font = st.GetFont()
        #font.PointSize += 10
        font = font.Bold()
        st.SetFont(font)

        # create a menu bar
        self.makeMenuBar()

        #create a vbox to store the widgets and buttons
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        
        # add a button to select the IFC file
        self.button0 = wx.Button(pnl,
                                 label=_("Select IFC File"))

        # create the Specifications button, disabled by default
        self.button1 = wx.Button(pnl, label=_("Create Specifications"))
        self.button1.Disable()

        # create the BOQ button, disabled by default
        self.button2 = wx.Button(pnl, label=_("Create Bill of Quantities"))
        self.button2.Disable()
        
        # add buttons, radiobox, etc. to the vbox
        vbox1.AddSpacer(40)
        vbox1.Add(st,           0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(self.button0, 0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(self.button1, 0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(self.button2, 0, wx.ALIGN_LEFT | wx.ALL, border=20)
        
        # add the vbox to the panel
        pnl.SetSizerAndFit(vbox1)

        # create bindings for buttons
        self.Bind(wx.EVT_BUTTON, self.OnOpen,                 self.button0)
        self.Bind(wx.EVT_BUTTON, self.OnCreateSpecifications, self.button1)
        self.Bind(wx.EVT_BUTTON, self.OnCreateBOQ,            self.button2)
        
        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText(_("Welcome to CharonIfc!"))

        # set the size
        self.SetSize(MIN_SIZE)
        
        # center the panel
        self.Centre()
        
        # Make this panel a File Drop Target
        # Create a File Drop Target object
        dnd = FileDropTarget(pnl,self.button0,self.button1,self.button2,self)
        # Link the Drop Target Object to the Text Control
        pnl.SetDropTarget(dnd)

    
    def CheckPandoc(self):
        """
        Function to check pandoc installation or return a message box
        """
        test = test_pandoc()
        if test:
            return
        else:
            dlg = wx.MessageBox(_("""Pandoc software (https://pandoc.org/) """
                                """is not installed. Please install Pandoc """
                                """if you want to export to html, docx """
                                """and odt format."""),
                                "Pandoc Software not installed",
                                wx.OK | wx.ICON_INFORMATION)


    def makeMenuBar(self):
        """
        A menu bar is composed of menus, which are composed of menu items.
        This method builds a set of menus and binds handlers to be called
        when the menu item is selected.
        """

        # Make a file menu with Hello and Exit items
        fileMenu = wx.Menu()
        # The "\t..." syntax defines an accelerator key that also triggers
        # the same event
        openItem = fileMenu.Append(-1, "&Open...\tCtrl-O",
                _("Open an IFC file"))
        editItem = fileMenu.Append(-1, "&Edit ConfigFile\tCtrl-E",
                _("Edit a configuration file"))
        fileMenu.AppendSeparator()
        # When using a stock ID we don't need to specify the menu item's
        # label
        exitItem = fileMenu.Append(wx.ID_EXIT)

        # Create a Preference selector menu
        preferenceMenu = wx.Menu()
        preferenceItem = preferenceMenu.Append(-1, "&Preferences...\tCtrl-P",
                         _("Choose the Preferences and configurations"))

        # Now a help menu for the about item
        helpMenu = wx.Menu()
        manualItem = helpMenu.Append(-1, "User Manual",
                                     _("Show the User Manual"))
        aboutItem = helpMenu.Append(wx.ID_ABOUT)

        # Make the menu bar and add the two menus to it. The '&' defines
        # that the next letter is the "mnemonic" for the menu item. On the
        # platforms that support it those letters are underlined and can be
        # triggered from the keyboard.
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(preferenceMenu, "&Preferences")
        menuBar.Append(helpMenu, "&Help")

        # Give the menu bar to the frame
        self.SetMenuBar(menuBar)

        # Finally, associate a handler function with the EVT_MENU event for
        # each of the menu items. That means that when that menu item is
        # activated then the associated handler function will be called.
        self.Bind(wx.EVT_MENU, self.OnOpen, openItem)
        self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
        self.Bind(wx.EVT_MENU, self.OnPreferences,  preferenceItem)
        self.Bind(wx.EVT_MENU, self.OnUserManual, manualItem)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
        self.Bind(wx.EVT_MENU, self.OnConfigFileEdit,  editItem)

    def EnableButton(self, event):
        myobject = event.GetEventObject()
        myobject.Enable()

    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)

    def OnPreferences(self, event):
        """Setup the user preferences and configuration file."""
        # open the preferences dialog
        frm = PreferencesFrame(None, title='CharonIfc')
        frm.Show()

    def OnConfigFileEdit(self, event):
        """Setup the user preferences and configuration file."""
        # create the file dialog
        with wx.FileDialog(self, message=_("Choose a Config file"),
                           defaultDir="",
                           defaultFile="",
                           wildcard="Config files (*.cfg)|*.cfg",
                           style=wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST
                           ) as fileDialog:

            # get the last directory chosen by the user from config file
            directory = GetConfig(self.config, 'lastdir')
            if directory is not None:
                # setup the last saved directory
                if os.path.exists(directory):
                    fileDialog.SetDirectory(directory)
                else:
                    logging.info("Directory {} does not exist.".format(directory))
            # return if the user close the dialog
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
        
            # open the preferences dialog
            frm = ConfigEditorFrame(None, title=pathname)
            frm.Show()

    def OnAbout(self, event):
        """Display an About Dialog"""
        # wx Python 4.0 compatibility issue
        try:
            info = wx.AboutDialogInfo()
        except AttributeError:
            from wx import adv
            info = adv.AboutDialogInfo()
        info.Name = "CharonIFC"
        info.Version = charonifclib.VERSION
        info.Copyright = "(C) 2017 Davide Vescovini"
        info.Description = """
        A library to extract information from an IFC file
        to produce Technical Documentation like 
        Specifications and Bill of Quantities.
        This program use the Open Source software
        IfcOpenShell, see
        <http://ifcopenshell.org/> an open source ([LGPL])
        software library for working with the Industry
        Foundation Classes ([IFC]) file format.
        Currently supported IFC releases are [IFC2x3 TC1]
        and [IFC4 Add1]. A pre-compiled version of this 
        program is distributed with a copy of this software."""
        info.WebSite = ("https://launchpad.net/charonifc",
                        "CharonIFC Project Page")
        info.Developers = ["Davide Vescovini"]
        info.License = """
        CharonIFC This program is free software: 
        you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>."""
        # Set the icon
        info.SetIcon(self.icon)
        # Show the wx.AboutBox
        # wx Python 4.0 compatibility issue
        try:
            wx.AboutBox(info)
        except AttributeError:
            adv.AboutBox(info)
        
    def OnUserManual(self, event):
        """Display the Manual"""
        # open an HTML file
        url = "file://{0}/usermanual_en.html".format(get_data_path())
        new = 2 # open in a new tab, if possible
        webbrowser.open(url,new=new)

    def OnOpen(self, event):
        """Display a file chooser Dialog"""

        # create the file dialog
        with wx.FileDialog(self, message=_("Choose an IFC file"),
                           defaultDir="",
                           defaultFile="",
                           wildcard="IFC files (*.ifc)|*.ifc",
                           style=wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST
                           ) as fileDialog:

            # get the last directory chosen by the user from config file
            directory = GetConfig(self.config, 'lastdir')
            if directory is not None:
                # setup the last saved directory
                if os.path.exists(directory):
                    fileDialog.SetDirectory(directory)
                else:
                    logging.info("Directory {} does not exist.".format(directory))
            # return if the user close the dialog
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            # save last chosen pathname in the config file
            lastdir = os.path.dirname(pathname)
            SaveConfig(self.config, 'lastdir', lastdir)
            # open the IFC file
            try:
                with open(pathname, 'r') as file:
                    global IFCfile
                    IFCfile = pathname
                    self.button0.Disable()
                    self.button1.Enable()
                    self.button2.Enable()                    
                    self.SetStatusText(IFCfile)
                # check ifcopenshell schema and IFC file schema and 
                # tell the user if they don't match
                IfcChk = charonifclib.IfcCheck(IFCfile)
                if not IfcChk.IsSchemaCorrect():
                    wx.LogError(_("""Attention, IFC schema '{}' """
                                """dosn't match the required schema '{}'."""
                                ).format(IfcChk.GetIfcSchema(),
                                IfcChk.GetIfcOpenShellSchema()))
                return pathname
            except IOError:
                wx.LogError("Cannot open file '{}'.".format(pathname))
                return

    def OnCreateSpecifications(self, event):
        """Create the Technical Specifications"""
        if IFCfile is None:
            wx.LogError(_("Cannot open file."))
            return
        # open the specification options frame
        #self.Hide()
        frm = SpecificationFrame(None, title='CharonIfc')
        frm.Show()

    def OnCreateBOQ(self, event):
        """Create the Bill Of Quantities"""
        if IFCfile is None:
            wx.LogError(_("Cannot open file."))
            return
        #self.Hide()
        frm = BOQFrame(None, title='CharonIfc')
        frm.Show()
        self.Show()

################################################################################
############ DRAG AND DROP - FILE ##############################################
################################################################################

# Define File Drop Target class
class FileDropTarget(wx.FileDropTarget):
   """ This object implements Drop Target functionality for Files """
   def __init__(self, obj, button0, button1, button2, frame):
      """ Initialize the Drop Target, passing in the Object Reference to
          indicate what should receive the dropped files """
      # Initialize the wxFileDropTarget Object
      wx.FileDropTarget.__init__(self)
      # Store the Object Reference for dropped files
      self.obj = obj
      self.button0 = button0
      self.button1 = button1
      self.button2 = button2
      self.frame = frame

   def OnDropFiles(self, x, y, filenames):
      """ Implement File Drop """
      # this function get a list of the files dropped
      # append a list of the file names dropped
      logging.debug("{} file(s) dropped at {},{}".format(len(filenames),x,y))
      for file in filenames:
          logging.info("{}".format(file))
          if not file.endswith(".ifc"):
              wx.LogError("File '{}' is not an IFC file.".format(file))
              continue
          # open the IFC file
          try:
              with open(file, 'r') as filename:
                    global IFCfile
                    IFCfile = file
                    self.button0.Disable()
                    self.button1.Enable()
                    self.button2.Enable()                    
                    self.frame.SetStatusText(IFCfile)
              return
          except IOError:
              wx.LogError("Cannot open file '%s'." % file)
              return

################################################################################
############ PREFERENCES FRAME #################################################
################################################################################

class PreferencesFrame(wx.Frame):
    """
    A Frame to choose the PREFERENCES Options and save the config file.
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(PreferencesFrame, self).__init__(*args, **kw)

        # get the configuration file or quit
        try:
            self.config = read_config_file()
        except:
            wx.LogError(_("Cannot open configuration file."))
            self.Destroy()
        
        # create a panel in the frame
        pnl = wx.Panel(self)
        
        # Create a Notebook to display and eventually change
        nb = wx.Notebook(pnl)
        # create the page windows as children of the notebook
        page1 = PageBlacklist(nb, "BLACKLIST_PROPERTY", "Property")
        page2 = PageBlacklist(nb, "BLACKLIST_IFCTYPE",  "IFC Type")
        page3 = PageCalcRules(nb, "IFCOBJECT_CALCULATION_RULES", col=2)
        page4 = PageSettings (nb)
        
        # add pages
        nb.AddPage(page1, _("Blacklist Property sections"))
        nb.AddPage(page2, _("Blacklist Ifc Types"))
        nb.AddPage(page3, _("Calculation Rules"))
        nb.AddPage(page4, _("Settings"))
        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)
        # create a panel in the frame
        pnl.SetSizer(sizer)
        
        # set the panel size
        self.SetSize(MIN_SIZE)
        
        # place the panel and show it
        self.Centre()
        self.Show(True)

class PageBlacklist(wx.Panel):
    def __init__(self, parent, cfg_section, b_txt):
        pnl = wx.Panel.__init__(self, parent)
        # read configuration file
        self.config = read_config_file()
        self.cfg_section = cfg_section
        # create the UI elements list
        hbox  = wx.BoxSizer(wx.HORIZONTAL)
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox2 = wx.BoxSizer(wx.VERTICAL)
        vbox3 = wx.BoxSizer(wx.VERTICAL)
        vbox4 = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        pnl1 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        pnl2 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        # create a list control
        self.lc = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
        self.lc.InsertColumn(0, _('Properties Blacklisted'))
        self.lc.SetColumnWidth(0, 160)
        # create a simple text
        if b_txt == "Property":
            bt = _("Property:")
            STxt = _("Type a Property and press 'Add'")
            # create a list of Pset properties
            c_list = sorted(charonifclib.IFCPSET.keys())
        elif b_txt == "IFC Type":
            bt = _("IFC Type:")
            STxt = _("Type an IFC Type and press 'Add'")
            # create a list of IfcTypes
            c_list = sorted(charonifclib.IFCSCHEMA["IfcTypes"])
        else:
            bt = b_txt
            STxt = _("Type a {} and press 'Add'").format(b_txt)
            c_list = list()
        self.st = wx.StaticText(pnl1, -1, STxt)
        vbox1.Add(self.st,  0, wx.EXPAND | wx.ALL)
        vbox1.Add(pnl1, 1, wx.EXPAND | wx.ALL, 3)
        vbox1.Add(pnl2, 1, wx.EXPAND | wx.ALL, 3)
        vbox2.Add(self.lc, 1, wx.EXPAND | wx.ALL, 3)
        self.tc1 = wx.ComboBox(pnl1, choices=c_list)
        hbox1.Add(wx.StaticText(pnl1, -1, bt), 0, wx.ALIGN_CENTER)
        hbox1.Add(self.tc1, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        vbox3.Add(self.tc1, 1, wx.ALIGN_CENTER)
        vbox3.Add(hbox1, 1, wx.ALIGN_CENTER)
        pnl1.SetSizer(vbox3)
        vbox4.Add(wx.Button(pnl2,10,_('Add')),   0, wx.ALIGN_CENTER|wx.TOP, 45)
        vbox4.Add(wx.Button(pnl2,11,_('Remove')),0, wx.ALIGN_CENTER|wx.TOP, 15)
        vbox4.Add(wx.Button(pnl2,12,_('Clear')), 0, wx.ALIGN_CENTER|wx.TOP, 15)
        pnl2.SetSizer(vbox4)
        self.Bind (wx.EVT_BUTTON, self.OnAdd,    id=10)
        self.Bind (wx.EVT_BUTTON, self.OnRemove, id=11)
        self.Bind (wx.EVT_BUTTON, self.OnClear,  id=12)
        hbox.Add(vbox1, 1, wx.EXPAND)
        hbox.Add(vbox2, 1, wx.EXPAND)
        self.SetSizer(hbox)
        # list the section
        if self.config.has_section(self.cfg_section):
            # Python 2.7 ConfigParser retro-compatibility
            try:
                blacklist = self.config[self.cfg_section].items()
            except AttributeError:
                blacklist = self.config.items(self.cfg_section)
            # populate the list
            num_items = self.lc.GetItemCount()
            for key in blacklist:
                self.lc.InsertStringItem(num_items, key[0])
                num_items+=1
        else:
            raise AttributeError

    def OnAdd(self, event):
        if not self.tc1.GetValue():
            wx.LogError(_("Text box is empty."))
            return
        num_items = self.lc.GetItemCount()
        txt = self.tc1.GetValue()
        self.lc.InsertStringItem(num_items, txt)
        self.tc1.Clear()
        # update the config file
        UpdateConfig(self.config, self.cfg_section, [(txt,'')])

    def OnRemove(self, event):
        index = self.lc.GetFocusedItem()
        elem = self.lc.GetItemText(index)
        dlg = wx.MessageBox(_("Do you want to delete {}?").format(elem),
                            _("Test Dialog"),
                            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg == wx.YES:
            self.lc.DeleteItem(index)
            # update the config file
            UpdateConfig(self.config, self.cfg_section, [(elem,0)])
        else:
            return

    def OnClear(self, event):
        dlg = wx.MessageBox(_("Do you really want to delete all sections?"),
                            _("Test Dialog"),
                            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg == wx.YES:
            self.lc.DeleteAllItems()
            # update the config file
            for e in self.config[self.cfg_section]:
               del self.config[self.cfg_section][e]
            write_config_file(self.config)
        else:
            return

class PageCalcRules(wx.Panel):
    def __init__(self, parent, cfg_section, col=1):
        pnl = wx.Panel.__init__(self, parent)
        # read configuration file
        self.config = read_config_file()
        self.cfg_section = cfg_section
        # create the UI elements list
        hbox  = wx.BoxSizer(wx.HORIZONTAL)
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox2 = wx.BoxSizer(wx.VERTICAL)
        vbox3 = wx.BoxSizer(wx.VERTICAL)
        vbox4 = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        pnl1 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        pnl2 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        # create a list control
        self.lc = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
        self.lc.InsertColumn(0, "IfcType")
        self.lc.SetColumnWidth(0, 160)
        self.lc.InsertColumn(1, _('Quantity Rule Name'))
        self.lc.SetColumnWidth(1, 160)
        # create a simple text
        bt1 = _("IfcType or IfcObject")
        bt2 = _("Quantity Rule")
        STxt = _("Type an IfcType or IfcObject and press 'Add'")
        self.st = wx.StaticText(pnl1, -1, STxt)
        vbox1.Add(self.st,  0, wx.EXPAND | wx.ALL)
        vbox1.Add(pnl1, 1, wx.EXPAND | wx.ALL, 3)
        vbox1.Add(pnl2, 1, wx.EXPAND | wx.ALL, 3)
        vbox2.Add(self.lc, 1, wx.EXPAND | wx.ALL, 3)
        self.tc1 = wx.ComboBox(pnl1, choices=sorted(charonifclib.IFCQTO.keys()))
        self.tc2 = wx.ComboBox(pnl1, choices=[]) #wx.TextCtrl(pnl1, -1)
        hbox1.Add(wx.StaticText(pnl1, -1, bt1),0, wx.ALIGN_CENTER)
        hbox1.Add(self.tc1, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        hbox2.Add(wx.StaticText(pnl1, -1, bt2),0, wx.ALIGN_CENTER)
        hbox2.Add(self.tc2, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        vbox3.Add(self.st, 1, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        vbox3.Add(hbox1,   1, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        vbox3.Add(hbox2,   1, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        pnl1.SetSizer(vbox3)
        vbox4.Add(wx.Button(pnl2,10,_('Add')),   0, wx.ALIGN_CENTER|wx.TOP, 45)
        vbox4.Add(wx.Button(pnl2,11,_('Remove')),0, wx.ALIGN_CENTER|wx.TOP, 15)
        vbox4.Add(wx.Button(pnl2,12,_('Clear')), 0, wx.ALIGN_CENTER|wx.TOP, 15)
        pnl2.SetSizer(vbox4)
        self.Bind (wx.EVT_BUTTON, self.OnAdd,    id=10)
        self.Bind (wx.EVT_BUTTON, self.OnRemove, id=11)
        self.Bind (wx.EVT_BUTTON, self.OnClear,  id=12)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelect)
        hbox.Add(vbox1, 1, wx.EXPAND)
        hbox.Add(vbox2, 1, wx.EXPAND)
        self.SetSizer(hbox)
        # list the section
        if self.config.has_section(self.cfg_section):
            # Python 2.7 ConfigParser retro-compatibility
            try:
                sect_list = self.config[self.cfg_section].items()
            except AttributeError:
                sect_list = self.config.items(self.cfg_section)
            # populate the list
            num_items = self.lc.GetItemCount()
            for key in sect_list:
                pos = self.lc.InsertStringItem(num_items, key[0])
                self.lc.SetStringItem(pos,1,key[1])
                num_items+=1
        else:
            raise AttributeError

    def OnAdd(self, event):
        if not self.tc1.GetValue():
            wx.LogError(_("Text box is empty."))
            return
        num_items = self.lc.GetItemCount()
        txt = self.tc1.GetValue()
        val = self.tc2.GetValue()
        pos = self.lc.InsertStringItem(num_items, txt)
        self.lc.SetStringItem(pos,1,val)
        self.tc1.SetValue('')
        self.tc2.SetValue('')
        # update the config file
        UpdateConfig(self.config, self.cfg_section, [(txt,val)])

    def OnRemove(self, event):
        index = self.lc.GetFocusedItem()
        elem = self.lc.GetItemText(index)
        dlg = wx.MessageBox(_("Do you want to delete {}?").format(elem),
                            _("Remove Calculation Rule"),
                            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg == wx.YES:
            self.lc.DeleteItem(index)
            # update the config file
            UpdateConfig(self.config, self.cfg_section, [(elem,0)])
        else:
            return

    def OnClear(self, event):
        dlg = wx.MessageBox(_("Do you really want to delete all sections?"),
                            _("Remove Calculation Rules"),
                            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg == wx.YES:
            self.lc.DeleteAllItems()
            # update the config file
            for e in self.config[self.cfg_section]:
               del self.config[self.cfg_section][e]
            write_config_file(self.config)
        else:
            return

    def OnSelect(self, event):
        if event.GetEventObject() is self.tc1:
            try:
                sel = sorted(charonifclib.IFCQTO[self.tc1.GetValue()])
            except AttributeError as err:
                return # do nothing for now
            self.tc2.SetItems(sel)

class PageSettings(wx.Panel):
    def __init__(self, parent):
        pnl = wx.Panel.__init__(self, parent)
        
        # read configuration file
        self.config = read_config_file()
        
        # setup local variables
        self.log_level = GetConfig(self.config, 'loglevel', is_int=True)
        self.log_filename = GetConfig(self.config, 'logfilename')
        self.fh = None # logger FileHandled
        
        # create the UI elements list
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        pnl1 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        
        # create radio buttons to select the output format
        FormatList = ['None', 'Debug', 'Information', 'Warning']
        self.rbox = wx.RadioBox(pnl1,
                                label = _("Logging Level"),
                                choices = FormatList,
                                majorDimension = 1,
                                style = wx.RA_SPECIFY_COLS)
        # setup radiobox option from config file
        if self.log_level is not None:
            if self.log_level == 0:
                self.rbox.SetSelection(0)
            elif self.log_level == 10:
                self.rbox.SetSelection(1)
            elif self.log_level == 20:
                self.rbox.SetSelection(2)
            elif self.log_level == 30:
                self.rbox.SetSelection(3)
        
        # add an option to save logging to file
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        # create a checkbox and a filebutton
        self.cb1 = wx.CheckBox(pnl1, label = _("Log to File"))
        if self.log_filename is not None:
            self.cb1.SetValue(True)
        self.button0 = wx.Button(pnl1, label=_("Choose Log File"))
        self.button0.Disable()
        # add the buttons in the UI
        hbox1.Add(self.cb1,    0, wx.ALIGN_LEFT | wx.ALL, border=20)
        hbox1.Add(self.button0,0, wx.ALIGN_LEFT | wx.ALL, border=20)
        # update the UI if the logfilename exists
        if self.log_filename is not None:
            # setup the name in the UI
            self.button0.SetLabel(self.log_filename)
            # check if checkbox is activated
            if self.cb1.GetValue():
                self.button0.Enable()
                self.fh = AddFileLogger(self.log_filename, self.log_level)
        
        # add buttons, radiobox, etc. to the vbox
        vbox1.Add(self.rbox,   0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(hbox1,       0, wx.ALIGN_LEFT | wx.ALL, border=20)
        
        # add the vbox to the panel
        pnl1.SetSizerAndFit(vbox1)
        
        # create bindings for each button
        self.rbox.Bind(wx.EVT_RADIOBOX,self.onRadioBox)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb1)
        self.Bind(wx.EVT_BUTTON,   self.onChooseFile, self.button0)


    def onRadioBox(self, event):
        rb = event.GetEventObject()
        if rb.GetStringSelection() == 'None':
            self.log_level = logging.NOTSET
        elif rb.GetStringSelection() == 'Information':
            self.log_level = logging.INFO
        elif rb.GetStringSelection() == 'Warning':
            self.log_level = logging.WARNING
        elif rb.GetStringSelection() == 'Debug':
            self.log_level = logging.DEBUG
        logger.setLevel(self.log_level)
        logging.info("Logging level set to: {}".format(self.log_level))
        # save the setting in config file
        SaveConfig(self.config, 'loglevel', self.log_level)
        
    def onChecked(self, event): 
        cb = event.GetEventObject()
        if cb is self.cb1:
            if cb.GetValue():
                self.button0.Enable()
                self.fh = AddFileLogger(self.log_filename, self.log_level)
                if self.fh is not None:
                    # add file handler
                    logging.info("Adding file logging")
            else:
                self.button0.Disable()
                self.log_filename = None
                logger.removeHandler(self.fh)
                logging.info("Removing file logging")

    def onChooseFile(self, event):
        # get the lastdir
        lastdir = GetConfig(self.config, "lastdir")
        if lastdir is None:
            lastdir = "~"
        
        # create the file dialog
        with wx.FileDialog(self, message=_("Choose a file"),
                           defaultDir=lastdir,
                           defaultFile="",
                           wildcard="",
                           style=wx.FD_SAVE) as fileDialog:

            # return if the user close the dialog
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            # Proceed saving the path
            self.log_filename = fileDialog.GetPath()
            SaveConfig(self.config, 'logfilename', self.log_filename)
            # add file handler
            self.fh = AddFileLogger(self.log_filename, self.log_level)
            logging.debug("Adding file logging")
            # update the UI
            self.button0.SetLabel(self.log_filename)
           
################################################################################
############ UPDATE CONFIG FILE SECTION ########################################
################################################################################

def UpdateConfig(config, section, t_list, filename=None):
    # parse a list of (option, value) tuples, update the section and save
    for option, value in t_list:
        if value == 0:
            # Python 2.7 compatibility
            try:
                del config[section][option]
            except AttributeError:
                config.remove_option(section, option)
        else:
            config.set(section, option, str(value))
    write_config_file(config, config_filename=filename)

def SaveConfig(config, key, value, section="USERSETTINGS", filename=None):
    # save the setting in config file
    # Python 2.7 compatibility
    value = str(value)
    try:
        config[section][key] = value
    except AttributeError:
        config.set(section, key, value)
    finally:
        write_config_file(config, config_filename=filename)

def GetConfig(config, key, is_int=False, bool=False, section="USERSETTINGS"):
    # save the setting in config file
    # Python 2.7 compatibility
    var = None
    if bool:
        var = False
    try:
        if is_int:
            var = int(config[section][key])
        elif bool:
            var = config[section].getboolean(key)
        else:
            var = config[section][key]
    except AttributeError:
        # Python 2.7 ConfigParser retro-compatibility
        try:
            if is_int:
                var = config.getint(section, key)
            elif bool:
                var = config.getboolean(section, key)
            else:
                var = config.get(section, key)
        except:
            logging.warning("'{}' not found in config file.".format(key))
    except KeyError:
        logging.warning("'{}' not found in config file.".format(key))
    # if var is boolean return false instead of None
    if bool and var is None:
        return False
    return var

def AddFileLogger(log_filename, log_level):
    """function to add a file logger to the logger object"""
    if log_filename is None:
        return None
    elif os.path.exists(os.path.dirname(log_filename)):
        # create file handler which logs even debug messages
        fh = logging.FileHandler(log_filename)
        fh.setLevel(log_level)
        # add the handlers to the logger
        logger.addHandler(fh)
        logging.info("Logging to:{} Level:{}".format(log_filename, log_level))
        return fh
    else:
        logging.error("Selected path {} does not exist".format(log_filename))
        return None
    
################################################################################
############ SPECIFICATION FRAME ###############################################
################################################################################

class SpecificationFrame(wx.Frame):
    """
    A Frame to choose the Specification Options and start the job.
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(SpecificationFrame, self).__init__(*args, **kw)

        # get the config file
        self.config = read_config_file()
        
        # options to extract all the objects properties
        self.ObjProp = False
        self.format = "docx"
        self.template = None
        # retrive title from config file
        self.title = GetConfig(self.config, 'title')
        if self.title is None:
            self.title = charonifclib.DEFAULT_TITLE
        
        # get the blacklists from config file
        # Python 2.7 ConfigParser retro-compatibility
        try:
            self.type_blacklist = self.config['BLACKLIST_IFCTYPE'].items()
            self.prop_blacklist = self.config['BLACKLIST_PROPERTY'].items()
        except AttributeError:
            self.type_blacklist = self.config.items('BLACKLIST_IFCTYPE')
            self.prop_blacklist = self.config.items('BLACKLIST_PROPERTY')
        
        #create the settings configuration
        self.settings = charonifclib.PrintSettings()
        
        # create a panel in the frame
        pnl = wx.Panel(self)

        #create a vbox to store the widgets and buttons
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        
        # create a check box for each required option
        self.cb1 = wx.CheckBox(pnl,
                               label = _("List Pset Properties for every IfcObject")
                               )

        # create radio buttons to select the output format
        self.formatdict = {'Word':         "docx", 
                           'OpenDocument': "odt", 
                           'RTF':          "rtf", 
                           'HTML':         "html", 
                           'Latex':        "latex",
                           'MediaWiki':    "mediawiki"}
        FormatList = sorted(self.formatdict.keys())
        self.rbox = wx.RadioBox(pnl,
                                label = _("Document Format"),
                                choices = FormatList,
                                majorDimension = 1,
                                style = wx.RA_SPECIFY_COLS)
        # get the last selection
        self.spefs = GetConfig(self.config, 'speformatselection', is_int=True)
        if self.spefs is not None:
            self.rbox.SetSelection(self.spefs)
            self.format = self.formatdict[FormatList[self.spefs]]
        
        # create a button to start the job
        self.button0 = wx.Button(pnl, label=_("Create the Specifications"))
        
        # create checkbox and a button for title setup
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb2 = wx.CheckBox(pnl, label = _("Use a custom title"))
        self.tc1 = wx.TextCtrl(pnl, -1)
        self.tc1.SetValue(self.title)
        self.tc1.Disable()
        hsizer1.Add(self.cb2, 0, wx.ALL, 20)
        hsizer1.Add(self.tc1, 0, wx.ALL, 20)
        
        # add a box to set the template file
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        # create checkbox and a button
        self.cb3 = wx.CheckBox(pnl,   label = _("Use a template"))
        self.button1 = wx.Button(pnl, label = _("Choose the template file"))
        self.button1.Disable()
        hsizer2.Add(self.cb3,     0, wx.ALL, 20)
        hsizer2.Add(self.button1, 0, wx.ALL, 20)
        
        # get the template name from config file
        self.ltemp = GetConfig(self.config, 'lastemplate')
        if self.ltemp is not None and os.path.exists(self.ltemp):
            self.button1.SetLabel(self.ltemp)
        
        # add buttons, radiobox, etc. to the vbox
        vbox1.Add(self.rbox,   0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(self.cb1,    0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(hsizer1,     0, wx.ALIGN_LEFT | wx.ALL, border=0)
        vbox1.Add(hsizer2,     0, wx.ALIGN_LEFT | wx.ALL, border=0)
        vbox1.Add(self.button0,0, wx.ALIGN_LEFT | wx.ALL, border=20)
        
        # add the vbox to the panel
        pnl.SetSizerAndFit(vbox1)
        
        # create bindings for each button
        self.Bind(wx.EVT_BUTTON,   self.OnCreateSpc,  self.button0)
        self.Bind(wx.EVT_BUTTON,   self.OnChooseFile, self.button1)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb1)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb2)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb3)
        self.rbox.Bind(wx.EVT_RADIOBOX,self.onRadioBox)
        
        # set the panel size
        self.SetSize(MIN_SIZE)

        # place the panel and show it
        self.Centre()
        self.Show(True)

    def EnableButton(self, event):
        myobject = event.GetEventObject()
        myobject.Enable()
    
    def onChecked(self, event): 
        cb = event.GetEventObject() 
        logging.debug("{0} {1} {2}".format(cb.GetLabel(),' is clicked',
                      cb.GetValue()))
        if cb is self.cb1:
            self.ObjProp = cb.GetValue()
        elif cb is self.cb2 and self.cb2.GetValue():
            self.tc1.Enable()
        elif cb is self.cb2 and not self.cb2.GetValue():
            self.tc1.Disable()
        elif cb is self.cb3 and self.cb3.GetValue():
            self.button1.Enable()
        elif cb is self.cb3 and not self.cb3.GetValue():
            self.button1.Disable()

    def onRadioBox(self, event):
        rb = event.GetEventObject()
        val = rb.GetSelection()
        self.spefs = SaveConfig(self.config, 'speformatselection', val)
        # assign the format variable
        self.format = self.formatdict[rb.GetStringSelection()]
        logging.debug("Chosen format: {}".format(self.format))


    def OnChooseFile(self, event):
        """Display a file chooser Dialog"""

        # create the file dialog
        with wx.FileDialog(self, message=_("Choose an Template file"),
                           defaultDir="",
                           defaultFile="",
                           wildcard="*.{}".format(self.format),
                           style=wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST
                           ) as fileDialog:

            # get the last template chosen by the user from config file
            if self.ltemp is not None:
                # setup the last saved directory
                if os.path.exists(self.ltemp):
                    fileDialog.SetDirectory(self.ltemp)
                else:
                    logging.info("Template {} does not exist.".format(self.ltemp))
            # return if the user close the dialog
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            template = fileDialog.GetPath()
            SaveConfig(self.config, 'lastemplate', template)
            # open the IFC file
            try:
                with open(template, 'r') as file:
                    # change the button1 name
                    self.button1.SetLabel(template)
                return template
            except IOError:
                wx.LogError("Cannot open file '%s'." % template)


    def OnCreateSpc(self, event):
        """Create the Specifications"""
        
        # get the title if we set it
        if self.cb2.GetValue() and self.tc1.GetValue():
            self.title = self.tc1.GetValue()
            logging.info("Using custom title: {}".format(self.title))
        
        # get the template and use it if set
        template = self.button1.GetLabel()
        if self.cb3.GetValue() and os.path.exists(template):
            self.template = template
            logging.info("Using custom template: {}".format(self.template))
        
        # create a wait dialog
        wait = wx.BusyInfo(_("Please wait, working..."))
        
        # run the program
        try:
            #Create a memory structure for each IFC object
            IfcLib = charonifclib.IfcParser(IFCfile)
            #create a format agnostic markup text
            MarkedUpText = IfcLib.MarkUpText(self.title, 
                                             self.type_blacklist,
                                             self.prop_blacklist,
                                             self.ObjProp,
                                             self.settings)
            
            # refresh the UI
            wx.GetApp().Yield()
            # create the output file
            if test_pandoc():
                # use 'pandoc' to create the output with the desired format
                outfile = charonifclib.PandocConverter(MarkedUpText, 
                                                       self.format, 
                                                       IFCfile, 
                                                       self.template)
            else:
                # create HTML file
                outfile = charonifclib.HtmlConverter(MarkedUpText,
                                                     IFCfile)
        except charonifclib.CharonIfcError as err:
            wx.LogError("Error, unable to continue: {0}".format(err))
            del wait
            return
        # close the wait dialog
        del wait
        
        # if all went well check if the file exists and display a message
        if os.path.exists(outfile):
            wx.LogMessage(_("Document Created: {}.").format(outfile))
        else:
            wx.LogError(_("Unable to create the document."))
        
        # close the window
        self.Show(False)
    
################################################################################
############ BOQ FRAME #########################################################
################################################################################

class BOQFrame(wx.Frame):
    """
    A Frame to choose the BOQ Options and start the job.
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(BOQFrame, self).__init__(*args, **kw)

        # IFC file and other options
        self.output = None
        self.list_price = False
        self.templfile = None
        self.addrebars = False
        self.sortbyspace = False
        self.importfile = None

        # get the blacklists from config file
        self.config = read_config_file()
        
        # create a panel in the frame
        pnl = wx.Panel(self)
        
        # create a vbox to store the widgets and buttons
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        
        # create radio buttons to select the output format
        self.formatdict =  {'CSV':         "csv",
                            'Primus PWE':  "pwe", 
                            'Primus XPWE': "xpwe", 
                            'Dump SQL':    "sql"}
        FormatList = sorted(self.formatdict.keys())
        self.rbox = wx.RadioBox(pnl,
                                label = _("File Format"),
                                choices = FormatList,
                                majorDimension = 1,
                                style = wx.RA_SPECIFY_COLS)
        # get the last selection
        self.boqfs = GetConfig(self.config, 'boqformatselection', is_int=True)
        if self.boqfs is not None:
            self.rbox.SetSelection(self.boqfs)
            self.output = self.formatdict[FormatList[self.boqfs]]
        
        # create an option to add Forms and Rebars for Concrete
        self.cb1 = wx.CheckBox(pnl, label = _("Add Concrete Forms and Rebars"))
        self.addrebars = GetConfig(self.config, 'addrebars', bool=True)
        self.cb1.SetValue(self.addrebars)
        
        # also create a template fo fill in
        self.cb2 = wx.CheckBox(pnl,
                               label=_("Create template for Tag associations"))
        
        # create a checkbox and a button to select a template file
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb3 = wx.CheckBox(pnl, label = _("Use a template"))
        # get the last chosen name from config file
        self.button0 = wx.Button(pnl, label=_("Choose the model file"))
        self.button0.Disable()
        hsizer1.Add(self.cb3,     0, wx.ALL, 20)
        hsizer1.Add(self.button0, 0, wx.ALL, 20)
        # get the template name from config file
        ltemp = GetConfig(self.config, 'boqtemplate')
        if ltemp is not None and os.path.exists(ltemp):
            self.button0.SetLabel(ltemp)
            if self.cb3.GetValue():
                self.templfile = ltemp
        
        # import a BOQ from Primus or SIX format
        # add a box to set the template file
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        # create checkbox and a button
        self.cb4 = wx.CheckBox(pnl,   label = _("Import A Primus or SIX file"))
        self.button1 = wx.Button(pnl, label = _("Choose the file to import"))
        self.button1.Disable()
        hsizer2.Add(self.cb4,     0, wx.ALL, 20)
        hsizer2.Add(self.button1, 0, wx.ALL, 20)
        # get the import file name from config file
        impfile = GetConfig(self.config, 'boqimportfile')
        if impfile is not None and os.path.exists(impfile):
            self.button1.SetLabel(impfile)
            if self.cb4.GetValue():
                self.importfile = impfile

        # create checkbox for sort-by-space option
        hsizer3 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb5 = wx.CheckBox(pnl,   label = _("Sort items by Space"))
        self.sortbyspace = GetConfig(self.config, 'sortbyspace', bool=True)
        self.cb5.SetValue(self.sortbyspace)
        hsizer3.Add(self.cb5,     0, wx.ALL, 20)
        
        # create a button to start the job
        self.button2 = wx.Button(pnl, label=_("Create the BOQ"))
        
        # add the buttons to vbox
        vbox1.Add(self.rbox,   0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(self.cb1,    0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(self.cb2,    0, wx.ALIGN_LEFT | wx.ALL, border=20)
        vbox1.Add(hsizer1,     0, wx.ALIGN_LEFT | wx.ALL, border=0)
        vbox1.Add(hsizer2,     0, wx.ALIGN_LEFT | wx.ALL, border=0)
        vbox1.Add(hsizer3,     0, wx.ALIGN_LEFT | wx.ALL, border=0)
        vbox1.Add(self.button2,0, wx.ALIGN_LEFT | wx.ALL, border=20)
        
        # add the vbox to the panel
        pnl.SetSizerAndFit(vbox1)
        
        # create the bindings for buttons and chackbox
        self.rbox.Bind(wx.EVT_RADIOBOX,self.onRadioBox)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb1)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb2)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb3)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb4)
        self.Bind(wx.EVT_CHECKBOX, self.onChecked,    self.cb5)
        self.Bind(wx.EVT_BUTTON,   self.OnChooseFile, self.button0)
        self.Bind(wx.EVT_BUTTON,   self.OnChooseFile, self.button1)
        self.Bind(wx.EVT_BUTTON,   self.OnCreateBOQ,  self.button2)
        
        # set the panel size
        self.SetSize(MIN_SIZE)
        
        # center the panel and show it
        self.Centre()
        self.Show(True)

    def onRadioBox(self, event):
        rb = event.GetEventObject()
        val = rb.GetSelection()
        SaveConfig(self.config, 'boqformatselection', val)
        # set the chosen output format
        self.output = self.formatdict[rb.GetStringSelection()]
        logging.debug("Chosen format: {}".format(self.output))
    
    def onChecked(self, event): 
        cb = event.GetEventObject() 
        logging.debug("{0} {1} {2}".format(cb.GetLabel(),' is clicked',
                      cb.GetValue()))
        if cb is self.cb1:
            self.addrebars = cb.GetValue()
            SaveConfig(self.config, 'addrebars', self.addrebars)
        if cb is self.cb2:
            self.list_price = cb.GetValue()
        elif cb is self.cb3 and self.cb3.GetValue():
            self.button0.Enable()
            if os.path.exists(self.button0.GetLabel()):
                self.templfile = self.button0.GetLabel()
        elif cb is self.cb3 and not self.cb3.GetValue():
            self.button0.Disable()
            self.templfile = None
        elif cb is self.cb4 and self.cb4.GetValue():
            self.button1.Enable()
            if os.path.exists(self.button1.GetLabel()):
                self.importfile = self.button1.GetLabel()
        elif cb is self.cb4 and not self.cb4.GetValue():
            self.button1.Disable()
            self.importfile = None
        elif cb is self.cb5:
            self.sortbyspace = cb.GetValue()
            SaveConfig(self.config, 'sortbyspace', self.sortbyspace)

    def OnChooseFile(self, event):
        """Display a file chooser Dialog"""

        # check the origin event and setup the filechooser widget
        widget = event.GetEventObject()
        if widget is self.button0:
            wldc = "*.cfg"
        elif widget is self.button1:
            wldc = "{}|{}|{}".format("Primus PWE files (*.pwe)|*.pwe",
                                     "Primus XPWE files (*.xpwe)|*.xpwe",
                                     "STR SIX files (*.xml)|*.xml")
        # create the file dialog
        with wx.FileDialog(self, message=_("Choose a file"),
                           defaultDir="",
                           defaultFile="",
                           wildcard=wldc,
                           style=wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST
                           ) as fileDialog:

            # get the last template chosen by the user from config file
            if widget is self.button0 and self.templfile is not None:
                # setup the last saved directory
                if os.path.exists(self.templfile):
                    fileDialog.SetDirectory(os.path.dirname(self.templfile))
                else:
                    logging.info("Template {} does't exist.".format(self.templfile))
            elif widget is self.button1 and self.importfile is not None:
                # setup the last saved directory
                if os.path.exists(self.importfile):
                    fileDialog.SetDirectory(os.path.dirname(self.importfile))
                else:
                    logging.info("File {} does not exist.".format(self.importfile))
            # return if the user close the dialog
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            chosenfile = fileDialog.GetPath()
            # save the last chosen template or input file
            if widget is self.button0:
                SaveConfig(self.config, 'boqtemplate', chosenfile)
            elif widget is self.button1:
                SaveConfig(self.config, 'boqimportfile', chosenfile)
            
            # open the chosen file
            try:
                with open(chosenfile, 'r') as file:
                    # change the button name
                    if widget is self.button0:
                        self.button0.SetLabel(chosenfile)
                    elif widget is self.button1:
                        self.button1.SetLabel(chosenfile)
                return chosenfile
            except IOError:
                wx.LogError("Cannot open file '%s'." % chosenfile)
    
    def OnCreateBOQ(self, event):
        """Create the Bill Of Quantities"""
        
        # get the template and use it if was set
        templfile = self.button0.GetLabel()
        if self.cb3.GetValue() and os.path.dirname(templfile):
            self.templfile = templfile
            logging.info("Using custom template: {}".format(self.templfile))
        
        # get the template and use it if was set
        importfile = self.button1.GetLabel()
        if self.cb4.GetValue() and os.path.dirname(importfile):
            self.importfile = importfile
            logging.info("Importing file: {}".format(self.importfile))
        
        # ask the user if he wants to overwrite the template file
        targetfile = "{}.cfg".format(os.path.splitext(IFCfile)[0])
        if self.list_price is True and os.path.exists(targetfile):
            # ask the user if he wants to overwrite the file
            dlg = wx.MessageBox(_("""{} already exists."""
                                  """Do you want ot override it?""").format(
                                  targetfile),
                                _("Confirm Overwrite"),
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            if dlg == wx.NO:
                return
        
        # create a wait dialog
        wait = wx.BusyInfo(_("Please wait, working..."))
        
        # run the program
        try:
            boq = charonifclib.IfcBOQ(IFCfile, output=self.output, 
                                      list_price=self.list_price, 
                                      assolist=self.templfile,
                                      add_concrete_rebars=self.addrebars,
                                      sort_by_space=self.sortbyspace,
                                      import_price_list=self.importfile)
        except charonifclib.CharonIfcError as err:
            wx.LogError(_("Error: {}").format(err))
        else:
            wx.LogMessage(_("BOQ '{}' Created.").format(boq.GetOutputFile()))
        finally:
            # close the wait dialog
            del wait
            
        # close the window
        self.Show(False)

################################################################################
############ CONFIG FILE EDITOR ################################################
################################################################################

class ConfigEditorFrame(wx.Frame):
    """
    A Frame to edit config files.
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(ConfigEditorFrame, self).__init__(*args, **kw)

        # read configuration file
        self.cfgfile = kw["title"]
        self.config = read_config_file(config_filename=self.cfgfile,
                                       check_required_sections=False)
        # create the UI elements list
        hbox  = wx.BoxSizer(wx.HORIZONTAL)
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        
        # create a list control
        self.lc = wx.TreeCtrl(self, style=wx.TR_EDIT_LABELS | wx.TR_HAS_BUTTONS
                              | wx.TR_ROW_LINES)
        root = self.lc.AddRoot(self.cfgfile)

        # list the section and add the items
        num_items = 0
        for section in self.config.sections():
            sec = self.lc.AppendItem(root, section)
            self.lc.SetItemBold(sec)
            num_items+=1
            # Python 2.7 ConfigParser retro-compatibility
            try:
                sectionlist = self.config[section].items()
            except AttributeError:
                sectionlist = self.config.items(section)
            # populate the list
            for key,value in sectionlist:
                pos = self.lc.AppendItem(sec, key)
                val = self.lc.AppendItem(pos, value)
                num_items+=1
        vbox1.Add(self.lc, 1, wx.EXPAND | wx.ALL, 3)
        hbox.Add(vbox1, 1, wx.EXPAND)
        self.SetSizer(hbox)
        
        # expand the tree
        self.lc.ExpandAll()
        
        # set the size
        self.SetSize(MIN_SIZE)
        
        # add binding actions
        self.lc.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.ContextMenu)
        self.lc.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEdit)

    def ContextMenu(self, event):
        """Popup a context menu when right-clicking on items"""
        item = event.GetItem() #Get the current row
        new_data = event.GetLabel() #Get the changed data
        # create a menu
        menu = wx.Menu()
        # expand all button for root
        if self.lc.GetRootItem() == item:
            mi1 = wx.MenuItem(menu, wx.NewId(), _("Expand All"))
            menu.AppendItem(mi1)
            self.Bind(wx.EVT_MENU, self.OnExpandAll, mi1)
        # if item is a 'value' do show the edit menu
        elif not self.lc.ItemHasChildren(item) and not self.lc.IsBold(item):
            mi1 = wx.MenuItem(menu, wx.NewId(), _("Edit"))
            menu.AppendItem(mi1)
            self.Bind(wx.EVT_MENU, self.OnKeyEdit, mi1)
        # create an add button
        elif self.lc.IsBold(self.lc.GetFocusedItem()):
            mi1 = wx.MenuItem(menu, wx.NewId(), _("Add"))
            menu.AppendItem(mi1)
            self.Bind(wx.EVT_MENU, self.OnAdd,    mi1)
        else:
            # create a remove button
            mi2 = wx.MenuItem(menu, wx.NewId(), _("Remove"))
            menu.AppendItem(mi2)
            self.Bind(wx.EVT_MENU, self.OnRemove, mi2)
        # show the menu where the mouse cursor is located
        self.PopupMenu(menu, event.GetPoint())

    def OnAdd(self, event, *args):
        """Function to add an element and save the config file"""
        # append a new item
        if self.lc.IsBold(self.lc.GetFocusedItem()):
            child = self.lc.GetFocusedItem()
        else:
            dlg = wx.MessageBox(_("Do you want to add '{}'?"),
                            _("Add Configuration Key"),
                            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            return
        # add key, value and expand the tree
        # popup menu to insert key and value
        dlg = wx.TextEntryDialog(None, _("Enter the key name"), "Add Key")
        with dlg as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                # assign key and value strings
                NewKey = dlg.GetValue()
                NewValue = "NewValue"
            else:
                # handle dialog being cancelled or ended by some other button
                return
        pos = self.lc.AppendItem(child, NewKey)
        val = self.lc.AppendItem(pos, NewValue)
        self.lc.ExpandAllChildren(pos)
        # save the data
        key = self.lc.GetItemText(pos)
        value = self.lc.GetItemText(val)
        sec = self.lc.GetItemText(child)
        # save the data
        SaveConfig(self.config, key, value, section=sec, filename=self.cfgfile)

    def OnRemove(self, event):
        """Function to remove an element and save the config file"""
        # get the focused row
        item = self.lc.GetFocusedItem()
        # if the wrong key or section has been selected exit
        if item == self.lc.GetRootItem() or self.lc.IsBold(item):
            # popup an error message
            wx.MessageBox(_("You can't delete this section"), "Error",
                          wx.OK | wx.OK_DEFAULT | wx.ICON_ERROR)
            return
        # get the key
        key = self.lc.GetItemText(self.lc.GetFocusedItem())
        # popup a confirmation message
        dlg = wx.MessageBox(_("Do you want to delete '{}'?").format(key),
                            _("Remove Configuration Key"),
                            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg == wx.YES:
            # detete the item from UI
            self.lc.Delete(self.lc.GetFocusedItem())
            # get the section and delete the key
            parent = self.lc.GetItemParent(item)
            if not self.lc.IsBold(parent):
                raise AttributeError
            section = self.lc.GetItemText(parent)
            UpdateConfig(self.config, section, [key, 0], filename=self.cfgfile)
        else:
            return

    def OnEdit(self, event, *args):
        """Function to edit an element and save the config file"""
        # get the focused row
        item = event.GetItem()
        # this case check if the edited label is a section name or root
        if item == self.lc.GetRootItem() or self.lc.IsBold(item):
            # popup an error message
            wx.MessageBox(_("Impossible to change section name"), "Error",
                          wx.OK | wx.OK_DEFAULT | wx.ICON_ERROR)
            return
        # check if the label is a key
        elif self.lc.IsBold(self.lc.GetItemParent(item)):
            key = event.GetLabel()
            old_key = self.lc.GetItemText(self.lc.GetFocusedItem())
            sec = self.lc.GetItemText(self.lc.GetItemParent(item))
            value = GetConfig(self.config, old_key, section=sec)
        # check if the label is a value
        else:
            value = event.GetLabel()
            parent = self.lc.GetItemParent(item)
            key = self.lc.GetItemText(parent)
            if self.lc.IsBold(self.lc.GetItemParent(parent)):
                sec = self.lc.GetItemText(self.lc.GetItemParent(parent))
            else:
                raise AttributeError
        # log the data
        logging.info("Section:{2} key:{0} val:{1}".format(key,value,sec))
        # save the data
        SaveConfig(self.config, key, value, section=sec, filename=self.cfgfile)

    def OnExpandAll(self, event, *args):
        """Function to expand the entire tree"""
        # expand all
        self.lc.ExpandAll()

    def OnKeyEdit(self, event, *args):
        """Function to edit a key"""
        # popup menu to insert key and value
        dlg = wx.TextEntryDialog(None, _("Enter the Value"), "Edit Value")
        # get the selected cell
        item = self.lc.GetFocusedItem()
        # set the current text in the dialog
        dlg.SetValue(self.lc.GetItemText(item))
        with dlg as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                # assign key and value strings
                value = dlg.GetValue()
            else:
                # handle dialog being cancelled or ended by some other button
                return
        # set text in the selected cell
        self.lc.SetItemText(item, value)
        # get parent and grandparent
        parent = self.lc.GetItemParent(item)
        grandparent = self.lc.GetItemParent(parent)
        # get item string
        key = self.lc.GetItemText(parent)
        sec = self.lc.GetItemText(grandparent)
        # log the data
        logging.info("Section:{2} key:{0} val:{1}".format(key,value,sec))
        # save the data
        SaveConfig(self.config, key, value, section=sec, filename=self.cfgfile)

################################################################################
############ START MAIN LOOP ###################################################
################################################################################

def main():
    # When this module is run create the app, the frame, show it, 
    # and start the event loop.
    app = wx.App()
    frm = CharonIfcFrame(None, title='CharonIFC')
    frm.Show()
    app.MainLoop()

################################################################################
############ MAIN LOOP #########################################################
################################################################################

if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    main()
