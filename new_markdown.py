#!/usr/bin/env python3
"""
New Markdown file creation functionality for the Coral Nautilus extension.

This module provides timestamped markdown file creation with an interactive
filename prompt using zenity. Files are automatically opened in VS Code after creation.
"""

import os
import urllib.parse
import subprocess
from datetime import datetime
from gi.repository import GLib


class MarkdownHandler:
    """Handles markdown file creation operations for the Coral extension."""
    
    def __init__(self, vscode_path):
        """
        Initialize the markdown handler.
        
        Args:
            vscode_path (str): Path to the VSCode executable
        """
        self.vscode_path = vscode_path
    
    def _start_markdown_creation(self, folder_path):
        """Kick off the async workflow to prompt for a markdown filename via zenity."""
        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        default_filename = f'{timestamp}.md'

        if not self._launch_zenity_dialog(folder_path, default_filename):
            # Fall back to the default filename when zenity is unavailable
            self._finalize_markdown_creation(folder_path, default_filename, default_filename)

    def _launch_zenity_dialog(self, folder_path, default_filename):
        """Spawn zenity entry dialog without blocking the Nautilus UI."""
        argv = [
            'zenity',
            '--entry',
            '--title=New Markdown File',
            '--text=Enter a file name for the markdown file:',
            '--modal',
            '--width=600',
            '--entry-text',
            default_filename,
        ]

        try:
            pid, _, stdout_fd, _ = GLib.spawn_async(
                argv,
                flags=GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                standard_output=True,
                standard_error=False,
            )
        except GLib.GError as exc:
            print(f'Failed to launch zenity: {exc}')
            return False

        GLib.child_watch_add(
            GLib.PRIORITY_DEFAULT,
            pid,
            self._on_zenity_finished,
            (stdout_fd, folder_path, default_filename),
        )
        return True

    def _on_zenity_finished(self, pid, status, data):
        """Process zenity result once the dialog closes."""
        stdout_fd, folder_path, default_filename = data

        user_input = ''
        try:
            with os.fdopen(stdout_fd, 'r', encoding='utf-8', errors='ignore') as stdout:
                user_input = stdout.read().strip()
        except Exception as exc:
            print(f'Error reading zenity output: {exc}')

        GLib.spawn_close_pid(pid)

        if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
            self._finalize_markdown_creation(folder_path, user_input, default_filename)
        else:
            # User cancelled or zenity failed; do nothing
            return

    def _finalize_markdown_creation(self, folder_path, user_input, default_filename):
        """Create the markdown file and open it in VSCode."""
        filename = user_input or default_filename
        filename = os.path.basename(filename)

        if not filename.lower().endswith('.md'):
            filename += '.md'

        file_path = os.path.join(folder_path, filename)

        try:
            with open(file_path, 'x') as f:
                f.write(f'\n\n')

            subprocess.Popen([self.vscode_path, file_path])
        except FileExistsError:
            print(f'File already exists, opening instead: {file_path}')
            subprocess.Popen([self.vscode_path, file_path])
        except Exception as e:
            print(f'Error creating markdown file: {e}')
            
    def new_markdown_from_selection(self, menu, selected_item):
        """
        Create a new timestamped markdown file based on the selected item and open it in VSCode.
        
        This method handles the "New Markdown" action when triggered from a file or folder
        selection. It determines the appropriate target directory based on the selection
        type and creates a new markdown file with a timestamp-based filename.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            selected_item (Nautilus.FileInfo): The selected file or folder that provides
                                              context for where to create the new file.
        
        Behavior:
            - Launches zenity asynchronously via GLib to keep the Nautilus UI responsive
            - Prompts the user (via zenity) for a filename, defaulting to a timestamp
            - If a folder is selected: Creates the markdown file inside that folder
            - If a file is selected: Creates the markdown file in the same directory as the file
            - Falls back to the timestamped filename when zenity is unavailable or blank input
            - Creates file with minimal content (two newlines)
            - Automatically opens the new file in VSCode
        
        File Naming:
            Default filename uses timestamp format with double dashes: 2025-10-12--14-30-45.md
        
        Error Handling:
            Prints error messages to console if file creation or VSCode launch fails.
            Opens the existing file in VSCode when the chosen filename already exists.
        """
        if selected_item.get_uri().startswith('file://'):
            selected_path = urllib.parse.unquote(selected_item.get_uri()[7:])
            
            # Determine the target folder
            if selected_item.is_directory():
                # If a folder is selected, create the file in that folder
                folder_path = selected_path
            else:
                # If a file is selected, create the file in the same folder as the selected file
                folder_path = os.path.dirname(selected_path)
            
            self._start_markdown_creation(folder_path)

    def new_markdown(self, menu, current_folder):
        """
        Create a new timestamped markdown file in the current folder and open it in VSCode.
        
        This method handles the "New Markdown" action when triggered from the background
        context menu (right-clicking on empty space). It creates a new markdown file
        directly in the current folder being viewed.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            current_folder (Nautilus.FileInfo): The folder where the new file should be created.
        
        Behavior:
            - Launches zenity asynchronously via GLib to keep the Nautilus UI responsive
            - Prompts the user (via zenity) for a filename, defaulting to a timestamp
            - Creates markdown file in the current folder
            - Falls back to the timestamped filename when zenity is unavailable or blank input
            - Creates file with minimal content (two newlines)
            - Automatically opens the new file in VSCode
        
        File Naming:
            Default filename uses timestamp format with double dashes: 2025-10-12--14-30-45.md
        
        Error Handling:
            Prints error messages to console if file creation or VSCode launch fails.
            Opens the existing file in VSCode when the chosen filename already exists.
        """
        if current_folder.get_uri().startswith('file://'):
            folder_path = urllib.parse.unquote(current_folder.get_uri()[7:])
            
            self._start_markdown_creation(folder_path)
            
            ############
            # ORIGINAL WAY OF CREATING NEW FILE WITHOUT PROMPTING USER TO ENTER FILENAME.
            # KEEP IN CASE WE NEED TO REVERT BACK
            #
            # # Create timestamp in YYYY-MM-DD--HH-MM-SS format
            # timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
            # filename = f'{timestamp}.md'
            # file_path = os.path.join(folder_path, filename)
            
            # # Create the new markdown file with some basic content
            # try:
            #     with open(file_path, 'w') as f:
            #         f.write(f'\n\n')
                
            #     # Open the new file in VSCode
            #     subprocess.Popen([self.vscode_path, file_path])
            # except Exception as e:
            #     print(f'Error creating markdown file: {e}')
            ############
