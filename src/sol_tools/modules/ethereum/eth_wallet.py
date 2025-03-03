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

import aiohttp
import httpx

# Setup logging
logger = logging.getLogger(__name__)

# Remove any existing handlers to prevent duplication
for handler in list(logger.handlers):
    logger.removeHandler(handler)

# Add a NullHandler by default to prevent logging warnings
logger.addHandler(logging.NullHandler())

# Configure logging based on test mode
IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

if IN_TEST_MODE:
    # Set critical+1 level (higher than any standard level)
    logger.setLevel(logging.CRITICAL + 1)
else:
    # In non-test mode, add a StreamHandler for console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

# Constants for Ethereum API
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
        """Get the input directory for Ethereum wallet lists."""
        # When used as a module in sol-tools
        if 'sol_tools' in sys.modules:
            from ...core.config import INPUT_DATA_DIR
            return INPUT_DATA_DIR / "api" / "ethereum" / "wallets"
        # When used standalone
        else:
            root = Config.get_project_root()
            return root / "data" / "input-data" / "api" / "ethereum" / "wallets"
    
    @staticmethod
    def get_output_dir() -> Path:
        """Get the output directory for Ethereum wallet analysis."""
        # When used as a module in sol-tools
        if 'sol_tools' in sys.modules:
            from ...core.config import OUTPUT_DATA_DIR
            return OUTPUT_DATA_DIR / "api" / "ethereum" / "wallet-analysis"
        # When used standalone
        else:
            root = Config.get_project_root()
            return root / "data" / "output-data" / "api" / "ethereum" / "wallet-analysis"
    
    @staticmethod
    def ensure_dir_exists(directory: Path) -> Path:
        """Ensure a directory exists and return its path."""
        directory.mkdir(parents=True, exist_ok=True)
        return directory

# Show progress bar
def show_progress_bar(iteration, total, prefix='', suffix='', length=30, fill='█'):
    """Display a progress bar in the console."""
    if total == 0:
        total = 1  # Avoid division by zero
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

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
            await asyncio.sleep(Config.RATE_LIMIT_DELAY)
            
            # Use the proper timeout object
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"HTTP {response.status}: {error_text[:200]}")
                    if retry < Config.MAX_RETRIES - 1:
                        # Use random delay within range for better retry behavior
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"API error for {address}: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        # Use random delay within range for better retry behavior
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
                    "balance_eth": balance_eth
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting balance for {address}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
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
            await asyncio.sleep(Config.RATE_LIMIT_DELAY)
            
            # Use the proper timeout object
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"HTTP {response.status}: {error_text[:200]}")
                    if retry < Config.MAX_RETRIES - 1:
                        # Use random delay within range for better retry behavior
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_msg = data.get("message", "Unknown error")
                    
                    # If no transactions found, this is actually OK
                    if "No transactions found" in error_msg:
                        return {
                            "status": "success",
                            "address": address,
                            "transactions": []
                        }
                    
                    logger.error(f"API error for {address}: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        # Use random delay within range for better retry behavior
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "address": address, "error": error_msg}
                
                # Process transactions
                transactions = data.get("result", [])
                
                # Format transactions
                formatted_txs = []
                for tx in transactions:
                    # Convert wei to ether
                    value_wei = int(tx.get("value", "0"))
                    value_eth = value_wei / 1e18
                    
                    # Format timestamp
                    timestamp = int(tx.get("timeStamp", "0"))
                    date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    formatted_txs.append({
                        "hash": tx.get("hash"),
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "value_wei": value_wei,
                        "value_eth": value_eth,
                        "timestamp": timestamp,
                        "date": date,
                        "gas": int(tx.get("gas", "0")),
                        "gas_price": int(tx.get("gasPrice", "0")),
                        "is_error": tx.get("isError", "0") == "1"
                    })
                
                return {
                    "status": "success",
                    "address": address,
                    "transactions": formatted_txs
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting transactions for {address}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "address": address, "error": str(e)}
    
    return {"status": "error", "address": address, "error": "Max retries exceeded"}

async def process_wallet(session: aiohttp.ClientSession, address: str) -> Dict[str, Any]:
    """Process a single wallet - get balance and transactions."""
    if not is_valid_eth_address(address):
        return {
            "status": "error", 
            "address": address, 
            "error": "Invalid Ethereum address format"
        }
    
    # Get balance and transactions in parallel
    balance_task = asyncio.create_task(get_wallet_balance(session, address))
    txs_task = asyncio.create_task(get_wallet_transactions(session, address))
    
    balance_result = await balance_task
    txs_result = await txs_task
    
    # Combine results
    if balance_result.get("status") == "error":
        return balance_result
    
    if txs_result.get("status") == "error":
        return txs_result
    
    # Create the combined result
    result = {
        "status": "success",
        "address": address,
        "balance_wei": balance_result.get("balance_wei", 0),
        "balance_eth": balance_result.get("balance_eth", 0),
        "transactions": txs_result.get("transactions", [])
    }
    
    return result

