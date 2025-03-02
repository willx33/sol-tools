"""Type stubs for the Dragon package."""

from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Tuple, cast

# Utility functions
def utils(**kwargs) -> Dict[str, Any]: ...
def purgeFiles(*args, **kwargs) -> bool: ...
def checkProxyFile(*args, **kwargs) -> bool: ...

# Component classes
class BaseDragonComponent:
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...
    def __call__(self, *args, **kwargs) -> Dict[str, Any]: ...

class BundleFinder(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...
    @staticmethod
    def teamTrades(address: str) -> List[str]: ...
    @staticmethod
    def checkBundle(tx1: str, tx2: str) -> Dict[str, Any]: ...
    @staticmethod
    def prettyPrint(data: Dict[str, Any], address: str) -> str: ...

class ScanAllTx(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class BulkWalletChecker(BaseDragonComponent):
    def __init__(self, wallets: Optional[List[str]] = None, skip_wallets: bool = False, 
                 output_dir: str = "", proxies: bool = False, threads: int = 10, **kwargs): ...
    def run(self) -> Tuple[int, List[str]]: ...

class TopTraders(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class TimestampTransactions(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class CopyTradeWalletFinder(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class TopHolders(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class EarlyBuyers(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class EthBulkWalletChecker(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class EthTopTraders(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class EthTimestampTransactions(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class EthScanAllTx(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

class GMGN(BaseDragonComponent):
    def __init__(self, *args, **kwargs): ...
    def run(self, *args, **kwargs) -> Dict[str, Any]: ...

# Export all these symbols
__all__ = [
    'utils', 'BundleFinder', 'ScanAllTx', 'BulkWalletChecker', 'TopTraders',
    'TimestampTransactions', 'purgeFiles', 'CopyTradeWalletFinder', 'TopHolders',
    'EarlyBuyers', 'checkProxyFile', 'EthBulkWalletChecker', 'EthTopTraders',
    'EthTimestampTransactions', 'EthScanAllTx', 'GMGN'
] 