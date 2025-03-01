"""Type stubs for the SolanaAdapter class."""

from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Tuple
from pathlib import Path

from sol_tools.core.base_adapter import BaseAdapter

class SolanaAdapter(BaseAdapter):
    helius_api_key: Optional[str]
    telegram_bot_token: Optional[str]
    telegram_chat_id: Union[int, str, None]
    input_dir: Path
    output_dir: Path
    cache_dir: Path
    _dragon_available: bool
    dragon: Any
    telegram_client: Any
    http_client: Any
    db_connection: Any
    monitoring_tasks: List[Any]
    cache: Dict[str, Any]
    open_files: List[Any]
    max_connections: int
    default_channel: str
    
    def __init__(
        self,
        test_mode: bool = ...,
        data_dir: Optional[Path] = ...,
        config_override: Optional[Dict[str, Any]] = ...,
        verbose: bool = ...
    ) -> None: ...
    
    def _init_dragon(self) -> bool: ...
    
    def _init_telegram(self) -> bool: ...
    
    def _init_websocket(self) -> bool: ...
    
    async def send_telegram(self, message: str) -> bool: ...
    
    def test_telegram(self) -> Dict[str, Any]: ...
    
    def token_monitor(self, token_address: str, min_amount: float = ...) -> Dict[str, Any]: ...
    
    def wallet_monitor(self, wallet_addresses: List[str]) -> Dict[str, Any]: ...
    
    def telegram_scraper(self, 
                    channel: str, 
                    limit: int = ..., 
                    filter_type: str = ..., 
                    export_csv: bool = ...) -> Dict[str, Any]: ...
    
    def _validate_solana_address(self, address: str) -> bool: ...
    
    def check_dragon_availability(self) -> bool: ...
    
    def solana_bundle_checker(self, contract_address: Union[str, List[str]]) -> Dict[str, Any]: ...
    
    def solana_wallet_checker(self, 
                          wallets: Union[str, List[str]], 
                          threads: Optional[int] = ...,
                          skip_wallets: bool = ..., 
                          use_proxies: bool = ...) -> Dict[str, Any]: ...
    
    def setup_wallet_monitor(self, 
                            wallet_address: str, 
                            token_filter: Optional[List[str]] = ..., 
                            test_mode: bool = ...) -> Dict[str, Any]: ...
    
    def _fetch_wallet_data(self, wallet_address: str) -> Dict[str, Any]: ...
    
    def get_token_data(self, token_symbol: str) -> Dict[str, Any]: ...
    
    async def initialize(self) -> bool: ...
    
    async def validate(self) -> bool: ...
    
    async def cleanup(self) -> None: ... 