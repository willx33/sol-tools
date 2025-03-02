"""
Standalone implementation of GMGN market cap functionality.
This module can be imported directly without dependencies on other modules.
"""

import asyncio
import logging
import random
import time
import json
import sys
import uuid
import aiohttp
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import contextlib
import io
import glob

# We don't import pandas at the top level to avoid unnecessary dependencies
# It will be imported only when needed for Excel export

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
    logging.getLogger().setLevel(logging.CRITICAL + 1)  # Beyond critical - nothing gets logged
    
    # Disable specific loggers that might be used
    for name in ['asyncio', 'aiohttp', 'urllib3', 'sol_tools']:
        logging.getLogger(name).setLevel(logging.CRITICAL + 1)
        logging.getLogger(name).addHandler(NullHandler())
    
    # Set our module logger to do nothing
    logger.setLevel(logging.CRITICAL + 1)
    logger.addHandler(NullHandler())
    
    # Patch print to do nothing in test mode
    original_print = print
    def silent_print(*args, **kwargs):
        pass
    
    # Only use silent print in modules that generate verbose output
    if __name__ == 'sol_tools.modules.gmgn.standalone_mcap':
        print = silent_print

# Context manager to suppress all output
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

# Simple progress bar for CLI
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

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
class Config:
    """Configuration constants for the GMGN Market Cap module."""
    
    # GMGN API base URL
    GMGN_BASE_URL = "https://gmgn.mobi/defi/quotation/v1/tokens/mcapkline/sol/"
    GMGN_CLIENT_ID = "gmgn_web_2025.0214.180010"
    GMGN_APP_VER = "2025.0214.180010"
    GMGN_TZ_NAME = "Europe/Berlin"
    GMGN_TZ_OFFSET = "3600"
    GMGN_APP_LANG = "\"en-US\""
    
    # Timeout settings
    REQUEST_TIMEOUT = 30.0  # seconds
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY_MIN = 1.0  # seconds
    RETRY_DELAY_MAX = 3.0  # seconds
    
    # Batch settings
    BATCH_DURATION = 3000  # 50 minutes per batch
    
    @staticmethod
    def generate_device_id() -> str:
        """Generate a random device ID to avoid rate limiting"""
        return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helper function to fetch a batch of market cap data
# ---------------------------------------------------------------------------
async def fetch_batch_async(session: aiohttp.ClientSession, token_address: str, 
                           batch_start: int, batch_end: int) -> List[Dict[str, Any]]:
    """Fetch a single batch of market cap data via GMGN API"""
    
    # Skip logging in test mode
    if IN_TEST_MODE:
        start_time_str = ""
        end_time_str = ""
    else:
        start_time_str = datetime.fromtimestamp(batch_start).strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = datetime.fromtimestamp(batch_end).strftime('%Y-%m-%d %H:%M:%S')
    
    params = {
        "device_id": Config.generate_device_id(),  # Use random device ID
        "client_id": Config.GMGN_CLIENT_ID,
        "from_app": "gmgn",
        "app_ver": Config.GMGN_APP_VER,
        "tz_name": Config.GMGN_TZ_NAME,
        "tz_offset": Config.GMGN_TZ_OFFSET,
        "app_lang": Config.GMGN_APP_LANG,
        "resolution": "1s",
        "from": batch_start,
        "to": batch_end
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://gmgn.mobi/",
        "Origin": "https://gmgn.mobi"
    }
    
    url = f"{Config.GMGN_BASE_URL}{token_address}"
    
    retry_delay = Config.RETRY_DELAY_MIN
    
    for retry in range(Config.MAX_RETRIES):
        try:
            # Delay between retries to avoid rate limiting
            await asyncio.sleep(0.5 + retry * 0.5)
            
            # Use aiohttp client with proper timeout handling
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            async with session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay * 2))
                    logger.warning(f"Rate limited for {token_address}, waiting {retry_after}s before retry {retry+1}/{Config.MAX_RETRIES}")
                    await asyncio.sleep(retry_after)
                    continue
                    
                if response.status != 200:
                    logger.error(f"Error fetching batch for {token_address}: HTTP {response.status}")
                    if retry < Config.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return []
                
                data = await response.json()
                if data.get("code") != 0:
                    error_msg = data.get('msg', 'Unknown error')
                    logger.error(f"API error fetching batch for {token_address}: {error_msg}")
                    
                    if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                        if retry < Config.MAX_RETRIES - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                    return []
                
                candles = data.get("data", [])
                logger.info(f"Fetched {len(candles)} candles for {token_address} from {start_time_str} to {end_time_str}")
                
                # Debug: Show first candle structure
                if candles and len(candles) > 0 and not IN_TEST_MODE:
                    logger.info(f"Sample candle structure: {candles[0]}")
                
                # Return the raw candles without formatting - we'll handle formatting in the caller
                return candles
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching batch for {token_address} from {start_time_str} to {end_time_str}")
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return []
            
        except Exception as e:
            logger.error(f"Error fetching batch for {token_address} from {start_time_str} to {end_time_str}: {e}")
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return []
    
    return []  # Return empty list if all retries failed

