"""
Standalone implementation of Ethereum Top Traders functionality.
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
    if __name__ == 'sol_tools.modules.ethereum.eth_traders':
        print = silent_print
    
    # Silence all known noisy modules
    for name in logging.root.manager.loggerDict:
        logger_instance = logging.getLogger(name)
        logger_instance.setLevel(logging.CRITICAL + 1)
        for handler in list(logger_instance.handlers):
            logger_instance.removeHandler(handler)
        logger_instance.addHandler(NullHandler())

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
    
    # Token trade analysis
    TOP_TRADERS_COUNT = 100  # Number of top traders to find
    MIN_TX_VALUE = 0.1  # Minimum transaction value in ETH to consider
    
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
        """Get the output directory for Ethereum top traders."""
        # When used as a module in sol-tools
        if 'sol_tools' in sys.modules:
            from ...core.config import OUTPUT_DATA_DIR
            return OUTPUT_DATA_DIR / "ethereum" / "top-traders"
        # When used standalone
        else:
            root = Config.get_project_root()
            return root / "data" / "output-data" / "ethereum" / "top-traders"
    
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

async def get_token_transfers(session: aiohttp.ClientSession, token_address: str, 
                              page: int = 1, offset: int = 100) -> Dict[str, Any]:
    """Get token transfers for a specific token."""
    params = {
        'module': 'account',
        'action': 'tokentx',
        'contractaddress': token_address,
        'page': str(page),
        'offset': str(offset),
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
                    
                    # If no transactions found, this is actually OK on later pages
                    if "No transactions found" in error_msg and page > 1:
                        return {
                            "status": "success",
                            "result": [],
                            "last_page": True
                        }
                    
                    logger.error(f"API error for token {token_address}: {error_msg}")
                    if retry < Config.MAX_RETRIES - 1:
                        # Use random delay within range for better retry behavior
                        delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                        await asyncio.sleep(delay)
                        continue
                    return {"status": "error", "error": error_msg}
                
                # Process transfers
                transfers = data.get("result", [])
                
                return {
                    "status": "success",
                    "result": transfers,
                    "last_page": len(transfers) < offset
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting transfers for token {token_address}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting transfers for token {token_address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": "Max retries exceeded"}

async def get_all_token_transfers(session: aiohttp.ClientSession, token_address: str, 
                                 max_pages: int = 5) -> List[Dict[str, Any]]:
    """Get all token transfers for a specific token, up to a maximum number of pages."""
    all_transfers = []
    page = 1
    last_page = False
    
    while not last_page and page <= max_pages:
        result = await get_token_transfers(session, token_address, page=page)
        
        if result.get("status") != "success":
            logger.error(f"Error getting transfers for page {page}: {result.get('error')}")
            break
        
        transfers = result.get("result", [])
        all_transfers.extend(transfers)
        
        last_page = result.get("last_page", False)
        page += 1
        
        # If we've collected a reasonable number of transfers, stop
        if len(all_transfers) >= 1000:
            break
    
    return all_transfers

def analyze_transfers(transfers: List[Dict[str, Any]], 
                     days_threshold: int = 30) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Analyze token transfers to find top traders.
    
    Args:
        transfers: List of token transfers
        days_threshold: Number of days to look back
        
    Returns:
        Tuple of (list of top traders, statistics)
    """
    # Calculate threshold date
    threshold_date = int((datetime.now() - timedelta(days=days_threshold)).timestamp())
    
    # Filter by date
    recent_transfers = [
        tx for tx in transfers 
        if int(tx.get("timeStamp", 0)) >= threshold_date
    ]
    
    # Calculate volume by address
    traders = {}
    for tx in recent_transfers:
        # Extract data
        from_addr = tx.get("from", "")
        to_addr = tx.get("to", "")
        value = int(tx.get("value", "0"))
        token_decimals = int(tx.get("tokenDecimal", "0"))
        
        # Calculate normalized value
        normalized_value = value / (10 ** token_decimals)
        
        # Store by address
        for addr in [from_addr, to_addr]:
            if not addr:
                continue
                
            if addr not in traders:
                traders[addr] = {
                    "address": addr,
                    "volume": 0,
                    "transactions": 0,
                    "buys": 0,
                    "sells": 0
                }
            
            traders[addr]["transactions"] += 1
            traders[addr]["volume"] += normalized_value
            
            # Track buys/sells
            if addr == to_addr:
                traders[addr]["buys"] += 1
            elif addr == from_addr:
                traders[addr]["sells"] += 1
    
    # Convert to list and sort by volume
    top_traders = sorted(
        list(traders.values()), 
        key=lambda x: x["volume"], 
        reverse=True
    )
    
    # Calculate statistics
    stats = {
        "total_traders": len(traders),
        "total_transactions": len(recent_transfers),
        "period_days": days_threshold,
        "top_trader_volume": top_traders[0]["volume"] if top_traders else 0,
        "timestamp": int(datetime.now().timestamp())
    }
    
    return top_traders[:Config.TOP_TRADERS_COUNT], stats

