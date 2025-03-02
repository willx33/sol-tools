"""
Test Dragon module functionality.

This module tests the Dragon module's functionality with real data.
"""

import os
import sys
import json
import importlib
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Mapping

# Add src to Python path to ensure Dragon can be found
current_dir = Path(__file__).resolve().parent
test_modules_dir = current_dir
tests_dir = test_modules_dir.parent
sol_tools_dir = tests_dir.parent
src_dir = sol_tools_dir.parent
dragon_dir = src_dir / "Dragon"

# Add paths to sys.path if they aren't already there
for path in [str(src_dir), str(dragon_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from src.sol_tools.tests.base_tester import BaseTester, cprint, STATUS_INDICATORS
from src.sol_tools.tests.test_data.real_test_data import REAL_TOKEN_ADDRESSES, REAL_WALLET_ADDRESSES, REAL_ETH_ADDRESSES

# Define this as a module-level variable
DRAGON_AVAILABLE = False

# Try to check if Dragon is available
try:
    import Dragon
    DRAGON_AVAILABLE = True
except ImportError as e:
    DRAGON_AVAILABLE = False
    print(f"Dragon import error: {e}")

def get_test_names() -> List[str]:
    """
    Get the names of all tests in this module.
    
    Returns:
        A list of test names for display in the test runner
    """
    return [
        "Dragon Module Imports",
        "Solana Wallet Import",
        "Ethereum Wallet Import",
        "GMGN Token Adapter",
        "Dragon Handlers"
    ]

class DragonTester(BaseTester):
    """Test Dragon module functionality with real data."""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """Initialize the DragonTester."""
        super().__init__("Dragon")
        
        # Store options
        self.options = options or {}
        
        # Create Dragon test directories
        self._create_dragon_directories()
        
        # Create test data
        self._create_test_data()
        
        # Dragon module references
        self.dragon_adapter = None
        self.gmgn_module = None
        
        # Set dragon_available from module-level variable
        self.dragon_available = DRAGON_AVAILABLE
        print(f"Dragon available: {self.dragon_available}")
        
        # Register Dragon as a required env var for all Dragon tests
        if not self.dragon_available:
            # Create a virtual environment variable that doesn't exist
            os.environ.setdefault("_REQUIRED_DRAGON_MODULE", "")
            
            # Apply this to all Dragon tests
            for test_name in dir(self):
                if test_name.startswith("test_dragon_"):
                    self.test_env_vars[test_name] = ["_REQUIRED_DRAGON_MODULE"]
                if test_name.startswith("test_gmgn_"):
                    self.test_env_vars[test_name] = ["_REQUIRED_DRAGON_MODULE"]
        
        # Attempt to import Dragon modules for tests
        self._try_import_dragon()
        
    def _create_dragon_directories(self) -> None:
        """Create Dragon-specific test directories."""
        # Create Dragon directories
        (self.test_root / "input-data" / "solana" / "wallet-lists").mkdir(parents=True, exist_ok=True)
        (self.test_root / "input-data" / "ethereum" / "wallet-lists").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "dragon").mkdir(parents=True, exist_ok=True)
    
    def _create_test_data(self) -> None:
        """Create test data files in the test directories."""
        # Create Solana test wallets using real data
        self.solana_wallets = [{"address": addr} for addr in REAL_WALLET_ADDRESSES]
        self.solana_wallets_file = self.test_root / "input-data" / "solana" / "wallet-lists" / "test_wallets.json"
        
        with open(self.solana_wallets_file, "w") as f:
            json.dump(self.solana_wallets, f, indent=2)
        
        # Create Ethereum test wallets using real Ethereum addresses
        self.ethereum_wallets = [{"address": addr} for addr in REAL_ETH_ADDRESSES["wallets"][:10]]
        self.ethereum_wallets_file = self.test_root / "input-data" / "ethereum" / "wallet-lists" / "test_wallets.json"
        
        with open(self.ethereum_wallets_file, "w") as f:
            json.dump(self.ethereum_wallets, f, indent=2)
        
        # Create GMGN token data
        self.gmgn_token_data = {
            "name": "Magic Eden Token",
            "symbol": "GMGN",
            "address": "4e8rF4Q5s8AmTacxvfVMKJtQKMjM2ZfbCGnzAEjRGKTZ",
            "decimals": 9
        }
    
    def _try_import_dragon(self) -> bool:
        """
        Try to import the Dragon module.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try to import the Dragon adapter using absolute import
            import src.sol_tools.modules.dragon.dragon_adapter as dragon_module
            self.dragon_adapter = dragon_module
            
            # Try to import the GMGN module
            try:
                import src.sol_tools.modules.gmgn.gmgn_adapter as gmgn_module
                self.gmgn_module = gmgn_module
            except ImportError as e:
                cprint(f"  ⚠️ Failed to import GMGN module: {str(e)}", "yellow")
            
            # Try to import handlers module using absolute import
            try:
                import src.sol_tools.modules.dragon.handlers as handlers_module
                return True
            except ImportError as e:
                cprint(f"  ❌ Failed to import Dragon handlers: {str(e)}", "red")
                return False
            
            return True
            
        except ImportError as e:
            cprint(f"  ⚠️ Failed to import Dragon module: {str(e)}", "yellow")
            self.logger.warning(f"Failed to import Dragon module: {str(e)}")
            return False
    
    async def test_dragon_imports(self) -> Optional[bool]:
        """Test if Dragon modules can be imported."""
        # This test requires Dragon module to be available
        if not self.dragon_available:
            cprint("  ⚠️ Dragon module not available, skipping", "yellow")
            # Return None to indicate the test should be skipped
            return None
            
        if self.dragon_adapter is None:
            cprint("  ❌ Dragon adapter module could not be imported", "red")
            return False
        
        cprint("  ✓ Dragon adapter module imported successfully", "green")
        return True
    
    async def test_dragon_solana_import(self) -> Optional[bool]:
        """
        Test importing Solana wallets into Dragon.
        
        @requires_env: SOL_TOOLS_DATA_DIR
        """
        # This test requires Dragon module to be available
        if not self.dragon_available:
            cprint("  ⚠️ Dragon module not available, skipping", "yellow")
            # Return None to indicate the test should be skipped
            return None
            
        if self.dragon_adapter is None:
            cprint("  ⚠️ Dragon adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment for testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter
            adapter_class = getattr(self.dragon_adapter, "DragonAdapter", None)
            if not adapter_class:
                cprint("  ❌ DragonAdapter class not found", "red")
                return False
                
            adapter = adapter_class()
            
            # Import the test wallet file
            filename = self.solana_wallets_file.name
            directory = self.solana_wallets_file.parent
            
            # Check file content before import
            try:
                with open(os.path.join(str(directory), filename), 'r') as f:
                    content = f.read()
                    self.logger.debug(f"File content: {content}")
            except Exception as e:
                self.logger.error(f"Error reading file before import: {e}")
            
            # Import the wallets
            import_method = getattr(adapter, "import_solana_wallets", None)
            if not import_method:
                cprint("  ❌ import_solana_wallets method not found", "red")
                
                # Restore original environment
                if original_data_dir:
                    os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
                else:
                    os.environ.pop("SOL_TOOLS_DATA_DIR", None)
                    
                return False
                
            result = import_method(filename, str(directory))
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            if not result:
                cprint("  ❌ Failed to import Solana wallets", "red")
                return False
            
            cprint("  ✓ Solana wallets imported successfully", "green")
            return True
            
        except Exception as e:
            self.logger.exception(f"Error in test_dragon_solana_import: {e}")
            cprint(f"  ❌ Error in test_dragon_solana_import: {e}", "red")
            return False
    
    async def test_dragon_ethereum_import(self) -> Optional[bool]:
        """
        Test importing Ethereum wallets into Dragon.
        
        @requires_env: SOL_TOOLS_DATA_DIR
        """
        # This test requires Dragon module to be available
        if not self.dragon_available:
            cprint("  ⚠️ Dragon module not available, skipping", "yellow")
            # Return None to indicate the test should be skipped
            return None
            
        if self.dragon_adapter is None:
            cprint("  ⚠️ Dragon adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment for testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter
            adapter_class = getattr(self.dragon_adapter, "DragonAdapter", None)
            if not adapter_class:
                cprint("  ❌ DragonAdapter class not found", "red")
                return False
                
            adapter = adapter_class()
            
            # Import the test wallet file
            filename = self.ethereum_wallets_file.name
            directory = self.ethereum_wallets_file.parent
            
            # Import the wallets
            import_method = getattr(adapter, "import_ethereum_wallets", None)
            if not import_method:
                cprint("  ❌ import_ethereum_wallets method not found", "red")
                
                # Restore original environment
                if original_data_dir:
                    os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
                else:
                    os.environ.pop("SOL_TOOLS_DATA_DIR", None)
                    
                return False
                
            result = import_method(filename, str(directory))
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            if not result:
                cprint("  ❌ Failed to import Ethereum wallets", "red")
                return False
            
            cprint("  ✓ Ethereum wallets imported successfully", "green")
            return True
            
        except Exception as e:
            self.logger.exception(f"Error in test_dragon_ethereum_import: {e}")
            cprint(f"  ❌ Error in test_dragon_ethereum_import: {e}", "red")
            return False
    
    async def test_gmgn_token_adapter(self) -> Optional[bool]:
        """
        Test GMGN token adapter functionality.
        
        @requires_env: SOL_TOOLS_DATA_DIR
        """
        # This test requires Dragon module to be available
        if not self.dragon_available:
            cprint("  ⚠️ Dragon module not available, skipping", "yellow")
            # Return None to indicate the test should be skipped
            return None
            
        if self.dragon_adapter is None:
            cprint("  ⚠️ Dragon adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment for testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Check if GMGN module exists in the codebase
            try:
                # Look for GMGN adapter in the codebase
                import src.sol_tools.modules.dragon.dragon_adapter as dragon_adapter
                if hasattr(dragon_adapter, 'GMGN_Client'):
                    cprint("  ✓ GMGN client found in Dragon adapter", "green")
                    
                    # Initialize GMGN client
                    gmgn_client = dragon_adapter.GMGN_Client()
                    
                    # Restore original environment
                    if original_data_dir:
                        os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
                    else:
                        os.environ.pop("SOL_TOOLS_DATA_DIR", None)
                        
                    cprint("  ✓ Successfully initialized GMGN client", "green")
                    return True
                else:
                    cprint("  ❌ GMGN_Client not found in Dragon adapter", "red")
            except ImportError as e:
                cprint(f"  ❌ Error importing Dragon adapter: {e}", "red")
                
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            return False
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_gmgn_token_adapter: {str(e)}", "red")
            self.logger.exception("Exception in test_gmgn_token_adapter")
            
            # Make sure we restore the environment
            try:
                if original_data_dir:
                    os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
                else:
                    os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            except:
                pass
                
            return False
    
    async def test_dragon_handlers(self) -> Optional[bool]:
        """Test loading Dragon handlers."""
        # This test requires Dragon module to be available
        if not self.dragon_available:
            cprint("  ⚠️ Dragon module not available, skipping", "yellow")
            # Return None to indicate the test should be skipped
            return None
            
        if self.dragon_adapter is None:
            cprint("  ⚠️ Dragon adapter not available, skipping", "yellow")
            return False
        
        try:
            # Try to import handlers using absolute import
            try:
                import src.sol_tools.modules.dragon.handlers as handlers
                if not handlers:
                    cprint("  ❌ Failed to import Dragon handlers", "red")
                    return False
            except ImportError as e:
                cprint(f"  ❌ Failed to import Dragon handlers: {e}", "red")
                return False
            
            cprint("  ✓ Dragon handlers loaded successfully", "green")
            return True
            
        except Exception as e:
            self.logger.exception(f"Error in test_dragon_handlers: {e}")
            cprint(f"  ❌ Error in test_dragon_handlers: {e}", "red")
            return False
    
    async def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all Dragon module tests.
        
        Returns:
            Dictionary mapping test names to results
        """
        # Discover environment variable requirements for tests
        self.discover_test_env_vars()
        
        # Run the tests using the base class method
        return await super().run_all_tests()

async def run_dragon_tests(options: Optional[Dict[str, Any]] = None) -> int:
    """Run all Dragon tests."""
    tester = DragonTester(options)
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
        print(f"Error running Dragon tests: {str(e)}")
        # Clean up
        tester.cleanup()
        return 1

if __name__ == "__main__":
    asyncio.run(run_dragon_tests()) 