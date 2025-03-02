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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import httpx
import tls_client

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
class Config:
    """Configuration constants for the GMGN Market Cap module."""
    
    # GeckoTerminal API base URL
    GECKO_TERMINAL_URL = "https://api.geckoterminal.com/api/v2"
    
    # Timeout settings
    REQUEST_TIMEOUT = 15.0  # seconds
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY_MIN = 1.0  # seconds
    RETRY_DELAY_MAX = 2.0  # seconds

# ---------------------------------------------------------------------------
# Helper class for making API requests
# ---------------------------------------------------------------------------
class ApiClient:
    """API client with browser fingerprinting evasion."""
    
    def __init__(self):
        """Initialize API client with browser fingerprinting evasion."""
        self.max_retries = Config.MAX_RETRIES
        self.timeout_sec = Config.REQUEST_TIMEOUT
        self.randomize_session()
    
    def randomize_session(self):
        """Create a new TLS session with randomized browser fingerprint."""
        try:
            # Try to create a TLS client session with a fixed identifier to avoid type issues
            self.identifier = "chrome_103"  # Use a string that matches a valid client identifier
            
            try:
                # Create session with direct string
                self.session = tls_client.Session(
                    random_tls_extension_order=True,
                    client_identifier="chrome_103"  # Using a simple string
                )
            except TypeError:
                # Fallback - create without client_identifier if needed
                self.session = tls_client.Session(
                    random_tls_extension_order=True
                )
                logger.debug("Created TLS session without client_identifier due to type error")
            
            # Use a fixed user agent
            self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
            
        except Exception as e:
            # Create a dummy session if tls_client fails
            logger.warning(f"Failed to create TLS session: {e}, falling back to regular HTTP client")
            self.identifier = "chrome_103"
            self.session = None
            self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
        
        # Set headers to mimic browser
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'dnt': '1',
            'user-agent': self.user_agent,
            'referer': 'https://www.geckoterminal.com/'
        }
    
    async def fetch_ohlcv(self, token_address: str, network: str, start_timestamp: Optional[Union[datetime, int]] = None, interval: str = "day") -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data for a token from GeckoTerminal API.
        
        Args:
            token_address: The token contract address
            network: Network (solana, ethereum, etc.)
            start_timestamp: Start time (datetime or unix timestamp)
            interval: Time interval (hour, day, or week)
            
        Returns:
            List of OHLCV candles
        """
        # Convert datetime to Unix timestamp (seconds) if needed
        if start_timestamp is None:
            start_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
        elif isinstance(start_timestamp, datetime):
            start_timestamp = int(start_timestamp.timestamp())
        
        # Normalize network name
        network = network.lower()
        if network == "sol":
            network = "solana"
        elif network == "eth":
            network = "ethereum"
        
        # Build URL
        base_url = f"{Config.GECKO_TERMINAL_URL}/networks/{network}/tokens/{token_address}/ohlcv/{interval}"
        
        # Add parameters
        params = {
            "aggregate": 1,
            "before_timestamp": int(time.time()),
            "after_timestamp": start_timestamp,
            "limit": 1000,  # Max allowed by API
            "currency": "usd"
        }
        
        for attempt in range(self.max_retries):
            try:
                # Use TLS client if available, otherwise use httpx
                if self.session is not None:
                    # TLS client doesn't accept timeout parameter directly in get
                    response = self.session.get(
                        base_url,
                        params=params,
                        headers=self.headers
                    )
                else:
                    # Fallback to httpx if tls_client isn't working
                    async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                        response = await client.get(
                            base_url,
                            params=params,
                            headers=self.headers
                        )
                
                # Check if we got a valid response
                if response and response.status_code == 200:
                    # Verify that we can parse the response
                    data = {}
                    if hasattr(response, 'json'):
                        try:
                            if callable(response.json):
                                json_data = response.json()
                            else:
                                response_text = response.text
                                if response_text is not None:
                                    json_data = json.loads(response_text)
                                else:
                                    return []
                            data = json_data.get("data", {}) or {}
                        except:
                            # If we can't parse JSON, try to extract from text
                            try:
                                response_text = response.text
                                if response_text is not None:
                                    json_data = json.loads(response_text)
                                    data = json_data.get("data", {}) or {}
                                else:
                                    return []
                            except:
                                return []
                    
                    # Process the OHLCV data and return
                    result = []
                    
                    try:
                        attributes = data.get("attributes", {})
                        ohlcv_list = attributes.get("ohlcv_list", [])
                        
                        for candle in ohlcv_list:
                            if len(candle) >= 6:  # Make sure we have all required data points
                                unix_time = candle[0] / 1000  # Convert from milliseconds to seconds
                                timestamp = datetime.fromtimestamp(unix_time)
                                
                                # Format the candle data
                                result.append({
                                    "timestamp": timestamp.isoformat(),
                                    "time": unix_time,
                                    "open": float(candle[1]),
                                    "high": float(candle[2]),
                                    "low": float(candle[3]),
                                    "close": float(candle[4]),
                                    "volume": float(candle[5]),
                                    # Calculate market cap if data is available
                                    "market_cap": self._calculate_market_cap(
                                        float(candle[4]),  # close price
                                        attributes.get("token_supply", 0)
                                    )
                                })
                    except Exception as e:
                        logger.warning(f"Error processing OHLCV data: {e}")
                    
                    # Return whatever we were able to parse
                    return result
                
                # Handle 404 errors specially (token not found)
                if response and response.status_code == 404:
                    logger.info(f"Token not found (404) for {token_address} on {network}")
                    return []
                
                # If we get here, the request failed
                error_msg = f"Status: {response.status_code}" if response else "No response"
                logger.warning(f"Failed to get OHLCV data: {error_msg} (attempt {attempt+1}/{self.max_retries})")
                
                # Backoff on failure
                await asyncio.sleep(random.uniform(Config.RETRY_DELAY_MIN, Config.RETRY_DELAY_MAX))
                
            except Exception as e:
                logger.warning(f"Exception during OHLCV fetch: {e} (attempt {attempt+1}/{self.max_retries})")
                
                # Backoff on exception
                await asyncio.sleep(random.uniform(Config.RETRY_DELAY_MIN, Config.RETRY_DELAY_MAX))
        
        # If we get here, all attempts failed
        logger.error(f"All {self.max_retries} attempts to fetch OHLCV data failed for {token_address} on {network}")
        return []
    
    def _calculate_market_cap(self, price: float, token_supply: float) -> float:
        """Calculate market cap from price and supply."""
        if price <= 0 or token_supply <= 0:
            return 0.0
        
        return price * token_supply

# ---------------------------------------------------------------------------
# Main function to fetch market cap data
# ---------------------------------------------------------------------------
async def standalone_fetch_token_mcaps(token_addresses: Union[str, List[str]], start_timestamp: Union[datetime, int]) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Fetch token market cap data for one or multiple tokens.
    
    Args:
        token_addresses: One token address or a list/space-separated string of token addresses
        start_timestamp: Start time (datetime or unix timestamp)
        
    Returns:
        List of market cap candles for a single token, or
        Dictionary of {token_address: List of market cap candles} for multiple tokens
    """
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
        # Create client
        client = ApiClient()
        
        # Process each token
        results = {}
        for token in token_addresses:
            # Determine network based on address format
            network = "solana" if len(token) in [43, 44] else "ethereum"
            
            # Fetch data
            logger.info(f"Fetching market cap data for {token} on {network}...")
            candles = await client.fetch_ohlcv(token, network, start_timestamp, "day")
            
            # Store results
            results[token] = candles
            
            # Short delay between requests to avoid rate limiting
            await asyncio.sleep(0.5)
        
        return results
    
    # Single token processing
    elif len(token_addresses) == 1:
        token = token_addresses[0]
        
        # Determine network based on address format
        network = "solana" if len(token) in [43, 44] else "ethereum"
        
        # Create client and fetch data
        client = ApiClient()
        logger.info(f"Fetching market cap data for {token} on {network}...")
        return await client.fetch_ohlcv(token, network, start_timestamp, "day")
    
    # No tokens provided
    else:
        logger.error("No token addresses provided")
        return {}

