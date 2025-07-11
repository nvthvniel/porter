#!/usr/bin/env python3

import unittest
import sys
from pathlib import Path

# Claude: script to run all tests

def main():
    """Claude: discover and run all tests"""
    # Claude: add the current directory to the path for imports
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Claude: discover all tests in the tests directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Claude: run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Claude: exit with error code if tests failed
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    main()