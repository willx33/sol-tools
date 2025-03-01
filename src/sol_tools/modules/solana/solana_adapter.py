"""Adapter for Solana monitoring and utilities."""

import os
import time
import json
import logging
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Callable
from pathlib import Path

class SolanaAdapter:
    """Adapter for Solana monitoring functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Solana adapter.
        
        Args:
            config: Additional configuration parameters (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Environment variables
        self.helius_api_key = os.environ.get("HELIUS_API_KEY")
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        # Get proper directories using the ensure_data_dir utility
        from ...utils.common import ensure_data_dir
        from ...core.config import CACHE_DIR
        
        # Use proper input/output directories
        self.input_dir = ensure_data_dir("solana", data_type="input")
        self.output_dir = ensure_data_dir("solana", data_type="output")
        
        # Create specific subdirectories under proper structure
        self.wallet_dir = ensure_data_dir("solana", "wallet-lists", data_type="input")
        self.token_dir = ensure_data_dir("solana", "token-lists", data_type="input")
        self.telegram_dir = ensure_data_dir("solana", "telegram", data_type="output")
        self.cache_dir = CACHE_DIR / "solana"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components conditionally based on environment variables
        self._init_telegram()
        self._init_websocket()
        
        # Attempt to initialize Dragon-related functionality
        self._init_dragon()
    
    def _init_dragon(self):
        """Initialize Dragon functionality."""
        try:
            # Import dragon_adapter here to prevent circular imports
            from ..dragon.dragon_adapter import DragonAdapter, DRAGON_IMPORTS_SUCCESS
            self.dragon = DragonAdapter()
            self.dragon_available = DRAGON_IMPORTS_SUCCESS
            
            # Ensure dragon paths are created
            if self.dragon_available:
                self.dragon.ensure_dragon_paths()
        except Exception as e:
            self.logger.error(f"Error initializing Dragon: {e}")
            self.dragon_available = False
    
    def _init_telegram(self) -> bool:
        """
        Initialize Telegram client if credentials are available.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        self.telegram_client = None
        
        if not (self.telegram_bot_token and self.telegram_chat_id):
            self.logger.warning("Telegram credentials not available")
            return False
            
        try:
            # Import conditionally to avoid requiring the dependency if not used
            from telegram import Bot
            self.telegram_client = Bot(token=self.telegram_bot_token)
            return True
        except ImportError:
            self.logger.warning("Python-telegram-bot not installed")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing Telegram: {e}")
            return False
    
    def _init_websocket(self) -> bool:
        """
        Initialize WebSocket client for Helius if API key is available.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        self.ws_client = None
        
        if not self.helius_api_key:
            self.logger.warning("Helius API key not available")
            return False
            
        # We'll just set a flag for now - actual initialization happens when needed
        self.ws_initialized = True
        return True
    
    async def send_telegram(self, message: str) -> bool:
        """
        Send a message to Telegram.
        
        Args:
            message: Message text to send
            
        Returns:
            True if the message was sent successfully, False otherwise
        """
        if not self.telegram_client:
            return False
            
        try:
            await self.telegram_client.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode="Markdown"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def test_telegram(self) -> Dict[str, Any]:
        """
        Test Telegram connection.
        
        Returns:
            Dictionary with test results
        """
        if not (self.telegram_bot_token and self.telegram_chat_id):
            return {
                "success": False,
                "error": "Telegram credentials not set"
            }
            
        # Run async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            test_message = "🤖 Sol Tools - Telegram test message"
            success = loop.run_until_complete(self.send_telegram(test_message))
            if success:
                return {
                    "success": True,
                    "message": "Telegram test message sent successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send Telegram message"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Telegram test error: {e}"
            }
        finally:
            loop.close()
    
    def token_monitor(self, token_address: str, min_amount: float = 1000.0) -> Dict[str, Any]:
        """
        Monitor transactions for a specific token.
        
        Args:
            token_address: Solana token address to monitor
            min_amount: Minimum transaction amount (in USD) to alert on
            
        Returns:
            Dictionary with monitoring results (or error information)
        """
        if not self.helius_api_key:
            return {
                "success": False,
                "error": "Helius API key not set"
            }
            
        # Validate token address format
        if not self._validate_solana_address(token_address):
            return {
                "success": False,
                "error": f"Invalid Solana token address: {token_address}"
            }
            
        # In a real implementation, we would set up a WebSocket connection to Helius
        # and monitor transactions. Since this functionality requires the Helius API key
        # which was already checked above, we'll simply return an error indicating
        # that the functionality is incomplete or unavailable.
        return {
            "success": False,
            "error": "Token monitoring requires Helius API integration which is not yet implemented"
        }
    
    def wallet_monitor(self, wallet_addresses: List[str]) -> Dict[str, Any]:
        """
        Monitor transactions for specific wallet addresses.
        
        Args:
            wallet_addresses: List of Solana wallet addresses to monitor
            
        Returns:
            Dictionary with monitoring results (or error information)
        """
        if not self.helius_api_key:
            return {
                "success": False,
                "error": "Helius API key not set"
            }
            
        # Validate wallet addresses
        invalid_wallets = [w for w in wallet_addresses if not self._validate_solana_address(w)]
        if invalid_wallets:
            return {
                "success": False,
                "error": f"Invalid Solana wallet addresses: {invalid_wallets}"
            }
            
        # Import ensure_file_dir from utils
        from ...utils.common import ensure_file_dir
        
        # Save wallet addresses to file in the proper location
        wallet_file = self.wallet_dir / "monitor-wallets.txt"
        # Ensure parent directory exists
        ensure_file_dir(wallet_file)
        with open(wallet_file, "w") as f:
            for wallet in wallet_addresses:
                f.write(f"{wallet}\n")
        
        # In a real implementation, we would set up WebSocket connections to monitor 
        # these wallets. Since this functionality requires the Helius API key
        # which was already checked above, we'll simply return an error indicating
        # that the functionality is incomplete or unavailable.
        return {
            "success": False,
            "error": "Wallet monitoring requires Helius API integration which is not yet implemented"
        }
    
    def telegram_scraper(self, 
                        channel: str, 
                        limit: int = 100, 
                        filter_type: str = "All messages", 
                        export_csv: bool = True) -> Dict[str, Any]:
        """
        Scrape token addresses from Telegram messages.
        
        Args:
            channel: Telegram channel username (without @)
            limit: Maximum number of messages to scrape
            filter_type: Type of filter to apply to messages
            export_csv: Whether to export results as CSV
            
        Returns:
            Dictionary with scraping results (or error information)
        """
        if not (self.telegram_bot_token and self.telegram_chat_id):
            return {
                "success": False,
                "error": "Telegram credentials not set"
            }
            
        # In a real implementation, we would use Telethon or similar to scrape
        # messages from the channel. Since this functionality requires Telegram
        # credentials which were already checked above, we'll simply return an error
        # indicating that the functionality is incomplete or unavailable.
        self.logger.info(f"Scraping channel: @{channel}")
        self.logger.info(f"Limit: {limit} messages")
        self.logger.info(f"Filter: {filter_type}")
        
        return {
            "success": False,
            "error": "Telegram scraping requires the python-telegram-bot or Telethon library which is not yet implemented"
        }
    
    def _validate_solana_address(self, address: str) -> bool:
        """
        Validate a Solana address format.
        
        Args:
            address: Address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        # Simple length check - could be enhanced with more validation
        return len(address) in [43, 44]
    
    # -------------------------------------------------------------------------
    # Dragon-related functionality - with fallback implementations
    # -------------------------------------------------------------------------
    
    def check_dragon_availability(self) -> bool:
        """
        Check if Dragon functionality is available.
        
        Returns:
            True if Dragon modules are available, False otherwise
        """
        # Re-check availability as it might change if library is installed during runtime
        try:
            if not hasattr(self, 'dragon_available') or not self.dragon_available:
                self._init_dragon()
            return self.dragon_available and self.dragon is not None
        except Exception:
            return False
    
    def solana_bundle_checker(self, contract_address: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Check for bundled transactions (multiple buys in one tx).
        
        Args:
            contract_address: Solana token contract address or list of addresses
            
        Returns:
            Dictionary with transaction data or error information
        """
        if not self.check_dragon_availability():
            return {"success": False, "error": "Dragon modules not available"}
        
        try:
            return self.dragon.solana_bundle_checker(contract_address)
        except Exception as e:
            self.logger.error(f"Error in solana_bundle_checker: {e}")
            return {"success": False, "error": f"Error: {str(e)}"}
    
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
        if not self.check_dragon_availability():
            return {"success": False, "error": "Dragon modules not available"}
        
        try:
            return self.dragon.solana_wallet_checker(wallets, threads, skip_wallets, use_proxies)
        except Exception as e:
            self.logger.error(f"Error in solana_wallet_checker: {e}")
            return {"success": False, "error": f"Error: {str(e)}"}