# ---------------------------------------------------------------------------
# Main function to fetch market cap data
# ---------------------------------------------------------------------------
async def standalone_fetch_token_mcaps(token_addresses: Union[str, List[str]], 
                                     start_timestamp: Union[datetime, int]) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Fetch token market cap data for one or multiple tokens.
    
    Args:
        token_addresses: One token address or a list/space-separated string of token addresses
        start_timestamp: Start time (datetime or unix timestamp)
        
    Returns:
        List of market cap candles for a single token, or
        Dictionary of {token_address: List of market cap candles} for multiple tokens
    """
    # Convert start_timestamp to Unix timestamp if it's a datetime
    if isinstance(start_timestamp, datetime):
        start_time_unix = int(start_timestamp.timestamp())
    else:
        start_time_unix = start_timestamp
    
    # Convert string input to list if needed
    if isinstance(token_addresses, str):
        # Check if it's a space-separated list
        if " " in token_addresses:
            token_addresses = token_addresses.split()
    
    # Convert single token to list for consistent processing
    if not isinstance(token_addresses, list):
        token_addresses = [token_addresses]
    
    # Process multiple tokens
    if len(token_addresses) > 1:
        # Process each token
        results = {}
        for token in token_addresses:
            # Fetch data
            logger.info(f"Fetching market cap data for {token} on solana...")
            candles = await fetch_single_token_mcaps(token, start_time_unix)
            
            # Store results
            results[token] = candles
            
            # Short delay between tokens to avoid rate limiting
            await asyncio.sleep(1.0)
        
        return results
    
    # Single token processing
    elif len(token_addresses) == 1:
        token = token_addresses[0]
        logger.info(f"Fetching market cap data for {token} on solana...")
        return await fetch_single_token_mcaps(token, start_time_unix)
    
    # No tokens provided
    else:
        logger.error("No token addresses provided")
        return {}

# ---------------------------------------------------------------------------
# Helper function to fetch complete data for a single token
# ---------------------------------------------------------------------------
async def fetch_single_token_mcaps(token_address: str, start_time_unix: int) -> List[Dict[str, Any]]:
    """Fetch complete market cap data for a single token using batch requests"""
    
    current_time = int(datetime.now().timestamp())
    end_time_unix = current_time
    
    all_candles = []
    batch_duration = Config.BATCH_DURATION
    current_batch_start = start_time_unix
    
    # Create batch ranges silently
    batch_ranges = []
    while current_batch_start < end_time_unix:
        current_batch_end = min(current_batch_start + batch_duration, end_time_unix)
        batch_ranges.append((current_batch_start, current_batch_end))
        current_batch_start += batch_duration
    
    # If there are no batch ranges, add one for the entire period
    if not batch_ranges:
        batch_ranges = [(start_time_unix, end_time_unix)]
    
    # Setup for progress bar in test mode
    batch_count = len(batch_ranges)
    
    # Use context manager to suppress output during the API calls
    with suppress_all_output():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_batch_async(session, token_address, batch_start, batch_end)
                     for batch_start, batch_end in batch_ranges]
            
            # Show minimal info in test mode
            if IN_TEST_MODE:
                # Extremely minimal output
                print(f"⏳ Processing {token_address}...")
                
            # Process tasks and show progress
            batch_results = []
            for i, task in enumerate(asyncio.as_completed(tasks), 1):
                try:
                    result = await task
                    batch_results.append(result)
                    if not IN_TEST_MODE:
                        show_progress_bar(i, batch_count, prefix='Progress:', suffix=f'Batch {i}/{batch_count}', length=20)
                except Exception as e:
                    batch_results.append(e)
                    if not IN_TEST_MODE:
                        show_progress_bar(i, batch_count, prefix='Progress:', suffix=f'Batch {i}/{batch_count} (error)', length=20)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    if not IN_TEST_MODE:
                        logger.error(f"Error in batch fetch for {token_address}: {result}")
                    continue
                # Only extend the list with results that are actually lists
                if isinstance(result, list) and result:
                    all_candles.extend(result)
            
            candle_count = len(all_candles)
            if IN_TEST_MODE:
                if candle_count > 0:
                    print(f"✅ Fetched {candle_count} candles")
                else:
                    print(f"⚠️ No data found")
    
    # Format candles consistently
    formatted_candles = []
    for candle in all_candles:
        # Skip verbose logging in formatter
        # Handle candles returned as dictionaries
        if isinstance(candle, dict) and 'time' in candle and 'close' in candle:
            try:
                # Convert time from milliseconds to seconds if needed
                time_val = candle.get('time')
                if isinstance(time_val, str):
                    time_val = int(time_val)
                elif time_val is None:
                    # Skip this candle if time is missing
                    continue
                
                unix_time = time_val / 1000 if time_val > 1000000000000 else time_val
                try:
                    timestamp = datetime.fromtimestamp(float(unix_time))
                except (ValueError, TypeError, OverflowError):
                    continue
                
                # Calculate market cap (if not provided)
                # For GMGN, we can calculate it or use a default if not directly available
                market_cap = float(candle.get('market_cap', 0))
                if market_cap == 0 and 'close' in candle:
                    # Use close price as an approximation for market cap if not available
                    # This is just a placeholder and not accurate, but better than nothing
                    market_cap = float(candle.get('close', 0)) * 1000000  # Assuming 1M tokens
                
                formatted_candles.append({
                    "timestamp": timestamp.isoformat(),
                    "time": unix_time,
                    "open": float(candle.get('open', 0)),
                    "high": float(candle.get('high', 0)),
                    "low": float(candle.get('low', 0)),
                    "close": float(candle.get('close', 0)),
                    "volume": float(candle.get('volume', 0)),
                    "market_cap": market_cap
                })
            except (ValueError, TypeError):
                pass
        # Handle candles returned as lists (fallback for array format)
        elif isinstance(candle, list) and len(candle) >= 6:
            try:
                unix_time = candle[0] / 1000 if candle[0] > 1000000000000 else candle[0]
                timestamp = datetime.fromtimestamp(unix_time)
                
                # Calculate market cap if not provided
                market_cap = float(candle[6]) if len(candle) >= 7 else float(candle[4]) * 1000000
                
                formatted_candles.append({
                    "timestamp": timestamp.isoformat(),
                    "time": unix_time,
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                    "market_cap": market_cap
                })
            except:
                pass
    
    return formatted_candles

# ---------------------------------------------------------------------------
# Command-line handler for testing
# ---------------------------------------------------------------------------
async def standalone_test(token_address=None, time_frame='1d'):
    """
    Test the standalone implementation of the GMGN market cap module.
    Args:
        token_address: The token address to fetch market cap data for. If not provided, a list of default tokens will be used.
        time_frame: The time frame to fetch data for.
    Returns:
        The formatted candle data.
    """
    from datetime import datetime, timedelta
    import json
    import os
    from pathlib import Path
    import sys
    
    # Set global test mode flag
    global IN_TEST_MODE
    IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

    # Verify we're in the correct test context
    test_mode = IN_TEST_MODE
    
    # Get project root for file paths
    project_root = Path(__file__).parent.parent.parent.parent.parent  # Navigate up to project root
    
    # Define input data directories
    default_input_dir = project_root / "data" / "input-data" / "api" / "gmgn" / "token-lists"
    general_input_dir = project_root / "data" / "input-data"
    
    # Ensure directories exist
    os.makedirs(default_input_dir, exist_ok=True)
    
    # Use default test token if in test mode and no token provided
    if test_mode and not token_address:
        # Use BONK token address for tests
        token_addresses = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        if not IN_TEST_MODE:
            print(f"Test mode: Using default test token: {token_addresses}")
    else:
        # Option to use existing input file or input new data
        if not test_mode and not token_address:
            token_addresses = None
            selected_file = None
            
            try:
                import inquirer
                
                # Create initial choice options
                initial_choices = [
                    "Use existing input data",
                    "Input new token addresses"
                ]
                
                questions = [
                    inquirer.List('action',
                                message="Choose an option:",
                                choices=initial_choices,
                                carousel=True)
                ]
                
                # Get initial choice
                answers = inquirer.prompt(questions)
                if not answers:
                    print("Selection cancelled. Exiting.")
                    return 1
                    
                choice = answers['action']
                
                # Handle file selection if user chose existing data
                if choice == "Use existing input data":
                    # Find all .txt files in the default and general input directories
                    default_files = list(default_input_dir.glob("*.txt"))
                    
                    # Search for .txt files in all subdirectories of general_input_dir
                    all_input_files = []
                    for file_path in general_input_dir.glob("**/*.txt"):
                        # Skip files that are already in default_files or are from default directory
                        rel_path = file_path.relative_to(general_input_dir)
                        if str(rel_path).startswith("api/gmgn/token-lists/"):
                            continue
                        all_input_files.append(file_path)
                    
                    # Combine lists, with default files first
                    input_files = default_files + all_input_files
                    
                    if not input_files:
                        print("No input files found. You'll need to input token addresses manually.")
                        token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                    else:
                        # Display available files in a selectable list
                        file_options = []
                        for file_path in input_files:
                            is_default = file_path in default_files
                            # Use relative path from project root for display
                            rel_path = file_path.relative_to(project_root)
                            display_name = f"{rel_path} {'(default)' if is_default else ''}"
                            file_options.append((display_name, str(file_path)))
                        
                        # Use inquirer for file selection
                        file_questions = [
                            inquirer.List('file',
                                        message="Select an input file:",
                                        choices=[option[0] for option in file_options],
                                        carousel=True)
                        ]
                        
                        # Get user selection
                        file_answers = inquirer.prompt(file_questions)
                        if not file_answers:
                            print("File selection cancelled. Please input token addresses manually.")
                            token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                        else:
                            selected_display = file_answers['file']
                            # Find the matching file path
                            for display, path in file_options:
                                if display == selected_display:
                                    selected_file = path
                                    break
                            
                            if selected_file:
                                print(f"\nSelected file: {selected_display}")
                                try:
                                    selected_file_path = Path(selected_file)
                                    with open(selected_file_path, 'r') as f:
                                        token_addresses = " ".join([line.strip() for line in f if line.strip()])
                                    
                                    if not token_addresses:
                                        print("Selected file is empty. Please input token addresses manually.")
                                        token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                                    else:
                                        tokens_count = len(token_addresses.split())
                                        print(f"Loaded {tokens_count} token address{'es' if tokens_count > 1 else ''} from file.")
                                except Exception as e:
                                    print(f"Error reading file: {e}")
                                    print("Please input token addresses manually.")
                                    token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                            else:
                                print("Error with file selection. Please input token addresses manually.")
                                token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                else:
                    # User chose to input new addresses
                    token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                
                # Check if we have token addresses
                if not token_addresses:
                    print("No token address provided. Exiting.")
                    return 1
                    
                # Convert comma-separated to space-separated for consistency 
                if "," in token_addresses:
                    token_addresses = " ".join([addr.strip() for addr in token_addresses.split(",")])
                
                # Ask if user wants to save the input for future use (only for manually entered addresses)
                if choice == "Input new token addresses" or selected_file is None:
                    save_input = input("\nSave these token addresses for future use? (y/n): ").lower().strip()
                    if save_input in ['y', 'yes']:
                        # Create filename with proper format
                        today = datetime.now()
                        tokens_list = token_addresses.split()
                        first_token = tokens_list[0]
                        token_identifier = f"{first_token[:3]}{first_token[-3:]}"
                        num_tokens = len(tokens_list)
                        
                        # Create filename in the required format
                        filename = f"{today.hour:02d}-{today.day:02d}-{today.month:02d}-{today.year}-{token_identifier}-{num_tokens}.txt"
                        file_path = default_input_dir / filename
                        
                        try:
                            with open(file_path, 'w') as f:
                                for token in tokens_list:
                                    f.write(f"{token}\n")
                            print(f"\n✅ Token addresses saved to: {file_path}")
                        except Exception as e:
                            print(f"\n❌ Error saving token addresses: {e}")
                        
            except ImportError:
                print("\nError: The inquirer package is required for arrow key navigation.")
                print("Please install it with: pip install inquirer")
                print("Falling back to basic input method.")
                
                print("\nChoose an option:")
                print("1. Use existing input data")
                print("2. Input new token addresses")
                
                choice = input("\nEnter choice (1-2): ").strip()
                
                if choice == "1":
                    print("This feature requires the inquirer package for full functionality.")
                    print("Please install it with: pip install inquirer")
                    
                # Fall back to simple input
                token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                if not token_addresses:
                    print("No token address provided. Exiting.")
                    return 1
                    
                # Convert comma-separated to space-separated for consistency
                if "," in token_addresses:
                    token_addresses = " ".join([addr.strip() for addr in token_addresses.split(",")])
        else:
            # Get token addresses from command line arguments or token_address parameter
            run_as_script = __name__ == "__main__" 
            if run_as_script and len(sys.argv) >= 2:
                token_addresses = sys.argv[1]
            else:
                # Interactive mode (skip if in test mode)
                if test_mode:
                    # Use the provided token_address or default to BONK
                    token_addresses = token_address or "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
                    if not IN_TEST_MODE:
                        print(f"Test mode: Using token address: {token_addresses}")
                else:
                    token_addresses = input("Enter token address(es) (comma-separated for multiple): ").strip()
                    if not token_addresses:
                        print("No token address provided. Exiting.")
                        return 1
                    
                    # Convert comma-separated to space-separated for consistency 
                    if "," in token_addresses:
                        token_addresses = " ".join([addr.strip() for addr in token_addresses.split(",")])
    
    # Set default start date based on time_frame parameter
    if isinstance(time_frame, str) and time_frame.lower().endswith('d') and time_frame[:-1].isdigit():
        # Process days format (e.g., "7d")
        days = int(time_frame[:-1])
        start_date = datetime.now() - timedelta(days=days)
        if test_mode and not IN_TEST_MODE:
            print(f"Test mode: Using timeframe of {days} days")
    else:
        # Default to 7 days
        start_date = datetime.now() - timedelta(days=7)
        if test_mode and not IN_TEST_MODE:
            print(f"Test mode: Using default timeframe of 7 days")
    
    # In test mode, use the default time range
    # Otherwise get start date from arguments or user input
    if not test_mode:
        if run_as_script and len(sys.argv) >= 3:
            start_date = sys.argv[2]  # Use the raw input directly
        else:
            # Interactive mode
            date_input = input("Enter time frame (e.g., '7d' for 7 days, '30d' for 30 days, or YYYY-MM-DD): ").strip()
            if not date_input:
                # Default to 7 days if no input
                start_date = datetime.now() - timedelta(days=7)
                print(f"Using default timeframe of 7 days")
            elif date_input.lower().endswith('d') and date_input[:-1].isdigit():
                # Process days format (e.g., "30d")
                days = int(date_input[:-1])
                start_date = datetime.now() - timedelta(days=days)
                print(f"Using timeframe of {days} days")
            elif date_input.isdigit():
                # Process as timestamp if it's all digits
                try:
                    start_date = int(date_input)
                    print(f"Using timestamp: {start_date}")
                except ValueError:
                    print(f"Warning: Could not parse '{date_input}' as timestamp. Using default (7 days ago).")
                    start_date = datetime.now() - timedelta(days=7)
            else:
                # Try to parse as YYYY-MM-DD
                try:
                    start_date = datetime.strptime(date_input, "%Y-%m-%d")
                    print(f"Using date: {start_date.strftime('%Y-%m-%d')}")
                except ValueError:
                    print(f"Warning: Could not parse date format '{date_input}'. Using default (7 days ago).")
                    start_date = datetime.now() - timedelta(days=7)
    
    print(f"Fetching market cap data for: {token_addresses}")
    if isinstance(start_date, datetime):
        print(f"Timeframe: From {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"Timeframe: From timestamp {start_date}")
    
    # Ensure start_date is the right type (datetime or int) before calling the fetch function
    if isinstance(start_date, str):
        # Try to parse as date string
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            # Try to parse as unix timestamp
            try:
                start_date = int(start_date)
            except ValueError:
                # If all else fails, use default
                print(f"Warning: Could not parse date '{start_date}'. Using default (7 days ago).")
                start_date = datetime.now() - timedelta(days=7)
    
    # Fetch the data
    if not test_mode:
        print("Fetching data from GMGN API (this may take a moment)...")
    else:
        print("⏳ Running GMGN market cap test...")
    
    start_time = time.time()
    result = await standalone_fetch_token_mcaps(token_addresses, start_date)
    elapsed = time.time() - start_time
    
    if test_mode:
        print(f"✅ Data fetched in {elapsed:.2f} seconds")
    
    # Create output directory - this is where files will be saved
    # Base directory is relative to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent  # Navigate up to project root
    
    # Use correct relative path for output
    if test_mode:
        # Use test output directory when in test mode
        output_dir = project_root / "data" / "test-output" / "api" / "gmgn" / "market-cap-data"
        print(f"Test mode: Using test output directory: {output_dir}")
    else:
        output_dir = project_root / "data" / "output-data" / "api" / "gmgn" / "market-cap-data"
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Single save prompt for all data
    save_file = test_mode
    if not test_mode:
        save_response = input("\nSave data for all tokens? (y/n): ").lower().strip()
        save_file = save_response in ['y', 'yes']
    
    # File format selection - simple approach to avoid recursion issues
    file_format = "json"  # Default format
    if save_file and not test_mode:
        try:
            import inquirer
            
            format_options = [
                "JSON (.json)",
                "Text (.txt)",
                "Excel (.xlsx)"
            ]
            
            questions = [
                inquirer.List('format',
                            message="Select file format:",
                            choices=format_options,
                            carousel=True)
            ]
            
            # Get user selection
            answers = inquirer.prompt(questions)
            if answers:
                selected_format = answers['format']
                if selected_format == "Text (.txt)":
                    file_format = "txt"
                elif selected_format == "Excel (.xlsx)":
                    file_format = "xlsx"
                else:
                    file_format = "json"
            # If cancelled, default to json
        except ImportError:
            # Only as a fallback if inquirer is not available
            print("\nSelect file format:")
            print("1. JSON (.json)")
            print("2. Text (.txt)")
            print("3. Excel (.xlsx)")
            
            format_choice = input("\nSelect format (1-3): ").strip()
            if format_choice == "2":
                file_format = "txt"
            elif format_choice == "3":
                file_format = "xlsx"
            else:
                file_format = "json"  # Default to JSON for any invalid input
        
        print(f"Selected format: .{file_format}")

    # Handle multiple tokens
    if isinstance(result, dict):
        if not test_mode:
            print(f"\nReceived data for {len(result)} tokens:")
        else:
            print(f"🔍 Processing {len(result)} tokens")
            
        summary_data = {}
        
        for token, candles in result.items():
            summary_data[token] = candles
            
            # Show first and last candle for each token
            if candles:
                if not test_mode:
                    first_candle = candles[0]
                    last_candle = candles[-1]
                    
                    # Convert timestamps to datetime objects for better readability
                    first_time = datetime.fromtimestamp(float(first_candle['time']))
                    last_time = datetime.fromtimestamp(float(last_candle['time']))
                    
                    print(f"Token: {token}")
                    print(f"Fetched {len(candles)} candles")
                    print(f"First candle: {first_time} - Close: {first_candle['close']:.4f}, Market Cap: {first_candle.get('market_cap', 'N/A')}")
                    print(f"Last candle: {last_time} - Close: {last_candle['close']:.4f}, Market Cap: {last_candle.get('market_cap', 'N/A')}")
                    print()
            elif not test_mode:
                print(f"Token: {token}")
                print(f"No candles found")
                print()
        
        # Save all data to a single file
        if save_file:
            try:
                # Create new filename format: 'Day-Month-Year-First 3 and last 3 characters of the first token used-Number of token outputs total combined'
                today = datetime.now()
                first_token = list(result.keys())[0]
                token_identifier = f"{first_token[:3]}{first_token[-3:]}"
                num_tokens = len(result)
                
                # Add "test_" prefix in test mode
                prefix = "test_" if test_mode else ""
                filename = f"{prefix}{today.day:02d}-{today.month:02d}-{today.year}-{token_identifier}-{num_tokens}"
                
                if file_format == "json":
                    combined_file = output_dir / f"{filename}.json"
                    # Save the file with proper error handling
                    with open(combined_file, 'w') as f:
                        json.dump(summary_data, f, indent=2)
                elif file_format == "txt":
                    combined_file = output_dir / f"{filename}.txt"
                    # Save as formatted text
                    with open(combined_file, 'w') as f:
                        f.write(json.dumps(summary_data, indent=2))
                elif file_format == "xlsx":
                    combined_file = output_dir / f"{filename}.xlsx"
                    try:
                        # Import pandas only when needed
                        import pandas as pd
                        from openpyxl import Workbook
                        
                        # Create Excel workbook with a sheet for each token
                        with pd.ExcelWriter(combined_file) as writer:
                            for token, candles in result.items():
                                # Convert to pandas DataFrame
                                df = pd.DataFrame(candles)
                                # Format the sheet name (Excel sheet names limited to 31 chars)
                                sheet_name = token[:15] if len(token) > 15 else token
                                # Write to Excel
                                df.to_excel(writer, sheet_name=sheet_name, index=False)
                    except ImportError:
                        print("\n⚠️ pandas or openpyxl module not found. Installing required packages...")
                        try:
                            import subprocess
                            subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
                            
                            # Try again after installing
                            import pandas as pd
                            from openpyxl import Workbook
                            
                            # Create Excel workbook with a sheet for each token
                            with pd.ExcelWriter(combined_file) as writer:
                                for token, candles in result.items():
                                    # Convert to pandas DataFrame
                                    df = pd.DataFrame(candles)
                                    # Format the sheet name (Excel sheet names limited to 31 chars)
                                    sheet_name = token[:15] if len(token) > 15 else token
                                    # Write to Excel
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                        except:
                            print("\n❌ Failed to install required packages for Excel export. Falling back to JSON.")
                            combined_file = output_dir / f"{filename}.json"
                            with open(combined_file, 'w') as f:
                                json.dump(summary_data, f, indent=2)
                
                # Verify file was saved successfully
                if os.path.exists(combined_file) and os.path.getsize(combined_file) > 0:
                    file_size_mb = os.path.getsize(combined_file) / (1024 * 1024)
                    if not test_mode:
                        print(f"\n✅ SUCCESS: All data saved successfully!")
                        print(f"   Filename: {combined_file.name}")
                        print(f"   Directory: {output_dir}")
                        print(f"   Full path: {combined_file.absolute()}")
                        print(f"   File size: {file_size_mb:.2f} MB")
                    else:
                        print(f"✅ Data saved to: {combined_file.name} ({file_size_mb:.2f} MB)")
                    
                    # Remove test files after saving to avoid cluttering
                    if test_mode:
                        os.remove(combined_file)
                        if not test_mode:
                            print(f"   Test file removed: {combined_file.name}")
                else:
                    if test_mode:
                        print(f"❌ File creation failed")
                    else:
                        print(f"\n❌ ERROR: File was not created at {combined_file} or is empty")
            except Exception as e:
                if test_mode:
                    print(f"❌ Save error: {str(e)}")
                else:
                    print(f"\n❌ ERROR: Failed to save data: {str(e)}")
        elif not test_mode:
            print("Data not saved per user request.")
            
        return result
    
    # Handle single token result
    else:
        candles = result
        if not test_mode:
            print(f"\nFetched {len(candles)} candles")
        else:
            print(f"🔍 Processed {len(candles)} candles")
        
        # Show first and last candle
        if candles:
            first_candle = candles[0]
            last_candle = candles[-1]
            
            # Convert timestamps to datetime objects for better readability
            first_time = datetime.fromtimestamp(float(first_candle['time']))
            last_time = datetime.fromtimestamp(float(last_candle['time']))
            
            if not test_mode:
                print(f"First candle: {first_time} - Close: {first_candle['close']:.4f}, Market Cap: {first_candle.get('market_cap', 'N/A')}")
                print(f"Last candle: {last_time} - Close: {last_candle['close']:.4f}, Market Cap: {last_candle.get('market_cap', 'N/A')}")
            
            # Save file using the common prompt
            if save_file:
                try:
                    # Create new filename format: 'Day-Month-Year-First 3 and last 3 characters of the token-1'
                    today = datetime.now()
                    token_identifier = f"{token_addresses[:3]}{token_addresses[-3:]}"
                    
                    # Add "test_" prefix in test mode
                    prefix = "test_" if test_mode else ""
                    filename = f"{prefix}{today.day:02d}-{today.month:02d}-{today.year}-{token_identifier}-1"
                    
                    if file_format == "json":
                        token_file = output_dir / f"{filename}.json"
                        # Save the file with proper error handling
                        with open(token_file, 'w') as f:
                            json.dump(candles, f, indent=2)
                    elif file_format == "txt":
                        token_file = output_dir / f"{filename}.txt"
                        # Save as formatted text
                        with open(token_file, 'w') as f:
                            f.write(json.dumps(candles, indent=2))
                    elif file_format == "xlsx":
                        token_file = output_dir / f"{filename}.xlsx"
                        try:
                            # Import pandas only when needed
                            import pandas as pd
                            
                            # Convert to pandas DataFrame
                            df = pd.DataFrame(candles)
                            # Save to Excel
                            df.to_excel(token_file, index=False)
                        except ImportError:
                            print("\n⚠️ pandas or openpyxl module not found. Installing required packages...")
                            try:
                                import subprocess
                                subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
                                
                                # Try again after installing
                                import pandas as pd
                                
                                # Convert to pandas DataFrame
                                df = pd.DataFrame(candles)
                                # Save to Excel
                                df.to_excel(token_file, index=False)
                            except:
                                print("\n❌ Failed to install required packages for Excel export. Falling back to JSON.")
                                token_file = output_dir / f"{filename}.json"
                                with open(token_file, 'w') as f:
                                    json.dump(candles, f, indent=2)
                    
                    # Verify file was saved successfully
                    if os.path.exists(token_file) and os.path.getsize(token_file) > 0:
                        file_size_mb = os.path.getsize(token_file) / (1024 * 1024)
                        if not test_mode:
                            print(f"\n✅ SUCCESS: Data saved successfully!")
                            print(f"   Filename: {token_file.name}")
                            print(f"   Directory: {output_dir}")
                            print(f"   Full path: {token_file.absolute()}")
                            print(f"   File size: {file_size_mb:.2f} MB")
                        else:
                            print(f"✅ Data saved to: {token_file.name} ({file_size_mb:.2f} MB)")
                        
                        # Remove test files after saving to avoid cluttering
                        if test_mode:
                            os.remove(token_file)
                            if not test_mode:
                                print(f"   Test file removed: {token_file.name}")
                    else:
                        if test_mode:
                            print(f"❌ File creation failed")
                        else:
                            print(f"\n❌ ERROR: File was not created at {token_file} or is empty")
                except Exception as e:
                    if test_mode:
                        print(f"❌ Save error: {str(e)}")
                    else:
                        print(f"\n❌ ERROR: Failed to save data: {str(e)}")
            elif not test_mode:
                print("Data not saved per user request.")
        
        return candles

if __name__ == "__main__":
    sys.exit(asyncio.run(standalone_test())) 