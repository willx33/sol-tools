"""
Handler module for Ethereum functionality in Sol Tools.
This module integrates the standalone implementations with the Sol Tools framework.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ...core.config import INPUT_DATA_DIR, OUTPUT_DATA_DIR
from ...core.handlers import BaseHandler
from .eth_wallet import EthWalletChecker, Config as WalletConfig, import_wallets_from_file
from .eth_traders import EthTopTraders, Config as TradersConfig
from .eth_timestamp import EthTimestampTransactions, Config as TimestampConfig
from .eth_scan import EthScanAllTx, Config as ScanConfig, import_addresses_from_file

# Setup logging
logger = logging.getLogger(__name__)

class EthWalletHandler(BaseHandler):
    """Handler for Ethereum wallet operations."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        super().__init__(config)
        self.name = "Ethereum Wallet Checker"
        self.description = "Check Ethereum wallet balances and transactions"
        
        # Set up paths
        self.input_dir = INPUT_DATA_DIR / "ethereum" / "wallets"
        self.output_dir = OUTPUT_DATA_DIR / "ethereum" / "wallet-analysis"
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, wallets: Optional[List[str]] = None, 
            skip_wallets: bool = False,
            output_dir: Optional[Path] = None,
            proxies: bool = False,
            threads: int = 10,
            test_mode: bool = False) -> bool:
        """
        Run the wallet checker.
        
        Args:
            wallets: List of wallet addresses to check
            skip_wallets: Whether to skip wallets that have been checked
            output_dir: Directory to save results
            proxies: Whether to use proxies
            threads: Number of threads to use
            test_mode: Run in test mode
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Use config values if not provided in args
        output_dir = output_dir or self.output_dir
        threads = threads or self.config.get('threads', 10)
        proxies = proxies or self.config.get('use_proxies', False)
        
        # Create instance
        checker = EthWalletChecker(
            wallets=wallets,
            skip_wallets=skip_wallets,
            output_dir=output_dir,
            proxies=proxies,
            threads=threads,
            test_mode=test_mode
        )
        
        # Run the checker
        return checker.run()

class EthScanHandler(BaseHandler):
    """Handler for Ethereum transaction scanning."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        super().__init__(config)
        self.name = "Ethereum Transaction Scanner"
        self.description = "Scan Ethereum transactions"
        
        # Set up paths
        self.input_dir = INPUT_DATA_DIR / "ethereum" / "addresses"
        self.output_dir = OUTPUT_DATA_DIR / "ethereum" / "scan-txns"
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, addresses: Optional[List[str]] = None,
            output_dir: Optional[Path] = None,
            test_mode: bool = False) -> bool:
        """
        Run the transaction scanner.
        
        Args:
            addresses: List of addresses to scan
            output_dir: Directory to save results
            test_mode: Run in test mode
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Use config values if not provided in args
        output_dir = output_dir or self.output_dir
        
        # Create instance
        scanner = EthScanAllTx(
            addresses=addresses,
            output_dir=output_dir,
            test_mode=test_mode
        )
        
        # Run the scanner
        return scanner.run()

class EthTimestampHandler(BaseHandler):
    """Handler for Ethereum timestamp-based transaction scanning."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        super().__init__(config)
        self.name = "Ethereum Timestamp Scanner"
        self.description = "Find Ethereum transactions by timestamp"
        
        # Set up paths
        self.input_dir = INPUT_DATA_DIR / "ethereum" / "timestamps"
        self.output_dir = OUTPUT_DATA_DIR / "ethereum" / "timestamp-txns"
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, contract_address: str,
            start_time: int,
            end_time: int,
            threads: int = 10) -> bool:
        """
        Run the timestamp scanner.
        
        Args:
            contract_address: Contract address to scan
            start_time: Start timestamp
            end_time: End timestamp
            threads: Number of threads to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Use config values if not provided in args
        threads = threads or self.config.get('threads', 10)
        
        # Create instance
        scanner = EthTimestampTransactions()
        
        # Run the scanner
        return scanner.run(contract_address, start_time, end_time, threads)

class EthTradersHandler(BaseHandler):
    """Handler for Ethereum top traders scanning."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        super().__init__(config)
        self.name = "Ethereum Top Traders Scanner"
        self.description = "Find top traders for Ethereum tokens"
        
        # Set up paths
        self.input_dir = INPUT_DATA_DIR / "ethereum" / "tokens"
        self.output_dir = OUTPUT_DATA_DIR / "ethereum" / "top-traders"
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, token_address: str,
            days: int = 30,
            output_dir: Optional[Path] = None,
            test_mode: bool = False) -> bool:
        """
        Run the top traders scanner.
        
        Args:
            token_address: Token contract address to scan
            days: Number of days to analyze
            output_dir: Directory to save results
            test_mode: Run in test mode
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Use config values if not provided in args
        output_dir = output_dir or self.output_dir
        days = days or self.config.get('days', 30)
        
        # Create instance
        scanner = EthTopTraders()
        
        # Run the scanner
        return scanner.run(token_address, days, output_dir, test_mode) 