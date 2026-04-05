#!/usr/bin/env python3
"""
Search functionality for the Coral Nautilus extension (ripgrep implementation).

This module provides recursive text search capabilities for folders,
including support for regular files and PDF documents. Supports multiple
search modes: literal text matching, basic regex, and extended regex.

Uses ripgrep (rg) for fast file content searching instead of grep.
The original grep-based implementation is preserved in search.py.
"""

import os
import urllib.parse
import subprocess
import tempfile
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
    """Handles search operations for the Coral extension using ripgrep."""
    
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

    def _convert_find_glob_to_rg_glob(self, pattern):
        """
        Convert a find-style glob pattern to an rg-compatible glob pattern.

        find's -path uses * to match any characters including /,
        while rg's --glob uses * for single path component and ** for recursive.

        Args:
            pattern (str): A find-style glob pattern (e.g., '*/node_modules/*')

        Returns:
            str: An rg-compatible glob pattern (e.g., '**/node_modules/**')
        """
        rg_pattern = pattern
        if rg_pattern.startswith('*/'):
            rg_pattern = '**/' + rg_pattern[2:]
        if rg_pattern.endswith('/*'):
            rg_pattern = rg_pattern[:-2] + '/**'
        return rg_pattern

    def _build_rg_glob_args(self, excluded_patterns, included_patterns, exclude_pdf=True):
        """
        Build --glob argument string for rg from config patterns.

        Args:
            excluded_patterns (list): List of find-style exclusion glob patterns
            included_patterns (list): List of inclusion glob patterns
            exclude_pdf (bool): Whether to add --glob '!*.pdf' (PDFs handled separately)

        Returns:
            str: Space-separated --glob arguments for rg command
        """
        parts = []

        # Convert exclusion patterns from find-style to rg-style
        for pattern in excluded_patterns:
            rg_pattern = self._convert_find_glob_to_rg_glob(pattern)
            parts.append(f"--glob '!{rg_pattern}'")

        # Add inclusion patterns (skip PDF since it's searched separately via pdftotext)
        if included_patterns:
            for pattern in included_patterns:
                if exclude_pdf and pattern == '*.pdf':
                    continue
                parts.append(f"--glob '{pattern}'")

        # Always exclude PDFs from rg content search (handled via pdftotext pipeline)
        if exclude_pdf:
            parts.append("--glob '!*.pdf'")

        return ' '.join(parts)
    
    def _get_pdf_cache_function(self):
        """
        Generate the bash function for PDF text caching.

        This function creates/uses cached PDF text content stored in ~/.cache/coral/
        to avoid repeatedly running pdftotext on unchanged PDF files.

        Cache key is a hash of (file path + modification timestamp), so the cache
        is automatically invalidated when the PDF is modified.

        Returns:
            str: Bash function code for get_pdf_text()
        """
        return r'''
# PDF caching function - caches pdftotext output in ~/.cache/coral/pdf-cache/
# Cache key is hash of (filepath + mtime), so cache invalidates on file change
PDF_CACHE_DIR="$HOME/.cache/coral/pdf-cache"

get_pdf_text() {
    local pdf_file="$1"

    # Get the file's modification timestamp
    local mtime=$(stat -c %Y "$pdf_file" 2>/dev/null)
    if [ -z "$mtime" ]; then
        # If we can't get mtime, fall back to direct pdftotext
        pdftotext "$pdf_file" - 2>/dev/null
        return
    fi

    # Create hash from filepath + mtime
    local cache_key=$(echo -n "${pdf_file}${mtime}" | md5sum | cut -d' ' -f1)
    local cache_file="${PDF_CACHE_DIR}/${cache_key}"

    # Ensure cache directory exists
    mkdir -p "$PDF_CACHE_DIR" 2>/dev/null

    # Check if cache file exists
    if [ -f "$cache_file" ]; then
        # Cache hit - read from cache
        cat "$cache_file"
    else
        # Cache miss - run pdftotext and save to cache
        local pdf_text=$(pdftotext "$pdf_file" - 2>/dev/null)
        echo "$pdf_text" > "$cache_file" 2>/dev/null
        echo "$pdf_text"
    fi
}
'''

    def _get_results_display_script(self, title, search_display, folder_path):
        """
        Generate the bash script portion for displaying search results in zenity.
        
        This method generates a script that:
        1. Saves search results to a temp file
        2. Creates a separate background script for the zenity results dialog loop
        3. Launches the background script detached (so it runs without a terminal)
        4. Exits the main script, allowing the terminal to close naturally
        
        This approach means the terminal is visible during the search (showing progress),
        but once complete, only the zenity dialog remains visible.
        
        Args:
            title (str): The title for the zenity window
            search_display (str): The search term(s) to display in messages
            folder_path (str): The root folder path for computing relative paths
        
        Returns:
            str: Bash script snippet for displaying results and opening files
        """
        # Get the temp folder path for storing results and the zenity script
        temp_folder = get_temp_folder()
        results_file = os.path.join(temp_folder, 'coral-search-results.txt')
        zenity_script = os.path.join(temp_folder, 'coral-zenity-loop.sh')
        
        return rf'''
echo ""
echo "Search complete!"
echo "Found ${{#RESULTS[@]}} results."

# If no results found, show a message and exit
if [ ${{#RESULTS[@]}} -eq 0 ]; then
    zenity --info --title="Search Results" --text="No results found for: {search_display}" --width=400
    exit 0
fi

# Save results to a temp file (one path per line)
RESULTS_FILE="{results_file}"
printf '%s\n' "${{RESULTS[@]}}" > "$RESULTS_FILE"

# Create a separate script for the zenity dialog loop
# This script will run detached from any terminal
cat > "{zenity_script}" << 'ZENITY_SCRIPT_EOF'
#!/bin/bash

RESULTS_FILE="{results_file}"
SEARCH_ROOT="{folder_path}"
VSCODE_PATH="{self.vscode_path}"
TITLE="{title}"

# Read results from temp file into array
declare -a RESULTS=()
while IFS= read -r line; do
    RESULTS+=("$line")
done < "$RESULTS_FILE"

# Create arrays for display (relative paths) and full paths
declare -a DISPLAY_PATHS=()
declare -A PATH_MAP=()  # Associative array to map relative -> full path

for full_path in "${{RESULTS[@]}}"; do
    # Compute relative path by stripping the search root prefix
    relative_path="${{full_path#$SEARCH_ROOT/}}"
    DISPLAY_PATHS+=("$relative_path")
    PATH_MAP["$relative_path"]="$full_path"
done

# Display results in zenity list and allow multiple selections
# Keep showing the list until user closes the window
while true; do
    selected=$(zenity --list \
        --title="$TITLE" \
        --text="Select a file to open (window stays open for multiple selections):\nRoot: {folder_path}" \
        --column="File Path (relative to search root)" \
        --width=900 \
        --height=600 \
        "${{DISPLAY_PATHS[@]}}")
    
    # If user cancelled/closed the window, exit the loop
    if [ $? -ne 0 ] || [ -z "$selected" ]; then
        break
    fi
    
    # Get the full path from the selected relative path
    full_path="${{PATH_MAP[$selected]}}"
    
    # Open the selected file based on its extension
    extension="${{full_path##*.}}"
    extension_lower=$(echo "$extension" | tr '[:upper:]' '[:lower:]')
    
    if [[ "$extension_lower" == "md" || "$extension_lower" == "txt" ]]; then
        # Open text/markdown files in VSCode
        "$VSCODE_PATH" "$full_path" &
    else
        # Open other files with default application
        xdg-open "$full_path" &
    fi
done

# Clean up temp files
rm -f "$RESULTS_FILE"
rm -f "{zenity_script}"
ZENITY_SCRIPT_EOF

chmod +x "{zenity_script}"

echo ""
echo "Launching results dialog..."

# Launch the zenity script as a fully detached background process
# Using nohup and redirecting all output to /dev/null ensures it's completely detached
nohup "{zenity_script}" > /dev/null 2>&1 &

# Small delay to ensure the background process starts before terminal closes
sleep 0.3

# Exit the terminal script - terminal window will close naturally
exit 0
'''
        
    def search_folder(self, menu, folder, search_type='literal'):
        """
        Recursively search for text in files within the selected folder.
        
        This method handles the "Search" action for folders. It prompts the user
        for a search term using zenity, then searches all files recursively including
        PDF files (using pdftotext), and displays the results in a zenity dialog.
        
        Args:
            menu (Nautilus.MenuItem): The menu item that triggered this action (unused).
            folder (Nautilus.FileInfo): The folder to search within.
            search_type (str): The type of search to perform:
                - 'literal': Exact text match (rg -F)
                - 'regex': Basic regular expressions (rg default)
                - 'extended': Extended regular expressions (rg default)
        
        Requirements:
            - zenity: For search term input dialog
            - rg (ripgrep): For fast text searching
            - pdftotext (poppler-utils): For PDF file searching
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
            # Default to the standard search
            self._search(folder_path, search_term, search_type)
        
    def _search(self, folder_path, search_term, search_type='literal'):
        """Execute the search command in a terminal using ripgrep.
        
        Args:
            folder_path (str): The folder path to search in.
            search_term (str): The search term to look for.
            search_type (str): The type of search:
                - 'literal': Exact text match using rg -F
                - 'regex': Regular expressions using rg (default engine)
                - 'extended': Extended regex using rg (default engine handles this)
        """
        # Determine rg flags based on search type
        # ripgrep's default regex engine handles both basic and extended regex,
        # so both 'regex' and 'extended' use the same flags
        if search_type == 'literal':
            rg_flags = '-F -l -i'  # Fixed string (literal), list files, case-insensitive
            rg_flags_quiet = '-F -q -i'  # For PDF search (quiet mode)
            search_type_label = 'Literal'
        elif search_type == 'extended':
            rg_flags = '-l -i'  # Regex mode (rg default handles extended), list files, case-insensitive
            rg_flags_quiet = '-q -i'  # For PDF search
            search_type_label = 'Extended Regex'
        else:  # regex (basic)
            rg_flags = '-l -i'  # Regex mode (rg default), list files, case-insensitive
            rg_flags_quiet = '-q -i'  # For PDF search
            search_type_label = 'Basic Regex'
        
        # Get excluded patterns from config
        excluded_patterns = self._get_search_patterns('excluded')
        
        # Get included patterns from config
        included_patterns = self._get_search_patterns('included')
        
        # Build rg glob arguments for content search
        rg_glob_args = self._build_rg_glob_args(excluded_patterns, included_patterns)
        
        # Build find command exclusions (still needed for PDF search and filename search)
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Determine if PDFs should be searched based on include patterns
        # If no include patterns specified, search PDFs by default
        # If include patterns specified, only search PDFs if *.pdf is in the list
        search_pdfs = not included_patterns or '*.pdf' in included_patterns
        
        # Create a search script that will be executed in the terminal
        script_content = rf'''#!/bin/bash
echo "Searching for: {search_term}"
echo "Search type: {search_type_label}"
echo "In folder: {folder_path}"
echo ""

# Initialize results array and seen set (to avoid duplicates)
declare -a RESULTS=()
declare -A SEEN_FILES=()

# Check if pdftotext is available
if ! command -v pdftotext &> /dev/null; then
    echo "WARNING: pdftotext not found. PDF files will not be searched."
    echo "To install pdftotext, run: sudo apt install poppler-utils"
    echo ""
fi

# Check if ripgrep is available
if ! command -v rg &> /dev/null; then
    echo "ERROR: ripgrep (rg) not found. Please install it:"
    echo "  sudo apt install ripgrep"
    echo ""
    echo "Press Enter to exit..."
    read
    exit 1
fi
''' + self._get_pdf_cache_function() + rf'''

echo "Searching regular files..."

# Initialize counter
matches_found=0

# Use ripgrep to search file contents recursively
# --no-ignore ensures rg doesn't skip files based on .gitignore
while IFS= read -r file; do
    ((matches_found++))
    echo -ne "\rMatches found: $matches_found"

    # Add to results array and mark as seen
    RESULTS+=("$file")
    SEEN_FILES["$file"]=1
done < <(rg {rg_flags} --no-ignore {rg_glob_args} -- "{search_term}" "{folder_path}" 2>/dev/null)

# Final newline after progress indicator
echo ""
echo ""

# Only search PDFs if search_pdfs is true
if [ "{search_pdfs}" = "True" ]; then
    echo "Searching PDF files..."

    # Reset counters for PDF search
    pdf_searched=0
    pdf_matches=0

    # Search PDF files if pdftotext is available (with exclusions)
    if command -v pdftotext &> /dev/null; then
        while IFS= read -r -d '' pdf_file; do
            ((pdf_searched++))

            # Display progress indicator for PDFs
            echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"

            if get_pdf_text "$pdf_file" | rg {rg_flags_quiet} -- "{search_term}"; then
                ((pdf_matches++))
                echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"

                # Add to results array and mark as seen
                RESULTS+=("$pdf_file")
                SEEN_FILES["$pdf_file"]=1
            fi
        done < <(find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null)
        # Final newline after PDF progress indicator
        echo ""
    else
        echo "(Skipping PDF files - pdftotext not installed)"
    fi
    echo ""
else
    echo "(Skipping PDF files - not in included file patterns)"
    echo ""
fi
echo "Searching for files and folders with matching names..."

# Reset counters for filename search
names_searched=0
names_matched=0

# Search for files and folders with names matching the search term (literal match)
while IFS= read -r -d '' matched_item; do
    ((names_searched++))

    # Skip if already in results (from content search)
    if [[ -n "${{SEEN_FILES[$matched_item]}}" ]]; then
        continue
    fi

    ((names_matched++))

    # Display progress indicator
    echo -ne "\rNames searched: $names_searched | Matches found: $names_matched"

    # Add to results array and mark as seen
    RESULTS+=("$matched_item")
    SEEN_FILES["$matched_item"]=1
done < <(find "{folder_path}" {find_exclusions}-iname "*{search_term}*" -print0 2>/dev/null)

# Final newline after progress indicator
echo ""
''' + self._get_results_display_script(f'Search Results for: {search_term}', search_term, folder_path)
        
        self._execute_search_script(script_content, 'search')
    
    def _execute_search_script(self, script_content, search_type_name):
        """
        Write and execute a search script in a terminal.
        
        Args:
            script_content (str): The bash script content to execute
            search_type_name (str): Name of the search type for error messages
        """
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
            print(f'Error executing {search_type_name}: {e}')
    
    def _or_search(self, folder_path, search_term, search_type='file-or'):
        """Execute a file-level OR search where files must contain ANY of the quoted terms.
        
        Uses ripgrep with multiple -e patterns and -F for literal matching.
        
        Args:
            folder_path (str): The folder path to search in.
            search_term (str): The search terms as quoted strings (e.g., "abc" "def").
            search_type (str): The type of search (should be 'file-or').
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
                '--text=File OR search requires at least 2 quoted terms.\nExample: "abc" "def"',
                '--width=400'
            ])
            return
        
        # Build rg -e pattern arguments for each term
        # Using -F (fixed string) mode, so no regex escaping needed
        rg_pattern_args = ' '.join([f'-e "{term}"' for term in terms])
        
        # Get excluded patterns from config
        excluded_patterns = self._get_search_patterns('excluded')
        
        # Get included patterns from config
        included_patterns = self._get_search_patterns('included')
        
        # Build rg glob arguments for content search
        rg_glob_args = self._build_rg_glob_args(excluded_patterns, included_patterns)
        
        # Build find command exclusions (still needed for PDF search)
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Determine if PDFs should be searched
        search_pdfs = not included_patterns or '*.pdf' in included_patterns
        
        # Display the search terms nicely formatted
        terms_display = ', '.join([f'"{term}"' for term in terms])
        
        # Create a search script for File OR search
        script_content = rf'''#!/bin/bash
echo "File OR Search"
echo "Searching for files containing ANY of: {terms_display}"
echo "In folder: {folder_path}"
echo ""

# Initialize results array
declare -a RESULTS=()

# Check if pdftotext is available
if ! command -v pdftotext &> /dev/null; then
    echo "WARNING: pdftotext not found. PDF files will not be searched."
    echo "To install pdftotext, run: sudo apt install poppler-utils"
    echo ""
fi

# Check if ripgrep is available
if ! command -v rg &> /dev/null; then
    echo "ERROR: ripgrep (rg) not found. Please install it:"
    echo "  sudo apt install ripgrep"
    echo ""
    echo "Press Enter to exit..."
    read
    exit 1
fi
''' + self._get_pdf_cache_function() + rf'''
echo "Searching regular files..."

# Initialize counter
matches_found=0

# Use ripgrep with multiple -e patterns for OR matching (literal with -F)
# --no-ignore ensures rg doesn't skip files based on .gitignore
while IFS= read -r file; do
    ((matches_found++))
    echo -ne "\rMatches found: $matches_found"
    
    # Add to results array
    RESULTS+=("$file")
done < <(rg -F -l -i --no-ignore {rg_glob_args} {rg_pattern_args} "{folder_path}" 2>/dev/null)

# Final newline after progress indicator
echo ""
echo ""

# Only search PDFs if search_pdfs is true
if [ "{search_pdfs}" = "True" ]; then
    echo "Searching PDF files..."

    # Reset counters for PDF search
    pdf_searched=0
    pdf_matches=0

    # Search PDF files if pdftotext is available
    if command -v pdftotext &> /dev/null; then
        while IFS= read -r -d '' pdf_file; do
            ((pdf_searched++))

            # Display progress indicator for PDFs
            echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"

            # Use cached PDF text and rg with multiple -e patterns for OR matching
            if get_pdf_text "$pdf_file" | rg -F -q -i {rg_pattern_args}; then
                ((pdf_matches++))
                echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"

                # Add to results array
                RESULTS+=("$pdf_file")
            fi
        done < <(find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null)
        # Final newline after PDF progress indicator
        echo ""
    else
        echo "(Skipping PDF files - pdftotext not installed)"
    fi
    echo ""
else
    echo "(Skipping PDF files - not in included file patterns)"
    echo ""
fi

''' + self._get_results_display_script(f'File OR Search Results: {terms_display}', terms_display, folder_path)
        
        self._execute_search_script(script_content, 'File OR')
    
    def _and_search(self, folder_path, search_term, search_type='file-and'):
        """Execute a file-level AND search where files must contain ALL of the quoted terms.
        
        Uses ripgrep --files for file enumeration and rg -F -q for per-file term checking.
        
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
        
        # Get excluded patterns from config
        excluded_patterns = self._get_search_patterns('excluded')
        
        # Get included patterns from config
        included_patterns = self._get_search_patterns('included')
        
        # Build rg glob arguments for file enumeration
        rg_glob_args = self._build_rg_glob_args(excluded_patterns, included_patterns)
        
        # Build find command exclusions (still needed for PDF search)
        find_exclusions = ''
        if excluded_patterns:
            exclusion_parts = []
            for pattern in excluded_patterns:
                exclusion_parts.append(f'-path "{pattern}" -prune -o')
            find_exclusions = ' '.join(exclusion_parts) + ' '
        
        # Determine if PDFs should be searched
        search_pdfs = not included_patterns or '*.pdf' in included_patterns
        
        # Display the search terms nicely formatted
        terms_display = ', '.join([f'"{term}"' for term in terms])
        
        # Build chained rg commands for AND logic
        # Using -F for literal matching, so no regex escaping needed
        # Each term must be found in the file for it to be a match
        rg_chain = ' && '.join([f'rg -F -q -i -- "{term}" "$file"' for term in terms])
        
        # Create a search script for File AND search
        script_content = rf'''#!/bin/bash
echo "File AND Search"
echo "Searching for files containing ALL of: {terms_display}"
echo "In folder: {folder_path}"
echo ""

# Initialize results array
declare -a RESULTS=()

# Check if pdftotext is available
if ! command -v pdftotext &> /dev/null; then
    echo "WARNING: pdftotext not found. PDF files will not be searched."
    echo "To install pdftotext, run: sudo apt install poppler-utils"
    echo ""
fi

# Check if ripgrep is available
if ! command -v rg &> /dev/null; then
    echo "ERROR: ripgrep (rg) not found. Please install it:"
    echo "  sudo apt install ripgrep"
    echo ""
    echo "Press Enter to exit..."
    read
    exit 1
fi
''' + self._get_pdf_cache_function() + rf'''
echo "Searching regular files..."

# Initialize counters
files_searched=0
matches_found=0

# Enumerate files using rg --files (respects glob patterns), then check each for ALL terms
# --no-ignore ensures rg doesn't skip files based on .gitignore
while IFS= read -r file; do
    ((files_searched++))
    
    # Display progress indicator
    echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
    
    # Check if file contains ALL search terms using chained rg with &&
    if {rg_chain}; then
        ((matches_found++))
        echo -ne "\rFiles searched: $files_searched | Matches found: $matches_found"
        
        # Add to results array
        RESULTS+=("$file")
    fi
done < <(rg --files --no-ignore {rg_glob_args} "{folder_path}" 2>/dev/null)

# Final newline after progress indicator
echo ""
echo ""

# Only search PDFs if search_pdfs is true
if [ "{search_pdfs}" = "True" ]; then
    echo "Searching PDF files..."

    # Reset counters for PDF search
    pdf_searched=0
    pdf_matches=0

    # Search PDF files if pdftotext is available
    if command -v pdftotext &> /dev/null; then
        while IFS= read -r -d '' pdf_file; do
            ((pdf_searched++))

            # Display progress indicator for PDFs
            echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"

            # Extract PDF text (using cache) and check if ALL terms are present
            pdf_text=$(get_pdf_text "$pdf_file")
            all_terms_found=true

            # Check each term individually using rg -F for literal matching
''' + '\n'.join([f'            if ! echo "$pdf_text" | rg -F -q -i -- "{term}"; then\n                all_terms_found=false\n            fi' for term in terms]) + rf'''

            if [ "$all_terms_found" = true ]; then
                ((pdf_matches++))
                echo -ne "\rPDF files searched: $pdf_searched | Matches found: $pdf_matches"

                # Add to results array
                RESULTS+=("$pdf_file")
            fi
        done < <(find "{folder_path}" {find_exclusions}-type f -name "*.pdf" -print0 2>/dev/null)
        # Final newline after PDF progress indicator
        echo ""
    else
        echo "(Skipping PDF files - pdftotext not installed)"
    fi
    echo ""
else
    echo "(Skipping PDF files - not in included file patterns)"
    echo ""
fi

''' + self._get_results_display_script(f'File AND Search Results: {terms_display}', terms_display, folder_path)
        
        self._execute_search_script(script_content, 'File AND')