async def find_top_traders(token_address: str, days: int, output_dir: Path, test_mode: bool = False) -> bool:
    """Find top traders for a specific token."""
    if not is_valid_eth_address(token_address):
        if not test_mode:
            print(f"Invalid Ethereum address: {token_address}")
        return False
    
    # Shorten address for display/filenames
    short_addr = f"{token_address[:6]}...{token_address[-4:]}"
    
    if not test_mode:
        print(f"Finding top traders for token {short_addr} over the last {days} days...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get token transfers
            if not test_mode:
                print("Fetching token transfers...")
            transfers = await get_all_token_transfers(session, token_address)
            
            if not transfers:
                if not test_mode:
                    print("No transfers found for this token.")
                return False
            
            # Analyze transfers
            if not test_mode:
                print(f"Analyzing {len(transfers)} transfers...")
            top_traders, stats = analyze_transfers(transfers, days_threshold=days)
            
            if not top_traders:
                if not test_mode:
                    print("No traders found for this token.")
                return False
            
            # Prepare output data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result = {
                "token_address": token_address,
                "analysis_date": timestamp,
                "days_analyzed": days,
                "statistics": stats,
                "top_traders": top_traders
            }
            
            # Save the results
            prefix = "test_" if test_mode else ""
            output_file = output_dir / f"{prefix}eth_top_traders_{short_addr}_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            if not test_mode:
                file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"\n✅ Top traders saved to {output_file}")
                print(f"   File size: {file_size_mb:.2f} MB")
                print(f"   Found {len(top_traders)} top traders out of {stats['total_traders']} total traders")
                print(f"   Analyzed {stats['total_transactions']} transactions over {days} days")
            
            # Remove test files after saving to avoid cluttering
            if test_mode and os.path.exists(output_file):
                os.remove(output_file)
                
            return True
    except Exception as e:
        logger.error(f"Error finding top traders: {str(e)}")
        if not test_mode:
            print(f"Error finding top traders: {str(e)}")
        return False

def run_top_traders_in_thread(token_address: str, days: int, output_dir: Path, test_mode: bool = False) -> bool:
    """
    Run the top traders finder in a separate thread with its own event loop.
    This is a workaround for "Cannot run the event loop while another loop is running" errors.
    """
    result_queue = queue.Queue()
    
    def thread_worker():
        # Create a new event loop for this thread
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        
        try:
            # Run the async function in this thread's event loop
            result = thread_loop.run_until_complete(find_top_traders(token_address, days, output_dir, test_mode))
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
                print(f"Error in top traders finder: {result}")
            return False
    else:
        if not test_mode:
            print("No result returned from thread")
        return False

class EthTopTraders:
    """Ethereum Top Traders class."""
    
    def __init__(self, token_address=None, days=30, output_dir=None, test_mode=False):
        """
        Initialize the Ethereum Top Traders finder.
        
        Args:
            token_address: Ethereum token contract address
            days: Number of days to analyze
            output_dir: Directory to save results
            test_mode: Run in test mode (no output)
        """
        self.token_address = token_address
        self.days = days
        
        # Handle output directory with proper defaults
        if output_dir is None:
            self.output_dir = Config.get_output_dir()
        else:
            self.output_dir = Path(output_dir)
            
        self.test_mode = test_mode
    
    def run(self) -> bool:
        """Run the top traders analysis and save results."""
        if not self.test_mode:
            print(f"Finding top traders for token {self.token_address} over the last {self.days} days")
        
        # Validate token address
        if not self.token_address:
            if not self.test_mode:
                print("No token address provided!")
            return False
        
        # Make sure output directory exists
        Config.ensure_dir_exists(self.output_dir)
        
        # Process token
        result = run_top_traders_in_thread(
            self.token_address, 
            self.days, 
            self.output_dir,
            self.test_mode
        )
        
        return result

async def standalone_test(token_address=None, days=30):
    """Run a standalone test of the top traders finder."""
    # Set test mode flag
    os.environ["TEST_MODE"] = "1"
    test_mode = True
    
    # Use default test token if none provided
    if not token_address:
        # SHIB token contract
        token_address = "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE"
    
    # Set up output directory
    output_dir = Config.get_output_dir()
    Config.ensure_dir_exists(output_dir)
    
    print(f"🧪 Running test mode on token {token_address} for {days} days...")
    
    # Create instance and run
    finder = EthTopTraders(
        token_address=token_address,
        days=days,
        output_dir=output_dir,
        test_mode=test_mode
    )
    
    result = finder.run()
    
    if result:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed")
    
    return 0 if result else 1

def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ethereum Top Traders Finder')
    parser.add_argument('--token', '-t', type=str, help='Ethereum token contract address')
    parser.add_argument('--days', '-d', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--output', '-o', type=str, help='Output directory (default: data/output-data/ethereum/top-traders)')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # If in test mode, run the test
    if args.test:
        return asyncio.run(standalone_test(token_address=args.token, days=args.days))
    
    # Make sure we have a token address
    if not args.token:
        print("❌ No token address specified.")
        print("Please use --token/-t to specify a token contract address.")
        return 1
    
    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Config.get_output_dir()
    
    Config.ensure_dir_exists(output_dir)
    
    # Create instance and run
    finder = EthTopTraders(
        token_address=args.token,
        days=args.days,
        output_dir=output_dir
    )
    
    result = finder.run()
    
    return 0 if result else 1

# For standalone execution
if __name__ == "__main__":
    sys.exit(main()) 