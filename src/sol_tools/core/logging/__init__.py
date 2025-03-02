"""
Advanced Logging Infrastructure for Sol Tools.

This module provides a structured, configurable logging system with support for
multiple verbosity levels, context information, and multiple output destinations.
"""

from .logger import SolLogger, LogLevel
from .handlers import ConsoleHandler, FileHandler, RemoteHandler
from .formatters import JsonFormatter, TextFormatter
from .query import LogQuery
from .config import LoggingConfig

__all__ = [
    "SolLogger",
    "LogLevel",
    "ConsoleHandler",
    "FileHandler",
    "RemoteHandler",
    "JsonFormatter",
    "TextFormatter",
    "LogQuery",
    "LoggingConfig",
    "configure_logging",
    "get_logger"
]

# Global logging configuration
_logging_config = LoggingConfig()

def configure_logging(config: LoggingConfig) -> None:
    """Configure the global logging system with the provided configuration."""
    global _logging_config
    _logging_config = config
    

def get_logger(name: str) -> SolLogger:
    """Get a logger instance with the specified name, using the global configuration."""
    return SolLogger.get_logger(name, _logging_config) 