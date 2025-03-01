"""
Base tester class that provides common functionality for all module testers.
This class provides test utilities, logging, and common setup/teardown methods.
"""

import os
import sys
import time
import json
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable

# Color codes for test output
COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "blue": "\033[94m",
    "bold": "\033[1m",
    "end": "\033[0m"
}

def cprint(message: str, color: str = None) -> None:
    """Print colored text to the console."""
    if color and color in COLORS:
        print(f"{COLORS[color]}{message}{COLORS['end']}")
    else:
        print(message)


class BaseTester:
    """Base class for all module testers with common functionality."""
    
    def __init__(self, module_name: str):
        """
        Initialize the base tester.
        
        Args:
            module_name: Name of the module being tested
        """
        self.module_name = module_name
        
        # Set up logging
        self.logger = self._setup_logger()
        
        # Create a temporary test directory
        self.test_root = Path(tempfile.mkdtemp(prefix=f"{module_name}_test_"))
        
        # Create standard test directories
        self._create_test_directories()
        
        # Test results tracking
        self.test_results = {}
        self.passed_tests = 0
        self.total_tests = 0
        
        # Start time for performance tracking
        self.start_time = time.time()
        
        cprint(f"🔍 Initializing {self.module_name} tests in: {self.test_root}", "cyan")
    
    def _setup_logger(self) -> logging.Logger:
        """Set up a logger for the tester."""
        logger = logging.getLogger(f"{self.module_name}_tester")
        logger.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(ch)
        
        return logger
    
    def _create_test_directories(self) -> None:
        """Create the standard directory structure for tests."""
        # Create input and output data directories
        (self.test_root / "input-data").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data").mkdir(parents=True, exist_ok=True)
        
        # Module-specific directories can be created in the subclasses
    
    def run_test(self, test_name: str, test_func: Callable) -> bool:
        """
        Run a single test and record the result.
        
        Args:
            test_name: Name of the test
            test_func: Function that implements the test
            
        Returns:
            bool: True if the test passed, False otherwise
        """
        cprint(f"  ▶ Running test: {test_name}...", "blue")
        self.total_tests += 1
        
        try:
            result = test_func()
            if result:
                cprint(f"  ✅ Test {test_name} passed", "green")
                self.passed_tests += 1
                self.test_results[test_name] = True
                return True
            else:
                cprint(f"  ❌ Test {test_name} failed", "red")
                self.test_results[test_name] = False
                return False
                
        except Exception as e:
            cprint(f"  ❌ Test {test_name} failed with exception: {str(e)}", "red")
            self.logger.exception(f"Exception in test {test_name}")
            self.test_results[test_name] = False
            return False
    
    def run_tests(self, tests: List[Tuple[str, Callable]]) -> Dict[str, bool]:
        """
        Run a list of tests and return the results.
        
        Args:
            tests: List of (test_name, test_function) tuples
            
        Returns:
            Dict mapping test names to pass/fail status
        """
        cprint(f"\n📌 Running {self.module_name} tests...", "cyan")
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        self._print_summary()
        
        return self.test_results
    
    def _print_summary(self) -> None:
        """Print a summary of the test results."""
        duration = time.time() - self.start_time
        
        cprint(f"\n📊 {self.module_name} Test Results:", "bold")
        cprint(f"  Passed: {self.passed_tests}/{self.total_tests} tests", "bold")
        cprint(f"  Duration: {duration:.2f} seconds", "bold")
        
        if self.passed_tests == self.total_tests:
            cprint(f"  ✅ All {self.module_name} tests passed!", "green")
        else:
            failed = self.total_tests - self.passed_tests
            cprint(f"  ⚠️ {failed} {self.module_name} tests failed", "yellow")
            
            # List failed tests
            cprint("  Failed tests:", "red")
            for test_name, result in self.test_results.items():
                if not result:
                    cprint(f"    - {test_name}", "red")
    
    def cleanup(self) -> None:
        """Clean up the test directory after tests are complete."""
        try:
            import shutil
            shutil.rmtree(self.test_root)
            cprint(f"🧹 Cleaned up test directory: {self.test_root}", "cyan")
        except Exception as e:
            self.logger.warning(f"Failed to clean up test directory: {str(e)}")
    
    def mock_file(self, file_path: str, content: Any, is_json: bool = False) -> Path:
        """
        Create a mock file with the given content.
        
        Args:
            file_path: Relative path to the file within the test directory
            content: Content to write to the file
            is_json: If True, encode content as JSON
            
        Returns:
            Path to the created file
        """
        full_path = self.test_root / file_path
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        mode = "w"  # Default text mode
        
        if is_json:
            with open(full_path, mode) as f:
                json.dump(content, f, indent=2)
        else:
            if isinstance(content, bytes):
                mode = "wb"  # Binary mode
                with open(full_path, mode) as f:
                    f.write(content)
            else:
                with open(full_path, mode) as f:
                    f.write(str(content))
        
        return full_path
    
    def read_mock_file(self, file_path: str, as_json: bool = False) -> Any:
        """
        Read a mock file from the test directory.
        
        Args:
            file_path: Relative path to the file within the test directory
            as_json: If True, decode content as JSON
            
        Returns:
            File content
        """
        full_path = self.test_root / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Mock file not found: {file_path}")
        
        if as_json:
            with open(full_path, "r") as f:
                return json.load(f)
        else:
            with open(full_path, "r") as f:
                return f.read() 