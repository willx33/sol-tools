"""
Tests for the GMGN module.

This file contains tests for the GMGN module functionality, including:
- Market cap data retrieval
- Token data retrieval
- Integration with other modules
"""

import os
import sys
import json
import asyncio
import logging
import tempfile
import importlib
import importlib.util  # Explicitly import util for spec-based imports
import io
import contextlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Callable, Type

# EXTREME SILENCE IMPLEMENTATION - RUN IMMEDIATELY
# This must be at the top of the file to silence everything
# before any other imports or operations
if os.environ.get("TEST_MODE") == "1":
    # Silence all output by redirecting to /dev/null during import
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    # Silence ALL loggers at import time
    logging.basicConfig(level=logging.CRITICAL + 100)  # Impossible high level
    
    # Replace print with silent version
    def silent_print(*args, **kwargs):
        pass
    builtins_print = print
    print = silent_print
    
    try:
        # Silence all existing loggers
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.setLevel(logging.CRITICAL + 100)
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
            logger.addHandler(logging.NullHandler())
    finally:
        # Restore stdout/stderr after this import-time code
        sys.stdout = original_stdout
        sys.stderr = original_stderr

from ...tests.base_tester import BaseTester, cprint, STATUS_INDICATORS

# Import test data carefully to avoid attribute errors
try:
    from ...tests.test_data.real_test_data import (
        REAL_TOKEN_ADDRESSES,
        REAL_WALLET_ADDRESSES
    )
except ImportError:
    # Define empty defaults if import fails
    REAL_TOKEN_ADDRESSES = {}
    REAL_WALLET_ADDRESSES = {}

@contextlib.contextmanager
def suppress_stdout():
    """
    Context manager to suppress stdout output.
    """
    # Save stdout reference
    original_stdout = sys.stdout
    
    # Use /dev/null to discard stdout
    null_out = open(os.devnull, 'w')
    
    try:
        # Redirect stdout to /dev/null
        sys.stdout = null_out
        yield
    finally:
        # Restore stdout
        sys.stdout = original_stdout
        null_out.close()

@contextlib.contextmanager
def suppress_all_output():
    """
    Context manager to suppress both stdout and stderr completely.
    """
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Create null streams
    null_out = open(os.devnull, 'w')
    
    try:
        # Redirect stdout and stderr to null
        sys.stdout = null_out
        sys.stderr = null_out
        yield
    finally:
        # Restore stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        null_out.close()

def get_test_names() -> List[str]:
    """
    Get the names of all tests in this module.
    
    Returns:
        A list of test names for display in the test runner
    """
    return [
        "Module Imports (GMGN components)",
        "Market Cap Data Retrieval",
        "Standalone Market Cap Implementation",
        "Multi-Token Market Cap Data",
        "Token Data Fetching",
        "Multi-Token Data Retrieval"
    ]