# ---------------------------------------------------------------------------
# Command-line handler for testing
# ---------------------------------------------------------------------------
async def standalone_test():
    """Test the standalone implementation."""
    import sys
    
    # Check command line args
    if len(sys.argv) < 2:
        print("Usage: python -m src.sol_tools.modules.gmgn.standalone_mcap <token_address> [start_date]")
        print("Example: python -m src.sol_tools.modules.gmgn.standalone_mcap DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")
        return 1
    
    # Get token addresses
    token_addresses = sys.argv[1]
    
    # Get start date if provided, otherwise use 30 days ago
    if len(sys.argv) >= 3:
        try:
            # Try to parse as YYYY-MM-DD
            start_date = datetime.strptime(sys.argv[2], "%Y-%m-%d")
        except ValueError:
            try:
                # Try to parse as integer (unix timestamp)
                start_date = int(sys.argv[2])
            except ValueError:
                print(f"Error: Invalid date format: {sys.argv[2]}")
                print("Please use YYYY-MM-DD format or a unix timestamp")
                return 1
    else:
        # Default to 30 days ago
        start_date = datetime.now() - timedelta(days=30)
    
    print(f"Fetching market cap data for: {token_addresses}")
    print(f"Timeframe: From {start_date}")
    
    # Fetch the data
    start_time = time.time()
    result = await standalone_fetch_token_mcaps(token_addresses, start_date)
    elapsed = time.time() - start_time
    
    # Check if we have multiple tokens
    if isinstance(result, dict):
        # Multiple tokens
        print(f"\nFetched data for {len(result)} tokens in {elapsed:.2f} seconds:")
        
        for token, candles in result.items():
            if candles:
                print(f"\n{token}: {len(candles)} candles")
                # Show first and last candle
                if len(candles) > 0:
                    print(f"First: {candles[0]['timestamp']} - ${candles[0]['close']} - MC: ${candles[0]['market_cap']:,.2f}")
                    print(f"Last:  {candles[-1]['timestamp']} - ${candles[-1]['close']} - MC: ${candles[-1]['market_cap']:,.2f}")
            else:
                print(f"\n{token}: No data found")
    else:
        # Single token
        candles = result
        if candles:
            print(f"\nFetched {len(candles)} candles in {elapsed:.2f} seconds")
            # Show first and last candle
            if len(candles) > 0:
                print(f"First: {candles[0]['timestamp']} - ${candles[0]['close']} - MC: ${candles[0]['market_cap']:,.2f}")
                print(f"Last:  {candles[-1]['timestamp']} - ${candles[-1]['close']} - MC: ${candles[-1]['market_cap']:,.2f}")
                
                # Ask if user wants to see all data
                show_all = input("\nDo you want to see all candles? (y/n): ").lower().strip()
                if show_all.startswith('y'):
                    for candle in candles:
                        print(f"{candle['timestamp']} - ${candle['close']} - MC: ${candle['market_cap']:,.2f}")
        else:
            print("\nNo data found")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(standalone_test())) 