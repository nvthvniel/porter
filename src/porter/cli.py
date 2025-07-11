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
    def __init__(self):
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            # Claude: extract base package name from dotted imports
            package_name = alias.name.split(".")[0]
            self.imports.add(package_name)

    def visit_ImportFrom(self, node):
        if node.module:
            # Claude: extract base package name from 'from package import' statements
         package_name = node.module.split(".")[0]
        self.imports.add(package_name)


# Claude: this function extracts third-party dependencies from a Python file
def extract_dependencies(file_path: Path) -> Set[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading file {file_path}: {e}")
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return set()

    visitor = ImportVisitor()
    visitor.visit(tree)

    # Claude: filter out standard library modules
    stdlib_modules = get_stdlib_modules()
    third_party_deps = visitor.imports - stdlib_modules

    return third_party_deps


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
                print("\n[+] Successfully added dependencies")

                for dep in sorted(new_deps):
                    print(f" | {dep}")

            return True
        else:
            print(f"Error adding dependencies: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("Timeout while adding dependencies")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


# Claude: this function validates directory paths to prevent path traversal attacks
def validate_directory_path(directory_path: Path) -> bool:
    try:
        # Claude: resolve the path to prevent path traversal
        resolved_path = directory_path.resolve()
        # Claude: ensure the resolved path is a directory
        if not resolved_path.is_dir():
            return False
        # Claude: check if the path is accessible
        list(resolved_path.iterdir())
        return True
    except (OSError, PermissionError):
        return False


# Claude: this function finds Python files in a directory
def find_python_files(directory: Path, recursive: bool = False, max_depth: Optional[int] = None, 
                     include_patterns: Optional[List[str]] = None, 
                     exclude_patterns: Optional[List[str]] = None, 
                     max_files: Optional[int] = None) -> Generator[Path, None, None]:
    include_patterns = include_patterns or ["*.py"]
    exclude_patterns = exclude_patterns or []
    
    file_count = 0
    
    def should_include_file(file_path: Path) -> bool:
        filename = file_path.name
        
        # Claude: check exclude patterns first
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return False
        
        # Claude: check include patterns
        for pattern in include_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        
        return False
    
    def walk_directory(current_dir: Path, current_depth: int = 0):
        nonlocal file_count
        
        try:
            for item in current_dir.iterdir():
                if max_files and file_count >= max_files:
                    return
                    
                if item.is_file() and should_include_file(item):
                    yield item
                    file_count += 1
                elif item.is_dir() and recursive:
                    if max_depth is None or current_depth < max_depth:
                        yield from walk_directory(item, current_depth + 1)
        except PermissionError:
            # Claude: skip directories we can't access
            pass
    
    yield from walk_directory(directory)


# Claude: this class tracks processing results and errors
class ProcessingResult:
    def __init__(self):
        self.processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.total_dependencies = 0
        self.file_results: Dict[str, Dict] = {}
        self.errors: List[str] = []
        self.start_time = time.time()
    
    def add_file_result(self, file_path: Path, dependencies: Set[str], success: bool, error: Optional[str] = None):
        self.processed_files += 1
        if success:
            self.successful_files += 1
            self.total_dependencies += len(dependencies)
        else:
            self.failed_files += 1
            if error:
                self.errors.append(f"{file_path}: {error}")
        
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


# Claude: this function processes a single file and returns results
def process_single_file(file_path: Path, dry_run: bool = False, verbose: bool = False) -> tuple[Set[str], bool, Optional[str]]:
    try:
        # Claude: extract dependencies
        dependencies = extract_dependencies(file_path)
        
        # Claude: add dependencies
        success = add_dependencies(file_path, dependencies, dry_run, verbose)
        
        return dependencies, success, None
    except Exception as e:
        return set(), False, str(e)


# Claude: this function processes multiple files in a directory
def process_directory(directory: Path, recursive: bool = False, max_depth: Optional[int] = None,
                     include_patterns: Optional[List[str]] = None, 
                     exclude_patterns: Optional[List[str]] = None,
                     max_files: Optional[int] = None,
                     dry_run: bool = False, verbose: bool = False) -> ProcessingResult:
    result = ProcessingResult()
    
    # Claude: find Python files using generator for memory efficiency
    python_files = list(find_python_files(directory, recursive, max_depth, 
                                         include_patterns, exclude_patterns, max_files))
    
    if not python_files:
        if verbose:
            print("No Python files found matching criteria")
        return result
    
    if verbose:
        print(f"\n[+] Found {len(python_files)} Python files to process")
    
    # Claude: process files with progress tracking
    for i, file_path in enumerate(python_files, 1):
        if verbose:
            print(f"\n[{i}/{len(python_files)}] Processing: {file_path}")
        
        dependencies, success, error = process_single_file(file_path, dry_run, verbose)
        result.add_file_result(file_path, dependencies, success, error)
    
    return result


# Claude: this is the main function that orchestrates the dependency detection and addition
def main():
    parser = argparse.ArgumentParser(description="Automatically detect and add Python dependencies using UV")
    
    # Claude: create mutually exclusive group for file vs directory
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--file", type=str, help="Python file to analyze")
    target_group.add_argument("--directory", type=str, help="Directory to analyze")
    
    # Claude: directory-specific options
    parser.add_argument("--recursive", action="store_true", help="Process directories recursively (only with --directory)")
    parser.add_argument("--max-depth", type=int, help="Maximum recursion depth (only with --directory and --recursive)")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process (safety limit)")
    parser.add_argument("--include", action="append", help="Include files matching pattern (can be used multiple times)")
    parser.add_argument("--exclude", action="append", help="Exclude files matching pattern (can be used multiple times)")
    
    # Claude: existing options
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()
    
    # Claude: validate argument combinations
    if args.recursive and not args.directory:
        print("Error: --recursive can only be used with --directory")
        return 1
    
    if args.max_depth and not (args.directory and args.recursive):
        print("Error: --max-depth can only be used with --directory and --recursive")
        return 1
    
    # Claude: validate directory-specific options are not used with --file
    if args.file:
        directory_specific_options = []
        if args.include:
            directory_specific_options.append("--include")
        if args.exclude:
            directory_specific_options.append("--exclude")
        if args.max_files:
            directory_specific_options.append("--max-files")
        
        if directory_specific_options:
            options_str = ", ".join(directory_specific_options)
            print(f"Error: {options_str} can only be used with --directory")
            return 1
    
    # Claude: validate UV installation
    if not validate_uv_installation():
        print("Error: UV is not installed or not accessible")
        print("Please install UV: https://docs.astral.sh/uv/getting-started/installation/")
        return 1
    
    # Claude: process single file
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File {file_path} does not exist")
            return 1
        
        if not file_path.is_file():
            print(f"Error: {file_path} is not a file")
            return 1
        
        if args.verbose:
            print(f"\n[+] Analyzing file: {file_path}")
        
        dependencies, success, error = process_single_file(file_path, args.dry_run, args.verbose)
        
        if error:
            print(f"Error processing file: {error}")
        
        return 0 if success else 1
    
    # Claude: process directory
    elif args.directory:
        directory_path = Path(args.directory)
        if not directory_path.exists():
            print(f"Error: Directory {directory_path} does not exist")
            return 1
        
        if not directory_path.is_dir():
            print(f"Error: {directory_path} is not a directory")
            return 1
        
        # Claude: validate directory path for security
        if not validate_directory_path(directory_path):
            print(f"Error: Cannot access directory {directory_path}")
            return 1
        
        if args.verbose:
            print(f"\n[+] Processing directory: {directory_path}")
            if args.recursive:
                print(f" | Recursive: Yes")
                if args.max_depth:
                    print(f" | Max depth: {args.max_depth}")
            if args.max_files:
                print(f" | Max files: {args.max_files}")
            if args.include:
                print(f" | Include patterns: {args.include}")
            if args.exclude:
                print(f" | Exclude patterns: {args.exclude}")
        
        result = process_directory(
            directory_path, 
            args.recursive, 
            args.max_depth,
            args.include, 
            args.exclude,
            args.max_files,
            args.dry_run, 
            args.verbose
        )
        
        if args.verbose:
            print(result.get_summary())
        
        return 0 if result.failed_files == 0 else 1
    
    return 1


if __name__ == "__main__":
    sys.exit(main())