#!/usr/bin/env python3

import os
import urllib.parse
import subprocess
import shutil
from gi.repository import Nautilus, GObject, GLib

# Import our handlers
from run_script import ScriptRunner
from run_script_for_folder import OpenFolderHandler

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
    with files and folders in the GNOME Nautilus file manager. It supports copying full
    paths, running custom scripts on folders, and executing shell scripts.
    
    Inherits from:
        GObject.GObject: Base class for GObject-based objects
        Nautilus.MenuProvider: Interface for providing custom menu items in Nautilus
    
    Class Constants:
        VSCODE_PATH (str): Path to the VSCode executable
        MENU_ICON (str): Unicode character used as visual marker for Coral menu items
    
    Menu Actions Provided:
        - Copy Full Path: Copies the selected item's full path to the clipboard
        - Custom Scripts: Run user-defined scripts on folders (configured via YAML)
        - Run Script: Executes shell scripts in a new terminal
    """
    VSCODE_PATH = '/usr/bin/code'
    CONFIG_FILE = os.path.expanduser('~/.config/coral/coral-config.yaml')
    MENU_ICON = '●  '
    
    def __init__(self):
        """
        Initialize the Nautilus extension.
        
        Calls the parent class constructor to properly initialize the GObject
        and Nautilus MenuProvider interfaces. This method is called automatically
        when Nautilus loads the extension.
        """
        super().__init__()
        # Initialize the handlers
        self.script_runner = ScriptRunner()
        self.open_folder_handler = OpenFolderHandler(self.CONFIG_FILE)


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
            - Copy Full Path: Always available for any single selection
            - Run Script: Available for .sh files
            - Custom Scripts: Available for directories (configured via YAML)
        """
        if len(files) != 1:
            return []
        
        file = files[0]
        items = []
        
        copy_full_path_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::copy_full_path',
            label='📋  Copy Full Path',
            tip='Copy the full path of the selected item to the clipboard'
        )
        copy_full_path_item.connect('activate', self.copy_full_path, file)
        items.append(copy_full_path_item)

        # Check if it's a shell script
        if not file.is_directory() and file.get_name().endswith('.sh'):
            run_script_item = Nautilus.MenuItem(
                name='AddNautilusMenuItems::run_script',
                label=f'{self.MENU_ICON}Run Script',
                tip='Run this shell script in a new terminal'
            )
            run_script_item.connect('activate', self.run_script, file)
            items.append(run_script_item)
        
        # Check if it's a folder - add script menu items
        if file.is_directory():
            # Add menu items for each script defined in the config
            scripts = self.open_folder_handler.get_scripts()
            for script in scripts:
                script_name = script.get('name', '')
                if script_name:
                    script_item = Nautilus.MenuItem(
                        name=f'AddNautilusMenuItems::run_script_{script_name}',
                        label=f'{script_name}',
                        tip=f'Run {script_name} script on this folder'
                    )
                    script_item.connect('activate', self.run_script_for_folder, file, script_name)
                    items.append(script_item)

        # Add Open Coral Configs option
        config_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::open_coral_configs',
            label=f'⚙️  Open Coral Configs',
            tip='Open Coral configuration file in VSCode'
        )
        config_item.connect('activate', self.open_coral_configs)
        items.append(config_item)
        
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
            - Open Coral Configs: Opens the Coral YAML config file in VSCode
        """
        items = []
        
        # Open Coral Configs option
        config_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::open_coral_configs_bg',
            label=f'⚙️  Open Coral Configs',
            tip='Open Coral configuration file in VSCode'
        )
        config_item.connect('activate', self.open_coral_configs)
        items.append(config_item)
        
        return items

    def run_script(self, menu, file):
        """
        Delegate to the script runner for executing shell scripts.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual script execution to the ScriptRunner.
        """
        self.script_runner.run_script(menu, file)

    def run_script_for_folder(self, menu, folder, script_name):
        """
        Delegate to the open folder handler for running scripts on folders.
        
        This is a wrapper method that maintains the existing menu interface
        while delegating the actual script execution to the OpenFolderHandler.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action.
            folder (Nautilus.FileInfo): The folder to pass to the script.
            script_name (str): The name of the script to run from the config.
        """
        self.open_folder_handler.run_script_for_folder(menu, folder, script_name)

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

    def copy_full_path(self, menu, selected_item):
        """
        Copy the selected file or folder path to the clipboard.
        """
        path = self._get_filesystem_path(selected_item)
        if not path:
            print('Copy Full Path: unable to resolve file path.')
            return

        if not shutil.which('xclip'):
            GLib.spawn_async(
                argv=['zenity', '--error', '--text=xclip is not installed.\n\nInstall it with:\n  sudo apt install xclip', '--width=400'],
                flags=GLib.SpawnFlags.SEARCH_PATH
            )
            return

        # Write path to a temp file so we can pipe it to xclip via bash
        # without blocking the Nautilus UI thread
        escaped_path = path.replace("'", "'\\''")
        GLib.spawn_async(
            argv=['bash', '-c', f"echo -n '{escaped_path}' | xclip -selection clipboard"],
            flags=GLib.SpawnFlags.SEARCH_PATH
        )

    def _get_filesystem_path(self, file_info):
        uri = file_info.get_uri()
        if not uri or not uri.startswith('file://'):
            return None
        return urllib.parse.unquote(uri[7:])

    
