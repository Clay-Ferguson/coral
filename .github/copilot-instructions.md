# Coral - Copilot Brief

## Essentials
- Single-file Nautilus extension in `coral_action.py`; class `CoralMenuProvider` derives from `GObject.GObject` + `Nautilus.MenuProvider` and registers three context menu items.
- `setup.sh` installs to `~/.local/share/nautilus-python/extensions/`; rerun after any code change and restart Nautilus with `nautilus -q`.
- Core constants: `VSCODE_PATH` (default `/usr/bin/code`) and `TEXT_FILE_EXTENSIONS` gate VS Code support and text detection.

## Menu Actions
- **New Markdown** appears everywhere. Prompts via `zenity --entry` with a timestamped default (`%Y-%m-%d--%H-%M-%S.md`), creates the file under the right-click target, and launches the chosen editor with `subprocess.Popen([self.VSCODE_PATH, path])`.
- **Open in VS Code** shows on folders, text-like files, or background. Resolves URIs, filters by MIME type + extension tuple, and opens VS Code in the correct mode (folder workspace vs single file).
- **Run Script** only surfaces for `.sh` files. Spawns `gnome-terminal` with `--working-directory` and wraps the script path in `bash -c '"{script}"; echo; read -n 1 -s -r -p "Press any key"'` to keep the terminal open.

## Patterns & Conventions
- Always validate file URIs: require `file://`, strip prefix, decode with `urllib.parse.unquote`, then operate on the filesystem path.
- Use both `mimetypes.guess_type()` and `TEXT_FILE_EXTENSIONS` to classify text files; keep the tuple updated if you enable new formats.
- Timestamped markdown naming uses double dashes between date/time segments; respect this when generating filenames.
- Minimal error dialogs: wrap risky IO in try/except and log via `print()` for journalctl inspection instead of UI prompts.

## Workflows
- Install/test loop: `./setup.sh`, `nautilus -q`, then open a new Nautilus window pointed at a sample directory.
- Debug by tailing logs: `journalctl -f | grep nautilus`. Add temporary prints inside handlers when Nautilus swallows tracebacks.
- Use diverse fixtures when verifying changes: folders, empty-space background, `.sh` scripts, plain text, non-text binaries to confirm menu visibility logic.

## Extension Tips
- Add actions inside `get_file_items()` (selection) or `get_background_items()` (empty space). Ensure unique `MenuItem` names under the `AddNautilusMenuItems::` namespace.
- Update `VSCODE_PATH` or replace VS Code invocations if a different editor is required; keep the central constant to avoid hardcoding.
- Include `zenity` in dependency checks when packaging or documenting; New Markdown depends on it for the filename prompt.