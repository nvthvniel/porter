# Porter

Automatically detect and add Python dependencies to scripts using UV.
- https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies

<br>

*Built using Claude Sonnet 4*

## Install

```bash
uv tool install git+https://github.com/nvthvniel/porter.git
```

## Uninstall
```bash
uv tool uninstall porter
```

## Usage

Porter processes one or more Python files and automatically adds their dependencies using UV's script dependency management.

### Basic Usage

```bash
# Single file
porter script.py

# Multiple files
porter test_1.py test_2.py module.py

# With options
porter --verbose --dry-run test_1.py test_2.py
```

## Options

- `--dry-run`: Show what would be done without making changes
- `--verbose`: Enable verbose output with progress tracking
- `--no-banner`: Don't show banner on startup

## Examples

```bash
# Process single file
porter script.py

# Process multiple files with verbose output
porter --verbose src/main.py src/utils.py tests/test_main.py

# Dry run to see what dependencies would be added
porter --dry-run --verbose *.py

# Real-world example
porter --verbose myproject/*.py
```

## Exit Codes

- `0`: All files processed successfully
- `1`: Some files processed successfully, some failed
- `2`: All files failed or no valid files provided
