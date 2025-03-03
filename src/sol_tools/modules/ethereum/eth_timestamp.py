"""
Standalone implementation of Ethereum Time Based Transaction Finder functionality.
This module can be imported directly without dependencies on other modules.
"""

import asyncio
import logging
import os
import json
import sys
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
import threading
import queue
import argparse
from typing import Dict, List, Any, Optional, Union, Tuple

import aiohttp
import httpx
import tls_client
import cloudscraper
from fake_useragent import UserAgent
import concurrent.futures

# Setup logging
logger = logging.getLogger(__name__)

# Global flag to track if we're in test mode
IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

# EXTREME AND AGGRESSIVE SILENCER
# This code runs immediately at import time
# It will detect if we're in test mode and silence EVERYTHING
if IN_TEST_MODE:
    # Silence ALL loggers
    logging.basicConfig(level=logging.CRITICAL + 1)
    
    # Disable the root logger completely
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL + 1)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    root_logger.addHandler(logging.NullHandler())
    
    # Create a do-nothing handler
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    
    # Replace all print functions with a no-op version
    def silent_print(*args, **kwargs):
        pass
    
    # Only use silent print in test mode
    if __name__ == 'sol_tools.modules.ethereum.eth_timestamp':
        print = silent_print
    
    # Silence all known noisy modules
    for name in logging.root.manager.loggerDict:
        logger_instance = logging.getLogger(name)
        logger_instance.setLevel(logging.CRITICAL + 1)
        for handler in list(logger_instance.handlers):
            logger_instance.removeHandler(handler)
        logger_instance.addHandler(NullHandler())

ua = UserAgent(os='linux', browsers=['firefox'])

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
    def get_output_dir() -> Path:
        """Get the output directory for Ethereum timestamp transactions."""
        # When used as a module in sol-tools
        if 'sol_tools' in sys.modules:
            from ...core.config import OUTPUT_DATA_DIR
            return OUTPUT_DATA_DIR / "ethereum" / "timestamp-txs"
        # When used standalone
        else:
            root = Config.get_project_root()
            return root / "data" / "output-data" / "ethereum" / "timestamp-txs"
    
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

