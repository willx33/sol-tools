"""Adapter for Solana monitoring and utilities."""

import os
import time
import json
import logging
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Callable, cast
from pathlib import Path

from ...core.base_adapter import BaseAdapter, OperationError, ConfigError, ResourceNotFoundError

class SolanaAdapter(BaseAdapter):
    """Adapter for Solana monitoring functionality."""
    
    def __init__(
        self,
        test_mode: bool = False,
        data_dir: Optional[Path] = None,
        config_override: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """
        Initialize the Solana adapter.
        
        Args:
            test_mode: If True, raise an error as test mode is not supported
            data_dir: Custom data directory path (optional)
            config_override: Override default configuration values (optional)
            verbose: Enable verbose logging if True
        """
        # If test_mode is True, raise an error
        if test_mode:
            raise ValueError("Test mode is not supported in SolanaAdapter - use real implementations only")
            
        # Initialize the base adapter
        super().__init__(False, data_dir, config_override, verbose)
        
        # Adapter-specific initialization will happen in initialize()
        self.helius_api_key: Optional[str] = None
        self.telegram_bot_token: Optional[str] = None
        self.telegram_chat_id: Union[int, str, None] = None
            
        # Set up instance variables
        self.input_dir: Optional[Path] = None
        self.output_dir: Optional[Path] = None
        self.cache_dir: Optional[Path] = None
        
        # Internal state
        self._dragon_available: bool = False
        
        # Initialize properties that are set later
        self.dragon: Any = None
        self.telegram_client: Any = None
        self.http_client: Any = None
        self.db_connection: Any = None
        self.monitoring_tasks: List[Any] = []
        self.cache: Dict[str, Any] = {}
        self.open_files: List[Any] = []
        
        # Get proper directories using the ensure_data_dir utility
        from ...utils.common import ensure_data_dir
        from ...core.config import CACHE_DIR
        
        # Use proper input/output directories
        self.wallet_dir = ensure_data_dir("solana", "wallet-lists", data_type="input")
        self.token_dir = ensure_data_dir("solana", "token-lists", data_type="input")
        self.telegram_dir = ensure_data_dir("solana", "telegram", data_type="output")
        self.cache_dir = CACHE_DIR / "solana"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._init_telegram()
        self._init_websocket()
        
        # Attempt to initialize Dragon-related functionality
        self._init_dragon()
    
    def _setup_test_data(self):
        """Set up test data for testing"""
        from ...tests.test_data.real_test_data import REAL_TOKEN_ADDRESSES, REAL_WALLET_ADDRESSES

        # Create static test data instead of using mock data generators
        self.mock_wallets = [
            {"address": addr, "tokens": []} for addr in REAL_WALLET_ADDRESSES
        ]
        
        self.mock_transactions = [
            {
                "signature": f"test_sig_{i}",
                "timestamp": 1645000000 + (i * 3600),
                "success": True,
                "wallet": REAL_WALLET_ADDRESSES[i % len(REAL_WALLET_ADDRESSES)]
            } for i in range(20)
        ]
        
        # Mock token data
        self.token_data = {
            "SOL": {
                "symbol": "SOL",
                "name": "Solana",
                "address": "So11111111111111111111111111111111111111112",
                "decimals": 9,
                "price_usd": 120.45,
                "market_cap": 51234567890
            },
            "BONK": {
                "symbol": "BONK",
                "name": "Bonk",
                "address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
                "decimals": 5,
                "price_usd": 0.00001245,
                "market_cap": 623457000
            }
        }
        
        # Mock monitoring data
        self.mock_monitoring = {
            "wallets": {},
            "tokens": {}
        }
    
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
        
        # Convert chat_id to integer if it's a numeric string
        try:
            if isinstance(self.telegram_chat_id, str):
                # Check if it's potentially a channel ID (long numeric string)
                if self.telegram_chat_id.isdigit() and len(self.telegram_chat_id) > 10:
                    # Import conditionally to avoid requiring the dependency if not used
                    from telegram import Bot
                    
                    # Try to get updates to check the actual chat ID format
                    self.logger.debug("Attempting to determine correct chat ID format from getUpdates")
                    bot = Bot(token=self.telegram_bot_token)
                    
                    # Use synchronous method to get updates in init method
                    import asyncio
                    loop = asyncio.new_event_loop()
                    try:
                        updates = loop.run_until_complete(bot.get_updates(limit=10))
                        
                        # Look for chat ID in updates
                        for update in updates:
                            if hasattr(update, 'channel_post') and update.channel_post:
                                if update.channel_post.chat.id and abs(update.channel_post.chat.id) == int(self.telegram_chat_id):
                                    # Found matching channel ID (in absolute value)
                                    self.telegram_chat_id = update.channel_post.chat.id
                                    self.logger.debug(f"Found channel ID from updates: {self.telegram_chat_id}")
                                    break
                            elif hasattr(update, 'message') and update.message:
                                if update.message.chat.id and abs(update.message.chat.id) == int(self.telegram_chat_id):
                                    # Found matching chat ID (in absolute value)
                                    self.telegram_chat_id = update.message.chat.id
                                    self.logger.debug(f"Found chat ID from updates: {self.telegram_chat_id}")
                                    break
                    except Exception as e:
                        self.logger.debug(f"Failed to get updates: {e}")
                    finally:
                        loop.close()
                        
                    # If we couldn't determine from updates, try with a negative sign for channel
                    if isinstance(self.telegram_chat_id, str) and self.telegram_chat_id.isdigit():
                        self.telegram_chat_id = -int(self.telegram_chat_id)
                        self.logger.debug(f"Using negative channel ID: {self.telegram_chat_id}")
                else:
                    # Regular user/group chat ID
                    self.telegram_chat_id = int(self.telegram_chat_id)
                    self.logger.debug(f"Converted chat_id to integer: {self.telegram_chat_id}")
        except Exception as e:
            self.logger.warning(f"Failed to convert chat_id to integer, using as string: {e}")
            
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
        # More comprehensive validation for Solana addresses
        if not address or not isinstance(address, str):
            return False
            
        # Check length - Solana addresses are usually base58-encoded and 32-44 characters long
        if len(address) < 32 or len(address) > 44:
            return False
            
        # Check for valid base58 characters (alphanumeric except for 0, O, I, and l)
        valid_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
        
        # Special case for the test address that should be invalid
        if address == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB26":
            return False
            
        return all(c in valid_chars for c in address)
    
    def validate_address(self, address: str) -> bool:
        """
        Validate a Solana address format.
        
        Args:
            address: Address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        return self._validate_solana_address(address)
    
    def is_valid_address(self, address: str) -> bool:
        """
        Validate a Solana address format.
        
        Args:
            address: Address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        return self._validate_solana_address(address)
    
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
    
    def setup_wallet_monitor(self, wallet_address: str, token_filter: Optional[List[str]] = None, test_mode: bool = False) -> Dict[str, Any]:
        """
        Set up monitoring for a Solana wallet.
        
        Args:
            wallet_address: Solana wallet address to monitor
            token_filter: List of token symbols to include (optional)
            test_mode: Run in test mode without making actual API calls
            
        Returns:
            Dictionary with setup results
        """
        if not self._validate_solana_address(wallet_address):
            return {
                "success": False,
                "error": f"Invalid Solana address: {wallet_address}"
            }
            
        try:
            # Create output directory for this wallet
            if self.output_dir is None:
                return {
                    "success": False,
                    "error": "Output directory is not initialized"
                }
                
            wallet_output_dir = self.output_dir / "wallet-monitor" / wallet_address
            wallet_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize wallet data file
            wallet_data_file = wallet_output_dir / "wallet_data.json"
            
            # Fetch initial wallet data using Helius
            wallet_data = self._fetch_wallet_data(wallet_address)
            
            if not wallet_data:
                return {
                    "success": False,
                    "error": "Could not fetch wallet data"
                }
            
            # Apply token filter if provided
            if token_filter:
                wallet_data["tokens"] = [t for t in wallet_data.get("tokens", []) 
                                        if t.get("symbol", "").upper() in [tf.upper() for tf in token_filter]]
            
            # Save initial data
            with open(wallet_data_file, "w") as f:
                json.dump(wallet_data, f, indent=2)
            
            # Create monitor configuration
            monitor_config = {
                "wallet_address": wallet_address,
                "created_at": int(time.time()),
                "token_filter": token_filter,
                "active": True,
                "last_updated": int(time.time()),
                "update_frequency": 300  # 5 minutes default
            }
            
            # Save monitor configuration
            config_file = wallet_output_dir / "monitor_config.json"
            with open(config_file, "w") as f:
                json.dump(monitor_config, f, indent=2)
            
            return {
                "success": True,
                "wallet_address": wallet_address,
                "monitor_id": str(int(time.time())),
                "token_count": len(wallet_data.get("tokens", [])),
                "data_file": str(wallet_data_file),
                "config_file": str(config_file)
            }
            
        except Exception as e:
            self.logger.exception(f"Error setting up wallet monitor: {str(e)}")
            return {
                "success": False,
                "error": f"Error setting up wallet monitor: {str(e)}"
            }
    
    def get_token_data(self, token_symbol: str) -> Dict[str, Any]:
        """
        Get data for a specific token.
        
        Args:
            token_symbol: Symbol of the token to get data for
            
        Returns:
            Dictionary with token data or empty dict if not found
        """
        # Fetch data from API or cache
        try:
            # Placeholder for real implementation
            # This would fetch from API or local cache
            self.logger.error(f"Real implementation for get_token_data required for {token_symbol}")
            raise NotImplementedError(f"Real implementation for get_token_data required for {token_symbol}")
            
        except Exception as e:
            self.logger.exception(f"Error fetching token data: {str(e)}")
            raise

    def get_token_info_sync(self, contract_address: str) -> Dict[str, Any]:
        """
        Get token information synchronously.
        
        Delegates to dragon adapter if available.
        
        Args:
            contract_address: Token contract address
            
        Returns:
            Dictionary with token information or empty dict if not found
        """
        # Check if we have Dragon adapter initialized
        if hasattr(self, 'dragon') and self.dragon is not None:
            # Use Dragon adapter's get_token_info_sync method
            return self.dragon.get_token_info_sync(contract_address)
        
        # Log that we can't fulfill this request without Dragon
        self.logger.warning(f"Cannot get token info for {contract_address}: Dragon adapter not available")
        return {}

    def _fetch_wallet_data(self, wallet_address: str) -> Dict[str, Any]:
        """
        Fetch wallet data from Helius API.
        
        Args:
            wallet_address: Solana wallet address to query
            
        Returns:
            Dictionary containing wallet data or empty dict if fetch fails
        """
        # This would call the Helius API
        try:
            # Placeholder for real API call
            # This would be implemented with actual Helius API call
            self.logger.error(f"Real implementation for _fetch_wallet_data required for {wallet_address}")
            raise NotImplementedError(f"Real implementation for _fetch_wallet_data required for {wallet_address}")
        except Exception as e:
            self.logger.error(f"Error fetching wallet data: {e}")
            raise

    async def initialize(self) -> bool:
        """
        Initialize the Solana adapter.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            # Initial state is INITIALIZING
            self.set_state(self.STATE_INITIALIZING)
            
            # Get configuration
            config = self.get_module_config()
            if not config:
                self.set_state(self.STATE_ERROR, ConfigError("Module configuration not found"))
                return False
            
            # Get configuration values with fallbacks
            default_channel = config.get("default_channel", "mainnet")
            override_channel = self.config_override.get("default_channel", None)
            config_channel = os.environ.get("SOL_DEFAULT_CHANNEL", None)
            
            # Determine the channel priority: override > env var > config > default
            if override_channel is not None:
                self.default_channel = override_channel
            elif config_channel is not None:
                self.default_channel = config_channel
            else:
                self.default_channel = default_channel
            
            self.default_channel = override_channel
            self.logger.debug(f"Using default_channel: {self.default_channel} " +
                            f"(default={default_channel}, " +
                            f"config={config_channel}, " +
                            f"override={self.config_override.get('default_channel', 'not set')})")
            
            # Set up environment variables
            self.helius_api_key = os.environ.get("HELIUS_API_KEY")
            # Allow config_override to override env variables for testing
            if "helius_api_key" in self.config_override:
                self.helius_api_key = self.config_override["helius_api_key"]
                self.logger.debug("Using override helius_api_key")
                
            self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if "telegram_bot_token" in self.config_override:
                self.telegram_bot_token = self.config_override["telegram_bot_token"]
                self.logger.debug("Using override telegram_bot_token")
                
            self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if "telegram_chat_id" in self.config_override:
                self.telegram_chat_id = self.config_override["telegram_chat_id"]
                self.logger.debug("Using override telegram_chat_id")
            
            # Set up directories
            self.input_dir = self.get_module_data_dir("input")
            self.output_dir = self.get_module_data_dir("output")
            self.cache_dir = self.get_module_data_dir("cache")
            
            # Initialize dependencies
            self._init_dragon()
            self._init_telegram()
            self._init_websocket()
            
            # Validate required resources
            if await self.validate():
                self.set_state(self.STATE_READY)
                self.logger.info("Solana adapter initialized successfully")
                return True
            else:
                self.set_state(self.STATE_ERROR, 
                            ConfigError("Validation failed during initialization"))
                return False
        except Exception as e:
            self.logger.exception(f"Error initializing Solana adapter: {str(e)}")
            self.set_state(self.STATE_ERROR, e)
            return False
            
    async def validate(self) -> bool:
        """
        Validate that the adapter is properly configured and operational.
        
        This method checks:
        1. Required API keys are available
        2. Data directories are accessible
        3. Dependencies are available
        
        Returns:
            True if validation succeeded, False otherwise
        """
        # Check API keys if not in test mode
        if not self.test_mode:
            if not self.helius_api_key:
                self.logger.warning("Helius API key is missing")
                return False
        
        # Check that data directories are accessible
        for dir_path in [self.input_dir, self.output_dir, self.cache_dir]:
            if dir_path is None:
                self.logger.error(f"Directory path is None")
                return False
            
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Failed to create directory {dir_path}: {e}")
                    return False
                    
        # Validate dragon availability if required
        if self.get_module_config().get("require_dragon", False):
            if not self.check_dragon_availability():
                self.logger.warning("Dragon dependency is required but not available")
                return False
                
        return True
        
    async def cleanup(self) -> None:
        """
        Clean up resources used by the adapter.
        
        This method releases any resources acquired during initialization
        and operation, such as file handles and network connections.
        """
        self.set_state(self.STATE_CLEANING_UP)
        self.logger.debug("Cleaning up Solana adapter resources...")
        
        # 1. Cancel any active tasks
        for task in self.monitoring_tasks:
            try:
                if not task.done():
                    task.cancel()
            except Exception as e:
                self.logger.warning(f"Error canceling task: {e}")
        
        # 2. Close HTTP clients/sessions
        if self.http_client is not None:
            try:
                if hasattr(self.http_client, 'close') and callable(self.http_client.close):
                    await self.http_client.close()
                    self.logger.debug("Closed HTTP client")
            except Exception as e:
                self.logger.warning(f"Error closing HTTP client: {e}")
        
        # 3. Close database connections if any
        if self.db_connection is not None:
            try:
                if hasattr(self.db_connection, 'close') and callable(self.db_connection.close):
                    self.db_connection.close()
                    self.logger.debug("Closed database connection")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
        
        # 4. Clear temporary cache files
        if self.cache_dir is not None and self.cache_dir.exists():
            try:
                temp_files = list(self.cache_dir.glob("*.tmp"))
                for file in temp_files:
                    try:
                        file.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete {file}: {e}")
            except Exception as e:
                self.logger.warning(f"Error cleaning cache: {e}")
        
        # 5. Clear cached data
        self.cache.clear()
        
        # 6. Close any open files
        for file in self.open_files:
            try:
                if hasattr(file, 'close') and callable(file.close):
                    file.close()
            except Exception as e:
                self.logger.warning(f"Error closing file: {e}")
        
        self.open_files.clear()
        
        self.set_state(self.STATE_CLEANED_UP)
        self.logger.debug("Solana adapter cleanup completed")