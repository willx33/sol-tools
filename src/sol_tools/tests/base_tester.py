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
import inspect
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable, Set, Mapping

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

# Test status indicators
STATUS_INDICATORS = {
    "passed": "🟢",  # Green dot
    "skipped": "🟡",  # Yellow dot
    "failed": "🔴",   # Red dot
    "running": "🔄"   # Running indicator
}

def cprint(message: str, color: Optional[str] = None) -> None:
    """Print colored text to the console."""
    if color and color in COLORS:
        print(f"{COLORS[color]}{message}{COLORS['end']}")
    else:
        print(message)


class BaseTester:
    """Base class for all module testers with common functionality."""
    
    def __init__(self, module_name: str, submodule_name: Optional[str] = None):
        """
        Initialize the base tester.
        
        Args:
            module_name: Name of the module being tested
            submodule_name: Optional name of the submodule being tested
        """
        self.module_name = module_name
        self.submodule_name = submodule_name
        self.full_name = f"{module_name}{f' > {submodule_name}' if submodule_name else ''}"
        
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
        self.skipped_tests = 0
        
        # Required environment variables for this module
        # Subclasses should override this with a list of required env vars
        self.required_env_vars = []
        
        # Environment variables required by specific tests
        # This will be populated during test discovery
        self.test_env_vars = {}
        
        # Start time for performance tracking
        self.start_time = time.time()
        
        cprint(f"🔍 Initializing {self.full_name} tests in: {self.test_root}", "cyan")
    
    def _setup_logger(self) -> logging.Logger:
        """Set up and configure logger."""
        logger_name = f"{self.module_name.lower()}_tester"
        if self.submodule_name:
            logger_name += f"_{self.submodule_name.lower()}"
            
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
        return logger
    
    def _create_test_directories(self) -> None:
        """Create standard test directories."""
        (self.test_root / "input-data").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data").mkdir(parents=True, exist_ok=True)
    
    async def run_test(self, test_name: str, test_func: Callable) -> Dict[str, Any]:
        """
        Run a single test function and return the result.
        
        Args:
            test_name: Name of the test
            test_func: Function to run for the test
            
        Returns:
            Dictionary with test result information
        """
        self.total_tests += 1
        
        # Check if this test has required env vars
        required_vars = self.test_env_vars.get(test_name, [])
        missing_vars = []
        
        # Check which env vars are missing
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        # Skip the test if any required env vars are missing
        if missing_vars:
            self.skipped_tests += 1
            print(f"{STATUS_INDICATORS['skipped']} {test_name}")
            print(f"     ⚠️  Missing environment variables: {', '.join(missing_vars)}")
            return {
                "name": test_name,
                "status": "skipped",
                "required_env_vars": missing_vars,
                "missing_env_vars": missing_vars
            }
        
        # Run the test
        print(f"{STATUS_INDICATORS['running']} Running: {test_name}")
        
        try:
            start_time = time.time()
            # Handle both async and non-async test functions
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            elapsed_time = time.time() - start_time
            
            # Handle None return value as a skip (added for Dragon module tests)
            if result is None:
                self.skipped_tests += 1
                print(f"{STATUS_INDICATORS['skipped']} {test_name} ({elapsed_time:.2f}s)")
                status = "skipped"
            elif result:
                self.passed_tests += 1
                print(f"{STATUS_INDICATORS['passed']} {test_name} ({elapsed_time:.2f}s)")
                status = "passed"
            else:
                print(f"{STATUS_INDICATORS['failed']} {test_name} ({elapsed_time:.2f}s)")
                status = "failed"
                
            # Return structured result
            return {
                "name": test_name,
                "status": status,
                "elapsed_time": elapsed_time
            }
            
        except Exception as e:
            print(f"{STATUS_INDICATORS['failed']} {test_name}")
            print(f"     ❌ Error: {str(e)}")
            self.logger.exception(f"Error in test {test_name}")
            
            # Return structured result
            return {
                "name": test_name,
                "status": "failed",
                "reason": str(e)
            }
    
    async def run_tests(self, tests: List[Tuple[str, Callable]]) -> Dict[str, Dict[str, Any]]:
        """
        Run multiple tests and return the results.
        
        Args:
            tests: List of tuples with test names and functions
            
        Returns:
            Dictionary with test results
        """
        results = {}
        
        for test_name, test_func in tests:
            result = await self.run_test(test_name, test_func)
            results[test_name] = result
        
        # Print module/submodule level summary
        overall_status = self._get_overall_status()
        print(f"\n{STATUS_INDICATORS[overall_status]} {self.full_name} Summary: {self.passed_tests}/{self.total_tests} tests passed, {self.skipped_tests} skipped")
        
        return results
    
    def _get_overall_status(self) -> str:
        """Get the overall status of all tests."""
        if self.total_tests == self.skipped_tests:
            return "skipped"
        elif self.passed_tests + self.skipped_tests == self.total_tests:
            return "passed"
        else:
            return "failed"
    
    def cleanup(self) -> None:
        """Clean up test resources."""
        import shutil
        try:
            # Don't delete the test directory when debugging
            if not os.environ.get("DEBUG_TESTS"):
                shutil.rmtree(self.test_root)
        except Exception as e:
            self.logger.warning(f"Error cleaning up test directory: {e}")
    
    def mock_file(self, file_path: str, content: Any, is_json: bool = False) -> Path:
        """
        Create a test file with content in the test directory.
        
        Args:
            file_path: Path to the file relative to the test root
            content: Content to write to the file
            is_json: Whether to convert content to JSON
            
        Returns:
            Path to the created file
        """
        full_path = self.test_root / file_path
        
        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to the file
        with open(full_path, "w") as f:
            if is_json:
                json.dump(content, f, indent=2)
            else:
                f.write(str(content))
                
        return full_path
    
    def read_file(self, file_path: str, as_json: bool = False) -> Any:
        """
        Read content from a test file.
        
        Args:
            file_path: Path to the file relative to the test root
            as_json: Whether to parse the content as JSON
            
        Returns:
            Content of the file
        """
        full_path = self.test_root / file_path
        
        try:
            with open(full_path, "r") as f:
                if as_json:
                    return json.load(f)
                return f.read()
        except FileNotFoundError:
            self.logger.warning(f"Test file not found: {file_path}")
            return None
    
    def discover_test_env_vars(self) -> Dict[str, List[str]]:
        """
        Discover required environment variables for each test method.
        
        This method inspects all test methods (starting with test_) and looks for
        docstring annotations specifying required environment variables.
        
        Format: @requires_env: ENV_VAR1, ENV_VAR2
        
        Returns:
            Dictionary mapping test names to lists of required env vars
        """
        env_vars = {}
        
        # Get all methods starting with "test_"
        test_methods = inspect.getmembers(
            self, 
            predicate=lambda x: inspect.ismethod(x) and x.__name__.startswith("test_")
        )
        
        for name, method in test_methods:
            # Get the docstring
            docstring = inspect.getdoc(method)
            if not docstring:
                continue
                
            # Look for the @requires_env annotation
            for line in docstring.splitlines():
                if line.strip().startswith("@requires_env:"):
                    # Extract the environment variables
                    vars_part = line.split("@requires_env:", 1)[1].strip()
                    required_vars = [v.strip() for v in vars_part.split(",")]
                    env_vars[name] = required_vars
                    break
        
        # Store the discovered env vars
        self.test_env_vars = env_vars
        return env_vars
    
    async def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all tests with environment variable checks.
        
        This method:
        1. Discovers all test methods and their required env vars
        2. Checks which env vars are available
        3. Runs tests that can run given the available env vars
        4. Skips tests that require missing env vars
        
        Returns:
            Dictionary with test results and summary information
        """
        # Discover tests and their env var requirements
        self.discover_test_env_vars()
        
        # Get all test methods
        test_methods = [
            (name, method) 
            for name, method in inspect.getmembers(
                self, 
                predicate=lambda x: inspect.ismethod(x) and x.__name__.startswith("test_")
            )
        ]
        
        # Sort tests by name for consistent ordering
        test_methods.sort(key=lambda x: x[0])
        
        # Run the tests
        results = {}
        
        for name, method in test_methods:
            # Run the test and get the result
            result = await self.run_test(name, method)
            results[name] = result
        
        # Print summary at the module level
        overall_status = self._get_overall_status()
        print(f"\n{STATUS_INDICATORS[overall_status]} {self.full_name} Summary: {self.passed_tests}/{self.total_tests} tests passed, {self.skipped_tests} skipped")
        
        # Return the results
        return results 