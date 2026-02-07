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
        """Run a named script from the config with the selected folder."""
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
        script_content = script_content.replace('"$OPEN_FOLDER"', f'"{folder_path}"')
        script_content = script_content.replace('$OPEN_FOLDER', f'"{folder_path}"')

        try:
            # Build a wrapper script that sources initialization files directly.
            # This is more reliable than capturing/parsing env output because:
            # 1. It avoids issues with multi-line env values breaking parsing
            # 2. The bash process itself will have nvm loaded, not just passed env vars
            # 3. We preserve the current session's GUI environment (DISPLAY, DBUS, XDG_*)
            wrapper_script = f'''#!/bin/bash
# Ensure HOME is set (may be missing in D-Bus activated processes)
export HOME="${{HOME:-$(getent passwd $(id -u) | cut -d: -f6)}}"

# Source shell initialization files to get full user environment
# Order matters: profile first, then bashrc (like a login interactive shell)
[ -r /etc/profile ] && . /etc/profile
[ -r "$HOME/.bash_profile" ] && . "$HOME/.bash_profile"
[ -r "$HOME/.profile" ] && . "$HOME/.profile"
[ -r "$HOME/.bashrc" ] && . "$HOME/.bashrc"

# Explicitly initialize nvm if available (in case bashrc checks for interactivity)
export NVM_DIR="${{NVM_DIR:-$HOME/.nvm}}"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Run the actual user script
{script_content}
'''

            # Start with current environment to preserve GUI session variables
            # (DISPLAY, DBUS_SESSION_BUS_ADDRESS, XDG_*, etc.)
            env = os.environ.copy()

            # Ensure HOME is set in the initial environment
            if 'HOME' not in env:
                import pwd
                env['HOME'] = pwd.getpwuid(os.getuid()).pw_dir

            subprocess.Popen(
                ['bash', '-c', wrapper_script],
                env=env,
                start_new_session=True  # Properly detach from parent
            )
        except Exception as e:
            print(f"Error executing script '{script_name}': {e}")