"""Type stubs for the Dragon package."""

from typing import Dict, List, Any, Optional, Union, Callable

# Import from the stub files
from sol_tools.modules.dragon.dragon_adapter import DragonAdapter

# Utility functions
def utils() -> Any: ...
def purgeFiles() -> Any: ...
def checkProxyFile() -> Any: ...

# Component classes
class BaseDragonComponent:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def run(self, *args: Any, **kwargs: Any) -> Any: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

class BundleFinder(BaseDragonComponent): ...
class ScanAllTx(BaseDragonComponent): ...
class BulkWalletChecker(BaseDragonComponent): ...
class TopTraders(BaseDragonComponent): ...
class TimestampTransactions(BaseDragonComponent): ...
class CopyTradeWalletFinder(BaseDragonComponent): ...
class TopHolders(BaseDragonComponent): ...
class EarlyBuyers(BaseDragonComponent): ...
class EthBulkWalletChecker(BaseDragonComponent): ...
class EthTopTraders(BaseDragonComponent): ...
class EthTimestampTransactions(BaseDragonComponent): ...
class EthScanAllTx(BaseDragonComponent): ...
class GMGN(BaseDragonComponent): ...

__all__ = [
    "utils", "BundleFinder", "ScanAllTx", "BulkWalletChecker", "TopTraders",
    "TimestampTransactions", "purgeFiles", "CopyTradeWalletFinder", "TopHolders",
    "EarlyBuyers", "checkProxyFile", "EthBulkWalletChecker", "EthTopTraders",
    "EthTimestampTransactions", "EthScanAllTx", "GMGN"
] 