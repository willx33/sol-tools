"""
GMGN module for Solana token market cap and token data
"""

# Export public functions and classes from the GMGN module

# Export market cap functionality
from .standalone_mcap import (
    standalone_fetch_token_mcaps,
    standalone_test as market_cap_test
)

# Export the token data implementation
from .standalone_token_data import (
    standalone_fetch_token_data,
    standalone_test as token_data_test
)

# Export the handlers
from .handlers import fetch_mcap_data_handler, fetch_token_data_handler

# For backwards compatibility with gmgn_adapter
from .gmgn_adapter import fetch_token_mcaps_async, fetch_multiple_token_mcaps_async

__all__ = [
    # Market Cap
    'standalone_fetch_token_mcaps',
    'fetch_token_mcaps_async',
    'fetch_multiple_token_mcaps_async',
    'market_cap_test',
    
    # Token Data
    'standalone_fetch_token_data',
    'token_data_test',
    
    # Handlers
    'fetch_mcap_data_handler',
    'fetch_token_data_handler'
]