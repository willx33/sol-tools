"""
Configuration Registry System for Sol Tools.

This module provides a centralized configuration registry that loads configuration
from multiple sources with clear precedence, validates against schemas, and provides
versioning and migration capabilities.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
import jsonschema
from dotenv import load_dotenv

# Create module-specific logger
logger = logging.getLogger(__name__)

# Default paths
from .config import ROOT_DIR, CONFIG_DIR, ENV_FILE


@dataclass
class ConfigSchema:
    """Schema for module configuration with versioning support."""
    
    schema: Dict[str, Any]
    version: str
    migrations: Dict[str, Callable] = field(default_factory=dict)
    required_env_vars: List[str] = field(default_factory=list)


class ConfigRegistry:
    """
    Centralized configuration registry for Sol Tools.
    
    The registry loads configuration from multiple sources with clear precedence:
    1. Environment variables
    2. Local configuration files
    3. Default configuration values
    
    It also supports schema validation, versioning, and hot-reloading.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern for the registry."""
        if cls._instance is None:
            cls._instance = super(ConfigRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, test_mode: bool = False, config_dir: Optional[Path] = None):
        """
        Initialize the configuration registry.
        
        Args:
            test_mode: If True, use test configuration
            config_dir: Custom configuration directory (optional)
        """
        # Skip re-initialization of singleton
        if self._initialized:
            return
            
        self.logger = logging.getLogger(f"{__name__}.ConfigRegistry")
        self.test_mode = test_mode
        self.config_dir = config_dir or CONFIG_DIR
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Main configuration file paths
        self.main_config_file = self.config_dir / "config.json"
        self.test_config_file = self.config_dir / "test_config.json"
        
        # Initialize configuration storage
        self.config = {}
        self.module_schemas = {}
        self.module_configs = {}
        
        # Load environment variables
        load_dotenv(ENV_FILE)
        
        # Load configuration at initialization
        self._load_all_configs()
        
        self._initialized = True
        self.logger.debug("Configuration registry initialized")
    
    def _load_all_configs(self) -> None:
        """Load all configuration files and apply precedence rules."""
        # Load default configuration
        self.config = self._get_default_config()
        
        # Load main configuration file
        config_file = self.test_config_file if self.test_mode else self.main_config_file
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                self._update_nested_dict(self.config, file_config)
                self.logger.debug(f"Loaded configuration from {config_file}")
            except Exception as e:
                self.logger.error(f"Error loading configuration from {config_file}: {e}")
                
        # Apply environment variable overrides
        self._apply_env_var_overrides()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration values."""
        # Import here to avoid circular imports
        from .config import DEFAULT_CONFIG
        return DEFAULT_CONFIG.copy()
    
    def _update_nested_dict(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively update a nested dictionary with values from another dictionary."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def _apply_env_var_overrides(self) -> None:
        """Apply configuration overrides from environment variables."""
        env_prefix = "SOL_TOOLS_"
        
        for env_name, env_value in os.environ.items():
            if env_name.startswith(env_prefix):
                # Extract the configuration key path from the environment variable name
                config_path = env_name[len(env_prefix):].lower().split('__')
                
                # Convert string values to appropriate types
                if env_value.lower() == 'true':
                    typed_value = True
                elif env_value.lower() == 'false':
                    typed_value = False
                elif env_value.isdigit():
                    typed_value = int(env_value)
                elif env_value.replace('.', '', 1).isdigit():
                    typed_value = float(env_value)
                else:
                    typed_value = env_value
                
                # Apply the override
                self._set_config_value(config_path, typed_value)
                self.logger.debug(f"Applied environment override for {'.'.join(config_path)}")
    
    def _set_config_value(self, path: List[str], value: Any) -> None:
        """Set a value in the configuration dictionary using a path."""
        current = self.config
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path[-1]] = value
    
    def register_schema(
        self, 
        module_name: str, 
        schema: Dict[str, Any], 
        version: str = "1.0.0", 
        migrations: Optional[Dict[str, Callable]] = None,
        required_env_vars: Optional[List[str]] = None
    ) -> None:
        """
        Register a configuration schema for a module.
        
        Args:
            module_name: Name of the module
            schema: JSON schema for validating module configuration
            version: Schema version
            migrations: Optional dictionary mapping source versions to migration functions
            required_env_vars: List of environment variables required by the module
        """
        self.module_schemas[module_name] = ConfigSchema(
            schema=schema,
            version=version,
            migrations=migrations or {},
            required_env_vars=required_env_vars or []
        )
        self.logger.debug(f"Registered schema for module {module_name} (version {version})")
        
        # Initialize module configuration if not already present
        if module_name not in self.module_configs:
            self.module_configs[module_name] = {}
    
    def validate_module_config(self, module_name: str) -> bool:
        """
        Validate a module's configuration against its registered schema.
        
        Args:
            module_name: Name of the module
            
        Returns:
            True if validation succeeded, False otherwise
        """
        if module_name not in self.module_schemas:
            self.logger.warning(f"No schema registered for module {module_name}")
            return True
            
        schema = self.module_schemas[module_name].schema
        config = self.get_module_config(module_name)
        
        try:
            jsonschema.validate(instance=config, schema=schema)
            self.logger.debug(f"Configuration for module {module_name} is valid")
            return True
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error(f"Configuration for module {module_name} is invalid: {e}")
            return False
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """
        Get the configuration for a specific module.
        
        This method applies the precedence rules:
        1. Module-specific environment variables
        2. Main configuration file
        3. Default module configuration
        
        Args:
            module_name: Name of the module
            
        Returns:
            Module-specific configuration dictionary
        """
        # If module config is already loaded, return it
        if module_name in self.module_configs and self.module_configs[module_name]:
            return self.module_configs[module_name]
            
        # Start with the default/base configuration
        module_config = {}
        
        # Apply module-specific configuration from the main config
        if module_name in self.config:
            module_config = self.config[module_name].copy()
            
        # Store the module configuration for future use
        self.module_configs[module_name] = module_config
        
        return module_config
    
    def save_config(self) -> None:
        """Save the current configuration to the appropriate config file."""
        # Determine which file to save to
        config_file = self.test_config_file if self.test_mode else self.main_config_file
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.debug(f"Configuration saved to {config_file}")
        except Exception as e:
            self.logger.error(f"Error saving configuration to {config_file}: {e}")
    
    def reload_config(self) -> None:
        """Reload configuration from disk (hot-reload)."""
        self._load_all_configs()
        self.logger.debug("Configuration reloaded")
        
    def get_config_value(self, key_path: Union[str, List[str]], default: Any = None) -> Any:
        """
        Get a configuration value using a dot-notation path or list of keys.
        
        Args:
            key_path: Either a dot-notation string (e.g., 'module.setting') or a list of keys
            default: Default value to return if the key is not found
            
        Returns:
            The configuration value or the default if not found
        """
        if isinstance(key_path, str):
            key_path = key_path.split('.')
            
        current = self.config
        for key in key_path:
            if key in current:
                current = current[key]
            else:
                return default
                
        return current
    
    def set_config_value(self, key_path: Union[str, List[str]], value: Any, save: bool = True) -> None:
        """
        Set a configuration value using a dot-notation path or list of keys.
        
        Args:
            key_path: Either a dot-notation string (e.g., 'module.setting') or a list of keys
            value: Value to set
            save: If True, save the configuration to disk after setting the value
        """
        if isinstance(key_path, str):
            key_path = key_path.split('.')
            
        self._set_config_value(key_path, value)
        
        if save:
            self.save_config()
    
    def check_required_env_vars(self, module_name: str) -> Dict[str, bool]:
        """
        Check if all required environment variables for a module are set.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary mapping environment variable names to their availability status
        """
        result = {}
        
        if module_name in self.module_schemas:
            required_vars = self.module_schemas[module_name].required_env_vars
            for var in required_vars:
                result[var] = var in os.environ
            
        return result 