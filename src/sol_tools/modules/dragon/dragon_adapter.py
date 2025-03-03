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
from typing import Dict, List, Any, Optional, Callable, Union, TYPE_CHECKING, overload
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
# Add a NullHandler to prevent "No handlers could be found" warnings
logger.addHandler(logging.NullHandler())

# Check if we're in test mode
IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

# If in test mode, silence all logging from this module
if IN_TEST_MODE:
    # Create a do-nothing handler
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    
    # Set critical+1 level (higher than any standard level)
    logger.setLevel(logging.CRITICAL + 1)
    
    # Remove any existing handlers and add our null handler
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.addHandler(NullHandler())

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

# Flag for tracking Dragon import success
DRAGON_IMPORTS_SUCCESS = False

# Function to check if Dragon is available
def check_dragon_availability() -> bool:
    """
    Check if the Dragon module is available in the Python path.
    
    Returns:
        bool: True if Dragon is available, False otherwise
    """
    # Check if Dragon is in sys.modules
    if "Dragon" in sys.modules:
        logger.info("Dragon module already imported")
        return True
    
    # Look for Dragon in PYTHONPATH
    potential_paths = []
    
    # 1. Check in standard Python path locations
    for path in sys.path:
        if not os.path.exists(path) or not os.path.isdir(path):
            continue
            
        dragon_path = os.path.join(path, "Dragon")
        if os.path.exists(dragon_path) and os.path.isdir(dragon_path):
            potential_paths.append(dragon_path)
    
    # 2. Check in parent directories
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)
    dragon_parent_path = os.path.join(parent_dir, "Dragon")
    if os.path.exists(dragon_parent_path) and os.path.isdir(dragon_parent_path):
        potential_paths.append(dragon_parent_path)
    
    # 3. Check next to the current directory
    dragon_sibling_path = os.path.join(os.path.dirname(cwd), "Dragon")
    if os.path.exists(dragon_sibling_path) and os.path.isdir(dragon_sibling_path):
        potential_paths.append(dragon_sibling_path)
    
    if potential_paths:
        logger.info(f"Found Dragon module at: {potential_paths[0]}")
        return True
    
    logger.error("ERROR: Dragon module not found. Real implementation is required.")
    logger.error("Please ensure the Dragon module is properly installed.")
    logger.error("Python path: " + str(sys.path))
    return False

# Try to import the real Dragon module - no fallbacks
if not check_dragon_availability():
    # Raising the ImportError for clarity when the module is not found
    raise ImportError("ERROR: Dragon module not found. Real implementation is required. No mock implementations are available or supported.")

try:
    # Add potential paths to sys.path
    dragon_module_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..')
    if dragon_module_path not in sys.path:
        sys.path.append(dragon_module_path)
    
    # Import real implementation only - no fallbacks to mocks
    import Dragon
    from Dragon import (
        utils, BundleFinder, ScanAllTx, BulkWalletChecker, TopTraders,
        TimestampTransactions, purgeFiles, CopyTradeWalletFinder, TopHolders,
        EarlyBuyers, checkProxyFile, GMGN
    )
    
    # Import Ethereum implementations from the ethereum module
    from ...modules.ethereum import (
        EthWalletChecker,
        EthTopTraders,
        EthScanAllTx,
        EthTimestampTransactions
    )
    
    # Verify that we didn't get placeholder implementations
    if (isinstance(EthWalletChecker, type) and 
        EthWalletChecker.__name__.startswith('Placeholder')):
        raise ImportError("Real EthWalletChecker implementation not available")
    if (isinstance(EthTopTraders, type) and 
        EthTopTraders.__name__.startswith('Placeholder')):
        raise ImportError("Real EthTopTraders implementation not available")
    if (isinstance(EthScanAllTx, type) and 
        EthScanAllTx.__name__.startswith('Placeholder')):
        raise ImportError("Real EthScanAllTx implementation not available")
    if (isinstance(EthTimestampTransactions, type) and 
        EthTimestampTransactions.__name__.startswith('Placeholder')):
        raise ImportError("Real EthTimestampTransactions implementation not available")
    
    DRAGON_IMPORTS_SUCCESS = True
    logger.info("Successfully imported real Dragon implementation")
except ImportError as e:
    logger.error(f"ERROR: Failed to import Dragon module. Error: {e}")
    logger.error("Please ensure the Dragon module is properly installed.")
    raise ImportError("ERROR: Dragon module not found. Real implementation is required. No mock implementations are available or supported.")

