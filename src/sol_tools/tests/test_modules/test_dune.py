"""
Test Dune API module functionality.

This module tests the Dune module's functionality with real data.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Mapping, Optional

from ...tests.base_tester import BaseTester, cprint, STATUS_INDICATORS
from ...tests.test_data.real_test_data import REAL_DUNE_QUERY_RESULT

def get_test_names() -> List[str]:
    """
    Get the names of all tests in this module.
    
    Returns:
        A list of test names for display in the test runner
    """
    return [
        "Dune Module Imports",
        "Dune Query Parsing",
        "Dune API Key Validation"
    ]

class DuneTester(BaseTester):
    """Test Dune module functionality with real data."""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """Initialize the DuneTester."""
        super().__init__("Dune")
        
        # Store options
        self.options = options or {}
        
        # Create Dune test directories
        self._create_dune_directories()
        
        # Create test data
        self._create_test_data()
        
        # Initialize Dune module
        self._init_dune_module()
        
        # Required environment variables for this module
        self.required_env_vars = ["DUNE_API_KEY"]
    
    def _create_dune_directories(self) -> None:
        """Create Dune-specific test directories."""
        (self.test_root / "input-data" / "dune").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "dune" / "queries").mkdir(parents=True, exist_ok=True)
    
    def _create_test_data(self) -> None:
        """Create test data for Dune tests."""
        # Use real query result data
        self.query_result = REAL_DUNE_QUERY_RESULT
        self.query_result_file = self.test_root / "output-data" / "dune" / "queries" / "test_query.json"
        
        with open(self.query_result_file, "w") as f:
            json.dump(self.query_result, f, indent=2)
    
    def _init_dune_module(self) -> None:
        """Initialize Dune module with test mode."""
        try:
            # Import Dune module
            from ...modules.dune import handlers as dune_handlers
            self.dune_handlers = dune_handlers
            
            self.module_available = True
            cprint("  ✓ Dune module imported successfully", "green")
            
        except ImportError as e:
            self.logger.warning(f"Failed to import Dune module: {str(e)}")
            self.module_available = False
            cprint(f"  ❌ Failed to import Dune module: {str(e)}", "red")
    
    async def test_dune_imports(self) -> bool:
        """Test if Dune module can be imported."""
        if not self.module_available:
            cprint("  ❌ Dune module could not be imported", "red")
            return False
        
        cprint("  ✓ Dune module imported successfully", "green")
        return True
    
    async def test_dune_query_parsing(self) -> bool:
        """Test parsing Dune query results."""
        if not self.module_available:
            cprint("  ⚠️ Dune module not available, skipping", "yellow")
            return False
        
        try:
            # Verify the query result file exists
            if not self.query_result_file.exists():
                cprint(f"  ❌ Query result file not found: {self.query_result_file}", "red")
                return False
            
            # Load and validate the query result data
            with open(self.query_result_file, "r") as f:
                data = json.load(f)
            
            # Check data structure
            if not isinstance(data, dict):
                cprint("  ❌ Query result data is not a dictionary", "red")
                return False
                
            cprint("  ✓ Successfully verified query result file structure", "green")
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_dune_query_parsing: {str(e)}", "red")
            self.logger.exception("Exception in test_dune_query_parsing")
            return False
    
    async def test_dune_api_key(self) -> bool:
        """
        Test if Dune API key is properly set.
        
        @requires_env: DUNE_API_KEY
        """
        if not self.module_available:
            cprint("  ⚠️ Dune module not available, skipping", "yellow")
            return False
            
        try:
            # Check if API key is in environment
            api_key = os.environ.get("DUNE_API_KEY")
            if not api_key:
                cprint("  ❌ DUNE_API_KEY environment variable not set", "red")
                return False
                
            # Verify it's not empty
            if not api_key.strip():
                cprint("  ❌ DUNE_API_KEY is empty", "red")
                return False
                
            cprint("  ✓ DUNE_API_KEY is properly set", "green")
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_dune_api_key: {str(e)}", "red")
            self.logger.exception("Exception in test_dune_api_key")
            return False
    
    async def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all Dune module tests.
        
        Returns:
            Dictionary mapping test names to results
        """
        # Discover environment variable requirements for tests
        self.discover_test_env_vars()
        
        # Run the tests using the base class method
        return await super().run_all_tests()

async def run_dune_tests(options: Optional[Dict[str, Any]] = None) -> int:
    """Run all Dune tests."""
    tester = DuneTester(options)
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
        print(f"Error running Dune tests: {str(e)}")
        # Clean up
        tester.cleanup()
        return 1

if __name__ == "__main__":
    asyncio.run(run_dune_tests()) 