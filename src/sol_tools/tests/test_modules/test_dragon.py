"""
Test Dragon module functionality.

This module tests the Dragon module's functionality with mock data.
"""

import os
import sys
import json
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...tests.base_tester import BaseTester, cprint
from ...tests.test_data.mock_data import (
    generate_solana_wallet_list,
    generate_ethereum_wallet_list,
    random_address
)

class DragonTester(BaseTester):
    """Test Dragon module functionality with mock data."""
    
    def __init__(self):
        """Initialize the DragonTester."""
        super().__init__("Dragon")
        
        # Create Dragon test directories
        self._create_dragon_directories()
        
        # Create test data
        self._create_test_data()
        
        # Dragon module references
        self.dragon_adapter = None
        self.gmgn_module = None
        
        # Attempt to import Dragon modules
        self._try_import_dragon()
    
    def _create_dragon_directories(self) -> None:
        """Create Dragon-specific test directories."""
        # Create Dragon directories
        (self.test_root / "input-data" / "solana" / "wallet-lists").mkdir(parents=True, exist_ok=True)
        (self.test_root / "input-data" / "ethereum" / "wallet-lists").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "dragon").mkdir(parents=True, exist_ok=True)
    
    def _create_test_data(self) -> None:
        """Create test data for Dragon tests."""
        # Create Solana test wallets
        self.solana_wallets = generate_solana_wallet_list(10)
        self.solana_wallets_file = self.test_root / "input-data" / "solana" / "wallet-lists" / "test_wallets.json"
        
        with open(self.solana_wallets_file, "w") as f:
            json.dump(self.solana_wallets, f, indent=2)
        
        # Create Ethereum test wallets
        self.ethereum_wallets = generate_ethereum_wallet_list(10)
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
            # Try to import the Dragon adapter
            from ...modules.dragon import dragon_adapter
            self.dragon_adapter = dragon_adapter
            
            # Try to import the GMGN module
            try:
                from ...modules.gmgn import gmgn_adapter
                self.gmgn_module = gmgn_adapter
            except ImportError:
                cprint("  ⚠️ Failed to import GMGN module, some tests will be skipped", "yellow")
            
            return True
            
        except ImportError as e:
            cprint(f"  ⚠️ Failed to import Dragon module: {str(e)}", "yellow")
            self.logger.warning(f"Failed to import Dragon module: {str(e)}")
            return False
    
    def test_dragon_imports(self) -> bool:
        """Test if Dragon modules can be imported."""
        if self.dragon_adapter is None:
            cprint("  ❌ Dragon adapter module could not be imported", "red")
            return False
        
        cprint("  ✓ Dragon adapter module imported successfully", "green")
        return True
    
    def test_dragon_solana_import(self) -> bool:
        """Test importing Solana wallets into Dragon."""
        if self.dragon_adapter is None:
            cprint("  ⚠️ Dragon adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter
            adapter = self.dragon_adapter.DragonAdapter(test_mode=True)
            
            # Import the test wallet file
            filename = self.solana_wallets_file.name
            directory = self.solana_wallets_file.parent
            
            result = adapter.import_solana_wallets(filename, str(directory))
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            if not result:
                cprint("  ❌ Failed to import Solana wallets", "red")
                return False
            
            # Check if data was saved properly
            try:
                # For test mode, this should be in memory only
                wallet_count = len(adapter.solana_wallets)
                if wallet_count != len(self.solana_wallets):
                    cprint(f"  ❌ Expected {len(self.solana_wallets)} wallets but got {wallet_count}", "red")
                    return False
            except:
                cprint("  ❌ Failed to access imported Solana wallets", "red")
                self.logger.exception("Failed to access imported Solana wallets")
                return False
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_dragon_solana_import: {str(e)}", "red")
            self.logger.exception("Exception in test_dragon_solana_import")
            return False
    
    def test_dragon_ethereum_import(self) -> bool:
        """Test importing Ethereum wallets into Dragon."""
        if self.dragon_adapter is None:
            cprint("  ⚠️ Dragon adapter not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter
            adapter = self.dragon_adapter.DragonAdapter(test_mode=True)
            
            # Import the test wallet file
            filename = self.ethereum_wallets_file.name
            directory = self.ethereum_wallets_file.parent
            
            result = adapter.import_ethereum_wallets(filename, str(directory))
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            if not result:
                cprint("  ❌ Failed to import Ethereum wallets", "red")
                return False
            
            # Check if data was saved properly
            try:
                # For test mode, this should be in memory only
                wallet_count = len(adapter.ethereum_wallets)
                if wallet_count != len(self.ethereum_wallets):
                    cprint(f"  ❌ Expected {len(self.ethereum_wallets)} wallets but got {wallet_count}", "red")
                    return False
            except:
                cprint("  ❌ Failed to access imported Ethereum wallets", "red")
                self.logger.exception("Failed to access imported Ethereum wallets")
                return False
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_dragon_ethereum_import: {str(e)}", "red")
            self.logger.exception("Exception in test_dragon_ethereum_import")
            return False
    
    def test_gmgn_token_adapter(self) -> bool:
        """Test GMGN token functionality."""
        if self.gmgn_module is None:
            cprint("  ⚠️ GMGN module not available, skipping", "yellow")
            return False
        
        try:
            # Set the environment before testing
            original_data_dir = os.environ.get("SOL_TOOLS_DATA_DIR", "")
            os.environ["SOL_TOOLS_DATA_DIR"] = str(self.test_root)
            
            # Create a test adapter
            adapter = self.gmgn_module.GMGNAdapter(test_mode=True)
            
            # Test adapter initialization
            if not hasattr(adapter, "token_info"):
                cprint("  ❌ GMGN adapter failed to initialize token_info", "red")
                return False
            
            # Restore original environment
            if original_data_dir:
                os.environ["SOL_TOOLS_DATA_DIR"] = original_data_dir
            else:
                os.environ.pop("SOL_TOOLS_DATA_DIR", None)
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_gmgn_token_adapter: {str(e)}", "red")
            self.logger.exception("Exception in test_gmgn_token_adapter")
            return False
    
    def test_dragon_handlers(self) -> bool:
        """Test Dragon handlers can be imported."""
        try:
            # Import Dragon handlers
            from ...modules.dragon import handlers as dragon_handlers
            
            # Check if key handlers exist
            required_handlers = [
                "solana_bundle_checker",
                "solana_wallet_checker",
                "solana_top_traders",
                "solana_scan_tx"
            ]
            
            missing_handlers = []
            for handler in required_handlers:
                if not hasattr(dragon_handlers, handler):
                    missing_handlers.append(handler)
            
            if missing_handlers:
                cprint(f"  ❌ Missing Dragon handlers: {', '.join(missing_handlers)}", "red")
                return False
            
            return True
            
        except ImportError as e:
            cprint(f"  ❌ Failed to import Dragon handlers: {str(e)}", "red")
            self.logger.exception("Failed to import Dragon handlers")
            return False
        except Exception as e:
            cprint(f"  ❌ Exception in test_dragon_handlers: {str(e)}", "red")
            self.logger.exception("Exception in test_dragon_handlers")
            return False
    
    def run_tests(self) -> Dict[str, bool]:
        """Run all Dragon tests."""
        tests = [
            ("Dragon Module Imports", self.test_dragon_imports),
            ("Dragon Solana Import", self.test_dragon_solana_import),
            ("Dragon Ethereum Import", self.test_dragon_ethereum_import),
            ("GMGN Token Adapter", self.test_gmgn_token_adapter),
            ("Dragon Handlers", self.test_dragon_handlers)
        ]
        
        return super().run_tests(tests)


def run_dragon_tests() -> bool:
    """Run all Dragon tests."""
    tester = DragonTester()
    try:
        results = tester.run_tests()
        return all(results.values())
    finally:
        tester.cleanup()


if __name__ == "__main__":
    run_dragon_tests() 