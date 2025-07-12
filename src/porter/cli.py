#!/usr/bin/env python3

import argparse
import ast
import sys
import subprocess
import fnmatch
import time
from pathlib import Path
from typing import Set, List, Optional, Dict, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed


# Claude: this class extracts imports from Python AST
class ImportVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path):
        self.imports = set()
        self.local_imports = set()
        self.file_path = file_path

    def visit_Import(self, node):
        for alias in node.names:
            # Claude: extract base package name from dotted imports
            package_name = alias.name.split(".")[0]
            # Claude: check if this is a local import
            if detect_local_import(package_name, self.file_path):
                self.local_imports.add(package_name)
            else:
                self.imports.add(package_name)

    def visit_ImportFrom(self, node):
        if node.module:
            # Claude: extract base package name from 'from package import' statements
            package_name = node.module.split(".")[0]
            # Claude: check if this is a local import
            if detect_local_import(node.module, self.file_path):
                self.local_imports.add(node.module)
            else:
                self.imports.add(package_name)


# Claude: this function extracts third-party dependencies from a Python file
def extract_dependencies(file_path: Path) -> tuple[Set[str], Set[str]]:
    # Claude: validate file size to prevent processing extremely large files
    try:
        file_size = file_path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            print(f"Error: File {file_path} is too large ({file_size} bytes) - skipping for safety")
            return set(), set()
        if file_size == 0:
            print(f"Warning: File {file_path} is empty - skipping")
            return set(), set()
    except (OSError, PermissionError) as e:
        print(f"Error accessing file {file_path}: {e}")
        return set(), set()

    # Claude: read file with improved encoding handling
    try:
        # Claude: attempt UTF-8 first, then fall back to other encodings
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = None
        encoding_used = None
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    content = file.read()
                    encoding_used = encoding
                    break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print(f"Error: Could not decode file {file_path} with any supported encoding")
            return set(), set()
            
    except (OSError, PermissionError) as e:
        print(f"Error reading file {file_path}: {e}")
        return set(), set()

    # Claude: validate that the file contains valid Python syntax
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path} (line {e.lineno}): {e.msg}")
        print(f"This may not be a valid Python file. Please check the file contents.")
        return set(), set()

    visitor = ImportVisitor(file_path)
    visitor.visit(tree)

    # Claude: filter out standard library modules
    stdlib_modules = get_stdlib_modules()
    third_party_deps = visitor.imports - stdlib_modules

    return third_party_deps, visitor.local_imports


# Claude: this function gets the standard library module names
def get_stdlib_modules() -> Set[str]:
    # Claude: use sys.stdlib_module_names for Python 3.10+
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)
    
    # Claude: fallback for older Python versions
    try:
        import isort
        return set(isort.stdlibs.py3.stdlib)
    except ImportError:
        # Claude: minimal fallback list of common stdlib modules
        return {
            "os", "sys", "json", "re", "datetime", "collections", "itertools",
            "functools", "pathlib", "urllib", "http", "email", "xml", "html",
            "csv", "sqlite3", "logging", "argparse", "subprocess", "threading",
            "multiprocessing", "asyncio", "typing", "dataclasses", "enum",
            "abc", "contextlib", "weakref", "copy", "pickle", "base64", "hashlib",
            "hmac", "secrets", "uuid", "random", "math", "statistics", "decimal",
            "fractions", "cmath", "time", "calendar", "zoneinfo", "locale",
            "gettext", "io", "StringIO", "BytesIO", "tempfile", "glob", "fnmatch",
            "linecache", "shutil", "stat", "filecmp", "tarfile", "zipfile",
            "gzip", "bz2", "lzma", "configparser", "platform", "ctypes",
            "struct", "codecs", "unicodedata", "stringprep", "readline",
            "rlcompleter", "cmd", "shlex", "tkinter", "turtle", "pdb", "profile",
            "pstats", "timeit", "trace", "traceback", "gc", "inspect", "site",
            "sysconfig", "importlib", "keyword", "pkgutil", "modulefinder",
            "runpy", "parser", "ast", "symtable", "token", "tokenize", "tabnanny",
            "pyclbr", "py_compile", "compileall", "dis", "pickletools", "distutils",
            "venv", "zipapp", "faulthandler", "tracemalloc", "warnings", "contextlib"
        }


