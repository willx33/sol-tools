#!/usr/bin/env python3
"""
Script to clean up cache and __pycache__ directories.
"""

import os
import sys
import shutil
from pathlib import Path


def clean_caches():
    """Clean up cache and __pycache__ directories."""
    root_dir = Path(__file__).parents[3]  # Get project root
    data_dir = root_dir / "data"
    
    # Clean main cache directory
    cache_dir = data_dir / "cache"
    pycache_dir = data_dir / "__pycache__"
    
    success = True
    
    # Clear cache directory if it exists
    if cache_dir.exists():
        try:
            for item in cache_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            print(f"✅ Successfully cleared cache directory: {cache_dir}")
        except Exception as e:
            print(f"❌ Error clearing cache directory: {e}")
            success = False
    else:
        print(f"⚠️ Cache directory does not exist: {cache_dir}")
    
    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear __pycache__ directory if it exists
    if pycache_dir.exists():
        try:
            shutil.rmtree(pycache_dir)
            pycache_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Successfully cleared __pycache__ directory: {pycache_dir}")
        except Exception as e:
            print(f"❌ Error clearing __pycache__ directory: {e}")
            success = False
    else:
        print(f"⚠️ __pycache__ directory does not exist: {pycache_dir}")
        pycache_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear any __pycache__ directories in the project
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        path = Path(dirpath)
        
        # Skip venv directory
        if "venv" in path.parts:
            continue
            
        # Skip the new central __pycache__ directory
        if str(path) == str(pycache_dir):
            continue
            
        if "__pycache__" in dirnames:
            pycache_dir_to_remove = path / "__pycache__"
            try:
                shutil.rmtree(pycache_dir_to_remove)
                count += 1
            except Exception as e:
                print(f"❌ Error removing {pycache_dir_to_remove}: {e}")
                success = False
    
    if count > 0:
        print(f"✅ Removed {count} additional __pycache__ directories")
    
    return success


if __name__ == "__main__":
    success = clean_caches()
    print("🧹 Cleanup complete.")
    sys.exit(0 if success else 1)