# Coral Configuration

Coral uses a YAML configuration file located at `~/.config/coral/coral-config.yaml`.

## Configuration Options

### Search Exclusions

You can exclude specific directories and files from search results using glob patterns.

```yaml
search:
  excluded:
    - "*/node_modules/*"    # Exclude all node_modules directories
    - "*/.git/*"            # Exclude .git directories
    - "*/.venv/*"           # Exclude Python virtual environments
    - "*/__pycache__/*"     # Exclude Python cache directories
```

#### How Exclusions Work

- Exclusions use **glob patterns** that are passed to the `find` command
- The `*` wildcard matches any characters
- Patterns are matched against the full path
- Excluded directories are pruned from the search (not descended into)

#### Common Patterns to Exclude

**JavaScript/Node.js:**
- `*/node_modules/*` - npm packages
- "*/.next/*" - Next.js build output
- `*/.nuxt/*` - Nuxt.js build output
- `*/dist/*` - Distribution/build output
- `*/build/*` - Build artifacts

**Python:**
- `*/.venv/*` - Virtual environments
- `*/venv/*` - Alternative venv naming
- `*/__pycache__/*` - Compiled bytecode
- `*/.pytest_cache/*` - Pytest cache
- `*.egg-info/*` - Package metadata

**Version Control:**
- `*/.git/*` - Git repository data
- `*/.svn/*` - Subversion data
- `*/.hg/*` - Mercurial data

**IDEs:**
- `*/.vscode/*` - VS Code settings
- `*/.idea/*` - JetBrains IDE settings
- `*/.eclipse/*` - Eclipse settings

**Other:**
- `*/target/*` - Java/Maven build output
- `*/bin/*` - Compiled binaries
- `*/obj/*` - Object files (.NET, C++)
- `*/.cache/*` - Cache directories

#### Adding Your Own Exclusions

Edit `~/.config/coral/coral-config.yaml` and add patterns to the `excluded` list:

```yaml
search:
  excluded:
    - "*/node_modules/*"
    - "*/.git/*"
    - "*/my_custom_dir/*"      # Add your custom exclusion here
    - "*/temp/*"               # Exclude temporary directories
    - "*/.backup/*"            # Exclude backup directories
```

Changes take effect immediately on the next search - no need to restart Nautilus.

## Default Configuration

When you first run `./setup.sh`, a default configuration file is created with sensible exclusions for common development directories. You can customize it to match your workflow.

## Troubleshooting

**Config file not found:**
- Run `./setup.sh` to create the default config
- Or manually create `~/.config/coral/coral-config.yaml`

**Exclusions not working:**
- Check the config file syntax (YAML is indentation-sensitive)
- Verify glob patterns match your directory structure
- Check terminal output during search for any error messages

**Python YAML library not available:**
- Install it: `sudo apt install python3-yaml`
- Or run `./setup.sh` which installs it automatically
