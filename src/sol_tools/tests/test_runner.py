"""
Sol Tools Test Runner

This module provides a comprehensive test execution experience with:
1. Tests grouped by module following the CLI menu structure
2. Clear status indicators (colored dots)
3. Proper environment variable checking
4. Detailed summary of test results

Usage:
    sol-tools --test [--module MODULE_NAME] [--debug]
"""

import os
import sys
import time
import asyncio
import argparse
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set, Mapping

# Define a local setup_logging function in case it's not available
def setup_logging(level="INFO"):
    """Set up logging with the specified level."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Color codes and status indicators
COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "blue": "\033[94m",
    "bold": "\033[1m",
    "end": "\033[0m"
}

# Test status indicators
STATUS_INDICATORS = {
    "passed": "🟢",  # Green dot
    "skipped": "🟡",  # Yellow dot
    "failed": "🔴",   # Red dot
    "running": "🔄"   # Running indicator
}

def cprint(message: str, color: Optional[str] = None) -> None:
    """Print colored text to the console."""
    if color and color in COLORS:
        print(f"{COLORS[color]}{message}{COLORS['end']}")
    else:
        print(message)

# Menu structure to organize tests
# Structure: {menu_section: {submenu: [module_name]}}
MENU_STRUCTURE = {
    "Solana Tools": {
        "Token Watcher": ["Solana"],
        "Wallet Watcher": ["Solana"],
        "TG Data Extractor": ["Telegram", "Solana"],
        "Bundle Tracker - Dragon": ["Dragon", "Solana"],
        "Wallet Profiler - Dragon": ["Dragon", "Solana"],
        "Top Trader Finder - Dragon": ["Dragon", "Solana"],
        "TX Scanner - Dragon": ["Dragon", "Solana"],
        "Copycat Finder - Dragon": ["Dragon", "Solana"],
        "Whale Tracker - Dragon": ["Dragon", "Solana"],
        "Early Investor Finder - Dragon": ["Dragon", "Solana"]
    },
    "Sharp Tools": {
        "Wallet Analyzer": ["Sharp"],
        "Address Splitter": ["Sharp"],
        "CSV Combiner": ["Sharp"],
        "Profit Filter": ["Sharp"]
    },
    "API Tools": {
        "Dune API Tools": ["Dune"],
        "GMGN Tools": ["GMGN"]
    },
    "Eth Tools": {
        "Wallet Profiler - Dragon": ["Dragon"],
        "Top Trader Finder - Dragon": ["Dragon"],
        "TX Scanner - Dragon": ["Dragon"],
        "Time-Based TX Finder - Dragon": ["Dragon"]
    }
}

# Module definitions organized according to the CLI menu structure
AVAILABLE_MODULES = {
    # Chain category
    "Solana": {
        "module_path": "src.sol_tools.tests.test_modules.test_solana",
        "run_func": "run_tests",
        "submodules": [],
        "category": "Solana Tools",
        "description": "Tests for Solana blockchain interaction",
        "required_env_vars": ["HELIUS_API_KEY"]
    },
    
    # Data category
    "GMGN": {
        "module_path": "src.sol_tools.tests.test_modules.test_gmgn",
        "run_func": "run_tests",
        "submodules": ["Token Data", "Market Cap Data"],
        "category": "API Tools",
        "submenu": "GMGN Tools",
        "description": "Tests for GMGN token data retrieval",
        "required_env_vars": []
    },
    "Dune": {
        "module_path": "src.sol_tools.tests.test_modules.test_dune",
        "run_func": "run_dune_tests",
        "submodules": [],
        "category": "API Tools",
        "submenu": "Dune API Tools",
        "description": "Tests for Dune Analytics integration",
        "required_env_vars": ["DUNE_API_KEY"]
    },
    
    # Integration category
    "Dragon": {
        "module_path": "src.sol_tools.tests.test_modules.test_dragon",
        "run_func": "run_dragon_tests",
        "submodules": [],
        "category": "Integration",
        "description": "Tests for Dragon module integration",
        "required_env_vars": []
    },
    
    # Web category
    "Sharp": {
        "module_path": "src.sol_tools.tests.test_modules.test_sharp",
        "run_func": "run_sharp_tests",
        "submodules": [],
        "category": "Sharp Tools",
        "description": "Tests for Sharp API integration",
        "required_env_vars": []
    },
    
    # Settings & Utilities
    "Telegram": {
        "module_path": "src.sol_tools.tests.test_modules.test_telegram",
        "run_func": "run_telegram_tests",
        "submodules": [],
        "category": "Settings",
        "description": "Tests for Telegram notification integration",
        "required_env_vars": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    }
}

def check_missing_env_vars(module_name: str) -> List[str]:
    """
    Check which required environment variables are missing for a module.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        List of missing environment variables
    """
    module_info = AVAILABLE_MODULES.get(module_name, {})
    required_vars = module_info.get("required_env_vars", [])
    # Check both if the var is missing or if it's an empty string
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value is None or value.strip() == "":
            missing_vars.append(var)
    return missing_vars

async def run_module_tests(module_name: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run tests for a specific module.
    
    Args:
        module_name: Name of the module to test
        options: Optional parameters to pass to the test runner
        
    Returns:
        Dictionary with test results
    """
    if module_name not in AVAILABLE_MODULES:
        print(f"{STATUS_INDICATORS['failed']} Module '{module_name}' not found")
        return {"status": "failed", "error": f"Module '{module_name}' not found"}
    
    module_info = AVAILABLE_MODULES[module_name]
    result = {"status": "unknown", "missing_env_vars": [], "has_skips": False, "has_failures": False}
    
    # Check for missing environment variables
    missing_vars = check_missing_env_vars(module_name)
    result["missing_env_vars"] = missing_vars
    
    # If there are missing environment variables, skip the test
    # All modules with missing env vars should be skipped
    if missing_vars:
        print(f"{STATUS_INDICATORS['skipped']} Skipping {module_name} tests due to missing environment variables: {', '.join(missing_vars)}")
        return {
            "status": "skipped",
            "missing_env_vars": missing_vars,
            "has_skips": True,
            "has_failures": False
        }
    
    try:
        # Import the module
        test_module = importlib.import_module(module_info["module_path"])
        
        # Get the run function
        run_func_name = module_info["run_func"]
        run_func = getattr(test_module, run_func_name)
        
        # Run the tests
        print(f"\n{COLORS['bold']}Running tests for {module_name}{COLORS['end']}")
        
        if asyncio.iscoroutinefunction(run_func):
            exit_code = await run_func(options)
        else:
            exit_code = run_func(options)
        
        # In our convention:
        # - exit_code == 0: All tests passed
        # - exit_code == 1: Some tests failed
        # - exit_code == 2: All tests were skipped (no failures)
        
        has_failures = False
        has_skips = False
        
        if exit_code == 0:
            # All tests passed
            status = "passed"
        elif exit_code == 2:
            # All tests were skipped
            status = "skipped"
            has_skips = True
        else:
            # Some tests failed
            status = "failed"
            has_failures = True
            
        # Update result with status information
        result.update({
            "status": status, 
            "exit_code": exit_code,
            "has_failures": has_failures,
            "has_skips": has_skips
        })
        
        return result
        
    except ImportError as e:
        print(f"{STATUS_INDICATORS['failed']} Failed to import {module_name} test module: {str(e)}")
        return {
            "status": "failed", 
            "error": str(e), 
            "has_failures": True, 
            "has_skips": False,
            "missing_env_vars": missing_vars
        }
    except Exception as e:
        print(f"{STATUS_INDICATORS['failed']} Error running {module_name} tests: {str(e)}")
        return {
            "status": "failed", 
            "error": str(e), 
            "has_failures": True, 
            "has_skips": False,
            "missing_env_vars": missing_vars
        }

