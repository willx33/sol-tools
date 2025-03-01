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

# Properly use the logs directory structure
from ...core.config import LOG_DIR
LOGS_DIR = LOG_DIR / "dragon"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Import Dragon modules
import Dragon
from Dragon import (
    utils, BundleFinder, ScanAllTx, BulkWalletChecker, TopTraders,
    TimestampTransactions, purgeFiles, CopyTradeWalletFinder, TopHolders,
    EarlyBuyers, checkProxyFile, EthBulkWalletChecker, EthTopTraders,
    EthTimestampTransactions, EthScanAllTx, GMGN
)
DRAGON_IMPORTS_SUCCESS = True


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
        proxies_file = INPUT_DATA_DIR / "dragon" / "proxies" / "proxies.txt"
        
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
    
    def __init__(self):
        """Initialize the Dragon adapter."""
        from ...core.config import INPUT_DATA_DIR, OUTPUT_DATA_DIR
        
        # Setup input and output directories
        self.input_data_dir = INPUT_DATA_DIR / "dragon"
        self.output_data_dir = OUTPUT_DATA_DIR / "dragon"
        
        # Define the new directory structure
        self.ethereum_input_dir = self.input_data_dir / "ethereum" / "wallet_lists"
        self.solana_input_dir = self.input_data_dir / "solana" / "wallet_lists"
        self.proxies_dir = self.input_data_dir / "proxies"
        
        self.ethereum_output_dirs = {
            "wallet_analysis": self.output_data_dir / "ethereum" / "wallet_analysis",
            "top_traders": self.output_data_dir / "ethereum" / "top_traders",
            "top_holders": self.output_data_dir / "ethereum" / "top_holders",
            "early_buyers": self.output_data_dir / "ethereum" / "early_buyers"
        }
        
        self.solana_output_dirs = {
            "wallet_analysis": self.output_data_dir / "solana" / "wallet_analysis",
            "top_traders": self.output_data_dir / "solana" / "top_traders",
            "top_holders": self.output_data_dir / "solana" / "top_holders",
            "early_buyers": self.output_data_dir / "solana" / "early_buyers"
        }
        
        self.token_info_dir = self.output_data_dir / "token_info"
        
        # Set up threading defaults
        self.default_threads = 40
        self.max_threads = 100
        
        # Set up async clients
        self.gmgn_client = GMGN_Client()
        self.token_handler = TokenDataHandler()
        
        # Initialize components from the original Dragon library if available
        self._init_dragon_components()
    
    def _init_dragon_components(self):
        """Initialize components from Dragon modules."""
        # Initialize Dragon components
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
    
    def ensure_dragon_paths(self) -> None:
        """
        Ensure proper paths for Dragon operations within the input-data/output-data structure.
        """
        # Make sure our input/output directories for Dragon exist
        self.input_data_dir.mkdir(parents=True, exist_ok=True)
        self.output_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Make sure specific directories exist
        self.ethereum_input_dir.mkdir(parents=True, exist_ok=True)
        self.solana_input_dir.mkdir(parents=True, exist_ok=True)
        self.proxies_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the output directories
        for dir_path in self.ethereum_output_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        for dir_path in self.solana_output_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        self.token_info_dir.mkdir(parents=True, exist_ok=True)

    def check_proxy_file(self, create_if_missing: bool = True) -> bool:
        """
        Check if proxy file exists and has content.
        
        Args:
            create_if_missing: Create an empty proxy file if it doesn't exist
            
        Returns:
            True if proxies are available, False otherwise
        """
        proxy_path = self.proxies_dir / "proxies.txt"
        
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
        Analyze PnL and win rates for multiple wallets.
        
        Args:
            wallets: List of wallet addresses or space-separated string of addresses
            threads: Number of threads to use for processing
            skip_wallets: Skip wallets with no buys in last 30 days
            use_proxies: Use proxies for API requests
            
        Returns:
            Dictionary with wallet analysis data or error information
        """
        try:
            self.ensure_dragon_paths()
        except Exception:
            return {"success": False, "error": "Could not ensure Dragon paths"}
            
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
            
            # Use the real wallet checker - if unavailable or fails, return error
            if not self.wallet_checker:
                return {"success": False, "error": "Wallet checker functionality not available"}
                
            try:
                data = self.wallet_checker.fetchWalletData(
                    valid_wallets, 
                    threads=threads,
                    skipWallets=skip_wallets,
                    useProxies=use_proxies
                )
                
                if data:
                    return {"success": True, "data": data}
                else:
                    return {"success": False, "error": "No data returned from wallet checker"}
            except Exception as e:
                return {"success": False, "error": f"Error during wallet analysis: {str(e)}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}