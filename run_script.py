#!/usr/bin/env python3
"""
Script execution functionality for the Coral Nautilus extension.

This module provides the ability to run shell scripts (.sh files) in a new
terminal window directly from the Nautilus file manager context menu.
"""

import os
import urllib.parse
import subprocess


class ScriptRunner:
    """Handles execution of shell scripts in terminal windows."""
    
    def __init__(self):
        """Initialize the script runner."""
        pass
    
    # Functions will be moved here by the user
    def run_script(self, menu, file):
        """
        Execute the selected shell script in a new terminal window.
        
        This method handles the "Run Script" action for .sh files. It opens a new
        gnome-terminal window, navigates to the script's directory, and executes
        the script while providing user feedback and keeping the terminal open
        for result inspection.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            file (Nautilus.FileInfo): The shell script file to execute.
        
        Behavior:
            - Opens a new gnome-terminal window
            - Sets working directory to the script's parent directory
            - Displays script name and directory before execution
            - Executes the script using bash
            - Shows completion message and waits for user input before closing
            - Keeps terminal open for result inspection
        
        Terminal Command Structure:
            Uses gnome-terminal with --working-directory and -- separator for proper
            command isolation and directory context.
        
        Security Note:
            Executes scripts directly with bash - users should verify script content
            before execution as this provides no sandboxing.
        """
        if file.get_uri().startswith('file://'):
            script_path = urllib.parse.unquote(file.get_uri()[7:])
            script_dir = os.path.dirname(script_path)
            script_name = os.path.basename(script_path)
            
            # Create a command that opens a new terminal, changes to the script directory, and runs the script
            # Using gnome-terminal with -- to ensure the terminal stays open after execution
            command = [
                'gnome-terminal',
                '--working-directory=' + script_dir,
                '--',
                'bash', '-c',
                f'echo "Running script: {script_name}"; echo "Directory: {script_dir}"; echo ""; bash "{script_name}"; echo ""; echo "Script execution completed. Press Enter to close..."; read'
            ]
            subprocess.Popen(command)
