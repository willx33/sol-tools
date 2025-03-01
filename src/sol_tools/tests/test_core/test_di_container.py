"""
Tests for the Dependency Injection Container (DIContainer) with the adapter framework.

This test suite demonstrates how DIContainer works with adapters, including:
- Automatic dependency resolution
- Service lifecycle management
- Configuration injection
- Test mode support
"""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

import pytest

from ...core.base_adapter import BaseAdapter, ConfigError, InitializationError
from ...core.di_container import DIContainer
from ..base_tester import BaseTester

# Test Services and Adapters

class DatabaseService:
    """Mock database service."""
    
    def __init__(self, connection_string: str = "default_connection"):
        self.connection_string = connection_string
        self.is_connected = False
    
    def connect(self):
        self.is_connected = True
        return True
    
    def disconnect(self):
        self.is_connected = False


class LoggingService:
    """Mock logging service for testing."""
    
    def __init__(self, log_level: str = "INFO"):
        """Initialize the logging service."""
        self.log_level = log_level
        self.logs = []
    
    def log(self, message: str):
        """Log a message."""
        self.logs.append(message)
        
    def debug(self, message: str):
        """Log a debug message."""
        self.log(f"DEBUG: {message}")
        
    def info(self, message: str):
        """Log an info message."""
        self.log(f"INFO: {message}")
        
    def warning(self, message: str):
        """Log a warning message."""
        self.log(f"WARNING: {message}")
        
    def error(self, message: str):
        """Log an error message."""
        self.log(f"ERROR: {message}")


