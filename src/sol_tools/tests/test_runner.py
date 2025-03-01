"""
Central test runner for Sol Tools.

This module provides the main function for running all tests.
"""

import os
import sys
import time
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


def run_all_tests() -> bool:
    """
    Run all tests for Sol Tools.
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    start_time = time.time()
    cprint("\n🚀 Starting Sol Tools Test Suite", "cyan")
    
    # Define test groups
    test_groups = [
        {"name": "File Operations", "run": run_file_ops_tests, "required": True},
        {"name": "Dragon Module", "run": run_dragon_tests, "required": True},
        {"name": "Solana Module", "run": run_solana_tests, "required": True},
    ]
    
    # Add optional test groups
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
            result = test_func()
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
    
    if failed_count == 0:
        cprint("\n✅ All required tests passed! Sol Tools is working correctly.", "green")
    else:
        cprint(f"\n❌ {failed_count} required test groups failed. Check the output above for details.", "red")
    
    # Return True only if all required tests passed
    return failed_count == 0


if __name__ == "__main__":
    sys.exit(0 if run_all_tests() else 1) 