# Claude: this function detects if an import is a local file or package
def detect_local_import(import_name: str, file_path: Path) -> bool:
    # Claude: handle relative imports (starting with dots)
    if import_name.startswith("."):
        return True
    
    # Claude: get the directory containing the current file
    file_dir = file_path.parent
    
    # Claude: resolve the file directory to prevent path traversal
    try:
        resolved_file_dir = file_dir.resolve()
    except (OSError, RuntimeError):
        return False
    
    # Claude: split import name for handling dotted imports
    import_parts = import_name.split(".")
    base_import = import_parts[0]
    
    # Claude: check for same directory .py file
    potential_py_file = resolved_file_dir / f"{base_import}.py"
    if potential_py_file.exists() and potential_py_file.is_file():
        # Claude: validate file is within expected boundaries
        try:
            resolved_potential = potential_py_file.resolve()
            if str(resolved_potential).startswith(str(resolved_file_dir)):
                return True
        except (OSError, RuntimeError):
            pass
    
    # Claude: check for package directory with __init__.py
    potential_package_dir = resolved_file_dir / base_import
    if potential_package_dir.exists() and potential_package_dir.is_dir():
        init_file = potential_package_dir / "__init__.py"
        if init_file.exists() and init_file.is_file():
            # Claude: validate package is within expected boundaries
            try:
                resolved_package = potential_package_dir.resolve()
                if str(resolved_package).startswith(str(resolved_file_dir)):
                    return True
            except (OSError, RuntimeError):
                pass
    
    # Claude: check for subdirectory imports (e.g., utils.helper)
    if len(import_parts) > 1:
        # Claude: construct potential subdirectory path
        subdir_path = resolved_file_dir
        for part in import_parts[:-1]:
            subdir_path = subdir_path / part
        
        # Claude: check for .py file in subdirectory
        potential_subdir_file = subdir_path / f"{import_parts[-1]}.py"
        if potential_subdir_file.exists() and potential_subdir_file.is_file():
            try:
                resolved_subdir = potential_subdir_file.resolve()
                if str(resolved_subdir).startswith(str(resolved_file_dir)):
                    return True
            except (OSError, RuntimeError):
                pass
    
    return False


# Claude: this function displays the porter ASCII art banner
def display_banner():
    banner = """
██████╗  ██████╗ ██████╗ ████████╗███████╗██████╗ 
██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
██████╔╝██║   ██║██████╔╝   ██║   █████╗  ██████╔╝
██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══╝  ██╔══██╗
██║     ╚██████╔╝██║  ██║   ██║   ███████╗██║  ██║
╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
"""
    print(banner)
    print("└─ Automatically detect and add Python dependencies to a script using UV")
    print("└─ GitHub: https://github.com/nvthvniel/porter")


# Claude: this function validates UV installation
def validate_uv_installation() -> bool:
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            shell=False,  # Claude: prevent command injection
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Claude: this function gets existing script dependencies
def get_existing_dependencies(file_path: Path) -> Set[str]:
    try:
        result = subprocess.run(
            ["uv", "tree", "--python-platform", str(file_path)],
            capture_output=True,
            text=True,
            shell=False,  # Claude: prevent command injection
            timeout=30
        )
        # Claude: parse output to extract existing dependencies
        # This is a simplified approach - UV's tree output format may vary
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            deps = set()
            for line in lines:
                if line.strip() and not line.startswith(" "):
                    # Claude: extract package name from tree output
                    package = line.split()[0]
                    deps.add(package)
            return deps
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return set()