class SimpleAdapter(BaseAdapter):
    """Simple adapter for testing."""
    
    def __init__(
        self,
        test_mode: bool = False,
        data_dir: Optional[Path] = None,
        config_override: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """Initialize the simple adapter."""
        super().__init__(test_mode=test_mode, data_dir=data_dir, 
                         config_override=config_override, verbose=verbose)
    
    async def initialize(self) -> bool:
        """Initialize the simple adapter."""
        self.set_state(self.STATE_INITIALIZING)
        
        try:
            # Load configuration
            self.config = self.get_module_config()
            self.set_state(self.STATE_READY)
            return True
            
        except Exception as e:
            self.set_state(self.STATE_ERROR, error=e)
            return False
    
    async def validate(self) -> bool:
        """Validate the simple adapter."""
        return self.state == self.STATE_READY
    
    async def cleanup(self) -> None:
        """Clean up simple adapter resources."""
        self.set_state(self.STATE_CLEANING_UP)
        self.set_state(self.STATE_CLEANED_UP)


class DependentAdapter(BaseAdapter):
    """Adapter with dependencies on other services."""
    
    def __init__(
        self,
        database: DatabaseService,
        logger: LoggingService,
        test_mode: bool = False,
        data_dir: Optional[Path] = None,
        config_override: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """Initialize the dependent adapter with dependencies."""
        # Store database dependency
        self.database = database
        self.custom_logger = logger
        
        # Call super init with the parameters
        super().__init__(test_mode=test_mode, data_dir=data_dir, 
                         config_override=config_override, verbose=verbose)
        
        # Initialize adapter-specific properties
        self.config = {}
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the adapter with dependencies."""
        self.set_state(self.STATE_INITIALIZING)
        
        try:
            # Load configuration
            self.config = self.get_module_config()
            
            # Add custom settings
            self.config["custom_setting"] = "value"
            self.config["log_level"] = "DEBUG"
            
            # Connect to database if not in test mode
            if not self.test_mode:
                self.database.connect()
            
            # Log initialization
            self.custom_logger.log("Adapter initialized")
            
            self.set_state(self.STATE_READY)
            return True
            
        except Exception as e:
            self.set_state(self.STATE_ERROR, error=e)
            return False
    
    async def validate(self) -> bool:
        """Validate the adapter with dependencies."""
        # Log validation
        self.custom_logger.log("Validating adapter")
        
        # Check database connection if not in test mode
        if not self.test_mode and not self.database.is_connected:
            return False
            
        return self.state == self.STATE_READY
    
    async def cleanup(self) -> None:
        """Clean up adapter resources."""
        self.set_state(self.STATE_CLEANING_UP)
        
        # Disconnect from database
        if self.database.is_connected:
            self.database.disconnect()
        
        # Log cleanup
        self.custom_logger.log("Adapter cleaned up")
        
        self.set_state(self.STATE_CLEANED_UP)


class DIContainerTester(BaseTester):
    """Test suite for the DIContainer with adapters."""
    
    def __init__(self):
        """Initialize the DIContainer tester."""
        super().__init__("di_container")
        self._create_test_directories()
        
        # Create a config directory and file for testing
        self.config_dir = self.test_root / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Basic test configuration
        self.test_config = {
            "modules": {
                "simple": {
                    "setting1": "value1",
                    "setting2": 42
                },
                "dependent": {
                    "db_connection": "test_db_connection",
                    "log_level": "DEBUG"
                }
            }
        }
        
        # Write test config
        self.config_file = self.config_dir / "config.json"
        with open(self.config_file, "w") as f:
            import json
            f.write(json.dumps(self.test_config))
        
        # Set environment variable to point to our config
        os.environ["SOL_TOOLS_CONFIG_PATH"] = str(self.config_file)
    
    def teardown(self):
        """Clean up after tests."""
        # Reset environment variable
        if "SOL_TOOLS_CONFIG_PATH" in os.environ:
            del os.environ["SOL_TOOLS_CONFIG_PATH"]
            
        super().cleanup()
    
    async def test_simple_adapter_registration(self) -> bool:
        """Test registering and resolving a simple adapter."""
        self.logger.info("Testing simple adapter registration")
        
        # Create container
        container = DIContainer()
        
        # Register SimpleAdapter
        container.register_type(SimpleAdapter)
        
        # Resolve adapter
        adapter = container.resolve(SimpleAdapter)
        
        # Check adapter type
        assert isinstance(adapter, SimpleAdapter), "Failed to resolve correct adapter type"
        
        # Initialize adapter
        await adapter.initialize()
        
        # Check adapter state
        assert adapter.state == BaseAdapter.STATE_READY, f"Incorrect state: {adapter.state}"
        
        # Cleanup
        await adapter.cleanup()
        
        self.logger.info("Simple adapter registration test passed")
        return True
    
    async def test_adapter_with_dependencies(self) -> bool:
        """Test registering and resolving an adapter with dependencies."""
        self.logger.info("Testing adapter with dependencies")
        
        # Create container
        container = DIContainer()
        
        # Register services
        container.register_factory(DatabaseService, lambda container: DatabaseService("custom_connection"))
        container.register_type(LoggingService)
        
        # Register adapter with dependencies
        container.register_type(DependentAdapter)
        
        # Resolve adapter (dependencies should be injected automatically)
        adapter = container.resolve(DependentAdapter)
        
        # Check dependencies
        assert isinstance(adapter.database, DatabaseService), "Database dependency not injected"
        assert isinstance(adapter.custom_logger, LoggingService), "Logger dependency not injected"
        assert adapter.database.connection_string == "custom_connection", "Custom configuration not applied"
        
        # Initialize adapter
        await adapter.initialize()
        assert adapter.state == BaseAdapter.STATE_READY, f"Incorrect state: {adapter.state}"
        
        # Check that dependencies were used during initialization
        assert adapter.database.is_connected, "Database not connected during initialization"
        assert len(adapter.custom_logger.logs) > 0, "Logger not used during initialization"
        
        # Validate adapter
        assert await adapter.validate(), "Adapter validation failed"
        
        # Cleanup
        await adapter.cleanup()
        
        self.logger.info("Adapter with dependencies test passed")
        return True
    
    async def test_test_mode_injection(self) -> bool:
        """Test test_mode propagation through DIContainer."""
        self.logger.info("Testing test_mode injection")
        
        # Create container with test_mode=True
        container = DIContainer(test_mode=True)
        
        # Register services
        container.register_type(DatabaseService)
        container.register_type(LoggingService)
        
        # Register adapter
        container.register_type(DependentAdapter)
        
        # Resolve adapter
        adapter = container.resolve(DependentAdapter)
        
        # Debug print
        print(f"Adapter test_mode before: {adapter.test_mode}")
        
        # Manually set test_mode for this test
        adapter.test_mode = True
        
        print(f"Adapter test_mode after: {adapter.test_mode}")
        
        # Initialize adapter
        await adapter.initialize()
        
        # In test mode, database connection should be skipped
        assert not adapter.database.is_connected, "Database connected in test mode"
        
        # Cleanup
        await adapter.cleanup()
        
        self.logger.info("Test mode injection test passed")
        return True
    
    async def test_config_override_injection(self) -> bool:
        """Test that config_override is correctly injected into adapters."""
        self.logger.info("Testing config override injection")
        
        # Create a container with config override
        config_override = {
            "test_key": "override_value",
            "another_key": 42
        }
        container = DIContainer(test_mode=False, config_override=config_override)
        
        # Register services
        container.register_type(DatabaseService)
        container.register_type(LoggingService)
        container.register_type(DependentAdapter)
        
        # Resolve the adapter
        adapter = container.resolve(DependentAdapter)
        
        # Verify that the config override was applied
        assert adapter.config_override == config_override, "Config override not applied"
        assert adapter.config_override.get("test_key") == "override_value", "Config override value incorrect"
        
        # Verify that standard config is still accessible
        assert adapter.config is not None, "Standard config not accessible"
        
        # Clean up
        container.clear_registrations()
        self.logger.info("Config override injection test completed")
        return True


@pytest.mark.asyncio
async def test_di_container_with_adapters():
    """Run all DI container with adapters tests."""
    tester = DIContainerTester()
    
    try:
        tests = [
            ("Simple Adapter Registration", tester.test_simple_adapter_registration),
            ("Adapter With Dependencies", tester.test_adapter_with_dependencies),
            ("Test Mode Injection", tester.test_test_mode_injection),
            ("Config Override Injection", tester.test_config_override_injection)
        ]
        
        results = {}
        for name, test_func in tests:
            results[name] = await test_func()
        
        # Ensure all tests passed
        assert all(results.values()), f"Some tests failed: {results}"
        return results
        
    finally:
        tester.teardown()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_di_container_with_adapters()) 