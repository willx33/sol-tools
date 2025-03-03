"""
Standalone implementation of Ethereum Wallet Checker functionality.
This module can be imported directly without dependencies on other modules.
"""

import asyncio
import logging
import os
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import threading
import queue
from typing import Dict, List, Any, Optional, Union, Tuple
import argparse
import re
import random
import tls_client
import cloudscraper
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import contextlib
import io

import aiohttp
import httpx

# EXTREME AND AGGRESSIVE SILENCER
# This code runs immediately at import time
# It will detect if we're in test mode and silence EVERYTHING
if os.environ.get("TEST_MODE") == "1":
    # Silence ALL loggers
    logging.basicConfig(level=logging.CRITICAL + 1)
    
    # Disable the root logger completely
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL + 1)
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    root_logger.addHandler(logging.NullHandler())
    
    # Create a do-nothing handler
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    
    # Replace all print functions with a no-op version
    def silent_print(*args, **kwargs):
        pass
    print = silent_print
    
    # Silence all known noisy modules
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.setLevel(logging.CRITICAL + 1)
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.addHandler(NullHandler())

# Now set up our own module logging AFTER the silencer
logger = logging.getLogger(__name__)

# Global flag to track if we're in test mode
IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

# Completely disable all logging in test mode immediately
if IN_TEST_MODE:
    # Disable all loggers
    logging.getLogger().setLevel(logging.CRITICAL + 1)
    
    # Disable specific loggers that might be used
    for name in ['asyncio', 'aiohttp', 'urllib3', 'sol_tools']:
        logging.getLogger(name).setLevel(logging.CRITICAL + 1)
        logging.getLogger(name).addHandler(NullHandler())
    
    # Set our module logger to do nothing
    logger.setLevel(logging.CRITICAL + 1)
    logger.addHandler(NullHandler())

@contextlib.contextmanager
def suppress_all_output():
    """Context manager to suppress both stdout and stderr output."""
    if not IN_TEST_MODE:
        yield  # If not in test mode, don't suppress anything
        return
        
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Create null streams
    null_out = open(os.devnull, 'w')
    
    try:
        # Redirect stdout and stderr to null
        sys.stdout = null_out
        sys.stderr = null_out
        yield
    finally:
        # Restore stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        null_out.close()

def show_progress_bar(iteration, total, prefix='', suffix='', length=30, fill='█'):
    """
    Call in a loop to create terminal progress bar
    """
    if IN_TEST_MODE:
        return  # Do nothing in test mode
        
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()

