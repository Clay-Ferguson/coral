#!/usr/bin/env python3

import os
import urllib.parse
import subprocess
import mimetypes
from datetime import datetime
from gi.repository import Nautilus, GObject

class AddNautilusMenuItems(GObject.GObject, Nautilus.MenuProvider):
    VSCODE_PATH = '/usr/bin/code'
    TEXT_FILE_EXTENSIONS = ('.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml', '.ini', '.cfg', '.conf')
    
    def __init__(self):
        super().__init__()

    def get_file_items(self, files):
        """Add menu item when files/folders are selected"""
        if len(files) != 1:
            return []
        
        file = files[0]
        items = []
        
        # Always add New Markdown option first (works for any selection)
        new_markdown_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::new_markdown_from_selection',
            label='New Markdown',
            tip='Create a new timestamped markdown file and open in VS Code'
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
                label='Open in VS Code',
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
                    label='Open in VS Code',
                    tip='Open this file in Visual Studio Code'
                )
                vscode_item.connect('activate', self.open_in_vscode, file)
                items.append(vscode_item)
        
        return items

    def get_background_items(self, current_folder):
        """Add menu item when right-clicking on background"""
        items = []
        
        # New Markdown file option
        new_markdown_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::new_markdown',
            label='New Markdown',
            tip='Create a new timestamped markdown file and open in VS Code'
        )
        new_markdown_item.connect('activate', self.new_markdown, current_folder)
        items.append(new_markdown_item)
        
        # Open current folder in VS Code option
        vscode_item = Nautilus.MenuItem(
            name='AddNautilusMenuItems::open_current_in_vscode',
            label='Open in VS Code',
            tip='Open current folder in Visual Studio Code'
        )
        vscode_item.connect('activate', self.open_in_vscode, current_folder)
        items.append(vscode_item)
        
        return items

    def new_markdown_from_selection(self, menu, selected_item):
        """Create a new timestamped markdown file based on selection and open it in VS Code"""
        if selected_item.get_uri().startswith('file://'):
            selected_path = urllib.parse.unquote(selected_item.get_uri()[7:])
            
            # Determine the target folder
            if selected_item.is_directory():
                # If a folder is selected, create the file in that folder
                folder_path = selected_path
            else:
                # If a file is selected, create the file in the same folder as the selected file
                folder_path = os.path.dirname(selected_path)
            
            # Create timestamp in YYYY-MM-DD--HH-MM-SS format
            timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
            filename = f'{timestamp}.md'
            file_path = os.path.join(folder_path, filename)
            
            # Create the new markdown file with some basic content
            try:
                with open(file_path, 'w') as f:
                    f.write(f'\n\n')
                
                # Open the new file in VS Code
                subprocess.Popen([self.VSCODE_PATH, file_path])
            except Exception as e:
                print(f'Error creating markdown file: {e}')

    def new_markdown(self, menu, current_folder):
        """Create a new timestamped markdown file and open it in VS Code"""
        if current_folder.get_uri().startswith('file://'):
            folder_path = urllib.parse.unquote(current_folder.get_uri()[7:])
            
            # Create timestamp in YYYY-MM-DD--HH-MM-SS format
            timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
            filename = f'{timestamp}.md'
            file_path = os.path.join(folder_path, filename)
            
            # Create the new markdown file with some basic content
            try:
                with open(file_path, 'w') as f:
                    f.write(f'\n\n')
                
                # Open the new file in VS Code
                subprocess.Popen([self.VSCODE_PATH, file_path])
            except Exception as e:
                print(f'Error creating markdown file: {e}')

    def run_script(self, menu, file):
        """Run the selected shell script in a new terminal"""
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
        """Open the selected file/folder in VS Code"""
        if file.get_uri().startswith('file://'):
            path = urllib.parse.unquote(file.get_uri()[7:])
            subprocess.Popen([self.VSCODE_PATH, path])