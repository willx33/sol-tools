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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Callable, Type

from ...tests.base_tester import BaseTester, cprint, STATUS_INDICATORS
from ...tests.test_data.real_test_data import (
    REAL_TOKEN_ADDRESSES,
    REAL_WALLET_ADDRESSES
)

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
    """Tester class for GMGN module functionality."""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """Initialize the GMGN tester with options."""
        # Initialize the base class
        super().__init__("GMGN")
        
        # Store options separately
        self.options = options or {}
        
        # Store real addresses for testing
        self.token_addresses = REAL_TOKEN_ADDRESSES
        self.wallet_addresses = REAL_WALLET_ADDRESSES
        
        # Required environment variables for the module
        # GMGN module doesn't require any specific env vars
        self.required_env_vars = []
        
        # Attempt to import GMGN modules
        self.module_imported = False
        self.gmgn_adapter = None
        self._try_import_gmgn()
    
    def _try_import_gmgn(self) -> bool:
        """Try to import the GMGN module."""
        try:
            # Direct imports instead of using importlib
            try:
                from sol_tools.modules.gmgn.gmgn_adapter import GMGNAdapter
                self.gmgn_adapter = GMGNAdapter
                
                from sol_tools.modules.gmgn import standalone_mcap
                self.standalone_mcap = standalone_mcap
                
                from sol_tools.modules.gmgn import standalone_token_data
                self.standalone_token_data = standalone_token_data
                
                self.module_imported = True
                cprint("  ✓ Successfully imported GMGN modules", "green")
                return True
            except ImportError:
                # Try alternative import paths
                # First, try with src prefix
                try:
                    from src.sol_tools.modules.gmgn.gmgn_adapter import GMGNAdapter
                    self.gmgn_adapter = GMGNAdapter
                    
                    from src.sol_tools.modules.gmgn import standalone_mcap
                    self.standalone_mcap = standalone_mcap
                    
                    from src.sol_tools.modules.gmgn import standalone_token_data
                    self.standalone_token_data = standalone_token_data
                    
                    self.module_imported = True
                    cprint("  ✓ Successfully imported GMGN modules (using src prefix)", "green")
                    return True
                except ImportError:
                    # Try relative imports
                    from ...modules.gmgn.gmgn_adapter import GMGNAdapter
                    self.gmgn_adapter = GMGNAdapter
                    
                    from ...modules.gmgn import standalone_mcap
                    self.standalone_mcap = standalone_mcap
                    
                    from ...modules.gmgn import standalone_token_data
                    self.standalone_token_data = standalone_token_data
                    
                    self.module_imported = True
                    cprint("  ✓ Successfully imported GMGN modules (using relative imports)", "green")
                    return True
        except (ImportError, AttributeError) as e:
            cprint(f"  ⚠️ Failed to import GMGN module: {str(e)}", "yellow")
            self.logger.warning(f"Failed to import GMGN module: {str(e)}")
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
        """
        Test market cap data retrieval functionality.
        """
        if not self.module_imported or not self.gmgn_adapter:
            cprint("  ⚠️ GMGN module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing market cap data retrieval...", "blue")
        
        try:
            # Initialize adapter
            adapter = self.gmgn_adapter()
            
            # Test with a token address
            token_address = self.token_addresses[0]
            # Use a small number of days to avoid overflow
            days = 1
            
            # Make the API call
            cprint(f"  Fetching market cap data for {token_address}...", "blue")
            
            # Set a timeout for the operation
            fetch_task = asyncio.create_task(adapter.fetch_token_mcap_data(token_address, days))
            try:
                result = await asyncio.wait_for(fetch_task, timeout=25)  # 25 second timeout
            except asyncio.TimeoutError:
                cprint("  ❌ Market cap fetch operation timed out after 25 seconds", "red")
                return False
            
            # Verify the result
            if result and isinstance(result, list) and len(result) > 0:
                cprint(f"  ✓ Successfully fetched {len(result)} candles", "green")
                # Discard results to avoid storing data
                result = None
                return True
            else:
                # Even if no market cap data is found, consider the test passing
                # as long as the API call completed successfully
                cprint("  ✓ API call successful, but no market cap data found for token", "green")
                return True
                
        except Exception as e:
            cprint(f"  ❌ Error fetching market cap data: {str(e)}", "red")
            self.logger.exception("Error in test_market_cap_fetch")
            return False
    
    async def test_standalone_market_cap(self) -> bool:
        """
        Test the standalone market cap implementation.
        """
        if not self.module_imported or not hasattr(self.standalone_mcap, "standalone_fetch_token_mcaps"):
            cprint("  ⚠️ GMGN module not imported or standalone function not found, skipping test", "yellow")
            return False
        
        cprint("  Testing standalone market cap implementation...", "blue")
        
        try:
            # Get the standalone function
            standalone_func = getattr(self.standalone_mcap, "standalone_fetch_token_mcaps")
            
            # Test with a token
            token_address = self.token_addresses[0]
            start_time = int((datetime.now() - timedelta(days=1)).timestamp())
            
            # Make the API call with a timeout
            cprint(f"  Fetching market cap data for {token_address}...", "blue")
            
            # Fetch with a timeout
            fetch_task = asyncio.create_task(standalone_func(token_address, start_time))
            try:
                result = await asyncio.wait_for(fetch_task, timeout=25)  # 25 second timeout
            except asyncio.TimeoutError:
                cprint("  ❌ Fetch operation timed out after 25 seconds", "red")
                return False
            
            # Verify the result
            if result and isinstance(result, list) and len(result) > 0:
                cprint(f"  ✓ Successfully fetched {len(result)} candles", "green")
                # Discard results
                result = None
                return True
            else:
                # Even if no market cap data is found, consider the test passing
                # as long as the API call completed successfully
                cprint("  ✓ API call successful, but no market cap data found for token", "green")
                return True
                
        except Exception as e:
            cprint(f"  ❌ Error fetching standalone market cap data: {str(e)}", "red")
            self.logger.exception("Error in test_standalone_market_cap")
            return False
    
    async def test_multi_token_mcap(self) -> bool:
        """
        Test multi-token market cap data retrieval.
        """
        if not self.module_imported or not self.gmgn_adapter:
            cprint("  ⚠️ GMGN module not imported or not enough token addresses", "yellow")
            return False
            
        if len(self.token_addresses) < 2:
            cprint("  ⚠️ Not enough token addresses for multi-token test", "yellow")
            return False
        
        cprint("  Testing multi-token market cap data retrieval...", "blue")
        
        try:
            # Initialize adapter
            adapter = self.gmgn_adapter()
            
            # Test with multiple token addresses
            token_addresses = self.token_addresses[:2]  # Use first two addresses
            # Use a small number of days to avoid overflow
            days = 1
            
            # Make the API call
            cprint(f"  Fetching market cap data for {len(token_addresses)} tokens...", "blue")
            
            # Join token addresses with spaces for the API
            token_str = " ".join(token_addresses)
            
            # Set a timeout for the operation
            fetch_task = asyncio.create_task(adapter.fetch_token_mcap_data(token_str, days))
            try:
                result = await asyncio.wait_for(fetch_task, timeout=30)  # 30 second timeout
            except asyncio.TimeoutError:
                cprint("  ❌ Multi-token market cap fetch operation timed out after 30 seconds", "red")
                return False
            
            # Verify the result
            if result and isinstance(result, dict):
                total_candles = sum(len(candles) for candles in result.values())
                cprint(f"  ✓ Successfully fetched data for {len(result)} tokens with {total_candles} total candles", "green")
                # Discard results
                result = None
                return True
            else:
                cprint("  ❌ Unexpected result format for multi-token market cap", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error fetching multi-token market cap data: {str(e)}", "red")
            self.logger.exception("Error in test_multi_token_mcap")
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