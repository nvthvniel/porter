#!/usr/bin/env python3

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Claude: add the parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from porter.cli import (
    find_python_files,
    validate_directory_path,
    extract_dependencies
)


# Claude: test class for file validation scenarios
class TestFileValidation(unittest.TestCase):
    
    def setUp(self):
        # Claude: create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        # Claude: cleanup temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_python_file_extension_validation(self):
        """Claude: test that only .py files are accepted"""
        # Claude: create files with different extensions
        files = [
            ("valid.py", "import os"),
            ("invalid.txt", "import os"),
            ("invalid.js", "const os = require('os');"),
            ("invalid.pyc", "compiled bytecode"),
            ("invalid.pyo", "optimized bytecode"),
            ("invalid", "no extension")
        ]
        
        for filename, content in files:
            file_path = self.temp_path / filename
            file_path.write_text(content)
        
        # Claude: find Python files
        python_files = list(find_python_files(self.temp_path, verbose=False))
        
        # Claude: should only find the .py file
        self.assertEqual(len(python_files), 1)
        self.assertEqual(python_files[0].name, "valid.py")
    
    def test_case_insensitive_extension_validation(self):
        """Claude: test that .py extension matching is case insensitive"""
        # Claude: create files with different case extensions
        files = [
            ("lower.py", "import os"),
            ("upper.PY", "import os"),
            ("mixed.Py", "import os"),
            ("mixed2.pY", "import os")
        ]
        
        for filename, content in files:
            file_path = self.temp_path / filename
            file_path.write_text(content)
        
        # Claude: find Python files
        python_files = list(find_python_files(self.temp_path, verbose=False))
        
        # Claude: should find all Python files regardless of case
        self.assertEqual(len(python_files), 4)
        file_names = {f.name for f in python_files}
        self.assertEqual(file_names, {"lower.py", "upper.PY", "mixed.Py", "mixed2.pY"})
    
    def test_file_size_validation(self):
        """Claude: test file size validation limits"""
        # Claude: create a normal Python file
        normal_file = self.temp_path / "normal.py"
        normal_file.write_text("import os")
        
        # Claude: create a file that will be mocked as too large
        large_file = self.temp_path / "large.py"
        large_file.write_text("import requests")
        
        # Claude: mock the large file's size
        def mock_stat(follow_symlinks=True):
            if self.name == "large.py":
                mock_stat_result = Mock()
                mock_stat_result.st_size = 11 * 1024 * 1024  # 11MB
                mock_stat_result.st_mode = 0o100644  # regular file
                return mock_stat_result
            else:
                return self.stat(follow_symlinks=follow_symlinks)
        
        # Claude: patch the stat method on the large file specifically
        original_stat = Path.stat
        def patched_stat(self, follow_symlinks=True):
            if self.name == "large.py":
                mock_stat_result = Mock()
                mock_stat_result.st_size = 11 * 1024 * 1024  # 11MB
                mock_stat_result.st_mode = 0o100644  # regular file
                return mock_stat_result
            else:
                return original_stat(self, follow_symlinks=follow_symlinks)
        
        with patch.object(Path, 'stat', patched_stat):
            with patch('builtins.print') as mock_print:
                python_files = list(find_python_files(self.temp_path, verbose=True))
        
        # Claude: should only find the normal file, not the large one
        self.assertEqual(len(python_files), 1)
        self.assertEqual(python_files[0].name, "normal.py")
        
        # Claude: should print warning about large file
        mock_print.assert_called()
        self.assertIn("too large", str(mock_print.call_args))
    
    def test_file_access_validation(self):
        """Claude: test file access validation"""
        # Claude: create a valid Python file
        valid_file = self.temp_path / "valid.py"
        valid_file.write_text("import os")
        
        # Claude: create another file that will have access issues
        access_file = self.temp_path / "access.py"
        access_file.write_text("import requests")
        
        # Claude: mock stat to raise permission error for access_file
        original_stat = Path.stat
        def patched_stat(self, follow_symlinks=True):
            if self.name == "access.py":
                raise PermissionError("Access denied")
            else:
                return original_stat(self, follow_symlinks=follow_symlinks)
        
        with patch.object(Path, 'stat', patched_stat):
            python_files = list(find_python_files(self.temp_path, verbose=False))
        
        # Claude: should only find the accessible file
        self.assertEqual(len(python_files), 1)
        self.assertEqual(python_files[0].name, "valid.py")
    
    def test_include_exclude_patterns(self):
        """Claude: test include/exclude pattern functionality"""
        # Claude: create various Python files
        files = [
            ("app.py", "import os"),
            ("test_app.py", "import unittest"),
            ("main.py", "import sys"),
            ("test_main.py", "import pytest"),
            ("__init__.py", ""),
            ("setup.py", "from setuptools import setup")
        ]
        
        for filename, content in files:
            file_path = self.temp_path / filename
            file_path.write_text(content)
        
        # Claude: test with exclude patterns
        python_files = list(find_python_files(
            self.temp_path, 
            exclude_patterns=["test_*", "__*"], 
            verbose=False
        ))
        
        # Claude: should exclude test files and __init__.py
        file_names = {f.name for f in python_files}
        expected_names = {"app.py", "main.py", "setup.py"}
        self.assertEqual(file_names, expected_names)
    
    def test_recursive_directory_traversal(self):
        """Claude: test recursive directory traversal"""
        # Claude: create nested directory structure
        sub_dir = self.temp_path / "subdir"
        sub_dir.mkdir()
        
        deep_dir = sub_dir / "deep"
        deep_dir.mkdir()
        
        # Claude: create Python files at different levels
        (self.temp_path / "root.py").write_text("import os")
        (sub_dir / "sub.py").write_text("import sys")
        (deep_dir / "deep.py").write_text("import json")
        
        # Claude: test non-recursive (should find only root level)
        files_non_recursive = list(find_python_files(self.temp_path, recursive=False, verbose=False))
        self.assertEqual(len(files_non_recursive), 1)
        self.assertEqual(files_non_recursive[0].name, "root.py")
        
        # Claude: test recursive (should find all files)
        files_recursive = list(find_python_files(self.temp_path, recursive=True, verbose=False))
        self.assertEqual(len(files_recursive), 3)
        file_names = {f.name for f in files_recursive}
        self.assertEqual(file_names, {"root.py", "sub.py", "deep.py"})
    
    def test_max_depth_limit(self):
        """Claude: test maximum depth limit in recursive traversal"""
        # Claude: create nested directory structure
        level1 = self.temp_path / "level1"
        level1.mkdir()
        
        level2 = level1 / "level2"
        level2.mkdir()
        
        level3 = level2 / "level3"
        level3.mkdir()
        
        # Claude: create Python files at different levels
        (self.temp_path / "root.py").write_text("import os")
        (level1 / "level1.py").write_text("import sys")
        (level2 / "level2.py").write_text("import json")
        (level3 / "level3.py").write_text("import re")
        
        # Claude: test with max_depth=1 (should find root and level1)
        files_depth1 = list(find_python_files(
            self.temp_path, 
            recursive=True, 
            max_depth=1, 
            verbose=False
        ))
        self.assertEqual(len(files_depth1), 2)
        file_names = {f.name for f in files_depth1}
        self.assertEqual(file_names, {"root.py", "level1.py"})
        
        # Claude: test with max_depth=2 (should find root, level1, and level2)
        files_depth2 = list(find_python_files(
            self.temp_path, 
            recursive=True, 
            max_depth=2, 
            verbose=False
        ))
        self.assertEqual(len(files_depth2), 3)
        file_names = {f.name for f in files_depth2}
        self.assertEqual(file_names, {"root.py", "level1.py", "level2.py"})
    
    def test_max_files_limit(self):
        """Claude: test maximum files limit"""
        # Claude: create multiple Python files
        for i in range(5):
            file_path = self.temp_path / f"file_{i}.py"
            file_path.write_text(f"import os  # File {i}")
        
        # Claude: test with max_files=3
        files_limited = list(find_python_files(
            self.temp_path, 
            max_files=3, 
            verbose=False
        ))
        
        # Claude: should find exactly 3 files
        self.assertEqual(len(files_limited), 3)
    
    def test_validate_directory_path_success(self):
        """Claude: test successful directory path validation"""
        # Claude: create valid directory with files
        (self.temp_path / "test.py").write_text("import os")
        
        result = validate_directory_path(self.temp_path)
        
        # Claude: should return True for valid directory
        self.assertTrue(result)
    
    def test_validate_directory_path_not_directory(self):
        """Claude: test validate_directory_path with file instead of directory"""
        # Claude: create a file
        file_path = self.temp_path / "not_a_directory.py"
        file_path.write_text("import os")
        
        result = validate_directory_path(file_path)
        
        # Claude: should return False for file
        self.assertFalse(result)
    
    def test_validate_directory_path_permission_denied(self):
        """Claude: test validate_directory_path with permission issues"""
        # Claude: mock iterdir to raise PermissionError
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Permission denied")):
            result = validate_directory_path(self.temp_path)
        
        # Claude: should return False for permission errors
        self.assertFalse(result)
    
    def test_validate_directory_path_os_error(self):
        """Claude: test validate_directory_path with OS error"""
        # Claude: mock iterdir to raise OSError
        with patch.object(Path, 'iterdir', side_effect=OSError("OS error")):
            result = validate_directory_path(self.temp_path)
        
        # Claude: should return False for OS errors
        self.assertFalse(result)


