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

# Try to import dotenv for environment variable loading
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

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
        "Bundle Tracker 🐉": ["Dragon", "Solana"],
        "Wallet Profiler 🐉": ["Dragon", "Solana"],
        "Top Trader Finder 🐉": ["Dragon", "Solana"],
        "TX Scanner 🐉": ["Dragon", "Solana"],
        "Copycat Finder 🐉": ["Dragon", "Solana"],
        "Whale Tracker 🐉": ["Dragon", "Solana"],
        "Early Investor Finder 🐉": ["Dragon", "Solana"]
    },
    "Data Tools": {
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
        "Wallet Profiler 🐉": ["Dragon"],
        "Top Trader Finder 🐉": ["Dragon"],
        "TX Scanner 🐉": ["Dragon"],
        "Time-Based TX Finder 🐉": ["Dragon"]
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
        "category": "Data Tools",
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
    Check if required environment variables are missing for a module.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        List of missing environment variable names
    """
    # Get module info
    module_info = AVAILABLE_MODULES.get(module_name)
    if not module_info:
        return []
    
    # Get required environment variables - fix the key name
    required_env_vars = module_info.get("required_env_vars", [])
    
    # Debug information
    if os.environ.get("DEBUG_TESTS") == "1":
        print(f"DEBUG: Required env vars for {module_name}: {required_env_vars}")
    
    # Check if any environment variables are missing
    missing_env_vars = []
    for var in required_env_vars:
        # Check if variable is not set or is empty
        value = os.environ.get(var, "")
        is_present = var in os.environ and value.strip()
        
        if os.environ.get("DEBUG_TESTS") == "1":
            print(f"DEBUG: Checking {var} - Present in os.environ: {var in os.environ}, " 
                  f"Value: {'<empty>' if not value.strip() else value[:3] + '***'}, "
                  f"Is Valid: {is_present}")
        
        if not is_present:
            missing_env_vars.append(var)
    
    return missing_env_vars

def check_module_env_vars(module_name):
    """
    Check and display environment variable status for a module.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        Tuple of (bool, str) where:
          - bool is True if all required environment variables are present
          - str is a message describing the status
    """
    # Get missing environment variables
    missing_env_vars = check_missing_env_vars(module_name)
    
    # If no missing environment variables, return True
    if not missing_env_vars:
        return True, ""
    
    # Format missing environment variables
    missing_vars_str = ", ".join(missing_env_vars)
    
    # Return False with message
    return False, f"Missing environment variables: {missing_vars_str}"

async def run_module_tests(module_name, module_info):
    """
    Run tests for a specific module.
    
    Args:
        module_name: Name of the module to test
        module_info: Module information from AVAILABLE_MODULES
        
    Returns:
        Dictionary with test results
    """
    # Import the module's test function
    module_path = module_info.get("module_path", "")
    run_func = module_info.get("run_func", "run_tests")
    
    if not module_path:
        return {
            "status": "error",
            "message": f"No module path specified for {module_name}"
        }
    
    try:
        # Import the module
        module = importlib.import_module(module_path)
        
        # Get the run_tests function from the module
        test_func = getattr(module, run_func)
        
        # Call the run_tests function with options
        options = {
            "test_mode": True,
            "verbose": os.environ.get("DEBUG_TESTS") == "1"
        }
        
        # Run the tests
        results = await test_func(options)
        
        # Check if the test function returned a dict of test results
        # or just a simple status code
        if isinstance(results, dict):
            # The function returned detailed test results
            return results
        elif isinstance(results, int):
            # The function returned a status code (0=success, non-0=failure)
            if results == 2:  # Special code for "all skipped"
                return {
                    "status": "skipped",
                    "code": results,
                    "message": "All tests skipped"
                }
            status = "passed" if results == 0 else "failed"
            return {
                "status": status,
                "code": results
            }
        else:
            # Default handling - assume success for backward compatibility
            return {
                "status": "passed" if results else "failed"
            }
            
    except ModuleNotFoundError:
        return {
            "status": "error",
            "message": f"Module {module_path} not found"
        }
    except AttributeError:
        return {
            "status": "error",
            "message": f"Function {run_func} not found in {module_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
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

async def run_all_tests(module_name=None):
    """
    Run all tests, or tests for a specific module if specified.
    
    Args:
        module_name: Optional name of a specific module to test
        
    Returns:
        Exit code: 0 for success, 1 for failures
    """
    start_time = time.time()
    
    # Print header
    cprint("\n🧪 Sol Tools Test Runner", "cyan")
    cprint("Running comprehensive tests organized by menu structure", "cyan")
    
    # Ensure environment variables are loaded from .env file
    try:
        if load_dotenv:
            env_file = os.environ.get("SOL_TOOLS_ENV_FILE", os.path.join(os.path.expanduser("~"), ".sol_tools", ".env"))
            
            if os.path.exists(env_file):
                cprint(f"Loading environment variables from {env_file}", "blue")
                load_dotenv(env_file, override=True)
                
                # Verify key variables were loaded
                for key_var in ["HELIUS_API_KEY", "DUNE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
                    if key_var in os.environ and os.environ[key_var].strip():
                        cprint(f"  ✓ {key_var} loaded successfully", "green")
            else:
                cprint(f"Warning: .env file not found at {env_file}", "yellow")
    except Exception:
        cprint("Warning: dotenv not installed, skipping .env file loading", "yellow")
    
    # Print environment variables
    print_env_vars()
    print("\n")
    
    # Temporary workaround for test module import
    if module_name == "":
        module_name = None
    
    # Dictionary to store results keyed by module name
    module_results = {}
    
    # Check all AVAILABLE_MODULES for the tests
    for module_name_to_test, module_info in AVAILABLE_MODULES.items():
        # Skip if a specific module was requested and this isn't it
        if module_name and module_name.lower() != module_name_to_test.lower():
            continue
            
        # Try to run the module tests
        try:
            # Check for required environment variables
            env_available, env_message = check_module_env_vars(module_name_to_test)
            
            if not env_available:
                cprint(f"\n🟡 Skipping {module_name_to_test} tests due to {env_message}", "yellow")
                # Store skipped test result
                module_results[module_name_to_test] = {
                    "status": "skipped",
                    "message": env_message,
                    "missing_env_vars": env_message.split("Missing environment variables:", 1)[1].strip().split(", ")
                }
                continue
                
            # Print module header
            cprint(f"\nRunning tests for {module_name_to_test}", "cyan")
            
            # Run the module tests
            module_result = await run_module_tests(module_name_to_test, module_info)
            
            # Store the result
            module_results[module_name_to_test] = module_result
        except Exception as e:
            cprint(f"Error running {module_name_to_test} tests: {str(e)}", "red")
            # Store error result
            module_results[module_name_to_test] = {
                "status": "error",
                "message": str(e)
            }
    
    # Print summary organized by menu structure
    print("\nTest Results by Menu Structure:")
    print_results_by_menu(module_results)
    
    # Print summary organized by category
    print("\nTest Results by Category:")
    print_results_by_category(module_results)
    
    # Print global summary
    exit_code = await print_summary(module_results, start_time)
    
    return exit_code

async def print_summary(module_results, start_time):
    """
    Print a summary of test results.
    
    Args:
        module_results: Dictionary mapping module names to test results
        start_time: Time when testing started
        
    Returns:
        Exit code: 0 for success, non-zero for failures
    """
    end_time = time.time()
    duration = end_time - start_time
    
    # Initialize counters
    modules_with_missing_deps = []
    passed_modules = []
    skipped_modules = []
    failed_modules = []
    
    # Count passed, skipped, and failed modules
    for module_name, results in module_results.items():
        # Check if this is a skipped module due to missing dependencies
        if isinstance(results, dict) and results.get("status") == "skipped":
            if "message" in results and "Missing environment variables:" in results["message"]:
                missing_vars = results["message"].split("Missing environment variables:", 1)[1].strip()
                modules_with_missing_deps.append(f"{module_name} (Missing: {missing_vars})")
            skipped_modules.append(module_name)
            continue
        
        # For modules with test results
        if isinstance(results, dict):
            # Check if the module has a simple status
            if "status" in results:
                status = results["status"]
                # Special case: if code is 2, it means all tests were skipped
                if status == "failed" and results.get("code") == 2:
                    skipped_modules.append(module_name)
                elif status == "passed":
                    passed_modules.append(module_name)
                elif status == "skipped":
                    skipped_modules.append(module_name)
                elif status == "failed" or status == "error":
                    failed_modules.append(module_name)
                continue
            
            # For modules with individual test results
            has_failures = False
            all_skipped = True
            
            # Check each test result
            for test_name, test_result in results.items():
                if isinstance(test_result, dict) and "status" in test_result:
                    status = test_result["status"]
                    if status == "failed":
                        has_failures = True
                        all_skipped = False
                    elif status != "skipped":
                        all_skipped = False
            
            # Categorize the module based on test results
            if has_failures:
                failed_modules.append(module_name)
            elif all_skipped:
                skipped_modules.append(module_name)
            else:
                passed_modules.append(module_name)
    
    # Print header
    print()
    cprint(f"📊 Test Summary (completed in {duration:.2f} seconds)", "bold")
    
    # Print modules with missing dependencies
    if modules_with_missing_deps:
        cprint(f"🟡 {len(modules_with_missing_deps)} modules had skipped tests due to missing dependencies", "yellow")
        for module in modules_with_missing_deps:
            print(f"    {module}")
    
    # Print module status counts
    if passed_modules:
        cprint(f"🟢 {len(passed_modules)} modules passed", "green")
    
    if skipped_modules:
        cprint(f"🟡 {len(skipped_modules)} modules skipped", "yellow")
    
    if failed_modules:
        cprint(f"🔴 {len(failed_modules)} modules failed", "red")
    
    # Print test coverage
    total_modules = len(module_results)
    if total_modules > 0:
        coverage_pct = (len(passed_modules) / total_modules) * 100
        print()
        print(f"Test Coverage: {len(passed_modules)}/{total_modules} ({coverage_pct:.1f}%)")
    
    # Print additional options if tests were skipped
    if skipped_modules:
        print()
        print("To run with mock data instead of API calls:")
        print("    sol-tools --test --mock-only")
        
        # Collect missing environment variables
        missing_env_vars = set()
        for module_name, results in module_results.items():
            if isinstance(results, dict) and "status" in results and results["status"] == "skipped":
                if "message" in results and "Missing environment variables:" in results["message"]:
                    vars_part = results["message"].split("Missing environment variables:", 1)[1].strip()
                    for var in vars_part.split(","):
                        missing_env_vars.add(var.strip())
        
        if missing_env_vars:
            print()
            print("Missing environment variables? Add them to .env:")
            for env in sorted(missing_env_vars):
                print(f"    {env}=your_value_here")
    
    # Return success status for command-line usage
    return 0 if not failed_modules else 1

def print_env_vars():
    """Display available environment variables."""
    print(f"{COLORS['cyan']}Environment variables detected:{COLORS['end']}")
    env_vars = [var for var in os.environ.keys() if var in [
        "HELIUS_API_KEY", "DUNE_API_KEY", "TELEGRAM_BOT_TOKEN", 
        "TELEGRAM_CHAT_ID", "SOL_TOOLS_DATA_DIR"
    ]]
    
    if env_vars:
        for var in env_vars:
            value = os.environ.get(var, "")
            is_empty = not value.strip()
            # Show the actual value (partially redacted) if it exists
            if not is_empty:
                # Redact for security while showing some of the value
                redacted_value = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "****"
                status = f"present ({redacted_value})"
            else:
                status = "present, but empty"
            print(f"  ✓ {var} ({status})")
    else:
        print(f"  No relevant environment variables found.")
    print()

def print_results_by_menu(module_results):
    """Print test results organized by menu structure."""
    print(f"\n{COLORS['bold']}Test Results by Menu Structure:{COLORS['end']}")
    
    # Organize and display the menu structure with test results
    print("Main Menu")
    for menu_section in sorted(MENU_STRUCTURE.keys()):
        print(f"├── {menu_section}")
        
        for idx, submenu in enumerate(sorted(MENU_STRUCTURE[menu_section].keys())):
            is_last = idx == len(MENU_STRUCTURE[menu_section]) - 1
            prefix = "└──" if is_last else "├──"
            
            status_indicator, missing_vars = get_menu_item_status(menu_section, submenu, module_results)
            
            # Skip menu items with no associated modules or no test results
            if not status_indicator:
                continue
            
            # Add missing env var information for yellow status
            missing_info = ""
            if status_indicator == STATUS_INDICATORS["skipped"] and missing_vars:
                missing_info = f" (Missing: {', '.join(missing_vars)})"
            
            print(f"│   {prefix} {status_indicator} {submenu}{missing_info}")

def print_results_by_category(module_results):
    """Print summary of results by module category."""
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
            if module_name in module_results:
                result = module_results[module_name]
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
                        try:
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
                        except ModuleNotFoundError:
                            # Module path might be wrong, skip detailed reporting
                            pass
                except Exception as e:
                    # Just continue without detailed test info if any issues
                    pass

def main():
    """Main entry point for the test runner module."""
    parser = argparse.ArgumentParser(description="Sol Tools Test Runner")
    parser.add_argument('--module', help='Run tests for a specific module')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--env-file', help='Path to .env file to load environment variables from')
    
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        setup_logging("DEBUG")
        # Also set an environment variable for test modules to use
        os.environ["DEBUG_TESTS"] = "1"
    else:
        setup_logging("INFO")
    
    # Handle environment file specification
    if args.env_file:
        os.environ["SOL_TOOLS_ENV_FILE"] = args.env_file
        print(f"Using environment file: {args.env_file}")
    
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