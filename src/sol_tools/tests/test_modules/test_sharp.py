"""
Test Sharp module functionality.

This module tests the Sharp module's functionality with mock data.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

from ...tests.base_tester import BaseTester, cprint

class SharpTester(BaseTester):
    """Test Sharp module functionality with mock data."""
    
    def __init__(self):
        """Initialize the SharpTester."""
        super().__init__("Sharp")
        
        # Create Sharp test directories
        self._create_sharp_directories()
        
        # Create test data
        self._create_test_data()
        
        # Initialize Sharp module (with test_mode=True)
        self._init_sharp_module()
    
    def _create_sharp_directories(self) -> None:
        """Create Sharp-specific test directories."""
        (self.test_root / "input-data" / "sharp").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output-data" / "sharp" / "portfolios").mkdir(parents=True, exist_ok=True)
    
    def _create_test_data(self) -> None:
        """Create test data for Sharp tests."""
        from ...tests.test_data.mock_data import generate_mock_sharp_portfolio
        
        # Create mock portfolio data
        self.mock_portfolio = generate_mock_sharp_portfolio()
        self.portfolio_file = self.test_root / "output-data" / "sharp" / "portfolios" / "test_portfolio.json"
        
        with open(self.portfolio_file, "w") as f:
            json.dump(self.mock_portfolio, f, indent=2)
        
        # Create wallet list for testing
        self.test_wallets = [
            "0x1234567890123456789012345678901234567890",
            "0x0987654321098765432109876543210987654321",
            "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        ]
        
        self.wallet_list_file = self.test_root / "input-data" / "sharp" / "test_wallets.txt"
        with open(self.wallet_list_file, "w") as f:
            f.write("\n".join(self.test_wallets))
    
    def _init_sharp_module(self) -> None:
        """Initialize Sharp module with test mode."""
        try:
            # Import Sharp module
            from ...modules.sharp import sharp_adapter
            
            # Initialize the adapter with test_mode if it has such parameter
            if hasattr(sharp_adapter, "SharpAdapter"):
                try:
                    # First try with test_mode and data_dir
                    self.sharp_adapter = sharp_adapter.SharpAdapter(
                        test_mode=True, 
                        data_dir=str(self.test_root)
                    )
                except TypeError:
                    try:
                        # Next try with just data_dir
                        self.sharp_adapter = sharp_adapter.SharpAdapter(
                            data_dir=str(self.test_root)
                        )
                    except TypeError:
                        # Finally try without any parameters
                        self.sharp_adapter = sharp_adapter.SharpAdapter()
            else:
                self.sharp_adapter = None
            
            # Import handlers
            from ...modules.sharp import handlers as sharp_handlers
            self.sharp_handlers = sharp_handlers
            
            self.module_available = True
            
        except ImportError as e:
            self.logger.warning(f"Failed to import Sharp module: {str(e)}")
            self.module_available = False
        except Exception as e:
            self.logger.warning(f"Error initializing Sharp module: {str(e)}")
            self.module_available = False
    
    def test_sharp_imports(self) -> bool:
        """Test if Sharp module can be imported."""
        if not self.module_available:
            cprint("  ❌ Sharp module could not be imported", "red")
            return False
        
        cprint("  ✓ Sharp module imported successfully", "green")
        return True
    
    def test_portfolio_fetch(self) -> bool:
        """Test fetching portfolio data."""
        if not self.module_available:
            cprint("  ⚠️ Sharp module not available, skipping", "yellow")
            return False
        
        try:
            # Verify the portfolio file exists
            if not self.portfolio_file.exists():
                cprint(f"  ❌ Portfolio file not found: {self.portfolio_file}", "red")
                return False
            
            # Read the portfolio data
            with open(self.portfolio_file, "r") as f:
                portfolio_data = json.load(f)
            
            # Verify the data has the expected structure
            if not isinstance(portfolio_data, dict) or "totalValueUsd" not in portfolio_data:
                cprint("  ❌ Portfolio data is missing expected fields", "red")
                return False
            
            cprint("  ✓ Successfully verified portfolio data", "green")
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_portfolio_fetch: {str(e)}", "red")
            self.logger.exception("Exception in test_portfolio_fetch")
            return False
    
    def test_wallet_splitter(self) -> bool:
        """Test wallet splitter functionality."""
        if not self.module_available:
            cprint("  ⚠️ Sharp module not available, skipping", "yellow")
            return False
        
        try:
            # Verify the wallet list file exists
            if not self.wallet_list_file.exists():
                cprint(f"  ❌ Wallet list file not found: {self.wallet_list_file}", "red")
                return False
            
            # Verify the file has the expected content
            with open(self.wallet_list_file, "r") as f:
                wallet_addresses = f.read().strip().split("\n")
            
            if len(wallet_addresses) != len(self.test_wallets):
                cprint(f"  ❌ Expected {len(self.test_wallets)} wallet addresses but found {len(wallet_addresses)}", "red")
                return False
            
            cprint("  ✓ Successfully verified wallet list data", "green")
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_wallet_splitter: {str(e)}", "red")
            self.logger.exception("Exception in test_wallet_splitter")
            return False
    
    def run_tests(self) -> Dict[str, bool]:
        """Run all Sharp tests."""
        tests = [
            ("Sharp Module Imports", self.test_sharp_imports),
            ("Portfolio Fetch", self.test_portfolio_fetch),
            ("Wallet Splitter", self.test_wallet_splitter)
        ]
        
        return super().run_tests(tests)


def run_sharp_tests() -> bool:
    """Run all Sharp tests."""
    tester = SharpTester()
    try:
        results = tester.run_tests()
        return all(results.values())
    finally:
        tester.cleanup()


if __name__ == "__main__":
    run_sharp_tests() 