def get_module_status_indicator(result: Dict[str, Any]) -> str:
    """
    Get a status indicator for a module based on its test results.
    
    Args:
        result: Dictionary with test results
        
    Returns:
        Status indicator string
    """
    if result.get("has_failures", False):
        return STATUS_INDICATORS["failed"]
    elif result.get("has_skips", False) or result.get("status") == "skipped":
        return STATUS_INDICATORS["skipped"]
    else:
        return STATUS_INDICATORS["passed"]

def get_modules_for_menu_item(menu_section: str, submenu: str) -> List[str]:
    """
    Get modules that are relevant for a menu item.
    
    Args:
        menu_section: Main menu section
        submenu: Submenu item
        
    Returns:
        List of module names
    """
    if menu_section in MENU_STRUCTURE and submenu in MENU_STRUCTURE[menu_section]:
        return MENU_STRUCTURE[menu_section][submenu]
    return []

def get_menu_item_status(menu_section: str, submenu: str, results: Dict[str, Dict[str, Any]]) -> Tuple[str, List[str]]:
    """
    Get the status indicator and missing env vars for a menu item.
    
    Args:
        menu_section: Main menu section
        submenu: Submenu item
        results: Dictionary with test results for all modules
        
    Returns:
        Tuple of (status_indicator, missing_env_vars)
    """
    modules = get_modules_for_menu_item(menu_section, submenu)
    
    # If no modules are associated with this menu item, skip it
    if not modules:
        return "", []
    
    # Gather results for all associated modules
    module_results = [results.get(module, {}) for module in modules if module in results]
    
    # If no results are available, skip this menu item
    if not module_results:
        return "", []
    
    # Check if any module has failures
    has_failures = any(result.get("has_failures", False) for result in module_results)
    
    # Check if any module has skips but no failures
    has_skips = any(result.get("has_skips", False) or result.get("status") == "skipped" for result in module_results)
    
    # Collect all missing environment variables
    missing_env_vars = []
    for result in module_results:
        missing_env_vars.extend(result.get("missing_env_vars", []))
    
    # Determine the status indicator
    if has_failures:
        status_indicator = STATUS_INDICATORS["failed"]
    elif has_skips:
        status_indicator = STATUS_INDICATORS["skipped"]
    else:
        status_indicator = STATUS_INDICATORS["passed"]
    
    return status_indicator, list(set(missing_env_vars))  # Deduplicate missing env vars

