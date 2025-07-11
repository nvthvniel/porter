# Porter

Automatically detect and add Python dependencies to a script using UV.

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

### Process Single File

```bash
porter --file script.py
```

### Process Directory

```bash
# Process all Python files in directory (non-recursive)
porter --directory /path/to/project

# Process directory recursively
porter --directory /path/to/project --recursive

# Process with filtering and limits
porter --directory /path/to/project --recursive --exclude "test_*.py" --max-files 50
```

## Options

### Target Selection (Required)
- `--file FILE`: Process single Python file
- `--directory DIRECTORY`: Process directory of Python files

### Directory Processing
- `--recursive`: Process directories recursively (only with --directory)
- `--max-depth N`: Maximum recursion depth (only with --directory and --recursive)
- `--max-files N`: Maximum number of files to process (safety limit)
- `--include PATTERN`: Include files matching pattern (can be used multiple times)
- `--exclude PATTERN`: Exclude files matching pattern (can be used multiple times)

### General Options
- `--dry-run`: Show what would be done without making changes
- `--verbose`: Enable verbose output

## Examples

```bash
# Process single file
porter --file script.py --dry-run --verbose

# Process directory with exclusions
porter --directory ./src --exclude "test_*.py" --exclude "*_test.py" --verbose

# Process directory recursively with depth limit
porter --directory ./project --recursive --max-depth 3 --max-files 100

# Process only specific files
porter --directory ./scripts --include "main_*.py" --include "run_*.py"
```
