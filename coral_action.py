#!/usr/bin/env python3

import os
import urllib.parse
import subprocess
import mimetypes
from datetime import datetime
from gi.repository import Nautilus, GObject, GLib

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
    
    def __init__(self):
        """
        Initialize the Nautilus extension.
        
        Calls the parent class constructor to properly initialize the GObject
        and Nautilus MenuProvider interfaces. This method is called automatically
        when Nautilus loads the extension.
        """
        super().__init__()

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
        
        return items

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

            subprocess.Popen([self.VSCODE_PATH, file_path])
        except FileExistsError:
            print(f'File already exists, opening instead: {file_path}')
            subprocess.Popen([self.VSCODE_PATH, file_path])
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
            #     subprocess.Popen([self.VSCODE_PATH, file_path])
            # except Exception as e:
            #     print(f'Error creating markdown file: {e}')
            ############

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
            subprocess.Popen([self.VSCODE_PATH, path])