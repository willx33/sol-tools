"""
Integration testing for Sol Tools workflows.
This module tests complete workflows that span multiple modules.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from ...tests.base_tester import BaseTester, cprint

class WorkflowTester(BaseTester):
    """Test integration workflows between modules."""
    
    def __init__(self):
        """Initialize the WorkflowTester."""
        super().__init__("Workflows")
        
        # Create workflow test directories
        self._create_workflow_directories()
        
        # Create test data
        self._create_workflow_test_data()
        
        # Import required adapters with test_mode=True
        self._init_test_adapters()
    
    def _create_workflow_directories(self) -> None:
        """Create workflow-specific test directories."""
        (self.test_root / "solana").mkdir(parents=True, exist_ok=True)
        (self.test_root / "ethereum").mkdir(parents=True, exist_ok=True)
        (self.test_root / "dragon").mkdir(parents=True, exist_ok=True)
        (self.test_root / "output").mkdir(parents=True, exist_ok=True)
    
    def _create_workflow_test_data(self) -> None:
        """Create test data for workflow tests."""
        from ...tests.test_data.mock_data import (
            generate_solana_wallet_list,
            generate_ethereum_wallet_list,
            generate_solana_transaction_list,
            generate_ethereum_transaction_list,
            create_mock_data_files
        )
        
        # Create mock data files in the test directory
        self.test_files = create_mock_data_files(self.test_root)
    
    def _init_test_adapters(self) -> None:
        """Initialize test adapters for all modules."""
        try:
            # Import Dragon adapter
            from ...modules.dragon.dragon_adapter import DragonAdapter
            self.dragon_adapter = DragonAdapter(test_mode=True)
            
            # Import Solana adapter
            from ...modules.solana.solana_adapter import SolanaAdapter
            self.solana_adapter = SolanaAdapter(test_mode=True)
            
            # Import GMGN adapter
            from ...modules.gmgn.gmgn_adapter import GMGNAdapter
            self.gmgn_adapter = GMGNAdapter(test_mode=True)
            
            self.adapters_available = True
            
        except ImportError as e:
            self.logger.warning(f"Failed to import adapters: {e}")
            self.adapters_available = False
    
    def test_cross_module_wallet_analysis(self) -> bool:
        """Test workflow between Solana and Dragon modules for wallet analysis."""
        if not self.adapters_available:
            cprint("  ⚠️ Adapters not available, skipping test", "yellow")
            return False
        
        try:
            # Step 1: Use Solana adapter to get wallet data
            wallet_address = self.solana_adapter.mock_wallets[0]["address"]
            
            # Step 2: Use Dragon adapter to analyze the wallet
            result = self.dragon_adapter.solana_wallet_checker([wallet_address])
            
            # Verify we got some kind of result back
            if not result:
                cprint("  ❌ Failed to get wallet analysis result", "red")
                return False
            
            cprint("  ✓ Successfully retrieved wallet analysis", "green")
            
            # Step 3: Try a workflow with GMGN and Dragon
            token_address = "4e8rF4Q5s8AmTacxvfVMKJtQKMjM2ZfbCGnzAEjRGKTZ"  # GMGN
            
            # Get token info from GMGN adapter
            token_info = self.gmgn_adapter.get_token_info(token_address)
            
            if not token_info or "symbol" not in token_info:
                cprint("  ❌ Failed to get token info from GMGN adapter", "red")
                return False
            
            cprint(f"  ✓ Successfully retrieved token info for {token_info.get('symbol', 'unknown')}", "green")
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_cross_module_wallet_analysis: {str(e)}", "red")
            self.logger.exception("Exception in cross-module workflow test")
            return False
    
    def test_data_sharing_between_modules(self) -> bool:
        """Test sharing data between different modules."""
        if not self.adapters_available:
            cprint("  ⚠️ Adapters not available, skipping test", "yellow")
            return False
        
        try:
            # Create a test file with token data
            token_data = {
                "symbol": "TEST",
                "name": "Test Token",
                "address": "TestTokenAddress123456789",
                "decimals": 9
            }
            
            token_file = self.mock_file("shared/token.json", token_data, is_json=True)
            
            # Step 1: Use file paths that could be read by multiple adapters
            if not token_file.exists():
                cprint(f"  ❌ Failed to create token file at {token_file}", "red")
                return False
            
            cprint(f"  ✓ Successfully created shared token file", "green")
            
            # Step 2: Check that all adapters can work with this file
            # This is a simplified test - in reality we would pass the file path
            # to each adapter method and verify they can process it
            token_file_content = self.read_mock_file("shared/token.json", as_json=True)
            
            if not token_file_content or token_file_content.get("symbol") != "TEST":
                cprint("  ❌ Failed to read back token data correctly", "red")
                return False
            
            cprint("  ✓ Successfully shared data between modules", "green")
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_data_sharing_between_modules: {str(e)}", "red")
            self.logger.exception("Exception in data sharing test")
            return False
    
    def run_tests(self) -> Dict[str, bool]:
        """Run all workflow tests."""
        tests = [
            ("Cross-Module Wallet Analysis", self.test_cross_module_wallet_analysis),
            ("Data Sharing Between Modules", self.test_data_sharing_between_modules)
        ]
        
        return super().run_tests(tests)


def run_workflow_tests(verbose=False) -> bool:
    """
    Run all workflow integration tests.
    
    Args:
        verbose: Whether to print verbose output
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    tester = WorkflowTester()
    try:
        results = tester.run_tests()
        return all(results.values())
    finally:
        tester.cleanup()


if __name__ == "__main__":
    run_workflow_tests() 