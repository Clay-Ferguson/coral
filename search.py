#!/usr/bin/env python3
"""
Search functionality for the Coral Nautilus extension.

This module provides recursive text search capabilities for folders,
including support for regular files and PDF documents. Supports multiple
search modes: literal text matching, basic regex, and extended regex.
"""

import os
import urllib.parse
import subprocess
import tempfile
from datetime import datetime
from gi.repository import GLib


def get_temp_folder():
    """
    Get the Coral temporary folder path, creating it if it doesn't exist.
    
    Returns:
        str: Path to the coral temporary folder (typically /tmp/coral)
    """
    temp_dir = os.path.join(tempfile.gettempdir(), 'coral')
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating coral temp directory: {e}")
            # Fall back to standard temp directory if creation fails
            return tempfile.gettempdir()
    return temp_dir

# Try to import yaml for config file support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class SearchHandler:
    """Handles search operations for the Coral extension."""
    
    def __init__(self, vscode_path, config_file):
        """
        Initialize the search handler.
        
        Args:
            vscode_path (str): Path to the VSCode executable
            config_file (str): Path to the config file
        """
        self.vscode_path = vscode_path
        self.config_file = config_file
    
    # Functions will be moved here by the user
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
        temp_dir = get_temp_folder()
        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        results_file = os.path.join(temp_dir, f'coral-search--{timestamp}.md')
        
        # Create a search script that will be executed in the terminal
        script_content = rf'''#!/bin/bash
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

# Initialize counters
files_searched=0
matches_found=0

# Search non-PDF files with exclusions and show progress
find "{folder_path}" {find_exclusions}-type f ! -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' file; do
    ((files_searched++))
    
    # Display progress indicator (overwrites same line)
    echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
    
    # Check if file matches the search term
    if grep {grep_flags} "{search_term}" "$file" >/dev/null 2>&1; then
        ((matches_found++))
        echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
        
        # URL encode the file path for the link
        encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$file', safe='/'))")
        
        # NOTE: Not using a markdown link because VSCode (which we open with) lets us CTRL+CLICK filenames to open them
        # echo "- [$file](file://$encoded_file)" >> "{results_file}"
        echo "- file://$encoded_file" >> "{results_file}"
    fi
done

# Final newline after progress indicator
echo ""
echo ""
echo "Searching PDF files..."
echo "" >> "{results_file}"
echo "## PDF Files" >> "{results_file}"
echo "" >> "{results_file}"

# Reset counters for PDF search
pdf_searched=0
pdf_matches=0

# Search PDF files if pdftotext is available (with exclusions)
if command -v pdftotext &> /dev/null; then
    find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' pdf_file; do
        ((pdf_searched++))
        
        # Display progress indicator for PDFs
        echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"
        
        if pdftotext "$pdf_file" - 2>/dev/null | grep {grep_flags_quiet} "{search_term}"; then
            ((pdf_matches++))
            echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"
            
            # URL encode the file path for the link
            encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$pdf_file', safe='/'))")
            
            # NOTE: Not using a markdown link because VSCode (which we open with) lets us CTRL+CLICK filenames to open them
            # echo "- [$pdf_file](file://$encoded_file)" >> "{results_file}"
            echo "- file://$encoded_file" >> "{results_file}"
        fi
    done
    # Final newline after PDF progress indicator
    echo ""
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
{self.vscode_path} "{results_file}"
'''
        
        # Write the script to a temporary file
        script_file = os.path.join(get_temp_folder(), 'coral-search-script.sh')
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