# Claude: this function adds dependencies using UV
def add_dependencies(file_path: Path, dependencies: Set[str], dry_run: bool = False, verbose: bool = False) -> bool:
    if not dependencies:
        if verbose:
            print("No dependencies to add")
        return True

    # Claude: validate file path to prevent path traversal
    resolved_path = file_path.resolve()
    if not resolved_path.is_file():
        print(f"Error: {file_path} is not a valid file")
        return False

    # Claude: get existing dependencies to avoid duplicates
    existing_deps = get_existing_dependencies(resolved_path)
    new_deps = dependencies - existing_deps

    if not new_deps:
        if verbose:
            print("All dependencies already exist")
        return True

    if dry_run:
        print(f"DRY RUN: Would execute: uv add --script {resolved_path} {' '.join(sorted(new_deps))}")
        return True

    try:
        # Claude: batch all dependencies in a single command for efficiency
        cmd = ["uv", "add", "--script", str(resolved_path)] + sorted(new_deps)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,  # Claude: prevent command injection
            timeout=120
        )

        if result.returncode == 0:
            if verbose:

                for dep in sorted(new_deps):
                    print(f" | {dep}")

            return True
        else:
            print(f"Error adding dependencies: {result.stderr}")
            print("Suggestion: Check if the dependencies exist or if there are network issues")
            return False

    except subprocess.TimeoutExpired:
        print("Timeout while adding dependencies (exceeded 2 minutes)")
        print("Suggestion: Check network connectivity or try with fewer dependencies")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Suggestion: Please check the file permissions and UV installation")
        return False






# Claude: this class tracks processing results and errors
class ProcessingResult:
    def __init__(self):
        self.processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.total_dependencies = 0
        self.file_results: Dict[str, Dict] = {}
        self.errors: List[str] = []
        self.local_import_warnings: Dict[str, Set[str]] = {}
        self.start_time = time.time()
    
    def add_file_result(self, file_path: Path, dependencies: Set[str], success: bool, local_imports: Set[str] = set(), error: Optional[str] = None):
        self.processed_files += 1
        if success:
            self.successful_files += 1
            self.total_dependencies += len(dependencies)
        else:
            self.failed_files += 1
            if error:
                self.errors.append(f"{file_path}: {error}")
        
        # Claude: store local imports if any detected
        if local_imports:
            self.local_import_warnings[str(file_path)] = local_imports
        
        self.file_results[str(file_path)] = {
            "dependencies": dependencies,
            "success": success,
            "error": error
        }
    
    def get_summary(self) -> str:
        elapsed_time = time.time() - self.start_time
        
        summary = f"\n[+] Processing Summary:\n"
        summary += f" | Files processed: {self.processed_files}\n"
        summary += f" | Successful: {self.successful_files}\n"
        summary += f" | Failed: {self.failed_files}\n"
        summary += f" | Total dependencies added: {self.total_dependencies}\n"
        summary += f" | Time taken: {elapsed_time:.2f} seconds\n"
        
        if self.errors:
            summary += f"\n[!] Errors encountered:\n"
            for error in self.errors:
                summary += f" | {error}\n"
        
        return summary
    
    def print_local_import_warnings(self):
        # Claude: display local import warnings in grouped format after processing
        if self.local_import_warnings:
            print(f"\n[-] Warning: Local imports detected, these will not be included. Consider using uv projects")
            for file_path, local_imports in self.local_import_warnings.items():
                for local_import in sorted(local_imports):
                    print(f" | {file_path}/{local_import}")


# Claude: this function processes a single file and returns results
def process_single_file(file_path: Path, dry_run: bool = False, verbose: bool = False) -> tuple[Set[str], Set[str], bool, Optional[str]]:
    try:
        # Claude: extract dependencies and local imports
        external_dependencies, local_imports = extract_dependencies(file_path)
        
        # Claude: add only external dependencies
        success = add_dependencies(file_path, external_dependencies, dry_run, verbose)
        
        return external_dependencies, local_imports, success, None
    except Exception as e:
        return set(), set(), False, str(e)


