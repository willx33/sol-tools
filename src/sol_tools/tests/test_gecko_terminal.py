#!/usr/bin/env python3
"""
Standalone test for GeckoTerminal API.

This script tests the GeckoTerminal API directly with known token addresses
to validate the token information retrieval functionality.
"""

import sys
import json
import logging
import httpx
import asyncio
import random
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gecko_terminal_test")

# Test token addresses (guaranteed to work)
TEST_TOKENS = [
    "So11111111111111111111111111111111111111112",  # SOL token (native)
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK token
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",  # SAMO token
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC token
]

async def get_token_info(contract_addr: str) -> Dict[str, Any]:
    """
    Get token information from GeckoTerminal API.
    
    Args:
        contract_addr: Token contract address
        
    Returns:
        Token information dictionary or error details
    """
    if not contract_addr:
        return {"error": "Empty contract address", "code": 400}
    
    # Determine network based on address format
    network = "solana" if len(contract_addr) in [43, 44] else "ethereum"
    
    # Use the correct endpoint for the network type
    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{contract_addr}"
    
    logger.info(f"Fetching token info from: {url}")
    
    max_retries = 3
    for attempt in range(max_retries):
        logger.info(f"Attempt {attempt+1}/{max_retries} to get token info for {contract_addr}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json().get("data", {}) or {}
                    logger.info(f"Successfully fetched token info for {contract_addr}")
                    return data
                
                # Handle 404 errors specially (token not found)
                if response.status_code == 404:
                    logger.info(f"Token not found (404) for {contract_addr} - this is normal for new tokens")
                    # Only retry once for 404 errors
                    if attempt > 0:
                        return {"error": "Token not found in GeckoTerminal API", "code": 404}
                
                # If we get here, the request failed
                error_msg = f"Status: {response.status_code}"
                logger.warning(f"Failed to get token info: {error_msg} (attempt {attempt+1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(1.0, 2.0))  # Backoff on failure
                
        except Exception as e:
            logger.error(f"Request error on attempt {attempt+1}: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(1.0, 2.0))
    
    logger.error(f"All {max_retries} attempts to get token info failed for {contract_addr}")
    return {"error": f"Failed after {max_retries} attempts", "code": 0}

async def main():
    """Test GeckoTerminal API with multiple token addresses."""
    
    logger.info(f"Testing GeckoTerminal API with {len(TEST_TOKENS)} tokens")
    
    success_count = 0
    failure_count = 0
    
    for token_address in TEST_TOKENS:
        logger.info(f"\nTesting token: {token_address}")
        
        # Get token info
        result = await get_token_info(token_address)
        
        # Check if we got an error
        if "error" in result:
            logger.error(f"Error retrieving token info: {result.get('error')}")
            logger.error(f"Error code: {result.get('code')}")
            failure_count += 1
            continue
        
        # Log the structure of the result
        try:
            logger.info(f"Token info result keys: {list(result.keys())}")
            
            # For debugging, print the entire result with indentation
            pretty_result = json.dumps(result, indent=2)
            logger.info(f"Token info result: {pretty_result}")
            
            # Check for attributes structure in GeckoTerminal API
            if "attributes" in result:
                attributes = result.get("attributes", {})
                if attributes:
                    logger.info(f"Token name: {attributes.get('name')}")
                    logger.info(f"Token symbol: {attributes.get('symbol')}")
                    logger.info(f"Token address: {attributes.get('address')}")
                    logger.info(f"Token price USD: {attributes.get('price_usd')}")
                    success_count += 1
                else:
                    logger.warning("Empty attributes in response")
                    failure_count += 1
            else:
                logger.warning("No attributes found in response structure")
                failure_count += 1
                
        except Exception as e:
            logger.error(f"Error processing token info: {e}")
            failure_count += 1
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info(f"Test Summary: {success_count} Successful, {failure_count} Failed")
    logger.info("="*60)
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    if sys.version_info >= (3, 7):
        sys.exit(asyncio.run(main()))
    else:
        # Fallback for Python 3.6
        loop = asyncio.get_event_loop()
        sys.exit(loop.run_until_complete(main())) 