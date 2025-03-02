"""
Real test data for Sol Tools.

This module provides constants with real addresses and data for testing.
All tests run against real data with no mocks.
"""

# Real token addresses for testing
REAL_TOKEN_ADDRESSES = [
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "63LfDmNb3MQ8mw9MtZ2To9bEA2M71kZUUGq5tiJxcqj9",  # Second token address
]

# Real wallet addresses for testing
REAL_WALLET_ADDRESSES = [
    "DfMxre4cKmvogbLrPigxmibVTTQDuzjdXojWzjCXXhzj",  # First wallet
    "4hSXPtxZgXFpo6Vxq9yqxNjcBoqWN3VoaPJWonUtupzD",  # Second wallet
]

# Real addresses by network
SOLANA_ADDRESSES = {
    "tokens": REAL_TOKEN_ADDRESSES,
    "wallets": REAL_WALLET_ADDRESSES,
}

# Real Ethereum addresses for testing
REAL_ETH_ADDRESSES = {
    "tokens": [
        "0x6b175474e89094c44da98b954eedeac495271d0f",  # DAI
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
    ],
    "wallets": [
        "0xF977814e90dA44bFA03b6295A0616a897441aceC",  # Binance wallet
        "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance wallet 2
    ]
}

# Real test data for Sharp portfolio analysis
REAL_SHARP_PORTFOLIO = {
    "name": "Test Portfolio",
    "wallets": REAL_ETH_ADDRESSES["wallets"],
    "date_created": "2023-12-01T00:00:00Z",
    "tokens": [
        {
            "symbol": "DAI",
            "address": REAL_ETH_ADDRESSES["tokens"][0],
            "name": "Dai Stablecoin",
            "decimals": 18,
            "balance": 1000.0
        },
        {
            "symbol": "USDC",
            "address": REAL_ETH_ADDRESSES["tokens"][1],
            "name": "USD Coin",
            "decimals": 6,
            "balance": 500.0
        }
    ]
}

# Real test data for Dune Analytics
REAL_DUNE_QUERY_RESULT = {
    "query_id": 1234567,
    "name": "Test Query",
    "description": "Sample query result for testing",
    "parameters": {},
    "results": {
        "rows": [
            {"wallet": REAL_ETH_ADDRESSES["wallets"][0], "token": "DAI", "balance": 1000.0},
            {"wallet": REAL_ETH_ADDRESSES["wallets"][1], "token": "USDC", "balance": 500.0}
        ],
        "metadata": {
            "column_names": ["wallet", "token", "balance"],
            "column_types": ["string", "string", "number"]
        }
    }
}

# Test configuration - only real data
TEST_CONFIG = {
    "use_real_data": True,
    "discard_results": True,
    "log_responses": False,
} 