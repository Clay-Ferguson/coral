#!/usr/bin/env python3

import os
import urllib.parse
import subprocess
import mimetypes
from datetime import datetime
from gi.repository import Nautilus, GObject, GLib

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
    
    def _load_config(self):
        """
        Load configuration from YAML file.
        
        Returns:
            dict: Configuration dictionary, or empty dict if config can't be loaded.
        """
        if not YAML_AVAILABLE:
            return {}
        
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                print(f"Config file not found: {self.CONFIG_FILE}")
                return {}
        except Exception as e:
            print(f"Error loading config file: {e}")
            return {}
    
    def _get_search_excluded_patterns(self):
        """
        Get excluded patterns for search from config file.
        
        Returns:
            list: List of glob patterns to exclude from search, or empty list.
        """
        config = self._load_config()
        
        try:
            excluded = config.get('search', {}).get('excluded', [])
            if isinstance(excluded, list):
                return excluded
            else:
                return []
        except Exception as e:
            print(f"Error reading excluded patterns from config: {e}")
            return []

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
        
        # Add Search submenu for directories
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
        
        # Search submenu for current folder
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

    def search_folder(self, menu, folder, search_type='literal'):
        """
        Recursively search for text in files within the selected folder.
        
        This method handles the "Search" action for folders. It prompts the user
        for a search term using zenity, then searches all files recursively including
        PDF files (using pdftotext), and displays the results in a markdown file
        opened in VSCode.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            folder (Nautilus.FileInfo): The folder to search within.
            search_type (str): The type of search to perform:
                - 'literal': Exact text match (grep -F)
                - 'regex': Basic regular expressions (grep default)
                - 'extended': Extended regular expressions (grep -E)
        
        Behavior:
            - Prompts user for search term via zenity dialog
            - Searches regular files using grep with appropriate flags
            - Searches PDF files using pdftotext + grep
            - Writes results to coral-search.md in system temp folder
            - Opens results in gnome-terminal showing search progress
            - Prompts user to press Enter to open results in VSCode
        
        Requirements:
            - zenity: For search term input dialog
            - pdftotext (poppler-utils): For PDF file searching
            - grep: For text searching
        
        Error Handling:
            Checks for pdftotext availability and prints installation command if missing.
        """
        if not folder.get_uri().startswith('file://'):
            return
            
        folder_path = urllib.parse.unquote(folder.get_uri()[7:])
        
        # If it's a file selection, use the parent directory
        if not folder.is_directory():
            folder_path = os.path.dirname(folder_path)
        
        # Prompt for search term using zenity
        argv = [
            'zenity',
            '--entry',
            '--title=Search Files',
            '--text=Enter search term:',
            '--modal',
            '--width=600',
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
            return
        
        GLib.child_watch_add(
            GLib.PRIORITY_DEFAULT,
            pid,
            self._on_search_term_entered,
            (stdout_fd, folder_path, search_type),
        )
    
    def _on_search_term_entered(self, pid, status, data):
        """Process search term once zenity dialog closes."""
        stdout_fd, folder_path, search_type = data
        
        search_term = ''
        try:
            with os.fdopen(stdout_fd, 'r', encoding='utf-8', errors='ignore') as stdout:
                search_term = stdout.read().strip()
        except Exception as exc:
            print(f'Error reading zenity output: {exc}')
        
        GLib.spawn_close_pid(pid)
        
        if not (os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0) or not search_term:
            # User cancelled or provided empty search term
            return
        
        # Create the search script
        self._execute_search(folder_path, search_term, search_type)
    
    def _execute_search(self, folder_path, search_term, search_type='literal'):
        """Execute the search command in a terminal.
        
        Args:
            folder_path (str): The folder path to search in.
            search_term (str): The search term to look for.
            search_type (str): The type of search:
                - 'literal': Exact text match using grep -F
                - 'regex': Basic regular expressions using grep (default)
                - 'extended': Extended regular expressions using grep -E
        """
        import tempfile
        
        # Determine grep flags based on search type
        if search_type == 'literal':
            grep_flags = '-F -l -i'  # Fixed string (literal), list files, case-insensitive
            grep_flags_quiet = '-F -q -i'  # For PDF search
            search_type_label = 'Literal'
        elif search_type == 'extended':
            grep_flags = '-E -l -i'  # Extended regex, list files, case-insensitive
            grep_flags_quiet = '-E -q -i'  # For PDF search
            search_type_label = 'Extended Regex'
        else:  # regex (basic)
            grep_flags = '-l -i'  # Basic regex (default), list files, case-insensitive
            grep_flags_quiet = '-q -i'  # For PDF search
            search_type_label = 'Basic Regex'
        
        # Get excluded patterns from config
        excluded_patterns = self._get_search_excluded_patterns()
        
        # Build find command exclusions
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                # Use -path for glob patterns and -prune to skip those directories
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Path to the results file with timestamp
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        results_file = os.path.join(temp_dir, f'coral-search--{timestamp}.md')
        
        # Create a search script that will be executed in the terminal
        script_content = f'''#!/bin/bash
echo "Searching for: {search_term}"
echo "Search type: {search_type_label}"
echo "In folder: {folder_path}"
echo ""
echo "# Search Results" > "{results_file}"
echo "" >> "{results_file}"
echo "**Search term:** {search_term}" >> "{results_file}"
echo "" >> "{results_file}"
echo "**Search type:** {search_type_label}" >> "{results_file}"
echo "" >> "{results_file}"
echo "**Search location:** {folder_path}" >> "{results_file}"
echo "" >> "{results_file}"
echo "**Date:** $(date)" >> "{results_file}"
echo "" >> "{results_file}"
echo "---" >> "{results_file}"
echo "" >> "{results_file}"

# Check if pdftotext is available
if ! command -v pdftotext &> /dev/null; then
    echo "WARNING: pdftotext not found. PDF files will not be searched."
    echo "To install pdftotext, run: sudo apt install poppler-utils"
    echo ""
    echo "## Note" >> "{results_file}"
    echo "pdftotext is not installed. PDF files were not searched." >> "{results_file}"
    echo "To enable PDF searching, run: \`sudo apt install poppler-utils\`" >> "{results_file}"
    echo "" >> "{results_file}"
fi

echo "Searching regular files..."
echo "## Regular Files" >> "{results_file}"
echo "" >> "{results_file}"

# Search non-PDF files with exclusions
find "{folder_path}" {find_exclusions}-type f ! -name "*.pdf" -print0 2>/dev/null | xargs -0 grep {grep_flags} "{search_term}" 2>/dev/null | while read -r file; do
    echo "Found in: $file"
    # URL encode the file path for the link
    encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$file', safe='/'))")

    # NOTE: Not using a markdown link because VSCode (which we open with) lets us CTRL+CLICK filenames to open them
    # echo "- [$file](file://$encoded_file)" >> "{results_file}"
    echo "- file://$encoded_file" >> "{results_file}"
done

echo ""
echo "Searching PDF files..."
echo "" >> "{results_file}"
echo "## PDF Files" >> "{results_file}"
echo "" >> "{results_file}"

# Search PDF files if pdftotext is available (with exclusions)
if command -v pdftotext &> /dev/null; then
    find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' pdf_file; do
        if pdftotext "$pdf_file" - 2>/dev/null | grep {grep_flags_quiet} "{search_term}"; then
            echo "Found in PDF: $pdf_file"
            # URL encode the file path for the link
            encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$pdf_file', safe='/'))")
            
            # NOTE: Not using a markdown link because VSCode (which we open with) lets us CTRL+CLICK filenames to open them
            # echo "- [$pdf_file](file://$encoded_file)" >> "{results_file}"
            echo "- file://$encoded_file" >> "{results_file}"
        fi
    done
else
    echo "(Skipping PDF files - pdftotext not installed)"
fi

echo ""
echo "Search complete!"

# Commented out so we just open immediately in VSCode instead of prompting first
# echo ""
# echo "Results written to: {results_file}"
# echo ""
# read -p "Press ENTER to open results in VSCode..."

# Open results in VSCode
{self.VSCODE_PATH} "{results_file}"
'''
        
        # Write the script to a temporary file
        script_file = os.path.join(tempfile.gettempdir(), 'coral-search-script.sh')
        try:
            with open(script_file, 'w') as f:
                f.write(script_content)
            os.chmod(script_file, 0o755)
            
            # Execute the script in a new terminal
            command = [
                'gnome-terminal',
                '--',
                'bash', script_file
            ]
            subprocess.Popen(command)
        except Exception as e:
            print(f'Error executing search: {e}')