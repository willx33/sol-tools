"""
Comprehensive test module for Dragon functionality.
Tests all Dragon modules with mock data without storing permanent records.
"""

import os
import sys
import time
import json
import tempfile
import importlib
import unittest
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Tuple

# Use these color codes for test output
COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "bold": "\033[1m",
    "end": "\033[0m"
}

def cprint(message: str, color: str = None) -> None:
    """Print colored text to the console."""
    if color and color in COLORS:
        print(f"{COLORS[color]}{message}{COLORS['end']}")
    else:
        print(message)

class DragonTester:
    """Tests Dragon module functionality with mock data."""
    
    def __init__(self):
        """Set up the tester with temporary directories."""
        # Create temp directories for testing
        self.test_root = Path(tempfile.mkdtemp(prefix="dragon_test_"))
        self.test_input = self.test_root / "input-data" / "dragon"
        self.test_output = self.test_root / "output-data" / "dragon"
        
        # Create necessary subdirectories
        (self.test_input / "ethereum" / "wallet_lists").mkdir(parents=True, exist_ok=True)
        (self.test_input / "solana" / "wallet_lists").mkdir(parents=True, exist_ok=True)
        (self.test_input / "proxies").mkdir(parents=True, exist_ok=True)
        
        (self.test_output / "ethereum" / "wallet_analysis").mkdir(parents=True, exist_ok=True)
        (self.test_output / "ethereum" / "top_traders").mkdir(parents=True, exist_ok=True)
        (self.test_output / "ethereum" / "top_holders").mkdir(parents=True, exist_ok=True)
        (self.test_output / "ethereum" / "early_buyers").mkdir(parents=True, exist_ok=True)
        
        (self.test_output / "solana" / "wallet_analysis").mkdir(parents=True, exist_ok=True)
        (self.test_output / "solana" / "top_traders").mkdir(parents=True, exist_ok=True)
        (self.test_output / "solana" / "top_holders").mkdir(parents=True, exist_ok=True)
        (self.test_output / "solana" / "early_buyers").mkdir(parents=True, exist_ok=True)
        
        (self.test_output / "token_info").mkdir(parents=True, exist_ok=True)
        
        # Add test data
        self.create_test_data()
        
        # Create test logger
        self.logger = logging.getLogger("dragon_test")
        self.logger.setLevel(logging.INFO)
        
        # Initialize component test status
        self.test_results = {}
    
    def create_test_data(self):
        """Create test data files for testing."""
        # Create Solana wallets test file
        with open(self.test_input / "solana" / "wallet_lists" / "wallets.txt", "w") as f:
            f.write("AA1XnMJ9HnqVqXLG73icxKU9AUfbMTe9a19isUWtw2JZ\n")
            f.write("DdzFFzCqrhsrKfA7gdVfBUwnfQGwRVy4NwgLzJi2KJKt\n")
            f.write("5aMTYWBtgESM1JJRBqPchhMDzvkfHKcNvr1ByuBmkwnJ\n")
        
        # Create Ethereum wallets test file
        with open(self.test_input / "ethereum" / "wallet_lists" / "wallets.txt", "w") as f:
            f.write("0x742d35Cc6634C0532925a3b844Bc454e4438f44e\n")
            f.write("0xdAC17F958D2ee523a2206206994597C13D831ec7\n")
            f.write("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48\n")
        
        # Create proxies test file
        with open(self.test_input / "proxies" / "proxies.txt", "w") as f:
            f.write("127.0.0.1:8080\n")
            f.write("127.0.0.1:8081:user:pass\n")
        
    def cleanup(self):
        """Clean up all test directories and files."""
        import shutil
        try:
            if self.test_root.exists():
                shutil.rmtree(self.test_root)
            cprint(f"✓ Test directories cleaned up successfully", "green")
        except Exception as e:
            cprint(f"✗ Error cleaning up test directories: {e}", "red")

    def _run_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """Run a test function and record the result."""
        try:
            cprint(f"\n▶ Testing {test_name}...", "cyan")
            result = test_func(*args, **kwargs)
            if result:
                cprint(f"✓ {test_name} passed", "green")
                self.test_results[test_name] = True
                return True
            else:
                cprint(f"✗ {test_name} failed", "red")
                self.test_results[test_name] = False
                return False
        except Exception as e:
            cprint(f"✗ {test_name} failed with error: {e}", "red")
            self.test_results[test_name] = False
            return False

    def test_dragon_module_imports(self) -> bool:
        """Test if Dragon modules can be imported."""
        try:
            # Try importing Dragon module
            import Dragon
            
            # Try importing key components
            from Dragon import GMGN
            from Dragon import utils
            from Dragon import BundleFinder
            from Dragon import TopTraders
            
            # Verify they're the expected types
            assert hasattr(GMGN, 'getTokenInfo'), "GMGN class does not have expected method"
            
            # Create an instance of GMGN class
            gmgn = GMGN()
            assert gmgn is not None, "Could not instantiate GMGN class"
            
            cprint("✓ All Dragon modules imported successfully", "green")
            return True
        except ImportError as e:
            cprint(f"✗ Dragon module import failed: {e}", "red")
            return False
        except AssertionError as e:
            cprint(f"✗ Dragon module validation failed: {e}", "red")
            return False
        except Exception as e:
            cprint(f"✗ Dragon module testing failed with unexpected error: {e}", "red")
            return False

    def test_dragon_adapter(self) -> bool:
        """Test creating a DragonAdapter instance and initializing components."""
        try:
            from sol_tools.modules.dragon.dragon_adapter import DragonAdapter
            
            # Create adapter with test directories
            adapter = DragonAdapter(data_dir=self.test_root)
            
            # Ensure all required attributes are present
            required_attrs = [
                'input_data_dir', 'output_data_dir', 'ethereum_input_dir', 
                'solana_input_dir', 'proxies_dir', 'ethereum_output_dirs',
                'solana_output_dirs', 'token_info_dir'
            ]
            
            for attr in required_attrs:
                assert hasattr(adapter, attr), f"DragonAdapter missing required attribute: {attr}"
            
            # Test the directory structure was created correctly
            adapter.ensure_dragon_paths()
            
            # Test some basic methods
            assert adapter.check_proxy_file(create_if_missing=True) is not None
            assert adapter.handle_threads(40) == 40
            assert adapter.validate_solana_address("AA1XnMJ9HnqVqXLG73icxKU9AUfbMTe9a19isUWtw2JZ") is True
            assert adapter.validate_ethereum_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e") is True
            
            cprint("✓ DragonAdapter initialized and basic methods verified", "green")
            return True
        except ImportError as e:
            cprint(f"✗ DragonAdapter import failed: {e}", "red")
            return False
        except AssertionError as e:
            cprint(f"✗ DragonAdapter validation failed: {e}", "red")
            return False
        except Exception as e:
            cprint(f"✗ DragonAdapter testing failed with unexpected error: {e}", "red")
            return False

    def test_gmgn_functionality(self) -> bool:
        """Test GMGN token functionality."""
        try:
            # Test GMGN client directly
            from sol_tools.modules.dragon.dragon_adapter import GMGN_Client
            
            # Create a client
            client = GMGN_Client(use_proxies=False)
            
            # Test session initialization
            client.randomize_session()
            assert client.session is not None, "Failed to initialize TLS session"
            
            # Test getting token info
            token_addr = "So11111111111111111111111111111111111111112"  # SOL wrapped token
            
            # Test token info functionality
            response = client.getTokenInfo(token_addr)
            # We just need it to not crash, actual data might be dummy values in test
            assert isinstance(response, dict), "Token info response is not a dictionary"
            
            # Test token listing methods
            list_methods = [
                'getNewTokens', 'getCompletingTokens', 'getSoaringTokens', 'getBondedTokens'
            ]
            
            for method_name in list_methods:
                method = getattr(client, method_name)
                result = method()
                assert isinstance(result, list), f"{method_name} did not return a list"
            
            # Test TokenDataHandler
            from sol_tools.modules.dragon.dragon_adapter import TokenDataHandler
            handler = TokenDataHandler(use_proxies=False)
            
            # Test sync method
            token_data = handler._get_token_info_sync(token_addr)
            assert isinstance(token_data, dict), "Token data sync method failed"
            
            cprint("✓ GMGN client and token handling functionality tested successfully", "green")
            return True
            
        except ImportError as e:
            cprint(f"✗ GMGN module import failed: {e}", "red")
            return False
        except AssertionError as e:
            cprint(f"✗ GMGN functionality validation failed: {e}", "red")
            return False
        except Exception as e:
            cprint(f"✗ GMGN testing failed with unexpected error: {e}", "red")
            return False

    def test_dragon_handlers(self) -> bool:
        """Test Dragon handlers module."""
        try:
            # Import handlers module
            from sol_tools.modules.dragon import handlers
            
            # Check if core handler functions exist
            handler_funcs = [
                'solana_bundle_checker', 'solana_wallet_checker', 'solana_top_traders',
                'solana_scan_tx', 'solana_copy_wallet_finder', 'solana_top_holders',
                'solana_early_buyers', 'eth_wallet_checker', 'eth_top_traders',
                'eth_scan_tx', 'eth_timestamp', 'gmgn_token_info',
                'gmgn_new_tokens', 'gmgn_completing_tokens', 'gmgn_soaring_tokens',
                'gmgn_bonded_tokens'
            ]
            
            for func_name in handler_funcs:
                assert hasattr(handlers, func_name), f"Handlers module missing function: {func_name}"
                assert callable(getattr(handlers, func_name)), f"Handler {func_name} is not callable"
            
            # Note: We don't actually call the handlers here as they would
            # try to interact with the full application environment
            
            cprint("✓ Dragon handlers module verified", "green")
            return True
        
        except ImportError as e:
            cprint(f"✗ Dragon handlers import failed: {e}", "red")
            return False
        except AssertionError as e:
            cprint(f"✗ Dragon handlers validation failed: {e}", "red")
            return False
        except Exception as e:
            cprint(f"✗ Dragon handlers testing failed with unexpected error: {e}", "red")
            return False

    def test_dragon_integration(self) -> bool:
        """Test Dragon integration with other modules."""
        try:
            # Check integration with solana module
            from sol_tools.modules.solana import handlers as solana_handlers
            
            # Verify dragon handler methods exist in solana module
            dragon_integration_funcs = [
                'dragon_solana_bundle', 'dragon_solana_wallet', 'dragon_solana_traders',
                'dragon_solana_scan', 'dragon_solana_copy', 'dragon_solana_holders',
                'dragon_solana_buyers'
            ]
            
            for func_name in dragon_integration_funcs:
                assert hasattr(solana_handlers, func_name), f"Solana handlers missing Dragon integration: {func_name}"
                assert callable(getattr(solana_handlers, func_name)), f"Solana Dragon handler {func_name} is not callable"
            
            # Check if solana adapter properly initializes dragon
            from sol_tools.modules.solana.solana_adapter import SolanaAdapter
            
            # Create test adapter
            adapter = SolanaAdapter(data_dir=self.test_root)
            
            # Verify dragon integration
            assert hasattr(adapter, 'dragon_available'), "SolanaAdapter missing dragon_available flag"
            
            # Test gmgn integration with other modules
            from sol_tools.modules.gmgn import handlers as gmgn_handlers
            assert hasattr(gmgn_handlers, 'fetch_mcap_data_handler'), "GMGN handler missing expected method"
            
            cprint("✓ Dragon integration with other modules verified", "green")
            return True
            
        except ImportError as e:
            cprint(f"✗ Dragon integration import failed: {e}", "red")
            return False
        except AssertionError as e:
            cprint(f"✗ Dragon integration validation failed: {e}", "red")
            return False
        except Exception as e:
            cprint(f"✗ Dragon integration testing failed with unexpected error: {e}", "red")
            return False

    def test_path_structure(self) -> bool:
        """Test path structure expected by Dragon modules."""
        try:
            # Verify the data directory structure
            from sol_tools.core.config import INPUT_DATA_DIR, OUTPUT_DATA_DIR
            
            # Check if the directory variables are defined
            assert INPUT_DATA_DIR is not None, "INPUT_DATA_DIR is not defined"
            assert OUTPUT_DATA_DIR is not None, "OUTPUT_DATA_DIR is not defined"
            
            # Verify these paths actually exist
            assert INPUT_DATA_DIR.exists(), "INPUT_DATA_DIR does not exist"
            assert OUTPUT_DATA_DIR.exists(), "OUTPUT_DATA_DIR does not exist"
            
            # Verify required dragon subdirectories exist
            required_input_dirs = [
                INPUT_DATA_DIR / "dragon" / "ethereum" / "wallet_lists",
                INPUT_DATA_DIR / "dragon" / "solana" / "wallet_lists",
                INPUT_DATA_DIR / "dragon" / "proxies"
            ]
            
            required_output_dirs = [
                OUTPUT_DATA_DIR / "dragon" / "ethereum" / "wallet_analysis",
                OUTPUT_DATA_DIR / "dragon" / "ethereum" / "top_traders",
                OUTPUT_DATA_DIR / "dragon" / "ethereum" / "top_holders",
                OUTPUT_DATA_DIR / "dragon" / "ethereum" / "early_buyers",
                OUTPUT_DATA_DIR / "dragon" / "solana" / "wallet_analysis",
                OUTPUT_DATA_DIR / "dragon" / "solana" / "top_traders",
                OUTPUT_DATA_DIR / "dragon" / "solana" / "top_holders",
                OUTPUT_DATA_DIR / "dragon" / "solana" / "early_buyers",
                OUTPUT_DATA_DIR / "dragon" / "token_info"
            ]
            
            for dir_path in required_input_dirs:
                assert dir_path.exists(), f"Required input directory does not exist: {dir_path}"
                
            for dir_path in required_output_dirs:
                assert dir_path.exists(), f"Required output directory does not exist: {dir_path}"
            
            # Verify placeholder files exist
            assert (INPUT_DATA_DIR / "dragon" / "proxies" / "proxies.txt").exists(), "proxies.txt not found"
            
            cprint("✓ Dragon directory structure verified", "green")
            return True
            
        except ImportError as e:
            cprint(f"✗ Path structure import failed: {e}", "red")
            return False
        except AssertionError as e:
            cprint(f"✗ Path structure validation failed: {e}", "red")
            return False
        except Exception as e:
            cprint(f"✗ Path structure testing failed with unexpected error: {e}", "red")
            return False

    def run_tests(self) -> bool:
        """Run all tests and return overall success status."""
        try:
            cprint("\n🧪 Running comprehensive Dragon module tests...", "cyan")
            
            # Run all test functions
            tests = [
                ("Dragon Module Imports", self.test_dragon_module_imports),
                ("Dragon Adapter", self.test_dragon_adapter),
                ("GMGN Functionality", self.test_gmgn_functionality),
                ("Dragon Handlers", self.test_dragon_handlers),
                ("Dragon Integration", self.test_dragon_integration),
                ("Directory Structure", self.test_path_structure)
            ]
            
            tests_passed = 0
            total_tests = len(tests)
            
            for test_name, test_func in tests:
                if self._run_test(test_name, test_func):
                    tests_passed += 1
            
            # Print summary
            cprint(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed", "bold")
            
            for test_name, result in self.test_results.items():
                color = "green" if result else "red"
                symbol = "✓" if result else "✗"
                cprint(f"{symbol} {test_name}", color)
            
            if tests_passed == total_tests:
                cprint("\n✅ All Dragon module tests passed!", "green")
                return True
            else:
                cprint(f"\n⚠️ {total_tests - tests_passed} tests failed", "yellow")
                return False
            
        finally:
            # Always clean up temporary files
            self.cleanup()

def run_dragon_tests():
    """Run all Dragon module tests and return success status."""
    tester = DragonTester()
    return tester.run_tests()

if __name__ == "__main__":
    success = run_dragon_tests()
    sys.exit(0 if success else 1)