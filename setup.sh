#!/bin/bash

# Create a custom Nautilus action that appears directly in the context menu
# This uses the newer Nautilus extension system
# Adds "Open in VS Code" for folders and text files, "Run Script" for .sh files, and "New Markdown" for creating timestamped markdown files

ACTIONS_DIR="$HOME/.local/share/nautilus-python/extensions"
ACTION_FILE="$ACTIONS_DIR/coral_action.py"

echo "Setting up Coral - direct context menu action for VS Code..."

# Create the directory
mkdir -p "$ACTIONS_DIR"

# Copy the Python extension from the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/coral_action.py" "$ACTION_FILE"

# Make sure it's executable
chmod +x "$ACTION_FILE"

# Install python3-nautilus if needed
echo "Installing required dependencies..."
sudo apt update && sudo apt install -y python3-nautilus

