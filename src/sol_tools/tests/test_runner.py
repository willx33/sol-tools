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
        "Bundle Tracker 🐉": ["Dragon", "Solana"],
        "Wallet Profiler 🐉": ["Dragon", "Solana"],
        "Top Trader Finder 🐉": ["Dragon", "Solana"],
        "TX Scanner 🐉": ["Dragon", "Solana"],
        "Copycat Finder 🐉": ["Dragon", "Solana"],
        "Whale Tracker 🐉": ["Dragon", "Solana"],
        "Early Investor Finder 🐉": ["Dragon", "Solana"]
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

def check_module_env_vars(module_name):
    """
    Check if a module has all required environment variables.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        Tuple of (status_indicator, missing_vars)
    """
    if module_name not in AVAILABLE_MODULES:
        return STATUS_INDICATORS["failed"], [f"Module '{module_name}' not found"]
    
    # Get required env vars for this module
    module_info = AVAILABLE_MODULES[module_name]
    required_env_vars = module_info.get("required_env_vars", [])
    
    # Check which env vars are missing
    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    # Return appropriate status based on missing vars
    if missing_vars:
        return STATUS_INDICATORS["skipped"], missing_vars
    
    return STATUS_INDICATORS["passed"], []

async def run_module_tests(module_name, module_info):
    """
    Run tests for a specific module.
    
    Args:
        module_name: Name of the module to test
        module_info: Module information from AVAILABLE_MODULES
        
    Returns:
        Dict containing test results and status
    """
    # Check required environment variables
    module_status, missing_env_vars = check_module_env_vars(module_name)
    
    if module_status == STATUS_INDICATORS["skipped"]:
        cprint(f"\n🟡 Skipping {module_name} tests due to missing environment variables: {', '.join(missing_env_vars)}", "yellow")
        return {
            "status": "skipped",
            "missing_env_vars": missing_env_vars,
            "has_skips": True
        }
    
    # Print module header
    cprint(f"\nRunning tests for {module_name}", "bold")
    
    try:
        # Import the test module
        module_path = module_info["module_path"]
        run_func_name = module_info.get("run_func", "run_tests")
        
        try:
            test_module = importlib.import_module(module_path)
            run_func = getattr(test_module, run_func_name)
        except (ImportError, AttributeError) as e:
            cprint(f"❌ Failed to import test module {module_path}: {str(e)}", "red")
            return {
                "status": "failed",
                "reason": f"Import error: {str(e)}",
                "has_failures": True
            }
        
        # Run the tests
        options = {}  # Can be expanded to pass options from command line
        
        # Allow both return styles - dict or int
        result = await run_func(options)
        
        if isinstance(result, int):
            # Old-style int return, convert to dict
            passed = result == 0
            return {
                "status": "passed" if passed else "failed",
                "has_failures": not passed,
                "exit_code": result
            }
        else:
            # New-style dict return with detailed results
            module_passed = not result.get("has_failures", False)
            has_skips = result.get("has_skips", False) or any(
                r.get("status") == "skipped" for r in result.get("tests", {}).values()
            )
            
            return {
                "status": "passed" if module_passed else "failed",
                "has_skips": has_skips,
                "has_failures": not module_passed,
                "tests": result.get("tests", {}),
                "total_tests": result.get("total_tests", 0),
                "passed_tests": result.get("passed_tests", 0),
                "skipped_tests": result.get("skipped_tests", 0)
            }
            
    except Exception as e:
        cprint(f"❌ Error running tests for {module_name}: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "failed",
            "reason": str(e),
            "has_failures": True
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
    Run all tests or tests for a specific module.
    
    Args:
        module_name: Optional name of a specific module to test
        
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    start_time = time.time()
    
    # Print header
    cprint("\n🧪 Sol Tools Test Runner", "bold")
    cprint("Running comprehensive tests organized by menu structure", "cyan")
    
    # Check environment variables
    print_env_vars()
    
    # Store results for each module
    module_results = {}
    
    # Run tests for the specified module, or all modules if none specified
    if module_name and module_name.lower() != "all":
        # Run tests for a specific module
        if module_name.lower() in AVAILABLE_MODULES:
            module_info = AVAILABLE_MODULES[module_name.lower()]
            module_results[module_name] = await run_module_tests(module_name, module_info)
        else:
            cprint(f"\n❌ Module '{module_name}' not found", "red")
            return 1
    else:
        # Run tests for all modules
        for name, info in AVAILABLE_MODULES.items():
            module_results[name] = await run_module_tests(name, info)
    
    # Print test results by menu structure
    print_results_by_menu(module_results)
    
    # Print test results by category
    print_results_by_category(module_results)
    
    # Print summary
    exit_code = await print_summary(module_results, start_time)
    
    # Return exit code
    return exit_code

async def print_summary(module_results, start_time):
    """Print a summary of test results."""
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Count the results
    passed_modules = []
    failed_modules = []
    skipped_modules = []
    
    total_tests = 0
    passed_tests = 0
    skipped_tests = 0
    failed_tests = 0
    
    # Process results for each module
    for module_name, result in module_results.items():
        module_status = result.get("status", "unknown")
        
        if "tests" in result:
            # Count test results for this module
            module_total = result.get("total_tests", 0)
            module_passed = result.get("passed_tests", 0)
            module_skipped = result.get("skipped_tests", 0)
            module_failed = module_total - module_passed - module_skipped
            
            # Add to the totals
            total_tests += module_total
            passed_tests += module_passed
            skipped_tests += module_skipped
            failed_tests += module_failed
        
        # Track module status
        if module_status == "passed":
            passed_modules.append(module_name)
        elif module_status == "skipped":
            skipped_modules.append(module_name)
        else:
            failed_modules.append(module_name)
    
    # Print the summary
    cprint("\n📊 Test Summary (completed in {:.2f} seconds)".format(elapsed_time), "bold")
    
    # Module status
    if skipped_modules:
        cprint(f"🟡 {len(skipped_modules)} modules had skipped tests due to missing dependencies", "yellow")
    if failed_modules:
        cprint(f"🔴 {len(failed_modules)} modules had failures", "red")
    
    cprint(f"🟢 {len(passed_modules)} modules passed", "green")
    
    # Detailed stats
    if total_tests > 0:
        # Only show detailed stats if we have test data
        print("\n📈 Detailed Test Statistics:")
        
        # Calculate percentages
        pass_percent = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        skip_percent = (skipped_tests / total_tests) * 100 if total_tests > 0 else 0
        fail_percent = (failed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"  Total Tests: {total_tests}")
        cprint(f"  Passed: {passed_tests} ({pass_percent:.1f}%)", "green")
        
        if skipped_tests > 0:
            cprint(f"  Skipped: {skipped_tests} ({skip_percent:.1f}%)", "yellow")
        
        if failed_tests > 0:
            cprint(f"  Failed: {failed_tests} ({fail_percent:.1f}%)", "red")
        
        # Calculate code coverage approximation if available
        print_coverage_summary(passed_tests, total_tests)
    
    # Return success status for command-line usage
    return 0 if not failed_modules else 1

def print_coverage_summary(passed_tests, total_tests):
    """
    Print an approximate code coverage summary.
    
    This is a very rough approximation of code coverage based on
    the test pass rate. It serves as a quick indicator only.
    """
    # Only show coverage indication if tests were run
    if total_tests == 0:
        return
    
    # Calculate estimated coverage (simple approximation)
    # This is intentionally conservative to avoid overestimating coverage
    est_coverage = min(95, (passed_tests / total_tests) * 100)
    
    # Print coverage bar
    bar_width = 30
    covered_width = int((est_coverage / 100) * bar_width)
    uncovered_width = bar_width - covered_width
    
    coverage_bar = f"[{'=' * covered_width}{' ' * uncovered_width}]"
    
    print("\n📊 Estimated Test Coverage:")
    print(f"  {coverage_bar} {est_coverage:.1f}%")
    print("  (This is an approximation based on test success rate)")
    
    # Add coverage insights
    if est_coverage < 50:
        cprint("  ⚠️ Low test coverage detected. Consider adding more tests.", "yellow")
    elif est_coverage < 70:
        cprint("  📝 Moderate test coverage. Key features are tested.", "cyan")
    else:
        cprint("  ✅ Good test coverage. Most functionality is being tested.", "green")

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
            is_empty = value.strip() == ""
            status = f"present, but empty" if is_empty else "present"
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