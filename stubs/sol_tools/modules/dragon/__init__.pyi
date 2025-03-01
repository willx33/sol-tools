"""Type stubs for the dragon module."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, Callable

# Flag to indicate if Dragon is available
DRAGON_AVAILABLE: bool

# Import from dragon_adapter
from sol_tools.modules.dragon.dragon_adapter import DragonAdapter

__all__ = ["DragonAdapter", "DRAGON_AVAILABLE"] 