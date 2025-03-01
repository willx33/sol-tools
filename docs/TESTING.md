# Sol Tools Testing Framework

This document describes the comprehensive testing framework for Sol Tools and how to extend it for new modules.

## Overview

The Sol Tools testing framework is designed to:

1. Enable full testing without external API dependencies
2. Support modular testing of individual components
3. Facilitate integration testing between modules
4. Provide realistic mock data for testing
5. Clean up after itself to prevent test pollution

## Running Tests

### Running All Tests

```bash
# Run all tests through the CLI
sol-tools --test

# Or directly using the Python module
python -m src.sol_tools.cli --test
```

### Running Individual Tests

For development purposes, you can run individual test modules:

```bash
# Run just the file operations tests
python -m src.sol_tools.tests.test_core.test_file_ops

# Run just the Dragon module tests
python -m src.sol_tools.tests.test_modules.test_dragon

# Run just the Solana module tests
python -m src.sol_tools.tests.test_modules.test_solana

# Run just the workflow integration tests
python -m src.sol_tools.tests.test_integration.test_workflows
```

## Test Framework Structure

The testing framework is organized into several components:

```
src/sol_tools/tests/
├── base_tester.py            # Base testing class with common functionality
├── test_data/
│   └── mock_data.py          # Mock data generators
├── test_core/
│   └── test_file_ops.py      # Tests for core functionality
├── test_modules/
│   ├── test_dragon.py        # Tests for Dragon module
│   ├── test_solana.py        # Tests for Solana module
│   ├── test_dune.py          # Tests for Dune module
│   └── test_sharp.py         # Tests for Sharp module
├── test_integration/
│   └── test_workflows.py     # Tests for cross-module workflows
└── test_runner.py            # Central test runner
```

## Adding Test Mode to New Modules

When creating new modules, follow these guidelines to ensure they work with the testing framework:

### 1. Add test_mode to Adapter Classes

All adapter classes should accept a `test_mode` parameter that enables mock functionality:

```python
class YourModuleAdapter:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        
        # Initialize differently based on test_mode
        if self.test_mode:
            self._setup_test_data()
        else:
            # Real initialization code
            pass
```

### 2. Implement Mock Data and APIs

Create mock implementations of all API calls and data structures:

```python
def _setup_test_data(self):
    """Set up mock data for testing"""
    from ...tests.test_data.mock_data import generate_your_mock_data
    
    # Initialize mock data
    self.mock_data = generate_your_mock_data()
```

### 3. Conditional API Calls

All methods that make external API calls should have conditional logic:

```python
def fetch_data(self, parameter):
    if self.test_mode:
        # Return mock data
        return self.mock_data.get(parameter, {})
    else:
        # Make real API call
        return self._make_api_request(parameter)
```

### 4. Creating a Test Module

Create a test module for your new component:

1. Create a new file at `src/sol_tools/tests/test_modules/test_your_module.py`
2. Implement a class that extends `BaseTester`
3. Add test methods for each functionality
4. Add a `run_your_module_tests()` function

Example:

```python
from ...tests.base_tester import BaseTester, cprint

class YourModuleTester(BaseTester):
    def __init__(self):
        super().__init__("YourModule")
        
        # Create test directories
        self._create_test_directories()
        
        # Create test data
        self._create_test_data()
        
        # Initialize module with test_mode=True
        self._init_module()
    
    # ... implement test methods ...
    
    def run_tests(self):
        tests = [
            ("Module Import Test", self.test_module_imports),
            ("Functionality Test", self.test_functionality)
        ]
        
        return super().run_tests(tests)

def run_your_module_tests():
    tester = YourModuleTester()
    try:
        results = tester.run_tests()
        return all(results.values())
    finally:
        tester.cleanup()
```

### 5. Update the Test Runner

Finally, update the central test runner to include your module:

1. Import your test module in `test_runner.py`
2. Add it to the test groups

```python
try:
    from .test_modules.test_your_module import run_your_module_tests
    YOUR_MODULE_AVAILABLE = True
except ImportError:
    YOUR_MODULE_AVAILABLE = False

# Add to test_groups list
if YOUR_MODULE_AVAILABLE:
    test_groups.append({
        "name": "Your Module", 
        "run": run_your_module_tests, 
        "required": False  # Set to True when stable
    })
```

## Mock Data

The framework includes generated mock data for testing. To add new mock data generators:

1. Add your generator function to `mock_data.py`
2. Follow the naming convention `generate_mock_your_data()`
3. Document the function's purpose and return format

Example:

```python
def generate_mock_your_data() -> Dict[str, Any]:
    """Generate mock data for YourModule testing."""
    return {
        "field1": random_value(),
        "field2": [random_item() for _ in range(5)],
        "timestamp": int(time.time())
    }
```

## Best Practices

1. **Isolation**: Tests should not depend on external services or previous test state
2. **Cleanup**: Always clean up any files or resources created during tests
3. **Comprehensive**: Test both success and failure paths
4. **Speed**: Tests should run quickly (minimize sleeps, use mock data)
5. **Clarity**: Test names should clearly indicate what's being tested
6. **Coverage**: Aim to test all public APIs and important internal functionality

## Future Extensions

The testing framework is designed to be extended. Some areas for future work:

1. Add test coverage metrics
2. Create benchmark tests for performance-critical components
3. Add model-based testing for complex state machines
4. Implement snapshot testing for complex data structures
5. Add UI testing for any web or GUI components 