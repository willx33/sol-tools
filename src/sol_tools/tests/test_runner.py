"""
Test runner script for Sol Tools modules.

This script provides a simple way to run tests for specific modules.
Usage:
    python -m src.sol_tools.tests.test_runner [module_name]

Available modules:
    - dragon: Tests the Dragon and GMGN adapters
    - all: Runs all available tests
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_runner")

# Add parent directory to path if running directly
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


async def run_dragon_tests():
    """Run Dragon module tests."""
    try:
        from src.sol_tools.tests.test_dragon_modules import main as dragon_main
        return await dragon_main()
    except Exception as e:
        logger.error(f"Error running Dragon tests: {e}")
        return 1


async def run_all_tests():
    """Run all available tests."""
    results = []
    
    # Run Dragon tests
    logger.info("Running Dragon tests...")
    dragon_result = await run_dragon_tests()
    results.append(("Dragon", dragon_result))
    
    # Add more test modules here as they become available
    
    # Report results
    logger.info("\n" + "="*60)
    logger.info("Overall Test Results:")
    for module, result in results:
        status = "PASSED" if result == 0 else "FAILED"
        logger.info(f"{module}: {status}")
    logger.info("="*60)
    
    # Return success only if all tests passed
    return 0 if all(r == 0 for _, r in results) else 1


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Sol Tools module tests")
    parser.add_argument("module", nargs="?", default="all", 
                        choices=["dragon", "all"],
                        help="Module to test (default: all)")
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_args()
    
    if args.module == "dragon":
        logger.info("Running Dragon tests...")
        return await run_dragon_tests()
    else:
        logger.info("Running all tests...")
        return await run_all_tests()


if __name__ == "__main__":
    # Run the async main function
    if sys.version_info >= (3, 7):
        result = asyncio.run(main())
    else:
        # Fallback for Python 3.6
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(main())
    
    sys.exit(result) 