"""
Log formatters for converting log entries to structured output.

This module provides formatters for different output formats, including text and JSON.
"""

import json
import datetime
from typing import Dict, Any, Protocol, Optional
from abc import ABC, abstractmethod


class LogFormatter(ABC):
    """Base abstract class for log formatters."""
    
    @abstractmethod
    def format(self, log_entry: Dict[str, Any]) -> str:
        """
        Format a log entry into a string representation.
        
        Args:
            log_entry: Dictionary containing log data
            
        Returns:
            Formatted string
        """
        pass


class JsonFormatter(LogFormatter):
    """
    Formatter for JSON output.
    
    This formatter converts log entries to a JSON string format, which is useful
    for structured logging and machine processing.
    """
    
    def __init__(self, indent: Optional[int] = None, ensure_ascii: bool = False):
        """
        Initialize the JSON formatter.
        
        Args:
            indent: Number of spaces for indentation (None for compact format)
            ensure_ascii: Whether to escape non-ASCII characters
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
    
    def format(self, log_entry: Dict[str, Any]) -> str:
        """
        Format a log entry as a JSON string.
        
        Args:
            log_entry: Dictionary containing log data
            
        Returns:
            JSON-formatted string
        """
        # Create a copy of the log entry to avoid modifying the original
        entry = log_entry.copy()
        
        # Convert timestamp to ISO format if it's a numeric value
        if 'context' in entry and 'timestamp' in entry['context']:
            timestamp = entry['context']['timestamp']
            if isinstance(timestamp, (int, float)):
                entry['context']['timestamp'] = datetime.datetime.fromtimestamp(
                    timestamp, tz=datetime.timezone.utc
                ).isoformat()
        
        # Serialize to JSON
        return json.dumps(entry, indent=self.indent, ensure_ascii=self.ensure_ascii)


class TextFormatter(LogFormatter):
    """
    Formatter for human-readable text output.
    
    This formatter converts log entries to a readable text format, which is useful
    for console output and log file readability.
    """
    
    def __init__(self, 
                 include_timestamp: bool = True,
                 include_level: bool = True,
                 include_module: bool = True,
                 include_trace_id: bool = False,
                 include_extra: bool = False):
        """
        Initialize the text formatter.
        
        Args:
            include_timestamp: Whether to include timestamp in output
            include_level: Whether to include log level in output
            include_module: Whether to include module name in output
            include_trace_id: Whether to include trace ID in output
            include_extra: Whether to include extra context data in output
        """
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_module = include_module
        self.include_trace_id = include_trace_id
        self.include_extra = include_extra
    
    def format(self, log_entry: Dict[str, Any]) -> str:
        """
        Format a log entry as a human-readable string.
        
        Args:
            log_entry: Dictionary containing log data
            
        Returns:
            Formatted string
        """
        parts = []
        
        # Add timestamp if enabled
        if self.include_timestamp and 'context' in log_entry and 'timestamp' in log_entry['context']:
            timestamp = log_entry['context']['timestamp']
            if isinstance(timestamp, (int, float)):
                time_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            else:
                time_str = str(timestamp)
            parts.append(f"[{time_str}]")
        
        # Add log level if enabled
        if self.include_level and 'level' in log_entry:
            level_str = log_entry['level'].ljust(8)  # Pad to 8 chars for alignment
            parts.append(f"[{level_str}]")
        
        # Add module name if enabled
        if self.include_module and 'context' in log_entry and 'module' in log_entry['context']:
            module = log_entry['context']['module']
            parts.append(f"[{module}]")
        
        # Add operation if available
        if 'context' in log_entry and 'operation' in log_entry['context']:
            operation = log_entry['context']['operation']
            parts.append(f"({operation})")
        
        # Add trace ID if enabled
        if self.include_trace_id and 'context' in log_entry and 'trace_id' in log_entry['context']:
            trace_id = log_entry['context']['trace_id']
            parts.append(f"[trace:{trace_id}]")
        
        # Add the message
        if 'message' in log_entry:
            parts.append(log_entry['message'])
        
        # Add extra context data if enabled
        if self.include_extra and 'context' in log_entry and 'extra' in log_entry['context']:
            extra_parts = []
            for key, value in log_entry['context'].get('extra', {}).items():
                if not isinstance(value, (dict, list)):  # Only include simple values
                    extra_parts.append(f"{key}={value}")
            
            if extra_parts:
                parts.append(f"[{', '.join(extra_parts)}]")
        
        return " ".join(parts) 