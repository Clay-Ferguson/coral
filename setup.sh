#!/bin/bash

# Create a custom Nautilus action that appears directly in the context menu
# This uses the newer Nautilus extension system
# Adds "New Markdown", "Copy Full Path", "Run Script" for .sh files, and the YAML-defined Custom Scripts

ACTIONS_DIR="$HOME/.local/share/nautilus-python/extensions"
ACTION_FILE="$ACTIONS_DIR/coral_action.py"

echo "Setting up Coral - direct context menu action for VS Code..."

# Create the directory
mkdir -p "$ACTIONS_DIR"

# Copy the Python extension from the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/coral_action.py" "$ACTION_FILE"
cp "$SCRIPT_DIR/new_markdown.py" "$ACTIONS_DIR/new_markdown.py"
cp "$SCRIPT_DIR/run_script_for_folder.py" "$ACTIONS_DIR/run_script_for_folder.py"
cp "$SCRIPT_DIR/run_script.py" "$ACTIONS_DIR/run_script.py"

# Remove stale modules left behind by older installs.
# NOTE: do NOT delete search_ugrep.py / search_static.py / search_static.sh /
# search_results_dialog.sh here -- search moved to the SonarEx extension, which
# installs files with those exact names into this same shared directory.
rm -f "$ACTIONS_DIR/search_grep.py" "$ACTIONS_DIR/search_ripgrep.py"
rm -rf "$ACTIONS_DIR/__pycache__"

# Make sure it's executable
chmod +x "$ACTION_FILE"

# Install python3-nautilus if needed
echo "Installing required dependencies..."
sudo apt update && sudo apt install -y python3-nautilus python3-yaml zenity

# Install bubblewrap if not already installed
# See example YAML for why we might want to install (and do install) bubblewrap here,
# even though it's not actually needed for Coral itself.
if ! command -v bwrap &> /dev/null; then
    echo "Installing bubblewrap for sandboxed VSCode launching..."
    sudo apt install -y bubblewrap
else
    echo "bubblewrap is already installed."
fi

# Create config directory and default config file if it doesn't exist
CONFIG_DIR="$HOME/.config/coral"
CONFIG_FILE="$CONFIG_DIR/coral-config.yaml"

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default configuration file..."
    cat > "$CONFIG_FILE" << 'EOF'
# Coral Nautilus Extension Configuration
# TIP: Run 'nautilus -q' after editing this file, to make it go into effect

# Custom scripts appear as menu items when you right-click a folder.
# Each script runs with $OPEN_FOLDER set to the full path of that folder.
# See the README for more examples.

scripts:
  - name: 🔧  Open in VSCode
    content: |
      code $OPEN_FOLDER
EOF
    echo "Default config created at: $CONFIG_FILE"
else
    echo "Config file already exists at: $CONFIG_FILE"
fi

nautilus -q
echo "Setup complete! Right-click on folders and text files to see the new options."