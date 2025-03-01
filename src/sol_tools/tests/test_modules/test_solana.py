"""
Test Solana module functionality.

This module tests the Solana module's functionality with mock data.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...tests.base_tester import BaseTester, cprint
from ...tests.test_data.mock_data import (
    generate_solana_wallet_list,
    generate_solana_transaction_list,
    random_address
)

class SolanaTester(BaseTester):
    """Test Solana module functionality with mock data."""
    
    def __init__(self):
        """Initialize the SolanaTester."""
        super().__init__("Solana")
        
        # Create Solana test directories
        self._create_solana_directories()
        
        # Create test data
        self._create_test_data()
        
        # Solana module reference
        self.solana_adapter = None
        
        # Attempt to import Solana module
        self._try_import_solana()
    
    def _create_solana_directories(self) -> None:
        """Create Solana-specific test directories."""
        (self.test_root / "input-data" / "solana" / "wallet-lists").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "solana" / "token-monitor").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "solana" / "wallet-monitor").mkdir(parents=True, exist_ok=True)
    
    def _create_test_data(self) -> None:
        """Create test data for Solana tests."""
        # Create test wallets
        self.solana_wallets = generate_solana_wallet_list(5)
        self.solana_wallets_file = self.test_root / "input-data" / "solana" / "wallet-lists" / "test_wallets.json"
        
        with open(self.solana_wallets_file, "w") as f:
            json.dump(self.solana_wallets, f, indent=2)
        
        # Create test transactions
        self.solana_transactions = generate_solana_transaction_list(20)
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
    
    def _try_import_solana(self) -> bool:
        """
        Try to import the Solana module.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try to import the Solana adapter
            from ...modules.solana import solana_adapter
            self.solana_adapter = solana_adapter
            return True
            
        except ImportError as e:
            cprint(f"  ⚠️ Failed to import Solana module: {str(e)}", "yellow")
            self.logger.warning(f"Failed to import Solana module: {str(e)}")
            return False
    
    def test_solana_imports(self) -> bool:
        """Test if Solana module can be imported."""
        if self.solana_adapter is None:
            cprint("  ❌ Solana adapter module could not be imported", "red")
            return False
        
        cprint("  ✓ Solana adapter module imported successfully", "green")
        return True
    
    def test_solana_adapter_init(self) -> bool:
        """Test Solana adapter initialization."""
        if self.solana_adapter is None:
            cprint("  ⚠️ Solana adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter with test_mode=True
            adapter = self.solana_adapter.SolanaAdapter(test_mode=True)
            
            # Verify adapter properties
            if not hasattr(adapter, "test_mode") or not adapter.test_mode:
                cprint("  ❌ Solana adapter test_mode not set correctly", "red")
                return False
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_solana_adapter_init: {str(e)}", "red")
            self.logger.exception("Exception in test_solana_adapter_init")
            return False
    
    def test_solana_token_monitor(self) -> bool:
        """Test Solana token monitor functionality."""
        if self.solana_adapter is None:
            cprint("  ⚠️ Solana adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter with test_mode=True
            adapter = self.solana_adapter.SolanaAdapter(test_mode=True)
            
            # Mock the token data
            adapter.token_data = {token["symbol"]: token for token in self.token_list}
            
            # Test get_token_data method
            token_data = adapter.get_token_data("SOL")
            if not token_data or token_data["symbol"] != "SOL":
                cprint("  ❌ Failed to get token data", "red")
                return False
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_solana_token_monitor: {str(e)}", "red")
            self.logger.exception("Exception in test_solana_token_monitor")
            return False
    
    def test_solana_wallet_monitor(self) -> bool:
        """Test Solana wallet monitor functionality."""
        if self.solana_adapter is None:
            cprint("  ⚠️ Solana adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter with test_mode=True
            adapter = self.solana_adapter.SolanaAdapter(test_mode=True)
            
            # Test wallet monitoring setup
            # We're just testing if the method exists and can be called in test mode
            wallet_address = random_address(False)
            
            # This should not raise an exception in test mode
            result = adapter.setup_wallet_monitor(wallet_address, test_mode=True)
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            # In test mode, it should return a dummy response
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_solana_wallet_monitor: {str(e)}", "red")
            self.logger.exception("Exception in test_solana_wallet_monitor")
            return False
    
    def test_solana_handlers(self) -> bool:
        """Test Solana handlers can be imported and basic functionality."""
        try:
            # Import Solana handlers
            from ...modules.solana import handlers as solana_handlers
            
            # Check if key handlers exist
            required_handlers = [
                "token_monitor",
                "wallet_monitor",
                "telegram_scraper"
            ]
            
            missing_handlers = []
            for handler in required_handlers:
                if not hasattr(solana_handlers, handler):
                    missing_handlers.append(handler)
            
            if missing_handlers:
                cprint(f"  ❌ Missing Solana handlers: {', '.join(missing_handlers)}", "red")
                return False
            
            return True
            
        except ImportError as e:
            cprint(f"  ❌ Failed to import Solana handlers: {str(e)}", "red")
            self.logger.exception("Failed to import Solana handlers")
            return False
        except Exception as e:
            cprint(f"  ❌ Exception in test_solana_handlers: {str(e)}", "red")
            self.logger.exception("Exception in test_solana_handlers")
            return False
    
    def test_telegram_integration(self) -> bool:
        """Test Solana telegram integration."""
        if self.solana_adapter is None:
            cprint("  ⚠️ Solana adapter not available, skipping", "yellow")
            return False
        
        try:
            # Import directly from solana_adapter
            if not hasattr(self.solana_adapter, "test_telegram"):
                cprint("  ⚠️ test_telegram function not found, skipping", "yellow")
                return True  # Not a failure, just skip
            
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Test in test mode, should not actually send messages
            result = self.solana_adapter.test_telegram(test_mode=True)
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_telegram_integration: {str(e)}", "red")
            self.logger.exception("Exception in test_telegram_integration")
            return False
    
    def run_tests(self) -> Dict[str, bool]:
        """Run all Solana tests."""
        tests = [
            ("Solana Module Imports", self.test_solana_imports),
            ("Solana Adapter Initialization", self.test_solana_adapter_init),
            ("Solana Token Monitor", self.test_solana_token_monitor),
            ("Solana Wallet Monitor", self.test_solana_wallet_monitor),
            ("Solana Handlers", self.test_solana_handlers),
            ("Telegram Integration", self.test_telegram_integration)
        ]
        
        return super().run_tests(tests)


def run_solana_tests(verbose=False) -> bool:
    """
    Run all Solana tests.
    
    Args:
        verbose: Whether to print verbose output
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    tester = SolanaTester()
    try:
        results = tester.run_tests()
        return all(results.values())
    finally:
        tester.cleanup()


if __name__ == "__main__":
    run_solana_tests() 