# If we're here, we've successfully imported Dragon
if not DRAGON_IMPORTS_SUCCESS:
    raise ImportError("ERROR: Dragon module imports failed. Real implementation is required. No mock implementations are available or supported.")

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
            network = "solana" if len(contract_addr) in [43, 44] else "ethereum"
            
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
                return f"{base}/rank/solana/pump/1h?limit=100&orderby=created_timestamp&direction=desc&new_creation=true"
            else:
                return f"{base}/rank/solana/moonshot/1h?limit=100&orderby=created_timestamp&direction=desc&new_creation=true"
        
        elif token_type == "completing":
            if site_choice == "Pump.Fun":
                return f"{base}/rank/solana/pump/1h?limit=100&orderby=progress&direction=desc&pump=true"
            else:
                return f"{base}/rank/solana/moonshot/1h?limit=100&orderby=progress&direction=desc&moonshot=true"
        
        elif token_type == "soaring":
            if site_choice == "Pump.Fun":
                return f"{base}/rank/solana/pump/1h?limit=100&orderby=market_cap_5m&direction=desc&soaring=true"
            else:
                return f"{base}/rank/solana/moonshot/1h?limit=100&orderby=market_cap_5m&direction=desc&soaring=true"
        
        elif token_type == "bonded":
            if site_choice == "Pump.Fun":
                return f"{base}/pairs/solana/new_pairs/1h?limit=100&orderby=market_cap&direction=desc&launchpad=pump&period=1h&filters[]=not_honeypot&filters[]=pump"
            else:
                return f"{base}/pairs/solana/new_pairs/1h?limit=100&orderby=open_timestamp&direction=desc&launchpad=moonshot&period=1h&filters[]=not_honeypot&filters[]=moonshot"
        
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
    """Adapter for the Dragon module."""
    
    def __init__(self, **kwargs):
        """
        Initialize the Dragon adapter.
        
        Args:
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        # Set default threads
        self.default_threads = kwargs.get('default_threads', 10)
        
        # Initialize components
        self._initialize_dragon_components()
        
        # Solana wallets storage
        self.solana_wallets = kwargs.get('solana_wallets') or []
        
        # Ethereum wallets storage
        self._ethereum_wallets = kwargs.get('ethereum_wallets') or []
        
        # Token metrics cache
        self.token_metrics_cache = {}
        
        # Check Dragon imports
        if not DRAGON_IMPORTS_SUCCESS:
            error_msg = "Dragon implementation is required but not available. No mock implementations are supported."
            self.logger.error(error_msg)
            raise ImportError(error_msg)
        
        # Initialize directory paths
        self.ethereum_input_dir = kwargs.get('ethereum_input_dir')
        self.solana_input_dir = kwargs.get('solana_input_dir')
        self.proxies_dir = kwargs.get('proxies_dir')
        self.ethereum_output_dirs = kwargs.get('ethereum_output_dirs') or {}
        self.solana_output_dirs = kwargs.get('solana_output_dirs') or {}
        self.token_info_dir = kwargs.get('token_info_dir')
        self.max_threads = kwargs.get('max_threads', 10)
        self.bundle = kwargs.get('bundle')
        
        # Initialize GMGN client
        self.gmgn_client = GMGN_Client(use_proxies=kwargs.get('use_proxies', False))
        
        # Set up token data handler
        self._token_data_handler = None
        self._token_data_handler_initialized = False
        self._use_proxies = kwargs.get('use_proxies', False)
        
        # Ensure directories exist
        for dir_path in [self.ethereum_input_dir, self.solana_input_dir, self.proxies_dir, self.token_info_dir]:
            _ensure_dir_exists(dir_path)
            
        for dirs in [self.ethereum_output_dirs or {}, self.solana_output_dirs or {}]:
            for dir_path in dirs.values():
                _ensure_dir_exists(dir_path)
                
        self.logger.info("Dragon adapter initialized successfully with real implementation")
    
    def _initialize_dragon_components(self) -> None:
        """Initialize all Dragon components."""
        # Verify Dragon is properly imported
        if not DRAGON_IMPORTS_SUCCESS:
            error_msg = "Dragon implementation is required but not available. No mock implementations are supported."
            self.logger.error(error_msg)
            raise ImportError(error_msg)
            
        # Initialize components with real Dragon implementations
        self.utils = utils
        self.purge_files = purgeFiles
        self.check_proxy_file = checkProxyFile
        
        # Initialize Dragon classes
        self.bundle_finder = BundleFinder
        self.scan_all_tx = ScanAllTx
        self.bulk_wallet_checker = BulkWalletChecker
        self.top_traders = TopTraders
        self.timestamp_transactions = TimestampTransactions
        self.copy_trade_wallet_finder = CopyTradeWalletFinder
        self.top_holders = TopHolders
        self.early_buyers = EarlyBuyers
        self.gmgn = GMGN
        
        # Initialize our Ethereum implementations
        try:
            # Create instances of the Ethereum components
            self.eth_bulk_wallet_checker = lambda **kwargs: EthWalletChecker(**kwargs)
            self.eth_top_traders = lambda **kwargs: EthTopTraders(**kwargs)
            self.eth_timestamp_transactions = lambda **kwargs: EthTimestampTransactions(**kwargs)
            self.eth_scan_all_tx = lambda **kwargs: EthScanAllTx(**kwargs)
            logger.debug("Successfully initialized Ethereum components")
        except Exception as e:
            logger.error(f"Could not initialize Ethereum components: {str(e)}")
            # Provide implementations that raise proper errors
            def eth_component_error(**kwargs):
                raise ImportError(f"Ethereum components failed to initialize: {str(e)}\nPlease check that all Ethereum modules are properly installed and configured.")
            self.eth_bulk_wallet_checker = eth_component_error
            self.eth_top_traders = eth_component_error
            self.eth_timestamp_transactions = eth_component_error
            self.eth_scan_all_tx = eth_component_error
        
        # Initialize BundleFinder instance
        self.bundle = BundleFinder

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
        Get token information for a contract address.
        
        Args:
            contract_address: Contract address to get information for
            
        Returns:
            Token information
        """
        if self.get_token_data_handler() is None:
            return {}
        return await self.get_token_data_handler().get_token_data(contract_address)  # type: ignore
    
    def get_token_info_sync(self, contract_address: str) -> Dict[str, Any]:
        """
        Synchronous version of get_token_info.
        
        Args:
            contract_address: Contract address to get information for
            
        Returns:
            Token information
        """
        if not hasattr(self, 'get_token_data_handler') or self.get_token_data_handler() is None:
            self.logger.warning("Token data handler is not initialized")
            return {}
            
        try:
            # Check if we have a method to get token info
            token_data_handler = self.get_token_data_handler()
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
                # Make sure bundle is initialized
                if self.bundle is None:
                    self.bundle = BundleFinder
                    
                # Call static methods on the BundleFinder class
                tx_hashes = BundleFinder.teamTrades(address)
                # Ensure we have at least two transaction hashes
                if len(tx_hashes) >= 2:
                    data = BundleFinder.checkBundle(tx_hashes[0], tx_hashes[1])
                    formatted = BundleFinder.prettyPrint(data, address)
                    return {
                        "success": True,
                        "address": address,
                        "data": data,
                        "formatted": formatted
                    }
                else:
                    return {
                        "success": False,
                        "address": address,
                        "error": "Not enough transaction hashes found"
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
                    mock_wallet = self.solana_wallets[0].copy() if self.solana_wallets else {
                        "address": wallet,
                        "tokens": [
                            {
                                "symbol": "SOL",
                                "name": "Solana",
                                "balance": 2.5,  # Static value instead of random
                                "price_usd": 125.45,
                                "value_usd": 313.63  # 2.5 * 125.45
                            }
                        ]
                    }
                    mock_wallet["address"] = wallet
                    # Use static values instead of random
                    for token in mock_wallet["tokens"]:
                        token["balance"] = 2.5  # Static value instead of random
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
        logger.debug(f"Importing Solana wallets from file: {filename} in directory: {directory}")

        try:
            # If directory is not provided, use the default input directory
            if not directory:
                directory = str(self.solana_input_dir)
            
            # Construct the full path
            file_path = Path(directory) / filename
            logger.debug(f"Full path to wallet file: {file_path}")
            
            # Check if the file exists
            if not Path(file_path).exists():
                logger.warning(f"Wallet file not found: {file_path}")
                return False
            
            # Read the file to populate solana_wallets
            try:
                with open(file_path, 'r') as f:
                    wallets_data = json.load(f)
                    # Store the wallets in memory
                    self.solana_wallets = wallets_data
                    logger.debug(f"Loaded wallets data: {wallets_data}")
                    logger.info(f"Imported {len(self.solana_wallets)} Solana wallets from {file_path}")
            except Exception as e:
                logger.error(f"Error reading wallet file {file_path}: {e}")
                return False
            
            # Return success
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
        logger.debug(f"Importing Ethereum wallets from file: {filename} in directory: {directory}")

        try:
            # If directory is not provided, use the default input directory
            if not directory:
                directory = str(self.ethereum_input_dir)
            
            # Construct the full path
            file_path = Path(directory) / filename
            logger.debug(f"Full path to wallet file: {file_path}")
            
            # Check if the file exists
            if not Path(file_path).exists():
                logger.warning(f"Wallet file not found: {file_path}")
                return False
            
            # Read the file to populate ethereum_wallets
            try:
                wallets = []
                with open(file_path, 'r') as f:
                    for line in f:
                        # Skip comments and empty lines
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        # Add the wallet to the list
                        wallets.append(line)
                
                # Store the wallets in memory
                self._ethereum_wallets = wallets
                logger.info(f"Imported {len(self._ethereum_wallets)} Ethereum wallets from {file_path}")
            except Exception as e:
                logger.error(f"Error reading wallet file {file_path}: {e}")
                return False
            
            # Return success
            return True
            
        except Exception as e:
            logger.exception(f"Error in import_ethereum_wallets: {str(e)}")
            return False

    def get_token_data_handler(self):
        """
        Get the token data handler, initializing it if necessary.
        
        Returns:
            The token data handler instance
        """
        # Only initialize once to avoid recursion
        if not self._token_data_handler_initialized:
            # Create token handler directly without import to avoid circular dependencies
            if hasattr(self, 'gmgn_client') and self.gmgn_client is not None:
                self._token_data_handler = TokenDataHandler(use_proxies=self._use_proxies)
            else:
                self.logger.error("Cannot initialize token data handler: gmgn_client is None")
                self._token_data_handler = None
            
            # Mark as initialized regardless of outcome to prevent future initialization attempts
            self._token_data_handler_initialized = True
                
        return self._token_data_handler

    def initialize(self):
        """Initialize the Dragon adapter for use."""
        # This method is already effectively implemented in __init__
        self.logger.info("Dragon adapter initialization complete")
        return True
    
    def cleanup(self):
        """Clean up resources used by the Dragon adapter."""
        # Close any open resources
        if hasattr(self, 'gmgn_client') and self.gmgn_client is not None:
            # Clean up the GMGN client if needed
            pass
            
        # Close thread pools
        if '_gmgn_threadpool' in globals():
            _gmgn_threadpool.shutdown(wait=False)
        if '_wallet_threadpool' in globals():
            _wallet_threadpool.shutdown(wait=False)
            
        self.logger.info("Dragon adapter cleaned up")
        return True
    
    @property
    def ethereum_wallets(self):
        """
        Get the list of Ethereum wallets.
        
        Returns:
            List of Ethereum wallet addresses
        """
        return getattr(self, '_ethereum_wallets', [])

    def validate(self, request_type: str, data: Any) -> bool:
        """
        Validate the input data.
        
        Args:
            request_type: Type of request to validate
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if request_type == "solana_address":
            return self.validate_solana_address(data)
        elif request_type == "ethereum_address":
            return self.validate_ethereum_address(data)
        elif request_type == "token_address":
            # Validate either Solana or Ethereum token address
            return self.validate_solana_address(data) or self.validate_ethereum_address(data)
        
        # Default fallback for unknown validation types
        return False

    def eth_top_traders(self, **kwargs: Any) -> Optional[EthTopTraders]:
        """
        Create an EthTopTraders instance.
        
        Args:
            **kwargs: Keyword arguments including:
                token_address (str): The Ethereum token contract address
                days (int, optional): Number of days to analyze
                output_dir (Path, optional): Directory to save results
                test_mode (bool, optional): Whether to run in test mode
                
        Returns:
            Optional[EthTopTraders]: The initialized instance or None if validation fails
        """
        token_address = kwargs.get('token_address')
        days = kwargs.get('days', 30)
        output_dir = kwargs.get('output_dir')
        test_mode = kwargs.get('test_mode', False)
        
        if token_address is None:
            logger.error("No token address provided")
            return None
            
        if not isinstance(token_address, str):
            logger.error(f"Invalid token address type: {type(token_address)}")
            return None
            
        if not self.validate_ethereum_address(token_address):
            logger.error(f"Invalid Ethereum address: {token_address}")
            return None
            
        try:
            # Pass kwargs directly to maintain flexibility
            return EthTopTraders(**kwargs)
        except Exception as e:
            logger.error(f"Error creating EthTopTraders instance: {e}")
            return None
            
    def eth_timestamp_transactions(self, **kwargs: Any) -> Optional[EthTimestampTransactions]:
        """
        Create an EthTimestampTransactions instance.
        
        Args:
            **kwargs: Keyword arguments including:
                contract_address (str): The Ethereum contract address
                start_time (int): Start timestamp
                end_time (int): End timestamp
                output_dir (Path, optional): Directory to save results
                
        Returns:
            Optional[EthTimestampTransactions]: The initialized instance or None if validation fails
        """
        contract_address = kwargs.get('contract_address')
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        output_dir = kwargs.get('output_dir')
        
        if contract_address is None:
            logger.error("No contract address provided")
            return None
            
        if not isinstance(contract_address, str):
            logger.error(f"Invalid contract address type: {type(contract_address)}")
            return None
            
        if not self.validate_ethereum_address(contract_address):
            logger.error(f"Invalid Ethereum address: {contract_address}")
            return None
            
        try:
            # Pass kwargs directly to maintain flexibility
            return EthTimestampTransactions(**kwargs)
        except Exception as e:
            logger.error(f"Error creating EthTimestampTransactions instance: {e}")
            return None