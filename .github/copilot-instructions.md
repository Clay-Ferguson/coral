# Coral - Copilot Brief

## Essentials
- Single-file Nautilus extension in `coral_action.py`; class `AddNautilusMenuItems` derives from `GObject.GObject` + `Nautilus.MenuProvider` and registers four context menu items.
- `setup.sh` installs to `~/.local/share/nautilus-python/extensions/`; rerun after any code change and restart Nautilus with `nautilus -q`.
- Core constants: `VSCODE_PATH` (default `/usr/bin/code`) and `TEXT_FILE_EXTENSIONS` gate VS Code support and text detection.
- Dependencies: `python3-nautilus`, `zenity` (for dialogs), `gnome-terminal`, `pdftotext` (optional, from `poppler-utils` for PDF search).

## Menu Actions
- **New Markdown** appears everywhere. Uses `GLib.spawn_async()` to launch `zenity --entry` non-blocking with timestamped default (`%Y-%m-%d--%H-%M-%S.md`). Callback chain: `_start_markdown_creation()` → `_launch_zenity_dialog()` → `_on_zenity_finished()` → `_finalize_markdown_creation()`. Creates file under right-click target and opens in VS Code.
- **Search** shows on folders/background. Prompts for search term via zenity, generates temporary bash script at `/tmp/coral-search-script.sh` that uses `grep -i` for regular files and `pdftotext | grep` for PDFs. Results written to timestamped `/tmp/coral-search--YYYY-MM-DD--HH-MM-SS.md` with clickable `file://` URLs and opened in VS Code. Search runs in `gnome-terminal` for live progress feedback.
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
- **Dependency installation**: `sudo apt install python3-nautilus zenity poppler-utils` installs all runtime dependencies. Minimal system: only `python3-nautilus` + `zenity` required; PDF search optional.

## Extension Points
- **New menu actions**: Add in `get_file_items()` for selection-based items or `get_background_items()` for empty-space context menus. Create `Nautilus.MenuItem` with unique `AddNautilusMenuItems::action_name` identifier and connect to handler method.
- **Changing editor**: Update `VSCODE_PATH` constant; all VS Code invocations reference this central value. Consider parameterizing if supporting multiple editors.
- **File type support**: Extend `TEXT_FILE_EXTENSIONS` tuple for new text formats. Both extension check and MIME type detection run in parallel—either match triggers text file treatment.
- **Async operations**: Always use `GLib.spawn_async()` + `GLib.child_watch_add()` pattern for dialogs/long-running tasks. Reference `_launch_zenity_dialog()` → `_on_zenity_finished()` callback chain as template.