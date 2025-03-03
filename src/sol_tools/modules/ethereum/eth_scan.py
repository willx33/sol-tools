"""
Standalone implementation of Ethereum Transaction Scanner functionality.
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
    if __name__ == 'sol_tools.modules.ethereum.eth_scan':
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
    
    # Transaction scan settings
    DEFAULT_BLOCKS = 10000  # Number of blocks to scan by default
    
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
        """Get the output directory for Ethereum transaction scans."""
        # When used as a module in sol-tools
        if 'sol_tools' in sys.modules:
            from ...core.config import OUTPUT_DATA_DIR
            return OUTPUT_DATA_DIR / "ethereum" / "transactions"
        # When used standalone
        else:
            root = Config.get_project_root()
            return root / "data" / "output-data" / "ethereum" / "transactions"
    
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

async def get_transactions(session: aiohttp.ClientSession, address: str, 
                          start_block: Optional[int] = None, 
                          end_block: Optional[int] = None) -> Dict[str, Any]:
    """Get transaction history for an Ethereum address."""
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'sort': 'desc',  # Latest first
        'apikey': Config.ETH_API_KEY
    }
    
    # Add optional block range
    if start_block is not None:
        params['startblock'] = str(start_block)
    if end_block is not None:
        params['endblock'] = str(end_block)
    
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
                            "result": [],
                        }
                    
                    logger.error(f"API error for address {address}: {error_msg}")
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
                    "result": transactions,
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting transactions for address {address}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "error": "Timeout"}
            
        except Exception as e:
            logger.error(f"Error getting transactions for address {address}: {str(e)}")
            if retry < Config.MAX_RETRIES - 1:
                # Use random delay within range for better retry behavior
                delay = Config.RETRY_DELAY_MIN + (Config.RETRY_DELAY_MAX - Config.RETRY_DELAY_MIN) * random.random()
                await asyncio.sleep(delay)
                continue
            return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": "Max retries exceeded"}

async def scan_multiple_addresses(addresses: List[str], 
                                 start_block: Optional[int] = None, 
                                 end_block: Optional[int] = None, 
                                 output_dir: Optional[Path] = None,
                                 test_mode: bool = False) -> bool:
    """Scan transactions for multiple Ethereum addresses."""
    if not addresses:
        if not test_mode:
            print("No addresses provided to scan!")
        return False
    
    if output_dir is None:
        output_dir = Config.get_output_dir()
    
    # Ensure output directory exists
    Config.ensure_dir_exists(output_dir)
    
    # Initialize counters and results
    total_addresses = len(addresses)
    processed = 0
    successful = 0
    errors = 0
    all_txs = []
    address_txs = {}
    
    if not test_mode:
        print(f"Scanning transactions for {total_addresses} addresses...")
    
    async with aiohttp.ClientSession() as session:
        for address in addresses:
            processed += 1
            
            # Validate address
            if not is_valid_eth_address(address):
                if not test_mode:
                    print(f"Invalid address format: {address}")
                errors += 1
                continue
            
            # Display progress
            if not test_mode:
                show_progress_bar(processed, total_addresses, 
                                prefix=f'Progress ({processed}/{total_addresses}): ', 
                                suffix=f'Address: {address[:6]}...{address[-4:]}')
            
            # Get transactions
            result = await get_transactions(session, address, start_block, end_block)
            
            if result.get("status") == "success":
                txs = result.get("result", [])
                
                # Add to overall results
                address_txs[address] = txs
                all_txs.extend(txs)
                
                successful += 1
            else:
                if not test_mode:
                    print(f"\nError getting transactions for {address}: {result.get('error')}")
                errors += 1
    
    # Prepare summary data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {
        "scan_date": timestamp,
        "addresses_scanned": total_addresses,
        "successful": successful,
        "errors": errors,
        "start_block": start_block,
        "end_block": end_block,
        "total_transactions": len(all_txs)
    }
    
    # Save the results
    if successful > 0:
        prefix = "test_" if test_mode else ""
        output_file = output_dir / f"{prefix}eth_scan_{successful}_addresses_{timestamp}.json"
        
        # Prepare the output data
        output_data = {
            "summary": summary,
            "address_transactions": address_txs
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        if not test_mode:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"\n✅ Transaction scan completed.")
            print(f"   Found {len(all_txs)} transactions across {successful} addresses")
            print(f"   Results saved to {output_file}")
            print(f"   File size: {file_size_mb:.2f} MB")
        
        # Remove test files after saving to avoid cluttering
        if test_mode and os.path.exists(output_file):
            os.remove(output_file)
            
        return True
    else:
        if not test_mode:
            print("\n❌ Transaction scan failed: no valid results to save")
        return False

def run_scanner_in_thread(addresses: List[str], 
                          start_block: Optional[int] = None, 
                          end_block: Optional[int] = None, 
                          output_dir: Optional[Path] = None,
                          test_mode: bool = False) -> bool:
    """
    Run the transaction scanner in a separate thread with its own event loop.
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
                scan_multiple_addresses(addresses, start_block, end_block, output_dir, test_mode)
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
                print(f"Error in transaction scanner: {result}")
            return False
    else:
        if not test_mode:
            print("No result returned from thread")
        return False

