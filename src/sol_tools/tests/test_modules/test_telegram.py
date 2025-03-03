"""
Test Telegram notification module functionality.

This module tests the Telegram notification functionality.
"""

import os
import json
import asyncio
import requests
from pathlib import Path
from typing import Dict, Any, List, Mapping, Optional

from ...tests.base_tester import BaseTester, cprint, STATUS_INDICATORS

def get_test_names() -> List[str]:
    """
    Get the names of all tests in this module.
    
    Returns:
        A list of test names for display in the test runner
    """
    return [
        "Telegram Module Imports",
        "Telegram Credentials Validation",
        "Telegram Message Sending"
    ]

class TelegramTester(BaseTester):
    """Test Telegram notification functionality."""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """Initialize the TelegramTester."""
        super().__init__("Telegram")
        
        # Store options
        self.options = options or {}
        
        # Create Telegram test directories
        self._create_telegram_directories()
        
        # Required environment variables for this module
        self.required_env_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    
    def _create_telegram_directories(self) -> None:
        """Create Telegram-specific test directories."""
        (self.test_root / "output-data" / "telegram").mkdir(parents=True, exist_ok=True)
    
    async def test_telegram_imports(self) -> bool:
        """
        Test that Telegram modules can be imported.
        
        Returns:
            bool: True if imports succeed, False otherwise
        """
        cprint("  Testing Telegram module imports...", "blue")
        
        try:
            # Import the main Telegram-related modules
            from ...utils.common import test_telegram
            
            cprint("  ✓ Successfully imported Telegram modules", "green")
            return True
            
        except Exception as e:
            cprint(f"  ❌ Failed to import Telegram modules: {str(e)}", "red")
            self.logger.exception("Exception in test_telegram_imports")
            return False
    
    async def test_telegram_credentials(self) -> Optional[bool]:
        """
        Test that Telegram credentials are available.
        
        Returns:
            Optional[bool]: 
                - True if credentials are available
                - None if test should be skipped due to missing credentials
        """
        cprint("  Testing Telegram credentials...", "blue")
        
        try:
            # Check for required environment variables
            telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
            
            # Debug: Print environment variables for debugging
            print(f"  DEBUG: TELEGRAM_BOT_TOKEN present = {telegram_bot_token is not None}, value = '{telegram_bot_token}'")
            print(f"  DEBUG: TELEGRAM_CHAT_ID present = {telegram_chat_id is not None}, value = '{telegram_chat_id}'")
            
            # Check if values are empty strings or None
            if not telegram_bot_token or telegram_bot_token.strip() == "":
                cprint("  ⚠️ TELEGRAM_BOT_TOKEN is not set or is empty", "yellow")
                return None  # Skip the test instead of failing
                
            if not telegram_chat_id or telegram_chat_id.strip() == "":
                cprint("  ⚠️ TELEGRAM_CHAT_ID is not set or is empty", "yellow")
                return None  # Skip the test instead of failing
                
            cprint("  ✓ Telegram credentials are properly set", "green")
            return True
            
        except Exception as e:
            cprint(f"  ❌ Exception in test_telegram_credentials: {str(e)}", "red")
            self.logger.exception("Exception in test_telegram_credentials")
            return False
    
    async def test_telegram_send(self) -> Optional[bool]:
        """
        Test sending a message to Telegram.
        
        Returns:
            Optional[bool]: 
                - True if message is sent successfully
                - None if test should be skipped due to missing credentials
                - False if there's an error sending the message
        """
        cprint("  Testing Telegram message sending...", "blue")
        
        try:
            # Check for required environment variables
            telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
            
            # Check if values are empty strings or None
            if not telegram_bot_token or telegram_bot_token.strip() == "" or not telegram_chat_id or telegram_chat_id.strip() == "":
                cprint("  ⚠️ Skipping test due to missing Telegram credentials", "yellow")
                return None  # Return None to indicate the test should be skipped
            
            # Attempt to send a test message
            message = "🧪 Sol Tools Test Runner - Test message"
            url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
            
            response = requests.post(url, json={
                "chat_id": telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            })
            
            if response.status_code == 200:
                cprint(f"  ✓ Test message sent successfully to Telegram", "green")
                return True
            else:
                cprint(f"  ❌ Failed to send message to Telegram: {response.text}", "red")
                return False
                
        except Exception as e:
            cprint(f"  ❌ Exception in test_telegram_send: {str(e)}", "red")
            self.logger.exception("Exception in test_telegram_send")
            return False
    
    async def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all Telegram module tests.
        
        Returns:
            Dictionary mapping test names to results
        """
        # Discover environment variable requirements for tests
        self.discover_test_env_vars()
        
        # Run the tests using the base class method
        return await super().run_all_tests()

async def run_telegram_tests(options: Optional[Dict[str, Any]] = None) -> int:
    """
    Run all Telegram tests.
    
    Args:
        options: Optional dictionary with test options
        
    Returns:
        int: Exit code
            - 0: All tests passed
            - 1: Some tests failed
            - 2: All tests were skipped
    """
    tester = TelegramTester(options)
    try:
        test_results = await tester.run_all_tests()
        
        # Clean up
        tester.cleanup()
        
        # Get all test results
        passed_tests = []
        skipped_tests = []
        failed_tests = []
        
        for test_name, result in test_results.items():
            status = result.get("status")
            if status == "passed":
                passed_tests.append(test_name)
            elif status == "skipped":
                skipped_tests.append(test_name)
            else:
                failed_tests.append(test_name)
        
        # Print summary
        # Commented out to avoid duplicate summary in the test runner output
        # print(f"\n{STATUS_INDICATORS['skipped' if len(skipped_tests) == len(test_results) else 'passed' if not failed_tests else 'failed']} Telegram Summary: {len(passed_tests)}/{len(test_results)} tests passed, {len(skipped_tests)} skipped")
        
        # If all tests were skipped or all remaining tests passed, consider it a success
        if len(failed_tests) == 0:
            # If all tests were skipped, return 2 (special code for "all skipped")
            if len(passed_tests) == 0 and len(skipped_tests) > 0:
                return 2
            # Otherwise return 0 (all tests passed or skipped)
            return 0
        else:
            # Some tests failed
            return 1
                       
    except Exception as e:
        print(f"Error running Telegram tests: {str(e)}")
        # Clean up
        tester.cleanup()
        return 1

if __name__ == "__main__":
    asyncio.run(run_telegram_tests()) 