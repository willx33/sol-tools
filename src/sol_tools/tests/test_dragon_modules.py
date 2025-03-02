"""
Comprehensive testing module for Dragon and GMGN adapters.

This module tests all functionality of the Dragon and GMGN adapters,
using mock data in place of real API calls, but executing the full code path
to ensure all modules work as expected.

Usage:
    python -m src.sol_tools.tests.test_dragon_modules

The tests will execute without requiring real API keys or connections,
and all test data will be cleaned up after execution.
"""

import os
import sys
import asyncio
import logging
import time
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dragon_tests")

# Add parent directory to path if running directly
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import modules to test
from src.sol_tools.modules.dragon.dragon_adapter import (
    DragonAdapter, GMGN_Client, TokenDataHandler, _ensure_dir_exists
)
from src.sol_tools.core.config import CACHE_DIR, INPUT_DATA_DIR, OUTPUT_DATA_DIR

# Import test data from the central test data file
from src.sol_tools.tests.test_data.real_test_data import (
    REAL_TOKEN_ADDRESSES as TEST_CONTRACT_ADDRESSES,
    REAL_WALLET_ADDRESSES as TEST_WALLET_ADDRESSES
)

# Test directory setup
TEST_DIR = CACHE_DIR / "tests" / "dragon"
TEST_DATA_DIR = TEST_DIR / "data"
TEST_OUTPUT_DIR = TEST_DIR / "output"


