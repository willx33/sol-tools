"""Dragon module for Solana, Ethereum, and GMGN analytics."""

# Make the adapter available for import directly from the module
from .dragon_adapter import DragonAdapter

# Flag to indicate if real Dragon package is available 
import sys
from typing import TYPE_CHECKING

# At runtime, check if Dragon is available
try:
    import Dragon
    DRAGON_AVAILABLE = True
except ImportError:
    DRAGON_AVAILABLE = False