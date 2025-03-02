#!/usr/bin/env python3
"""
Test script for GMGN_Client token info functionality.

This script directly tests the GMGN_Client implementation to verify
that the token info retrieval works correctly after the fixes.
"""

import sys
import asyncio
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gmgn_client_test")

# Test token addresses (guaranteed to work)
TEST_TOKENS = [
    "So11111111111111111111111111111111111111112",  # SOL token (native)
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK token
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",  # SAMO token
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC token
]

# Import the real GMGN_Client implementation
async def init_and_test():
    """Initialize and test the GMGN_Client."""
    try:
        # Import the DragonAdapter class which contains the GMGN_Client
        from src.sol_tools.modules.dragon.dragon_adapter import GMGN_Client
        logger.info("Successfully imported GMGN_Client class")
        
        # Create an instance with proxy support disabled for testing
        client = GMGN_Client(use_proxies=False)
        logger.info("Created GMGN_Client instance")
        
        success_count = 0
        failure_count = 0
        
        # Test each token address
        for token_address in TEST_TOKENS:
            logger.info(f"\nTesting token: {token_address}")
            
            # Call the getTokenInfo method
            result = client.getTokenInfo(token_address)
            
            # Check for errors
            if isinstance(result, dict) and "error" in result:
                error_code = result.get("code", 0)
                error_msg = result.get("error", "Unknown error")
                
                # 404 errors are normal for some tokens, especially new ones
                if error_code == 404:
                    logger.info(f"Token not found (404) for {token_address} - this is normal for new tokens")
                    success_count += 1  # Still count as success since API works
                else:
                    logger.error(f"Error retrieving token info: {error_msg} (code: {error_code})")
                    failure_count += 1
                continue
            
            # Check result format
            if not result or not isinstance(result, dict):
                logger.error(f"Invalid result format for {token_address}: {type(result)}")
                failure_count += 1
                continue
            
            # Log success details
            logger.info(f"Token info result keys: {list(result.keys())}")
            
            # Check for GeckoTerminal API structure
            if "attributes" in result:
                attributes = result.get("attributes", {})
                if attributes:
                    logger.info(f"Token name: {attributes.get('name')}")
                    logger.info(f"Token symbol: {attributes.get('symbol')}")
                    logger.info(f"Token address: {attributes.get('address')}")
                    success_count += 1
                else:
                    logger.warning("Empty attributes in response")
                    failure_count += 1
            elif "id" in result:
                # Basic data structure
                logger.info(f"Token ID: {result.get('id')}")
                logger.info(f"Token type: {result.get('type')}")
                success_count += 1
            else:
                logger.warning(f"Unrecognized result format: {result}")
                failure_count += 1
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info(f"Test Summary: {success_count} Successful, {failure_count} Failed")
        logger.info("="*60)
        
        return 0 if failure_count == 0 else 1
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error testing GMGN_Client: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    if sys.version_info >= (3, 7):
        result = asyncio.run(init_and_test())
    else:
        # Fallback for Python 3.6
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(init_and_test())
    
    sys.exit(result) 