"""
Handler module for Ethereum functionality in Sol Tools.
This module integrates the standalone implementations with the Sol Tools framework.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from ...core.config import INPUT_DATA_DIR, OUTPUT_DATA_DIR
from ...core.handlers import BaseHandler
from .eth_wallet import EthWalletChecker, Config as WalletConfig, import_wallets_from_file
from .eth_scan import EthScanAllTx, Config as ScanConfig, import_addresses_from_file
from .eth_timestamp import EthTimestampTransactions

# Setup logging
logger = logging.getLogger(__name__)

class EthWalletHandler(BaseHandler):
    """Handler for Ethereum wallet checking functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        super().__init__(config)
        
        # Set up paths
        self.input_dir = INPUT_DATA_DIR / "api" / "ethereum" / "wallets"
        self.output_dir = OUTPUT_DATA_DIR / "api" / "ethereum" / "wallet-analysis"
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the checker
        self.checker = None
    
    def setup(self) -> bool:
        """Set up the handler."""
        try:
            # Validate API key
            if not WalletConfig.ETH_API_KEY:
                logger.error("No Ethereum API key found. Please set ETHEREUM_API_KEY environment variable.")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error setting up EthWalletHandler: {str(e)}")
            return False
    
    def run(self, wallet_file: str, threads: int = 10) -> bool:
        """
        Run the wallet checker.
        
        Args:
            wallet_file: Path to the wallet list file (relative to input_dir)
            threads: Number of threads to use for processing
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get full path to wallet file
            wallet_path = self.input_dir / wallet_file
            if not wallet_path.exists():
                logger.error(f"Wallet file not found: {wallet_path}")
                return False
            
            # Initialize checker
            self.checker = EthWalletChecker(
                output_dir=self.output_dir,
                threads=threads
            )
            
            # Import wallets and run
            wallets = import_wallets_from_file(wallet_path)
            if not wallets:
                logger.error("No wallets found in file")
                return False
            
            # Set wallets and run
            self.checker.wallets = wallets
            result = self.checker.run()
            
            return result
            
        except Exception as e:
            logger.error(f"Error running wallet checker: {str(e)}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            # Nothing to clean up for now
            return True
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")
            return False

class EthScanHandler(BaseHandler):
    """Handler for Ethereum transaction scanning functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        super().__init__(config)
        
        # Set up paths
        self.input_dir = INPUT_DATA_DIR / "api" / "ethereum" / "addresses"
        self.output_dir = OUTPUT_DATA_DIR / "api" / "ethereum" / "transactions"
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the scanner
        self.scanner = None
    
    def setup(self) -> bool:
        """Set up the handler."""
        try:
            # Validate API key
            if not ScanConfig.ETH_API_KEY:
                logger.error("No Ethereum API key found. Please set ETHEREUM_API_KEY environment variable.")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error setting up EthScanHandler: {str(e)}")
            return False
    
    def run(self, address_file: str, start_block: int = 0) -> bool:
        """
        Run the transaction scanner.
        
        Args:
            address_file: Path to the address list file (relative to input_dir)
            start_block: Starting block number
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get full path to address file
            address_path = self.input_dir / address_file
            if not address_path.exists():
                logger.error(f"Address file not found: {address_path}")
                return False
            
            # Initialize scanner
            self.scanner = EthScanAllTx(
                output_dir=self.output_dir,
                start_block=start_block
            )
            
            # Import addresses and run
            addresses = import_addresses_from_file(address_path)
            if not addresses:
                logger.error("No addresses found in file")
                return False
            
            # Set addresses and run
            self.scanner.addresses = addresses
            result = self.scanner.run()
            
            return result
            
        except Exception as e:
            logger.error(f"Error running transaction scanner: {str(e)}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            # Nothing to clean up for now
            return True
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")
            return False

class EthTimestampHandler(BaseHandler):
    """Handler for Ethereum timestamp-based transaction search."""
    
    def __init__(self):
        super().__init__()
        self.eth_api_key = os.environ.get("ETHEREUM_API_KEY")
        self.input_dir = INPUT_DATA_DIR / "api" / "ethereum" / "addresses"
        self.output_dir = OUTPUT_DATA_DIR / "api" / "ethereum" / "timestamp-txs"
        self.searcher = None
        self.start_time = None
        self.end_time = None
    
    def setup(self) -> bool:
        """Set up the handler."""
        if not self.eth_api_key:
            logger.error("ETHEREUM_API_KEY environment variable not set")
            return False
        
        self.searcher = EthTimestampTransactions(
            output_dir=self.output_dir,
            test_mode=self.test_mode
        )
        return True
    
    def run(self) -> bool:
        """Run the handler."""
        if not self.searcher:
            logger.error("Handler not set up")
            return False
        
        # Import addresses from input directory
        addresses = []
        for file in self.input_dir.glob("*.txt"):
            try:
                with open(file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            addresses.append(line)
            except Exception as e:
                logger.error(f"Error reading {file}: {e}")
                continue
        
        if not addresses:
            logger.error(f"No addresses found in {self.input_dir}")
            return False
        
        # Run the searcher
        self.searcher.addresses = addresses
        self.searcher.start_time = self.start_time
        self.searcher.end_time = self.end_time
        return self.searcher.run()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        pass 