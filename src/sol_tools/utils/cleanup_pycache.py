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
    
    # Verify .env has PYTHONPYCACHEPREFIX set
    env_file = root_dir / ".env"
    if not env_file.exists():
        print("Warning: .env file not found.")
        return
        
    with open(env_file, "r") as f:
        content = f.read()
        
    if "PYTHONPYCACHEPREFIX" not in content:
        print("Warning: PYTHONPYCACHEPREFIX not in .env file.")
        print("Please add the following line to your .env file:")
        print("PYTHONPYCACHEPREFIX=./data/__pycache__")
    else:
        print("PYTHONPYCACHEPREFIX already set in .env file.")
        
    print("\nInstructions:")
    print("1. When running your code, make sure to load the .env file to set PYTHONPYCACHEPREFIX")
    print("2. Alternatively, you can set this environment variable before running your scripts:")
    print("   export PYTHONPYCACHEPREFIX=./data/__pycache__")
    
if __name__ == "__main__":
    main()