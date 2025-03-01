#!/usr/bin/env python3
"""
Simple test script for ensuring directories exist before file operations.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(msg, color=None):
    """Print colored text to console."""
    if color and hasattr(Colors, color.upper()):
        color_code = getattr(Colors, color.upper())
        print(f"{color_code}{msg}{Colors.END}")
    else:
        print(msg)

def ensure_file_dir(file_path):
    """
    Ensure that the parent directory of a file exists.
    Creates all parent directories if they don't exist.
    
    Args:
        file_path: Path to the file (can be either a string or Path object)
        
    Returns:
        Path object to the file's parent directory
    """
    path = Path(file_path)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def run_tests():
    """Run all tests for directory creation functionality."""
    print_colored("\n🧪 Testing directory creation functionality...\n", "cyan")
    
    # Use a temporary directory for testing
    test_dir = Path(tempfile.mkdtemp(prefix="dir_test_"))
    print(f"Running tests in: {test_dir}")
    
    try:
        # Test 1: Basic directory creation
        print_colored("\nTest 1: Basic directory creation", "cyan")
        file_path = test_dir / "basic" / "test.txt"
        ensure_file_dir(file_path)
        
        if file_path.parent.exists():
            print_colored(f"✓ Created directory: {file_path.parent}", "green")
        else:
            print_colored(f"✗ Failed to create directory: {file_path.parent}", "red")
            return False
            
        # Test 2: Deep nested directory
        print_colored("\nTest 2: Deep nested directory", "cyan")
        deep_path = test_dir / "a" / "b" / "c" / "d" / "e" / "f" / "deep.txt"
        ensure_file_dir(deep_path)
        
        if deep_path.parent.exists():
            print_colored(f"✓ Created nested directories: {deep_path.parent}", "green")
        else:
            print_colored(f"✗ Failed to create deep directories: {deep_path.parent}", "red")
            return False
            
        # Test 3: Actually write to a file
        print_colored("\nTest 3: Writing to a file in a non-existent directory", "cyan")
        json_file = test_dir / "data" / "config" / "settings.json"
        ensure_file_dir(json_file)
        
        # Write some data
        data = {"test": True, "value": 42}
        with open(json_file, "w") as f:
            json.dump(data, f)
            
        if json_file.exists():
            print_colored(f"✓ Created and wrote to file: {json_file}", "green")
        else:
            print_colored(f"✗ Failed to create and write to file: {json_file}", "red")
            return False
            
        print_colored("\n✓ All tests passed! Directory creation is working correctly.", "green")
        return True
        
    finally:
        # Clean up the test directory
        shutil.rmtree(test_dir)
        
if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)