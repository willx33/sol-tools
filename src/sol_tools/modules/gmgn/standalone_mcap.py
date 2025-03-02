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
from readchar import readchar, key
import threading
import queue

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
            
            # Debug output for URL construction
            if retry == 0 and not IN_TEST_MODE:
                logger.debug(f"Request URL: {url}")
                logger.debug(f"Request params: {params}")
            
            async with session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay * 2))
                    print(f"⚠️ Rate limited for {token_address}, waiting {retry_after}s before retry {retry+1}/{Config.MAX_RETRIES}")
                    logger.warning(f"Rate limited for {token_address}, waiting {retry_after}s before retry {retry+1}/{Config.MAX_RETRIES}")
                    await asyncio.sleep(retry_after)
                    continue
                    
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"HTTP {response.status}: {error_text[:200]}"
                    if not IN_TEST_MODE:
                        print(f"❌ Error fetching batch for {token_address}: {error_msg}")
                    logger.error(f"Error fetching batch for {token_address}: {error_msg}")
                    
                    if retry < Config.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return []
                
                try:
                    data = await response.json()
                except Exception as e:
                    print(f"❌ Error parsing JSON response: {str(e)}")
                    logger.error(f"Error parsing JSON for {token_address}: {str(e)}")
                    if retry < Config.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return []
                
                # Check for API error code
                if data.get("code") != 0:
                    error_msg = data.get('msg', 'Unknown error')
                    print(f"❌ API error for {token_address}: {error_msg}")
                    logger.error(f"API error fetching batch for {token_address}: {error_msg}")
                    
                    if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                        if retry < Config.MAX_RETRIES - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                    return []
                
                candles = data.get("data", [])
                if not IN_TEST_MODE:
                    print(f"✅ Fetched {len(candles)} candles for {token_address} from {start_time_str} to {end_time_str}")
                logger.info(f"Fetched {len(candles)} candles for {token_address} from {start_time_str} to {end_time_str}")
                
                # Debug: Show first candle structure
                if candles and len(candles) > 0 and not IN_TEST_MODE:
                    logger.debug(f"Sample candle structure: {candles[0]}")
                
                # Return the raw candles without formatting - we'll handle formatting in the caller
                return candles
                
        except asyncio.TimeoutError:
            error_msg = f"Timeout fetching batch for {token_address} from {start_time_str} to {end_time_str}"
            print(f"⚠️ {error_msg}")
            logger.error(error_msg)
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return []
            
        except Exception as e:
            error_msg = f"Unexpected error fetching batch for {token_address}: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            if retry < Config.MAX_RETRIES - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return []
    
    print(f"❌ All retries failed for {token_address}")
    return []

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
    
    try:
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
                        print(f"❌ Error fetching batch {i}/{batch_count} for {token_address}: {str(e)}")
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
        
        if not all_candles:
            print(f"⚠️ Warning: No data retrieved for token {token_address}. This could indicate an API issue or invalid token.")
    except Exception as e:
        print(f"❌ Error processing {token_address}: {str(e)}")
        logger.error(f"Error processing {token_address}: {str(e)}")
        return []
    
    # Format candles consistently
    formatted_candles = []
    for candle in all_candles:
        # Skip verbose logging in formatter
        # Handle candles returned as dictionaries
        if isinstance(candle, dict):
            try:
                # Convert time from milliseconds to seconds if needed
                time_val = candle.get('time')
                if time_val is None:
                    time_val = candle.get('timestamp', int(datetime.now().timestamp()))
                
                # Handle string timestamps
                if isinstance(time_val, str):
                    try:
                        time_val = int(time_val)
                    except ValueError:
                        time_val = int(datetime.now().timestamp())
                
                # Normalize extremely large timestamps (ms to seconds)
                if time_val > 10000000000:  # If timestamp is in milliseconds
                    time_val = time_val // 1000
                
                # Validate timestamp is in reasonable range (1970-2100)
                current_time = int(datetime.now().timestamp())
                if time_val < 0 or time_val > 4102444800:  # Jan 1, 2100
                    time_val = current_time
                
                # Handle all numeric fields, ensuring proper conversion
                def safe_number_convert(value, default=0.0):
                    if value is None:
                        return default
                    if isinstance(value, (int, float)):
                        return float(value)
                    if isinstance(value, str):
                        try:
                            return float(value)
                        except ValueError:
                            return default
                    return default
                
                # Format date string safely
                try:
                    date_str = datetime.fromtimestamp(time_val).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OverflowError):
                    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Create a standardized candle format
                formatted_candle = {
                    "timestamp": int(time_val),
                    "date": date_str,
                    "open": safe_number_convert(candle.get('open')),
                    "high": safe_number_convert(candle.get('high')),
                    "low": safe_number_convert(candle.get('low')),
                    "close": safe_number_convert(candle.get('close')),
                    "volume": safe_number_convert(candle.get('volume')),
                    "market_cap": safe_number_convert(candle.get('market_cap')),
                }
                formatted_candles.append(formatted_candle)
            except Exception as e:
                # Skip this candle on any error
                if not IN_TEST_MODE:
                    logger.error(f"Error formatting candle: {str(e)}")
        # Handle candles returned as lists (fallback for array format)
        elif isinstance(candle, list) and len(candle) >= 6:
            try:
                # Normalize timestamp
                unix_time = candle[0]
                if unix_time > 10000000000:  # If timestamp is in milliseconds
                    unix_time = unix_time // 1000
                
                # Validate timestamp
                current_time = int(datetime.now().timestamp())
                if unix_time < 0 or unix_time > 4102444800:  # Jan 1, 2100
                    unix_time = current_time
                
                # Format date safely
                try:
                    date_str = datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OverflowError):
                    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Calculate market cap if not provided
                market_cap = float(candle[6]) if len(candle) >= 7 else float(candle[4]) * 1000000
                
                formatted_candles.append({
                    "timestamp": int(unix_time),
                    "date": date_str,
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                    "market_cap": market_cap
                })
            except Exception as e:
                # Skip this candle on any error
                if not IN_TEST_MODE:
                    logger.error(f"Error formatting candle: {str(e)}")
    
    return formatted_candles

