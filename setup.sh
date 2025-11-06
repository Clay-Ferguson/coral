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
cp "$SCRIPT_DIR/search.py" "$ACTIONS_DIR/search.py"
cp "$SCRIPT_DIR/new_markdown.py" "$ACTIONS_DIR/new_markdown.py"

# Make sure it's executable
chmod +x "$ACTION_FILE"

# Install python3-nautilus if needed
echo "Installing required dependencies..."
sudo apt update && sudo apt install -y python3-nautilus python3-yaml

# Create config directory and default config file if it doesn't exist
CONFIG_DIR="$HOME/.config/coral"
CONFIG_FILE="$CONFIG_DIR/coral-config.yaml"

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default configuration file..."
    cat > "$CONFIG_FILE" << 'EOF'
# Coral Nautilus Extension Configuration

search:
  # Patterns to exclude from searches (glob patterns)
  # These directories/files will be skipped during recursive search
  excluded:
    - "*/node_modules/*"
    - "*/.git/*"
    - "*/.venv/*"
    - "*/__pycache__/*"
    - "*/venv/*"
    - "*/.svn/*"
    - "*/.hg/*"
    - "*/build/*"
    - "*/dist/*"
    - "*/.next/*"
    - "*/.nuxt/*"
EOF
    echo "Default config created at: $CONFIG_FILE"
else
    echo "Config file already exists at: $CONFIG_FILE"
fi

