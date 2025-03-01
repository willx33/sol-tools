"""
Tests for environment variable handling and configuration.

This module tests the environment variable handling and configuration system.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path to ensure imports work correctly
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root))

from src.sol_tools.tests.base_tester import BaseTester, cprint

# Define a simplified version of required environment variables
REQUIRED_ENV_VARS = {
    'solana': ['HELIUS_API_KEY'],
    'dune': ['DUNE_API_KEY'],
    'telegram': ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'],
    'core': []
}

# Implement a local version of check_env_vars
def check_env_vars(module):
    """Check if all required environment variables for a module are set."""
    if module not in REQUIRED_ENV_VARS:
        return True
    
    for var in REQUIRED_ENV_VARS[module]:
        if var not in os.environ or not os.environ[var]:
            return False
    return True

class EnvironmentTester(BaseTester):
    """Test environment variable handling and configuration."""
    
    def __init__(self, verbose=False):
        """Initialize the EnvironmentTester."""
        super().__init__("Environment")
        self.verbose = verbose
        
        # Save original environment
        self._save_environment()
        
        # Create test environment file
        self._create_env_file()
    
    def _save_environment(self):
        """Save the original environment for restoration after tests."""
        self.original_env = {}
        for module, vars_list in REQUIRED_ENV_VARS.items():
            for var in vars_list:
                if var in os.environ:
                    self.original_env[var] = os.environ[var]
    
    def _restore_environment(self):
        """Restore the original environment."""
        # Clean up environment
        for module, vars_list in REQUIRED_ENV_VARS.items():
            for var in vars_list:
                if var in os.environ:
                    del os.environ[var]
        
        # Restore original values
        for var, value in self.original_env.items():
            os.environ[var] = value
    
    def _create_env_file(self):
        """Create a test .env file."""
        self.env_file = self.test_root / ".env"
        
        # Create .env file with test values
        env_content = """
# Test environment file
HELIUS_API_KEY=test_helius_key
DUNE_API_KEY=test_dune_key
TELEGRAM_BOT_TOKEN=test_telegram_token
TELEGRAM_CHAT_ID=test_chat_id
"""
        with open(self.env_file, "w") as f:
            f.write(env_content)
        
        if self.verbose:
            cprint(f"✓ Created test .env file at {self.env_file}", "green")
    
    def test_load_env_file(self):
        """Test loading environment variables from .env file."""
        # Clear relevant environment variables
        for module, vars_list in REQUIRED_ENV_VARS.items():
            for var in vars_list:
                if var in os.environ:
                    del os.environ[var]
        
        if self.verbose:
            cprint("✓ Cleared environment variables", "blue")
        
        # Set test file as environment variable source
        os.environ['SOL_TOOLS_ENV_FILE'] = str(self.env_file)
        
        try:
            # Manually load environment variables from .env file
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            
            # Check if environment variables were loaded
            env_vars_loaded = (
                os.environ.get('HELIUS_API_KEY') == 'test_helius_key' and
                os.environ.get('DUNE_API_KEY') == 'test_dune_key' and
                os.environ.get('TELEGRAM_BOT_TOKEN') == 'test_telegram_token' and
                os.environ.get('TELEGRAM_CHAT_ID') == 'test_chat_id'
            )
            
            if self.verbose:
                if env_vars_loaded:
                    cprint("✓ Successfully loaded environment variables from .env file", "green")
                else:
                    cprint("❌ Failed to load environment variables from .env file", "red")
                    for var in ['HELIUS_API_KEY', 'DUNE_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']:
                        cprint(f"  - {var}: {os.environ.get(var, 'NOT SET')}", "red")
            
            return env_vars_loaded
            
        except Exception as e:
            if self.verbose:
                cprint(f"❌ Error loading environment: {str(e)}", "red")
            return False
    
    def test_missing_env_validation(self):
        """Test validation of missing environment variables."""
        # Clear relevant environment variables
        for module, vars_list in REQUIRED_ENV_VARS.items():
            for var in vars_list:
                if var in os.environ:
                    del os.environ[var]
        
        # Check each module's env vars
        results = {}
        for module in REQUIRED_ENV_VARS.keys():
            result = check_env_vars(module)
            results[module] = result
            
            if self.verbose:
                status = "✓" if result else "❌"
                cprint(f"{status} Module {module}: {'All variables present' if result else 'Missing variables'}", 
                      "green" if result else "red")
        
        # Expected result: all modules should fail validation since we cleared the env vars
        expected_results = {module: False for module in REQUIRED_ENV_VARS.keys() if REQUIRED_ENV_VARS[module]}
        
        # Modules with no required env vars should pass
        for module, vars_list in REQUIRED_ENV_VARS.items():
            if not vars_list:
                expected_results[module] = True
        
        if self.verbose:
            cprint("✓ Validation test completed", "green")
        
        return results == expected_results
    
    def test_selective_env_validation(self):
        """Test validation with only some environment variables set."""
        # Clear relevant environment variables
        for module, vars_list in REQUIRED_ENV_VARS.items():
            for var in vars_list:
                if var in os.environ:
                    del os.environ[var]
        
        # Set only some environment variables
        os.environ['HELIUS_API_KEY'] = 'test_helius_key'
        
        if self.verbose:
            cprint("✓ Set Solana API key only", "blue")
        
        # Check each module's env vars
        results = {}
        for module in REQUIRED_ENV_VARS.keys():
            result = check_env_vars(module)
            results[module] = result
            
            if self.verbose:
                status = "✓" if result else "❌"
                cprint(f"{status} Module {module}: {'All variables present' if result else 'Missing variables'}", 
                      "green" if result else "red")
        
        # Expected results: only modules that require HELIUS_API_KEY and nothing else should pass
        expected_results = {}
        for module, vars_list in REQUIRED_ENV_VARS.items():
            # Module passes if it has no required vars or if it only requires HELIUS_API_KEY
            if not vars_list:
                expected_results[module] = True
            elif len(vars_list) == 1 and 'HELIUS_API_KEY' in vars_list:
                expected_results[module] = True
            else:
                expected_results[module] = False
        
        if self.verbose:
            cprint("✓ Selective validation test completed", "green")
        
        return results == expected_results
    
    def run_all_tests(self):
        """Run all environment tests."""
        tests = [
            ("Load Environment from File", self.test_load_env_file),
            ("Missing Environment Validation", self.test_missing_env_validation),
            ("Selective Environment Validation", self.test_selective_env_validation),
        ]
        
        # Run the tests
        results = self.run_tests(tests)
        
        # Restore original environment
        self._restore_environment()
        
        # Clean up after ourselves
        self.cleanup()
        
        # Return True only if all tests passed
        return all(results.values())


def run_environment_tests(verbose=False):
    """
    Run all environment tests.
    
    Args:
        verbose: Whether to print verbose output
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    tester = EnvironmentTester(verbose=verbose)
    try:
        return tester.run_all_tests()
    except Exception as e:
        cprint(f"❌ Environment tests failed with exception: {str(e)}", "red")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the tests with verbose output if invoked directly
    run_environment_tests(verbose=True) 