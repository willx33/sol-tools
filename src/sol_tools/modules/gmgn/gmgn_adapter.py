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
# Function to fetch a single batch of market cap data via GMGN API
# ---------------------------------------------------------------------------
async def fetch_batch_async(session: aiohttp.ClientSession, token_address: str, batch_start: int, batch_end: int):
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
            
            async with session.get(url, params=params, headers=headers, timeout=30) as response:
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
async def fetch_token_mcaps_async(token_address: str, start_timestamp: datetime, end_timestamp: datetime = None):
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
            if result:
                all_candles.extend(result)
        
        logger.info(f"Successfully fetched {len(all_candles)} candles for {token_address}")
    
    # Sort candles by time in ascending order
    all_candles.sort(key=lambda x: int(x.get("time", 0)))
    return all_candles