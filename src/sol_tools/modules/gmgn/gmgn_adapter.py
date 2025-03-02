"""
GMGN adapter for fetching Solana token market cap data
"""

import asyncio
import aiohttp
import uuid
import time
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Iterable

# Set up logging
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration for GMGN API calls
# ---------------------------------------------------------------------------
class Config:
    GMGN_BASE_URL = "https://gmgn.mobi/defi/quotation/v1/tokens/mcapkline/sol/"
    GMGN_CLIENT_ID = "gmgn_web_2025.0214.180010"
    GMGN_APP_VER = "2025.0214.180010"
    GMGN_TZ_NAME = "Europe/Berlin"
    GMGN_TZ_OFFSET = "3600"
    GMGN_APP_LANG = "\"en-US\""
    
    @staticmethod
    def generate_device_id() -> str:
        """Generate a random device ID to avoid rate limiting"""
        return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# GMGN Adapter Class
# ---------------------------------------------------------------------------
class GMGNAdapter:
    """Adapter for GMGN functionality within Sol Tools framework."""
    
    def __init__(self, 
                 output_dir: Optional[Path] = None,
                 test_mode: bool = False):
        """
        Initialize the GMGN adapter.
        
        Args:
            output_dir: Directory for saving output data
            test_mode: NOT SUPPORTED - will raise an error
        """
        # If test_mode is True, raise an error
        if test_mode:
            raise ValueError("Test mode is not supported in GMGN adapter. Use real implementations.")
        
        # Set up output directory
        if output_dir is None:
            # Use default directory
            base_dir = Path(os.path.expanduser("~")) / ".sol_tools"
            self.output_dir = base_dir / "gmgn_data"
        else:
            self.output_dir = output_dir / "gmgn_data"
            
        # Create directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up token information (basic info, initialized later in real mode)
        self.token_info = {
            "GMGN": {
                "name": "Magic Eden Token",
                "symbol": "GMGN",
                "address": "4e8rF4Q5s8AmTacxvfVMKJtQKMjM2ZfbCGnzAEjRGKTZ",
                "decimals": 9
            }
        }
    
    async def fetch_token_mcap_data(self, token_address: str, days: int = 7) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        Fetch market cap data for a token.
        
        Args:
            token_address: Token contract address
            days: Number of days of data to retrieve
            
        Returns:
            List of market cap data or dictionary mapping token addresses to lists of market cap data
        """
        try:
            # Try to import the standalone implementation
            from .standalone_mcap import standalone_fetch_token_mcaps
            
            # Calculate start timestamp from days
            start_time = datetime.now() - timedelta(days=days)
            
            # Call the function
            return await standalone_fetch_token_mcaps(token_address, start_time)
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing standalone_fetch_token_mcaps: {e}")
            raise NotImplementedError("Market cap data API implementation not available")
    
    def get_token_info_sync(self, contract_address: str) -> Dict[str, Any]:
        """
        Get token information synchronously.
        
        Args:
            contract_address: Contract address
            
        Returns:
            Token information
        """
        try:
            # Import the entire module instead of a specific function
            from . import standalone_token_data
            
            # Call the function through the module
            return standalone_token_data.get_token_info_sync(contract_address)
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing get_token_info_sync: {e}")
            raise NotImplementedError("API implementation not available in this version")
    
    async def get_token_info(self, contract_address: str) -> Dict[str, Any]:
        """
        Get token information asynchronously.
        
        Args:
            contract_address: Contract address
            
        Returns:
            Token information
        """
        try:
            # Import the entire module instead of a specific function
            from . import standalone_token_data
            
            # Call the function through the module
            return await standalone_token_data.get_token_info(contract_address)
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing get_token_info: {e}")
            # Try falling back to synchronous version
            return self.get_token_info_sync(contract_address)
    
    async def get_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Get new tokens from GMGN.
        
        Returns:
            List of new tokens
        """
        try:
            # Import the entire module instead of a specific function
            from . import standalone_token_data
            
            # Call the function through the module
            return await standalone_token_data.get_new_tokens()
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing get_new_tokens: {e}")
            raise NotImplementedError("API implementation not available in this version")
    
    async def get_completing_tokens(self) -> List[Dict[str, Any]]:
        """
        Get completing tokens from GMGN.
        
        Returns:
            List of completing tokens
        """
        try:
            # Import the entire module instead of a specific function
            from . import standalone_token_data
            
            # Call the function through the module
            return await standalone_token_data.get_completing_tokens()
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing get_completing_tokens: {e}")
            raise NotImplementedError("API implementation not available in this version")
    
    async def get_soaring_tokens(self) -> List[Dict[str, Any]]:
        """
        Get soaring tokens from GMGN.
        
        Returns:
            List of soaring tokens
        """
        try:
            # Import the entire module instead of a specific function
            from . import standalone_token_data
            
            # Call the function through the module
            return await standalone_token_data.get_soaring_tokens()
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing get_soaring_tokens: {e}")
            raise NotImplementedError("API implementation not available in this version")
    
    async def get_bonded_tokens(self) -> List[Dict[str, Any]]:
        """
        Get bonded tokens from GMGN.
        
        Returns:
            List of bonded tokens
        """
        try:
            # Import the entire module instead of a specific function
            from . import standalone_token_data
            
            # Call the function through the module
            return await standalone_token_data.get_bonded_tokens()
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing get_bonded_tokens: {e}")
            raise NotImplementedError("API implementation not available in this version")

