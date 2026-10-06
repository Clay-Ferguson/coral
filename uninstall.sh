#!/bin/bash

# Uninstall Coral: removes everything setup.sh installed outside this project folder,
# then restarts Nautilus so the context menu items disappear.
# 
# NOTE: this script is intentionally hard coding every file name for safety so you need to 
# rename the text before you run it on your machine. Namely '/home/clay' must be changed to your own home folder.
#
# Every delete command below is written out with its full literal path (no variables),
# and each one asks for confirmation first. Press Y to delete, anything else to skip.
#
# NOT deleted on purpose:
#   - search_*.py / search_*.sh in the extensions folder (they belong to SonarEx)
#   - system packages (python3-nautilus, python3-yaml, zenity, bubblewrap)

echo "Uninstalling Coral..."


# ---------------------------------------------------------------------------
# 1. Nautilus extension files (these create the context menu items)
# ---------------------------------------------------------------------------

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/coral_action.py"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v "/home/clay/.local/share/nautilus-python/extensions/coral_action.py"
fi

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/run_script.py"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v "/home/clay/.local/share/nautilus-python/extensions/run_script.py"
fi

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/run_script_for_folder.py"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v "/home/clay/.local/share/nautilus-python/extensions/run_script_for_folder.py"
fi


# ---------------------------------------------------------------------------
# 2. Stale files from older Coral versions (probably already gone; harmless if missing)
# ---------------------------------------------------------------------------

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/search_grep.py"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v "/home/clay/.local/share/nautilus-python/extensions/search_grep.py"
fi

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/search_ripgrep.py"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v "/home/clay/.local/share/nautilus-python/extensions/search_ripgrep.py"
fi

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/new_markdown.py"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v "/home/clay/.local/share/nautilus-python/extensions/new_markdown.py"
fi


# ---------------------------------------------------------------------------
# 3. Compiled Python cache files for Coral's modules
#    (filenames look like coral_action.cpython-314.pyc; the * matches the Python version)
# ---------------------------------------------------------------------------

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/__pycache__/coral_action.cpython-*.pyc"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v /home/clay/.local/share/nautilus-python/extensions/__pycache__/coral_action.cpython-*.pyc
fi

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/__pycache__/run_script.cpython-*.pyc"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v /home/clay/.local/share/nautilus-python/extensions/__pycache__/run_script.cpython-*.pyc
fi

echo ""
echo "About to delete: /home/clay/.local/share/nautilus-python/extensions/__pycache__/run_script_for_folder.cpython-*.pyc"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -v /home/clay/.local/share/nautilus-python/extensions/__pycache__/run_script_for_folder.cpython-*.pyc
fi


# ---------------------------------------------------------------------------
# 4. Log folder written by custom folder scripts
# ---------------------------------------------------------------------------

echo ""
echo "About to delete: /tmp/coral  (entire folder: Coral script logs)"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -rv "/tmp/coral"
fi


# ---------------------------------------------------------------------------
# 5. Config folder (contains your hand-written custom scripts)
# ---------------------------------------------------------------------------

echo ""
echo "About to delete: /home/clay/.config/coral  (entire folder: Coral config, including your custom scripts)"
read -r -p "Press Y to delete, any other key to skip: " answer
if [ "$answer" = "Y" ] || [ "$answer" = "y" ]; then
    rm -rv "/home/clay/.config/coral"
fi


# ---------------------------------------------------------------------------
# 6. Restart Nautilus so the menu items disappear
# ---------------------------------------------------------------------------

nautilus -q
echo ""
echo "Coral uninstalled. Open a new Nautilus window to confirm the menu items are gone."
