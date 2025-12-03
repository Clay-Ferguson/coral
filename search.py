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

    def _get_search_patterns(self, pattern_type):
        """
        Get search patterns from config file.
        
        Args:
            pattern_type (str): Either 'excluded' or 'included'
        
        Returns:
            list: List of glob patterns, or empty list.
        """
        config = self._load_config()
        
        try:
            patterns = config.get('search', {}).get(pattern_type, [])
            if isinstance(patterns, list):
                return patterns
            else:
                return []
        except Exception as e:
            print(f"Error reading {pattern_type} patterns from config: {e}")
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
        
        # Customize the prompt text based on search type
        if search_type == 'file-or':
            prompt_text = 'Enter search terms (ORed):\nExample: "ABC" "DEF"\n(finds files containing ANY of the terms)'
        elif search_type == 'file-and':
            prompt_text = 'Enter search terms (ANDed):\nExample: "ABC" "DEF"\n(finds files containing ALL of the terms)'
        else:
            prompt_text = 'Enter search term:'
        
        # Prompt for search term using zenity
        argv = [
            'zenity',
            '--entry',
            '--title=Search Files',
            f'--text={prompt_text}',
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
        
        # Route to the appropriate search function based on search_type
        if search_type == 'file-or':
            self._or_search(folder_path, search_term, search_type)
        elif search_type == 'file-and':
            self._and_search(folder_path, search_term, search_type)
        else:
            # Default to the original line-by-line search
            self._search(folder_path, search_term, search_type)
        
    def _search(self, folder_path, search_term, search_type='literal'):
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
        excluded_patterns = self._get_search_patterns('excluded')
        
        # Get included patterns from config
        included_patterns = self._get_search_patterns('included')
        
        # Build find command exclusions
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                # Use -path for glob patterns and -prune to skip those directories
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Build find command inclusions for non-PDF files
        find_inclusions_non_pdf = ''
        if included_patterns:
            # Build -name conditions for included patterns (excluding PDF pattern)
            inclusion_parts = []
            for pattern in included_patterns:
                if pattern != '*.pdf':  # PDFs are handled separately
                    inclusion_parts.append(f'-name "{pattern}"')
            
            if inclusion_parts:  # Only add if there are non-PDF patterns
                # Combine with -o (OR) and wrap in parentheses
                find_inclusions_non_pdf = '\\( ' + ' -o '.join(inclusion_parts) + ' \\) '
        
        # Determine if PDFs should be searched based on include patterns
        # If no include patterns specified, search PDFs by default
        # If include patterns specified, only search PDFs if *.pdf is in the list
        search_pdfs = not included_patterns or '*.pdf' in included_patterns
        
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
find "{folder_path}" {find_exclusions}-type f {find_inclusions_non_pdf}! -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' file; do
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

# Only search PDFs if search_pdfs is true
if [ "{search_pdfs}" = "True" ]; then
    # Ask user if they want to search PDF files
    echo ""
    read -p "Search PDF files? (y/n): " search_pdfs_choice
    if [[ "$search_pdfs_choice" =~ ^[Yy]$ ]]; then
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
    else
        echo "(Skipping PDF search)"
        echo ""
    fi
else
    echo "(Skipping PDF files - not in included file patterns)"
    echo ""
fi
echo "Searching for files and folders with matching names..."
echo "" >> "{results_file}"
echo "## Files & Folders" >> "{results_file}"
echo "" >> "{results_file}"

# Reset counters for filename search
names_searched=0
names_matched=0

# Search for files and folders with names matching the search term (literal match)
find "{folder_path}" {find_exclusions}-iname "*{search_term}*" -print0 2>/dev/null | while IFS= read -r -d '' matched_item; do
    ((names_searched++))
    ((names_matched++))
    
    # Display progress indicator
    echo -ne "\rNames searched: $names_searched | Matches found: $names_matched"
    
    # URL encode the file path for the link
    encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$matched_item', safe='/'))")
    
    # NOTE: Not using a markdown link because VSCode (which we open with) lets us CTRL+CLICK filenames to open them
    # echo "- [$matched_item](file://$encoded_file)" >> "{results_file}"
    echo "- file://$encoded_file" >> "{results_file}"
done

# Final newline after progress indicator
echo ""

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
    
    def _or_search(self, folder_path, search_term, search_type='file-or'):
        """Execute a file-level OR search where files must contain ANY of the quoted terms.
        
        Args:
            folder_path (str): The folder path to search in.
            search_term (str): The search terms as quoted strings (e.g., "abc" "def").
            search_type (str): The type of search (should be 'file-or').
        """
        import shlex
        import tempfile
        
        # Parse the quoted terms from the user input
        try:
            terms = shlex.split(search_term)
        except ValueError as e:
            # Show error dialog if parsing fails
            subprocess.Popen([
                'zenity',
                '--error',
                '--title=Search Error',
                '--text=Error parsing search terms. Please use quoted strings like "term1" "term2"',
                '--width=400'
            ])
            print(f'Error parsing search terms: {e}')
            return
        
        # Validate that we have at least 2 terms
        if len(terms) < 2:
            subprocess.Popen([
                'zenity',
                '--error',
                '--title=Search Error',
                '--text=File OR search requires at least 2 quoted terms.\nExample: "abc" "def"',
                '--width=400'
            ])
            return
        
        # Escape terms for use in grep (escape special regex characters for literal matching)
        # Since we want literal matching, we need to escape: . * [ ] ^ $ \
        def escape_for_grep(term):
            """Escape special regex characters for literal matching in grep."""
            special_chars = r'\.[]^$*'
            for char in special_chars:
                term = term.replace(char, '\\' + char)
            return term
        
        escaped_terms = [escape_for_grep(term) for term in terms]
        
        # Join terms with | for regex alternation
        grep_pattern = '|'.join(escaped_terms)
        
        # Get excluded patterns from config
        excluded_patterns = self._get_search_patterns('excluded')
        
        # Get included patterns from config
        included_patterns = self._get_search_patterns('included')
        
        # Build find command exclusions
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Build find command inclusions for non-PDF files
        find_inclusions_non_pdf = ''
        if included_patterns:
            inclusion_parts = []
            for pattern in included_patterns:
                if pattern != '*.pdf':
                    inclusion_parts.append(f'-name "{pattern}"')
            
            if inclusion_parts:
                find_inclusions_non_pdf = '\\( ' + ' -o '.join(inclusion_parts) + ' \\) '
        
        # Determine if PDFs should be searched
        search_pdfs = not included_patterns or '*.pdf' in included_patterns
        
        # Path to the results file with timestamp
        temp_dir = get_temp_folder()
        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        results_file = os.path.join(temp_dir, f'coral-search--{timestamp}.md')
        
        # Display the search terms nicely formatted
        terms_display = ', '.join([f'"{term}"' for term in terms])
        
        # Create a search script for File OR search
        script_content = rf'''#!/bin/bash
echo "File OR Search"
echo "Searching for files containing ANY of: {terms_display}"
echo "In folder: {folder_path}"
echo ""
echo "# File OR Search Results" > "{results_file}"
echo "" >> "{results_file}"
echo "**Search terms (OR):** {terms_display}" >> "{results_file}"
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

# Search non-PDF files using grep with OR pattern (|)
find "{folder_path}" {find_exclusions}-type f {find_inclusions_non_pdf}! -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' file; do
    ((files_searched++))
    
    # Display progress indicator
    echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
    
    # Check if file matches any of the search terms using extended regex with OR
    if grep -E -l -i '{grep_pattern}' "$file" >/dev/null 2>&1; then
        ((matches_found++))
        echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
        
        # URL encode the file path for the link
        encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$file', safe='/'))")
        
        echo "- file://$encoded_file" >> "{results_file}"
    fi
done

# Final newline after progress indicator
echo ""
echo ""

# Only search PDFs if search_pdfs is true
if [ "{search_pdfs}" = "True" ]; then
    # Ask user if they want to search PDF files
    echo ""
    read -p "Search PDF files? (y/n): " search_pdfs_choice
    if [[ "$search_pdfs_choice" =~ ^[Yy]$ ]]; then
        echo "Searching PDF files..."
        echo "" >> "{results_file}"
        echo "## PDF Files" >> "{results_file}"
        echo "" >> "{results_file}"

        # Reset counters for PDF search
        pdf_searched=0
        pdf_matches=0

        # Search PDF files if pdftotext is available
        if command -v pdftotext &> /dev/null; then
            find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' pdf_file; do
                ((pdf_searched++))
                
                # Display progress indicator for PDFs
                echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"
                
                # Use pdftotext to extract text and grep with OR pattern
                if pdftotext "$pdf_file" - 2>/dev/null | grep -E -q -i '{grep_pattern}'; then
                    ((pdf_matches++))
                    echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"
                    
                    # URL encode the file path for the link
                    encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$pdf_file', safe='/'))")
                    
                    echo "- file://$encoded_file" >> "{results_file}"
                fi
            done
            # Final newline after PDF progress indicator
            echo ""
        else
            echo "(Skipping PDF files - pdftotext not installed)"
        fi
        echo ""
    else
        echo "(Skipping PDF search)"
        echo ""
    fi
else
    echo "(Skipping PDF files - not in included file patterns)"
    echo ""
fi

echo ""
echo "Search complete!"

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
            print(f'Error executing File OR search: {e}')
    
    def _and_search(self, folder_path, search_term, search_type='file-and'):
        """Execute a file-level AND search where files must contain ALL of the quoted terms.
        
        Args:
            folder_path (str): The folder path to search in.
            search_term (str): The search terms as quoted strings (e.g., "abc" "def").
            search_type (str): The type of search (should be 'file-and').
        """
        import shlex
        
        # Parse the quoted terms from the user input
        try:
            terms = shlex.split(search_term)
        except ValueError as e:
            # Show error dialog if parsing fails
            subprocess.Popen([
                'zenity',
                '--error',
                '--title=Search Error',
                '--text=Error parsing search terms. Please use quoted strings like "term1" "term2"',
                '--width=400'
            ])
            print(f'Error parsing search terms: {e}')
            return
        
        # Validate that we have at least 2 terms
        if len(terms) < 2:
            subprocess.Popen([
                'zenity',
                '--error',
                '--title=Search Error',
                '--text=File AND search requires at least 2 quoted terms.\nExample: "abc" "def"',
                '--width=400'
            ])
            return
        
        # Escape terms for use in grep (escape special regex characters for literal matching)
        def escape_for_grep(term):
            """Escape special regex characters for literal matching in grep."""
            special_chars = r'\.[]^$*'
            for char in special_chars:
                term = term.replace(char, '\\' + char)
            return term
        
        escaped_terms = [escape_for_grep(term) for term in terms]
        
        # Get excluded patterns from config
        excluded_patterns = self._get_search_patterns('excluded')
        
        # Get included patterns from config
        included_patterns = self._get_search_patterns('included')
        
        # Build find command exclusions
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Build find command inclusions for non-PDF files
        find_inclusions_non_pdf = ''
        if included_patterns:
            inclusion_parts = []
            for pattern in included_patterns:
                if pattern != '*.pdf':
                    inclusion_parts.append(f'-name "{pattern}"')
            
            if inclusion_parts:
                find_inclusions_non_pdf = '\\( ' + ' -o '.join(inclusion_parts) + ' \\) '
        
        # Determine if PDFs should be searched
        search_pdfs = not included_patterns or '*.pdf' in included_patterns
        
        # Path to the results file with timestamp
        temp_dir = get_temp_folder()
        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        results_file = os.path.join(temp_dir, f'coral-search--{timestamp}.md')
        
        # Display the search terms nicely formatted
        terms_display = ', '.join([f'"{term}"' for term in terms])
        
        # Build the chained grep commands for AND logic
        # For each file, we need to check if ALL terms are present
        grep_chain = ' && '.join([f'grep -q -i "{term}" "$file"' for term in escaped_terms])
        
        # Create a search script for File AND search
        script_content = rf'''#!/bin/bash
echo "File AND Search"
echo "Searching for files containing ALL of: {terms_display}"
echo "In folder: {folder_path}"
echo ""
echo "# File AND Search Results" > "{results_file}"
echo "" >> "{results_file}"
echo "**Search terms (AND):** {terms_display}" >> "{results_file}"
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

# Search non-PDF files using chained grep commands for AND logic
find "{folder_path}" {find_exclusions}-type f {find_inclusions_non_pdf}! -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' file; do
    ((files_searched++))
    
    # Display progress indicator
    echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
    
    # Check if file contains ALL search terms using chained grep with &&
    if {grep_chain}; then
        ((matches_found++))
        echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
        
        # URL encode the file path for the link
        encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$file', safe='/'))")
        
        echo "- file://$encoded_file" >> "{results_file}"
    fi
done

# Final newline after progress indicator
echo ""
echo ""

# Only search PDFs if search_pdfs is true
if [ "{search_pdfs}" = "True" ]; then
    # Ask user if they want to search PDF files
    echo ""
    read -p "Search PDF files? (y/n): " search_pdfs_choice
    if [[ "$search_pdfs_choice" =~ ^[Yy]$ ]]; then
        echo "Searching PDF files..."
        echo "" >> "{results_file}"
        echo "## PDF Files" >> "{results_file}"
        echo "" >> "{results_file}"

        # Reset counters for PDF search
        pdf_searched=0
        pdf_matches=0

        # Search PDF files if pdftotext is available
        if command -v pdftotext &> /dev/null; then
            find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null | while IFS= read -r -d '' pdf_file; do
                ((pdf_searched++))
                
                # Display progress indicator for PDFs
                echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"
                
                # Extract PDF text and check if ALL terms are present
                pdf_text=$(pdftotext "$pdf_file" - 2>/dev/null)
                all_terms_found=true
                
                # Check each term individually
''' + '\n'.join([f'                if ! echo "$pdf_text" | grep -q -i "{term}"; then\n                    all_terms_found=false\n                fi' for term in escaped_terms]) + rf'''
                
                if [ "$all_terms_found" = true ]; then
                    ((pdf_matches++))
                    echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"
                    
                    # URL encode the file path for the link
                    encoded_file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$pdf_file', safe='/'))")
                    
                    echo "- file://$encoded_file" >> "{results_file}"
                fi
            done
            # Final newline after PDF progress indicator
            echo ""
        else
            echo "(Skipping PDF files - pdftotext not installed)"
        fi
        echo ""
    else
        echo "(Skipping PDF search)"
        echo ""
    fi
else
    echo "(Skipping PDF files - not in included file patterns)"
    echo ""
fi

echo ""
echo "Search complete!"

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
            print(f'Error executing File AND search: {e}')