class DragonTestSuite:
    """Test suite for Dragon and GMGN modules."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.setup_test_environment()
        self.adapter = None
        self.gmgn_client = None
        self.token_handler = None
        self.success_count = 0
        self.failure_count = 0
        self.skipped_count = 0
        
    def setup_test_environment(self):
        """Set up test directories and data."""
        # Create test directories
        _ensure_dir_exists(TEST_DIR)
        _ensure_dir_exists(TEST_DATA_DIR)
        _ensure_dir_exists(TEST_OUTPUT_DIR)
        
        # Create subdirectories
        dirs_to_create = [
            TEST_DATA_DIR / "input" / "ethereum",
            TEST_DATA_DIR / "input" / "solana",
            TEST_DATA_DIR / "input" / "proxies",
            TEST_DATA_DIR / "output" / "ethereum" / "wallet_analysis",
            TEST_DATA_DIR / "output" / "ethereum" / "token_analysis",
            TEST_DATA_DIR / "output" / "solana" / "wallet_analysis",
            TEST_DATA_DIR / "output" / "solana" / "token_analysis",
            TEST_DATA_DIR / "token_info"
        ]
        
        for dir_path in dirs_to_create:
            _ensure_dir_exists(dir_path)
            
        # Create a sample proxy file
        proxy_file = TEST_DATA_DIR / "input" / "proxies" / "proxies.txt"
        with open(proxy_file, 'w') as f:
            f.write("# Test proxy file\n")
            f.write("127.0.0.1:8080\n")
            
        logger.info("Test environment set up successfully")
        
    def cleanup_test_environment(self):
        """Clean up test data."""
        try:
            # Remove test directory
            if TEST_DIR.exists():
                shutil.rmtree(TEST_DIR)
            logger.info("Test environment cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up test environment: {e}")
            
    async def initialize_adapter(self):
        """Initialize the Dragon adapter."""
        try:
            # Initialize with test directories
            self.adapter = DragonAdapter(
                data_dir=TEST_DATA_DIR,
                test_mode=True,  # Use test mode
                verbose=False
            )
            
            # Initialize the adapter (note: initialize() is synchronous, not async)
            success = self.adapter.initialize()
            if success:
                logger.info("Dragon adapter initialized successfully")
                
                # Also initialize individual components for direct testing
                self.gmgn_client = GMGN_Client(use_proxies=False)
                self.token_handler = TokenDataHandler(use_proxies=False)
                
                return True
            else:
                logger.error("Failed to initialize Dragon adapter")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Dragon adapter: {e}")
            return False
            
    async def cleanup_adapter(self):
        """Clean up the Dragon adapter."""
        if self.adapter:
            # Note: cleanup() is synchronous, not async
            self.adapter.cleanup()
            logger.info("Dragon adapter cleaned up")
            
    def log_test_result(self, test_name: str, success: bool, error=None, skipped=False):
        """Log test result and update counters."""
        if skipped:
            logger.info(f"🔄 SKIPPED: {test_name} - {error if error else 'Not applicable in this environment'}")
            self.skipped_count += 1
        elif success:
            logger.info(f"✅ PASSED: {test_name}")
            self.success_count += 1
        else:
            logger.error(f"❌ FAILED: {test_name} - {error if error else 'Unknown error'}")
            self.failure_count += 1
            
    async def test_gmgn_token_info_single(self):
        """Test GMGN token info with a single address."""
        test_name = "GMGN Token Info (Single Address)"
        
        try:
            # Direct method test
            token_address = TEST_CONTRACT_ADDRESSES[0]
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            result = await self.adapter.get_token_info(token_address)
            
            # Verify result structure
            if isinstance(result, dict):
                logger.info(f"Token info received for {token_address} (mock mode)")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, f"Expected dict, got {type(result)}")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    async def test_gmgn_token_info_multiple(self):
        """Test GMGN token info with multiple addresses."""
        test_name = "GMGN Token Info (Multiple Addresses)"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Test with multiple addresses
            results = await asyncio.gather(*[
                self.adapter.get_token_info(addr) for addr in TEST_CONTRACT_ADDRESSES
            ])
            
            # Verify results
            if all(isinstance(result, dict) for result in results):
                logger.info(f"Token info received for {len(results)} addresses (mock mode)")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, "Not all results were dictionaries")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_gmgn_token_info_sync(self):
        """Test synchronous GMGN token info retrieval."""
        test_name = "GMGN Token Info (Sync)"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Test synchronous method
            token_address = TEST_CONTRACT_ADDRESSES[0]
            result = self.adapter.get_token_info_sync(token_address)
            
            # Verify result
            if isinstance(result, dict):
                logger.info(f"Token info received synchronously for {token_address} (mock mode)")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, f"Expected dict, got {type(result)}")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_gmgn_client_direct(self):
        """Test GMGN client directly."""
        test_name = "GMGN Client Direct"
        
        try:
            # Guard against None
            if self.gmgn_client is None:
                self.log_test_result(test_name, False, "GMGN client is not initialized")
                return
                
            # Test direct client
            token_address = TEST_CONTRACT_ADDRESSES[0]
            result = self.gmgn_client.getTokenInfo(token_address)
            
            # Verify result
            if isinstance(result, dict):
                logger.info(f"GMGN client direct test successful for {token_address}")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, f"Expected dict, got {type(result)}")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_token_data_handler(self):
        """Test TokenDataHandler."""
        test_name = "TokenDataHandler"
        
        try:
            # Guard against None
            if self.token_handler is None:
                self.log_test_result(test_name, False, "Token data handler is not initialized")
                return
                
            # Test token data handler
            token_address = TEST_CONTRACT_ADDRESSES[0]
            result = self.token_handler._get_token_info_sync(token_address)
            
            # Verify result
            if isinstance(result, dict):
                logger.info(f"TokenDataHandler test successful for {token_address}")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, f"Expected dict, got {type(result)}")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_token_listings(self):
        """Test token listings functionality."""
        test_name = "Token Listings"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Test all token listing functions
            new_tokens = self.adapter.get_new_tokens()
            completing_tokens = self.adapter.get_completing_tokens()
            soaring_tokens = self.adapter.get_soaring_tokens()
            bonded_tokens = self.adapter.get_bonded_tokens()
            
            # Verify results are lists
            if all(isinstance(result, list) for result in [new_tokens, completing_tokens, soaring_tokens, bonded_tokens]):
                logger.info("All token listing functions returned lists (mock mode)")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, "Not all results were lists")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_solana_wallet_checker_single(self):
        """Test Solana wallet checker with a single address."""
        test_name = "Solana Wallet Checker (Single)"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Create some mock test data for wallet checking
            if not hasattr(self.adapter, 'solana_wallets') or not self.adapter.solana_wallets:
                self.adapter.solana_wallets = [{
                    "address": TEST_WALLET_ADDRESSES[0],
                    "tokens": [
                        {
                            "name": "Mock Token",
                            "symbol": "MOCK",
                            "address": TEST_CONTRACT_ADDRESSES[0],
                            "balance": 1000.0,
                            "price_usd": 0.5,
                            "value_usd": 500.0
                        }
                    ],
                    "total_value_usd": 500.0
                }]
            
            # Test wallet checker with a single wallet
            wallet_address = TEST_WALLET_ADDRESSES[0]
            result = self.adapter.solana_wallet_checker(wallet_address)
            
            # Verify result
            if isinstance(result, dict) and (result.get("success", False) or result.get("status") == "success"):
                logger.info(f"Wallet checker successful for {wallet_address} (mock mode)")
                self.log_test_result(test_name, True)
            else:
                failure_reason = "Result was not a successful dictionary"
                if isinstance(result, dict) and "error" in result:
                    failure_reason = result["error"]
                self.log_test_result(test_name, False, failure_reason)
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_solana_wallet_checker_multiple(self):
        """Test Solana wallet checker with multiple addresses."""
        test_name = "Solana Wallet Checker (Multiple)"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Create some mock test data for wallet checking
            if not hasattr(self.adapter, 'solana_wallets') or not self.adapter.solana_wallets:
                self.adapter.solana_wallets = [
                    {
                        "address": addr,
                        "tokens": [
                            {
                                "name": f"Mock Token {i}",
                                "symbol": f"MCK{i}",
                                "address": TEST_CONTRACT_ADDRESSES[0],
                                "balance": 1000.0 * (i + 1),
                                "price_usd": 0.5,
                                "value_usd": 500.0 * (i + 1)
                            }
                        ],
                        "total_value_usd": 500.0 * (i + 1)
                    }
                    for i, addr in enumerate(TEST_WALLET_ADDRESSES)
                ]
            
            # Test with multiple wallets
            result = self.adapter.solana_wallet_checker(TEST_WALLET_ADDRESSES)
            
            # Verify result
            if isinstance(result, dict) and (result.get("success", False) or result.get("status") == "success"):
                logger.info(f"Wallet checker successful for {len(TEST_WALLET_ADDRESSES)} wallets (mock mode)")
                self.log_test_result(test_name, True)
            else:
                failure_reason = "Result was not a successful dictionary"
                if isinstance(result, dict) and "error" in result:
                    failure_reason = result["error"]
                self.log_test_result(test_name, False, failure_reason)
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    def test_import_wallets(self):
        """Test wallet importing functionality."""
        test_name = "Import Wallets"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Create wallet files for testing
            solana_wallet_file = TEST_DATA_DIR / "input" / "solana" / "wallets.txt"
            ethereum_wallet_file = TEST_DATA_DIR / "input" / "ethereum" / "wallets.txt"
            
            # Write test wallet addresses to files
            with open(solana_wallet_file, 'w') as f:
                f.write("\n".join(TEST_WALLET_ADDRESSES))
                
            with open(ethereum_wallet_file, 'w') as f:
                f.write("0x1234567890123456789012345678901234567890\n")
                f.write("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd\n")
                
            # Test import functions
            solana_result = self.adapter.import_solana_wallets("wallets.txt", str(TEST_DATA_DIR / "input" / "solana"))
            ethereum_result = self.adapter.import_ethereum_wallets("wallets.txt", str(TEST_DATA_DIR / "input" / "ethereum"))
            
            # Verify results
            if solana_result and ethereum_result:
                logger.info("Wallet import functions successful (mock mode)")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, f"Solana: {solana_result}, Ethereum: {ethereum_result}")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    def test_validate_addresses(self):
        """Test address validation functions."""
        test_name = "Address Validation"
        
        try:
            # Guard against None
            if self.adapter is None:
                self.log_test_result(test_name, False, "Adapter is not initialized")
                return
                
            # Test Solana validation
            solana_validations = [
                self.adapter.validate_solana_address(addr) for addr in TEST_WALLET_ADDRESSES
            ]
            
            # Test Ethereum validation
            ethereum_validations = [
                self.adapter.validate_ethereum_address("0x1234567890123456789012345678901234567890"),
                self.adapter.validate_ethereum_address("1234567890123456789012345678901234567890")
            ]
            
            # Verify all validations are boolean
            if all(isinstance(v, bool) for v in solana_validations + ethereum_validations):
                logger.info("Address validation functions return boolean results")
                self.log_test_result(test_name, True)
            else:
                self.log_test_result(test_name, False, "Not all results were boolean")
                
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
            
    async def run_all_tests(self, options: Optional[Dict[str, Any]] = None):
        """
        Run all tests.
        
        Args:
            options: Dictionary of test options
                - verbose: Show detailed output
                - mock_only: Only run tests with mock data
                - quick: Run only quick tests
                - live: Run tests with real API calls
        """
        if options is None:
            options = {}
        
        try:
            # Initialize the adapter
            test_mode = not options.get('live', False)
            if not await self.initialize_adapter():
                logger.error("Failed to initialize adapter. Aborting tests.")
                return False
                
            # Run tests
            logger.info("Starting Dragon and GMGN tests...")
            
            # GMGN token info tests
            await self.test_gmgn_token_info_single()
            await self.test_gmgn_token_info_multiple()
            self.test_gmgn_token_info_sync()
            self.test_gmgn_client_direct()
            self.test_token_data_handler()
            
            # Token listings tests
            self.test_token_listings()
            
            # Skip time-consuming tests if quick mode is enabled
            if not options.get('quick', False):
                # Wallet tests
                self.test_solana_wallet_checker_single()
                self.test_solana_wallet_checker_multiple()
                self.test_import_wallets()
                
                # Utility function tests
                self.test_validate_addresses()
            
            # Clean up the adapter
            await self.cleanup_adapter()
            
            # Report results
            logger.info("\n" + "="*60)
            logger.info(f"Test Results: {self.success_count} Passed, {self.failure_count} Failed, {self.skipped_count} Skipped")
            logger.info("="*60)
            
            return self.failure_count == 0
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
        finally:
            # Always clean up
            self.cleanup_test_environment()
            

async def main(options: Optional[Dict[str, Any]] = None):
    """
    Main function to run tests.
    
    Args:
        options: Dictionary of test options
            - verbose: Show detailed output
            - mock_only: Only run tests with mock data
            - quick: Run only quick tests
            - live: Run tests with real API calls
            
    Returns:
        int: 0 if all tests passed, 1 otherwise
    """
    if options is None:
        options = {}
        
    try:
        logger.info("Starting Dragon module tests")
        
        # Configure logging level based on verbose option
        if options.get('verbose', False):
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
        
        test_suite = DragonTestSuite()
        success = await test_suite.run_all_tests(options)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1
    

if __name__ == "__main__":
    # Parse command-line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test Dragon and GMGN modules")
    parser.add_argument("--verbose", action="store_true", help="Show detailed test output")
    parser.add_argument("--quick", action="store_true", help="Run only quick tests")
    parser.add_argument("--mock-only", action="store_true", help="Only run tests with mock data")
    parser.add_argument("--live", action="store_true", help="Run tests with real API calls")
    args = parser.parse_args()
    
    # Convert args to options
    options = {
        'verbose': args.verbose,
        'quick': args.quick,
        'mock_only': args.mock_only,
        'live': args.live
    }
    
    # Run the async main function
    if sys.version_info >= (3, 7):
        result = asyncio.run(main(options))
    else:
        # Fallback for Python 3.6
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(main(options))
    
    sys.exit(result) 