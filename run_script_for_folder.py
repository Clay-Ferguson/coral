#!/usr/bin/env python3
"""
Script execution functionality for the Coral Nautilus extension.

This module provides the ability to run user-defined scripts from the YAML config
file against selected folders in the Nautilus file manager context menu.
"""

import os
import urllib.parse
import subprocess

# Try to import yaml for config file support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class OpenFolderHandler:
    """Handles running user-defined scripts against selected folders."""
    
    def __init__(self, config_file):
        """
        Initialize the OpenFolderHandler.
        
        Args:
            config_file (str): Path to the YAML configuration file
        """
        self.config_file = config_file
    
    def _load_config(self):
        """
        Load configuration from YAML file.
        
        Returns:
            dict: Configuration dictionary, or empty dict if config can't be loaded.
        """
        if not YAML_AVAILABLE:
            return {}
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                print(f"Config file not found: {self.config_file}")
                return {}
        except Exception as e:
            print(f"Error loading config file: {e}")
            return {}
    
    def get_scripts(self):
        """
        Get the list of scripts defined in the config file.
        
        Returns:
            list: List of script dictionaries with 'name' and 'content' keys.
                  Returns empty list if no scripts are defined or config unavailable.
        """
        config = self._load_config()
        
        try:
            scripts = config.get('scripts', [])
            if isinstance(scripts, list):
                # Filter to only include valid script entries (must have name and content)
                return [s for s in scripts if isinstance(s, dict) and 'name' in s and 'content' in s]
            else:
                return []
        except Exception as e:
            print(f"Error reading scripts from config: {e}")
            return []
    
    def run_script_for_folder(self, menu, folder, script_name):
        """
        Run a named script from the config with the selected folder.
        
        This method executes a script defined in the YAML config file, replacing
        the $OPEN_FOLDER variable with the path of the selected folder.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            folder (Nautilus.FileInfo): The folder to pass to the script.
            script_name (str): The name of the script to run from the config.
        
        Behavior:
            - Looks up the script by name in the config file
            - Replaces $OPEN_FOLDER with the actual folder path
            - Executes the script using bash in a subprocess
            - Uses subprocess.Popen for non-blocking execution
        """
        if not folder.get_uri().startswith('file://'):
            print(f"Invalid URI: {folder.get_uri()}")
            return
        
        folder_path = urllib.parse.unquote(folder.get_uri()[7:])
        
        # Find the script by name
        scripts = self.get_scripts()
        script_content = None
        for script in scripts:
            if script.get('name') == script_name:
                script_content = script.get('content', '')
                break
        
        if not script_content:
            print(f"Script not found: {script_name}")
            return
        
        # Replace $OPEN_FOLDER with the actual folder path
        # Use quotes around the path to handle spaces and special characters
        script_content = script_content.replace('$OPEN_FOLDER', f'"{folder_path}"')
        
        try:
            # Execute the script using bash
            subprocess.Popen(['bash', '-c', script_content])
        except Exception as e:
            print(f"Error executing script '{script_name}': {e}")
