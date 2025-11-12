#!/usr/bin/env python3

import os
import urllib.parse
import subprocess
import mimetypes
from datetime import datetime
from gi.repository import Nautilus, GObject, GLib

# Import our handlers
from search import SearchHandler
from new_markdown import MarkdownHandler
from open_in_vscode import VSCodeHandler
from run_script import ScriptRunner

# Try to import yaml for config file support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not available. Config file features will be disabled.")

class AddNautilusMenuItems(GObject.GObject, Nautilus.MenuProvider):
    """
    A Nautilus file manager extension that adds developer-focused context menu actions.
    
    This extension provides convenient right-click menu options for developers working
    with files and folders in the GNOME Nautilus file manager. It supports creating
    markdown files, opening files/folders in VSCode, and executing shell scripts.
    
    Inherits from:
        GObject.GObject: Base class for GObject-based objects
        Nautilus.MenuProvider: Interface for providing custom menu items in Nautilus
    
    Class Constants:
        VSCODE_PATH (str): Path to the VSCode executable
        TEXT_FILE_EXTENSIONS (tuple): File extensions considered as text files
    
    Menu Actions Provided:
        - New Markdown: Creates timestamped markdown files
        - Open in VSCode: Opens files/folders in Visual Studio Code
        - Run Script: Executes shell scripts in a new terminal
    """
    VSCODE_PATH = '/usr/bin/code'
    TEXT_FILE_EXTENSIONS = ('.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml', '.ini', '.cfg', '.conf')
    CONFIG_FILE = os.path.expanduser('~/.config/coral/coral-config.yaml')
    
    def __init__(self):
        """
        Initialize the Nautilus extension.
        
        Calls the parent class constructor to properly initialize the GObject
        and Nautilus MenuProvider interfaces. This method is called automatically
        when Nautilus loads the extension.
        """
        super().__init__()
        # Initialize the handlers
        self.search_handler = SearchHandler(self.VSCODE_PATH, self.CONFIG_FILE)
        self.markdown_handler = MarkdownHandler(self.VSCODE_PATH)
        self.vscode_handler = VSCodeHandler(self.VSCODE_PATH)
        self.script_runner = ScriptRunner()


    def get_file_items(self, files):
        """
        Add context menu items when files or folders are selected.
        
        This method is called by Nautilus when the user right-clicks on selected
        files or folders. It analyzes the selection and provides appropriate menu
        items based on the file type and context.
        
        Args:
            files (list): List of Nautilus.FileInfo objects representing selected files/folders.
                         Only processes single selections (len(files) == 1).
        
        Returns:
            list: List of Nautilus.MenuItem objects to display in the context menu.
                  Returns empty list if multiple files are selected.
        
        Menu Items Added:
            - New Markdown: Always available for any single selection
            - Search: Available for directories to perform recursive text search
            - Run Script: Available for .sh files
            - Open in VSCode: Available for directories and text files
        
        File Type Detection:
            Uses dual detection strategy:
            1. MIME type analysis via mimetypes.guess_type()
            2. File extension matching against TEXT_FILE_EXTENSIONS
        """
        if len(files) != 1:
            return []
        
        file = files[0]
        items = []
        
        # Always add New Markdown option first (works for any selection)
        new_markdown_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::new_markdown_from_selection',
            label='New Markdown',
            tip='Create a new timestamped markdown file and open in VSCode'
        )
        new_markdown_item.connect('activate', self.new_markdown_from_selection, file)
        items.append(new_markdown_item)
        
        # Check if it's a shell script
        if not file.is_directory() and file.get_name().endswith('.sh'):
            run_script_item = Nautilus.MenuItem(
                name='AddNautilusMenuItems::run_script',
                label='Run Script',
                tip='Run this shell script in a new terminal'
            )
            run_script_item.connect('activate', self.run_script, file)
            items.append(run_script_item)
        
        # Check if it's a folder or a text file
        if file.is_directory():
            vscode_item = Nautilus.MenuItem(
                name='AddNautilusMenuItems::open_in_vscode',
                label='Open in VSCode',
                tip='Open this folder in Visual Studio Code'
            )
            vscode_item.connect('activate', self.open_in_vscode, file)
            items.append(vscode_item)
        elif not file.is_directory():
            # Check if it's a text file using mimetypes
            filename = file.get_name()
            mimetype, _ = mimetypes.guess_type(filename)
            
            # Consider it a text file if mimetype starts with 'text/' or if it's a known text extension
            is_text_file = (mimetype and mimetype.startswith('text/')) or \
                          filename.endswith(self.TEXT_FILE_EXTENSIONS)
            
            if is_text_file:
                vscode_item = Nautilus.MenuItem(
                    name='AddNautilusMenuItems::open_file_in_vscode',
                    label='Open in VSCode',
                    tip='Open this file in Visual Studio Code'
                )
                vscode_item.connect('activate', self.open_in_vscode, file)
                items.append(vscode_item)
        
        # Add Open Coral Configs option
        config_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::open_coral_configs',
            label='Open Coral Configs',
            tip='Open Coral configuration file in VSCode'
        )
        config_item.connect('activate', self.open_coral_configs)
        items.append(config_item)
        
        # Add Search submenu for directories (at the end)
        if file.is_directory():
            search_parent = Nautilus.MenuItem(
                name='AddNautilusMenuItems::search_parent',
                label='Search',
                tip='Search options'
            )
            
            # Create submenu
            search_submenu = Nautilus.Menu()
            
            # Literal search option
            literal_item = Nautilus.MenuItem(
                name='AddNautilusMenuItems::search_literal',
                label='Literal',
                tip='Search for exact text (no special characters)'
            )
            literal_item.connect('activate', self.search_folder, file, 'literal')
            search_submenu.append_item(literal_item)
            
            # Basic regex search option
            regex_item = Nautilus.MenuItem(
                name='AddNautilusMenuItems::search_regex',
                label='Basic Regex',
                tip='Search using basic regular expressions'
            )
            regex_item.connect('activate', self.search_folder, file, 'regex')
            search_submenu.append_item(regex_item)
            
            # Extended regex search option
            extended_item = Nautilus.MenuItem(
                name='AddNautilusMenuItems::search_extended',
                label='Extended Regex',
                tip='Search using extended regular expressions (|, +, ?, etc.)'
            )
            extended_item.connect('activate', self.search_folder, file, 'extended')
            search_submenu.append_item(extended_item)
            
            # Attach submenu to parent
            search_parent.set_submenu(search_submenu)
            items.append(search_parent)
        
        return items

    def get_background_items(self, current_folder):
        """
        Add context menu items when right-clicking on empty space in Nautilus.
        
        This method is called by Nautilus when the user right-clicks on empty space
        within a folder view, providing context menu options relevant to the current
        directory without any specific file selection.
        
        Args:
            current_folder (Nautilus.FileInfo): Object representing the current folder
                                               being viewed in Nautilus.
        
        Returns:
            list: List of Nautilus.MenuItem objects to display in the context menu.
        
        Menu Items Added:
            - New Markdown: Creates a new timestamped markdown file in current folder
            - Search: Recursively search for text in the current folder
            - Open in VSCode: Opens the current folder in Visual Studio Code
        """
        items = []
        
        # New Markdown file option
        new_markdown_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::new_markdown',
            label='New Markdown',
            tip='Create a new timestamped markdown file and open in VSCode'
        )
        new_markdown_item.connect('activate', self.new_markdown, current_folder)
        items.append(new_markdown_item)
        
        # Open current folder in VSCode option
        vscode_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::open_current_in_vscode',
            label='Open in VSCode',
            tip='Open current folder in Visual Studio Code'
        )
        vscode_item.connect('activate', self.open_in_vscode, current_folder)
        items.append(vscode_item)
        
        # Open Coral Configs option
        config_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::open_coral_configs_bg',
            label='Open Coral Configs',
            tip='Open Coral configuration file in VSCode'
        )
        config_item.connect('activate', self.open_coral_configs)
        items.append(config_item)
        
        # Search submenu for current folder (at the end)
        search_parent = Nautilus.MenuItem(
            name='AddNautilusMenuItems::search_current_parent',
            label='Search',
            tip='Search options'
        )
        
        # Create submenu
        search_submenu = Nautilus.Menu()
        
        # Literal search option
        literal_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::search_current_literal',
            label='Literal',
            tip='Search for exact text (no special characters)'
        )
        literal_item.connect('activate', self.search_folder, current_folder, 'literal')
        search_submenu.append_item(literal_item)
        
        # Basic regex search option
        regex_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::search_current_regex',
            label='Basic Regex',
            tip='Search using basic regular expressions'
        )
        regex_item.connect('activate', self.search_folder, current_folder, 'regex')
        search_submenu.append_item(regex_item)
        
        # Extended regex search option
        extended_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::search_current_extended',
            label='Extended Regex',
            tip='Search using extended regular expressions (|, +, ?, etc.)'
        )
        extended_item.connect('activate', self.search_folder, current_folder, 'extended')
        search_submenu.append_item(extended_item)
        
        # Attach submenu to parent
        search_parent.set_submenu(search_submenu)
        items.append(search_parent)
        
        return items

    def search_folder(self, menu, folder, search_type='literal'):
        """
        Delegate to the search handler for folder search operations.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual search functionality to the SearchHandler.
        """
        self.search_handler.search_folder(menu, folder, search_type)

    def new_markdown_from_selection(self, menu, selected_item):
        """
        Delegate to the markdown handler for creating markdown from selection.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual markdown creation to the MarkdownHandler.
        """
        self.markdown_handler.new_markdown_from_selection(menu, selected_item)

    def new_markdown(self, menu, current_folder):
        """
        Delegate to the markdown handler for creating markdown in current folder.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual markdown creation to the MarkdownHandler.
        """
        self.markdown_handler.new_markdown(menu, current_folder)

    def open_in_vscode(self, menu, file):
        """
        Delegate to the VSCode handler for opening files/folders in VSCode.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual VSCode opening to the VSCodeHandler.
        """
        self.vscode_handler.open_in_vscode(menu, file)

    def run_script(self, menu, file):
        """
        Delegate to the script runner for executing shell scripts.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual script execution to the ScriptRunner.
        """
        self.script_runner.run_script(menu, file)

    def open_coral_configs(self, menu, file=None):
        """
        Open the Coral configuration file in Visual Studio Code.
        
        This method opens the YAML configuration file located at
        ~/.config/coral/coral-config.yaml directly in VSCode, allowing users
        to quickly edit their Coral settings.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            file (Nautilus.FileInfo, optional): The file context (unused, since we always
                                               open the config file regardless of context).
        
        Behavior:
            - Opens the config file at ~/.config/coral/coral-config.yaml
            - Uses the VSCode path specified in VSCODE_PATH constant
            - Launches VSCode with the config file as the target
            - Works from any context (file selection or background menu)
        """
        config_path = os.path.expanduser('~/.config/coral/coral-config.yaml')
        subprocess.Popen([self.VSCODE_PATH, config_path])

    