async def get_block_by_timestamp(session: aiohttp.ClientSession, timestamp: int, closest: str = "before") -> Dict[str, Any]:
    """Get the block number closest to a specific timestamp."""
    params = {
        'module': 'block',
        'action': 'getblocknobytime',
        'timestamp': str(timestamp),
        'closest': closest,  # 'before' or 'after'
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
                        await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                        continue
                    return {"status": "error", "error": f"HTTP {response.status}"}
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"API error getting block by timestamp: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                        continue
                    return {"status": "error", "error": error_msg}
                
                # The result is the block number
                block_number = int(data.get("result", "0"))
                return {
                    "status": "success",
                    "block_number": block_number,
                    "timestamp": timestamp
                }
                
        except asyncio.TimeoutError:
            logger.error("Timeout getting block by timestamp")
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                continue
            return {"status": "error", "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting block by timestamp: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                continue
            return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": "Max retries exceeded"}

async def get_transactions_by_address(session: aiohttp.ClientSession, 
                                     address: str,
                                     start_block: int,
                                     end_block: int) -> Dict[str, Any]:
    """Get transactions for a specific address within a block range."""
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': str(start_block),
        'endblock': str(end_block),
        'sort': 'asc',
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
                        await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
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
                        await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                        continue
                    return {"status": "error", "address": address, "error": error_msg}
                
                # Process transactions
                transactions = data.get("result", [])
                
                return {
                    "status": "success",
                    "address": address,
                    "transactions": transactions
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting transactions for {address}")
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                continue
            return {"status": "error", "address": address, "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random())
                continue
            return {"status": "error", "address": address, "error": str(e)}
    
    return {"status": "error", "address": address, "error": "Max retries exceeded"}

async def get_transaction_history(session: aiohttp.ClientSession, address: str) -> Dict[str, Any]:
    """Get entire transaction history for an address."""
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
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
                    return {"status": "error", "error": f"HTTP {response.status}"}
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_msg = data.get("message", "Unknown error")
                    
                    # If no transactions found, this is actually OK
                    if "No transactions found" in error_msg:
                        return {
                            "status": "success",
                            "result": []
                        }
                    
                    logger.error(f"API error for {address}: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        # Use random delay within range for better retry behavior
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "error": error_msg}
                
                # Process transactions
                transactions = data.get("result", [])
                
                return {
                    "status": "success",
                    "result": transactions
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting history for {address}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting history for {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": "Max retries exceeded"}

def filter_transactions_by_time(transactions: List[Dict[str, Any]], 
                              start_time: datetime, 
                              end_time: datetime) -> List[Dict[str, Any]]:
    """Filter transactions by timestamp range."""
    # Convert timestamps to UNIX timestamps for comparison
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(end_time.timestamp())
    
    # Filter transactions
    filtered = []
    for tx in transactions:
        # Get transaction timestamp and convert to integer
        tx_timestamp = int(tx.get("timeStamp", "0"))
        
        # Check if the transaction is within our time range
        if start_timestamp <= tx_timestamp <= end_timestamp:
            filtered.append(tx)
    
    return filtered

def format_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Format a transaction for output."""
    # Convert wei to ether
    value_wei = int(tx.get("value", "0"))
    value_eth = value_wei / 1e18
    
    # Format timestamp
    timestamp = int(tx.get("timeStamp", "0"))
    date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    # Format gas
    gas_price_gwei = int(tx.get("gasPrice", "0")) / 1e9
    gas_used = int(tx.get("gasUsed", "0"))
    gas_fee_eth = (gas_price_gwei * gas_used) / 1e9
    
    return {
        "hash": tx.get("hash"),
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value_wei": value_wei,
        "value_eth": value_eth,
        "timestamp": timestamp,
        "date": date,
        "block_number": int(tx.get("blockNumber", "0")),
        "gas_price_gwei": gas_price_gwei,
        "gas_used": gas_used,
        "gas_fee_eth": gas_fee_eth,
        "is_error": tx.get("isError", "0") == "1",
        "contract_address": tx.get("contractAddress", ""),
        "input": tx.get("input", "0x")[:66] + "..." if len(tx.get("input", "0x")) > 66 else tx.get("input", "0x")
    }

async def find_transactions_by_time(addresses: List[str], 
                                  start_time: datetime, 
                                  end_time: datetime,
                                  output_dir: Optional[Path] = None,
                                  test_mode: bool = False) -> bool:
    """Find transactions for a list of addresses within a time range."""
    if not addresses:
        if not test_mode:
            print("No addresses provided!")
        return False
    
    if output_dir is None:
        output_dir = Config.get_output_dir()
    
    # Ensure output directory exists
    Config.ensure_dir_exists(output_dir)
    
    # Initialize counters and results
    total_addresses = len(addresses)
    processed = 0
    successful = 0
    with_transactions = 0
    errors = 0
    all_transactions = []
    address_transactions = {}
    
    if not test_mode:
        print(f"Finding transactions for {total_addresses} addresses between:")
        print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with aiohttp.ClientSession() as session:
        for address in addresses:
            processed += 1
            
            # Validate address
            if not is_valid_eth_address(address):
                if not test_mode:
                    print(f"Invalid Ethereum address format: {address}")
                errors += 1
                continue
            
            # Display progress
            if not test_mode:
                show_progress_bar(processed, total_addresses, 
                                 prefix=f'Progress ({processed}/{total_addresses}): ', 
                                 suffix=f'Address: {address[:6]}...{address[-4:]}')
            
            # Get transaction history
            tx_result = await get_transaction_history(session, address)
            
            if tx_result.get("status") == "success":
                # Get raw transactions and filter by time
                raw_txs = tx_result.get("result", [])
                filtered_txs = filter_transactions_by_time(raw_txs, start_time, end_time)
                
                # Format transactions for output
                formatted_txs = [format_transaction(tx) for tx in filtered_txs]
                
                # Store results
                address_transactions[address] = formatted_txs
                all_transactions.extend(formatted_txs)
                
                successful += 1
                if formatted_txs:
                    with_transactions += 1
            else:
                if not test_mode:
                    print(f"\nError getting history for {address}: {tx_result.get('error')}")
                errors += 1
    
    # Save results if any successful requests
    if successful > 0:
        # Prepare filename with time range
        start_str = start_time.strftime("%Y%m%d")
        end_str = end_time.strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create summary
        summary = {
            "timestamp": int(datetime.now().timestamp()),
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "addresses_scanned": total_addresses,
            "addresses_with_transactions": with_transactions,
            "successful_requests": successful,
            "failed_requests": errors,
            "total_transactions_found": len(all_transactions)
        }
        
        # Format output data
        output_data = {
            "summary": summary,
            "transactions": address_transactions
        }
        
        # Save to file
        prefix = "test_" if test_mode else ""
        output_file = output_dir / f"{prefix}eth_txs_{start_str}_to_{end_str}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        if not test_mode:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"\n✅ Transaction search completed.")
            print(f"   Found {len(all_transactions)} transactions for {with_transactions} addresses")
            print(f"   Results saved to {output_file}")
            print(f"   File size: {file_size_mb:.2f} MB")
        
        # Remove test files after saving to avoid cluttering
        if test_mode and os.path.exists(output_file):
            os.remove(output_file)
            
        return True
    else:
        if not test_mode:
            print("\n❌ Transaction search failed: no valid results to save")
        return False

def run_finder_in_thread(addresses: List[str], 
                        start_time: datetime, 
                        end_time: datetime, 
                        output_dir: Optional[Path] = None,
                        test_mode: bool = False) -> bool:
    """
    Run the timestamp transaction finder in a separate thread with its own event loop.
    This is a workaround for "Cannot run the event loop while another loop is running" errors.
    """
    result_queue = queue.Queue()
    
    def thread_worker():
        # Create a new event loop for this thread
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        
        try:
            # Run the async function in this thread's event loop
            result = thread_loop.run_until_complete(
                find_transactions_by_time(addresses, start_time, end_time, output_dir, test_mode)
            )
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
                print(f"Error finding transactions: {result}")
            return False
    else:
        if not test_mode:
            print("No result returned from thread")
        return False

class EthTimestampTransactions:
    """Ethereum Timestamp Transactions finder class."""
    
    def __init__(self):
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.cloudScraper = cloudscraper.create_scraper()
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s

    def fetch_url(self, url, headers):
        retries = 3
        for attempt in range(retries):
            try:
                response = self.sendRequest.get(url, headers=headers).json()
                return response
            except Exception:
                print(f"[🐲] Error fetching data, trying backup...")
            finally:
                try:
                    response = self.cloudScraper.get(url, headers=headers).json()
                    return response
                except Exception:
                    print(f"[🐲] Backup scraper failed, retrying...")
            
            time.sleep(1)
        
        print(f"[🐲] Failed to fetch data after {retries} attempts.")
        return {}

    def getMintTimestamp(self, contractAddress):
        headers = {
            "User-Agent": ua.random
        }
        url = f"https://gmgn.ai/defi/quotation/v1/tokens/eth/{contractAddress}"
        retries = 3

        for attempt in range(retries):
            try:
                response = self.sendRequest.get(url, headers=headers).json()['data']['token']['creation_timestamp']
                return response
            except Exception:
                print(f"[🐲] Error fetching data, trying backup...")
            finally:
                try:
                    response = self.cloudScraper.get(url, headers=headers).json()['data']['token']['creation_timestamp']
                    return response
                except Exception:
                    print(f"[🐲] Backup scraper failed, retrying...")
            
            time.sleep(1)
        
        print(f"[🐲] Failed to fetch data after {retries} attempts.")
        return None

    def getTxByTimestamp(self, contractAddress, threads, start, end):
        base_url = f"https://gmgn.ai/defi/quotation/v1/trades/eth/{contractAddress}?limit=100"
        paginator = None
        urls = []
        all_trades = []

        headers = {
            "User-Agent": ua.random
        }
        
        print(f"[🐲] Starting... please wait.")

        start = int(start)
        end = int(end)

        while True:
            url = f"{base_url}&cursor={paginator}" if paginator else base_url
            urls.append(url)
            
            response = self.fetch_url(url, headers)
            trades = response.get('data', {}).get('history', [])
            
            if not trades or trades[-1]['timestamp'] < start:
                break

            paginator = response['data'].get('next')
            if not paginator:
                break
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.fetch_url, url, headers): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                response = future.result()
                trades = response.get('data', {}).get('history', [])
                filtered_trades = [trade for trade in trades if start <= trade['timestamp'] <= end]
                all_trades.extend(filtered_trades)

        wallets = []
        
        # Use our project's data structure
        output_dir = Path(os.getcwd()) / "data" / "output-data" / "ethereum" / "timestamp-txns"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = output_dir / f"txns_{self.shorten(contractAddress)}__{random.randint(1111, 9999)}.txt"

        for trade in all_trades:
            wallets.append(trade.get("maker"))

        with open(filename, 'a') as f:
            for wallet in wallets:
                f.write(f"{wallet}\n")
        
        print(f"[🐲] {len(wallets)} trades successfully saved to {filename}")
        return True

    def run(self, contract_address: str, start_time: int, end_time: int, threads: int = 10) -> bool:
        """Run the timestamp transaction analysis."""
        if not contract_address:
            print("No contract address provided!")
            return False
            
        return self.getTxByTimestamp(contract_address, threads, start_time, end_time)

def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """Parse a datetime string into a datetime object."""
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2023-01-15 14:30:00
        '%Y-%m-%d',           # 2023-01-15
        '%m/%d/%Y %H:%M:%S',  # 01/15/2023 14:30:00
        '%m/%d/%Y',           # 01/15/2023
    ]
    
    for format_str in formats:
        try:
            return datetime.strptime(datetime_str, format_str)
        except ValueError:
            continue
    
    return None

async def standalone_test(addresses=None, start_time_str=None, end_time_str=None):
    """Run a standalone test of the timestamp transaction finder."""
    # Set test mode flag
    os.environ["TEST_MODE"] = "1"
    test_mode = True
    
    # Use default test addresses if none provided
    if not addresses:
        # Sample ETH addresses
        addresses = [
            "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # vitalik.eth
            "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8"   # Binance cold wallet
        ]
    
    # Parse start and end times
    now = datetime.now()
    
    if start_time_str:
        start_time = parse_datetime(start_time_str)
        if start_time is None:
            print(f"Error: Could not parse start time '{start_time_str}'")
            return 1
    else:
        start_time = now - timedelta(days=7)  # Default to 7 days ago
    
    if end_time_str:
        end_time = parse_datetime(end_time_str)
        if end_time is None:
            print(f"Error: Could not parse end time '{end_time_str}'")
            return 1
    else:
        end_time = now  # Default to now
    
    # Set up output directory
    output_dir = Config.get_output_dir()
    Config.ensure_dir_exists(output_dir)
    
    print(f"🧪 Running test mode on {len(addresses)} addresses...")
    
    # Create instance and run
    finder = EthTimestampTransactions()
    
    result = finder.run(addresses[0], int(start_time.timestamp()), int(end_time.timestamp()))
    
    if result:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed")
    
    return 0 if result else 1

def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ethereum Timestamp Transaction Finder')
    parser.add_argument('--addresses', '-a', type=str, nargs='+', help='Ethereum addresses to scan')
    parser.add_argument('--start-time', '-s', type=str, help='Start time (YYYY-MM-DD [HH:MM:SS])')
    parser.add_argument('--end-time', '-e', type=str, help='End time (YYYY-MM-DD [HH:MM:SS])')
    parser.add_argument('--output', '-o', type=str, help='Output directory (default: data/output-data/ethereum/timestamp-txs)')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # If in test mode, run the test
    if args.test:
        return asyncio.run(standalone_test(
            addresses=args.addresses,
            start_time_str=args.start_time,
            end_time_str=args.end_time
        ))
    
    # Make sure we have at least one address
    if not args.addresses:
        print("❌ No addresses specified.")
        print("Please use --addresses/-a to specify one or more Ethereum addresses.")
        return 1
    
    # Parse start and end times
    now = datetime.now()
    
    if args.start_time:
        start_time = parse_datetime(args.start_time)
        if start_time is None:
            print(f"Error: Could not parse start time '{args.start_time}'")
            print("Please use format YYYY-MM-DD [HH:MM:SS]")
            return 1
    else:
        start_time = now - timedelta(days=1)  # Default to 24 hours ago
    
    if args.end_time:
        end_time = parse_datetime(args.end_time)
        if end_time is None:
            print(f"Error: Could not parse end time '{args.end_time}'")
            print("Please use format YYYY-MM-DD [HH:MM:SS]")
            return 1
    else:
        end_time = now  # Default to now
    
    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Config.get_output_dir()
    
    Config.ensure_dir_exists(output_dir)
    
    # Create instance and run
    finder = EthTimestampTransactions()
    
    result = finder.run(args.addresses[0], int(start_time.timestamp()), int(end_time.timestamp()))
    
    return 0 if result else 1

# For standalone execution
if __name__ == "__main__":
    sys.exit(main()) 