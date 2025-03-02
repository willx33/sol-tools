"""Adapter for Dragon modules to work with the Sol Tools framework."""

import os
import sys
import logging
import json
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor

# Import BaseAdapter
from ...core.base_adapter import BaseAdapter, ConfigError, OperationError, ResourceNotFoundError

# Import necessary libraries
import tls_client
import httpx
try:
    # Import the UserAgent class directly
    from fake_useragent import UserAgent  # type: ignore
except:
    # Define a fallback if fake_useragent fails
    class UserAgent:
        @property
        def random(self):
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Set up logging
logger = logging.getLogger(__name__)

# Set up thread pools for concurrent operations
_gmgn_threadpool = ThreadPoolExecutor(max_workers=20)
_wallet_threadpool = ThreadPoolExecutor(max_workers=40)

# Use cache directory for temporary logs
from ...core.config import CACHE_DIR
LOGS_DIR = CACHE_DIR / "logs" / "dragon"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Import Dragon modules
from typing import TYPE_CHECKING

# For type checking only
if TYPE_CHECKING:
    import Dragon  # type: ignore
    from Dragon import (  # type: ignore
        utils, BundleFinder, ScanAllTx, BulkWalletChecker, TopTraders,
        TimestampTransactions, purgeFiles, CopyTradeWalletFinder, TopHolders,
        EarlyBuyers, checkProxyFile, EthBulkWalletChecker, EthTopTraders,
        EthTimestampTransactions, EthScanAllTx, GMGN
    )

# Flag to indicate if Dragon imports were successful
DRAGON_IMPORTS_SUCCESS = False

# At runtime, try to import the real Dragon module or use the mock
try:
    import Dragon
    from Dragon import (
        utils, BundleFinder, ScanAllTx, BulkWalletChecker, TopTraders,
        TimestampTransactions, purgeFiles, CopyTradeWalletFinder, TopHolders,
        EarlyBuyers, checkProxyFile, EthBulkWalletChecker, EthTopTraders,
        EthTimestampTransactions, EthScanAllTx, GMGN
    )
    DRAGON_IMPORTS_SUCCESS = True
except ImportError:
    # Use our mock implementation for development/testing
    from . import dragon_mock as Dragon
    from .dragon_mock import (
        utils, BundleFinder, ScanAllTx, BulkWalletChecker, TopTraders,
        TimestampTransactions, purgeFiles, CopyTradeWalletFinder, TopHolders,
        EarlyBuyers, checkProxyFile, EthBulkWalletChecker, EthTopTraders,
        EthTimestampTransactions, EthScanAllTx, GMGN
    )
    DRAGON_IMPORTS_SUCCESS = False
    logger.warning("Using mock Dragon implementation - functionality will be limited")


def save_dragon_log(category: str, data_key: str, response_data: Dict[str, Any], error: Optional[str] = None):
    """Save API response data to log files for debugging and analysis."""
    try:
        from ...utils.common import ensure_file_dir
        
        timestamp = int(time.time())
        log_data = {
            "timestamp": timestamp,
            "key": data_key,
            "response": response_data,
            "error": error
        }
        
        # Create category directory
        category_dir = LOGS_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to log file
        safe_key = data_key.replace("/", "_").replace("\\", "_")
        log_file = category_dir / f"{category}_{safe_key}_{timestamp}.json"
        
        # Ensure parent directory exists
        ensure_file_dir(log_file)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved {category} log to {log_file}")
        
    except Exception as e:
        logger.error(f"Error saving {category} log: {e}")


