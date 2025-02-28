"""Adapter for Dragon modules to work with the Sol Tools framework."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union

# Create a path reference to the original Dragon code
# This assumes the Dragon modules are in a specific location
# We'll need to adapt this to the actual location in the final structure
DRAGON_PATH = Path(__file__).parents[4] / "Dragon"
if str(DRAGON_PATH) not in sys.path:
    sys.path.append(str(DRAGON_PATH))

# Import Dragon modules, with fallback for missing modules
try:
    from Dragon import (
        utils, BundleFinder, ScanAllTx, BulkWalletChecker, TopTraders,
        TimestampTransactions, purgeFiles, CopyTradeWalletFinder, TopHolders,
        EarlyBuyers, checkProxyFile, EthBulkWalletChecker, EthTopTraders,
        EthTimestampTransactions, EthScanAllTx, gmgnTools, GMGN
    )
    DRAGON_IMPORTS_SUCCESS = True
except ImportError as e:
    print(f"Warning: Could not import Dragon modules: {e}")
    DRAGON_IMPORTS_SUCCESS = False


class DragonAdapter:
    """Adapter for Dragon functionality to work within Sol Tools framework."""
    
    def __init__(self, data_dir: Union[str, Path]):
        """
        Initialize the Dragon adapter.
        
        Args:
            data_dir: Path to the data directory for storing Dragon outputs
        """
        from ...core.config import OUTPUT_DATA_DIR
        self.data_dir = Path(data_dir) if data_dir else OUTPUT_DATA_DIR
        self.dragon_data_dir = self.data_dir / "dragon"
        
        # Create necessary subdirectories
        for chain in ["Solana", "Ethereum", "GMGN"]:
            for subdir in ["TopTraders", "TopHolders", "EarlyBuyers", "BulkWallet"]:
                (self.dragon_data_dir / chain / subdir).mkdir(parents=True, exist_ok=True)
        
        # Proxies directory
        (self.dragon_data_dir / "Proxies").mkdir(parents=True, exist_ok=True)
        
        # Initialize components only if imports succeeded
        if DRAGON_IMPORTS_SUCCESS:
            # Solana components
            self.bundle = BundleFinder()
            self.scan = ScanAllTx()
            self.wallet_checker = BulkWalletChecker()
            self.top_traders = TopTraders()
            self.timestamp = TimestampTransactions()
            self.copy_wallet = CopyTradeWalletFinder()
            self.top_holders = TopHolders()
            self.early_buyers = EarlyBuyers()
            
            # Ethereum components
            self.eth_wallet = EthBulkWalletChecker()
            self.eth_traders = EthTopTraders()
            self.eth_timestamp = EthTimestampTransactions()
            self.eth_scan = EthScanAllTx()
            
            # GMGN component
            self.gmgn = GMGN()
        
    def ensure_dragon_paths(self):
        """Create and return paths to match Dragon's expected directory structure."""
        # Make sure the Dragon module can find its data directories
        original_dragon_data = Path("Dragon/data")
        
        # Use symbolic links or copy directory structure as needed
        if not os.path.exists(original_dragon_data):
            os.makedirs(original_dragon_data, exist_ok=True)
            
            # Create symbolic links to our data directory
            # Note: on Windows, this might require administrator privileges
            for chain in ["Solana", "Ethereum", "GMGN", "Proxies"]:
                src = self.dragon_data_dir / chain
                dst = original_dragon_data / chain
                
                # Create the chain directory if it doesn't exist
                if not os.path.exists(dst):
                    if os.path.exists(src):
                        # Try symbolic link first
                        try:
                            os.symlink(src, dst)
                        except (OSError, NotImplementedError):
                            # Fall back to just creating the directory
                            os.makedirs(dst, exist_ok=True)
                    else:
                        os.makedirs(src, exist_ok=True)
                        os.makedirs(dst, exist_ok=True)

    def check_proxy_file(self, create_if_missing: bool = True) -> bool:
        """
        Check if proxy file exists and has content.
        
        Args:
            create_if_missing: Create an empty proxy file if it doesn't exist
            
        Returns:
            True if proxies are available, False otherwise
        """
        proxy_path = self.dragon_data_dir / "Proxies" / "proxies.txt"
        
        if not os.path.exists(proxy_path) and create_if_missing:
            # Create the directory and empty file
            os.makedirs(os.path.dirname(proxy_path), exist_ok=True)
            with open(proxy_path, 'w') as f:
                pass
                
        # Check if the file has content
        if os.path.exists(proxy_path):
            with open(proxy_path, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            return len(proxies) > 0
            
        return False
        
    def handle_threads(self, threads: Optional[int] = None) -> int:
        """
        Normalize thread count with sane defaults.
        
        Args:
            threads: Requested thread count or None for default
            
        Returns:
            Normalized thread count (40 by default, capped at 100)
        """
        try:
            threads = int(threads or 40)
            if threads > 100:
                return 40
            return threads
        except (ValueError, TypeError):
            return 40
            
    def validate_solana_address(self, address: str) -> bool:
        """
        Validate a Solana address format.
        
        Args:
            address: Solana address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        return len(address) in [43, 44]
    
    def validate_ethereum_address(self, address: str) -> bool:
        """
        Validate an Ethereum address format.
        
        Args:
            address: Ethereum address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        return len(address) in [40, 41, 42]
    
    # Solana implementations
    def solana_bundle_checker(self, contract_address: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Check for bundled transactions (multiple buys in one tx).
        
        Args:
            contract_address: Solana token contract address or list of addresses
            
        Returns:
            Dictionary with transaction data or error information
        """
        if not DRAGON_IMPORTS_SUCCESS:
            return {"success": False, "error": "Dragon modules not available"}
        
        # Convert to list if it's a string
        if isinstance(contract_address, str):
            # Support space-separated addresses in a single string
            from ...utils.common import parse_input_addresses
            addresses = parse_input_addresses(contract_address)
        else:
            addresses = contract_address
            
        if not addresses:
            return {"success": False, "error": "No valid contract address provided"}
            
        # Import and use the new process_multiple_inputs utility for consistent handling
        from ...utils.common import process_multiple_inputs
        
        # Define a processor function for each address
        def process_contract(address):
            if not self.validate_solana_address(address):
                return {
                    "success": False,
                    "error": f"Invalid Solana contract address: {address}"
                }
                
            try:
                self.ensure_dragon_paths()
                tx_hashes = self.bundle.teamTrades(address)
                data = self.bundle.checkBundle(tx_hashes[0], tx_hashes[1])
                formatted = self.bundle.prettyPrint(data, address)
                return {
                    "success": True,
                    "address": address,
                    "data": data,
                    "formatted": formatted
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "address": address
                }
                
        # Process all addresses with the utility
        results = process_multiple_inputs(
            addresses,
            process_contract,
            description="contract",
            show_progress=False  # Don't show progress here; handlers will do this
        )
        
        # Format the return value
        all_formatted = []
        for result in results.get("all_results", []):
            if result.get("success", False):
                all_formatted.append({
                    "address": result.get("address", "Unknown"),
                    "formatted": result.get("formatted", "No data")
                })
        
        # Add the formatted data to the results
        results["data"] = all_formatted
        
        return results
    
    def solana_wallet_checker(self, 
                             wallets: Union[str, List[str]], 
                             threads: Optional[int] = None,
                             skip_wallets: bool = False, 
                             use_proxies: bool = False) -> Dict[str, Any]:
        """
        Analyze PnL and win rates for multiple wallets.
        
        Args:
            wallets: List of wallet addresses or space-separated string of addresses
            threads: Number of threads to use for processing
            skip_wallets: Skip wallets with no buys in last 30 days
            use_proxies: Use proxies for API requests
            
        Returns:
            Dictionary with wallet analysis data or error information
        """
        if not DRAGON_IMPORTS_SUCCESS:
            return {"success": False, "error": "Dragon modules not available"}
            
        # Handle string input (space-separated)
        if isinstance(wallets, str):
            from ...utils.common import parse_input_addresses
            wallet_list = parse_input_addresses(wallets)
        else:
            wallet_list = wallets
            
        if not wallet_list:
            return {"success": False, "error": "No wallet addresses provided"}
            
        # Validate all wallets
        from ...utils.common import validate_addresses
        valid_wallets, invalid_wallets = validate_addresses(wallet_list, self.validate_solana_address)
        
        if invalid_wallets:
            return {
                "success": False, 
                "error": f"Invalid wallet addresses provided: {', '.join(invalid_wallets[:5])}" + 
                         (f" and {len(invalid_wallets) - 5} more" if len(invalid_wallets) > 5 else "")
            }
            
        try:
            self.ensure_dragon_paths()
            threads = self.handle_threads(threads)
            
            # Check proxies if requested
            if use_proxies and not self.check_proxy_file():
                return {"success": False, "error": "Proxy file empty or not found"}
                
            data = self.wallet_checker.fetchWalletData(
                valid_wallets, 
                threads=threads,
                skipWallets=skip_wallets,
                useProxies=use_proxies
            )
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Add similar implementations for other Dragon functionality