async def run_all_tests(specific_module: Optional[str] = None) -> int:
    """
    Run all tests or tests for a specific module.
    
    Args:
        specific_module: Optional name of a specific module to test
        
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    start_time = time.time()
    results = {}
    
    print(f"\n{COLORS['bold']}🧪 Sol Tools Test Runner{COLORS['end']}")
    print(f"Running comprehensive tests organized by menu structure\n")
    
    # Display available environment variables
    print(f"{COLORS['cyan']}Environment variables detected:{COLORS['end']}")
    env_vars = [var for var in os.environ.keys() if var in ["HELIUS_API_KEY", "DUNE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SOL_TOOLS_DATA_DIR"]]
    if env_vars:
        for var in env_vars:
            value = os.environ.get(var, "")
            is_empty = value.strip() == ""
            status = f"present, but empty" if is_empty else "present"
            print(f"  ✓ {var} ({status})")
    else:
        print(f"  No relevant environment variables found.")
    print()
    
    # If a specific module is specified, only run tests for that module
    if specific_module:
        # Handle case-insensitivity by normalizing to uppercase for comparison
        specific_module_upper = specific_module.upper()
        module_found = False
        
        for module_name in AVAILABLE_MODULES.keys():
            if module_name.upper() == specific_module_upper:
                result = await run_module_tests(module_name)
                results[module_name] = result
                module_found = True
                break
                
        if not module_found:
            print(f"{STATUS_INDICATORS['failed']} Module '{specific_module}' not found")
            return 1
    else:
        # Run tests for all modules
        for module_name in AVAILABLE_MODULES:
            result = await run_module_tests(module_name)
            results[module_name] = result
    
    # Print test results organized by menu structure
    print(f"\n{COLORS['bold']}Test Results by Menu Structure:{COLORS['end']}")
    
    # Organize and display the menu structure with test results
    print("Main Menu")
    for menu_section in sorted(MENU_STRUCTURE.keys()):
        print(f"├── {menu_section}")
        
        for idx, submenu in enumerate(sorted(MENU_STRUCTURE[menu_section].keys())):
            is_last = idx == len(MENU_STRUCTURE[menu_section]) - 1
            prefix = "└──" if is_last else "├──"
            
            status_indicator, missing_vars = get_menu_item_status(menu_section, submenu, results)
            
            # Skip menu items with no associated modules or no test results
            if not status_indicator:
                continue
            
            # Add missing env var information for yellow status
            missing_info = ""
            if status_indicator == STATUS_INDICATORS["skipped"] and missing_vars:
                missing_info = f" (Missing: {', '.join(missing_vars)})"
            
            print(f"│   {prefix} {status_indicator} {submenu}{missing_info}")
    
    # Print summary of results by module category
    print(f"\n{COLORS['bold']}Test Results by Category:{COLORS['end']}")
    
    # Group modules by category
    modules_by_category = {}
    for module_name, module_info in AVAILABLE_MODULES.items():
        category = module_info.get("category", "General")
        if category not in modules_by_category:
            modules_by_category[category] = []
        modules_by_category[category].append(module_name)
    
    # Display results for each category
    for category, module_names in sorted(modules_by_category.items()):
        print(f"{category}")
        for module_name in sorted(module_names):
            if module_name in results:
                result = results[module_name]
                status_indicator = get_module_status_indicator(result)
                
                # Format module status
                status_text = "All tests passed"
                if result.get("has_failures", False):
                    status_text = "Some tests failed"
                elif result.get("has_skips", False) or result.get("status") == "skipped":
                    status_text = "Some tests skipped"
                    # Add missing environment variables info
                    missing_vars = result.get("missing_env_vars", [])
                    if missing_vars:
                        status_text += f" (Missing: {', '.join(missing_vars)})"
                
                print(f"  {status_indicator} {module_name} - {status_text}")
                
                # Call the module's test runner and extract detailed test results
                try:
                    module_info = AVAILABLE_MODULES.get(module_name)
                    if (module_info and not result.get("missing_env_vars") and 
                        (not result.get("has_skips", False) or 
                         (result.get("has_skips", False) and not result.get("has_failures", False)))):
                        # Import the module to get test details
                        test_module = importlib.import_module(module_info["module_path"])
                        # See if the module has a function to get test names
                        if hasattr(test_module, "get_test_names"):
                            test_names = test_module.get_test_names()
                            # Display each test with proper indentation and icon
                            for test_name in test_names:
                                if result.get("status") == "passed":
                                    print(f"    • {test_name}")
                        # If the module doesn't have test names, try to infer from the module info
                        elif "submodules" in module_info and module_info["submodules"]:
                            for submodule in module_info["submodules"]:
                                print(f"    • {submodule}")
                except Exception as e:
                    # Just continue without detailed test info if any issues
                    pass
    
    # Print final summary
    elapsed_time = time.time() - start_time
    print(f"\n{COLORS['bold']}📊 Test Summary (completed in {elapsed_time:.2f} seconds){COLORS['end']}")
    
    failed_modules = [module for module, result in results.items() if result.get("has_failures", False)]
    passed_modules = [module for module, result in results.items() 
                      if not result.get("has_failures", False) and not result.get("has_skips", False)]
    skipped_modules = [module for module, result in results.items() 
                       if not result.get("has_failures", False) and result.get("has_skips", False)]
    
    if failed_modules:
        print(f"{STATUS_INDICATORS['failed']} {len(failed_modules)} modules had test failures")
    
    if skipped_modules:
        print(f"{STATUS_INDICATORS['skipped']} {len(skipped_modules)} modules had skipped tests due to missing dependencies")
    
    if passed_modules:
        print(f"{STATUS_INDICATORS['passed']} {len(passed_modules)} modules passed")
    
    # Return success status for command-line usage
    return 0 if not failed_modules else 1

def main():
    """Main entry point for the test runner module."""
    parser = argparse.ArgumentParser(description="Sol Tools Test Runner")
    parser.add_argument('--module', help='Run tests for a specific module')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        setup_logging("DEBUG")
        # Also set an environment variable for test modules to use
        os.environ["DEBUG_TESTS"] = "1"
    else:
        setup_logging("INFO")
    
    # Run the tests
    try:
        asyncio.run(run_all_tests(args.module))
    except KeyboardInterrupt:
        print("\nTest run interrupted by user.")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        print(f"\nError running tests: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 