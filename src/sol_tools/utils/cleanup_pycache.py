#!/usr/bin/env python3
"""
Script to clean up __pycache__ directories and centralize them in data/__pycache__.
"""

import os
import shutil
from pathlib import Path
import sys

def main():
    """Clean up all __pycache__ directories and ensure PYTHONPYCACHEPREFIX is set."""
    root_dir = Path(__file__).parents[3]  # Get project root
    
    # Ensure data/__pycache__ exists
    data_pycache = root_dir / "data" / "__pycache__"
    data_pycache.mkdir(parents=True, exist_ok=True)
    
    print(f"Created central __pycache__ directory at: {data_pycache}")
    
    # Count and delete existing __pycache__ directories
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        path = Path(dirpath)
        
        # Skip venv directory
        if "venv" in path.parts:
            continue
            
        # Skip the new central __pycache__ directory
        if str(path) == str(data_pycache):
            continue
            
        if "__pycache__" in dirnames:
            pycache_dir = path / "__pycache__"
            print(f"Removing: {pycache_dir}")
            shutil.rmtree(pycache_dir)
            count += 1
    
    print(f"Removed {count} __pycache__ directories.")
    
    # No need to check .env file anymore as PYTHONPYCACHEPREFIX is set programmatically
    print("\nInformation:")
    print("The PYTHONPYCACHEPREFIX is now set programmatically in cli.py when the application starts.")
    print("The central __pycache__ directory will be used regardless of .env configuration.")
    
if __name__ == "__main__":
    main()