class EthScanAllTx:
    """Ethereum Transaction Scanner class."""
    
    def __init__(self, addresses=None, start_block=None, end_block=None, output_dir=None, test_mode=False):
        """
        Initialize the Ethereum Transaction Scanner.
        
        Args:
            addresses: List of Ethereum addresses to scan
            start_block: Starting block for scan (optional)
            end_block: Ending block for scan (optional)
            output_dir: Directory to save results
            test_mode: Run in test mode (no output)
        """
        self.addresses = addresses or []
        self.start_block: Optional[int] = start_block
        self.end_block: Optional[int] = end_block
        
        # Handle output directory with proper defaults
        if output_dir is None:
            self.output_dir = Config.get_output_dir()
        else:
            self.output_dir = Path(output_dir)
            
        self.test_mode = test_mode
    
    def run(self) -> bool:
        """Run the transaction scanner and save results."""
        if not self.test_mode:
            print(f"Scanning transactions for {len(self.addresses)} addresses")
        
        # Validate addresses
        if not self.addresses:
            if not self.test_mode:
                print("No addresses provided!")
            return False
        
        # Make sure output directory exists
        Config.ensure_dir_exists(self.output_dir)
        
        # Process addresses
        result = run_scanner_in_thread(
            self.addresses, 
            self.start_block, 
            self.end_block, 
            self.output_dir,
            self.test_mode
        )
        
        return result

async def standalone_test(addresses=None, start_block=None, end_block=None):
    """Run a standalone test of the transaction scanner."""
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
    
    # Set up output directory
    output_dir = Config.get_output_dir()
    Config.ensure_dir_exists(output_dir)
    
    print(f"🧪 Running test mode on {len(addresses)} addresses...")
    
    # Create instance and run
    scanner = EthScanAllTx(
        addresses=addresses,
        start_block=start_block,
        end_block=end_block,
        output_dir=output_dir,
        test_mode=test_mode
    )
    
    result = scanner.run()
    
    if result:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed")
    
    return 0 if result else 1

def import_addresses_from_file(file_path: Union[str, Path]) -> List[str]:
    """
    Import Ethereum addresses from a file.
    
    Args:
        file_path: Path to the file containing addresses
        
    Returns:
        List of addresses
    """
    addresses = []
    path = Path(file_path)
    
    if not path.exists():
        print(f"Address file not found: {path}")
        return addresses
    
    try:
        with open(path, 'r') as f:
            for line in f:
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Add the address to the list
                addresses.append(line)
        
        return addresses
    except Exception as e:
        print(f"Error reading address file {path}: {e}")
        return []

def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ethereum Transaction Scanner')
    parser.add_argument('--addresses', '-a', type=str, nargs='+', help='Ethereum addresses to scan')
    parser.add_argument('--start-block', '-s', type=int, help='Starting block for scan')
    parser.add_argument('--end-block', '-e', type=int, help='Ending block for scan')
    parser.add_argument('--output', '-o', type=str, help='Output directory (default: data/output-data/ethereum/transactions)')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # If in test mode, run the test
    if args.test:
        return asyncio.run(standalone_test(
            addresses=args.addresses,
            start_block=args.start_block,
            end_block=args.end_block
        ))
    
    # Make sure we have at least one address
    if not args.addresses:
        print("❌ No addresses specified.")
        print("Please use --addresses/-a to specify one or more Ethereum addresses.")
        return 1
    
    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Config.get_output_dir()
    
    Config.ensure_dir_exists(output_dir)
    
    # Create instance and run
    scanner = EthScanAllTx(
        addresses=args.addresses,
        start_block=args.start_block,
        end_block=args.end_block,
        output_dir=output_dir
    )
    
    result = scanner.run()
    
    return 0 if result else 1

# For standalone execution
if __name__ == "__main__":
    sys.exit(main()) 