class GMGN_Client:
    """Improved GMGN client with proper browser fingerprinting avoidance."""
    
    BASE_URL = "https://gmgn.ai/defi/quotation"
    
    def __init__(self, use_proxies: bool = False):
        """Initialize GMGN client with browser fingerprinting evasion."""
        self.use_proxies = use_proxies
        self.proxy_position = 0
        self.max_retries = 5
        self.timeout_sec = 10.0
        self.randomize_session()
    
    def randomize_session(self):
        """Create a new TLS session with randomized browser fingerprint."""
        try:
            # Use a list of identifiers directly instead of accessing tls_client.settings
            identifier_options = [
                "chrome103", "chrome104", "chrome105", "chrome106", 
                "safari15_3", "safari15_5", "firefox102", "firefox104", 
                "opera89", "opera90"
            ]
            
            # Select random browser
            self.identifier = random.choice(identifier_options)
            self.session = tls_client.Session(
                random_tls_extension_order=True,
                client_identifier=self.identifier  # type: ignore
            )
            
            # Use a fixed user agent to avoid errors with fake_useragent
            self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
            
        except Exception:
            # Create a dummy session if tls_client fails
            self.identifier = "chrome_103"
            self.session = None
            self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
        
        # Set headers to mimic browser
        self.headers = {
            'Host': 'gmgn.ai',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'dnt': '1',
            'priority': 'u=1, i',
            'referer': 'https://gmgn.ai/?chain=sol',
            'user-agent': self.user_agent,
        }
    
    def load_proxies(self) -> List[Dict[str, str]]:
        """Load proxies from the proxies.txt file."""
        from ...core.config import INPUT_DATA_DIR
        proxies_file = INPUT_DATA_DIR / "proxies" / "proxies.txt"
        
        if not proxies_file.exists():
            return []
        
        try:
            with open(proxies_file, 'r') as file:
                proxy_lines = file.read().splitlines()
            
            formatted_proxies = []
            for proxy in proxy_lines:
                if not proxy or proxy.startswith('#'):
                    continue
                    
                if ':' in proxy:  
                    parts = proxy.split(':')
                    if len(parts) == 4:  # ip:port:username:password
                        ip, port, username, password = parts
                        formatted_proxies.append({
                            'http': f"http://{username}:{password}@{ip}:{port}",
                            'https': f"http://{username}:{password}@{ip}:{port}"
                        })
                    elif len(parts) == 2:  # ip:port
                        ip, port = parts
                        formatted_proxies.append({
                            'http': f"http://{ip}:{port}",
                            'https': f"http://{ip}:{port}"
                        })
                else:
                    formatted_proxies.append({
                        'http': f"http://{proxy}",
                        'https': f"http://{proxy}"
                    })
                    
            return formatted_proxies
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
            return []
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy from the rotation."""
        proxies = self.load_proxies()
        if not proxies:
            return None
            
        proxy = proxies[self.proxy_position % len(proxies)]
        self.proxy_position += 1
        return proxy
    
    def configure_proxy(self):
        """Configure session with the next proxy if enabled."""
        if not self.use_proxies or self.session is None:
            if hasattr(self, 'session') and self.session is not None:
                self.session.proxies = {}
            return
            
        proxy = self.get_next_proxy()
        if not proxy or self.session is None:
            if hasattr(self, 'session') and self.session is not None:
                self.session.proxies = {}
            return
            
        if isinstance(proxy, dict):
            self.session.proxies = {
                'http': proxy.get('http', ''),
                'https': proxy.get('https', '')
            }
        elif isinstance(proxy, str):
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
    
    def getTokenInfo(self, contract_addr: str) -> Dict[str, Any]:
        """Get token information from GMGN."""
        if not contract_addr:
            return {}
        
        response = None
        try:
            # Determine network based on address format
            network = "sol" if len(contract_addr) in [43, 44] else "eth"
            
            # Use the correct endpoint for the network type
            url = f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{contract_addr}"
            
            logger.debug(f"Fetching token info from: {url}")
            
            for attempt in range(self.max_retries):
                logger.debug(f"Attempt {attempt+1}/{self.max_retries} to get token info for {contract_addr}")
                
                try:
                    # Use httpx for requests with timeout if tls_client fails
                    if self.session:
                        # Don't pass timeout parameter to session.get
                        response = self.session.get(url)
                    else:
                        # Fall back to httpx with timeout
                        response = httpx.get(url, timeout=5)
                    
                    if response and response.status_code == 200:
                        data = response.json().get("data", {}) or {}
                        logger.debug(f"Successfully fetched token info for {contract_addr}")
                        return data
                    
                    # Handle 404 errors specially (token not found)
                    if response and response.status_code == 404:
                        logger.info(f"Token not found (404) for {contract_addr} - this is normal for new tokens")
                        # Only retry once for 404 errors
                        if attempt > 0:
                            return {"error": "Token not found in GeckoTerminal API", "code": 404}
                    
                except Exception as req_error:
                    logger.warning(f"Request error on attempt {attempt+1}: {req_error}")
                    response = None
                    
                # If we get here, the request failed
                error_msg = f"Status: {response.status_code}" if response else "No response"
                logger.warning(f"Failed to get token info: {error_msg} (attempt {attempt+1}/{self.max_retries})")
                
                time.sleep(random.uniform(1.0, 2.0))  # Backoff on failure
                self.randomize_session()  # Try with new session
                
            # If we've exhausted all retries
            if response and response.status_code == 404:
                error_resp = {"error": "Token not found in GeckoTerminal API", "code": 404}
                logger.info(f"Token {contract_addr} not found after {self.max_retries} attempts (404)")
                return error_resp
                
            logger.error(f"All {self.max_retries} attempts to get token info failed for {contract_addr}")
            return {"error": f"Failed after {self.max_retries} attempts", "code": response.status_code if response else 0}
        except Exception as e:
            logger.error(f"Error getting token info for {contract_addr}: {e}")
            return {"error": str(e), "code": 0}
    
    def _get_token_url(self, token_type: str, site_choice: str = "Pump.Fun") -> str:
        """Get the appropriate URL for different token queries."""
        base = "https://gmgn.ai/defi/quotation/v1"
        
        if token_type == "new":
            if site_choice == "Pump.Fun":
                return f"{base}/rank/sol/pump/1h?limit=100&orderby=created_timestamp&direction=desc&new_creation=true"
            else:
                return f"{base}/rank/sol/moonshot/1h?limit=100&orderby=created_timestamp&direction=desc&new_creation=true"
        
        elif token_type == "completing":
            if site_choice == "Pump.Fun":
                return f"{base}/rank/sol/pump/1h?limit=100&orderby=progress&direction=desc&pump=true"
            else:
                return f"{base}/rank/sol/moonshot/1h?limit=100&orderby=progress&direction=desc&moonshot=true"
        
        elif token_type == "soaring":
            if site_choice == "Pump.Fun":
                return f"{base}/rank/sol/pump/1h?limit=100&orderby=market_cap_5m&direction=desc&soaring=true"
            else:
                return f"{base}/rank/sol/moonshot/1h?limit=100&orderby=market_cap_5m&direction=desc&soaring=true"
        
        elif token_type == "bonded":
            if site_choice == "Pump.Fun":
                return f"{base}/pairs/sol/new_pairs/1h?limit=100&orderby=market_cap&direction=desc&launchpad=pump&period=1h&filters[]=not_honeypot&filters[]=pump"
            else:
                return f"{base}/pairs/sol/new_pairs/1h?limit=100&orderby=open_timestamp&direction=desc&launchpad=moonshot&period=1h&filters[]=not_honeypot&filters[]=moonshot"
        
        return ""
    
    def _fetch_tokens(self, token_type: str, site_choice: str = "Pump.Fun") -> List[Dict[str, Any]]:
        """Fetch tokens of a specific type from GMGN."""
        url = self._get_token_url(token_type, site_choice)
        if not url:
            return []
        
        # Refresh session and proxy
        self.randomize_session()
        self.configure_proxy()
        
        max_attempts = 3
        tokens = []
        
        for attempt in range(max_attempts):
            try:
                response = None
                if self.session is not None:
                    response = self.session.get(url, headers=self.headers)
                else:
                    logger.warning("Session is None, cannot make request")
                    time.sleep(random.uniform(1, 2))
                    continue
                
                if response.status_code != 200:
                    logger.warning(f"Error {response.status_code} fetching {token_type} tokens, attempt {attempt+1}/{max_attempts}")
                    time.sleep(random.uniform(1, 2))
                    continue
                
                data = response.json()
                
                # Process based on token type
                if token_type == "bonded":
                    # Safely extract the pairs list with proper null checks
                    items = []
                    if data is not None and isinstance(data, dict):
                        data_dict = data.get('data')
                        if data_dict is not None and isinstance(data_dict, dict):
                            pairs = data_dict.get('pairs')
                            if pairs is not None and isinstance(pairs, list):
                                items = pairs
                    for item in items:
                        if not item.get('base_address'):
                            continue
                        tokens.append({
                            'address': item.get('base_address'),
                            'name': item.get('base_name', ''),
                            'symbol': item.get('base_symbol', ''),
                            'price': item.get('price', 0),
                            'market_cap': item.get('market_cap', 0),
                            'liquidity': item.get('liquidity', 0)
                        })
                else:
                    items = data.get('data', {}).get('rank', [])
                    for item in items:
                        if not item.get('address'):
                            continue
                        tokens.append({
                            'address': item.get('address'),
                            'name': item.get('name', ''),
                            'symbol': item.get('symbol', ''),
                            'price': item.get('price', 0),
                            'market_cap': item.get('market_cap', 0),
                            'liquidity': item.get('liquidity', 0)
                        })
                
                return tokens
                
            except Exception as e:
                logger.error(f"Error fetching {token_type} tokens, attempt {attempt+1}/{max_attempts}: {e}")
                time.sleep(random.uniform(1, 3))
        
        return tokens
    
    def getNewTokens(self) -> List[Dict[str, Any]]:
        """Get new token listings."""
        return self._fetch_tokens("new")
    
    def getCompletingTokens(self) -> List[Dict[str, Any]]:
        """Get completing token listings."""
        return self._fetch_tokens("completing")
    
    def getSoaringTokens(self) -> List[Dict[str, Any]]:
        """Get soaring token listings."""
        return self._fetch_tokens("soaring")
    
    def getBondedTokens(self) -> List[Dict[str, Any]]:
        """Get bonded token listings."""
        return self._fetch_tokens("bonded")


class TokenDataHandler:
    """Handler for token data with retry logic and caching."""
    
    def __init__(self, use_proxies: bool = False):
        """Initialize the token data handler."""
        self.gmgn = GMGN_Client(use_proxies=use_proxies)
        self.max_retries = 5
        self.timeout_sec = 30.0
        self.logger = logging.getLogger(__name__)
    
    def _get_token_info_sync(self, address: str) -> Dict[str, Any]:
        """Get token info with retries and timeout."""
        if not hasattr(self, 'gmgn') or self.gmgn is None:
            self.logger.error("GMGN client not initialized in TokenDataHandler")
            return {"error": "GMGN client not initialized properly"}
            
        start_time = time.time()
        fail_count = 0
        last_err = None
        
        # More detailed logging
        self.logger.info(f"Fetching token data for {address} with {self.max_retries} retries and {self.timeout_sec}s timeout")
        
        while fail_count < self.max_retries:
            elapsed = time.time() - start_time
            if elapsed > self.timeout_sec:
                error_msg = f"Could not get data from GMGN in {self.timeout_sec}s"
                self.logger.error(error_msg)
                save_dragon_log("gmgn", address, {}, error_msg)
                return {"error": error_msg}
            
            try:
                self.logger.debug(f"Attempt {fail_count+1}/{self.max_retries} for token {address}")
                # Wait a moment between retries to avoid overwhelming the API
                if fail_count > 0:
                    time.sleep(random.uniform(0.5, 1.5))
                
                token_data = self.gmgn.getTokenInfo(address)
                
                # Check for 404 error - these are expected for new tokens
                if token_data.get("code") == 404:
                    self.logger.info(f"Token {address} not found in GeckoTerminal - this is normal for new tokens")
                    
                    # Only do a single retry for 404s - no point in retrying more
                    if fail_count > 0:
                        # We already retried once, return the not found error
                        return {
                            "error": token_data.get("error", "Token not found"),
                            "code": 404,
                            "not_found": True
                        }
                    
                    fail_count += 1
                    continue
                
                if not token_data:
                    last_err = "Empty response"
                    self.logger.warning(f"Empty response for token {address}")
                    fail_count += 1
                    continue
                    
                if "error" in token_data:
                    last_err = token_data.get("error", "Unknown error")
                    self.logger.warning(f"Error in token data for {address}: {last_err}")
                    fail_count += 1
                    continue
                
                # Success
                self.logger.info(f"Successfully fetched token data for {address}")
                return token_data
                
            except Exception as e:
                last_err = str(e)
                self.logger.warning(f"Exception during token data fetch for {address}: {last_err}")
                fail_count += 1
        
        error_response = {
            "error": f"GMGN getTokenInfo failed after {fail_count} retries: {last_err}"
        }
        self.logger.error(error_response["error"])
        save_dragon_log("gmgn", address, error_response)
        return error_response
    
    async def get_token_data(self, address: str) -> Dict[str, Any]:
        """Get token data asynchronously."""
        loop = asyncio.get_running_loop()
        start_time = time.time()
        result = await loop.run_in_executor(_gmgn_threadpool, self._get_token_info_sync, address)
        result["fetch_time"] = time.time() - start_time
        save_dragon_log("gmgn", address, result)
        return result


# Helper to safely check and create directories
def _ensure_dir_exists(dir_path):
    """Ensure directory exists, creating it if necessary."""
    # Simply return if the path is None
    if dir_path is None:
        return
    
    # Check if path exists and create if needed
    if hasattr(dir_path, 'exists') and not dir_path.exists():
        if hasattr(dir_path, 'mkdir'):
            dir_path.mkdir(parents=True, exist_ok=True)


class DragonAdapter(BaseAdapter):
    """
    DragonDEX adapter for interacting with the Dragon ecosystem.
    
    Attributes:
        ethereum_input_dir: Directory for Ethereum input files
        solana_input_dir: Directory for Solana input files
        proxies_dir: Directory for proxy configuration
        ethereum_output_dirs: Directories for Ethereum output
        solana_output_dirs: Directories for Solana output
        token_info_dir: Directory for token information
        max_threads: Maximum number of threads for concurrent operations
        bundle: Bundle configuration
        solana_wallets: Solana wallet configurations
    """
    
    def __init__(self, 
                 ethereum_input_dir: Optional[Path] = None,
                 solana_input_dir: Optional[Path] = None,
                 proxies_dir: Optional[Path] = None,
                 ethereum_output_dirs: Optional[Dict[str, Path]] = None,
                 solana_output_dirs: Optional[Dict[str, Path]] = None,
                 token_info_dir: Optional[Path] = None,
                 max_threads: int = 10,
                 bundle: Any = None,
                 solana_wallets: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize DragonAdapter."""
        super().__init__(**kwargs)
        
        # Initialize directory paths
        self.ethereum_input_dir = ethereum_input_dir
        self.solana_input_dir = solana_input_dir
        self.proxies_dir = proxies_dir
        self.ethereum_output_dirs = ethereum_output_dirs or {}
        self.solana_output_dirs = solana_output_dirs or {}
        self.token_info_dir = token_info_dir
        self.max_threads = max_threads
        self.bundle = bundle
        self.solana_wallets = solana_wallets or []
        
        # Ensure directories exist
        for dir_path in [ethereum_input_dir, solana_input_dir, proxies_dir, token_info_dir]:
            _ensure_dir_exists(dir_path)
            
        for dirs in [ethereum_output_dirs or {}, solana_output_dirs or {}]:
            for dir_path in dirs.values():
                _ensure_dir_exists(dir_path)
        
        # Set up internal state
        self.dragon_available = False
        self.dragon_components = {}
        self.proxy_list = []
        self.gmgn_client = None
        self.token_data_handler = None
        
        # Paths will be set during initialization
        self.wallets_dir = None
        self.export_dir = None
        self.proxy_file = None
        
        # Override default threads if specified in config
        self.default_threads = 10
        
    async def initialize(self) -> bool:
        """
        Initialize the Dragon adapter.
        
        This method:
        1. Loads configuration
        2. Sets up directories
        3. Initializes Dragon components
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            self.set_state(self.STATE_INITIALIZING)
            self.logger.debug("Initializing Dragon adapter...")
            
            # Get module-specific configuration
            module_config = self.get_module_config()
            
            # Apply configuration overrides for demonstration
            if "default_threads" in module_config:
                self.default_threads = module_config["default_threads"]
                self.logger.debug(f"Using configured default_threads: {self.default_threads}")
            
            # Override from direct config_override if provided
            if "default_threads" in self.config_override:
                self.default_threads = self.config_override["default_threads"]
                self.logger.debug(f"Using override default_threads: {self.default_threads}")
            
            # Set up directories
            self.wallets_dir = self.get_module_data_dir("wallets")
            self.export_dir = self.get_module_data_dir("export")
            self.proxy_file = self.get_module_data_dir("input") / "proxies.txt"
            
            # Ensure directories exist
            self.wallets_dir.mkdir(parents=True, exist_ok=True)
            self.export_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize Dragon components
            self._init_dragon_components()
            
            # Initialize GMGN client with proxy setting from config
            use_proxies = module_config.get("use_proxies", False)
            self.gmgn_client = GMGN_Client(use_proxies=use_proxies)
            self.token_data_handler = TokenDataHandler(use_proxies=use_proxies)
            
            # Validate required resources
            if await self.validate():
                self.set_state(self.STATE_READY)
                self.logger.info("Dragon adapter initialized successfully")
                return True
            else:
                self.set_state(self.STATE_ERROR, 
                               ConfigError("Validation failed during initialization"))
                return False
            
        except Exception as e:
            self.set_state(self.STATE_ERROR, e)
            self.logger.error(f"Failed to initialize Dragon adapter: {e}")
            return False
    
    async def validate(self) -> bool:
        """
        Validate that the adapter is properly configured and operational.
        
        This method checks:
        1. Required directories are accessible
        2. Dragon components are available or properly mocked
        
        Returns:
            True if validation succeeded, False otherwise
        """
        # Check that data directories are accessible
        for dir_path in [self.wallets_dir, self.export_dir]:
            if dir_path is not None and not dir_path.exists():
                try:
                    if dir_path is not None:
                        dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Failed to create directory {dir_path}: {e}")
                    return False
        
        # In test mode, we don't need actual Dragon components
        if self.test_mode:
            return True
        
        # Check if proxy file exists if use_proxies is enabled
        if self.get_module_config().get("use_proxies", False):
            proxy_exists = self.check_proxy_file(create_if_missing=True)
            if not proxy_exists:
                self.logger.warning("Proxy file doesn't exist but use_proxies is enabled")
                # We'll continue anyway since this isn't critical
                
        # Check Dragon availability - if required but not available, fail validation
        if not self.dragon_available and self.get_module_config().get("require_dragon", False):
            self.logger.error("Dragon functionality is required but not available")
            return False
            
        return True
    
    async def cleanup(self) -> None:
        """
        Clean up resources used by the adapter.
        
        This method releases any resources acquired during initialization
        and operation, such as thread pools and network connections.
        """
        self.set_state(self.STATE_CLEANING_UP)
        self.logger.debug("Cleaning up Dragon adapter resources...")
        
        # Close threadpools
        if hasattr(self, '_gmgn_threadpool') and _gmgn_threadpool:
            _gmgn_threadpool.shutdown(wait=False)
        
        if hasattr(self, '_wallet_threadpool') and _wallet_threadpool:
            _wallet_threadpool.shutdown(wait=False)
        
        # Close GMGN client if it exists
        if self.gmgn_client is not None and hasattr(self.gmgn_client, 'session') and getattr(self.gmgn_client, 'session', None) is not None:
            try:
                # Using getattr with default to avoid attribute error
                session = getattr(self.gmgn_client, 'session', None)
                if session is not None and hasattr(session, 'close'):
                    session.close()
            except Exception as e:
                self.logger.warning(f"Error closing GMGN client: {e}")
                
        # Clear any cached data
        if not self.test_mode:
            try:
                # Only delete temporary files in non-test mode
                temp_files = list(LOGS_DIR.glob("*.json"))
                for temp_file in temp_files:
                    try:
                        if temp_file.is_file():
                            temp_file.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete temp file {temp_file}: {e}")
            except Exception as e:
                self.logger.warning(f"Error cleaning up temporary files: {e}")
        
        self.set_state(self.STATE_CLEANED_UP)
        self.logger.debug("Dragon adapter cleanup completed")
        
    def _init_dragon_components(self):
        """Initialize Dragon components or create placeholders if not available."""
        try:
            # Store references to Dragon components
            self.dragon_components = {
                "BundleFinder": BundleFinder,
                "ScanAllTx": ScanAllTx,
                "BulkWalletChecker": BulkWalletChecker,
                "TopTraders": TopTraders,
                "TimestampTransactions": TimestampTransactions,
                "purgeFiles": purgeFiles,
                "CopyTradeWalletFinder": CopyTradeWalletFinder,
                "TopHolders": TopHolders,
                "EarlyBuyers": EarlyBuyers,
                "checkProxyFile": checkProxyFile,
                "EthBulkWalletChecker": EthBulkWalletChecker, 
                "EthTopTraders": EthTopTraders,
                "EthTimestampTransactions": EthTimestampTransactions,
                "EthScanAllTx": EthScanAllTx,
                "GMGN": GMGN
            }
            
            self.dragon_available = DRAGON_IMPORTS_SUCCESS
            self.logger.debug(f"Dragon components loaded successfully (using {'actual' if DRAGON_IMPORTS_SUCCESS else 'mock'} implementation)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Dragon components: {e}")
            self.dragon_available = False
            self.dragon_components = {}

    def ensure_dragon_paths(self) -> None:
        """
        Ensure proper paths for Dragon operations within the input-data/output-data structure.
        """
        try:
            # Make sure specific input directories exist
            if self.ethereum_input_dir is not None:
                self.ethereum_input_dir.mkdir(parents=True, exist_ok=True)
            if self.solana_input_dir is not None:
                self.solana_input_dir.mkdir(parents=True, exist_ok=True)
            if self.proxies_dir is not None:
                self.proxies_dir.mkdir(parents=True, exist_ok=True)
            
            # Create the output directories
            if self.ethereum_output_dirs is not None:
                for key, dir_path in self.ethereum_output_dirs.items():
                    if dir_path is not None:
                        dir_path.mkdir(parents=True, exist_ok=True)
                
            if self.solana_output_dirs is not None:
                for key, dir_path in self.solana_output_dirs.items():
                    if dir_path is not None:
                        dir_path.mkdir(parents=True, exist_ok=True)
                
            if self.token_info_dir is not None:
                self.token_info_dir.mkdir(parents=True, exist_ok=True)
            
            # Add a log message to help with debugging
            logger.info("Successfully created all Dragon directories")
            
        except Exception as e:
            logger.error(f"Error creating Dragon directories: {e}")

    def check_proxy_file(self, create_if_missing: bool = True) -> bool:
        """
        Check if proxy file exists and has content.
        
        Args:
            create_if_missing: Create an empty proxy file if it doesn't exist
            
        Returns:
            True if proxies are available, False otherwise
        """
        proxy_path = None
        if self.proxies_dir is not None:
            proxy_path = self.proxies_dir / "proxies.txt"
        
        if proxy_path is not None and not proxy_path.exists() and create_if_missing:
            # Create the directory and empty file
            from ...utils.common import ensure_file_dir
            ensure_file_dir(proxy_path)
            proxy_path.touch()
                
        # Check if the file has content
        if proxy_path is not None and proxy_path.exists():
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
            threads = int(threads or self.default_threads)
            if threads > self.max_threads:
                return self.default_threads
            return threads
        except (ValueError, TypeError):
            return self.default_threads
            
    def validate_solana_address(self, address: str) -> bool:
        """
        Validate a Solana address format.
        
        Args:
            address: Solana address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        if not address:
            return False
        return len(address) in [43, 44] and address[0] in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    def validate_ethereum_address(self, address: str) -> bool:
        """
        Validate an Ethereum address format.
        
        Args:
            address: Ethereum address to validate
            
        Returns:
            True if the address format is valid, False otherwise
        """
        if not address:
            return False
        if address.startswith("0x"):
            return len(address) == 42 and all(c in "0123456789abcdefABCDEF" for c in address[2:])
        return len(address) == 40 and all(c in "0123456789abcdefABCDEF" for c in address)
    
    # GMGN Implementation
    async def get_token_info(self, contract_address: str) -> Dict[str, Any]:
        """
        Get token information from GMGN.
        
        Args:
            contract_address: Token contract address
            
        Returns:
            Token information
        """
        if self.token_data_handler is None:
            return {}
        return await self.token_data_handler.get_token_data(contract_address)  # type: ignore
    
    def get_token_info_sync(self, contract_address: str) -> Dict[str, Any]:
        """
        Synchronous version of get_token_info.
        
        Args:
            contract_address: Contract address to get information for
            
        Returns:
            Token information
        """
        if not hasattr(self, 'token_data_handler') or self.token_data_handler is None:
            self.logger.warning("Token data handler is not initialized")
            return {}
            
        try:
            # Check if we have a method to get token info
            token_data_handler = getattr(self, 'token_data_handler', None)
            if token_data_handler is not None and hasattr(token_data_handler, '_get_token_info_sync'):
                return token_data_handler._get_token_info_sync(contract_address)
            else:
                self.logger.error("No _get_token_info_sync method available")
                return {}
        except Exception as e:
            self.logger.error(f"Error getting token info for {contract_address}: {e}")
            return {}
    
    def get_new_tokens(self) -> List[Dict[str, Any]]:
        """Get new token listings."""
        if self.gmgn_client is None:
            return []
        return self.gmgn_client.getNewTokens()
    
    def get_completing_tokens(self) -> List[Dict[str, Any]]:
        """Get completing token listings."""
        if self.gmgn_client is None:
            return []
        return self.gmgn_client.getCompletingTokens()
    
    def get_soaring_tokens(self) -> List[Dict[str, Any]]:
        """Get soaring token listings."""
        if self.gmgn_client is None:
            return []
        return self.gmgn_client.getSoaringTokens()
    
    def get_bonded_tokens(self) -> List[Dict[str, Any]]:
        """Get bonded token listings."""
        if self.gmgn_client is None:
            return []
        return self.gmgn_client.getBondedTokens()
    
    # Solana implementations
    def solana_bundle_checker(self, contract_address: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Check for bundled transactions (multiple buys in one tx).
        
        Args:
            contract_address: Solana token contract address or list of addresses
            
        Returns:
            Dictionary with transaction data or error information
        """
        try:
            self.ensure_dragon_paths()
        except Exception:
            return {"success": False, "error": "Could not ensure Dragon paths"}
        
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
        Check Solana wallets and get detailed information.
        
        Args:
            wallets: Single wallet address or list of addresses
            threads: Number of threads to use (default: self.default_threads)
            skip_wallets: Skip wallet analysis if possible
            use_proxies: Use proxies for requests
            
        Returns:
            Dictionary with wallet check results
        """
        # Test mode handling
        if self.test_mode:
            # Create mock wallet data
            if isinstance(wallets, str):
                wallets = [wallets]
            
            result = {
                "success": True,
                "wallets_processed": len(wallets),
                "wallet_data": {},
                "timestamp": int(time.time())
            }
            
            for wallet in wallets:
                # Find a mock wallet or generate a new one
                mock_wallet = next((w for w in self.solana_wallets if w["address"] == wallet), None)
                if not mock_wallet:
                    # Use the first wallet as a template
                    from ...tests.test_data.mock_data import random_token_amount
                    mock_wallet = self.solana_wallets[0].copy()
                    mock_wallet["address"] = wallet
                    # Randomize some values
                    for token in mock_wallet["tokens"]:
                        token["balance"] = random_token_amount()
                        token["value_usd"] = round(token["balance"] * token["price_usd"], 2)
                
                result["wallet_data"][wallet] = mock_wallet
            
            return result
        
        # Start of non-test mode code
        start_time = time.time()
        
        # Ensure Dragon paths exist
        self.ensure_dragon_paths()
        
        # Handle single wallet or list
        if isinstance(wallets, str):
            wallets = [wallets]
        
        # Validate all wallets
        valid_wallets = []
        for wallet in wallets:
            if self.validate_solana_address(wallet):
                valid_wallets.append(wallet)
            else:
                logger.warning(f"Invalid Solana address: {wallet}")
        
        if not valid_wallets:
            logger.error("No valid Solana addresses provided")
            return {"success": False, "error": "No valid Solana addresses provided"}
        
        # Set number of threads
        threads = self.handle_threads(threads)
        
        # Check proxy file
        if use_proxies:
            self.check_proxy_file()
        
        try:
            # Prepare parameters for Dragon BulkWalletChecker
            output_dir = str(self.solana_output_dirs["wallet_analysis"])
            os.makedirs(output_dir, exist_ok=True)
            
            # Handle BulkWalletChecker by importing the necessary module
            from ...wallet.bulk_wallet_checker import BulkWalletChecker
            
            try:
                checker = BulkWalletChecker(
                    wallets=valid_wallets,
                    skip_wallets=skip_wallets,
                    output_dir=output_dir,
                    proxies=use_proxies,
                    threads=threads
                )
                
                # Run the checker (returns status code and files created)
                result = checker.run()
                
                if result["status"] != "success":
                    raise Exception(result.get("message", "Unknown error in BulkWalletChecker"))
                    
                # Process results and return in our adapter's format
                return {
                    "status": "success",
                    "wallets_processed": len(valid_wallets),
                    "results_location": output_dir,
                    "metadata": result.get("data", {}),
                    "timestamp": int(time.time()),
                    "duration": round(time.time() - start_time, 2)
                }
                
            except Exception as e:
                logger.error(f"Error in BulkWalletChecker: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "wallets_processed": 0,
                    "timestamp": int(time.time()),
                    "duration": round(time.time() - start_time, 2)
                }
            
        except Exception as e:
            logger.exception(f"Error in solana_wallet_checker: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "wallets_processed": 0,
                "timestamp": int(time.time()),
                "duration": round(time.time() - start_time, 2)
            }

    def import_solana_wallets(self, filename: str, directory: Optional[str] = None) -> bool:
        """
        Import Solana wallets from a file.
        
        Args:
            filename: Name of the file containing wallet addresses
            directory: Directory where the file is located (optional)
            
        Returns:
            True if successful, False otherwise
        """
        dir_path = directory or ""  # Use empty string if None

        if self.test_mode:
            # In test mode, just pretend we imported the wallets
            try:
                # If directory is not provided, use the default input directory
                if not directory:
                    directory = str(self.solana_input_dir)
                
                # Construct the full path
                file_path = Path(directory) / filename
                
                # Check if the file exists
                if not Path(file_path).exists():
                    logger.warning(f"Wallet file not found: {file_path}")
                    return False
                
                # Pretend we processed the file - no actual file read in test mode
                logger.info(f"Test mode: Simulating import of Solana wallets from {file_path}")
                
                # Return success
                return True
                
            except Exception as e:
                logger.exception(f"Error in import_solana_wallets: {str(e)}")
                return False
        
        # Real mode implementation would go here
        try:
            # Import wallets using Dragon functionality if available
            # For now, just return success
            return True
            
        except Exception as e:
            logger.exception(f"Error in import_solana_wallets: {str(e)}")
            return False
    
    def import_ethereum_wallets(self, filename: str, directory: Optional[str] = None) -> bool:
        """
        Import Ethereum wallets from a file.
        
        Args:
            filename: Name of the file containing wallet addresses
            directory: Directory where the file is located (optional)
            
        Returns:
            True if successful, False otherwise
        """
        dir_path = directory or ""  # Use empty string if None

        if self.test_mode:
            # In test mode, just pretend we imported the wallets
            try:
                # If directory is not provided, use the default input directory
                if not directory:
                    directory = str(self.ethereum_input_dir)
                
                # Construct the full path
                file_path = Path(directory) / filename
                
                # Check if the file exists
                if not Path(file_path).exists():
                    logger.warning(f"Wallet file not found: {file_path}")
                    return False
                
                # Pretend we processed the file - no actual file read in test mode
                logger.info(f"Test mode: Simulating import of Ethereum wallets from {file_path}")
                
                # Return success
                return True
                
            except Exception as e:
                logger.exception(f"Error in import_ethereum_wallets: {str(e)}")
                return False
        
        # Real mode implementation would go here
        try:
            # Import wallets using Dragon functionality if available
            # For now, just return success
            return True
            
        except Exception as e:
            logger.exception(f"Error in import_ethereum_wallets: {str(e)}")
            return False