#!/usr/bin/env python3
"""
VSCode integration functionality for the Coral Nautilus extension.

This module provides the ability to open files and folders in Visual Studio Code
directly from the Nautilus file manager context menu.
"""

import urllib.parse
import subprocess


class VSCodeHandler:
    """Handles opening files and folders in Visual Studio Code."""
    
    def __init__(self, vscode_path):
        """
        Initialize the VSCode handler.
        
        Args:
            vscode_path (str): Path to the VSCode executable
        """
        self.vscode_path = vscode_path
    
    # Functions will be moved here by the user
    def open_in_vscode(self, menu, file):
        """
        Open the selected file or folder in Visual Studio Code.
        
        This method handles the "Open in VSCode" action for both files and folders.
        It launches VSCode with the selected item as the target, allowing developers
        to quickly open their files or projects in their preferred editor.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            file (Nautilus.FileInfo): The file or folder to open in VSCode.
        
        Behavior:
            - Launches VSCode using the path specified in VSCODE_PATH class constant
            - Passes the file/folder path as an argument to VSCode
            - Works with both individual files and entire directories
            - Uses subprocess.Popen for non-blocking execution
        
        URI Handling:
            - Validates that the URI starts with 'file://' for local files
            - Uses urllib.parse.unquote to properly decode the file path
            - Handles file paths with spaces and special characters
        
        Integration:
            VSCode path is configurable via the VSCODE_PATH class constant,
            defaulting to '/usr/bin/code' for standard Linux installations.
        """
        if file.get_uri().startswith('file://'):
            path = urllib.parse.unquote(file.get_uri()[7:])
            subprocess.Popen([self.vscode_path, path])
