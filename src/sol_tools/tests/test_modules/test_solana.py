"""
Test Solana module functionality.

This module tests the Solana module's functionality with real data.
"""

import os
import sys
import json
import tempfile
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable, Type

from ...tests.base_tester import BaseTester, cprint
from ...tests.test_data.real_test_data import REAL_WALLET_ADDRESSES, REAL_TOKEN_ADDRESSES

# Use real test data for Solana tests
SOLANA_TEST_WALLETS = [{"address": addr} for addr in REAL_WALLET_ADDRESSES]
SOLANA_TEST_TRANSACTIONS = [
    {
        "signature": f"real_sig_{i}",
        "timestamp": 1645000000 + (i * 3600),
        "success": True,
        "wallet": REAL_WALLET_ADDRESSES[i % len(REAL_WALLET_ADDRESSES)]
    } for i in range(5)  # Reduced number for faster tests
]

# Define a stub for SolanaAdapter if not available
class StubSolanaAdapter:
    def __init__(self, api_key=None, **kwargs):
        self.api_key = api_key
        
    def validate_solana_address(self, address):
        # Stub implementation for validation
        return len(address) >= 32
        
    async def get_wallet_balance(self, wallet_address):
        # Stub implementation
        return 0.0
        
    async def get_token_price(self, token_address):
        # Stub implementation
        return 0.0

# Attempt to import the real adapter
try:
    from ...modules.solana.solana_adapter import SolanaAdapter as RealSolanaAdapter
    SolanaAdapter = RealSolanaAdapter
except ImportError:
    # Use the stub if import fails
    SolanaAdapter = StubSolanaAdapter

def get_test_names() -> List[str]:
    """
    Get the names of all tests in this module.
    
    Returns:
        A list of test names for display in the test runner
    """
    return [
        "Solana Module Imports",
        "Solana Adapter Initialization",
        "Wallet Address Validation",
        "Token Address Validation",
        "Wallet Balance Retrieval",
        "Token Price Retrieval"
    ]

