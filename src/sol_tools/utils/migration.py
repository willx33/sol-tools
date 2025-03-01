"""
Migration utilities for Sol Tools.

This module provides functions for migrating existing configuration files,
adapters, and other components to the new architecture.
"""

import os
import json
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

# Create module-specific logger
logger = logging.getLogger(__name__)

# Import registry for migration
from ..core.config_registry import ConfigRegistry
from ..core.config import CONFIG_DIR, MAIN_CONFIG


def migrate_config() -> bool:
    """
    Migrate the existing configuration file to the new registry format.
    
    This function:
    1. Creates a backup of the existing config
    2. Reads the existing config
    3. Converts it to the new format
    4. Saves it back
    
    Returns:
        True if migration succeeded, False otherwise
    """
    # Create backup of existing config
    if MAIN_CONFIG.exists():
        backup_path = CONFIG_DIR / f"config.backup.{int(time.time())}.json"
        try:
            shutil.copy2(MAIN_CONFIG, backup_path)
            logger.info(f"Created backup of config at {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup of config: {e}")
            return False
    
    try:
        # Read existing config
        if MAIN_CONFIG.exists():
            with open(MAIN_CONFIG, 'r') as f:
                old_config = json.load(f)
        else:
            old_config = {}
        
        # Create new registry
        registry = ConfigRegistry()
        
        # Migrate each module's configuration
        for module_name, config in old_config.items():
            if isinstance(config, dict):
                # Convert module config to new format
                restructured_config = _restructure_module_config(module_name, config)
                
                # Set the config in the registry
                registry.set_config_value(module_name, restructured_config, save=False)
        
        # Save the new config
        registry.save_config()
        
        logger.info("Configuration migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to migrate configuration: {e}")
        return False


def _restructure_module_config(module_name: str, old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Restructure a module's configuration to the new format.
    
    Args:
        module_name: Name of the module
        old_config: Old configuration dictionary
        
    Returns:
        New restructured configuration dictionary
    """
    # Apply module-specific transformations
    if module_name == "solana":
        # Example transformation for Solana module
        if "api_keys" in old_config:
            # Move API keys to the top level
            for key, value in old_config.pop("api_keys").items():
                old_config[key] = value
        
        # Add default settings if missing
        if "require_dragon" not in old_config:
            old_config["require_dragon"] = False
            
        if "max_connections" not in old_config:
            old_config["max_connections"] = 5
    
    elif module_name == "dragon":
        # Example transformation for Dragon module
        if "threads" in old_config:
            old_config["default_threads"] = old_config.pop("threads")
        
        # Add default settings if missing
        if "use_proxies" not in old_config:
            old_config["use_proxies"] = False
    
    elif module_name == "dune":
        # Example transformation for Dune module
        if "cache" in old_config:
            old_config["cache_results"] = old_config.pop("cache")
        
        # Add default settings if missing
        if "cache_timeout" not in old_config:
            old_config["cache_timeout"] = 3600
    
    # Return the restructured config
    return old_config


def migrate_env_vars() -> bool:
    """
    Migrate environment variables to the new format.
    
    This function:
    1. Identifies old-format environment variables
    2. Creates new-format variables
    3. Updates the .env file
    
    Returns:
        True if migration succeeded, False otherwise
    """
    from ..core.config import ENV_FILE
    
    try:
        # Map of old to new environment variable names
        env_var_mapping = {
            "HELIUS_KEY": "HELIUS_API_KEY",
            "DUNE_KEY": "DUNE_API_KEY",
            "TELEGRAM_TOKEN": "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_ID": "TELEGRAM_CHAT_ID"
        }
        
        # Load the .env file
        from dotenv import load_dotenv, set_key
        load_dotenv(ENV_FILE)
        
        # Check for old format variables and migrate them
        changes_made = False
        for old_name, new_name in env_var_mapping.items():
            old_value = os.environ.get(old_name)
            if old_value and not os.environ.get(new_name):
                # Set the new variable
                set_key(ENV_FILE, new_name, old_value)
                # Optionally comment out the old variable
                # set_key(ENV_FILE, old_name, f"# Migrated to {new_name}")
                changes_made = True
        
        if changes_made:
            logger.info("Environment variables migration completed successfully")
        else:
            logger.info("No environment variables needed migration")
            
        return True
    except Exception as e:
        logger.error(f"Failed to migrate environment variables: {e}")
        return False


def run_migrations() -> bool:
    """
    Run all migration utilities.
    
    Returns:
        True if all migrations succeeded, False if any failed
    """
    logger.info("Starting migrations...")
    
    # Migrate configuration
    config_success = migrate_config()
    if not config_success:
        logger.warning("Configuration migration failed")
    
    # Migrate environment variables
    env_success = migrate_env_vars()
    if not env_success:
        logger.warning("Environment variables migration failed")
    
    # Overall success
    success = config_success and env_success
    
    if success:
        logger.info("All migrations completed successfully")
    else:
        logger.warning("Some migrations failed")
    
    return success


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migrations
    run_migrations() 