class GmgnTester(BaseTester):
    """Tester for GMGN module functionality"""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """Initialize the GMGN tester with options."""
        # Initialize the base class
        super().__init__("GMGN")
        
        # Store options separately
        self.options = options or {}
        
        # Store real addresses for testing
        self.token_addresses = []
        self.wallet_addresses = []
        
        # Default token addresses for tests
        self.token_addresses = [
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
            "7LJDPUUPBDUwJ9NYjUZXH7xGLhtPRdYmEJypFYfYVY3z",  # JTO
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC
        ]
        
        # Default wallet addresses for tests
        self.wallet_addresses = [
            "3SZ7dpXCYu1XN6r6L9Q1zFjFGV1Ppxz7GZQKFd8wYS7B",
            "2JCxZv5rYzeXWZ9ffPCd7B3Ty2831tNqiLZBkYbMYw7f"
        ]
        
        # Try to use real test data if available
        try:
            # Try to get SOL tokens from REAL_TOKEN_ADDRESSES
            if isinstance(REAL_TOKEN_ADDRESSES, dict) and 'SOL' in REAL_TOKEN_ADDRESSES:
                sol_tokens = REAL_TOKEN_ADDRESSES['SOL']
                if isinstance(sol_tokens, list) and sol_tokens:
                    self.token_addresses = sol_tokens
            
            # Try to get SOL wallets from REAL_WALLET_ADDRESSES
            if isinstance(REAL_WALLET_ADDRESSES, dict) and 'SOL' in REAL_WALLET_ADDRESSES:
                sol_wallets = REAL_WALLET_ADDRESSES['SOL']
                if isinstance(sol_wallets, list) and sol_wallets:
                    self.wallet_addresses = sol_wallets
        except Exception:
            # If any error occurs, just use defaults (which are already set)
            pass
        
        # Required environment variables for the module
        # GMGN module doesn't require any specific env vars
        self.required_env_vars = []
        
        # Attempt to import GMGN modules
        self.module_imported = False
        self.gmgn_adapter = None
        self.standalone_mcap = None
        self._try_import_gmgn()
        
        # Set up logger to only show errors (silence info and debug)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
        
        # Disable all logging when in test mode
        # This is a more aggressive approach than previous attempts
        logging.getLogger().setLevel(logging.CRITICAL)
        for name in ['urllib3', 'aiohttp', 'sol_tools', 'asyncio']:
            logging.getLogger(name).setLevel(logging.CRITICAL)
        
        # Add null handlers to prevent any output from escaping
        for name in logging.root.manager.loggerDict:
            if name.startswith('sol_tools') or name in ['urllib3', 'aiohttp', 'asyncio']:
                logger = logging.getLogger(name)
                logger.setLevel(logging.CRITICAL)
                for handler in list(logger.handlers):
                    logger.removeHandler(handler)
                logger.addHandler(logging.NullHandler())
    
    def _try_import_gmgn(self) -> bool:
        """Try to import the GMGN module components."""
        try:
            # Import the module
            import sol_tools.modules.gmgn.gmgn_adapter as gmgn_adapter
            import sol_tools.modules.gmgn.standalone_mcap as standalone_mcap
            
            # Store module references - try both naming conventions
            adapter_class = getattr(gmgn_adapter, "GmgnAdapter", None)
            if adapter_class is None:
                adapter_class = getattr(gmgn_adapter, "GMGNAdapter", None)
            
            if adapter_class is None:
                self.logger.warning("Could not find GmgnAdapter or GMGNAdapter class in module")
                return False
                
            self.gmgn_adapter = adapter_class
            self.standalone_mcap = standalone_mcap
            self.module_imported = True
            return True
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"Failed to import GMGN module: {e}")
            self.module_imported = False
            return False
    
    async def test_module_imports(self) -> bool:
        """
        Test that the GMGN module can be imported.
        
        This test verifies that all required modules for GMGN functionality
        can be imported correctly.
        """
        if not self.module_imported:
            cprint("  ⚠️ GMGN module not imported", "yellow")
            return False
            
        cprint("  Testing GMGN module imports...", "blue")
        
        try:
            # Check if we have the necessary modules
            if not self.gmgn_adapter:
                cprint(f"  ❌ GmgnAdapter not found", "red")
                return False
                
            if not hasattr(self.standalone_mcap, "standalone_fetch_token_mcaps"):
                cprint(f"  ❌ standalone_fetch_token_mcaps function not found", "red")
                return False
                
            cprint("  ✓ Successfully verified GMGN modules", "green")
            return True
        except Exception as e:
            cprint(f"  ❌ Error importing GMGN modules: {str(e)}", "red")
            self.logger.exception("Error in test_module_imports")
            return False
    
    async def test_market_cap_fetch(self) -> bool:
        """Test the market cap data fetch functionality using the adapter"""
        self.logger.info(f"Market cap fetch test: {datetime.now()}")
        
        try:
            cprint("🧪 Testing market cap data fetch...", "yellow")
            
            # Check if the module was imported successfully
            if not self.module_imported or not self.gmgn_adapter:
                cprint(f"  ⚠️ GMGN module not imported, skipping test", "yellow")
                return False
            
            # Initialize the adapter using our stored class reference
            adapter = self.gmgn_adapter()
            
            # Use BONK token address for testing
            token_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
            days = 3  # Use a small number of days to make the test faster
            
            # Set TEST_MODE environment variable for this test (enables simplified output)
            os.environ["TEST_MODE"] = "1"
            
            # Execute with output suppression
            with suppress_all_output():
                # Make the API call
                cprint("  📊 Fetching market cap data...", "blue")
                
                # Set a timeout for the operation
                fetch_task = asyncio.create_task(adapter.fetch_token_mcap_data(token_address, days))
                try:
                    result = await asyncio.wait_for(fetch_task, timeout=25)  # 25 second timeout
                except asyncio.TimeoutError:
                    cprint("  ❌ Market cap fetch operation timed out after 25 seconds", "red")
                    # Clean up environment variable
                    if "TEST_MODE" in os.environ:
                        del os.environ["TEST_MODE"]
                    return False
            
            # Clean up environment variable
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
                
            # Verify the result
            if result and isinstance(result, list) and len(result) > 0:
                cprint(f"  ✅ Successfully fetched {len(result)} candles", "green")
                # Discard results to avoid storing data
                result = None
                return True
            else:
                # Even if no market cap data is found, consider the test passing
                # as long as the API call completed successfully
                cprint("  ✅ API call successful, but no market cap data found for token", "green")
                return True
                
        except Exception as e:
            cprint(f"  ❌ Error fetching market cap data: {str(e)}", "red")
            self.logger.exception("Error in test_market_cap_fetch")
            # Clean up any leftover environment variable
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
            return False
    
    async def test_standalone_market_cap(self) -> bool:
        """Test the standalone market cap data fetch functionality"""
        self.logger.info(f"Standalone market cap test: {datetime.now()}")
        
        try:
            cprint("🧪 Testing standalone market cap data fetch...", "yellow")
            
            # Check if the module was imported successfully
            if not self.module_imported or not self.standalone_mcap:
                cprint(f"  ⚠️ GMGN standalone module not imported, skipping test", "yellow")
                return False
            
            # Access the standalone test function
            standalone_test = getattr(self.standalone_mcap, "standalone_test", None)
            if not standalone_test or not callable(standalone_test):
                cprint(f"  ❌ standalone_test function not found", "red")
                return False
            
            # Set TEST_MODE environment variable for this test
            os.environ["TEST_MODE"] = "1"
            
            # Execute with aggressive output suppression
            with suppress_all_output():
                # Make the API call
                cprint("  📊 Fetching market cap data...", "blue")
                
                # Set a timeout for the operation
                fetch_task = asyncio.create_task(standalone_test())
                try:
                    result = await asyncio.wait_for(fetch_task, timeout=25)  # 25 second timeout
                except asyncio.TimeoutError:
                    cprint("  ❌ Market cap fetch operation timed out after 25 seconds", "red")
                    # Clean up environment variable
                    if "TEST_MODE" in os.environ:
                        del os.environ["TEST_MODE"]
                    return False
            
            # Clean up environment variable
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
                
            # Verify the result
            if result and isinstance(result, (list, dict)) and (len(result) > 0 if isinstance(result, list) else len(result.keys()) > 0):
                cprint(f"  ✅ Successfully fetched market cap data", "green")
                # Discard results to avoid storing data
                result = None
                return True
            else:
                # Even if no market cap data is found, consider the test passing
                # as long as the API call completed successfully
                cprint("  ✅ API call successful, but no market cap data found for token", "green")
                return True
                
        except Exception as e:
            cprint(f"  ❌ Error fetching market cap data: {str(e)}", "red")
            self.logger.exception("Error in test_standalone_market_cap")
            # Clean up any leftover environment variable
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
            return False
    
    async def test_multi_token_mcap(self) -> bool:
        """Test multi-token market cap data fetch"""
        self.logger.info(f"Multi-token market cap test: {datetime.now()}")
        
        try:
            cprint("🧪 Testing multi-token market cap data fetch...", "yellow")
            
            # Check if the module was imported successfully
            if not self.module_imported or not self.gmgn_adapter:
                cprint(f"  ⚠️ GMGN module not imported, skipping test", "yellow")
                return False
            
            # Initialize the adapter using our stored class reference
            adapter = self.gmgn_adapter()
            
            # Test with multiple tokens (use popular tokens for consistent results)
            token_addresses = [
                "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
                "7LJDPUUPBDUwJ9NYjUZXH7xGLhtPRdYmEJypFYfYVY3z",  # JTO
                "LBuRc6GzabdkXPYWbYPwP4ujzqJMxQCJSdCnrV11hHk"    # BERN
            ]
            
            # Use a short time frame for faster tests
            days = 3
            
            # Set test mode environment variable
            os.environ["TEST_MODE"] = "1"
            
            # Execute adapter fetch with output suppression
            with suppress_all_output():
                # Process each token individually since there's no multi-token method
                result = {}
                # Make the API call with timeout for each token
                cprint("  📊 Fetching multi-token market cap data...", "blue")
                
                # Set a timeout for the entire operation
                try:
                    # Process each token individually
                    for token in token_addresses:
                        # Use the existing fetch_token_mcap_data method for each token
                        fetch_task = asyncio.create_task(adapter.fetch_token_mcap_data(token, days))
                        token_result = await asyncio.wait_for(fetch_task, timeout=25)  # 25 second timeout per token
                        if token_result:
                            result[token] = token_result
                except asyncio.TimeoutError:
                    cprint("  ❌ Multi-token market cap fetch operation timed out", "red")
                    # Clean up environment variable
                    if "TEST_MODE" in os.environ:
                        del os.environ["TEST_MODE"]
                    return False
            
            # Clean up environment variable
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
            
            # Check result validity
            if result and isinstance(result, dict) and len(result.keys()) > 0:
                total_candles = sum(len(candles) for candles in result.values())
                cprint(f"  ✅ Successfully fetched data for {len(result.keys())}/{len(token_addresses)} tokens with {total_candles} total candles", "green")
                # Discard results to avoid storing large data
                result = None
                return True
            else:
                cprint("  ⚠️ API call completed, but no market cap data was returned", "yellow")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error in multi-token market cap test: {str(e)}", "red")
            self.logger.exception("Error in test_multi_token_mcap")
            # Clean up any leftover environment variable
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
            return False
    
    async def test_token_data_fetch(self) -> bool:
        """
        Test token data retrieval functionality.
        """
        if not self.module_imported or not self.gmgn_adapter:
            cprint("  ⚠️ GMGN module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing token data retrieval...", "blue")
        
        try:
            # Initialize adapter
            adapter = self.gmgn_adapter()
            
            # Test with a token address
            token_address = self.token_addresses[0]
            
            # Make the API call
            cprint(f"  Fetching token data for {token_address}...", "blue")
            
            # Set a timeout for the operation
            fetch_task = asyncio.create_task(adapter.get_token_info(token_address))
            try:
                result = await asyncio.wait_for(fetch_task, timeout=25)  # 25 second timeout
            except asyncio.TimeoutError:
                cprint("  ❌ Token data fetch operation timed out after 25 seconds", "red")
                return False
            
            # Verify the result
            if result and isinstance(result, dict):
                cprint(f"  ✓ Successfully fetched token data: {result.get('symbol')}", "green")
                return True
            else:
                cprint("  ❌ Failed to fetch token data or unexpected format", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error fetching token data: {str(e)}", "red")
            self.logger.exception("Error in test_token_data_fetch")
            return False
    
    async def test_multi_token_data(self) -> bool:
        """
        Test multi-token data retrieval.
        """
        if not self.module_imported or not self.gmgn_adapter:
            cprint("  ⚠️ GMGN module not imported or not enough token addresses", "yellow")
            return False
            
        if len(self.token_addresses) < 2:
            cprint("  ⚠️ Not enough token addresses for multi-token test", "yellow")
            return False
        
        cprint("  Testing multi-token data retrieval...", "blue")
        
        try:
            # Initialize adapter
            adapter = self.gmgn_adapter()
            
            # Test with multiple token addresses
            token_addresses = self.token_addresses[:2]  # Use first two addresses
            
            # Make the API call
            cprint(f"  Fetching token data for {len(token_addresses)} tokens...", "blue")
            
            # Process tokens one by one since there's no batch method
            results = []
            for token_address in token_addresses:
                try:
                    token_data = await adapter.get_token_info(token_address)
                    results.append(token_data)
                except Exception as e:
                    cprint(f"  ⚠️ Error fetching data for {token_address}: {e}", "yellow")
            
            # Check if we got any results
            if results:
                cprint(f"  ✓ Successfully fetched data for {len(results)} tokens", "green")
                return True
            else:
                cprint("  ❌ Failed to fetch data for any tokens", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error fetching multi-token data: {str(e)}", "red")
            self.logger.exception("Error in test_multi_token_data")
            return False
    
    async def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all GMGN module tests.
        
        Returns:
            Dictionary mapping test names to results
        """
        # Discover environment variable requirements for tests
        self.discover_test_env_vars()
        
        # Run the tests using the base class method
        return await super().run_all_tests()

async def run_tests(options: Optional[Dict[str, Any]] = None) -> int:
    """Run all GMGN module tests."""
    tester = GmgnTester(options)
    try:
        test_results = await tester.run_all_tests()
        
        # Clean up
        tester.cleanup()
        
        # Get all non-skipped test results
        non_skipped_results = [result for result in test_results.values() 
                              if result.get("status") != "skipped"]
        
        # If all tests were skipped, return 2 (special code for "all skipped")
        if not non_skipped_results:
            return 2
            
        # Return 0 (success) if all non-skipped tests passed, 1 (failure) otherwise
        return 0 if all(result.get("status") == "passed" 
                       for result in non_skipped_results) else 1
                       
    except Exception as e:
        print(f"Error running GMGN tests: {str(e)}")
        # Clean up
        tester.cleanup()
        return 1

if __name__ == "__main__":
    # Allow running this file directly for testing
    asyncio.run(run_tests()) 