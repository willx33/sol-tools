# Sol Tools Testing Framework

[← Back to Main Documentation](../../../README.md)

This directory contains the comprehensive testing framework for the Sol Tools project. The testing system is designed with a focus on clean, minimal output that uses emoji indicators rather than verbose logging.

## Testing Philosophy

Our testing approach follows these core principles:

1. **Minimal Output**: Tests should provide clear indicators of success/failure without verbose logs.
2. **Emoji Indicators**: We use emoji symbols (✅ 🔄 🔴 etc.) to indicate test status for easy visual scanning.
3. **Organized Structure**: Tests are organized by module following the same structure as the CLI menu.
4. **Environment Detection**: Tests automatically detect required environment variables and skip tests that can't run.
5. **Condensed Files**: We avoid one-off test files, instead integrating tests into our structured suite.

## Directory Structure

- `test_modules/` - Tests for each functional module (Dragon, GMGN, Solana, etc.)
- `test_core/` - Tests for core framework components
- `test_integration/` - Tests that verify interactions between modules
- `test_data/` - Shared test data used across all tests

## Test Runner

The central component of our testing framework is `test_runner.py`, which provides:

- Organized test execution by module
- Automatic environment variable validation
- Consistent status reporting
- Summary outputs that match our CLI menu structure

Example usage:
```bash
# Run all tests
python -m src.sol_tools.tests.test_runner

# Run tests for a specific module
python -m src.sol_tools.tests.test_runner --module gmgn
```

## Base Tester

The `base_tester.py` file provides the `BaseTester` class that all module-specific test classes inherit from. It handles:

- Test discovery and execution
- Environment variable requirements
- Test setup and teardown
- Consistent test reporting format

## Test Output Style

We strongly prefer minimal test output that uses emoji indicators:

- ✅ or 🟢 - Test passed
- 🔄 - Test running/skipped
- 🔴 - Test failed

Example of ideal test output:
```
🔄 Running: test_market_cap_fetch
🧪 Testing market cap data fetch...
  ✅ Successfully fetched 259201 candles
🟢 test_market_cap_fetch (1.76s)
```

## Adding New Tests

When adding new tests:

1. Identify the appropriate module directory
2. Add tests to the existing test file or create a new one following the same pattern
3. Ensure your test class inherits from `BaseTester`
4. Use minimal logging and emoji indicators for status
5. Document environment variable requirements using the `@requires_env` decorator

## Module-Specific Documentation

- [Core Tests](./test_core/README.md) - Tests for framework internals
- [Module Tests](./test_modules/README.md) - Tests for functional modules
- [Integration Tests](./test_integration/README.md) - Cross-module tests 