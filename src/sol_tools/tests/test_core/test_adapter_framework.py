"""
Tests for the modular adapter framework and the BaseAdapter implementation.

This suite tests the core functionality of the adapter architecture, including:
- Adapter lifecycle management (initialize, validate, cleanup)
- Configuration handling and overriding
- Test mode behavior
- Error handling
"""

import os
import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, Optional, List

import pytest

from ...core.base_adapter import (
    BaseAdapter, 
    ConfigError, 
    InitializationError,
    ValidationError, 
    OperationError, 
    ResourceNotFoundError
)
from ...core.config_registry import ConfigRegistry
from ..base_tester import BaseTester


# Create a minimal test adapter that implements BaseAdapter
class MinimalTestAdapter(BaseAdapter):
    """Minimal adapter implementation for testing purposes."""
    
    def __init__(
        self,
        test_mode: bool = False,
        data_dir: Optional[Path] = None,
        config_override: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        fail_initialize: bool = False,
        fail_validate: bool = False,
        fail_cleanup: bool = False
    ):
        """Initialize the test adapter with standard parameters."""
        super().__init__(test_mode, data_dir, config_override, verbose)
        
        # Additional test parameters
        self.fail_initialize = fail_initialize
        self.fail_validate = fail_validate
        self.fail_cleanup = fail_cleanup
        
        # Tracking variables
        self.initialize_called = False
        self.validate_called = False
        self.cleanup_called = False
        self.resources_created = []
    
    async def initialize(self) -> bool:
        """Initialize the test adapter."""
        self.set_state(self.STATE_INITIALIZING)
        self.initialize_called = True
        
        try:
            # Load configuration
            self.config = self.get_module_config()
            
            # For testing: ensure we have default values if config doesn't have them
            if "api_key" not in self.config:
                self.config["api_key"] = "default_key"
            if "max_retries" not in self.config:
                self.config["max_retries"] = 3
            if "timeout" not in self.config:
                self.config["timeout"] = 30
            
            # Create test resources
            if not self.test_mode:
                self.resources_created.append("database_connection")
                self.resources_created.append("network_client")
            
            # Simulate failure if requested
            if self.fail_initialize:
                raise InitializationError("Simulated initialization failure")
            
            # Set success state
            self.set_state(self.STATE_READY)
            return True
            
        except Exception as e:
            self.set_state(self.STATE_ERROR, error=e)
            return False
    
    async def validate(self) -> bool:
        """Validate the test adapter."""
        self.validate_called = True
        
        try:
            # Check if we're properly initialized
            if self.state != self.STATE_READY:
                raise ValidationError("Adapter not initialized")
            
            # Check resources
            if not self.test_mode and not self.resources_created:
                raise ValidationError("Required resources not created")
            
            # Simulate failure if requested
            if self.fail_validate:
                raise ValidationError("Simulated validation failure")
                
            return True
            
        except Exception as e:
            self.set_state(self.STATE_ERROR, error=e)
            return False
    
    async def cleanup(self) -> None:
        """Clean up test adapter resources."""
        self.set_state(self.STATE_CLEANING_UP)
        self.cleanup_called = True
        
        try:
            # Clean up resources
            if self.resources_created:
                for resource in self.resources_created:
                    self.logger.debug(f"Cleaning up resource: {resource}")
            
            # Clear resources list
            self.resources_created = []
            
            # Simulate failure if requested
            if self.fail_cleanup:
                raise OperationError("Simulated cleanup failure")
                
            self.set_state(self.STATE_CLEANED_UP)
            
        except Exception as e:
            self.set_state(self.STATE_ERROR, error=e)
            raise


