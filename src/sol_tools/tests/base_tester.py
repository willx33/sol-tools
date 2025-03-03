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
        Run a single test and return results.
        
        Args:
            test_name: Name of the test
            test_func: Function to run
            
        Returns:
            Dictionary containing test results
        """
        # Initialize test result
        result = {
            "name": test_name,
            "status": "running",
            "duration": 0,
            "start_time": time.time(),
            "message": None,
            "exception": None,
            "skipped_reason": None
        }
        
        # Check if any required environment variables are missing
        missing_env_vars = self.check_missing_env_vars(test_name)
        if missing_env_vars:
            # Skip test if environment variables are missing
            result.update({
                "status": "skipped",
                "skipped_reason": f"Missing environment variables: {', '.join(missing_env_vars)}",
                "end_time": time.time(),
                "duration": 0
            })
            self.skipped_tests += 1
            self.total_tests += 1
            
            # Display skip message
            print(f"{STATUS_INDICATORS['skipped']} {test_name}")
            print(f"     ⚠️  {result['skipped_reason']}")
            
            return result
        
        # Run the test
        self.total_tests += 1
        start_time = time.time()
        print(f"{STATUS_INDICATORS['running']} Running: {test_name}")
        
        try:
            # Call the test function
            test_result = await test_func()
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Handle different return types from test functions
            if test_result is None:
                # None result means the test was skipped
                status = "skipped"
                self.skipped_tests += 1
            elif isinstance(test_result, bool):
                # Boolean result indicates pass/fail
                if test_result:
                    status = "passed"
                    self.passed_tests += 1
                else:
                    status = "failed"
            else:
                # Any other result type is treated as a structured result
                # This allows tests to return more detailed information
                if isinstance(test_result, dict) and "status" in test_result:
                    status = test_result["status"]
                    if status == "passed":
                        self.passed_tests += 1
                    elif status == "skipped":
                        self.skipped_tests += 1
                else:
                    # Default to passed if the result is truthy
                    status = "passed" if test_result else "failed"
                    if status == "passed":
                        self.passed_tests += 1
            
            # Print test status
            if status == "passed":
                print(f"{STATUS_INDICATORS['passed']} {test_name} ({elapsed_time:.2f}s)")
            elif status == "skipped":
                print(f"{STATUS_INDICATORS['skipped']} {test_name}")
            else:
                print(f"{STATUS_INDICATORS['failed']} {test_name} ({elapsed_time:.2f}s)")
                
            # Return structured result
            if isinstance(test_result, dict) and "status" in test_result:
                # If the test returned a dict with status, merge it with our result
                result.update(test_result)
                # Make sure to update the status and duration
                result["status"] = status
                result["duration"] = elapsed_time
            else:
                # Otherwise just update the basic fields
                result.update({
                    "status": status,
                    "duration": elapsed_time,
                    "end_time": end_time
                })
            return result
            
        except Exception as e:
            # Handle exceptions during test execution
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            self.logger.error(f"Error in test {test_name}")
            self.logger.exception(str(e))
            
            print(f"{STATUS_INDICATORS['failed']} {test_name} ({elapsed_time:.2f}s)")
            print(f"     ❌ Error: {str(e)}")
            
            # Return structured result
            result.update({
                "status": "failed",
                "reason": str(e),
                "exception": str(e),
                "duration": elapsed_time,
                "end_time": end_time
            })
            return result
    
    def validate_data_structure(self, data: Any, schema: Dict, path: str = "") -> List[str]:
        """
        Validate data against a schema definition.
        
        This is a simple schema validator that checks:
        - Types are correct
        - Required fields are present
        - Nested structures match expectations
        
        Args:
            data: The data to validate
            schema: A dictionary mapping field names to expected types or nested schemas
            path: Current path for error reporting (used for nested validation)
            
        Returns:
            List of error messages (empty if validation passes)
        """
        errors = []
        
        # Handle None schema as accepting any value
        if schema is None:
            return errors
            
        # Check if data is of the correct type
        if isinstance(schema, type) or isinstance(schema, tuple):
            # Schema is a simple type check
            if not isinstance(data, schema):
                errors.append(f"{path}: Expected {schema}, got {type(data)}")
            return errors
            
        # Handle dict schema against dict data
        if isinstance(schema, dict):
            # First validate the data is a dict
            if not isinstance(data, dict):
                errors.append(f"{path}: Expected dict, got {type(data)}")
                return errors
                
            # Check required fields are present
            for key, value_schema in schema.items():
                # Skip optional fields (keys that start with ?)
                is_optional = False
                if key.startswith("?"):
                    clean_key = key[1:]
                    is_optional = True
                else:
                    clean_key = key
                
                # Check if required field is present
                if clean_key not in data:
                    if not is_optional:
                        errors.append(f"{path}.{clean_key}: Missing required field")
                    continue
                    
                # Validate field value (recursively for nested schemas)
                if isinstance(value_schema, dict):
                    # Nested schema validation
                    nested_errors = self.validate_data_structure(
                        data[clean_key], 
                        value_schema,
                        f"{path}.{clean_key}"
                    )
                    errors.extend(nested_errors)
                else:
                    # Simple type validation
                    if not isinstance(data[clean_key], value_schema):
                        errors.append(
                            f"{path}.{clean_key}: Expected {value_schema}, " +
                            f"got {type(data[clean_key])}"
                        )
        
        # Handle list schema against list data
        elif isinstance(schema, list) and len(schema) == 1:
            # Schema is a list with element type definition
            if not isinstance(data, list):
                errors.append(f"{path}: Expected list, got {type(data)}")
                return errors
                
            # Validate each list element
            element_schema = schema[0]
            for i, element in enumerate(data):
                element_errors = self.validate_data_structure(
                    element,
                    element_schema,
                    f"{path}[{i}]"
                )
                errors.extend(element_errors)
                
        return errors
    
    async def with_timeout(self, coro, timeout: int = 30, error_message: str = "Operation timed out"):
        """
        Run a coroutine with a timeout.
        
        Args:
            coro: The coroutine to run
            timeout: Timeout in seconds
            error_message: Message to include in the timeout exception
            
        Returns:
            The result of the coroutine
            
        Raises:
            TimeoutError: If the operation times out
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(error_message)
    
    def create_temp_file(self, content: str = "", extension: str = ".txt") -> Path:
        """
        Create a temporary file with the specified content.
        
        Args:
            content: Content to write to the file
            extension: File extension to use
            
        Returns:
            Path to the temporary file
        """
        fd, path = tempfile.mkstemp(suffix=extension, dir=self.test_root)
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(content)
        return Path(path)
    
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
        Discover environment variables required by each test method.
        
        This method inspects each test method for the presence of
        environment variable requirements in docstrings or function annotations.
        
        Returns:
            A dictionary mapping test names to lists of required environment variables
        """
        env_vars = {}
        
        # Get all test methods (starting with 'test_')
        for attr_name in dir(self):
            if attr_name.startswith('test_'):
                method = getattr(self, attr_name)
                
                # Skip if not callable
                if not callable(method):
                    continue
                
                # Initialize as empty list
                env_vars[attr_name] = []
                
                # Check for docstring with environment variable requirements
                if method.__doc__ and "requires:" in method.__doc__.lower():
                    doc_lines = method.__doc__.splitlines()
                    for line in doc_lines:
                        if "requires:" in line.lower():
                            # Extract environment variable names
                            _, requires_str = line.lower().split("requires:", 1)
                            required_vars = [
                                v.strip().upper() 
                                for v in requires_str.split(",")
                                if v.strip()
                            ]
                            env_vars[attr_name].extend(required_vars)
        
        return env_vars

    def check_env_vars(self, env_vars: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if all required environment variables are set.
        
        Args:
            env_vars: List of environment variable names to check
            
        Returns:
            Tuple of (all_present, missing_vars) where:
              - all_present is True if all variables are set
              - missing_vars is a list of missing variable names
        """
        missing = []
        valid = True
        
        for var in env_vars:
            if var not in os.environ or not os.environ[var]:
                missing.append(var)
                valid = False
                
        return valid, missing

    def check_missing_env_vars(self, test_name: str) -> List[str]:
        """
        Check if a specific test has missing environment variables.
        
        Args:
            test_name: The name of the test method to check
            
        Returns:
            List of missing environment variable names
        """
        # Get required environment variables for this test
        test_env_vars = self.test_env_vars.get(test_name, [])
        # Combine with module-level required env vars
        required_env_vars = list(set(test_env_vars + self.required_env_vars))
        
        # Check if all environment variables are set
        _, missing = self.check_env_vars(required_env_vars)
        return missing

    def create_env_var_doc(self) -> str:
        """
        Creates a documentation string for environment variables used by this tester.
        
        Returns:
            A formatted string describing required environment variables
        """
        all_env_vars = set(self.required_env_vars)
        
        # Add environment variables from individual tests
        for vars_list in self.test_env_vars.values():
            all_env_vars.update(vars_list)
            
        if not all_env_vars:
            return "No environment variables required"
            
        # Check which ones are set
        env_var_status = []
        for var in sorted(all_env_vars):
            if var in os.environ and os.environ[var]:
                env_var_status.append(f"✓ {var} (set)")
            elif var in os.environ:
                env_var_status.append(f"✓ {var} (present, but empty)")
            else:
                env_var_status.append(f"✗ {var} (not set)")
                
        return "Required environment variables:\n  " + "\n  ".join(env_var_status)
    
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