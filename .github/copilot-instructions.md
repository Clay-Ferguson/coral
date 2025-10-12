# Coral - AI Development Guide

## Project Overview
Coral is a Nautilus file manager extension that provides developer-focused context menu actions. It's a single-file Python extension using GObject introspection to integrate with GNOME's Nautilus file manager.

## Architecture

### Core Components
- **`coral_action.py`**: Single main file implementing the Nautilus extension
- **`setup.sh`**: Installation script that copies the extension to `~/.local/share/nautilus-python/extensions/`
- **Extension Pattern**: Uses GObject inheritance with `Nautilus.MenuProvider` interface

### Key Architecture Decisions
- **Single file design**: All functionality in one Python file for simplicity
- **Class constants for configuration**: `VSCODE_PATH` and `TEXT_FILE_EXTENSIONS` defined as class variables for easy modification
- **Dual context support**: Implements both `get_file_items()` (selection-based) and `get_background_items()` (empty space) menu providers

## Development Patterns

### Menu Item Creation Pattern
```python
item = Nautilus.MenuItem(
    name='AddNautilusMenuItems::unique_action_name',
    label='Display Name',
    tip='Tooltip description'
)
item.connect('activate', self.handler_method, context_object)
```

### File Type Detection Strategy
Uses **dual detection**: MIME types (`mimetypes.guess_type()`) + file extension fallback via `TEXT_FILE_EXTENSIONS` tuple. This ensures reliability across different file systems and configurations.

### URI Handling Convention
All file operations follow this pattern:
1. Check `file.get_uri().startswith('file://')`
2. Decode with `urllib.parse.unquote(uri[7:])`
3. Use decoded path for file operations

## Critical Workflows

### Installation & Testing
```bash
./setup.sh                 # Install extension
nautilus -q                # Restart Nautilus
nautilus /path/to/test     # Test in new window
```

### Development Iteration
After code changes:
1. Run `./setup.sh` to copy updated file
2. Restart Nautilus with `nautilus -q`
3. Test context menus on various file types

### Debugging
- Extension errors appear in system logs: `journalctl -f | grep nautilus`
- Python errors are often silent in Nautilus - add `print()` statements for debugging
- Test different file types: folders, `.sh` scripts, text files, unknown files

## Project-Specific Conventions

### Timestamp Format
Uses `datetime.now().strftime('%Y-%m-%d--%H-%M-%S')` for markdown file naming (note double dashes)

### Terminal Command Construction
For shell script execution, uses `gnome-terminal` with specific pattern:
- `--working-directory=` for correct context
- `--` separator before bash commands
- Interactive prompt to keep terminal open

### Error Handling
Minimal error handling by design - uses try/catch around file operations but doesn't show user dialogs (following Nautilus extension best practices)

## Integration Points

### External Dependencies
- **Nautilus Python bindings**: `python3-nautilus` package required
- **GObject Introspection**: `gi.repository.Nautilus`, `gi.repository.GObject`
- **VS Code**: Hardcoded path `/usr/bin/code` (configurable via `VSCODE_PATH`)
- **gnome-terminal**: Used for script execution

### File System Integration
- Installs to: `~/.local/share/nautilus-python/extensions/`
- Creates files with system umask permissions
- Respects Nautilus file URI scheme

## Extension Points

### Adding New File Types
Update `TEXT_FILE_EXTENSIONS` tuple in class definition. The extension uses both MIME type detection and extension matching for maximum compatibility.

### Adding New Actions
Follow the established pattern in `get_file_items()` or `get_background_items()`:
1. Create conditional logic for when action should appear
2. Create `Nautilus.MenuItem` with unique name
3. Connect to handler method
4. Add to items list

### Modifying External Tool Paths
Update class constants (`VSCODE_PATH`) rather than hardcoding paths in methods.