"""
Dependency Injection Container for Sol Tools.

This module provides a container for managing module dependencies, enabling
automatic resolution, lifecycle management, and testing support.
"""

import inspect
import logging
from typing import Dict, Any, Optional, List, Type, Set, Callable, TypeVar, Union, cast
from enum import Enum

# Create module-specific logger
logger = logging.getLogger(__name__)

# Generic type for dependency classes
T = TypeVar('T')


class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected."""
    pass


class DependencyNotFoundError(Exception):
    """Exception raised when a required dependency is not found."""
    pass


class DependencyLifecycle(str, Enum):
    """Lifecycle options for dependencies in the container."""
    
    SINGLETON = "singleton"  # One instance shared by all consumers
    TRANSIENT = "transient"  # New instance created for each consumer
    SCOPED = "scoped"        # One instance per scope (not fully implemented yet)


class DependencyRegistration:
    """Registration information for a dependency in the container."""
    
    def __init__(
        self, 
        interface_type: Type,
        implementation_type: Optional[Type] = None,
        instance: Optional[Any] = None,
        factory: Optional[Callable[..., Any]] = None,
        lifecycle: DependencyLifecycle = DependencyLifecycle.SINGLETON,
        is_mock: bool = False,
        dependencies: Optional[Dict[str, Type]] = None
    ):
        """
        Initialize a dependency registration.
        
        Args:
            interface_type: Type that will be requested from the container
            implementation_type: Concrete type to instantiate (optional)
            instance: Pre-created instance to return (optional)
            factory: Factory function for creating instances (optional)
            lifecycle: Lifecycle pattern for the dependency
            is_mock: Whether this is a mock registration for testing
            dependencies: Dictionary of named dependencies required by this type
        """
        self.interface_type = interface_type
        self.implementation_type = implementation_type or interface_type
        self.instance = instance
        self.factory = factory
        self.lifecycle = lifecycle
        self.is_mock = is_mock
        self.dependencies = dependencies or {}
        
        # Validate registration
        if instance is not None and factory is not None:
            raise ValueError("Cannot specify both instance and factory")
            
        if instance is not None and lifecycle != DependencyLifecycle.SINGLETON:
            raise ValueError("Pre-created instances must use SINGLETON lifecycle")


class DIContainer:
    """
    Dependency Injection Container for managing module dependencies.
    
    The container supports:
    - Registration of interfaces, implementations, and instances
    - Automatic dependency resolution
    - Lifecycle management (singleton, transient)
    - Mock registration for testing
    - Circular dependency detection
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern for the container."""
        if cls._instance is None:
            cls._instance = super(DIContainer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, test_mode: bool = False, config_override: Optional[Dict[str, Any]] = None):
        """
        Initialize the dependency injection container.
        
        Args:
            test_mode: If True, operate in test mode with mock dependencies
            config_override: Optional configuration overrides to apply to adapters
        """
        # Always update test_mode and config_override, even if already initialized
        self.test_mode = test_mode
        self.config_override = config_override or {}
        
        # Skip full re-initialization of singleton if already initialized
        if getattr(self, '_initialized', False):
            self.logger.debug(f"Updating existing container with test_mode={test_mode}, config_override={self.config_override}")
            return
        
        self.logger = logging.getLogger(f"{__name__}.DIContainer")
        
        # Initialize registrations
        self.registrations: Dict[Type, DependencyRegistration] = {}
        
        # Initialize resolution tracking for circular dependency detection
        self.resolution_stack: List[Type] = []
        
        # Register test_mode as a singleton
        self.register_instance(bool, test_mode)
        
        self._initialized = True
        self.logger.debug("Dependency injection container initialized")
    
    def register_type(
        self, 
        interface_type: Type[T], 
        implementation_type: Optional[Type] = None,
        lifecycle: DependencyLifecycle = DependencyLifecycle.SINGLETON,
        dependencies: Optional[Dict[str, Type]] = None
    ) -> None:
        """
        Register a type with the container.
        
        Args:
            interface_type: Type that will be requested from the container
            implementation_type: Concrete type to instantiate (optional)
            lifecycle: Lifecycle pattern for the dependency
            dependencies: Dictionary of named dependencies required by this type
        """
        if implementation_type is None:
            implementation_type = interface_type
            
        if dependencies is None:
            # Auto-detect dependencies from constructor parameters
            dependencies = self._detect_dependencies(implementation_type)
        
        self.registrations[interface_type] = DependencyRegistration(
            interface_type=interface_type,
            implementation_type=implementation_type,
            lifecycle=lifecycle,
            dependencies=dependencies
        )
        
        self.logger.debug(f"Registered type {interface_type.__name__}")
    
    def register_instance(self, interface_type: Type[T], instance: T) -> None:
        """
        Register a pre-created instance with the container.
        
        Args:
            interface_type: Type that will be requested from the container
            instance: Pre-created instance to return
        """
        self.registrations[interface_type] = DependencyRegistration(
            interface_type=interface_type,
            instance=instance,
            lifecycle=DependencyLifecycle.SINGLETON
        )
        
        self.logger.debug(f"Registered instance of {interface_type.__name__}")
    
    def register_factory(
        self, 
        interface_type: Type[T], 
        factory: Callable[..., T],
        lifecycle: DependencyLifecycle = DependencyLifecycle.SINGLETON
    ) -> None:
        """
        Register a factory function with the container.
        
        Args:
            interface_type: Type that will be requested from the container
            factory: Factory function for creating instances
            lifecycle: Lifecycle pattern for the dependency
        """
        self.registrations[interface_type] = DependencyRegistration(
            interface_type=interface_type,
            factory=factory,
            lifecycle=lifecycle
        )
        
        self.logger.debug(f"Registered factory for {interface_type.__name__}")
    
    def register_mock(self, interface_type: Type[T], mock_instance: T) -> None:
        """
        Register a mock implementation for testing.
        
        Args:
            interface_type: Type to mock in the container
            mock_instance: Mock instance to use
        """
        self.registrations[interface_type] = DependencyRegistration(
            interface_type=interface_type,
            instance=mock_instance,
            is_mock=True,
            lifecycle=DependencyLifecycle.SINGLETON
        )
        
        self.logger.debug(f"Registered mock for {interface_type.__name__}")
    
    def resolve(self, interface_type: Type[T]) -> T:
        """
        Resolve a dependency from the container.
        
        Args:
            interface_type: Type to resolve
            
        Returns:
            Instance of the requested type
            
        Raises:
            DependencyNotFoundError: If the dependency is not registered
            CircularDependencyError: If a circular dependency is detected
        """
        # Check for circular dependencies
        if interface_type in self.resolution_stack:
            path_str = " -> ".join([t.__name__ for t in self.resolution_stack + [interface_type]])
            raise CircularDependencyError(f"Circular dependency detected: {path_str}")
        
        # Check if the type is registered
        if interface_type not in self.registrations:
            # Check if testing and a mock implementation is required
            if self.test_mode:
                # Try to create a simple mock automatically
                self.logger.warning(f"Auto-creating mock for {interface_type.__name__} in test mode")
                mock_instance = type(f"Mock{interface_type.__name__}", (), {})()
                self.register_mock(interface_type, mock_instance)
            else:
                raise DependencyNotFoundError(f"No registration found for {interface_type.__name__}")
        
        registration = self.registrations[interface_type]
        
        # If it's a singleton and we already have an instance, return it
        if (registration.lifecycle == DependencyLifecycle.SINGLETON and 
                registration.instance is not None):
            return cast(T, registration.instance)
        
        # Create a new instance
        self.resolution_stack.append(interface_type)
        
        try:
            instance = self._create_instance(registration)
        finally:
            self.resolution_stack.pop()
        
        # Store the instance if it's a singleton
        if registration.lifecycle == DependencyLifecycle.SINGLETON:
            registration.instance = instance
        
        return cast(T, instance)
    
    def _create_instance(self, registration: DependencyRegistration) -> Any:
        """Create an instance based on the registration information."""
        if registration.factory is not None:
            # Use factory function
            return registration.factory(self)
        
        # Resolve dependencies
        kwargs = {}
        for param_name, param_type in registration.dependencies.items():
            try:
                kwargs[param_name] = self.resolve(param_type)
            except DependencyNotFoundError as e:
                self.logger.warning(f"Could not resolve dependency {param_name} of type {param_type.__name__}: {e}")
                # Continue without this dependency - let the implementation handle missing deps
        
        # Check if this is an adapter and pass test_mode and config_override if it is
        from sol_tools.core.base_adapter import BaseAdapter
        is_adapter = False
        try:
            is_adapter = issubclass(registration.implementation_type, BaseAdapter)
        except TypeError:
            # Not a class or doesn't support issubclass
            pass
            
        if is_adapter:
            # Always pass test_mode to adapters from the container's test_mode
            # Make sure it's explicitly set in kwargs to override any default value
            kwargs['test_mode'] = self.test_mode
            
            # Always pass config_override to adapters, even if it's empty
            # Use a copy to avoid sharing the same instance which could cause issues
            kwargs['config_override'] = self.config_override.copy() if self.config_override else {}
                
            self.logger.debug(f"Creating adapter {registration.implementation_type.__name__} with test_mode={self.test_mode}, config_override={self.config_override}")
        
        # Create the instance
        instance = registration.implementation_type(**kwargs)
        
        # Double-check that test_mode and config_override are properly set for adapter instances
        if isinstance(instance, BaseAdapter):
            # Ensure test_mode is correctly set to the container's test_mode
            if instance.test_mode != self.test_mode:
                self.logger.warning(f"Correcting test_mode for {registration.implementation_type.__name__} from {instance.test_mode} to {self.test_mode}")
                instance.test_mode = self.test_mode
            
            # Ensure config_override is correctly set
            if self.config_override is not None and instance.config_override != self.config_override:
                self.logger.warning(f"Correcting config_override for {registration.implementation_type.__name__}")
                instance.config_override = self.config_override.copy()  # Use copy to ensure we don't have reference issues
        
        return instance
    
    def _detect_dependencies(self, implementation_type: Type) -> Dict[str, Type]:
        """Detect dependencies from constructor parameter annotations."""
        dependencies = {}
        
        # Get constructor signature
        try:
            signature = inspect.signature(implementation_type.__init__)
            
            # Skip 'self' parameter and get annotated parameters
            for param_name, param in list(signature.parameters.items())[1:]:
                if param.annotation != inspect.Parameter.empty:
                    dependencies[param_name] = param.annotation
        except (ValueError, TypeError) as e:
            # If we can't get the signature, just return an empty dict
            self.logger.warning(f"Could not detect dependencies for {implementation_type.__name__}: {e}")
        
        return dependencies
    
    def clear_registrations(self) -> None:
        """Clear all registrations from the container."""
        self.registrations.clear()
        self.logger.debug("Cleared all registrations")
    
    def clear_instances(self) -> None:
        """Clear all singleton instances while keeping registrations."""
        for registration in self.registrations.values():
            registration.instance = None
        self.logger.debug("Cleared all instances")
        
    def resolve_all(self, base_type: Type[T]) -> List[T]:
        """
        Resolve all implementations of a base type.
        
        Args:
            base_type: Base type to find implementations for
            
        Returns:
            List of instances of types that implement or extend the base type
        """
        result = []
        
        for reg_type, registration in self.registrations.items():
            # Check if this type is or inherits from the base type
            try:
                if issubclass(registration.implementation_type, base_type):
                    result.append(self.resolve(reg_type))
            except TypeError:
                # Ignore types that don't support issubclass
                pass
        
        return result
        
    def is_registered(self, interface_type: Type) -> bool:
        """
        Check if a type is registered with the container.
        
        Args:
            interface_type: Type to check
            
        Returns:
            True if the type is registered, False otherwise
        """
        return interface_type in self.registrations 