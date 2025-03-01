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
from typing import Dict, List, Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor

# Import necessary libraries
import tls_client
import httpx
try:
    from fake_useragent import UserAgent
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
    # Create mock Dragon modules for graceful startup failure
    DRAGON_IMPORTS_SUCCESS = False
    class PlaceholderClass:
        """Placeholder for missing Dragon components."""
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            return {"success": False, "error": "Dragon module not installed"}
    
    # Create placeholder classes 
    Dragon = PlaceholderClass()
    utils = BundleFinder = ScanAllTx = BulkWalletChecker = TopTraders = PlaceholderClass()
    TimestampTransactions = purgeFiles = CopyTradeWalletFinder = PlaceholderClass()
    TopHolders = EarlyBuyers = checkProxyFile = EthBulkWalletChecker = PlaceholderClass()
    EthTopTraders = EthTimestampTransactions = EthScanAllTx = GMGN = PlaceholderClass()


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
            # Choose only modern browsers for better compatibility
            identifier_options = [
                br for br in tls_client.settings.ClientIdentifiers.__args__
                if br.startswith(('chrome', 'safari', 'firefox', 'opera'))
            ]
            
            # Select random browser
            self.identifier = random.choice(identifier_options)
            self.session = tls_client.Session(
                random_tls_extension_order=True,
                client_identifier=self.identifier
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
        if not self.use_proxies:
            self.session.proxies = None
            return
            
        proxy = self.get_next_proxy()
        if not proxy:
            self.session.proxies = None
            return
            
        if isinstance(proxy, dict):
            self.session.proxies = {
                'http': proxy.get('http'),
                'https': proxy.get('https')
            }
        elif isinstance(proxy, str):
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
    
    def getTokenInfo(self, contract_addr: str) -> Dict[str, Any]:
        """Get token information from GMGN."""
        if not contract_addr:
            error_response = {"error": "No contract address provided"}
            save_dragon_log("gmgn", contract_addr, {}, "No contract address provided")
            return error_response
        
        # Refresh session and proxy
        self.randomize_session()
        self.configure_proxy()
        
        url = f"{self.BASE_URL}/v1/tokens/sol/{contract_addr}"
        
        try:
            resp = self.session.get(url, headers=self.headers)
            
            if resp.status_code != 200:
                error_msg = f"HTTP {resp.status_code}"
                error_response = {"error": error_msg, "body": resp.text}
                save_dragon_log("gmgn", contract_addr, error_response, error_msg)
                return error_response
            
            data = resp.json()
            
            price = float(data.get('price', 0))
            mcap = float(data.get('market_cap', 0))
            liq = float(data.get('liquidity', 0))
            vol24 = float(data.get('volume_24h', 0))
            p24 = float(data.get('price_24h', 0))
            holders = int(data.get('holder_count', 0))
            sym = data.get('symbol', '')
            nm = data.get('name', '')
            
            price_change_24h = 0.0
            if p24 > 0:
                price_change_24h = ((price - p24) / p24) * 100
            
            response_data = {
                "priceUsd": price,
                "marketCap": mcap,
                "liquidityUsd": liq,
                "volume24h": vol24,
                "priceChange24h": price_change_24h,
                "holders": holders,
                "symbol": sym,
                "name": nm
            }
            
            save_dragon_log("gmgn", contract_addr, response_data)
            return response_data
            
        except Exception as e:
            error_msg = str(e)
            error_response = {"error": error_msg}
            save_dragon_log("gmgn", contract_addr, {}, error_msg)
            return error_response
    
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
                response = self.session.get(url, headers=self.headers)
                
                if response.status_code != 200:
                    logger.warning(f"Error {response.status_code} fetching {token_type} tokens, attempt {attempt+1}/{max_attempts}")
                    time.sleep(random.uniform(1, 2))
                    continue
                
                data = response.json()
                
                # Process based on token type
                if token_type == "bonded":
                    items = data.get('data', {}).get('pairs', [])
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
        self.timeout_sec = 10.0
    
    def _get_token_info_sync(self, address: str) -> Dict[str, Any]:
        """Get token info with retries and timeout."""
        start_time = time.time()
        fail_count = 0
        last_err = None
        
        while fail_count < self.max_retries:
            elapsed = time.time() - start_time
            if elapsed > self.timeout_sec:
                error_msg = f"Could not get data from GMGN in {self.timeout_sec}s"
                save_dragon_log("gmgn", address, {}, error_msg)
                return {"error": error_msg}
            
            try:
                token_data = self.gmgn.getTokenInfo(address)
                
                if not token_data:
                    last_err = "Empty response"
                    fail_count += 1
                    time.sleep(random.uniform(0.5, 1.0))
                    continue
                    
                if "error" in token_data:
                    last_err = token_data
                    fail_count += 1
                    time.sleep(random.uniform(0.5, 1.0))
                    continue
                
                return token_data
                
            except Exception as e:
                last_err = str(e)
                fail_count += 1
                time.sleep(random.uniform(0.5, 1.3))
        
        error_response = {
            "error": f"GMGN getTokenInfo failed after {fail_count} retries: {last_err}"
        }
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


class DragonAdapter:
    """Adapter for Dragon functionality to work within Sol Tools framework."""
    
    def __init__(self, test_mode: bool = False):
        """
        Initialize the Dragon adapter.
        
        Args:
            test_mode: If True, operate in test mode without external API calls
        """
        from ...core.config import INPUT_DATA_DIR, OUTPUT_DATA_DIR
        
        # Set test mode flag
        self.test_mode = test_mode
        
        # Define the input directory structure
        self.ethereum_input_dir = INPUT_DATA_DIR / "ethereum" / "wallet-lists"
        self.solana_input_dir = INPUT_DATA_DIR / "solana" / "wallet-lists"
        self.proxies_dir = INPUT_DATA_DIR / "proxies"
        
        # Define the output directory structure based on blockchain
        self.ethereum_output_dirs = {
            "wallet_analysis": OUTPUT_DATA_DIR / "ethereum" / "dragon" / "wallet-analysis",
            "top_traders": OUTPUT_DATA_DIR / "ethereum" / "dragon" / "top-traders",
            "top_holders": OUTPUT_DATA_DIR / "ethereum" / "dragon" / "top-holders",
            "early_buyers": OUTPUT_DATA_DIR / "ethereum" / "dragon" / "early-buyers"
        }
        
        self.solana_output_dirs = {
            "wallet_analysis": OUTPUT_DATA_DIR / "solana" / "dragon" / "wallet-analysis",
            "top_traders": OUTPUT_DATA_DIR / "solana" / "dragon" / "top-traders",
            "top_holders": OUTPUT_DATA_DIR / "solana" / "dragon" / "top-holders",
            "early_buyers": OUTPUT_DATA_DIR / "solana" / "dragon" / "early-buyers"
        }
        
        # GMGN token info is part of API modules
        self.token_info_dir = OUTPUT_DATA_DIR / "api" / "gmgn" / "token-info"
        
        # Set up threading defaults
        self.default_threads = 40
        self.max_threads = 100
        
        # Initialize mock data for test mode
        if self.test_mode:
            from ...tests.test_data.mock_data import (
                generate_solana_wallet_list,
                generate_ethereum_wallet_list,
                generate_solana_transaction_list,
                generate_ethereum_transaction_list
            )
            # Initialize in-memory storage for test mode
            self.solana_wallets = generate_solana_wallet_list(10)
            self.ethereum_wallets = generate_ethereum_wallet_list(10)
            self.solana_transactions = generate_solana_transaction_list(20)
            self.ethereum_transactions = generate_ethereum_transaction_list(20)
            self.logger = logging.getLogger("DragonAdapter_test")
        
        # Set up async clients (if not in test mode)
        if not self.test_mode:
            self.gmgn_client = GMGN_Client()
            self.token_handler = TokenDataHandler()
        
        # Initialize components from the original Dragon library
        # This needs to happen for both test and real modes
        self._init_dragon_components()

    def _init_dragon_components(self):
        """Initialize components from Dragon modules."""
        if not DRAGON_IMPORTS_SUCCESS:
            logger.warning("Dragon modules not available, initializing with placeholders")
            return False
        
        # Create mock BulkWalletChecker class with a run method if in test mode
        if hasattr(self, 'test_mode') and self.test_mode:
            # We need to define these as properties even in test mode
            class MockDragonComponent:
                """Mock component for Dragon modules in test mode."""
                def __init__(self, component_name):
                    self.component_name = component_name
                
                def run(self, *args, **kwargs):
                    """Mock run method that returns success and empty file list."""
                    return [0, []]  # Status code 0 = success
                
                def __call__(self, *args, **kwargs):
                    """Allow the component to be called as a function."""
                    return {"success": True, "test_mode": True, "component": self.component_name}
            
            # Create mock components
            self.bundle = MockDragonComponent("BundleFinder")
            self.scan = MockDragonComponent("ScanAllTx")
            self.wallet_checker = MockDragonComponent("BulkWalletChecker")
            self.top_traders = MockDragonComponent("TopTraders")
            self.timestamp = MockDragonComponent("TimestampTransactions")
            self.copy_wallet = MockDragonComponent("CopyTradeWalletFinder")
            self.top_holders = MockDragonComponent("TopHolders")
            self.early_buyers = MockDragonComponent("EarlyBuyers")
            
            # Ethereum components
            self.eth_wallet = MockDragonComponent("EthBulkWalletChecker")
            self.eth_traders = MockDragonComponent("EthTopTraders")
            self.eth_timestamp = MockDragonComponent("EthTimestampTransactions")
            self.eth_scan = MockDragonComponent("EthScanAllTx")
            
            # Add GMGN mock
            self.gmgn = MockDragonComponent("GMGN")
            
            # The BulkWalletChecker needs special handling because it's used differently
            class MockBulkWalletChecker:
                def __init__(self, *args, **kwargs):
                    self.output_dir = kwargs.get("output_dir", "")
                    self.wallets = kwargs.get("wallets", [])
                
                def run(self):
                    """Mock run method that returns success and created files."""
                    # We'll pretend we created files for tracking
                    return [0, [f"{wallet}.json" for wallet in self.wallets]]
            
            # Replace the simpler mock with the more specific one
            self.BulkWalletChecker = MockBulkWalletChecker
            
            return True
        
        # Initialize Dragon components (real mode)
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
        self.eth_scan = EthScanAllTx if 'EthScanAllTx' in globals() else None
        
        # GMGN component
        self.gmgn = GMGN if 'GMGN' in globals() else None
        
        return True

    def ensure_dragon_paths(self) -> None:
        """
        Ensure proper paths for Dragon operations within the input-data/output-data structure.
        """
        try:
            # Make sure specific input directories exist
            self.ethereum_input_dir.mkdir(parents=True, exist_ok=True)
            self.solana_input_dir.mkdir(parents=True, exist_ok=True)
            self.proxies_dir.mkdir(parents=True, exist_ok=True)
            
            # Create the output directories
            for dir_path in self.ethereum_output_dirs.values():
                dir_path.mkdir(parents=True, exist_ok=True)
                
            for dir_path in self.solana_output_dirs.values():
                dir_path.mkdir(parents=True, exist_ok=True)
                
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
        proxy_path = self.proxies_dir / "proxies.txt"
        
        if not proxy_path.exists() and create_if_missing:
            # Create the directory and empty file
            from ...utils.common import ensure_file_dir
            ensure_file_dir(proxy_path)
            proxy_path.touch()
                
        # Check if the file has content
        if proxy_path.exists():
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
        return await self.token_handler.get_token_data(contract_address)
    
    def get_token_info_sync(self, contract_address: str) -> Dict[str, Any]:
        """
        Synchronous version of get_token_info.
        
        Args:
            contract_address: Token contract address
            
        Returns:
            Token information
        """
        return self.token_handler._get_token_info_sync(contract_address)
    
    def get_new_tokens(self) -> List[Dict[str, Any]]:
        """Get new token listings."""
        return self.gmgn_client.getNewTokens()
    
    def get_completing_tokens(self) -> List[Dict[str, Any]]:
        """Get completing token listings."""
        return self.gmgn_client.getCompletingTokens()
    
    def get_soaring_tokens(self) -> List[Dict[str, Any]]:
        """Get soaring token listings."""
        return self.gmgn_client.getSoaringTokens()
    
    def get_bonded_tokens(self) -> List[Dict[str, Any]]:
        """Get bonded token listings."""
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
            
            # Call Dragon's BulkWalletChecker
            checker = self.BulkWalletChecker(
                wallets=valid_wallets,
                skip_wallets=skip_wallets,
                output_dir=output_dir,
                proxies=use_proxies,
                threads=threads
            )
            
            # Run the checker (returns status code and files created)
            checker_result = checker.run()
            
            # Process the result
            if checker_result[0] != 0:
                logger.error(f"BulkWalletChecker failed with status code {checker_result[0]}")
                return {"success": False, "error": f"BulkWalletChecker failed with status code {checker_result[0]}"}
            
            # Load and process the wallet data from files
            wallet_data = {}
            for wallet in valid_wallets:
                wallet_file = Path(output_dir) / f"{wallet}.json"
                if wallet_file.exists():
                    try:
                        with open(wallet_file, "r") as f:
                            wallet_data[wallet] = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Error decoding wallet data file for {wallet}")
                else:
                    logger.warning(f"No data file found for wallet {wallet}")
            
            # Create the result dictionary
            result = {
                "success": True,
                "wallets_processed": len(valid_wallets),
                "wallet_data": wallet_data,
                "files_created": checker_result[1] if len(checker_result) > 1 else [],
                "timestamp": int(time.time()),
                "duration": round(time.time() - start_time, 2)
            }
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in solana_wallet_checker: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "wallets_processed": 0,
                "timestamp": int(time.time()),
                "duration": round(time.time() - start_time, 2)
            }

    def import_solana_wallets(self, filename: str, directory: str = None) -> bool:
        """
        Import Solana wallets from a file.
        
        Args:
            filename: Name of the file containing wallet addresses
            directory: Directory where the file is located (optional)
            
        Returns:
            True if successful, False otherwise
        """
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
    
    def import_ethereum_wallets(self, filename: str, directory: str = None) -> bool:
        """
        Import Ethereum wallets from a file.
        
        Args:
            filename: Name of the file containing wallet addresses
            directory: Directory where the file is located (optional)
            
        Returns:
            True if successful, False otherwise
        """
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