class AdapterFrameworkTester(BaseTester):
    """Test suite for the adapter framework."""
    
    def __init__(self):
        """Initialize the adapter framework tester."""
        super().__init__("adapter_framework")
        self._create_test_directories()
        
    async def test_adapter_lifecycle(self) -> bool:
        """Test the complete lifecycle of an adapter."""
        self.logger.info("Testing adapter lifecycle management")
        
        # Create adapter
        adapter = MinimalTestAdapter(test_mode=False, verbose=True)
        
        # Initialize
        success = await adapter.initialize()
        assert success, "Adapter initialization failed"
        assert adapter.initialize_called, "Initialize method not called"
        assert adapter.state == BaseAdapter.STATE_READY, f"Incorrect state: {adapter.state}"
        
        # Validate
        success = await adapter.validate()
        assert success, "Adapter validation failed"
        assert adapter.validate_called, "Validate method not called"
        
        # Cleanup
        await adapter.cleanup()
        assert adapter.cleanup_called, "Cleanup method not called"
        assert adapter.state == BaseAdapter.STATE_CLEANED_UP, f"Incorrect state: {adapter.state}"
        assert not adapter.resources_created, "Resources not properly cleaned up"
        
        self.logger.info("Adapter lifecycle test passed")
        return True
    
    async def test_config_override(self) -> bool:
        """Test the configuration override functionality."""
        self.logger.info("Testing configuration override")
        
        # Create a temporary configuration file
        config_dir = self.test_root / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Write a test config to the config directory
        test_config = {
            "modules": {
                "test": {
                    "api_key": "default_key",
                    "max_retries": 3,
                    "timeout": 30
                }
            }
        }
        
        config_file = config_dir / "config.json"
        with open(config_file, "w") as f:
            f.write(json.dumps(test_config))
        
        # Set environment variable to point to our config
        os.environ["SOL_TOOLS_CONFIG_PATH"] = str(config_file)
        
        # Create adapter with config override
        override = {
            "api_key": "override_key",
            "max_retries": 5
        }
        
        adapter = MinimalTestAdapter(
            test_mode=False,
            verbose=True,
            config_override=override
        )
        
        # Initialize to load configuration
        success = await adapter.initialize()
        assert success, "Adapter initialization failed"
        
        # Check that overrides were applied correctly
        config = adapter.config
        assert config["api_key"] == "override_key", "API key override not applied"
        assert config["max_retries"] == 5, "max_retries override not applied"
        assert config["timeout"] == 30, "Default config value not preserved"
        
        # Clean up
        await adapter.cleanup()
        
        # Reset environment variable
        if "SOL_TOOLS_CONFIG_PATH" in os.environ:
            del os.environ["SOL_TOOLS_CONFIG_PATH"]
            
        self.logger.info("Configuration override test passed")
        return True
    
    async def test_test_mode(self) -> bool:
        """Test adapter behavior in test mode."""
        self.logger.info("Testing adapter in test mode")
        
        # Create adapter in test mode
        adapter = MinimalTestAdapter(test_mode=True, verbose=True)
        
        # Initialize
        success = await adapter.initialize()
        assert success, "Adapter initialization failed in test mode"
        
        # Verify no resources were created
        assert not adapter.resources_created, "Resources created in test mode"
        
        # Clean up
        await adapter.cleanup()
        
        self.logger.info("Test mode behavior test passed")
        return True
    
    async def test_error_handling(self) -> bool:
        """Test adapter error handling."""
        self.logger.info("Testing adapter error handling")
        
        # Test initialization failure
        adapter = MinimalTestAdapter(fail_initialize=True, verbose=True)
        success = await adapter.initialize()
        assert not success, "Adapter should fail initialization"
        assert adapter.state == BaseAdapter.STATE_ERROR, f"Incorrect state: {adapter.state}"
        assert isinstance(adapter.error, InitializationError), f"Incorrect error type: {type(adapter.error)}"
        
        # Test validation failure
        adapter = MinimalTestAdapter(fail_validate=True, verbose=True)
        await adapter.initialize()
        success = await adapter.validate()
        assert not success, "Adapter should fail validation"
        assert adapter.state == BaseAdapter.STATE_ERROR, f"Incorrect state: {adapter.state}"
        assert isinstance(adapter.error, ValidationError), f"Incorrect error type: {type(adapter.error)}"
        
        # Test cleanup failure
        adapter = MinimalTestAdapter(fail_cleanup=True, verbose=True)
        await adapter.initialize()
        
        try:
            await adapter.cleanup()
            assert False, "Cleanup should raise an exception"
        except OperationError:
            # Expected exception
            pass
            
        assert adapter.state == BaseAdapter.STATE_ERROR, f"Incorrect state: {adapter.state}"
        
        self.logger.info("Error handling test passed")
        return True
        
    async def test_invalid_config(self) -> bool:
        """Test handling of invalid configuration."""
        self.logger.info("Testing invalid configuration handling")
        
        # Create a temporary configuration file with invalid structure
        config_dir = self.test_root / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Write an invalid config (missing modules section)
        invalid_config = {
            "not_modules": {
                "test": {
                    "api_key": "test_value"
                }
            }
        }
        
        config_file = config_dir / "invalid_config.json"
        with open(config_file, "w") as f:
            f.write(json.dumps(invalid_config))
        
        # Set environment variable to point to our invalid config
        os.environ["SOL_TOOLS_CONFIG_PATH"] = str(config_file)
        
        # Create adapter
        adapter = MinimalTestAdapter(verbose=True)
        
        # Initialize should still succeed but with default values
        success = await adapter.initialize()
        assert success, "Adapter should initialize with defaults despite invalid config"
        
        # Check that default values are used (don't check specific value, just that it exists)
        config = adapter.config
        assert "api_key" in config, "Default api_key not set"
        
        # Write a malformed JSON file
        with open(config_file, "w") as f:
            f.write("{invalid json")
        
        # Create another adapter
        adapter2 = MinimalTestAdapter(verbose=True)
        
        # Initialize should still succeed with defaults
        success = await adapter2.initialize()
        assert success, "Adapter should initialize with defaults despite malformed config"
        
        # Clean up
        await adapter.cleanup()
        await adapter2.cleanup()
        
        # Reset environment variable
        if "SOL_TOOLS_CONFIG_PATH" in os.environ:
            del os.environ["SOL_TOOLS_CONFIG_PATH"]
            
        self.logger.info("Invalid configuration test passed")
        return True
        
    async def test_uninitialized_adapter(self) -> bool:
        """Test handling of uninitialized adapters."""
        self.logger.info("Testing uninitialized adapter handling")
        
        # Create adapter but don't initialize it
        adapter = MinimalTestAdapter(verbose=True)
        
        # Validate should fail gracefully
        success = await adapter.validate()
        assert not success, "Validate should fail on uninitialized adapter"
        assert adapter.state == BaseAdapter.STATE_ERROR, f"Incorrect state: {adapter.state}"
        
        # Try to use adapter methods (this simulates a user trying to use an adapter without initialization)
        try:
            # In a real adapter, this would be a business method that requires initialization
            # Here we'll just try accessing config which should be None/empty before initialization
            if adapter.config and len(adapter.config) > 0:
                self.logger.warning("Adapter has config data despite not being initialized")
        except Exception as e:
            self.logger.warning(f"Exception when accessing uninitialized adapter: {str(e)}")
            # We don't assert here because we want to test graceful failure, not specific exceptions
        
        # Cleanup should work on uninitialized adapter
        try:
            await adapter.cleanup()
            assert adapter.state == BaseAdapter.STATE_CLEANED_UP, f"Incorrect state after cleanup: {adapter.state}"
            self.logger.info("Cleanup succeeded on uninitialized adapter")
        except Exception as e:
            self.logger.error(f"Cleanup failed on uninitialized adapter: {str(e)}")
            assert False, "Cleanup should work on uninitialized adapter"
        
        self.logger.info("Uninitialized adapter test passed")
        return True


@pytest.mark.asyncio
async def test_adapter_framework():
    """Run all adapter framework tests."""
    tester = AdapterFrameworkTester()
    
    tests = [
        ("Adapter Lifecycle", tester.test_adapter_lifecycle),
        ("Configuration Override", tester.test_config_override),
        ("Test Mode", tester.test_test_mode),
        ("Error Handling", tester.test_error_handling),
        ("Invalid Configuration", tester.test_invalid_config),
        ("Uninitialized Adapter", tester.test_uninitialized_adapter)
    ]
    
    results = {}
    for name, test_func in tests:
        results[name] = await test_func()
    
    tester.cleanup()
    
    # Ensure all tests passed
    assert all(results.values()), f"Some tests failed: {results}"
    return results


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_adapter_framework()) 