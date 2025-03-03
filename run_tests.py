#!/usr/bin/env python3
"""
Test runner script for Sol Tools.

This script provides a simple way to run tests for specific modules.
Usage:
    python run_tests.py [module_name] [options]

Available modules:
    - dragon: Tests the Dragon and GMGN adapters
    - solana: Tests the Solana module
    - ethereum: Tests the Ethereum module
    - dune: Tests the Dune module
    - sharp: Tests the Sharp module
    - gmgn: Tests the GMGN module
    - csv: Tests the CSV module
    - core: Tests the core framework
    - integration: Tests integration between modules
    - all: Runs all available tests
    
Options:
    --verbose: Show detailed test output
    --quick: Run only quick tests (skip time-consuming ones)
    --mock-only: Only run tests with mock data (no API calls)
    --live: Run tests with real API calls (requires API keys)
    --no-mock: Force disable test_mode even in tests (use real implementations)
"""

import sys
import asyncio
import logging
import argparse
import os

# Import the test runner
from src.sol_tools.tests.test_runner import run_all_tests

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    parser = argparse.ArgumentParser(description="Run Sol Tools tests")
    parser.add_argument("module", default="all", nargs="?", help="Module to test (default: all)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed test output")
    parser.add_argument("--quick", action="store_true", help="Run only quick tests")
    parser.add_argument("--mock-only", action="store_true", help="Only run tests with mock data")
    parser.add_argument("--live", action="store_true", help="Run tests with real API calls")
    parser.add_argument("--no-mock", action="store_true", help="Disable test mode even in tests")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Set debug environment variable if specified
    if args.debug:
        os.environ["DEBUG_TESTS"] = "1"
    
    # Run the tests
    try:
        exit_code = asyncio.run(run_all_tests(args.module))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest run interrupted by user.")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        print(f"\nError running tests: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1) 