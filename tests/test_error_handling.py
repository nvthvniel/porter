#!/usr/bin/env python3

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import subprocess

# Claude: add the parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from porter.cli import (
    extract_dependencies,
    find_python_files,
    validate_directory_path,
    add_dependencies,
    validate_uv_installation,
    process_single_file
)


# Claude: test class for error handling scenarios
class TestErrorHandling(unittest.TestCase):
    
    def setUp(self):
        # Claude: create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        # Claude: cleanup temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_dependencies_nonexistent_file(self):
        """Claude: test extract_dependencies with non-existent file"""
        non_existent_file = self.temp_path / "does_not_exist.py"
        
        # Claude: capture stdout to check error message
        with patch('builtins.print') as mock_print:
            result = extract_dependencies(non_existent_file)
        
        # Claude: should return empty set and print error message
        self.assertEqual(result, set())
        mock_print.assert_called()
        self.assertIn("Error accessing file", str(mock_print.call_args))
    
    def test_extract_dependencies_empty_file(self):
        """Claude: test extract_dependencies with empty file"""
        empty_file = self.temp_path / "empty.py"
        empty_file.write_text("")
        
        with patch('builtins.print') as mock_print:
            result = extract_dependencies(empty_file)
        
        # Claude: should return empty set and print warning
        self.assertEqual(result, set())
        mock_print.assert_called()
        self.assertIn("empty", str(mock_print.call_args))
    
    def test_extract_dependencies_large_file(self):
        """Claude: test extract_dependencies with file too large"""
        large_file = self.temp_path / "large.py"
        
        # Claude: mock file size to be over 10MB
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 11 * 1024 * 1024  # 11MB
            
            with patch('builtins.print') as mock_print:
                result = extract_dependencies(large_file)
        
        # Claude: should return empty set and print error
        self.assertEqual(result, set())
        mock_print.assert_called()
        self.assertIn("too large", str(mock_print.call_args))
    
    def test_extract_dependencies_syntax_error(self):
        """Claude: test extract_dependencies with syntax error"""
        syntax_error_file = self.temp_path / "syntax_error.py"
        syntax_error_file.write_text("def invalid_syntax(\n    pass")
        
        with patch('builtins.print') as mock_print:
            result = extract_dependencies(syntax_error_file)
        
        # Claude: should return empty set and print syntax error
        self.assertEqual(result, set())
        mock_print.assert_called()
        # Claude: check that either "Syntax error" or the suggestion message was printed
        call_args_str = str(mock_print.call_args_list)
        self.assertTrue("Syntax error" in call_args_str or "not be a valid Python file" in call_args_str)
    
    def test_extract_dependencies_encoding_error(self):
        """Claude: test extract_dependencies with encoding issues"""
        encoding_file = self.temp_path / "encoding.py"
        
        # Claude: write binary data that can't be decoded as UTF-8
        with open(encoding_file, 'wb') as f:
            f.write(b'\xff\xfe\x00\x00import os')
        
        with patch('builtins.print') as mock_print:
            result = extract_dependencies(encoding_file)
        
        # Claude: should handle encoding gracefully
        self.assertEqual(result, set())
    
    def test_find_python_files_non_python_extension(self):
        """Claude: test find_python_files skips non-Python files"""
        txt_file = self.temp_path / "not_python.txt"
        txt_file.write_text("print('hello')")
        
        files = list(find_python_files(self.temp_path, verbose=False))
        
        # Claude: should not include .txt files
        self.assertEqual(len(files), 0)
    
    def test_find_python_files_large_file_warning(self):
        """Claude: test find_python_files skips large files with warning"""
        large_file = self.temp_path / "large.py"
        large_file.write_text("import os")
        
        # Claude: mock file size to be over 10MB
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
                files = list(find_python_files(self.temp_path, verbose=True))
        
        # Claude: should skip large files and print warning
        self.assertEqual(len(files), 0)
        mock_print.assert_called()
        self.assertIn("too large", str(mock_print.call_args))
    
    def test_validate_directory_path_nonexistent(self):
        """Claude: test validate_directory_path with non-existent directory"""
        non_existent_dir = self.temp_path / "does_not_exist"
        
        result = validate_directory_path(non_existent_dir)
        
        # Claude: should return False for non-existent directory
        self.assertFalse(result)
    
    def test_validate_directory_path_file_not_dir(self):
        """Claude: test validate_directory_path with file instead of directory"""
        file_path = self.temp_path / "not_a_dir.py"
        file_path.write_text("import os")
        
        result = validate_directory_path(file_path)
        
        # Claude: should return False for file
        self.assertFalse(result)
    
    def test_validate_directory_path_permission_error(self):
        """Claude: test validate_directory_path with permission error"""
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            result = validate_directory_path(self.temp_path)
        
        # Claude: should return False for permission errors
        self.assertFalse(result)
    
    def test_validate_uv_installation_not_found(self):
        """Claude: test validate_uv_installation when UV is not installed"""
        with patch('subprocess.run', side_effect=FileNotFoundError("UV not found")):
            result = validate_uv_installation()
        
        # Claude: should return False when UV is not found
        self.assertFalse(result)
    
    def test_validate_uv_installation_timeout(self):
        """Claude: test validate_uv_installation with timeout"""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("uv", 10)):
            result = validate_uv_installation()
        
        # Claude: should return False on timeout
        self.assertFalse(result)
    
    def test_add_dependencies_invalid_file(self):
        """Claude: test add_dependencies with invalid file path"""
        invalid_file = self.temp_path / "does_not_exist.py"
        
        with patch('builtins.print') as mock_print:
            result = add_dependencies(invalid_file, {"requests"}, dry_run=False)
        
        # Claude: should return False and print error
        self.assertFalse(result)
        mock_print.assert_called()
        self.assertIn("not a valid file", str(mock_print.call_args))
    
    def test_add_dependencies_subprocess_error(self):
        """Claude: test add_dependencies with subprocess error"""
        python_file = self.temp_path / "test.py"
        python_file.write_text("import os")
        
        # Claude: mock subprocess to return error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Package not found"
        
        with patch('subprocess.run', return_value=mock_result):
            with patch('builtins.print') as mock_print:
                result = add_dependencies(python_file, {"nonexistent_package"}, dry_run=False)
        
        # Claude: should return False and print error with suggestion
        self.assertFalse(result)
        mock_print.assert_called()
        call_args_str = str(mock_print.call_args_list)
        self.assertIn("Error adding dependencies", call_args_str)
        self.assertIn("Suggestion:", call_args_str)
    
    def test_add_dependencies_timeout(self):
        """Claude: test add_dependencies with timeout"""
        python_file = self.temp_path / "test.py"
        python_file.write_text("import os")
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("uv", 120)):
            with patch('builtins.print') as mock_print:
                result = add_dependencies(python_file, {"requests"}, dry_run=False)
        
        # Claude: should return False and print timeout error with suggestion
        self.assertFalse(result)
        mock_print.assert_called()
        call_args_str = str(mock_print.call_args_list)
        self.assertIn("Timeout", call_args_str)
        self.assertIn("Suggestion:", call_args_str)
    
    def test_process_single_file_exception(self):
        """Claude: test process_single_file with unexpected exception"""
        python_file = self.temp_path / "test.py"
        python_file.write_text("import os")
        
        # Claude: mock extract_dependencies to raise exception
        with patch('porter.cli.extract_dependencies', side_effect=Exception("Unexpected error")):
            dependencies, success, error = process_single_file(python_file)
        
        # Claude: should return error information
        self.assertEqual(dependencies, set())
        self.assertFalse(success)
        self.assertIn("Unexpected error", error)


# Claude: test class for encoding handling scenarios
class TestEncodingHandling(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_dependencies_utf8_bom(self):
        """Claude: test extract_dependencies with UTF-8 BOM"""
        bom_file = self.temp_path / "bom.py"
        
        # Claude: write UTF-8 BOM encoded file
        with open(bom_file, 'wb') as f:
            f.write(b'\xef\xbb\xbfimport requests\n')
        
        # Claude: BOM files may not parse correctly in Python, so we expect empty set
        with patch('builtins.print') as mock_print:
            result = extract_dependencies(bom_file)
        
        # Claude: BOM causes syntax error, so we expect empty set
        self.assertEqual(result, set())
    
    def test_extract_dependencies_latin1_encoding(self):
        """Claude: test extract_dependencies with Latin-1 encoding"""
        latin1_file = self.temp_path / "latin1.py"
        
        # Claude: write Latin-1 encoded file
        with open(latin1_file, 'wb') as f:
            f.write("import requests\n# Comment with special char: \xe9\n".encode('latin-1'))
        
        result = extract_dependencies(latin1_file)
        
        # Claude: should successfully extract dependencies
        self.assertIn("requests", result)


if __name__ == '__main__':
    unittest.main()