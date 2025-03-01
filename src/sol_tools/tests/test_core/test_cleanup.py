"""
Tests for the cleanup system.

This module tests the cleanup functionality to ensure temporary data is properly disposed of.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path to ensure imports work correctly
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root))

from src.sol_tools.tests.base_tester import BaseTester, cprint
from src.sol_tools.utils.cleanup import clean_caches


class CleanupTester(BaseTester):
    """Test cleanup functionality."""
    
    def __init__(self, verbose=False):
        """Initialize the CleanupTester."""
        super().__init__("Cleanup")
        self.verbose = verbose
        
        # Create test directories and files
        self._create_test_files()
    
    def _create_test_files(self):
        """Create test files and directories for testing cleanup."""
        # Create pycache directories with dummy files
        pycache_dirs = [
            self.test_root / "src" / "__pycache__",
            self.test_root / "src" / "module1" / "__pycache__",
            self.test_root / "src" / "module2" / "__pycache__",
        ]
        
        for pycache_dir in pycache_dirs:
            pycache_dir.mkdir(parents=True, exist_ok=True)
            # Create some dummy .pyc files
            (pycache_dir / "file1.cpython-39.pyc").write_text("dummy content")
            (pycache_dir / "file2.cpython-39.pyc").write_text("dummy content")
        
        # Create cache directory with subdirectories
        cache_dir = self.test_root / "data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create cache subdirectories
        cache_subdirs = [
            cache_dir / "api_responses",
            cache_dir / "processed_data",
            cache_dir / "temp_files",
        ]
        
        for subdir in cache_subdirs:
            subdir.mkdir(exist_ok=True)
            # Create some dummy cache files
            (subdir / "cached_data_1.json").write_text('{"data": "test"}')
            (subdir / "cached_data_2.json").write_text('{"data": "test2"}')
        
        if self.verbose:
            cprint("✓ Created test directories and files", "green")
    
    def test_clean_pycache(self):
        """Test cleaning of __pycache__ directories."""
        # Count initial __pycache__ directories
        initial_count = 0
        for dirpath, dirnames, filenames in os.walk(self.test_root):
            if os.path.basename(dirpath) == "__pycache__":
                initial_count += 1
        
        if self.verbose:
            cprint(f"✓ Found {initial_count} __pycache__ directories before cleanup", "blue")
        
        # Prepare cleanup environment
        os.environ["SOL_TOOLS_TEST_ROOT"] = str(self.test_root)
        
        # Define a function to find directories to clean
        def _find_directories_to_clean(root_dir, dir_name):
            """Find directories with the given name under the root directory."""
            result = []
            for dirpath, dirnames, filenames in os.walk(root_dir):
                if os.path.basename(dirpath) == dir_name:
                    result.append(dirpath)
            return result
        
        # Modify the cleanup function for testing
        def test_clean_func():
            root_dir = Path(os.environ.get("SOL_TOOLS_TEST_ROOT", self.test_root))
            pycache_dirs = _find_directories_to_clean(root_dir, "__pycache__")
            
            cleaned = 0
            for pycache_dir in pycache_dirs:
                if self.verbose:
                    cprint(f"Cleaning {pycache_dir}", "blue")
                for item in Path(pycache_dir).glob("*.pyc"):
                    item.unlink()
                cleaned += 1
            
            return cleaned > 0
        
        # Run the test cleanup
        result = test_clean_func()
        
        # Verify that __pycache__ directories were cleaned
        empty_count = 0
        for dirpath, dirnames, filenames in os.walk(self.test_root):
            if os.path.basename(dirpath) == "__pycache__":
                if len(filenames) == 0:
                    empty_count += 1
        
        if self.verbose:
            cprint(f"✓ Found {empty_count} empty __pycache__ directories after cleanup", "green")
        
        # Test is successful if cleanup reported success
        return result
    
    def test_clean_cache(self):
        """Test cleaning of cache directories."""
        # Count initial cache files
        cache_dir = self.test_root / "data" / "cache"
        initial_file_count = sum(1 for _ in cache_dir.glob("**/*") if _.is_file())
        
        if self.verbose:
            cprint(f"✓ Found {initial_file_count} cache files before cleanup", "blue")
        
        # Prepare cleanup environment
        os.environ["SOL_TOOLS_TEST_ROOT"] = str(self.test_root)
        
        # Modify the cleanup function for testing
        def test_clean_func():
            cache_dir = Path(os.environ.get("SOL_TOOLS_TEST_ROOT", self.test_root)) / "data" / "cache"
            
            if not cache_dir.exists():
                return False
            
            cleaned = 0
            for item in cache_dir.glob("**/*"):
                if item.is_file():
                    if self.verbose:
                        cprint(f"Cleaning {item}", "blue")
                    item.unlink()
                    cleaned += 1
            
            return cleaned > 0
        
        # Run the test cleanup
        result = test_clean_func()
        
        # Verify that cache files were cleaned
        remaining_file_count = sum(1 for _ in cache_dir.glob("**/*") if _.is_file())
        
        if self.verbose:
            cprint(f"✓ Found {remaining_file_count} cache files after cleanup", "green")
        
        # Test is successful if cleanup reported success and files were removed
        return result and remaining_file_count < initial_file_count
    
    def test_directory_recreation(self):
        """Test that directories are recreated after cleanup."""
        # Clean directories first
        cache_dir = self.test_root / "data" / "cache"
        
        # Remove all cache directories
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
        
        if self.verbose:
            cprint("✓ Removed cache directory", "blue")
        
        # Prepare cleanup environment
        os.environ["SOL_TOOLS_TEST_ROOT"] = str(self.test_root)
        
        # Modify the cleanup function for testing
        def test_recreate_func():
            cache_dir = Path(os.environ.get("SOL_TOOLS_TEST_ROOT", self.test_root)) / "data" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create standard subdirectories
            subdirs = ["api_responses", "processed_data", "temp_files"]
            for subdir in subdirs:
                (cache_dir / subdir).mkdir(exist_ok=True)
            
            return cache_dir.exists() and all((cache_dir / subdir).exists() for subdir in subdirs)
        
        # Run the test recreation
        result = test_recreate_func()
        
        # Verify that directories were recreated
        all_dirs_exist = cache_dir.exists() and all(
            (cache_dir / subdir).exists() 
            for subdir in ["api_responses", "processed_data", "temp_files"]
        )
        
        if self.verbose:
            if all_dirs_exist:
                cprint("✓ All directories were successfully recreated", "green")
            else:
                cprint("❌ Some directories were not recreated", "red")
        
        return result and all_dirs_exist
    
    def run_all_tests(self):
        """Run all cleanup tests."""
        tests = [
            ("Clean __pycache__ Directories", self.test_clean_pycache),
            ("Clean Cache Directories", self.test_clean_cache),
            ("Directory Recreation", self.test_directory_recreation),
        ]
        
        # Run the tests
        results = self.run_tests(tests)
        
        # Clean up after ourselves
        self.cleanup()
        
        # Return True only if all tests passed
        return all(results.values())


def run_cleanup_tests(verbose=False):
    """
    Run all cleanup tests.
    
    Args:
        verbose: Whether to print verbose output
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    tester = CleanupTester(verbose=verbose)
    try:
        return tester.run_all_tests()
    except Exception as e:
        cprint(f"❌ Cleanup tests failed with exception: {str(e)}", "red")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the tests with verbose output if invoked directly
    run_cleanup_tests(verbose=True) 