def run_fetch_token_mcaps_in_thread(token_address, start_time_unix):
    """
    Run the fetch_single_token_mcaps function in a separate thread with its own event loop.
    This is a workaround for "Cannot run the event loop while another loop is running" errors.
    """
    result_queue = queue.Queue()
    
    def thread_worker():
        # Create a new event loop for this thread
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        
        try:
            # Run the async function in this thread's event loop
            result = thread_loop.run_until_complete(fetch_single_token_mcaps(token_address, start_time_unix))
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
            raise Exception(result)
    else:
        raise Exception("No result returned from thread")

# ---------------------------------------------------------------------------
# Command-line handler for testing
# ---------------------------------------------------------------------------
async def standalone_test(token_address=None, time_frame='1d'):
    """
    Standalone function for testing market cap data retrieval.
    This can be run directly from the command line.
    """
    # Basic initial setup
    token_addresses = None
    # Use environment variable for test mode instead of basing it on how we're called
    test_mode = os.environ.get("TEST_MODE") == "1"
    save_file = None
    file_format = None
    selected_file_path = None
    
    # We'll use this variable to track what state the selection process is in
    start_date = datetime.now() - timedelta(hours=1)  # Default to 1 hour ago
    
    # Set up globals for the whole session
    global IN_TEST_MODE
    IN_TEST_MODE = test_mode
    
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
        # Interactive flow with back options
        if not test_mode and not token_address:
            # Define states for the workflow
            STATE_MAIN_MENU = 0
            STATE_FILE_SELECTION = 1
            STATE_MANUAL_INPUT = 2
            STATE_TIME_FRAME = 3
            STATE_SAVE_OPTION = 4
            STATE_FILE_FORMAT = 5
            STATE_PROCESSING = 6
            
            # Initialize variables
            current_state = STATE_MAIN_MENU
            token_addresses = None
            selected_file_path = None
            start_date = None
            save_file = None
            file_format = None
            
            # State machine for navigation
            while current_state < STATE_PROCESSING:
                # Main menu (initial choice)
                if current_state == STATE_MAIN_MENU:
                    print("\n" + "═" * 60)
                    print("📊 GMGN MARKET CAP DATA - MAIN MENU")
                    print("═" * 60)
                    print("Choose an option:")
                    print("  1. 📁 Use existing input data")
                    print("  2. ✏️  Input new token addresses")
                    print("  3. 🚪 Exit")
                    print("─" * 60)
                    
                    choice = input("\n➤ Enter choice (1-3): ").strip()
                    
                    if choice == "1":
                        current_state = STATE_FILE_SELECTION
                    elif choice == "2":
                        current_state = STATE_MANUAL_INPUT
                    elif choice == "3":
                        print("\n👋 Exiting program. Goodbye!")
                        return 1
                    else:
                        print("\n❌ Invalid choice. Please try again.")
                
                # File selection menu
                elif current_state == STATE_FILE_SELECTION:
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
                        print("\n⚠️  No input files found. You'll need to input token addresses manually.")
                        current_state = STATE_MANUAL_INPUT
                    else:
                        print("\n" + "═" * 60)
                        print("📁 FILE SELECTION")
                        print("═" * 60)
                        print("Select a file by number:")
                        for i, file_path in enumerate(input_files, 1):
                            # Use relative path from project root for display
                            rel_path = file_path.relative_to(project_root)
                            
                            # Only mark this specific file as default
                            specific_default_path = "data/input-data/api/gmgn/token-lists/token_addresses.txt"
                            is_default = str(rel_path) == specific_default_path
                            
                            display_name = f"{rel_path} {'🔹 (default)' if is_default else ''}"
                            print(f"  {i}. {display_name}")
                        
                        print(f"  {len(input_files) + 1}. ✏️  Input addresses manually")
                        print(f"  {len(input_files) + 2}. ↩️  Back to main menu")
                        print("─" * 60)
                        
                        # Get user selection with robust error handling
                        selected_file_path = None
                        while True:
                            file_choice = input("\n➤ Select option (or press Enter for default file): ").strip()
                            
                            # Handle empty input - use default file
                            if not file_choice:
                                # Find the default file path
                                default_file = default_input_dir / "token_addresses.txt"
                                if default_file in input_files:
                                    selected_file_path = default_file
                                    print(f"\n✅ Using default file: data/input-data/api/gmgn/token-lists/token_addresses.txt")
                                    break
                                else:
                                    print("\n⚠️  Default file not found. Please select a file or input manually.")
                                    continue
                            
                            try:
                                choice_num = int(file_choice)
                                if 1 <= choice_num <= len(input_files):
                                    selected_file_path = input_files[choice_num - 1]
                                    break
                                elif choice_num == len(input_files) + 1:
                                    current_state = STATE_MANUAL_INPUT
                                    break
                                elif choice_num == len(input_files) + 2:
                                    current_state = STATE_MAIN_MENU
                                    break
                                else:
                                    print(f"\n❌ Please enter a number between 1 and {len(input_files) + 2}")
                            except ValueError:
                                print("\n❌ Please enter a valid number")
                        
                        # If we selected a file (not "Back" or "Manual input")
                        if selected_file_path and current_state == STATE_FILE_SELECTION:
                            print(f"\n📄 Selected file: {selected_file_path.relative_to(project_root)}")
                            try:
                                with open(selected_file_path, 'r') as f:
                                    token_addresses = " ".join([line.strip() for line in f if line.strip()])
                                
                                if not token_addresses:
                                    print("\n⚠️  Selected file is empty. Please input token addresses manually.")
                                    current_state = STATE_MANUAL_INPUT
                                else:
                                    tokens_count = len(token_addresses.split())
                                    print(f"✅ Loaded {tokens_count} token address{'es' if tokens_count > 1 else ''} from file.")
                                    current_state = STATE_TIME_FRAME
                            except Exception as e:
                                print(f"\n❌ Error reading file: {e}")
                                print("Please input token addresses manually.")
                                current_state = STATE_MANUAL_INPUT
                
                # Manual token input
                elif current_state == STATE_MANUAL_INPUT:
                    print("\n" + "═" * 60)
                    print("✏️  TOKEN ADDRESS INPUT")
                    print("═" * 60)
                    print("Input token addresses (comma-separated for multiple)")
                    print("Type 'back' to return to the main menu")
                    print("─" * 60)
                    
                    token_input = input("\n➤ Enter token address(es): ").strip()
                    
                    if token_input.lower() == 'back':
                        current_state = STATE_MAIN_MENU
                        continue
                    
                    # Check if we have token addresses
                    if not token_input:
                        print("\n❌ No token address provided. Please try again or type 'back'.")
                        continue
                    
                    # Convert comma-separated to space-separated for consistency 
                    if token_input and "," in token_input:
                        token_addresses = " ".join([addr.strip() for addr in token_input.split(",")])
                    else:
                        token_addresses = token_input
                    
                    # Ask if user wants to save the input for future use
                    while True:
                        save_input = input("\n➤ Save these token addresses for future use? (y/n, default=y, or 'back'): ").lower().strip()
                        
                        if save_input == 'back':
                            # Go back to the token input prompt
                            token_addresses = None
                            break
                        
                        if save_input in ['y', 'yes'] or not save_input:  # Default to yes if empty
                            # Create filename with proper format
                            today = datetime.now()
                            tokens_list = token_addresses.split()
                            first_token = tokens_list[0] if tokens_list else ""
                            token_identifier = f"{first_token[:3]}{first_token[-3:]}" if first_token else "unknown"
                            num_tokens = len(tokens_list)
                            
                            # Create filename in the required format
                            filename = f"{today.hour:02d}-{today.day:02d}-{today.month:02d}-{today.year}-{token_identifier}-{num_tokens}.txt"
                            file_path = default_input_dir / filename
                            
                            try:
                                with open(file_path, 'w') as f:
                                    for token in tokens_list:
                                        f.write(f"{token}\n")
                                print(f"\n✅ Token addresses saved to: {file_path}")
                                current_state = STATE_TIME_FRAME
                                break
                            except Exception as e:
                                print(f"\n❌ Error saving token addresses: {e}")
                                current_state = STATE_TIME_FRAME
                                break
                        elif save_input in ['n', 'no']:
                            current_state = STATE_TIME_FRAME
                            break
                        else:
                            print("\n❌ Invalid input. Please enter 'y', 'n', or 'back'.")
                    
                    # If we broke out of the loop without setting a new state, continue with the same state
                    if token_addresses is None:
                        continue
                
                # Time frame selection
                elif current_state == STATE_TIME_FRAME:
                    # Predefined time frames with friendly labels and their values
                    time_options = [
                        ("5 minutes", datetime.now() - timedelta(minutes=5)),
                        ("30 minutes", datetime.now() - timedelta(minutes=30)),
                        ("1 hour", datetime.now() - timedelta(hours=1)),
                        ("3 hours", datetime.now() - timedelta(hours=3)),
                        ("8 hours", datetime.now() - timedelta(hours=8)),
                        ("12 hours", datetime.now() - timedelta(hours=12)),
                        ("1 day", datetime.now() - timedelta(days=1)),
                        ("3 days", datetime.now() - timedelta(days=3)),
                        ("1 week", datetime.now() - timedelta(days=7)),
                        ("1 month", datetime.now() - timedelta(days=30)),
                        ("Custom (enter manually)", None)
                    ]
                    
                    print("\n" + "═" * 60)
                    print("⏱️  TIME FRAME SELECTION")
                    print("═" * 60)
                    print("Select a time frame for data retrieval:")
                    for i, (label, _) in enumerate(time_options, 1):
                        # Highlight the default option (1 hour)
                        is_default = i == 3  # 1 hour is the 3rd option
                        display_label = f"{label} 🔹 (default)" if is_default else label
                        print(f"  {i}. {display_label}")
                    print(f"  {len(time_options) + 1}. ↩️  Back to previous step")
                    print("─" * 60)
                    
                    # Get user selection with robust error handling
                    while True:
                        time_choice = input("\n➤ Select option (or press Enter for 1 hour): ").strip()
                        
                        # Default to 1 hour (option 3) if empty input
                        if not time_choice:
                            label, start_date = time_options[2]  # 1 hour is index 2 (the third option)
                            print(f"\n✅ Using default time frame: {label}")
                            current_state = STATE_SAVE_OPTION
                            break
                        
                        try:
                            choice_num = int(time_choice)
                            if 1 <= choice_num <= len(time_options):
                                if choice_num == len(time_options):  # Custom option
                                    print("\n📝 Custom Time Frame")
                                    print("─" * 60)
                                    print("Examples: '7d' for 7 days, '12h' for 12 hours, or YYYY-MM-DD")
                                    print("Type 'back' to return to time frame selection")
                                    
                                    while True:
                                        date_input = input("\n➤ Enter custom time frame: ").strip()
                                        
                                        if date_input.lower() == 'back':
                                            break  # Go back to time frame selection
                                        
                                        if not date_input:
                                            # Default to 7 days if no input
                                            start_date = datetime.now() - timedelta(days=7)
                                            print(f"\n✅ Using default timeframe of 7 days")
                                            current_state = STATE_SAVE_OPTION
                                            break
                                        elif date_input.lower().endswith('d') and date_input[:-1].isdigit():
                                            # Process days format (e.g., "30d")
                                            days = int(date_input[:-1])
                                            start_date = datetime.now() - timedelta(days=days)
                                            print(f"\n✅ Using timeframe of {days} days")
                                            current_state = STATE_SAVE_OPTION
                                            break
                                        elif date_input.lower().endswith('h') and date_input[:-1].isdigit():
                                            # Process hours format (e.g., "12h")
                                            hours = int(date_input[:-1])
                                            start_date = datetime.now() - timedelta(hours=hours)
                                            print(f"\n✅ Using timeframe of {hours} hours")
                                            current_state = STATE_SAVE_OPTION
                                            break
                                        elif date_input.isdigit():
                                            # Process as timestamp if it's all digits
                                            try:
                                                start_date = int(date_input)
                                                print(f"\n✅ Using timestamp: {start_date}")
                                                current_state = STATE_SAVE_OPTION
                                                break
                                            except ValueError:
                                                print(f"\n❌ Warning: Could not parse '{date_input}' as timestamp. Please try again or type 'back'.")
                                        else:
                                            # Try to parse as YYYY-MM-DD
                                            try:
                                                start_date = datetime.strptime(date_input, "%Y-%m-%d")
                                                print(f"\n✅ Using date: {start_date.strftime('%Y-%m-%d')}")
                                                current_state = STATE_SAVE_OPTION
                                                break
                                            except ValueError:
                                                print(f"\n❌ Warning: Could not parse date format '{date_input}'. Please try again or type 'back'.")
                                    
                                    # If we didn't set a new state, continue with time frame selection
                                    if current_state == STATE_TIME_FRAME:
                                        continue
                                    else:
                                        break
                                        
                                else:
                                    # Use the predefined time frame
                                    label, start_date = time_options[choice_num - 1]
                                    print(f"\n✅ Using time frame: {label}")
                                    current_state = STATE_SAVE_OPTION
                                    break
                            elif choice_num == len(time_options) + 1:
                                # Go back to previous step
                                if selected_file_path:
                                    current_state = STATE_FILE_SELECTION
                                else:
                                    current_state = STATE_MANUAL_INPUT
                                break
                            else:
                                print(f"\n❌ Please enter a number between 1 and {len(time_options) + 1}")
                        except ValueError:
                            print("\n❌ Please enter a valid number")
                
                # Save data option
                elif current_state == STATE_SAVE_OPTION:
                    print("\n" + "═" * 60)
                    print("💾 SAVE OPTIONS")
                    print("═" * 60)
                    
                    while True:
                        save_response = input("\n➤ Save data for all tokens? (y/n, default=y, or 'back'): ").lower().strip()
                        
                        if save_response == 'back':
                            current_state = STATE_TIME_FRAME
                            break
                        elif save_response in ['y', 'yes'] or not save_response:  # Default to yes if empty
                            save_file = True
                            print("\n✅ Data will be saved after processing")
                            current_state = STATE_FILE_FORMAT
                            break
                        elif save_response in ['n', 'no']:
                            save_file = False
                            print("\n⚠️  Data will not be saved")
                            current_state = STATE_PROCESSING
                            break
                        else:
                            print("\n❌ Invalid input. Please enter 'y', 'n', or 'back'.")
                
                # File format selection
                elif current_state == STATE_FILE_FORMAT:
                    if save_file:
                        print("\n" + "═" * 60)
                        print("📊 FILE FORMAT SELECTION")
                        print("═" * 60)
                        print("Select format for saving data:")
                        print("  1. JSON (.json) 🔹 (default)")
                        print("  2. Text (.txt)")
                        print("  3. Excel (.xlsx)")
                        print("  4. ↩️  Back to previous step")
                        print("─" * 60)
                        
                        while True:
                            format_choice = input("\n➤ Select format (1-4, default=1): ").strip()
                            
                            if not format_choice:  # Default to JSON if empty
                                file_format = "json"
                                print("\n✅ Using default format: JSON")
                                current_state = STATE_PROCESSING
                                break
                            elif format_choice == "1":
                                file_format = "json"
                                print("\n✅ Selected format: JSON")
                                current_state = STATE_PROCESSING
                                break
                            elif format_choice == "2":
                                file_format = "txt"
                                print("\n✅ Selected format: Text")
                                current_state = STATE_PROCESSING
                                break
                            elif format_choice == "3":
                                file_format = "xlsx"
                                print("\n✅ Selected format: Excel")
                                current_state = STATE_PROCESSING
                                break
                            elif format_choice == "4":
                                current_state = STATE_SAVE_OPTION
                                break
                            else:
                                print("\n❌ Invalid choice. Please enter a number between 1 and 4.")
                    else:
                        # If not saving, skip file format selection
                        current_state = STATE_PROCESSING
            
            # If we've made it here, we're ready to process
            print("\n" + "═" * 60)
            print("🔄 PROCESSING DATA")
            print("═" * 60)
        else:
            # Get token addresses from command line arguments or token_address parameter
            token_addresses = token_address if token_address else " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    
    # Define run_as_script for later use
    run_as_script = __name__ == "__main__"
    
    # Use the configured values or defaults
    if not test_mode and not token_address and 'start_date' not in locals():
        # If we didn't go through the interactive flow
        start_date = datetime.now() - timedelta(days=7)
    
    print(f"\n📡 Fetching market cap data for: {token_addresses}")
    if isinstance(start_date, datetime):
        print(f"⏱️  Timeframe: From {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create output directory - this is where files will be saved
    # Base directory is relative to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent  # Navigate up to project root
    
    # Use correct relative path for output
    if test_mode:
        # Use test output directory when in test mode
        output_dir = project_root / "data" / "test-output" / "api" / "gmgn" / "market-cap-data"
        print(f"🧪 Test mode: Using test output directory: {output_dir}")
    else:
        output_dir = project_root / "data" / "output-data" / "api" / "gmgn" / "market-cap-data"
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # If we didn't go through the interactive flow, ask about saving
    if test_mode or token_address or ('save_file' not in locals() or save_file is None):
        save_file = test_mode
        if not test_mode:
            print("\n" + "═" * 60)
            print("💾 SAVE OPTIONS")
            print("═" * 60)
            save_response = input("\n➤ Save data for all tokens? (y/n, default=y): ").lower().strip()
            save_file = save_response in ['y', 'yes'] or not save_response  # Default to yes if empty
            if save_file:
                print("✅ Data will be saved after processing")
            else:
                print("⚠️  Data will not be saved")
    
    # File format selection if we didn't choose it in the interactive flow
    if ('file_format' not in locals() or file_format is None):
        file_format = "json"  # Default format
        if save_file and not test_mode:
            print("\n" + "═" * 60)
            print("📊 FILE FORMAT SELECTION")
            print("═" * 60)
            print("Select format for saving data:")
            print("  1. JSON (.json) 🔹 (default)")
            print("  2. Text (.txt)")
            print("  3. Excel (.xlsx)")
            print("─" * 60)
            
            format_choice = input("\n➤ Select format (1-3, default=1): ").strip()
            if not format_choice:  # Default to JSON if empty
                file_format = "json"
                print("\n✅ Using default format: JSON")
            elif format_choice == "2":
                file_format = "txt"
                print("\n✅ Selected format: Text")
            elif format_choice == "3":
                file_format = "xlsx"
                print("\n✅ Selected format: Excel")
            else:
                file_format = "json"  # Default to JSON for any invalid input
                print("\n✅ Using default format: JSON")
            
            print("\n" + "═" * 60)
            print("🔄 PROCESSING DATA")
            print("═" * 60)
    
    # Ensure token_addresses is a list of strings
    if isinstance(token_addresses, str):
        # Split by space or comma if it's a string
        token_addresses = token_addresses.replace(',', ' ').split()
    
    # Handle the case where token_addresses might be None
    if token_addresses is None or len(token_addresses) == 0:
        print("No token addresses provided. Exiting.")
        return []
    
    # Empty results container
    result = {}
    
    # Convert start_date to Unix timestamp if it's a datetime
    if isinstance(start_date, datetime):
        start_time_unix = int(start_date.timestamp())
    elif isinstance(start_date, int):
        start_time_unix = start_date
    else:
        # Default to 7 days ago if we can't parse the input
        start_time_unix = int((datetime.now() - timedelta(days=7)).timestamp())
    
    # Process tokens one at a time using our thread-based solution
    for token in token_addresses:
        print(f"\n📊 Processing token: {token}")
        try:
            # Process this single token using our thread-based wrapper
            candles = run_fetch_token_mcaps_in_thread(token, start_time_unix)
            
            # Store results if we got any
            if candles and isinstance(candles, list) and len(candles) > 0:
                result[token] = candles
                
                # Display summary for this token if not in test mode
                if not test_mode:
                    first_candle = candles[0]
                    last_candle = candles[-1]
                    
                    # Get timestamp safely
                    def get_timestamp(candle):
                        timestamp = candle.get('timestamp', candle.get('time'))
                        if isinstance(timestamp, str):
                            try:
                                timestamp = int(timestamp)
                            except ValueError:
                                return int(time.time())
                        elif timestamp is None:
                            return int(time.time())
                        
                        # Normalize timestamp (convert from ms to seconds if needed)
                        if timestamp > 10000000000:  # If timestamp is in milliseconds
                            timestamp = timestamp // 1000
                        
                        # Validate timestamp is in reasonable range (1970-2100)
                        current_time = int(time.time())
                        if timestamp < 0 or timestamp > 4102444800:  # Jan 1, 2100
                            timestamp = current_time
                        
                        return timestamp
                    
                    # Format dates safely
                    first_timestamp = get_timestamp(first_candle)
                    last_timestamp = get_timestamp(last_candle)
                    
                    # Safe date formatting
                    try:
                        first_time = datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OverflowError, OSError):
                        first_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                    try:
                        last_time = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OverflowError, OSError):
                        last_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Get close price safely
                    def get_close(candle):
                        close = candle.get('close')
                        if close is None:
                            return 0.0
                        if isinstance(close, str):
                            try:
                                return float(close)
                            except ValueError:
                                return 0.0
                        return close
                    
                    first_close = get_close(first_candle)
                    last_close = get_close(last_candle)
                    
                    # Print token summary
                    print(f"Token: {token}")
                    print(f"Fetched {len(candles)} candles")
                    print(f"First candle: {first_time} - Close: {first_close:.4f}, Market Cap: {first_candle.get('market_cap', 'N/A')}")
                    print(f"Last candle: {last_time} - Close: {last_close:.4f}, Market Cap: {last_candle.get('market_cap', 'N/A')}")
                    print()
            elif not test_mode:
                print(f"No data found for token: {token}")
            
        except Exception as e:
            print(f"❌ Error processing token {token}: {str(e)}")
    
    # Prepare summary data
    summary_data = {}
    for token, candles in result.items():
        # Extract what we need for the summary
        token_data = []
        for candle in candles:
            # Make sure timestamp is an integer
            timestamp = candle.get('timestamp')
            if timestamp is None and 'time' in candle:
                timestamp = candle.get('time')
            
            # Convert string timestamps to int if needed
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                except ValueError:
                    timestamp = int(time.time())  # Use current time as fallback
            elif timestamp is None:
                timestamp = int(time.time())  # Use current time as fallback
            
            data_point = {
                "timestamp": timestamp,
                "date": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                "open": candle.get('open', 0),
                "high": candle.get('high', 0),
                "low": candle.get('low', 0),
                "close": candle.get('close', 0),
                "volume": candle.get('volume', 0),
                "market_cap": candle.get('market_cap', 0)
            }
            token_data.append(data_point)
        summary_data[token] = token_data
    
    # Save all data to a single file
    if save_file:
        try:
            # Create new filename format: 'Day-Month-Year-First 3 and last 3 characters of the first token used-Number of token outputs total combined'
            today = datetime.now()
            if result:
                first_token = list(result.keys())[0]
                token_identifier = f"{first_token[:3]}{first_token[-3:]}"
                num_tokens = len(result)
            else:
                token_identifier = "none"
                num_tokens = 0
                
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

if __name__ == "__main__":
    sys.exit(asyncio.run(standalone_test())) 