# ---------------------------------------------------------------------------
# Function to fetch a single batch of market cap data via GMGN API
# ---------------------------------------------------------------------------
async def fetch_batch_async(session: aiohttp.ClientSession, token_address: str, batch_start: int, batch_end: int) -> List[Dict[str, Any]]:
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
    
    max_retries = 3
    retry_delay = 1  # Start with 1 second delay
    
    for retry in range(max_retries):
        try:
            # Delay between retries to avoid rate limiting
            await asyncio.sleep(0.5 + retry * 0.5)
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay * 2))
                    logger.warning(f"Rate limited for {token_address}, waiting {retry_after}s before retry {retry+1}/{max_retries}")
                    await asyncio.sleep(retry_after)
                    continue
                if response.status != 200:
                    logger.error(f"Error fetching batch for {token_address}: HTTP {response.status}")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return []
                
                data = await response.json()
                if data.get("code") != 0:
                    error_msg = data.get('msg', 'Unknown error')
                    logger.error(f"API error fetching batch for {token_address}: {error_msg}")
                    
                    if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                        if retry < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                    return []
                candles = data.get("data", [])
                logger.info(f"Fetched {len(candles)} candles for {token_address} from {start_time_str} to {end_time_str}")
                return candles
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching batch for {token_address} from {start_time_str} to {end_time_str}")
            if retry < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return []
            
        except Exception as e:
            logger.error(f"Error fetching batch for {token_address} from {start_time_str} to {end_time_str}: {e}")
            if retry < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return []
    
    return []  # Return empty list if all retries failed

# ---------------------------------------------------------------------------
# Function to fetch complete market cap data for a token using batch requests
# ---------------------------------------------------------------------------
async def _internal_fetch_token_mcaps_async(token_address: str, start_timestamp: datetime, end_timestamp: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Internal implementation for fetching token market cap data."""
    start_time_unix = int(start_timestamp.timestamp())
    current_time = int(datetime.now().timestamp())
    end_time_unix = int(end_timestamp.timestamp()) if end_timestamp else current_time

    all_candles = []
    batch_duration = 3000  # 3000 seconds (50 minutes) per batch
    current_batch_start = start_time_unix
    
    # Create batch ranges
    batch_ranges = []
    while current_batch_start < end_time_unix:
        current_batch_end = min(current_batch_start + batch_duration, end_time_unix)
        batch_ranges.append((current_batch_start, current_batch_end))
        current_batch_start += batch_duration
    
    logger.info(f"Created {len(batch_ranges)} batch ranges for {token_address}")
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_batch_async(session, token_address, batch_start, batch_end)
                 for batch_start, batch_end in batch_ranges]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Error in batch fetch for {token_address}: {result}")
                continue
            if result and not isinstance(result, BaseException):
                all_candles.extend(result)
        
        logger.info(f"Successfully fetched {len(all_candles)} candles for {token_address}")
    
    # Sort candles by time in ascending order
    all_candles.sort(key=lambda x: int(x.get("time", 0)))
    return all_candles

# ---------------------------------------------------------------------------
# Public Functions for Market Cap Data
# ---------------------------------------------------------------------------
async def fetch_token_mcaps_async(token_address: str, start_timestamp: datetime) -> List[Dict[str, Any]]:
    """
    Fetch market cap data for a token.
    
    Args:
        token_address: Token address to fetch data for
        start_timestamp: Starting timestamp for data
        
    Returns:
        List of market cap candles
    """
    from .standalone_mcap import standalone_fetch_token_mcaps
    
    # Convert datetime to timestamp if needed
    if isinstance(start_timestamp, datetime):
        start_time = int(start_timestamp.timestamp())
    else:
        start_time = int(start_timestamp)
    
    # Use the standalone implementation
    result = await standalone_fetch_token_mcaps(token_address, start_time)
    
    # Ensure we return a list
    if isinstance(result, dict):
        # If we got a dict (multiple tokens), just take the first one
        if token_address in result:
            return result[token_address]
        elif len(result) > 0:
            return list(result.values())[0]
        return []
    
    # Already a list
    return result

async def fetch_multiple_token_mcaps_async(token_addresses: List[str], start_timestamp: datetime) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch market cap data for multiple tokens.
    
    Args:
        token_addresses: List of token addresses to fetch data for
        start_timestamp: Starting timestamp for data
        
    Returns:
        Dictionary mapping token addresses to lists of market cap candles
    """
    from .standalone_mcap import standalone_fetch_token_mcaps
    
    # Convert datetime to timestamp if needed
    if isinstance(start_timestamp, datetime):
        start_time = int(start_timestamp.timestamp())
    else:
        start_time = int(start_timestamp)
    
    # Join the addresses with spaces
    token_str = " ".join(token_addresses)
    
    # Use the standalone implementation
    result = await standalone_fetch_token_mcaps(token_str, start_time)
    
    # Ensure we return a dict
    if not isinstance(result, dict):
        # If we got a list (single token), convert to dict
        return {token_addresses[0]: result} if token_addresses else {}
    
    # Already a dict
    return result