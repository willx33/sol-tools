#!/usr/bin/env python3
"""
Check if the Dragon module can be imported and verify its components.
"""

import os
import sys
import importlib
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dragon_checker")

def check_dragon_import():
    """Attempt to import the Dragon module and verify its components."""
    
    logger.info("Checking Python search path...")
    for i, path in enumerate(sys.path):
        logger.info(f"Path {i}: {path}")
    
    # Try to find any Dragon module in the environment
    logger.info("\nSearching for Dragon module...")
    try:
        # First try to directly import
        logger.info("Attempting direct import of Dragon module...")
        try:
            import Dragon
            logger.info(f"✅ Dragon module found at: {Dragon.__file__}")
            
            # Check if key components exist
            components = [
                "utils", "BundleFinder", "ScanAllTx", "BulkWalletChecker", 
                "TopTraders", "TimestampTransactions", "purgeFiles", 
                "CopyTradeWalletFinder", "TopHolders", "EarlyBuyers", 
                "checkProxyFile", "EthBulkWalletChecker", "EthTopTraders",
                "EthTimestampTransactions", "EthScanAllTx", "GMGN"
            ]
            
            logger.info("\nChecking for Dragon components:")
            for component in components:
                if hasattr(Dragon, component):
                    logger.info(f"✅ Component found: Dragon.{component}")
                else:
                    logger.info(f"❌ Component missing: Dragon.{component}")
            
        except ImportError as e:
            logger.warning(f"❌ Direct import failed: {e}")
            
            # Try searching for the module in potential locations
            logger.info("\nSearching for potential Dragon module locations...")
            
            # Add current directory to path
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.append(cwd)
                logger.info(f"Added current directory to path: {cwd}")
            
            # Add parent directory to path
            parent_dir = str(Path(cwd).parent)
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)
                logger.info(f"Added parent directory to path: {parent_dir}")
            
            # Try searching subdirectories
            potential_locations = []
            for root, dirs, files in os.walk(cwd):
                if "__init__.py" in files and "dragon" in root.lower():
                    potential_locations.append(root)
            
            if potential_locations:
                logger.info(f"Found {len(potential_locations)} potential locations:")
                for loc in potential_locations:
                    logger.info(f"  - {loc}")
            else:
                logger.info("No potential Dragon module locations found in subdirectories")
            
    except Exception as e:
        logger.error(f"Error during Dragon module check: {e}")

if __name__ == "__main__":
    logger.info("Dragon Module Import Checker")
    logger.info("--------------------------")
    check_dragon_import() 