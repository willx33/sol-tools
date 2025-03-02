"""
Mock implementations of Dragon module for development and testing.

This module provides stub implementations of Dragon classes and functions used in dragon_adapter.py,
allowing the code to be linted correctly and to function without the actual Dragon package.
"""

import logging
from typing import Dict, Any, List, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

# Utility functions
def utils(**kwargs):
    """Mock Dragon utility functions."""
    return {"success": False, "error": "Mock Dragon utils called", "mock": True}

def purgeFiles(*args, **kwargs):
    """Mock file purging function."""
    logger.debug("Mock Dragon purgeFiles called")
    return True

def checkProxyFile(*args, **kwargs):
    """Mock proxy file checking function."""
    logger.debug("Mock Dragon checkProxyFile called")
    return True

# Base mock class for Dragon components
class BaseMockComponent:
    """Base class for mock Dragon components."""
    
    def __init__(self, component_name, *args, **kwargs):
        """Initialize the mock component."""
        self.component_name = component_name
        self.args = args
        self.kwargs = kwargs
        
    def run(self, *args, **kwargs):
        """Mock run method."""
        return {
            "success": False,
            "error": f"Mock Dragon {self.component_name} not implemented",
            "mock": True
        }
        
    def __call__(self, *args, **kwargs):
        """Make component callable."""
        return self.run(*args, **kwargs)

# Specific components
class BundleFinder(BaseMockComponent):
    """Mock Dragon BundleFinder component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("BundleFinder", *args, **kwargs)

class ScanAllTx(BaseMockComponent):
    """Mock Dragon ScanAllTx component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("ScanAllTx", *args, **kwargs)

class BulkWalletChecker(BaseMockComponent):
    """Mock Dragon BulkWalletChecker component."""
    
    def __init__(self, wallets=None, *args, **kwargs):
        super().__init__("BulkWalletChecker", *args, **kwargs)
        self.wallets = wallets or []
        
    def run(self):
        """Mock run method with wallet-specific response."""
        return {
            "success": False,
            "error": "Mock Dragon BulkWalletChecker not implemented",
            "mock": True,
            "wallets_count": len(self.wallets) if isinstance(self.wallets, list) else 1
        }

class TopTraders(BaseMockComponent):
    """Mock Dragon TopTraders component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("TopTraders", *args, **kwargs)

class TimestampTransactions(BaseMockComponent):
    """Mock Dragon TimestampTransactions component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("TimestampTransactions", *args, **kwargs)

class CopyTradeWalletFinder(BaseMockComponent):
    """Mock Dragon CopyTradeWalletFinder component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("CopyTradeWalletFinder", *args, **kwargs)

class TopHolders(BaseMockComponent):
    """Mock Dragon TopHolders component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("TopHolders", *args, **kwargs)

class EarlyBuyers(BaseMockComponent):
    """Mock Dragon EarlyBuyers component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("EarlyBuyers", *args, **kwargs)

class EthBulkWalletChecker(BaseMockComponent):
    """Mock Dragon EthBulkWalletChecker component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("EthBulkWalletChecker", *args, **kwargs)

class EthTopTraders(BaseMockComponent):
    """Mock Dragon EthTopTraders component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("EthTopTraders", *args, **kwargs)

class EthTimestampTransactions(BaseMockComponent):
    """Mock Dragon EthTimestampTransactions component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("EthTimestampTransactions", *args, **kwargs)

class EthScanAllTx(BaseMockComponent):
    """Mock Dragon EthScanAllTx component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("EthScanAllTx", *args, **kwargs)

class GMGN(BaseMockComponent):
    """Mock Dragon GMGN component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("GMGN", *args, **kwargs)
        
    def getTokenInfo(self, token_address):
        """Mock implementation of getTokenInfo that mimics GeckoTerminal API response."""
        logger.debug(f"Mock Dragon GMGN.getTokenInfo called for {token_address}")
        
        # Return mock token data in GeckoTerminal format
        return {
            "id": f"token-{token_address}",
            "type": "token",
            "attributes": {
                "name": "Mock Token",
                "symbol": "MOCK",
                "address": token_address,
                "coingecko_coin_id": "mock-token",
                "decimals": 9,
                "total_supply": "1000000000000000",
                "price_usd": "0.12345678",
                "fdv_usd": "1000000",
                "total_reserve_in_usd": "500000", 
                "volume_usd": {
                    "h24": "250000"
                },
                "price_change_percentage": {
                    "h24": "5.25"
                }
            },
            "relationships": {
                "top_pools": {
                    "data": [
                        {
                            "id": "pool-mock-1",
                            "type": "pool"
                        }
                    ]
                }
            }
        }
    
    def getNewTokens(self):
        """Mock implementation of getNewTokens."""
        logger.debug("Mock Dragon GMGN.getNewTokens called")
        return [
            {"name": "New Token 1", "symbol": "NEW1", "address": "MockAddr1", "price": 0.1},
            {"name": "New Token 2", "symbol": "NEW2", "address": "MockAddr2", "price": 0.2}
        ]
        
    def getCompletingTokens(self):
        """Mock implementation of getCompletingTokens."""
        logger.debug("Mock Dragon GMGN.getCompletingTokens called")
        return [
            {"name": "Completing Token 1", "symbol": "COMP1", "address": "MockAddr3", "price": 0.3},
            {"name": "Completing Token 2", "symbol": "COMP2", "address": "MockAddr4", "price": 0.4}
        ]
        
    def getSoaringTokens(self):
        """Mock implementation of getSoaringTokens."""
        logger.debug("Mock Dragon GMGN.getSoaringTokens called")
        return [
            {"name": "Soaring Token 1", "symbol": "SOAR1", "address": "MockAddr5", "price": 0.5},
            {"name": "Soaring Token 2", "symbol": "SOAR2", "address": "MockAddr6", "price": 0.6}
        ]
    
    def getBondedTokens(self):
        """Mock implementation of getBondedTokens."""
        logger.debug("Mock Dragon GMGN.getBondedTokens called")
        return [
            {"name": "Bonded Token 1", "symbol": "BOND1", "address": "MockAddr7", "price": 0.7},
            {"name": "Bonded Token 2", "symbol": "BOND2", "address": "MockAddr8", "price": 0.8}
        ] 