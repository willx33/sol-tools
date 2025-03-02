"""Dragon module for Solana, Ethereum, and GMGN analytics."""

# Add src to Python path to ensure Dragon is found
import sys
import os
from pathlib import Path

# Add parent directories to sys.path
current_dir = Path(__file__).resolve().parent
module_dir = current_dir.parent.parent  # sol_tools
src_dir = module_dir.parent  # src
root_dir = src_dir.parent   # project root
dragon_dir = src_dir / "Dragon"

# Add paths to sys.path if they exist and aren't already there
for path in [str(src_dir), str(root_dir), str(dragon_dir)]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# Make the adapter available for import directly from the module
from .dragon_adapter import DragonAdapter, GMGN_Client

# Flag to indicate if real Dragon package is available 
from typing import TYPE_CHECKING

# At runtime, check if Dragon is available
try:
    import Dragon
    DRAGON_AVAILABLE = True
except ImportError:
    DRAGON_AVAILABLE = False

# Define what symbols should be exported
__all__ = ['DragonAdapter', 'DRAGON_AVAILABLE', 'GMGN_Client']