"""Type stubs for the base_adapter module."""

from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path

class OperationError(Exception): ...
class ConfigError(Exception): ...
class ResourceNotFoundError(Exception): ...

class BaseAdapter:
    """Base class for all adapters in the Sol Tools framework."""
    
    # Constants for state management
    STATE_UNINITIALIZED: str
    STATE_INITIALIZING: str
    STATE_READY: str
    STATE_ERROR: str
    STATE_CLEANING_UP: str
    STATE_CLEANED_UP: str
    
    # Instance variables
    test_mode: bool
    data_dir: Path
    config_override: Dict[str, Any]
    state: str
    error: Optional[Exception]
    logger: Any
    
    def __init__(
        self,
        test_mode: bool = False,
        data_dir: Optional[Path] = None,
        config_override: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ) -> None: ...
    
    def set_state(self, state: str, error: Optional[Exception] = None) -> None: ...
    
    def get_state(self) -> str: ...
    
    def is_ready(self) -> bool: ...
    
    def has_error(self) -> bool: ...
    
    def get_error(self) -> Optional[Exception]: ...
    
    def get_module_config(self) -> Dict[str, Any]: ...
    
    def get_module_data_dir(self, subdir: str = "") -> Path: ...
    
    async def initialize(self) -> bool: ...
    
    async def validate(self) -> bool: ...
    
    async def cleanup(self) -> None: ... 