"""
Abstract base class for all Sol Tools module adapters.

This module defines the standardized interface that all adapter modules must implement,
providing a consistent pattern for initialization, lifecycle management, configuration,
and error handling across the Sol Tools ecosystem.
"""

import os
import abc
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Create a module-specific logger
logger = logging.getLogger(__name__)


class AdapterError(Exception):
    """Base exception class for all adapter-related errors."""
    pass


class ConfigError(AdapterError):
    """Exception raised for configuration-related errors."""
    pass


class InitializationError(AdapterError):
    """Exception raised when adapter initialization fails."""
    pass


class ValidationError(AdapterError):
    """Exception raised when validation fails."""
    pass


class OperationError(AdapterError):
    """Exception raised during adapter operations."""
    pass


class ResourceNotFoundError(AdapterError):
    """Exception raised when a required resource is not found."""
    pass


class BaseAdapter(abc.ABC):
    """
    Abstract base class that all module adapters must inherit from.
    
    This class defines a standardized interface for all adapters, including:
    - Common initialization parameters
    - Lifecycle methods (initialize, validate, cleanup)
    - Utility methods for configuration and state management
    - Standardized logging interface
    - Consistent error handling
    """
    
    # Define adapter states
    STATE_UNINITIALIZED = "uninitialized"
    STATE_INITIALIZING = "initializing"
    STATE_READY = "ready"
    STATE_ERROR = "error"
    STATE_CLEANING_UP = "cleaning_up"
    STATE_CLEANED_UP = "cleaned_up"
    
    def __init__(
        self,
        test_mode: bool = False,
        data_dir: Optional[Path] = None,
        config_override: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """
        Initialize the adapter with standard parameters.
        
        Args:
            test_mode: If True, operate in test mode without external API calls
            data_dir: Custom data directory path (optional)
            config_override: Override default configuration values (optional)
            verbose: Enable verbose logging if True
        """
        # Initialize logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.verbose = verbose
        
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
        
        # Set up adapter state
        self._state = self.STATE_UNINITIALIZED
        self._error = None
        
        # Store initialization parameters
        self.test_mode = test_mode
        self.data_dir = data_dir
        self.config_override = config_override or {}
        
        # Configuration will be loaded during initialization
        self.config = {}
        
        self.logger.debug(f"Adapter {self.__class__.__name__} created (test_mode={test_mode})")
    
    @property
    def state(self) -> str:
        """Get the current adapter state."""
        return self._state
    
    @property
    def error(self) -> Optional[Exception]:
        """Get the last error that occurred, if any."""
        return self._error
    
    def set_state(self, state: str, error: Optional[Exception] = None) -> None:
        """
        Update the adapter state.
        
        Args:
            state: New state to set
            error: Optional error to store when entering an error state
        """
        self._state = state
        if error is not None:
            self._error = error
            self.logger.error(f"Adapter entered error state: {error}")
        self.logger.debug(f"Adapter state changed to: {state}")
    
    def is_ready(self) -> bool:
        """Check if the adapter is initialized and ready for operations."""
        return self._state == self.STATE_READY
    
    def get_module_name(self) -> str:
        """Get the module name derived from the adapter class name."""
        class_name = self.__class__.__name__
        if class_name.endswith("Adapter"):
            return class_name[:-7].lower()
        return class_name.lower()
    
    def get_module_data_dir(self, data_type: Optional[str] = None) -> Path:
        """
        Get the module-specific data directory.
        
        Args:
            data_type: Optional subdirectory type (e.g., 'input', 'output', 'cache')
            
        Returns:
            Path to the module-specific data directory
        """
        from ..utils.common import ensure_data_dir
        
        module_name = self.get_module_name()
        return ensure_data_dir(module_name, data_type=data_type)
    
    def get_module_config(self) -> Dict[str, Any]:
        """
        Get the module-specific configuration.
        
        This method retrieves module-specific configuration from the global config,
        applies any overrides, and returns the result.
        
        Returns:
            Module-specific configuration dictionary
        """
        if not self.config:
            # Import here to avoid circular imports
            from .config_registry import ConfigRegistry
            
            module_name = self.get_module_name()
            registry = ConfigRegistry()
            self.config = registry.get_module_config(module_name)
            
            # Apply any overrides
            if self.config_override:
                self.config.update(self.config_override)
                
        return self.config
    
    @abc.abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the adapter and prepare it for use.
        
        This method should perform any necessary setup, including:
        - Loading configuration
        - Establishing connections
        - Validating inputs
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def validate(self) -> bool:
        """
        Validate that the adapter is properly configured and operational.
        
        This method should check that all required resources are available
        and that the adapter can perform its intended functions.
        
        Returns:
            True if validation succeeded, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources used by the adapter.
        
        This method should release any resources acquired during initialization
        and operation, such as file handles, network connections, or temporary files.
        """
        pass 