class Config:
    """Configuration for Ethereum API calls."""
    
    # API settings
    ETH_API_KEY = os.environ.get("ETHEREUM_API_KEY", "")
    ETH_ENDPOINT = "https://api.etherscan.io/api"
    
    # Request settings
    REQUEST_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY_MIN = 1.0  # seconds
    RETRY_DELAY_MAX = 3.0  # seconds
    
    # Thread settings
    DEFAULT_THREADS = 10
    
    # Rate limiting
    RATE_LIMIT_DELAY = 0.2  # seconds between API calls
    
    # Data directories
    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory."""
        # When used as a module in sol-tools
        if 'sol_tools' in sys.modules:
            from ...core.config import ROOT_DIR
            return ROOT_DIR
        # When used standalone
        else:
            # Try to find the project root based on common markers
            current_dir = Path(__file__).resolve().parent
            for _ in range(10):  # Limit the search depth
                if (current_dir / ".git").exists() or (current_dir / "pyproject.toml").exists():
                    return current_dir
                if current_dir.parent == current_dir:  # Reached the root of the filesystem
                    break
                current_dir = current_dir.parent
            # Fallback to the user's home directory if we can't find the project root
            return Path.home() / "sol-tools"
    
    @staticmethod
    def get_input_dir() -> Path:
        """Get the input directory for wallet lists."""
        if 'sol_tools' in sys.modules:
            from ...core.config import INPUT_DATA_DIR
            return INPUT_DATA_DIR / "ethereum" / "wallets"
        return Path.home() / "sol-tools" / "data" / "input-data" / "ethereum" / "wallets"
    
    @staticmethod
    def get_output_dir() -> Path:
        """Get the output directory for wallet analysis."""
        if 'sol_tools' in sys.modules:
            from ...core.config import OUTPUT_DATA_DIR
            return OUTPUT_DATA_DIR / "ethereum" / "wallets"
        return Path.home() / "sol-tools" / "data" / "output-data" / "ethereum" / "wallets"
    
    @staticmethod
    def ensure_dir_exists(directory: Path) -> Path:
        """Ensure a directory exists and return its path."""
        directory.mkdir(parents=True, exist_ok=True)
        return directory

# Function to validate Ethereum address
def is_valid_eth_address(address: str) -> bool:
    """Check if the given string is a valid Ethereum address."""
    # Basic validation - should start with 0x and be 42 chars long (0x + 40 hex chars)
    if not address.startswith('0x') or len(address) != 42:
        return False
    
    # Check if address contains only hex characters after 0x
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False

async def get_wallet_balance(session: aiohttp.ClientSession, address: str) -> Dict[str, Any]:
    """Get the ETH balance for a wallet address."""
    params = {
        'module': 'account',
        'action': 'balance',
        'address': address,
        'tag': 'latest',
        'apikey': Config.ETH_API_KEY
    }
    
    url = Config.ETH_ENDPOINT
    
    for retry in range(Config.MAX_RETRIES):
        try:
            # Add delay for rate limiting
            await asyncio.sleep(Config.RATE_LIMIT_DELAY * (1 + retry))
            
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', Config.RETRY_DELAY_MIN * 2))
                    if not IN_TEST_MODE:
                        print(f"⚠️ Rate limited for {address}, waiting {retry_after}s before retry {retry+1}/{Config.MAX_RETRIES}")
                    logger.warning(f"Rate limited for {address}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"HTTP {response.status}: {error_text[:200]}"
                    if not IN_TEST_MODE:
                        print(f"❌ Error fetching balance for {address}: {error_msg}")
                    logger.error(f"Error fetching balance for {address}: {error_msg}")
                    
                    if retry < Config.MAX_RETRIES - 1:
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": error_msg}
                
                try:
                    data = await response.json()
                except Exception as e:
                    if not IN_TEST_MODE:
                        print(f"❌ Error parsing JSON response: {str(e)}")
                    logger.error(f"Error parsing JSON for {address}: {str(e)}")
                    if retry < Config.MAX_RETRIES - 1:
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": f"JSON parse error: {str(e)}"}
                
                if data.get("status") != "1":
                    error_msg = data.get("message", "Unknown error")
                    if not IN_TEST_MODE:
                        print(f"❌ API error for {address}: {error_msg}")
                    logger.error(f"API error for {address}: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": error_msg}
                
                # Convert wei to ether
                balance_wei = int(data.get("result", "0"))
                balance_eth = balance_wei / 1e18
                
                return {
                    "status": "success",
                    "address": address,
                    "balance_wei": balance_wei,
                    "balance_eth": balance_eth,
                    "timestamp": int(time.time())
                }
                
        except asyncio.TimeoutError:
            if not IN_TEST_MODE:
                print(f"❌ Timeout getting balance for {address}")
            logger.error(f"Timeout getting balance for {address}")
            if retry < Config.MAX_RETRIES - 1:
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": "Timeout"}
            
        except Exception as e:
            if not IN_TEST_MODE:
                print(f"❌ Error getting balance for {address}: {str(e)}")
            logger.error(f"Error getting balance for {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": str(e)}
    
    return {"status": "error", "address": address, "error": "Max retries exceeded"}

async def get_wallet_transactions(session: aiohttp.ClientSession, address: str) -> Dict[str, Any]:
    """Get the recent transactions for a wallet address."""
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': '0',
        'endblock': '99999999',
        'page': '1',
        'offset': '10',  # Get last 10 transactions
        'sort': 'desc',  # Latest first
        'apikey': Config.ETH_API_KEY
    }
    
    url = Config.ETH_ENDPOINT
    
    for retry in range(Config.MAX_RETRIES):
        try:
            # Add delay for rate limiting
            await asyncio.sleep(Config.RATE_LIMIT_DELAY * (1 + retry))
            
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', Config.RETRY_DELAY_MIN * 2))
                    if not IN_TEST_MODE:
                        print(f"⚠️ Rate limited for {address}, waiting {retry_after}s before retry {retry+1}/{Config.MAX_RETRIES}")
                    logger.warning(f"Rate limited for {address}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"HTTP {response.status}: {error_text[:200]}"
                    if not IN_TEST_MODE:
                        print(f"❌ Error fetching transactions for {address}: {error_msg}")
                    logger.error(f"Error fetching transactions for {address}: {error_msg}")
                    
                    if retry < Config.MAX_RETRIES - 1:
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": error_msg}
                
                try:
                    data = await response.json()
                except Exception as e:
                    if not IN_TEST_MODE:
                        print(f"❌ Error parsing JSON response: {str(e)}")
                    logger.error(f"Error parsing JSON for {address}: {str(e)}")
                    if retry < Config.MAX_RETRIES - 1:
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": f"JSON parse error: {str(e)}"}
                
                if data.get("status") != "1":
                    error_msg = data.get("message", "Unknown error")
                    if not IN_TEST_MODE:
                        print(f"❌ API error for {address}: {error_msg}")
                    logger.error(f"API error for {address}: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": error_msg}
                
                transactions = data.get("result", [])
                
                return {
                    "status": "success",
                    "address": address,
                    "transactions": transactions,
                    "timestamp": int(time.time())
                }
                
        except asyncio.TimeoutError:
            if not IN_TEST_MODE:
                print(f"❌ Timeout getting transactions for {address}")
            logger.error(f"Timeout getting transactions for {address}")
            if retry < Config.MAX_RETRIES - 1:
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": "Timeout"}
            
        except Exception as e:
            if not IN_TEST_MODE:
                print(f"❌ Error getting transactions for {address}: {str(e)}")
            logger.error(f"Error getting transactions for {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": str(e)}
    
    return {"status": "error", "address": address, "error": "Max retries exceeded"}

async def process_wallet(session: aiohttp.ClientSession, address: str) -> Dict[str, Any]:
    """Process a single wallet address."""
    if not is_valid_eth_address(address):
        return {"status": "error", "address": address, "error": "Invalid Ethereum address"}
    
    # Get balance and transactions concurrently
    balance_task = asyncio.create_task(get_wallet_balance(session, address))
    transactions_task = asyncio.create_task(get_wallet_transactions(session, address))
    
    balance_result, transactions_result = await asyncio.gather(balance_task, transactions_task)
    
    # If either call failed, return the error
    if balance_result["status"] == "error":
        return balance_result
    if transactions_result["status"] == "error":
        return transactions_result
    
    # Combine the results
    return {
        "status": "success",
        "address": address,
        "balance_wei": balance_result["balance_wei"],
        "balance_eth": balance_result["balance_eth"],
        "transactions": transactions_result["transactions"],
        "timestamp": int(time.time())
    }

async def process_wallets(wallets: List[str], output_dir: Optional[Path] = None, threads: int = 10, test_mode: bool = False) -> bool:
    """Process a list of wallet addresses."""
    if not wallets:
        if not IN_TEST_MODE:
            print("❌ No wallet addresses provided")
        logger.error("No wallet addresses provided")
        return False
    
    if output_dir is None:
        output_dir = Config.get_output_dir()
    
    Config.ensure_dir_exists(output_dir)
    
    # Create timestamp for output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"wallet_analysis_{timestamp}.json"
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(threads)
    
    async def process_with_semaphore(wallet):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                return await process_wallet(session, wallet)
    
    if not IN_TEST_MODE:
        print(f"🔍 Processing {len(wallets)} wallets...")
    
    results = []
    total_wallets = len(wallets)
    processed = 0
    
    # Process wallets concurrently with semaphore
    tasks = [process_with_semaphore(wallet) for wallet in wallets]
    for task in asyncio.as_completed(tasks):
        result = await task
        results.append(result)
        processed += 1
        if not IN_TEST_MODE:
            show_progress_bar(processed, total_wallets, prefix='Progress:', suffix='Complete')
    
    # Save results
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        if not IN_TEST_MODE:
            print(f"\n✅ Results saved to {output_file}")
        return True
    except Exception as e:
        if not IN_TEST_MODE:
            print(f"\n❌ Error saving results: {str(e)}")
        logger.error(f"Error saving results: {str(e)}")
        return False

def run_wallet_checker_in_thread(wallets: List[str], output_dir: Optional[Path] = None, threads: int = 10, test_mode: bool = False) -> bool:
    """Run the wallet checker in a separate thread."""
    def thread_worker():
        return asyncio.run(process_wallets(wallets, output_dir, threads, test_mode))
    
    try:
        return thread_worker()
    except Exception as e:
        if not IN_TEST_MODE:
            print(f"❌ Error running wallet checker: {str(e)}")
        logger.error(f"Error running wallet checker: {str(e)}")
        return False

def import_wallets_from_file(file_path: Union[str, Path]) -> List[str]:
    """
    Import wallet addresses from a file.
    
    Args:
        file_path: Path to the file containing wallet addresses
        
    Returns:
        List of wallet addresses
    """
    wallets = []
    path = Path(file_path)
    
    if not path.exists():
        print(f"Wallet file not found: {path}")
        return wallets
    
    try:
        with open(path, 'r') as f:
            for line in f:
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Add the wallet to the list
                wallets.append(line)
        
        return wallets
    except Exception as e:
        print(f"Error reading wallet file {path}: {e}")
        return []

ua = UserAgent(os='linux', browsers=['firefox'])

class EthWalletChecker:
    """Ethereum Wallet Checker class."""
    
    def __init__(self, wallets=None, skip_wallets=False, output_dir=None, proxies=False, threads=10, test_mode=False):
        """
        Initialize the Ethereum Wallet Checker.
        
        Args:
            wallets: List of wallet addresses to check
            skip_wallets: Flag to skip wallet importing
            output_dir: Directory to save results
            proxies: Flag to use proxies
            threads: Number of threads to use
            test_mode: Run in test mode (no output)
        """
        # Initialize module logger to prevent handler errors
        self.logger = logging.getLogger(__name__)
        
        # Remove any existing handlers to prevent duplication
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
        
        # Add a NullHandler by default
        self.logger.addHandler(logging.NullHandler())
        
        # Set logging level based on test mode
        if test_mode or IN_TEST_MODE:
            self.logger.setLevel(logging.CRITICAL + 1)
        else:
            # In non-test mode, add a StreamHandler for console output
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)
        
        self.wallets = wallets or []
        self.skip_wallets = skip_wallets
        
        # Handle output directory with proper defaults
        if output_dir is None:
            self.output_dir = Config.get_output_dir()
        else:
            self.output_dir = Path(output_dir)
        
        self.proxies = proxies
        self.threads = threads
        self.test_mode = test_mode or IN_TEST_MODE
        
        # Log initialization
        self.logger.debug("EthWalletChecker initialized with %d wallets", len(self.wallets))
        
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.cloudScraper = cloudscraper.create_scraper()
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s
        self.skippedWallets = 0
        self.results = []
    
    def getTokenDistro(self, wallet: str):
        url = f"https://gmgn.ai/defi/quotation/v1/rank/eth/wallets/{wallet}/unique_token_7d?interval=30d"
        headers = {
            "User-Agent": ua.random
        }
        retries = 3
        tokenDistro = []

        for attempt in range(retries):
            try:
                response = self.sendRequest.get(url, headers=headers).json()
                tokenDistro = response['data']['tokens']
                if tokenDistro:  
                    break
            except Exception:
                time.sleep(1)
            
            try:
                response = self.cloudScraper.get(url, headers=headers).json()
                tokenDistro = response['data']['tokens']
                if tokenDistro:
                    break
            except Exception:
                time.sleep(1)
        
        if not tokenDistro:
            return {
                "No Token Distribution Data": None
            }

        FiftyPercentOrMore = 0
        ZeroToFifty = 0
        FiftyTo100 = 0
        TwoToFour = 0
        FiveToSix = 0
        SixPlus = 0
        NegativeToFifty = 0 

        for profit in tokenDistro:
            total_profit_pnl = profit.get('total_profit_pnl')
            if total_profit_pnl is not None:
                profitMultiplier = total_profit_pnl * 100

                if profitMultiplier <= -50:
                    FiftyPercentOrMore += 1
                elif -50 < profitMultiplier < 0:
                    NegativeToFifty += 1
                elif 0 <= profitMultiplier < 50:
                    ZeroToFifty += 1
                elif 50 <= profitMultiplier < 199:
                    FiftyTo100 += 1
                elif 200 <= profitMultiplier < 499:
                    TwoToFour += 1
                elif 500 <= profitMultiplier < 600:
                    FiveToSix += 1
                elif profitMultiplier >= 600:
                    SixPlus += 1

        return {
            "-50% +": FiftyPercentOrMore,
            "0% - -50%": NegativeToFifty,
            "0 - 50%": ZeroToFifty,
            "50% - 199%": FiftyTo100,
            "200% - 499%": TwoToFour,
            "500% - 600%": FiveToSix,
            "600% +": SixPlus
        }

    def getWalletData(self, wallet: str, skipWallets: bool):
        url = f"https://gmgn.ai/defi/quotation/v1/smartmoney/eth/walletNew/{wallet}?period=7d"
        headers = {
            "User-Agent": ua.random
        }
        retries = 3
        
        for attempt in range(retries):
            try:
                response = self.sendRequest.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data['msg'] == "success":
                        data = data['data']
                        
                        if skipWallets:
                            if 'buy_30d' in data and isinstance(data['buy_30d'], (int, float)) and data['buy_30d'] > 0 and float(data['sol_balance']) >= 1.0:
                                return self.processWalletData(wallet, data, headers)
                            else:
                                self.skippedWallets += 1
                                print(f"[🐲] Skipped {self.skippedWallets} wallets", end="\r")
                                return None
                        else:
                            return self.processWalletData(wallet, data, headers)
            
            except Exception:
                print(f"[🐲] Error fetching data, trying backup...")
            
            try:
                response = self.cloudScraper.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data['msg'] == "success":
                        data = data['data']
                        
                        if skipWallets:
                            if 'buy_30d' in data and isinstance(data['buy_30d'], (int, float)) and data['buy_30d'] > 0 and float(data['sol_balance']) >= 1.0:
                                return self.processWalletData(wallet, data, headers)
                            else:
                                self.skippedWallets += 1
                                print(f"[🐲] Skipped {self.skippedWallets} wallets", end="\r")
                                return None
                        else:
                            return self.processWalletData(wallet, data, headers)
            
            except Exception:
                print(f"[🐲] Backup scraper failed, retrying...")
            
            time.sleep(1)
        
        print(f"[🐲] Failed to fetch data for wallet {wallet} after {retries} attempts.")
        return None

    def processWalletData(self, wallet, data, headers):
        direct_link = f"https://gmgn.ai/eth/address/{wallet}"
        total_profit_percent = f"{data['total_profit_pnl'] * 100:.2f}%" if data['total_profit_pnl'] is not None else "error"
        realized_profit_7d_usd = f"${data['realized_profit_7d']:,.2f}" if data['realized_profit_7d'] is not None else "error"
        realized_profit_30d_usd = f"${data['realized_profit_30d']:,.2f}" if data['realized_profit_30d'] is not None else "error"
        winrate_7d = f"{data['winrate'] * 100:.2f}%" if data['winrate'] is not None else "?"
        sol_balance = f"{float(data['sol_balance']):.2f}" if data['sol_balance'] is not None else "?"

        try:
            winrate_30data = self.sendRequest.get(f"https://gmgn.ai/defi/quotation/v1/smartmoney/eth/walletNew/{wallet}?period=30d", headers=headers).json()['data']
            winrate_30d = f"{winrate_30data['winrate'] * 100:.2f}%" if winrate_30data['winrate'] is not None else "?"
        except Exception:
            print(f"[🐲] Error fetching winrate 30d data, trying backup..")
            winrate_30data = self.cloudScraper.get(f"https://gmgn.ai/defi/quotation/v1/smartmoney/eth/walletNew/{wallet}?period=30d", headers=headers).json()['data']
            winrate_30d = f"{winrate_30data['winrate'] * 100:.2f}%" if winrate_30data['winrate'] is not None else "?"

        if "Skipped" in data.get("tags", []):
            return {
                "wallet": wallet,
                "tags": ["Skipped"],
                "directLink": direct_link
            }
        tokenDistro = self.getTokenDistro(wallet)

        try:
            tags = data['tags'] 
        except Exception:
            tags = "?"
        
        return {
            "wallet": wallet,
            "totalProfitPercent": total_profit_percent,
            "7dUSDProfit": realized_profit_7d_usd,
            "30dUSDProfit": realized_profit_30d_usd,
            "winrate_7d": winrate_7d,
            "winrate_30d": winrate_30d,
            "tags": tags,
            "sol_balance": sol_balance,
            "token_distribution": tokenDistro if tokenDistro else {},
            "directLink": direct_link
        }
    
    def fetchWalletData(self, wallets, threads, skipWallets):
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.getWalletData, wallet.strip(), skipWallets): wallet for wallet in wallets}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    self.results.append(result)

        result_dict = {}
        for result in self.results:
            wallet = result.get('wallet')
            if wallet:
                result_dict[wallet] = result
                result.pop('wallet', None)  
            else:
                print(f"[🐲] Missing 'wallet' key in result: {result}")

        if self.results and 'token_distribution' in self.results[0]:
            token_dist_keys = self.results[0]['token_distribution'].keys()
        else:
            token_dist_keys = []  

        identifier = self.shorten(list(result_dict)[0])
        filename = f"{identifier}_{random.randint(1111, 9999)}.csv"

        # Use our project's data structure
        output_dir = Path(os.getcwd()) / "data" / "output-data" / "ethereum" / "wallet-analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        path = output_dir / f"wallets_{filename}"

        with open(path, 'w', newline='') as outfile:
            writer = csv.writer(outfile)

            header = ['Identifier'] + list(next(iter(result_dict.values())).keys())

            if 'token_distribution' in header:
                header.remove('token_distribution')

            header.extend(token_dist_keys)

            writer.writerow(header)

            for key, value in result_dict.items():
                row = [key]
                for h in header[1:]:
                    if h in value:
                        row.append(value[h])
                    elif 'token_distribution' in value and h in value['token_distribution']:
                        row.append(value['token_distribution'][h])
                    else:
                        row.append(None)
                writer.writerow(row)

        print(f"[🐲] Saved data for {len(result_dict.items())} wallets to {filename}")

    def run(self) -> bool:
        """Run the wallet checker and save results."""
        if not self.test_mode:
            print(f"Checking {len(self.wallets)} Ethereum wallets with {self.threads} threads")
        
        # Validate we have wallets to check
        if not self.wallets:
            if not self.test_mode:
                print("No wallets to check!")
            return False
        
        # Make sure output directory exists
        Config.ensure_dir_exists(self.output_dir)
        
        # Process wallets
        self.fetchWalletData(self.wallets, self.threads, self.skip_wallets)
        
        return True

async def standalone_test(test_addresses: Optional[List[str]] = None) -> bool:
    """Run a standalone test of the wallet checker functionality."""
    with suppress_all_output():
        # Use test addresses or a default test address
        if not test_addresses:
            test_addresses = [
                "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Vitalik's address
                "0x1db3439a222c519ab44bb1144fc28167b4fa6ee6"   # Binance cold wallet
            ]
        
        # Create test output directory
        test_output_dir = Config.get_output_dir() / "test_output"
        Config.ensure_dir_exists(test_output_dir)
        
        try:
            # Process test wallets
            success = await process_wallets(test_addresses, test_output_dir, threads=2, test_mode=True)
            
            # Clean up test files
            if success:
                for file in test_output_dir.glob("wallet_analysis_*.json"):
                    try:
                        os.remove(file)
                    except Exception:
                        pass
                try:
                    os.rmdir(test_output_dir)
                except Exception:
                    pass
            
            return success
            
        except Exception as e:
            logger.error(f"Error in standalone test: {str(e)}")
            return False

def main():
    """Main entry point for standalone usage."""
    parser = argparse.ArgumentParser(description="Ethereum Wallet Checker")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--input", type=str, help="Input file with wallet addresses (one per line)")
    parser.add_argument("--output-dir", type=str, help="Output directory for results")
    parser.add_argument("--threads", type=int, default=10, help="Number of concurrent threads")
    args = parser.parse_args()
    
    if args.test:
        os.environ["TEST_MODE"] = "1"
        success = asyncio.run(standalone_test())
        sys.exit(0 if success else 1)
    
    # Normal operation mode
    if not args.input:
        print("Error: Please provide an input file with wallet addresses")
        sys.exit(1)
    
    try:
        # Read wallet addresses from input file
        with open(args.input, 'r') as f:
            wallets = [line.strip() for line in f if line.strip()]
        
        # Set output directory
        output_dir = Path(args.output_dir) if args.output_dir else Config.get_output_dir()
        
        # Run the wallet checker
        success = run_wallet_checker_in_thread(wallets, output_dir, args.threads)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 