# Claude: this function validates and processes multiple files
def validate_file_list(file_paths: List[str], verbose: bool = False) -> List[Path]:
    validated_files = []
    seen_paths = set()
    
    for file_str in file_paths:
        file_path = Path(file_str)
        
        # Claude: resolve path to handle relative paths and detect duplicates
        try:
            resolved_path = file_path.resolve()
        except (OSError, RuntimeError) as e:
            print(f"Error: Cannot resolve path {file_path}: {e}")
            continue
        
        # Claude: check for duplicates
        if str(resolved_path) in seen_paths:
            if verbose:
                print(f"Warning: Duplicate file path ignored: {file_path}")
            continue
        seen_paths.add(str(resolved_path))
        
        # Claude: validate file exists
        if not resolved_path.exists():
            print(f"Error: File does not exist: {file_path}")
            continue
        
        # Claude: validate it's a file
        if not resolved_path.is_file():
            print(f"Error: Path is not a file: {file_path}")
            continue
        
        # Claude: validate Python file extension for security
        if not resolved_path.name.lower().endswith(".py"):
            print(f"Error: File is not a Python file: {file_path}")
            continue
        
        validated_files.append(resolved_path)
    
    return validated_files


# Claude: this function processes multiple files with progress tracking
def process_multiple_files(file_paths: List[str], dry_run: bool = False, verbose: bool = False) -> ProcessingResult:
    result = ProcessingResult()
    
    # Claude: validate all files upfront
    valid_files = validate_file_list(file_paths, verbose)
    
    if not valid_files:
        if verbose:
            print("No valid Python files to process")
        return result
    
    if verbose:
        print(f"\n[+] Processing {len(valid_files)} Python files")
    
    # Claude: process files sequentially with progress tracking
    for i, file_path in enumerate(valid_files, 1):
        if verbose:
            print(f"\n[+] {i}/{len(valid_files)}: {file_path}")
        
        dependencies, local_imports, success, error = process_single_file(file_path, dry_run, verbose)
        result.add_file_result(file_path, dependencies, success, local_imports, error)
        
        # Claude: provide immediate feedback for failures
        if not success and error:
            print(f"Error processing {file_path}: {error}")
    
    # Claude: display all local import warnings after processing
    result.print_local_import_warnings()
    
    return result




# Claude: this is the main function that orchestrates the dependency detection and addition
def main():
    parser = argparse.ArgumentParser(description="Automatically detect and add Python dependencies using UV")
    
    # Claude: positional arguments for multiple files
    parser.add_argument("files", nargs="+", metavar="FILE", help="Python files to analyze")
    
    # Claude: options
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--no-banner", action="store_true", help="Disable ASCII art banner display")

    args = parser.parse_args()
    
    # Claude: validate UV installation
    if not validate_uv_installation():
        print("Error: UV is not installed or not accessible")
        print("Please install UV: https://docs.astral.sh/uv/getting-started/installation/")
        return 1
    
    # Claude: display banner after UV validation but before file processing
    if not args.no_banner:
        display_banner()
    
    # Claude: process multiple files
    result = process_multiple_files(args.files, args.dry_run, args.verbose)
    
    # Claude: display summary if verbose or if there were any issues
    if args.verbose or result.failed_files > 0:
        print(result.get_summary())
    
    # Claude: intelligent exit codes - 0 for all success, 1 for some failures, 2 for all failures
    if result.processed_files == 0:
        return 2  # Claude: no valid files processed
    elif result.failed_files == 0:
        return 0  # Claude: all files processed successfully
    elif result.successful_files == 0:
        return 2  # Claude: all files failed
    else:
        return 1  # Claude: mixed results


if __name__ == "__main__":
    sys.exit(main())