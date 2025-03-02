"""
Logging configuration module.

This module provides configuration management for the logging system, including
handler registration, log level settings, and sensitive data pattern definitions.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Pattern, Callable, Type
from dataclasses import dataclass, field

from ...core.config import CACHE_DIR


@dataclass
class LoggingConfig:
    """Configuration for the logging system."""
    
    # Default log level
    level: str = "INFO"
    
    # Handler configurations
    console_enabled: bool = True
    console_format: str = "text"  # or "json"
    console_level: Optional[str] = None  # None means use the default level
    
    file_enabled: bool = False
    file_path: Optional[Path] = None
    file_format: str = "json"  # or "text"
    file_level: Optional[str] = None
    file_max_size: int = 10 * 1024 * 1024  # 10 MB
    file_max_files: int = 5
    file_compress: bool = True
    
    remote_enabled: bool = False
    remote_url: Optional[str] = None
    remote_auth_token: Optional[str] = None
    remote_level: Optional[str] = None
    remote_batch_size: int = 100
    remote_timeout: int = 30  # seconds
    
    # Filter settings
    context_filters: Dict[str, str] = field(default_factory=dict)
    
    # Handler class references (filled in at runtime)
    _handler_classes: Dict[str, Type] = field(default_factory=dict)
    _formatter_classes: Dict[str, Type] = field(default_factory=dict)
    
    # Compiled regex patterns for sensitive data
    _sensitive_patterns: List[Tuple[Pattern, Callable]] = field(default_factory=list)
    
    def __post_init__(self):
        """Process the configuration after initialization."""
        # If no file path is specified but file logging is enabled, use a default path
        if self.file_enabled and not self.file_path:
            log_dir = CACHE_DIR / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = log_dir / "sol_tools.log"
        
        # Initialize sensitive data patterns
        self._init_sensitive_patterns()
    
    def _init_sensitive_patterns(self):
        """Initialize patterns for masking sensitive data."""
        # API key pattern (alphanumeric string typically 32-64 chars)
        self._sensitive_patterns.append(
            (re.compile(r'(["\']?(?:api[_-]?key|api[_-]?token|access[_-]?token|auth[_-]?token)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9]{32,64})(["\']?)', re.IGNORECASE),
             lambda m: m.group(1) + "*" * 8 + m.group(3))
        )
        
        # JWT token pattern
        self._sensitive_patterns.append(
            (re.compile(r'(eyJ[a-zA-Z0-9_-]{5,}\.eyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,})'),
             lambda m: "*" * 12)
        )
        
        # Private key pattern (hex string)
        self._sensitive_patterns.append(
            (re.compile(r'(["\']?(?:private[_-]?key|secret[_-]?key)["\']?\s*[:=]\s*["\']?)([a-fA-F0-9]{32,64})(["\']?)', re.IGNORECASE),
             lambda m: m.group(1) + "*" * 8 + m.group(3))
        )
        
        # Password pattern
        self._sensitive_patterns.append(
            (re.compile(r'(["\']?(?:password|passwd)["\']?\s*[:=]\s*["\']?)([^"\'\s]{3,})(["\']?)', re.IGNORECASE),
             lambda m: m.group(1) + "*" * len(m.group(2)) + m.group(3))
        )
        
    def get_level(self) -> int:
        """Get the configured log level as an integer value."""
        from .logger import LogLevel
        return LogLevel.from_string(self.level)
    
    def get_handlers(self) -> List[Any]:
        """
        Get configured handlers based on the configuration.
        
        Returns:
            A list of initialized handler objects
        """
        handlers = []
        
        # Dynamically import handler and formatter classes to avoid circular imports
        if not self._handler_classes:
            from .handlers import ConsoleHandler, FileHandler, RemoteHandler
            self._handler_classes = {
                "console": ConsoleHandler,
                "file": FileHandler,
                "remote": RemoteHandler
            }
            
        if not self._formatter_classes:
            from .formatters import JsonFormatter, TextFormatter
            self._formatter_classes = {
                "json": JsonFormatter,
                "text": TextFormatter
            }
        
        # Create console handler if enabled
        if self.console_enabled:
            console_level = self.console_level or self.level
            formatter_class = self._formatter_classes.get(self.console_format, self._formatter_classes["text"])
            handlers.append(self._handler_classes["console"](
                level=console_level,
                formatter=formatter_class()
            ))
        
        # Create file handler if enabled and path is set
        if self.file_enabled and self.file_path:
            file_level = self.file_level or self.level
            formatter_class = self._formatter_classes.get(self.file_format, self._formatter_classes["json"])
            handlers.append(self._handler_classes["file"](
                level=file_level,
                formatter=formatter_class(),
                file_path=self.file_path,
                max_size=self.file_max_size,
                max_files=self.file_max_files,
                compress=self.file_compress
            ))
        
        # Create remote handler if enabled and URL is set
        if self.remote_enabled and self.remote_url:
            remote_level = self.remote_level or self.level
            # For remote logging, always use JSON
            formatter_class = self._formatter_classes["json"]
            handlers.append(self._handler_classes["remote"](
                level=remote_level,
                formatter=formatter_class(),
                url=self.remote_url,
                auth_token=self.remote_auth_token,
                batch_size=self.remote_batch_size,
                timeout=self.remote_timeout
            ))
        
        return handlers
    
    def get_sensitive_patterns(self) -> List[Tuple[Pattern, Callable]]:
        """Get the configured sensitive data patterns."""
        return self._sensitive_patterns
    
    def from_dict(self, config_dict: Dict[str, Any]) -> "LoggingConfig":
        """
        Update configuration from a dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            Self for method chaining
        """
        # Update simple attributes
        for key, value in config_dict.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, key, value)
        
        # Handle file_path specially
        if 'file_path' in config_dict and config_dict['file_path']:
            self.file_path = Path(config_dict['file_path'])
            
        # Re-initialize sensitive patterns
        self._init_sensitive_patterns()
        
        # Add any additional patterns from the config
        if 'sensitive_patterns' in config_dict:
            for pattern_str, replacement in config_dict['sensitive_patterns']:
                if callable(replacement):
                    repl_func = replacement
                else:
                    repl_func = lambda m: replacement
                self._sensitive_patterns.append((re.compile(pattern_str), repl_func))
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.
        
        Returns:
            Dictionary containing configuration values
        """
        result = {}
        
        # Include all public attributes
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, Path):
                    result[key] = str(value)
                else:
                    result[key] = value
                    
        return result 