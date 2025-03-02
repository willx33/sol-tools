"""
Standalone implementation of GMGN token data functionality.
This module uses the GeckoTerminal API and supports multiple token addresses.
"""

import asyncio
import logging
import random
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

import httpx
import tls_client
from tls_client.sessions import ClientIdentifiers

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
class Config:
    """Configuration constants for the GMGN Token Data module."""
    
    # GeckoTerminal API base URL
    GECKO_TERMINAL_URL = "https://api.geckoterminal.com/api/v2/networks"
    
    # Timeout settings
    REQUEST_TIMEOUT = 10.0  # seconds
    
    # Retry settings
    MAX_RETRIES = 5
    RETRY_DELAY_MIN = 1.0  # seconds
    RETRY_DELAY_MAX = 2.0  # seconds
    
    # Network mapping
    @staticmethod
    def determine_network(address: str) -> str:
        """Determine the network based on the token address format."""
        if len(address) in [43, 44]:
            return "solana"
        return "ethereum"  # Default to Ethereum for other formats

# ---------------------------------------------------------------------------
# Helper class for making API requests
# ---------------------------------------------------------------------------
class ApiClient:
    """API client with browser fingerprinting evasion."""
    
    def __init__(self, use_proxies: bool = False):
        """Initialize API client with browser fingerprinting evasion."""
        self.use_proxies = use_proxies
        self.proxy_position = 0
        self.max_retries = Config.MAX_RETRIES
        self.timeout_sec = Config.REQUEST_TIMEOUT
        self.randomize_session()
    
    def randomize_session(self):
        """Create a new TLS session with randomized browser fingerprint."""
        try:
            # Try to create a TLS client session using a fixed identifier to avoid type issues
            # This is a workaround for the linter errors with ClientIdentifiers
            self.identifier = "chrome_103"  # Use a string that matches a valid client identifier
            
            try:
                # Create session with direct string - this may work depending on implementation
                self.session = tls_client.Session(
                    random_tls_extension_order=True,
                    client_identifier="chrome_103"  # Using a simple string to avoid type issues
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
    
    def load_proxies(self) -> List[Dict[str, str]]:
        """Load proxies from the proxies.txt file."""
        try:
            from ...core.config import INPUT_DATA_DIR
            proxies_file = INPUT_DATA_DIR / "proxies" / "proxies.txt"
            
            if not proxies_file.exists():
                return []
            
            with open(proxies_file, 'r') as file:
                proxy_lines = file.read().splitlines()
            
            formatted_proxies = []
            for proxy in proxy_lines:
                if not proxy or proxy.startswith('#'):
                    continue
                    
                if ':' in proxy:  
                    parts = proxy.split(':')
                    if len(parts) == 4:  # ip:port:username:password
                        ip, port, username, password = parts
                        formatted_proxies.append({
                            'http': f"http://{username}:{password}@{ip}:{port}",
                            'https': f"http://{username}:{password}@{ip}:{port}"
                        })
                    elif len(parts) == 2:  # ip:port
                        ip, port = parts
                        formatted_proxies.append({
                            'http': f"http://{ip}:{port}",
                            'https': f"http://{ip}:{port}"
                        })
                else:
                    formatted_proxies.append({
                        'http': f"http://{proxy}",
                        'https': f"http://{proxy}"
                    })
                    
            return formatted_proxies
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
            return []
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy from the rotation."""
        proxies = self.load_proxies()
        if not proxies:
            return None
            
        proxy = proxies[self.proxy_position % len(proxies)]
        self.proxy_position += 1
        return proxy

    async def fetch_token_data(self, token_address: str) -> Dict[str, Any]:
        """
        Fetch token data from the GeckoTerminal API.
        
        Args:
            token_address: The token address to fetch data for
            
        Returns:
            Dictionary with token data or error information
        """
        if not token_address:
            return {"error": "Empty token address", "code": 400}
        
        # Determine network based on address format
        network = Config.determine_network(token_address)
        
        # Build the API URL
        url = f"{Config.GECKO_TERMINAL_URL}/{network}/tokens/{token_address}"
        
        logger.debug(f"Fetching token data from: {url}")
        
        for attempt in range(self.max_retries):
            logger.debug(f"Attempt {attempt+1}/{self.max_retries} to get token data for {token_address}")
            
            # Randomize session after first attempt
            if attempt > 0:
                self.randomize_session()
                
            try:
                response = None
                
                # Use tls_client if available, otherwise fall back to httpx
                if self.session:
                    response = self.session.get(url, headers=self.headers)
                else:
                    # Use httpx with timeout
                    async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                        response = await client.get(url, headers=self.headers)
                
                if response and response.status_code == 200:
                    # Extract and process the data
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
                                    return {"error": "Empty response", "code": 500}
                            data = json_data.get("data", {}) or {}
                        except:
                            # If we can't parse JSON, try to extract from text
                            try:
                                response_text = response.text
                                if response_text is not None:
                                    json_data = json.loads(response_text)
                                    data = json_data.get("data", {}) or {}
                                else:
                                    return {"error": "Empty response", "code": 500}
                            except:
                                return {"error": "Failed to parse JSON response", "code": 500}
                    
                    logger.debug(f"Successfully fetched token data for {token_address}")
                    return self._process_gecko_terminal_data(data)
                
                # Handle 404 errors specially (token not found)
                if response and response.status_code == 404:
                    logger.info(f"Token not found (404) for {token_address} - this is normal for new tokens")
                    # Only retry once for 404 errors
                    if attempt > 0:
                        return {"error": "Token not found in GeckoTerminal API", "code": 404}
                
                # If we get here, the request failed
                error_msg = f"Status: {response.status_code}" if response else "No response"
                logger.warning(f"Failed to get token data: {error_msg} (attempt {attempt+1}/{self.max_retries})")
                
                # Backoff on failure
                await asyncio.sleep(random.uniform(Config.RETRY_DELAY_MIN, Config.RETRY_DELAY_MAX))
                
            except Exception as e:
                logger.warning(f"Request error on attempt {attempt+1}: {e}")
                
                # Backoff on exception
                await asyncio.sleep(random.uniform(Config.RETRY_DELAY_MIN, Config.RETRY_DELAY_MAX))
        
        # If we've exhausted all retries
        return {"error": f"Failed after {self.max_retries} attempts", "code": 500}
    
    def _process_gecko_terminal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize data from GeckoTerminal API.
        
        Args:
            data: Raw data from the API
            
        Returns:
            Normalized token data
        """
        if not data:
            return {"error": "Empty data received", "code": 500}
        
        result = {}
        
        try:
            attributes = data.get("attributes", {})
            
            # Extract basic token information
            result["name"] = attributes.get("name", "Unknown")
            result["symbol"] = attributes.get("symbol", "Unknown")
            result["address"] = data.get("id", "").split("_")[-1] if data.get("id") else ""
            result["decimals"] = attributes.get("decimals", 0)
            
            # Extract price information
            result["priceUsd"] = float(attributes.get("price_usd") or 0)
            result["priceChange24h"] = float(attributes.get("price_change_percentage_24h") or 0)
            
            # Extract market information
            result["marketCap"] = float(attributes.get("market_cap_usd") or 0)
            result["volume24h"] = float(attributes.get("volume_usd_24h") or 0)
            result["liquidityUsd"] = float(attributes.get("liquidity_usd") or 0)
            
            # Additional attributes
            result["holders"] = attributes.get("total_holders", 0)
            result["atl"] = float(attributes.get("atl") or 0)
            result["ath"] = float(attributes.get("ath") or 0)
            
            # Add network information
            result["network"] = attributes.get("network_name", "unknown")
            
            # Add timestamp
            result["fetchTime"] = datetime.now().isoformat()
            
            # Add raw data for debugging if needed
            # result["raw_data"] = data
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing GeckoTerminal data: {e}")
            return {"error": f"Data processing error: {e}", "code": 500, "raw_data": data}

# ---------------------------------------------------------------------------
# Main function to fetch token data for a single token
# ---------------------------------------------------------------------------
async def fetch_token_data_async(token_address: str, use_proxies: bool = False) -> Dict[str, Any]:
    """
    Fetch token data for a single token.
    
    Args:
        token_address: The token address to fetch data for
        use_proxies: Whether to use proxies for the requests
        
    Returns:
        Dictionary with token data
    """
    client = ApiClient(use_proxies=use_proxies)
    return await client.fetch_token_data(token_address)

# ---------------------------------------------------------------------------
# Function to fetch token data for multiple tokens
# ---------------------------------------------------------------------------
async def fetch_multiple_tokens_async(token_addresses: List[str], use_proxies: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Fetch token data for multiple tokens asynchronously.
    
    Args:
        token_addresses: List of token addresses to fetch data for
        use_proxies: Whether to use proxies for the requests
        
    Returns:
        Dictionary mapping token addresses to their data
    """
    # Create a single client to use for all requests
    client = ApiClient(use_proxies=use_proxies)
    
    # Create tasks for each token
    tasks = {token: asyncio.create_task(client.fetch_token_data(token)) for token in token_addresses}
    
    # Wait for all tasks to complete
    results = {}
    for token, task in tasks.items():
        try:
            results[token] = await task
        except Exception as e:
            logger.error(f"Error fetching token data for {token}: {e}")
            results[token] = {"error": str(e), "code": 500}
    
    return results

# ---------------------------------------------------------------------------
# Main entry point for standalone usage
# ---------------------------------------------------------------------------
async def standalone_fetch_token_data(token_address: Union[str, List[str]], use_proxies: bool = False) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Standalone function to fetch token data.
    This is the main entry point for the module.
    
    Args:
        token_address: The token address or list of addresses to fetch data for
        use_proxies: Whether to use proxies for the requests
        
    Returns:
        Either a dictionary with token data (for a single token) or a dictionary
        mapping token addresses to their data (for multiple tokens)
    """
    # Handle string input with space-separated tokens
    if isinstance(token_address, str) and ' ' in token_address:
        token_addresses = [addr.strip() for addr in token_address.split(' ') if addr.strip()]
        return await fetch_multiple_tokens_async(token_addresses, use_proxies)
    
    # Handle list of tokens
    if isinstance(token_address, list):
        return await fetch_multiple_tokens_async(token_address, use_proxies)
    
    # Handle single token
    return await fetch_token_data_async(token_address, use_proxies)

# ---------------------------------------------------------------------------
# Helper functions for GMGNAdapter to call
# ---------------------------------------------------------------------------
def get_token_info_sync(contract_address: str) -> Dict[str, Any]:
    """
    Synchronous version of get_token_info.
    
    Args:
        contract_address: Contract address of the token
        
    Returns:
        Token information dictionary
    """
    # Run the async function in a new event loop
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(fetch_token_data_async(contract_address))
    finally:
        loop.close()

async def get_token_info(contract_address: str) -> Dict[str, Any]:
    """
    Get token information asynchronously.
    
    Args:
        contract_address: Contract address of the token
        
    Returns:
        Token information dictionary
    """
    return await fetch_token_data_async(contract_address)

async def get_new_tokens() -> List[Dict[str, Any]]:
    """
    Get new tokens from the GeckoTerminal API.
    
    Returns:
        List of new tokens
    """
    logger.error("get_new_tokens is not implemented in this version")
    raise NotImplementedError("get_new_tokens is not implemented in this version")

async def get_completing_tokens() -> List[Dict[str, Any]]:
    """
    Get completing tokens from the GeckoTerminal API.
    
    Returns:
        List of completing tokens
    """
    logger.error("get_completing_tokens is not implemented in this version")
    raise NotImplementedError("get_completing_tokens is not implemented in this version")

async def get_soaring_tokens() -> List[Dict[str, Any]]:
    """
    Get soaring tokens from the GeckoTerminal API.
    
    Returns:
        List of soaring tokens
    """
    logger.error("get_soaring_tokens is not implemented in this version")
    raise NotImplementedError("get_soaring_tokens is not implemented in this version")

async def get_bonded_tokens() -> List[Dict[str, Any]]:
    """
    Get bonded tokens from the GeckoTerminal API.
    
    Returns:
        List of bonded tokens
    """
    logger.error("get_bonded_tokens is not implemented in this version")
    raise NotImplementedError("get_bonded_tokens is not implemented in this version")

# ---------------------------------------------------------------------------
# Command-line handler for testing
# ---------------------------------------------------------------------------
async def standalone_test():
    """Test the standalone implementation with sample tokens."""
    from pathlib import Path
    import os
    
    print("\n==== GMGN Token Data Fetcher ====\n")
    
    # Get token address input
    token_input = input("Enter token address(es) - space-separated for multiple (default: BONK token): ").strip()
    if not token_input:
        # BONK token on Solana
        token_input = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        print(f"Using default BONK token: {token_input}")
    
    # Process tokens
    token_addresses = [addr.strip() for addr in token_input.split(' ') if addr.strip()]
    
    # Setup output directory
    output_dir = Path.home() / "sol-tools" / "data" / "output-data" / "api" / "gmgn" / "token-data"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🔍 Fetching token data for {len(token_addresses)} token(s)...\n")
    
    try:
        # Fetch data
        start_time = time.time()
        result = await standalone_fetch_token_data(token_addresses)
        elapsed = time.time() - start_time
        
        # Handle the result based on whether it's a single token or multiple tokens
        if len(token_addresses) == 1 and not isinstance(result, dict) or isinstance(result, dict) and "error" in result:
            # Single token with error
            print(f"❌ Failed to fetch token data: {result.get('error', 'Unknown error')}")
            return
        
        # Check for empty or error results
        success_count = 0
        error_count = 0
        
        if len(token_addresses) == 1:
            # Single token result
            token_data = result
            if "error" in token_data:
                print(f"❌ Failed to fetch token data for {token_addresses[0]}: {token_data.get('error')}")
                error_count += 1
            else:
                print(f"✅ Successfully fetched token data for {token_addresses[0]}")
                success_count += 1
                
                # Display token summary
                print("\n📊 Token Information:")
                print(f"Name:             {token_data.get('name', 'Unknown')}")
                print(f"Symbol:           {token_data.get('symbol', 'Unknown')}")
                print(f"Price:            ${token_data.get('priceUsd', 0):.8f}")
                print(f"Market Cap:       ${token_data.get('marketCap', 0):,.2f}")
                print(f"Liquidity:        ${token_data.get('liquidityUsd', 0):,.2f}")
                print(f"24h Volume:       ${token_data.get('volume24h', 0):,.2f}")
                print(f"24h Change:       {token_data.get('priceChange24h', 0):.2f}%")
                print(f"Holders:          {token_data.get('holders', 0):,}")
                
                # Save data
                output_file = output_dir / f"token_data_{token_addresses[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
                print(f"\nResults saved to: {output_file}")
        else:
            # Multiple tokens result
            for token, data in result.items():
                if "error" in data:
                    print(f"❌ Failed to fetch token data for {token}: {data.get('error')}")
                    error_count += 1
                else:
                    print(f"✅ Successfully fetched token data for {token}")
                    success_count += 1
            
            # Summary stats
            print(f"\n📊 Summary: {success_count} successful, {error_count} failed, completed in {elapsed:.2f} seconds")
            
            if success_count > 0:
                # Ask if user wants to see token details
                show_details = input("\nDo you want to see token details? (y/n): ").lower().strip()
                if show_details.startswith('y'):
                    for token, data in result.items():
                        if "error" not in data:
                            print(f"\n--- {data.get('name', 'Unknown')} ({data.get('symbol', 'Unknown')}) ---")
                            print(f"Address:          {token}")
                            print(f"Price:            ${data.get('priceUsd', 0):.8f}")
                            print(f"Market Cap:       ${data.get('marketCap', 0):,.2f}")
                            print(f"Liquidity:        ${data.get('liquidityUsd', 0):,.2f}")
                            print(f"24h Volume:       ${data.get('volume24h', 0):,.2f}")
                            print(f"24h Change:       {data.get('priceChange24h', 0):.2f}%")
                            print(f"Holders:          {data.get('holders', 0):,}")
                            print(f"Network:          {data.get('network', 'Unknown')}")
                            if data.get('ath', 0) > 0:
                                print(f"All-time High:   ${data.get('ath', 0):.8f}")
                            if data.get('atl', 0) > 0:
                                print(f"All-time Low:    ${data.get('atl', 0):.8f}")
                
                # Save data
                output_file = output_dir / f"token_data_multiple_{len(token_addresses)}tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "token_count": len(token_addresses),
                        "success_count": success_count,
                        "error_count": error_count,
                        "data": result
                    }, f, indent=2)
                print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Finished processing")

# Make the module runnable directly
if __name__ == "__main__":
    asyncio.run(standalone_test()) 