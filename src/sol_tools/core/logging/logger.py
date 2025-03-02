"""
Core logging functionality for Sol Tools.

This module defines the main logging classes including log levels and the central
logger implementation with context tracking.
"""

import threading
import uuid
import time
from enum import IntEnum
from typing import Dict, Any, List, Optional, Union, Set

from .config import LoggingConfig


class LogLevel(IntEnum):
    """Log level enumeration in order of increasing verbosity."""
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5
    
    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """Convert a string representation to a LogLevel enum value."""
        level_map = {
            "ERROR": cls.ERROR,
            "WARNING": cls.WARNING,
            "INFO": cls.INFO,
            "DEBUG": cls.DEBUG,
            "TRACE": cls.TRACE
        }
        
        normalized = level_str.upper()
        if normalized not in level_map:
            raise ValueError(f"Invalid log level: {level_str}. Valid levels are: {', '.join(level_map.keys())}")
        
        return level_map[normalized]
    
    def __str__(self) -> str:
        """Convert the enum value to a string representation."""
        return self.name


class LogContext:
    """Class to manage logging context information."""
    
    def __init__(self, 
                module: str, 
                operation: Optional[str] = None,
                trace_id: Optional[str] = None):
        """
        Initialize a new logging context.
        
        Args:
            module: The module generating the log
            operation: The current operation being performed
            trace_id: A unique ID for tracking related log messages across components
        """
        self.module = module
        self.operation = operation
        self.trace_id = trace_id or str(uuid.uuid4())
        self.timestamp = time.time()
        self.extra: Dict[str, Any] = {}
    
    def add(self, key: str, value: Any) -> "LogContext":
        """Add extra context information."""
        self.extra[key] = value
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the context to a dictionary for logging."""
        context_dict = {
            "module": self.module,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
        }
        
        if self.operation:
            context_dict["operation"] = self.operation
            
        # Add any extra context attributes
        context_dict.update(self.extra)
        
        return context_dict


class SolLogger:
    """
    The main logger class for Sol Tools.
    
    Features:
    - Multiple verbosity levels
    - Context tracking
    - Sensitive data masking
    - Multiple output handlers
    """
    
    # Class-level registry of loggers by name
    _loggers: Dict[str, "SolLogger"] = {}
    # Thread-local storage for context
    _context_store = threading.local()
    
    @classmethod
    def get_logger(cls, name: str, config: Optional[LoggingConfig] = None) -> "SolLogger":
        """
        Get or create a logger with the specified name.
        
        Args:
            name: The logger name, typically the module name
            config: Optional configuration for the logger
            
        Returns:
            A SolLogger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = SolLogger(name, config)
        return cls._loggers[name]
    
    def __init__(self, name: str, config: Optional[LoggingConfig] = None):
        """
        Initialize a new logger.
        
        Args:
            name: The logger name
            config: Optional configuration for the logger
        """
        self.name = name
        self.config = config or LoggingConfig()
        self.handlers = self.config.get_handlers()
        self.level = self.config.get_level()
        self.sensitive_patterns = self.config.get_sensitive_patterns()
        
    def set_context(self, module: str, operation: Optional[str] = None, trace_id: Optional[str] = None) -> LogContext:
        """
        Set the current context for this thread.
        
        Args:
            module: The module generating the log
            operation: The current operation being performed
            trace_id: A unique ID for tracking related log messages across components
            
        Returns:
            The created LogContext instance
        """
        context = LogContext(module, operation, trace_id)
        setattr(SolLogger._context_store, 'context', context)
        return context
    
    def get_context(self) -> Optional[LogContext]:
        """Get the current context for this thread."""
        return getattr(SolLogger._context_store, 'context', None)
    
    def clear_context(self) -> None:
        """Clear the current context for this thread."""
        if hasattr(SolLogger._context_store, 'context'):
            delattr(SolLogger._context_store, 'context')
    
    def mask_sensitive_data(self, message: str) -> str:
        """
        Mask sensitive data in log messages.
        
        Args:
            message: The message to process
            
        Returns:
            The message with sensitive data masked
        """
        if not self.sensitive_patterns:
            return message
            
        masked_message = message
        for pattern, mask_func in self.sensitive_patterns:
            masked_message = pattern.sub(mask_func, masked_message)
            
        return masked_message
    
    def _log(self, level: LogLevel, message: str, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a message at the specified level.
        
        Args:
            level: The log level
            message: The message to log
            additional_context: Additional context to include with this log entry
        """
        if level > self.level:
            return
            
        # Get the current context or create a default one
        context = self.get_context() or LogContext(self.name)
        
        # Add any additional context
        if additional_context:
            for key, value in additional_context.items():
                context.add(key, value)
        
        # Mask sensitive data
        masked_message = self.mask_sensitive_data(message)
        
        # Create the log entry
        log_entry = {
            "level": str(level),
            "message": masked_message,
            "context": context.to_dict()
        }
        
        # Send to all handlers
        for handler in self.handlers:
            handler.emit(log_entry)
    
    # Log level-specific methods
    
    def error(self, message: str, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error message."""
        self._log(LogLevel.ERROR, message, additional_context)
    
    def warning(self, message: str, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, additional_context)
    
    def info(self, message: str, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message."""
        self._log(LogLevel.INFO, message, additional_context)
    
    def debug(self, message: str, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, additional_context)
    
    def trace(self, message: str, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """Log a trace message."""
        self._log(LogLevel.TRACE, message, additional_context)
    
    # Context manager support
    
    def __enter__(self) -> "SolLogger":
        """Context manager entry - can be used to create a logging context scope."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleans up the logging context."""
        self.clear_context()
        return None 