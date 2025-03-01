"""
Test file operations functionality.

Tests file operations, directory creation, and file IO.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from ...tests.base_tester import BaseTester, cprint

class FileOpsTester(BaseTester):
    """Test file operations functionality."""
    
    def __init__(self):
        """Initialize the FileOpsTester."""
        super().__init__("FileOps")
        
        # Create test paths
        self.test_text_file = self.test_root / "test.txt"
        self.test_json_file = self.test_root / "test.json"
        self.test_nested_dir = self.test_root / "nested" / "dir" / "structure"
        self.test_nested_file = self.test_nested_dir / "nested_file.txt"
    
    def ensure_file_dir(self, file_path):
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
    
    def test_ensure_dir_creation(self) -> bool:
        """Test directory creation functionality."""
        try:
            # Test basic directory creation
            test_dir = self.test_root / "test_dir"
            self.ensure_file_dir(test_dir / "somefile.txt")
            
            if not test_dir.exists() or not test_dir.is_dir():
                cprint(f"  ❌ Directory {test_dir} was not created", "red")
                return False
            
            # Test nested directory creation
            nested_dir = self.test_nested_dir
            self.ensure_file_dir(self.test_nested_file)
            
            if not nested_dir.exists() or not nested_dir.is_dir():
                cprint(f"  ❌ Nested directory {nested_dir} was not created", "red")
                return False
            
            # Test with string path
            string_path = str(self.test_root / "string_path" / "file.txt")
            self.ensure_file_dir(string_path)
            
            string_dir = Path(string_path).parent
            if not string_dir.exists() or not string_dir.is_dir():
                cprint(f"  ❌ String path directory {string_dir} was not created", "red")
                return False
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_ensure_dir_creation: {str(e)}", "red")
            self.logger.exception("Exception in test_ensure_dir_creation")
            return False
    
    def test_text_file_write_read(self) -> bool:
        """Test writing to and reading from a text file."""
        try:
            # Test content
            test_content = "This is a test file content.\nWith multiple lines.\n"
            
            # Write to file
            self.ensure_file_dir(self.test_text_file)
            with open(self.test_text_file, "w") as f:
                f.write(test_content)
            
            # Verify file exists
            if not self.test_text_file.exists():
                cprint(f"  ❌ Text file {self.test_text_file} was not created", "red")
                return False
            
            # Read back and verify content
            with open(self.test_text_file, "r") as f:
                read_content = f.read()
            
            if read_content != test_content:
                cprint(f"  ❌ Text file content mismatch:\nExpected: {test_content}\nGot: {read_content}", "red")
                return False
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_text_file_write_read: {str(e)}", "red")
            self.logger.exception("Exception in test_text_file_write_read")
            return False
    
    def test_json_file_write_read(self) -> bool:
        """Test writing to and reading from a JSON file."""
        try:
            # Test JSON content
            test_json = {
                "name": "Test JSON",
                "values": [1, 2, 3, 4, 5],
                "nested": {
                    "key": "value",
                    "flag": True,
                    "count": 42
                }
            }
            
            # Write JSON to file
            self.ensure_file_dir(self.test_json_file)
            with open(self.test_json_file, "w") as f:
                json.dump(test_json, f, indent=2)
            
            # Verify file exists
            if not self.test_json_file.exists():
                cprint(f"  ❌ JSON file {self.test_json_file} was not created", "red")
                return False
            
            # Read back and verify content
            with open(self.test_json_file, "r") as f:
                read_json = json.load(f)
            
            if read_json != test_json:
                cprint(f"  ❌ JSON file content mismatch:\nExpected: {test_json}\nGot: {read_json}", "red")
                return False
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_json_file_write_read: {str(e)}", "red")
            self.logger.exception("Exception in test_json_file_write_read")
            return False
    
    def test_nested_file_write_read(self) -> bool:
        """Test writing to and reading from a nested file."""
        try:
            # Test content for nested file
            test_content = "This is content in a deeply nested file."
            
            # Write to nested file
            self.ensure_file_dir(self.test_nested_file)
            with open(self.test_nested_file, "w") as f:
                f.write(test_content)
            
            # Verify file exists
            if not self.test_nested_file.exists():
                cprint(f"  ❌ Nested file {self.test_nested_file} was not created", "red")
                return False
            
            # Read back and verify content
            with open(self.test_nested_file, "r") as f:
                read_content = f.read()
            
            if read_content != test_content:
                cprint(f"  ❌ Nested file content mismatch:\nExpected: {test_content}\nGot: {read_content}", "red")
                return False
            
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_nested_file_write_read: {str(e)}", "red")
            self.logger.exception("Exception in test_nested_file_write_read")
            return False
    
    def run_tests(self) -> Dict[str, bool]:
        """Run all file operations tests."""
        tests = [
            ("Directory Creation", self.test_ensure_dir_creation),
            ("Text File Write/Read", self.test_text_file_write_read),
            ("JSON File Write/Read", self.test_json_file_write_read),
            ("Nested File Write/Read", self.test_nested_file_write_read)
        ]
        
        return super().run_tests(tests)


def run_file_ops_tests() -> bool:
    """Run all file operations tests."""
    tester = FileOpsTester()
    try:
        results = tester.run_tests()
        return all(results.values())
    finally:
        tester.cleanup()


if __name__ == "__main__":
    run_file_ops_tests() 