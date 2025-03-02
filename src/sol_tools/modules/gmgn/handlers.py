"""
CLI command handlers for the GMGN module
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Import directly from the standalone implementations
from .standalone_mcap import standalone_fetch_token_mcaps, standalone_test as mcap_standalone_test

# Import the token data implementation
from .standalone_token_data import standalone_fetch_token_data, standalone_test as token_data_standalone_test

logger = logging.getLogger(__name__)

# Use the v3 implementation to avoid issues
async def fetch_mcap_data_handler():
    """Handler for fetching market cap data from GMGN"""
    print("\n==== GMGN Market Cap Data Fetcher ====")
    print("This tool fetches historical market cap data for Solana tokens.")
    print("You can enter multiple token addresses separated by commas or spaces.")
    print("For the time frame, you can use formats like '30d' for 30 days, '7d' for 7 days, or a specific date 'YYYY-MM-DD'.")
    # Simply delegate to our v3 implementation's test function
    await mcap_standalone_test()

# Export the v3 fetch function for backward compatibility
fetch_token_mcaps_async = standalone_fetch_token_mcaps

# Add the new handler for token data
async def fetch_token_data_handler():
    """Handler for fetching token data from GMGN"""
    # The token data module already has its own header and instructions
    # Simply delegate to our token data implementation's test function
    await token_data_standalone_test()