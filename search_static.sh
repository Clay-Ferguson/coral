#!/bin/bash
#
# Coral "Search (Static)" helper.
#
# Launched in a terminal by search_static.py. Prompts for a search string,
# runs ugrep to collect the full paths of every matching file, writes those
# paths to a timestamped file in /tmp, and opens that file in VS Code.
#
# Usage: search_static.sh <search-dir> <vscode-path> [extra ugrep args...]
#
set -u

SEARCH_DIR="$1"
VSCODE_PATH="$2"
shift 2
UGREP_ARGS=("$@")

pause_and_exit() {
    echo ""
    echo "Press Enter to close..."
    read -r
    exit "${1:-0}"
}

if ! command -v ugrep >/dev/null 2>&1; then
    echo "ERROR: ugrep not found. Please install it:"
    echo "  sudo apt install ugrep"
    pause_and_exit 1
fi

echo "Coral Search (Static)"
echo "Folder: $SEARCH_DIR"
echo ""
echo 'Query syntax: "quoted phrases" match literally, space or AND requires all'
echo 'terms, OR matches any term, NOT (or -term) excludes. Unquoted terms are'
echo 'regular expressions.'
echo ""
read -r -p "Search for: " QUERY

if [ -z "$QUERY" ]; then
    echo "No search string entered."
    pause_and_exit 0
fi

OUTPUT_FILE="/tmp/coral-search-$(date +%Y-%m-%d--%H-%M-%S).txt"

echo ""
echo "Searching..."

# -l lists matching file names only; -% is Boolean query mode and --files
# applies the query at whole-file scope. -- ends option processing so a query
# beginning with '-' (Boolean NOT) is still read as the pattern.
ugrep -r -i -l -% --files "${UGREP_ARGS[@]}" -- "$QUERY" "$SEARCH_DIR" > "$OUTPUT_FILE"
STATUS=$?

# ugrep exits 0 when it matched, 1 when it did not, and >1 on a real error.
if [ "$STATUS" -gt 1 ]; then
    echo "ugrep failed (exit code $STATUS)."
    rm -f "$OUTPUT_FILE"
    pause_and_exit "$STATUS"
fi

COUNT=$(wc -l < "$OUTPUT_FILE")

if [ "$COUNT" -eq 0 ]; then
    echo "No files matched: $QUERY"
    rm -f "$OUTPUT_FILE"
    pause_and_exit 0
fi

echo "$COUNT file(s) matched."
echo "Results: $OUTPUT_FILE"

"$VSCODE_PATH" "$OUTPUT_FILE"
