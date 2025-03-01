"""
Test script to verify menu indicators for missing environment variables.
"""

import os
import sys
from pathlib import Path
import logging

# Add project root to path to ensure imports work correctly
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the menu system
from src.sol_tools.core.menu import create_main_menu, check_module_env_vars
from src.sol_tools.cli import create_handlers
from src.sol_tools.core.config import REQUIRED_ENV_VARS

def test_menu_env_indicators(partial_config=False):
    """
    Test that menu items are properly marked when environment variables are missing.
    
    Args:
        partial_config: If True, only set some environment variables to test partial config
    """
    # Clear all relevant environment variables first
    for module, vars_list in REQUIRED_ENV_VARS.items():
        for var in vars_list:
            if var in os.environ:
                del os.environ[var]
    
    # Print current environment variables for debugging
    print("\nCurrent Environment Variables:")
    for module, vars_list in REQUIRED_ENV_VARS.items():
        for var in vars_list:
            print(f"{var}: {os.environ.get(var, 'NOT SET')}")
    
    # Set test environment variables
    print("\nSetting test environment variables...")
    if partial_config:
        # Only set some variables to test partial configuration
        os.environ["HELIUS_API_KEY"] = "test_key"  # For Solana
        # Leave DUNE_API_KEY unset
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"  # For Telegram
        # Leave TELEGRAM_CHAT_ID unset
    else:
        # Set all variables
        os.environ["HELIUS_API_KEY"] = "test_key"
        os.environ["DUNE_API_KEY"] = "test_key"
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
        os.environ["TELEGRAM_CHAT_ID"] = "test_id"
    
    # Reload modules to ensure they pick up the new environment variables
    import importlib
    from src.sol_tools.core import config
    importlib.reload(config)
    
    # Print updated environment variables for debugging
    print("\nUpdated Environment Variables:")
    for module, vars_list in REQUIRED_ENV_VARS.items():
        for var in vars_list:
            print(f"{var}: {os.environ.get(var, 'NOT SET')}")
    
    # Create handler dictionary
    handlers = create_handlers()
    
    # Create the main menu
    main_menu = create_main_menu(handlers)
    
    # Print the environment variable status
    print("\nEnvironment Variable Status:")
    print(f"Solana: {check_module_env_vars('solana')}")
    print(f"Dragon: {check_module_env_vars('dragon')}")
    print(f"Dune: {check_module_env_vars('dune')}")
    print(f"Ethereum: {check_module_env_vars('ethereum')}")
    print(f"GMGN: {check_module_env_vars('gmgn')}")
    print(f"Telegram: {check_module_env_vars('telegram')}")
    print(f"BullX: {check_module_env_vars('bullx')}")
    print(f"Sharp: {check_module_env_vars('sharp')}")
    
    # Check the main menu items
    print("\nMain Menu Items:")
    for option in main_menu:
        indicator = "🔴" if option.missing_env_vars else "✅"
        print(f"{indicator} {option.name}")
        
        # Check children if available
        if option.children:
            for child in option.children:
                if child.name != "Back":  # Skip "Back" options
                    child_indicator = "🔴" if child.missing_env_vars else "✅"
                    print(f"  {child_indicator} {child.name}")
                    
                    # Check grandchildren if available
                    if child.children:
                        for grandchild in child.children:
                            if grandchild.name != "Back":  # Skip "Back" options
                                grandchild_indicator = "🔴" if grandchild.missing_env_vars else "✅"
                                print(f"    {grandchild_indicator} {grandchild.name}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    # Test with partial configuration (some env vars missing)
    test_menu_env_indicators(partial_config=True) 