class SolanaTester(BaseTester):
    """Test Solana module functionality with real data."""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """Initialize the SolanaTester."""
        super().__init__("Solana")
        
        # Store options
        self.options = options or {}
        
        # Create Solana test directories
        self._create_solana_directories()
        
        # Create test data
        self._create_test_data()
        
        # Initialize Solana module
        self._init_solana_module()
        
        # Required environment variables for Solana module
        self.required_env_vars = ["HELIUS_API_KEY"]
    
    def _create_solana_directories(self) -> None:
        """Create Solana-specific test directories."""
        (self.test_root / "input-data" / "solana").mkdir(parents=True, exist_ok=True)
        (self.test_root / "input-data" / "solana" / "wallet-lists").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "solana").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "solana" / "monitoring").mkdir(parents=True, exist_ok=True)
    
    def _create_test_data(self) -> None:
        """Create test data files in the test directories."""
        # Create test wallets using real data
        self.solana_wallets = SOLANA_TEST_WALLETS
        self.solana_wallets_file = self.test_root / "input-data" / "solana" / "wallet-lists" / "test_wallets.json"
        
        with open(self.solana_wallets_file, "w") as f:
            json.dump(self.solana_wallets, f, indent=2)
        
        # Create test transactions using real data
        self.solana_transactions = SOLANA_TEST_TRANSACTIONS
        self.solana_transactions_file = self.test_root / "output-data" / "solana" / "transactions.json"
        
        with open(self.solana_transactions_file, "w") as f:
            json.dump(self.solana_transactions, f, indent=2)
        
        # Create token list for monitoring
        self.token_list = [
            {
                "symbol": "SOL",
                "name": "Solana",
                "address": "So11111111111111111111111111111111111111112",
                "decimals": 9
            },
            {
                "symbol": "USDC",
                "name": "USD Coin",
                "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "decimals": 6
            },
            {
                "symbol": "BONK",
                "name": "Bonk",
                "address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
                "decimals": 5
            }
        ]
        
        self.token_list_file = self.test_root / "input-data" / "solana" / "token_list.json"
        
        with open(self.token_list_file, "w") as f:
            json.dump(self.token_list, f, indent=2)
    
    def _init_solana_module(self) -> None:
        """Initialize Solana module."""
        try:
            # Try to import the Solana adapter - just check if import is possible
            module_name = "solana_adapter"
            module_path = f"src.sol_tools.modules.solana.{module_name}"
            
            # Check if module exists
            try:
                # Use importlib.import_module which is more reliable than find_spec
                importlib.import_module(module_path)
                self.module_imported = True
                cprint(f"  ✓ Solana module found at {module_path}", "green")
            except ImportError:
                self.module_imported = False
                cprint(f"  ⚠️ Solana module not found at {module_path}", "yellow")
            
        except (ImportError, ModuleNotFoundError) as e:
            cprint(f"  ⚠️ Failed to import Solana module: {str(e)}", "yellow")
            self.logger.warning(f"Failed to import Solana module: {str(e)}")
            self.module_imported = False
    
    def _get_adapter_class(self) -> Optional[Callable]:
        """Get the SolanaAdapter class dynamically."""
        try:
            module_path = "src.sol_tools.modules.solana.solana_adapter"
            module = importlib.import_module(module_path)
            return getattr(module, "SolanaAdapter", None)
        except (ImportError, AttributeError):
            return None
    
    async def test_module_imports(self) -> bool:
        """
        Test that the Solana module can be imported.
        """
        if not self.module_imported:
            cprint("  ⚠️ Solana module not imported", "yellow")
            return False
            
        cprint("  Testing Solana module imports...", "blue")
        
        try:
            # Get the adapter class
            SolanaAdapter = self._get_adapter_class()
            if SolanaAdapter is None:
                cprint("  ❌ Failed to find SolanaAdapter class", "red")
                return False
                
            cprint("  ✓ Successfully imported Solana modules", "green")
            return True
        except Exception as e:
            cprint(f"  ❌ Error importing Solana modules: {str(e)}", "red")
            self.logger.exception("Error in test_module_imports")
            return False
    
    async def test_solana_adapter_init(self) -> bool:
        """
        Test Solana adapter initialization.
        
        @requires_env: HELIUS_API_KEY
        """
        if not self.module_imported:
            cprint("  ⚠️ Solana module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing Solana adapter initialization...", "blue")
        
        try:
            # Get the adapter class
            SolanaAdapter = self._get_adapter_class()
            if SolanaAdapter is None:
                cprint("  ❌ Failed to find SolanaAdapter class", "red")
                return False
            
            # Initialize the adapter with whatever kwargs are used by the actual implementation
            adapter_kwargs = {"api_key": os.environ.get("HELIUS_API_KEY")}
            adapter = SolanaAdapter(**adapter_kwargs)
            
            # Check if the adapter initialized correctly
            cprint("  ✓ Successfully initialized Solana adapter", "green")
            return True
        except Exception as e:
            cprint(f"  ❌ Error initializing Solana adapter: {str(e)}", "red")
            self.logger.exception("Error in test_solana_adapter_init")
            return False
    
    async def test_wallet_validation(self) -> bool:
        """
        Test Solana wallet validation functionality.
        """
        if not self.module_imported:
            cprint("  ⚠️ Solana module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing Solana wallet validation...", "blue")
        
        try:
            # Get the adapter class
            SolanaAdapter = self._get_adapter_class()
            if SolanaAdapter is None:
                cprint("  ❌ Failed to find SolanaAdapter class", "red")
                return False
            
            # Initialize the adapter
            adapter = SolanaAdapter()
            
            # Use getattr to call methods to avoid linter issues
            validate_method = getattr(adapter, "validate_address", None)
            if validate_method is None:
                validate_method = getattr(adapter, "is_valid_address", None)
            
            if validate_method is None:
                cprint("  ❌ Could not find validation method on SolanaAdapter", "red")
                return False
            
            # Test with valid addresses
            valid_results = []
            for addr in REAL_WALLET_ADDRESSES:
                result = validate_method(addr)
                valid_results.append(result)
                cprint(f"  Validating {addr}: {'✓' if result else '❌'}", "blue")
            
            # Test with invalid addresses
            invalid_results = []
            invalid_addresses = ["not-a-wallet", "123", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB26"]
            for addr in invalid_addresses:
                result = not validate_method(addr)
                invalid_results.append(result)
                cprint(f"  Validating invalid {addr}: {'✓' if result else '❌'}", "blue")
            
            # Check that all validations worked correctly
            all_valid = all(valid_results)
            all_invalid = all(invalid_results)
            
            if all_valid and all_invalid:
                cprint("  ✓ Wallet validation working correctly", "green")
                return True
            else:
                if not all_valid:
                    cprint("  ❌ Some valid addresses were not recognized", "red")
                if not all_invalid:
                    cprint("  ❌ Some invalid addresses were incorrectly recognized as valid", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error in wallet validation test: {str(e)}", "red")
            self.logger.exception("Error in test_wallet_validation")
            return False
    
    async def test_token_validation(self) -> bool:
        """
        Test Solana token validation functionality.
        """
        if not self.module_imported:
            cprint("  ⚠️ Solana module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing Solana token validation...", "blue")
        
        try:
            # Get the adapter class
            SolanaAdapter = self._get_adapter_class()
            if SolanaAdapter is None:
                cprint("  ❌ Failed to find SolanaAdapter class", "red")
                return False
            
            # Initialize the adapter
            adapter = SolanaAdapter()
            
            # Use getattr to call methods to avoid linter issues
            validate_method = getattr(adapter, "validate_address", None)
            if validate_method is None:
                validate_method = getattr(adapter, "is_valid_address", None)
            
            if validate_method is None:
                cprint("  ❌ Could not find validation method on SolanaAdapter", "red")
                return False
            
            # Test with valid token addresses
            valid_results = []
            for addr in [t["address"] for t in self.token_list]:
                valid_results.append(validate_method(addr))
            
            # Test with invalid addresses
            invalid_results = []
            invalid_addresses = ["not-a-token", "123", "inva"]
            for addr in invalid_addresses:
                invalid_results.append(not validate_method(addr))
            
            # Check that all validations worked correctly
            all_valid = all(valid_results)
            all_invalid = all(invalid_results)
            
            if all_valid and all_invalid:
                cprint("  ✓ Token validation working correctly", "green")
                return True
            else:
                cprint("  ❌ Token validation not working as expected", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error in token validation test: {str(e)}", "red")
            self.logger.exception("Error in test_token_validation")
            return False
    
    async def test_wallet_balance(self) -> bool:
        """
        Test retrieving wallet balance information.
        
        @requires_env: HELIUS_API_KEY
        """
        if not self.module_imported:
            cprint("  ⚠️ Solana module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing wallet balance retrieval...", "blue")
        
        try:
            # Get the adapter class
            SolanaAdapter = self._get_adapter_class()
            if SolanaAdapter is None:
                cprint("  ❌ Failed to find SolanaAdapter class", "red")
                return False
            
            # Initialize the adapter with whatever kwargs are used by the actual implementation
            adapter = SolanaAdapter(**{"api_key": os.environ.get("HELIUS_API_KEY")})
            
            # Test with a real wallet address
            wallet_address = REAL_WALLET_ADDRESSES[0]
            
            # Use getattr to call methods to avoid linter issues
            balance_method = getattr(adapter, "get_wallet_balance", None)
            if balance_method is None:
                balance_method = getattr(adapter, "get_balance", None)
            
            if balance_method is None:
                cprint("  ❌ Could not find balance method on SolanaAdapter", "red")
                return False
            
            # Get the wallet balance
            balance = await balance_method(wallet_address)
            
            # Check that we got a valid balance
            if balance is not None and isinstance(balance, (int, float)) and balance >= 0:
                cprint(f"  ✓ Successfully retrieved balance for {wallet_address}: {balance} SOL", "green")
                return True
            else:
                cprint(f"  ❌ Failed to retrieve valid balance for {wallet_address}", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error retrieving wallet balance: {str(e)}", "red")
            self.logger.exception("Error in test_wallet_balance")
            return False
    
    async def test_token_price(self) -> bool:
        """
        Test retrieving token price information.
        
        @requires_env: HELIUS_API_KEY
        """
        if not self.module_imported:
            cprint("  ⚠️ Solana module not imported, skipping test", "yellow")
            return False
        
        cprint("  Testing token price retrieval...", "blue")
        
        try:
            # Use dynamic import to avoid linter issues
            import importlib
            solana_module = importlib.import_module("....modules.solana.solana_adapter", package=__name__)
            SolanaAdapter = getattr(solana_module, "SolanaAdapter")
            
            # Initialize the adapter with whatever kwargs are used by the actual implementation
            adapter = SolanaAdapter(**{"api_key": os.environ.get("HELIUS_API_KEY")})
            
            # Test with a real token address (SOL)
            token_address = "So11111111111111111111111111111111111111112"  # SOL
            
            # Use getattr to call methods to avoid linter issues
            price_method = getattr(adapter, "get_token_price", None)
            if price_method is None:
                price_method = getattr(adapter, "get_price", None)
            
            if price_method is None:
                cprint("  ❌ Could not find price method on SolanaAdapter", "red")
                return False
            
            # Get the token price
            price = await price_method(token_address)
            
            # Check that we got a valid price
            if price is not None and isinstance(price, (int, float)) and price > 0:
                cprint(f"  ✓ Successfully retrieved price for SOL: ${price}", "green")
                return True
            else:
                cprint(f"  ❌ Failed to retrieve valid price for SOL", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Error retrieving token price: {str(e)}", "red")
            self.logger.exception("Error in test_token_price")
            return False
    
    async def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all Solana module tests.
        
        Returns:
            Dictionary mapping test names to results
        """
        # Discover environment variable requirements for tests
        self.discover_test_env_vars()
        
        # Run the tests using the base class method
        return await super().run_all_tests()

async def run_tests(options: Optional[Dict[str, Any]] = None) -> int:
    """Run all Solana module tests."""
    tester = SolanaTester(options)
    try:
        test_results = await tester.run_all_tests()
        
        # Clean up resources
        try:
            tester.cleanup()
        except Exception as cleanup_error:
            print(f"Warning: Error during cleanup: {cleanup_error}")
        
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
        print(f"Error running Solana tests: {str(e)}")
        
        # Clean up resources
        try:
            tester.cleanup()
        except Exception as cleanup_error:
            print(f"Warning: Error during cleanup: {cleanup_error}")
            
        return 1

if __name__ == "__main__":
    # Allow running this file directly for testing
    import asyncio
    asyncio.run(run_tests()) 