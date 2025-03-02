#!/usr/bin/env python3
"""
Test script to directly test the GMGN_Client market cap functionality.

This script isolates the market cap functionality to identify issues
with maximum recursion depth that were previously occurring.
"""

import sys
import time
import logging
import argparse
import traceback
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gmgn_market_cap_test")

# Test token addresses (guaranteed to work)
TEST_TOKENS = [
    "So11111111111111111111111111111111111111112",  # SOL token (native)
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK token
]

def run_market_cap_test(debug_mode: bool = False) -> int:
    """
    Test the GMGN_Client market cap functionality.
    
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
        
        # Test each function that could potentially cause recursion issues
        success_count = 0
        failure_count = 0
        
        # Test new tokens function
        try:
            logger.info("\nTesting getNewTokens()...")
            tokens = client.getNewTokens()
            
            if isinstance(tokens, list):
                logger.info(f"Successfully fetched {len(tokens)} new tokens")
                if tokens:
                    sample = tokens[:3] if len(tokens) >= 3 else tokens
                    logger.info(f"Sample tokens: {sample}")
                success_count += 1
            else:
                logger.error(f"Invalid result type for getNewTokens: {type(tokens)}")
                failure_count += 1
        except Exception as e:
            logger.error(f"Error testing getNewTokens: {e}")
            logger.debug(traceback.format_exc())
            failure_count += 1
        
        # Test completing tokens function
        try:
            logger.info("\nTesting getCompletingTokens()...")
            tokens = client.getCompletingTokens()
            
            if isinstance(tokens, list):
                logger.info(f"Successfully fetched {len(tokens)} completing tokens")
                if tokens:
                    sample = tokens[:3] if len(tokens) >= 3 else tokens
                    logger.info(f"Sample tokens: {sample}")
                success_count += 1
            else:
                logger.error(f"Invalid result type for getCompletingTokens: {type(tokens)}")
                failure_count += 1
        except Exception as e:
            logger.error(f"Error testing getCompletingTokens: {e}")
            logger.debug(traceback.format_exc())
            failure_count += 1
        
        # Test soaring tokens function
        try:
            logger.info("\nTesting getSoaringTokens()...")
            tokens = client.getSoaringTokens()
            
            if isinstance(tokens, list):
                logger.info(f"Successfully fetched {len(tokens)} soaring tokens")
                if tokens:
                    sample = tokens[:3] if len(tokens) >= 3 else tokens
                    logger.info(f"Sample tokens: {sample}")
                success_count += 1
            else:
                logger.error(f"Invalid result type for getSoaringTokens: {type(tokens)}")
                failure_count += 1
        except Exception as e:
            logger.error(f"Error testing getSoaringTokens: {e}")
            logger.debug(traceback.format_exc())
            failure_count += 1
        
        # Test bonded tokens function
        try:
            logger.info("\nTesting getBondedTokens()...")
            tokens = client.getBondedTokens()
            
            if isinstance(tokens, list):
                logger.info(f"Successfully fetched {len(tokens)} bonded tokens")
                if tokens:
                    sample = tokens[:3] if len(tokens) >= 3 else tokens
                    logger.info(f"Sample tokens: {sample}")
                success_count += 1
            else:
                logger.error(f"Invalid result type for getBondedTokens: {type(tokens)}")
                failure_count += 1
        except Exception as e:
            logger.error(f"Error testing getBondedTokens: {e}")
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
    parser = argparse.ArgumentParser(description="Test GMGN_Client market cap functionality")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    return run_market_cap_test(debug_mode=args.debug)

if __name__ == "__main__":
    sys.exit(main()) 