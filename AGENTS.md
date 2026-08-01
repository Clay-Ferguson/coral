# Coral (Nautilus Extension) 

# About Coral
Coral is an extension for Linux Nautilus which adds a right-click context menu to various files and folders. It has a config file named `coral-config.yaml`, which sets up certain parameters for the app, including a 'scripts' property which allows additional custom menu items to be added to the menu that can be defined by the user by directly editing the `coral-config.yaml`

## Essentials about Coral
- Single-file Nautilus extension in `coral_action.py`; class `AddNautilusMenuItems` derives from `GObject.GObject` + `Nautilus.MenuProvider` and registers four context menu items.
- `setup.sh` installs to `~/.local/share/nautilus-python/extensions/`; rerun after any code change and restart Nautilus with `nautilus -q`.
- Core constants: `VSCODE_PATH` (default `/usr/bin/code`) and `TEXT_FILE_EXTENSIONS` gate VS Code support and text detection.
- Dependencies: `python3-nautilus`, `zenity` (for dialogs), `gnome-terminal`, `ugrep` (for both Search menu items), `pdftotext` (optional, from `poppler-utils` for PDF search).
- `setup.sh` must copy every new module/script into the extensions dir; `search_static.sh` also needs `chmod +x` there.

## Menu Actions
- **New Markdown** appears everywhere. Uses `GLib.spawn_async()` to launch `zenity --entry` non-blocking with timestamped default (`%Y-%m-%d--%H-%M-%S.md`). Callback chain: `_start_markdown_creation()` → `_launch_zenity_dialog()` → `_on_zenity_finished()` → `_finalize_markdown_creation()`. Creates file under right-click target and opens in VS Code.
- **Search (Interactive)** shows on folders/background as a single menu item (no submenu). Launches ugrep's interactive TUI (`ugrep -Q -% --files -r -i .`) in `gnome-terminal` with the folder as working directory; implemented by `SearchHandler.search_folder()` in `search_ugrep.py`, the sole search implementation. User types the pattern live in the TUI, no zenity involved. `-%` = Boolean query mode: `"quoted phrases"` are exact/literal, space/AND = all terms, OR = any, NOT/`-` = exclude, unquoted terms are regex. `--files` = queries match at whole-file scope, not per line. Honors config `search.included`/`search.excluded` patterns via ugrep `-g` globs (find-style `*/name/*` exclusions convert to `!name/`). Searches PDF content via `--filter='pdf:pdftotext -q % -'` when pdftotext is installed (ugrep executes filters directly, not via shell—no redirection/pipes allowed).
- **Search (Static)** shows on folders/background next to the interactive item. `StaticSearchHandler.search_folder_static()` in `search_static.py` (subclasses `SearchHandler` to reuse the config→glob pipeline via `build_ugrep_glob_list()`) opens `gnome-terminal` running the companion `search_static.sh`. The shell script owns all terminal-side interaction—add future prompts/options there, not in Python. It prompts for a query, runs `ugrep -r -i -l -% --files <globs> -- "$QUERY" "$SEARCH_DIR"` (absolute dir so output paths are absolute; `--` guards queries starting with `-`), writes matching paths to `/tmp/coral-search-%Y-%m-%d--%H-%M-%S.txt`, and opens it in VS Code. Script argv: `<search-dir> <vscode-path> [extra ugrep args...]`—extra args are passed as separate argv entries, so nothing is shell-quoted. Terminal auto-closes on success; pauses for Enter on error, empty query, or no matches (ugrep exit 1 = no match, >1 = error).
- **Open in VS Code** shows on folders, text-like files, or background. Resolves URIs via `urllib.parse.unquote(uri[7:])`, filters by MIME type + extension tuple, opens VS Code in correct mode (folder workspace vs single file).
- **Run Script** only surfaces for `.sh` files. Spawns `gnome-terminal --working-directory=<script_dir> -- bash -c 'echo ...; bash "{script}"; echo ...; read'` to display script name/directory and keep terminal open after execution.

## Patterns & Conventions
- **URI handling**: Always validate `file://` prefix, strip it with `[7:]`, decode with `urllib.parse.unquote()`, then operate on filesystem path.
- **Text file detection**: Dual strategy using `mimetypes.guess_type()` (check `mimetype.startswith('text/')`) AND `TEXT_FILE_EXTENSIONS` tuple. Update tuple when enabling new formats.
- **Timestamped naming**: Uses double dashes between segments (`YYYY-MM-DD--HH-MM-SS`); maintain this format for all generated files.
- **Async dialogs**: Use `GLib.spawn_async()` with flags `SEARCH_PATH | DO_NOT_REAP_CHILD` and `GLib.child_watch_add()` callback pattern to prevent blocking Nautilus UI. Never use blocking `subprocess.run()` for user input.
- **Error handling**: Wrap risky IO in try/except, log via `print()` for journalctl inspection. No error dialogs—keep UI non-intrusive.
- **Menu item naming**: Use `AddNautilusMenuItems::` namespace prefix for all `MenuItem` names to avoid conflicts.

## Workflows
- **Install/test loop**: Run `./setup.sh`, then `nautilus -q` to restart Nautilus. Open new Nautilus window to test changes.
- **Debugging**: Tail logs with `journalctl -f | grep nautilus` (or `journalctl -f /usr/bin/nautilus`). Add temporary `print()` statements in handlers when Nautilus swallows tracebacks—they appear in journal.
- **Testing fixtures**: Verify against diverse targets: folders, empty-space background, `.sh` scripts, plain text files (`.txt`, `.md`), non-text binaries to confirm menu visibility logic works correctly across contexts.
- **Dependency installation**: `sudo apt install python3-nautilus zenity ugrep poppler-utils` installs all runtime dependencies. Minimal system: only `python3-nautilus` + `zenity` required; `ugrep` needed for Search, PDF search optional.

## Extension Points
- **New menu actions**: Add in `get_file_items()` for selection-based items or `get_background_items()` for empty-space context menus. Create `Nautilus.MenuItem` with unique `AddNautilusMenuItems::action_name` identifier and connect to handler method.
- **Changing editor**: Update `VSCODE_PATH` constant; all VS Code invocations reference this central value. Consider parameterizing if supporting multiple editors.
- **File type support**: Extend `TEXT_FILE_EXTENSIONS` tuple for new text formats. Both extension check and MIME type detection run in parallel—either match triggers text file treatment.
- **Async operations**: Always use `GLib.spawn_async()` + `GLib.child_watch_add()` pattern for dialogs/long-running tasks. Reference `_launch_zenity_dialog()` → `_on_zenity_finished()` callback chain as template.