"""
Central test runner for Sol Tools.

This module provides the main function for running all tests.
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

from .base_tester import cprint
from .test_core.test_file_ops import run_file_ops_tests
from .test_modules.test_dragon import run_dragon_tests
from .test_modules.test_solana import run_solana_tests

# Import optional testers if available
try:
    from .test_modules.test_sharp import run_sharp_tests
    SHARP_AVAILABLE = True
except ImportError:
    SHARP_AVAILABLE = False

try:
    from .test_modules.test_dune import run_dune_tests
    DUNE_AVAILABLE = True
except ImportError:
    DUNE_AVAILABLE = False

try:
    from .test_modules.test_gmgn import run_gmgn_tests
    GMGN_AVAILABLE = True
except ImportError:
    GMGN_AVAILABLE = False

try:
    from .test_modules.test_ethereum import run_ethereum_tests
    ETHEREUM_AVAILABLE = True
except ImportError:
    ETHEREUM_AVAILABLE = False

try:
    from .test_integration.test_workflows import run_workflow_tests
    WORKFLOWS_AVAILABLE = True
except ImportError:
    WORKFLOWS_AVAILABLE = False

# Enhanced test framework - add additional test modules
try:
    from .test_core.test_config import run_config_tests
    CONFIG_TESTS_AVAILABLE = True
except ImportError:
    CONFIG_TESTS_AVAILABLE = False

try:
    from .test_core.test_cleanup import run_cleanup_tests
    CLEANUP_TESTS_AVAILABLE = True
except ImportError:
    CLEANUP_TESTS_AVAILABLE = False

try:
    from .test_core.test_environment import run_environment_tests
    ENVIRONMENT_TESTS_AVAILABLE = True
except ImportError:
    ENVIRONMENT_TESTS_AVAILABLE = False


def save_test_report(results: Dict[str, bool], duration: float, timestamp: str) -> str:
    """
    Save the test results to a JSON file in the cache directory.
    
    Args:
        results: Dictionary of test group results
        duration: Test duration in seconds
        timestamp: Timestamp string for the report
        
    Returns:
        str: Path to the saved report file
    """
    # Ensure reports directory exists
    try:
        root_dir = Path(__file__).parents[3]  # Project root
        # Save reports to cache directory instead of dedicated reports directory
        reports_dir = root_dir / "data" / "cache" / "test-reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Create report data
        report = {
            "timestamp": timestamp,
            "duration": duration,
            "results": results,
            "passed": all(results.values()),
            "pass_count": sum(1 for v in results.values() if v),
            "total_count": len(results),
            "pass_percentage": round(sum(1 for v in results.values() if v) / len(results) * 100, 2),
            "environment": {
                "python_version": sys.version,
                "os": sys.platform
            }
        }
        
        # Generate filename with timestamp
        filename = f"test_report_{timestamp.replace(' ', '_').replace(':', '-')}.json"
        report_path = reports_dir / filename
        
        # Write report to file
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            
        return str(report_path)
        
    except Exception as e:
        cprint(f"⚠️ Failed to save test report: {str(e)}", "yellow")
        return ""


def run_all_tests(save_report: bool = True, verbose: bool = False) -> bool:
    """
    Run all tests for Sol Tools.
    
    Args:
        save_report: Whether to save a test report
        verbose: Whether to print verbose information
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    start_time = time.time()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cprint("\n🚀 Starting Sol Tools Test Suite", "cyan")
    cprint(f"Timestamp: {timestamp}", "cyan")
    
    # Define test groups
    test_groups = [
        {"name": "File Operations", "run": run_file_ops_tests, "required": True},
        {"name": "Dragon Module", "run": run_dragon_tests, "required": True},
        {"name": "Solana Module", "run": run_solana_tests, "required": True},
    ]
    
    # Add optional core test groups
    if CONFIG_TESTS_AVAILABLE:
        test_groups.append({"name": "Config System", "run": run_config_tests, "required": True})
    
    if CLEANUP_TESTS_AVAILABLE:
        test_groups.append({"name": "Cleanup System", "run": run_cleanup_tests, "required": True})
    
    if ENVIRONMENT_TESTS_AVAILABLE:
        test_groups.append({"name": "Environment System", "run": run_environment_tests, "required": True})
    
    # Add optional module test groups
    if SHARP_AVAILABLE:
        test_groups.append({"name": "Sharp Module", "run": run_sharp_tests, "required": False})
    
    if DUNE_AVAILABLE:
        test_groups.append({"name": "Dune Module", "run": run_dune_tests, "required": False})
    
    if GMGN_AVAILABLE:
        test_groups.append({"name": "GMGN Module", "run": run_gmgn_tests, "required": False})
    
    if ETHEREUM_AVAILABLE:
        test_groups.append({"name": "Ethereum Module", "run": run_ethereum_tests, "required": False})
    
    if WORKFLOWS_AVAILABLE:
        test_groups.append({"name": "Integration Workflows", "run": run_workflow_tests, "required": False})
    
    # Run tests and collect results
    results = {}
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    
    for group in test_groups:
        group_name = group["name"]
        test_func = group["run"]
        required = group["required"]
        
        cprint(f"\n==== Testing {group_name} ====", "bold")
        
        try:
            result = test_func(verbose=verbose)
            results[group_name] = result
            
            if result:
                passed_count += 1
                cprint(f"✅ {group_name} tests passed", "green")
            else:
                if required:
                    failed_count += 1
                    cprint(f"❌ {group_name} tests failed", "red")
                else:
                    skipped_count += 1
                    cprint(f"⚠️ {group_name} tests failed (optional)", "yellow")
        except Exception as e:
            if required:
                failed_count += 1
                cprint(f"❌ {group_name} tests crashed: {str(e)}", "red")
            else:
                skipped_count += 1
                cprint(f"⚠️ {group_name} tests crashed (optional): {str(e)}", "yellow")
            results[group_name] = False
    
    # Print summary
    duration = time.time() - start_time
    total_tests = passed_count + failed_count
    
    cprint("\n==== Test Summary ====", "bold")
    cprint(f"Total duration: {duration:.2f} seconds", "bold")
    cprint(f"Passed: {passed_count}/{total_tests} required test groups", "bold")
    
    if skipped_count > 0:
        cprint(f"Skipped/Failed: {skipped_count} optional test groups", "yellow")
    
    # Save test report if requested
    if save_report:
        report_path = save_test_report(results, duration, timestamp)
        if report_path:
            cprint(f"📊 Test report saved to: {report_path}", "cyan")
    
    if failed_count == 0:
        cprint("\n✅ All required tests passed! Sol Tools is working correctly.", "green")
    else:
        cprint(f"\n❌ {failed_count} required test groups failed. Check the output above for details.", "red")
    
    # Return True only if all required tests passed
    return failed_count == 0


if __name__ == "__main__":
    # Process command-line arguments
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    save_report = "--report" in sys.argv or "-r" in sys.argv
    
    sys.exit(0 if run_all_tests(save_report=save_report, verbose=verbose) else 1) 