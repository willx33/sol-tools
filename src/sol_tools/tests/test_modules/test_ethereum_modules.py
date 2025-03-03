"""
Test file for Ethereum modules in SOL Tools.
This tests all Ethereum modules for proper functionality.
"""

import os
import sys
import unittest
from pathlib import Path
import json
import logging
from unittest.mock import patch, MagicMock

# Import base test class for consistent testing
from sol_tools.tests.base_tester import BaseTester

# Import the Ethereum modules
from sol_tools.modules.ethereum.eth_wallet import EthWalletChecker, Config as WalletConfig
from sol_tools.modules.ethereum.eth_traders import EthTopTraders
from sol_tools.modules.ethereum.eth_scan import EthScanAllTx
from sol_tools.modules.ethereum.eth_timestamp import EthTimestampTransactions
from sol_tools.modules.ethereum.standalone_eth_wallet import (
    is_valid_eth_address,
    import_wallets_from_file
)
from sol_tools.modules.ethereum.handlers import EthWalletHandler

# Test data
TEST_WALLET = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"  # Vitalik's address
INVALID_WALLET = "not-a-wallet"
TEST_API_KEY = "test_api_key"

class TestEthereumModules(unittest.TestCase):
    """Test class for Ethereum modules."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests."""
        # Set test mode
        os.environ["TEST_MODE"] = "1"
        
        # Mock API key
        os.environ["ETHEREUM_API_KEY"] = TEST_API_KEY
        
        # Set up test directories
        cls.test_input_dir = Path("data/input-data/api/ethereum/wallets")
        cls.test_output_dir = Path("data/output-data/api/ethereum/wallet-analysis")
        
        # Create test directories
        cls.test_input_dir.mkdir(parents=True, exist_ok=True)
        cls.test_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test wallet file
        cls.test_wallet_file = cls.test_input_dir / "test_wallets.txt"
        with open(cls.test_wallet_file, "w") as f:
            f.write("0x742d35Cc6634C0532925a3b844Bc454e4438f44e\n")  # Vitalik's address
            f.write("0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B\n")  # Another well-known address
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests."""
        # Remove test files
        if cls.test_wallet_file.exists():
            cls.test_wallet_file.unlink()
        
        # Clean up test directories if empty
        try:
            cls.test_input_dir.rmdir()
            cls.test_output_dir.rmdir()
        except OSError:
            pass  # Directory not empty or already deleted
        
        # Remove environment variables
        os.environ.pop("TEST_MODE", None)
        os.environ.pop("ETHEREUM_API_KEY", None)
    
    def test_wallet_validation(self):
        """Test Ethereum address validation."""
        # Test valid address
        self.assertTrue(is_valid_eth_address(TEST_WALLET))
        
        # Test invalid addresses
        self.assertFalse(is_valid_eth_address(INVALID_WALLET))
        self.assertFalse(is_valid_eth_address("0x" + "0" * 40))  # Wrong format
        self.assertFalse(is_valid_eth_address(""))  # Empty string
    
    def test_wallet_import(self):
        """Test wallet import functionality."""
        # Test importing valid wallet file
        wallets = import_wallets_from_file(self.test_wallet_file)
        self.assertEqual(len(wallets), 2)
        self.assertEqual(wallets[0], TEST_WALLET)
        self.assertEqual(wallets[1], "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B")
        
        # Test importing non-existent file
        wallets = import_wallets_from_file("non_existent.txt")
        self.assertEqual(len(wallets), 0)
    
    def test_wallet_checker_initialization(self):
        """Test EthWalletChecker initialization."""
        checker = EthWalletChecker(test_mode=True)
        self.assertIsNotNone(checker)
        self.assertEqual(checker.threads, 10)  # Default threads
        self.assertTrue(checker.test_mode)
    
    def test_wallet_handler_initialization(self):
        """Test EthWalletHandler initialization."""
        handler = EthWalletHandler()
        self.assertIsNotNone(handler)
        self.assertTrue(handler.input_dir.exists())
        self.assertTrue(handler.output_dir.exists())
    
    def test_wallet_handler_setup(self):
        """Test EthWalletHandler setup."""
        handler = EthWalletHandler()
        self.assertTrue(handler.setup())
        
        # Test without API key
        with patch.dict(os.environ, {"ETHEREUM_API_KEY": ""}):
            handler = EthWalletHandler()
            self.assertFalse(handler.setup())
    
    @patch("aiohttp.ClientSession")
    def test_wallet_handler_run(self, mock_session):
        """Test EthWalletHandler run functionality."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "status": "1",
            "result": "1000000000000000000"  # 1 ETH in wei
        }
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        # Create handler and run
        handler = EthWalletHandler()
        self.assertTrue(handler.setup())
        
        # Test with valid wallet file
        result = handler.run("test_wallets.txt", threads=2)
        self.assertTrue(result)
        
        # Test with non-existent wallet file
        result = handler.run("non_existent.txt", threads=2)
        self.assertFalse(result)
    
    def test_logging_silenced_in_test_mode(self):
        """Test that logging is properly silenced in test mode."""
        # Create a checker in test mode
        checker = EthWalletChecker(test_mode=True)
        
        # Get the logger
        logger = logging.getLogger("sol_tools.modules.ethereum.standalone_eth_wallet")
        
        # Verify logger level is set higher than CRITICAL
        self.assertGreater(logger.level, logging.CRITICAL)
    
    def test_directory_structure(self):
        """Test that directory structure is properly maintained."""
        # Check input directory structure
        input_dir = Path("data/input-data/api/ethereum/wallets")
        self.assertTrue(input_dir.exists())
        self.assertTrue(input_dir.is_dir())
        
        # Check output directory structure
        output_dir = Path("data/output-data/api/ethereum/wallet-analysis")
        self.assertTrue(output_dir.exists())
        self.assertTrue(output_dir.is_dir())
    
    def test_config_paths(self):
        """Test configuration path handling."""
        # Test standalone mode
        config = WalletConfig()
        
        # Input directory
        input_dir = config.get_input_dir()
        self.assertTrue("ethereum/wallets" in str(input_dir))
        
        # Output directory
        output_dir = config.get_output_dir()
        self.assertTrue("ethereum/wallet-analysis" in str(output_dir))
    
    def test_error_handling(self):
        """Test error handling in the wallet checker."""
        # Test with invalid wallet
        checker = EthWalletChecker(wallets=[INVALID_WALLET], test_mode=True)
        result = checker.run()
        self.assertFalse(result)
        
        # Test with empty wallet list
        checker = EthWalletChecker(wallets=[], test_mode=True)
        result = checker.run()
        self.assertFalse(result)

    def test_input_directory_structure(self):
        """Test that input directory structure is correct."""
        # Get input directory
        input_dir = Path("data/input-data/api/ethereum/wallets")
        
        # Check directory exists
        self.assertTrue(input_dir.exists())
        self.assertTrue(input_dir.is_dir())
        
        # Check directory path contains expected components
        self.assertTrue("ethereum/wallets" in str(input_dir))


if __name__ == "__main__":
    unittest.main() 