async def process_wallets(wallets: List[str], output_dir: Path, threads: int = 10, test_mode: bool = False) -> bool:
    """Process a list of wallet addresses and save the results."""
    # Create sessions and process wallets in batches
    processed_count = 0
    total_wallets = len(wallets)
    results = []
    
    if not test_mode:
        print(f"Processing {total_wallets} Ethereum wallets...")
    
    async with aiohttp.ClientSession() as session:
        # Process wallets in parallel with concurrency control
        semaphore = asyncio.Semaphore(threads)
        
        async def process_with_semaphore(wallet):
            async with semaphore:
                return await process_wallet(session, wallet)
        
        # Create tasks for all wallets
        tasks = [process_with_semaphore(wallet) for wallet in wallets]
        
        # Process all tasks and collect results
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            try:
                result = await task
                results.append(result)
                processed_count += 1
                
                if not test_mode:
                    # Show progress
                    show_progress_bar(processed_count, total_wallets, 
                                     prefix=f'Progress:', 
                                     suffix=f'Complete ({processed_count}/{total_wallets})', 
                                     length=40)
            except Exception as e:
                logger.error(f"Error processing wallet: {str(e)}")
                continue
    
    # Save results to output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use a more descriptive output filename
    wallets_count = len(wallets)
    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = wallets_count - success_count
    
    # Add "test_" prefix in test mode
    prefix = "test_" if test_mode else ""
    output_file = output_dir / f"{prefix}eth_wallet_results_{timestamp}_{wallets_count}wallets_{success_count}success_{error_count}errors.json"
    
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        if not test_mode:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"\n✅ Results saved to {output_file}")
            print(f"   File size: {file_size_mb:.2f} MB")
            print(f"   Wallets processed: {wallets_count}")
            print(f"   Successful: {success_count}")
            print(f"   Errors: {error_count}")
        
        # Remove test files after saving to avoid cluttering
        if test_mode and os.path.exists(output_file):
            os.remove(output_file)
            
        return True
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        if not test_mode:
            print(f"\n❌ Error saving results: {str(e)}")
        return False

def run_wallet_checker_in_thread(wallets: List[str], output_dir: Path, threads: int = 10, test_mode: bool = False) -> bool:
    """
    Run the wallet checker in a separate thread with its own event loop.
    This is a workaround for "Cannot run the event loop while another loop is running" errors.
    """
    result_queue = queue.Queue()
    
    def thread_worker():
        # Create a new event loop for this thread
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        
        try:
            # Run the async function in this thread's event loop
            result = thread_loop.run_until_complete(process_wallets(wallets, output_dir, threads, test_mode))
            result_queue.put(("success", result))
        except Exception as e:
            result_queue.put(("error", str(e)))
        finally:
            thread_loop.close()
    
    # Start the thread and wait for it to complete
    thread = threading.Thread(target=thread_worker)
    thread.daemon = True
    thread.start()
    thread.join()
    
    # Get the result
    if not result_queue.empty():
        status, result = result_queue.get()
        if status == "success":
            return result
        else:
            if not test_mode:
                print(f"Error in wallet checker: {result}")
            return False
    else:
        if not test_mode:
            print("No result returned from thread")
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

async def standalone_test(wallet_addresses=None, threads=2):
    """Run a standalone test of the wallet checker."""
    # Set test mode flag
    os.environ["TEST_MODE"] = "1"
    test_mode = True
    
    # Use default test wallets if none provided
    if not wallet_addresses:
        wallet_addresses = [
            "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Vitalik's address
            "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"   # Another well-known address
        ]
    
    # Ensure we have a list of wallets
    if isinstance(wallet_addresses, str):
        wallet_addresses = [wallet_addresses]
    
    # Set up output directory
    output_dir = Config.get_output_dir()
    Config.ensure_dir_exists(output_dir)
    
    print(f"🧪 Running test mode on {len(wallet_addresses)} wallets...")
    
    # Create instance and run
    checker = EthWalletChecker(
        wallets=wallet_addresses,
        threads=threads,
        output_dir=output_dir,
        test_mode=test_mode
    )
    
    result = checker.run()
    
    if result:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed")
    
    return 0 if result else 1

def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ethereum Wallet Checker')
    parser.add_argument('--wallet', '-w', type=str, help='Path to wallet list file')
    parser.add_argument('--threads', '-t', type=int, default=10, help='Number of threads to use')
    parser.add_argument('--output', '-o', type=str, help='Output directory (default: data/output-data/ethereum/wallet-analysis)')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # If in test mode, run the test
    if args.test:
        return asyncio.run(standalone_test(threads=args.threads))
    
    # Make sure we have a wallet file
    if not args.wallet:
        print("❌ No wallet file specified.")
        print("Please use --wallet/-w to specify a wallet list file.")
        return 1
    
    # Import wallets from file
    wallets = import_wallets_from_file(args.wallet)
    
    if not wallets:
        print("❌ No wallets found in the specified file.")
        return 1
    
    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Config.get_output_dir()
    
    Config.ensure_dir_exists(output_dir)
    
    # Create instance and run
    checker = EthWalletChecker(
        wallets=wallets,
        threads=args.threads,
        output_dir=output_dir
    )
    
    result = checker.run()
    
    return 0 if result else 1

# For standalone execution
if __name__ == "__main__":
    sys.exit(main()) 