# Claude: test class for edge cases in file validation
class TestFileValidationEdgeCases(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_symlink_handling(self):
        """Claude: test handling of symbolic links"""
        # Claude: create a Python file and a symlink to it
        original_file = self.temp_path / "original.py"
        original_file.write_text("import os")
        
        symlink_file = self.temp_path / "symlink.py"
        try:
            symlink_file.symlink_to(original_file)
            
            # Claude: find Python files
            python_files = list(find_python_files(self.temp_path, verbose=False))
            
            # Claude: should find both files (original and symlink)
            self.assertEqual(len(python_files), 2)
            file_names = {f.name for f in python_files}
            self.assertEqual(file_names, {"original.py", "symlink.py"})
            
        except OSError:
            # Claude: skip test if symlinks are not supported
            self.skipTest("Symlinks not supported on this system")
    
    def test_hidden_files(self):
        """Claude: test handling of hidden files"""
        # Claude: create hidden and non-hidden Python files
        (self.temp_path / "visible.py").write_text("import os")
        (self.temp_path / ".hidden.py").write_text("import sys")
        
        # Claude: find Python files
        python_files = list(find_python_files(self.temp_path, verbose=False))
        
        # Claude: should find both visible and hidden files
        self.assertEqual(len(python_files), 2)
        file_names = {f.name for f in python_files}
        self.assertEqual(file_names, {"visible.py", ".hidden.py"})
    
    def test_unicode_filenames(self):
        """Claude: test handling of unicode filenames"""
        # Claude: create files with unicode characters
        unicode_files = [
            ("café.py", "import os"),
            ("测试.py", "import sys"),
            ("файл.py", "import json")
        ]
        
        for filename, content in unicode_files:
            try:
                file_path = self.temp_path / filename
                file_path.write_text(content)
            except (OSError, UnicodeError):
                # Claude: skip files that can't be created on this system
                continue
        
        # Claude: find Python files
        python_files = list(find_python_files(self.temp_path, verbose=False))
        
        # Claude: should handle unicode filenames gracefully
        self.assertGreaterEqual(len(python_files), 1)
        
        # Claude: all found files should have .py extension
        for file_path in python_files:
            self.assertTrue(file_path.name.lower().endswith('.py'))


if __name__ == '__main__':
    unittest.main()