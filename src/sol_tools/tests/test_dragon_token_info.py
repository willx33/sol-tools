#!/usr/bin/env python3
"""
Test script to directly test the GMGN_Client.getTokenInfo method.

This script isolates the token info functionality to identify issues
with maximum recursion depth.
"""

import sys
import time
import random
import logging
import argparse
import traceback
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("dragon_token_info_test")

# Test token addresses (guaranteed to work)
TEST_TOKENS = [
    "So11111111111111111111111111111111111111112",  # SOL token (native)
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK token
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",  # SAMO token
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC token
]

def run_gmgn_client_test(debug_mode: bool = False) -> int:
    """
    Test the GMGN_Client.getTokenInfo method directly.
    
    Args:
        debug_mode: Enable debug logging
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        if debug_mode:
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
        
        # Import the GMGN_Client class
        logger.info("Importing GMGN_Client...")
        from src.sol_tools.modules.dragon.dragon_adapter import GMGN_Client
        logger.info("Successfully imported GMGN_Client")
        
        # Create an instance
        logger.info("Creating GMGN_Client instance...")
        client = GMGN_Client(use_proxies=False)
        logger.info("GMGN_Client instance created")
        
        # Use a separate counter variable instead of modifying the class
        call_count = 0
        
        # Save a reference to the original method
        original_get_token_info = client.getTokenInfo
        
        # Define a wrapper function to monitor recursion
        def getTokenInfo_with_monitoring(contract_addr: str) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            
            if call_count > 1000:  # Set a reasonable limit
                logger.critical(f"Recursion detected! Call count: {call_count}")
                raise RecursionError("Maximum recursion depth detected in getTokenInfo!")
                
            if call_count % 100 == 0:
                logger.warning(f"Deep call stack detected: {call_count} calls")
                
            # Log the URL construction for debugging
            network = "solana" if len(contract_addr) in [43, 44] else "ethereum"
            url = f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{contract_addr}"
            logger.debug(f"Call #{call_count} - URL: {url}")
            
            result = original_get_token_info(contract_addr)
            call_count -= 1
            return result
        
        # Replace the method with our monitored version if debug_mode is enabled
        if debug_mode:
            logger.info("Installing monitoring wrapper...")
            client.getTokenInfo = getTokenInfo_with_monitoring
            
        # Test with each token address
        success_count = 0
        failure_count = 0
        
        for token_address in TEST_TOKENS:
            logger.info(f"\nTesting token: {token_address}")
            
            try:
                # Reset call count for each test
                call_count = 0
                
                # Call getTokenInfo
                result = client.getTokenInfo(token_address)
                
                # Check if it's an error response
                if isinstance(result, dict) and "error" in result:
                    error_code = result.get("code", 0)
                    error_msg = result.get("error", "Unknown error")
                    
                    # 404 errors are normal for some tokens
                    if error_code == 404:
                        logger.info(f"Token not found (404) for {token_address}")
                        # Still count as a success since the API is working properly
                        success_count += 1
                    else:
                        logger.error(f"Error retrieving token info: {error_msg}")
                        failure_count += 1
                    continue
                
                # Check result structure
                if isinstance(result, dict):
                    logger.info(f"Result structure: {list(result.keys())}")
                    
                    if "attributes" in result:
                        attrs = result.get("attributes", {})
                        logger.info(f"Token: {attrs.get('name', 'Unknown')} ({attrs.get('symbol', 'Unknown')})")
                        success_count += 1
                    elif "id" in result and "type" in result:
                        logger.info(f"Token ID: {result.get('id')}, Type: {result.get('type')}")
                        success_count += 1
                    else:
                        logger.warning(f"Unexpected result format: {list(result.keys())}")
                        failure_count += 1
                else:
                    logger.error(f"Invalid result type: {type(result)}")
                    failure_count += 1
                    
            except RecursionError as r:
                logger.critical(f"RecursionError: {r}")
                logger.critical(f"Maximum recursion depth exceeded when testing {token_address}")
                failure_count += 1
                # Print debugging info to help diagnose
                if debug_mode:
                    # Check the network determination logic
                    network = "solana" if len(token_address) in [43, 44] else "ethereum"
                    logger.critical(f"Address: {token_address}, Length: {len(token_address)}, Network: {network}")
                    logger.critical(f"URL: https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{token_address}")
                
            except Exception as e:
                logger.error(f"Exception testing {token_address}: {e}")
                logger.debug(traceback.format_exc())
                failure_count += 1
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info(f"Test Results: {success_count} Successful, {failure_count} Failed")
        logger.info("="*60)
        
        return 0 if failure_count == 0 else 1
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        logger.debug(traceback.format_exc())
        return 1

def main():
    """Parse arguments and run the test."""
    parser = argparse.ArgumentParser(description="Test Dragon GMGN_Client token info functionality")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    return run_gmgn_client_test(debug_mode=args.debug)

if __name__ == "__main__":
    sys.exit(main()) 