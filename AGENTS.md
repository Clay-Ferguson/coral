# Coral (Nautilus Extension) 

# About Coral
Coral is an extension for Linux Nautilus which adds a right-click context menu to various files and folders. It has a config file named `coral-config.yaml`, which sets up certain parameters for the app, including a 'scripts' property which allows additional custom menu items to be added to the menu that can be defined by the user by directly editing the `coral-config.yaml`

## Essentials about Coral
- Single-file Nautilus extension in `coral_action.py`; class `AddNautilusMenuItems` derives from `GObject.GObject` + `Nautilus.MenuProvider` and registers the context menu items, delegating each to a handler module.
- `setup.sh` installs to `~/.local/share/nautilus-python/extensions/`; rerun after any code change and restart Nautilus with `nautilus -q`.
- Core constants: `VSCODE_PATH` (default `/usr/bin/code`) and `CONFIG_FILE` (`~/.config/coral/coral-config.yaml`).
- Dependencies: `python3-nautilus`, `python3-yaml`, `zenity` (error dialogs), `gnome-terminal` (Run Script and custom scripts), `xclip` (Copy Full Path).
- `setup.sh` must copy every new module into the extensions dir and `chmod +x` any `.sh` helper it installs. Shell helpers locate each other via `$(dirname "${BASH_SOURCE[0]}")`, so they must land in the same directory.
- **Search moved out of this project.** The recursive content search (`Search (Interactive)` / `Search (Static)`, ugrep, the zenity results dialog, and the `search.*` config keys) now lives in the standalone SonarEx extension at `../sonarex`. Both extensions install into the same `~/.local/share/nautilus-python/extensions/` directory, so Coral's `setup.sh` must never delete `search_*.py` / `search_*.sh` there.

## Menu Actions
- **Run Script** only surfaces for `.sh` files. Spawns `gnome-terminal --working-directory=<script_dir> -- bash -c 'echo ...; bash "{script}"; echo ...; read'` to display script name/directory and keep terminal open after execution.

## Patterns & Conventions
- **URI handling**: Always validate `file://` prefix, strip it with `[7:]`, decode with `urllib.parse.unquote()`, then operate on filesystem path.
- **Timestamped naming**: Uses double dashes between segments (`YYYY-MM-DD--HH-MM-SS`); maintain this format for all generated files.
- **Async dialogs**: Use `GLib.spawn_async()` with flags `SEARCH_PATH | DO_NOT_REAP_CHILD` and `GLib.child_watch_add()` callback pattern to prevent blocking Nautilus UI. Never use blocking `subprocess.run()` for user input.
- **Error handling**: Wrap risky IO in try/except, log via `print()` for journalctl inspection. No error dialogs—keep UI non-intrusive.
- **Menu item naming**: Use `AddNautilusMenuItems::` namespace prefix for all `MenuItem` names to avoid conflicts.

## Workflows
- **Install/test loop**: Run `./setup.sh`, then `nautilus -q` to restart Nautilus. Open new Nautilus window to test changes.
- **Debugging**: Tail logs with `journalctl -f | grep nautilus` (or `journalctl -f /usr/bin/nautilus`). Add temporary `print()` statements in handlers when Nautilus swallows tracebacks—they appear in journal.
- **Testing fixtures**: Verify against diverse targets: folders, empty-space background, `.sh` scripts, and plain files, to confirm menu visibility logic works correctly across contexts.
- **Dependency installation**: `sudo apt install python3-nautilus python3-yaml zenity xclip` installs all runtime dependencies. Minimal system: only `python3-nautilus` + `zenity` required.

## Extension Points
- **New menu actions**: Add in `get_file_items()` for selection-based items or `get_background_items()` for empty-space context menus. Create `Nautilus.MenuItem` with unique `AddNautilusMenuItems::action_name` identifier and connect to handler method.
- **Changing editor**: Update `VSCODE_PATH` constant; all VS Code invocations reference this central value. Consider parameterizing if supporting multiple editors.
- **Async operations**: Always use `GLib.spawn_async()` + `GLib.child_watch_add()` pattern for dialogs/long-running tasks. Reference `_launch_zenity_dialog()` → `_on_zenity_finished()` callback chain as template.