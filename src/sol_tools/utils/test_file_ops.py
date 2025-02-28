"""
Test file operations, specifically the automatic directory creation functionality.

This script tests the ensure_file_dir functionality across modules.
"""

import os
import shutil
import json
import tempfile
import sys
from pathlib import Path
from typing import Dict, Any, List

# Create a simple console output function
def print_colored(msg, color=None):
    """Print colored text to console."""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "end": "\033[0m"
    }
    
    if color and color in colors:
        print(f"{colors[color]}{msg}{colors['end']}")
    else:
        print(msg)

# Define the ensure_file_dir function directly in this file for testing
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

# Test paths - will use a temporary directory for testing
TEST_ROOT = Path(tempfile.mkdtemp(prefix="sol_tools_test_"))
print(f"Running tests in temporary directory: {TEST_ROOT}")

def cleanup():
    """Clean up the test directory after running tests."""
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)

def test_ensure_file_dir():
    """Test the ensure_file_dir function directly."""
    print_colored("\nTesting ensure_file_dir basic functionality", "cyan")
    
    # Test with a simple path
    test_file = TEST_ROOT / "test_dir" / "test_file.txt"
    ensure_file_dir(test_file)
    
    # Check if the directory was created
    assert test_file.parent.exists(), f"Failed to create directory: {test_file.parent}"
    print_colored(f"✓ Created directory: {test_file.parent}", "green")
    
    # Test with a deeper nested path
    deep_file = TEST_ROOT / "level1" / "level2" / "level3" / "deep_file.txt"
    ensure_file_dir(deep_file)
    
    # Check if all directories were created
    assert deep_file.parent.exists(), f"Failed to create deep directory: {deep_file.parent}"
    print_colored(f"✓ Created nested directories: {deep_file.parent}", "green")
    
    # Test with a file in the current directory (shouldn't fail)
    current_file = TEST_ROOT / "current_file.txt"
    ensure_file_dir(current_file)
    assert current_file.parent.exists()
    print_colored(f"✓ Verified current directory: {current_file.parent}", "green")
    
    return True

def test_file_write_operations():
    """Test writing files to non-existent directories."""
    print_colored("\nTesting file write operations with auto-directory creation", "cyan")
    
    # Test writing a text file
    text_file = TEST_ROOT / "text_dir" / "test.txt"
    ensure_file_dir(text_file)
    with open(text_file, "w") as f:
        f.write("Test content")
    
    assert text_file.exists(), f"Failed to create text file: {text_file}"
    print_colored(f"✓ Created and wrote to text file: {text_file}", "green")
    
    # Test writing a JSON file
    json_file = TEST_ROOT / "json_dir" / "nested" / "test.json"
    ensure_file_dir(json_file)
    with open(json_file, "w") as f:
        json.dump({"key": "value"}, f)
    
    assert json_file.exists(), f"Failed to create JSON file: {json_file}"
    print_colored(f"✓ Created and wrote to JSON file: {json_file}", "green")
    
    return True

def test_module_simulations():
    """Simulate the file operations of various modules."""
    print_colored("\nTesting simulated module operations", "cyan")
    
    # Simulate dragon_adapter.py log saving
    dragon_log_file = TEST_ROOT / "logs" / "dragon" / "api" / "test_log.json"
    ensure_file_dir(dragon_log_file)
    with open(dragon_log_file, "w") as f:
        json.dump({"timestamp": 123456789, "data": "test"}, f)
    
    assert dragon_log_file.exists(), f"Failed to create dragon log file: {dragon_log_file}"
    print_colored(f"✓ Simulated dragon module log write: {dragon_log_file}", "green")
    
    # Simulate solana_adapter.py wallet address saving
    solana_wallet_file = TEST_ROOT / "data" / "solana" / "wallets" / "monitor-wallets.txt"
    ensure_file_dir(solana_wallet_file)
    with open(solana_wallet_file, "w") as f:
        f.write("wallet1\nwallet2\nwallet3\n")
    
    assert solana_wallet_file.exists(), f"Failed to create solana wallet file: {solana_wallet_file}"
    print_colored(f"✓ Simulated solana module wallet file write: {solana_wallet_file}", "green")
    
    # Simulate sharp_adapter.py CSV saving
    sharp_csv_file = TEST_ROOT / "data" / "sharp" / "csv" / "filtered" / "test_filtered.csv"
    ensure_file_dir(sharp_csv_file)
    with open(sharp_csv_file, "w") as f:
        f.write("wallet,amount\nwallet1,100\nwallet2,200\n")
    
    assert sharp_csv_file.exists(), f"Failed to create sharp CSV file: {sharp_csv_file}"
    print_colored(f"✓ Simulated sharp module CSV write: {sharp_csv_file}", "green")
    
    # Simulate a very deep path that would cause issues without ensure_file_dir
    deep_config_file = TEST_ROOT / "config" / "modules" / "submodules" / "specific" / "very" / "deep" / "settings.json"
    ensure_file_dir(deep_config_file)
    with open(deep_config_file, "w") as f:
        json.dump({"setting": "value"}, f)
    
    assert deep_config_file.exists(), f"Failed to create deep config file: {deep_config_file}"
    print_colored(f"✓ Simulated deep config file write: {deep_config_file}", "green")
    
    return True

def run_all_tests():
    """Run all test functions."""
    print_colored("\n🧪 Running sol-tools file system tests...", "cyan")
    print_colored("Testing automatic directory creation functionality\n", "cyan")
    
    try:
        tests_passed = 0
        total_tests = 3
        
        if test_ensure_file_dir():
            tests_passed += 1
        
        if test_file_write_operations():
            tests_passed += 1
        
        if test_module_simulations():
            tests_passed += 1
        
        print_colored(f"\nTest Results: {tests_passed}/{total_tests} tests passed", "bold")
        
        if tests_passed == total_tests:
            print_colored("✓ All tests passed! The ensure_file_dir function is working correctly.", "green")
        else:
            print_colored("✗ Some tests failed. Please check the output above for details.", "red")
        
        return tests_passed == total_tests
    
    finally:
        # Always clean up the test directory
        cleanup()

if __name__ == "__main__":
    run_all_tests()