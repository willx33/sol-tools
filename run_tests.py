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

# Import the test runner
from src.sol_tools.tests.test_runner import main as run_tests

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    parser = argparse.ArgumentParser(description="Run Sol Tools tests")
    
    # Run the tests
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code) 