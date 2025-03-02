"""
Log query interface for searching and filtering logs.

This module provides functionality for searching and filtering logs based on
various criteria like level, timestamp, and context attributes.
"""

import json
import re
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Union, Callable, Pattern, Iterator

from .logger import LogLevel


class LogQuery:
    """
    Query interface for searching and filtering logs.
    
    This class provides methods to search log files with various filters
    and return matching log entries.
    """
    
    def __init__(self, log_dir: Path):
        """
        Initialize a log query instance.
        
        Args:
            log_dir: Directory containing log files to search
        """
        self.log_dir = log_dir
        if not self.log_dir.exists():
            raise ValueError(f"Log directory {log_dir} does not exist")
    
    def find_log_files(self, pattern: str = "*.log*", include_rotated: bool = True) -> List[Path]:
        """
        Find log files matching the specified pattern.
        
        Args:
            pattern: Glob pattern for log files
            include_rotated: Whether to include rotated log files
            
        Returns:
            List of matching log file paths
        """
        files = list(self.log_dir.glob(pattern))
        
        if include_rotated:
            # Also include compressed log files
            files.extend(self.log_dir.glob("*.log.*.gz"))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return files
    
    def _read_log_file(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """
        Read and parse a log file, yielding log entries.
        
        Args:
            file_path: Path to the log file
            
        Yields:
            Parsed log entries as dictionaries
        """
        # Check if file is compressed
        is_compressed = file_path.suffix.lower() == '.gz'
        
        # Open file with appropriate method
        if is_compressed:
            open_func = gzip.open
            mode = 'rt'  # Text mode for gzip
        else:
            open_func = open
            mode = 'r'
        
        with open_func(file_path, mode, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON log entry
                    entry = json.loads(line)
                    if isinstance(entry, dict):
                        yield entry
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
    
    def search(self, 
               level: Optional[Union[str, LogLevel]] = None,
               min_timestamp: Optional[Union[datetime, float]] = None,
               max_timestamp: Optional[Union[datetime, float]] = None,
               message_pattern: Optional[Union[str, Pattern]] = None,
               context_filters: Optional[Dict[str, Any]] = None,
               limit: int = 1000,
               order: str = "desc") -> List[Dict[str, Any]]:
        """
        Search logs with the specified filters.
        
        Args:
            level: Minimum log level to include
            min_timestamp: Minimum timestamp for log entries
            max_timestamp: Maximum timestamp for log entries
            message_pattern: Regex pattern or string to match in messages
            context_filters: Context attributes to filter by (key-value pairs)
            limit: Maximum number of results to return
            order: Result order ("asc" or "desc" by timestamp)
            
        Returns:
            List of matching log entries
        """
        # Convert level to LogLevel enum if string
        min_level = None
        if level is not None:
            if isinstance(level, str):
                min_level = LogLevel.from_string(level)
            else:
                min_level = level
        
        # Convert timestamps to float if datetime objects
        min_time = None
        if min_timestamp is not None:
            if isinstance(min_timestamp, datetime):
                min_time = min_timestamp.timestamp()
            else:
                min_time = float(min_timestamp)
        
        max_time = None
        if max_timestamp is not None:
            if isinstance(max_timestamp, datetime):
                max_time = max_timestamp.timestamp()
            else:
                max_time = float(max_timestamp)
        
        # Compile regex pattern if string
        msg_regex = None
        if message_pattern is not None:
            if isinstance(message_pattern, str):
                msg_regex = re.compile(message_pattern)
            else:
                msg_regex = message_pattern
        
        # Find log files
        log_files = self.find_log_files()
        
        # Collect matching entries
        results = []
        for file_path in log_files:
            for entry in self._read_log_file(file_path):
                # Apply filters
                
                # Level filter
                if min_level is not None:
                    if 'level' not in entry:
                        continue
                    
                    entry_level = LogLevel.from_string(entry['level'])
                    if entry_level > min_level:
                        continue
                
                # Timestamp filters
                entry_time = None
                if 'context' in entry and 'timestamp' in entry['context']:
                    entry_time = entry['context']['timestamp']
                    
                    # Convert ISO format to timestamp if needed
                    if isinstance(entry_time, str):
                        try:
                            entry_time = datetime.fromisoformat(entry_time).timestamp()
                        except ValueError:
                            # If we can't parse it, just skip the timestamp filter
                            entry_time = None
                
                if entry_time is not None:
                    if min_time is not None and entry_time < min_time:
                        continue
                    if max_time is not None and entry_time > max_time:
                        continue
                
                # Message filter
                if msg_regex is not None:
                    if 'message' not in entry or not msg_regex.search(entry['message']):
                        continue
                
                # Context filters
                if context_filters:
                    skip = False
                    for key, value in context_filters.items():
                        # Check if key exists in nested context structure
                        if 'context' not in entry:
                            skip = True
                            break
                            
                        if key in entry['context']:
                            entry_value = entry['context'][key]
                        elif key in entry['context'].get('extra', {}):
                            entry_value = entry['context']['extra'][key]
                        else:
                            skip = True
                            break
                        
                        # Check if value matches (supports regex patterns)
                        if isinstance(value, Pattern):
                            if not isinstance(entry_value, str) or not value.search(entry_value):
                                skip = True
                                break
                        elif entry_value != value:
                            skip = True
                            break
                    
                    if skip:
                        continue
                
                # Add to results
                results.append(entry)
                
                # Check limit
                if len(results) >= limit:
                    break
            
            # Stop if we've reached the limit
            if len(results) >= limit:
                break
        
        # Sort results by timestamp
        if order.lower() == "asc":
            results.sort(key=lambda e: e.get('context', {}).get('timestamp', 0))
        else:
            results.sort(key=lambda e: e.get('context', {}).get('timestamp', 0), reverse=True)
        
        return results
    
    def get_recent_logs(self, 
                        hours: int = 24, 
                        level: Optional[str] = None, 
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent logs from the specified time period.
        
        Args:
            hours: Number of hours to look back
            level: Minimum log level to include
            limit: Maximum number of results to return
            
        Returns:
            List of matching log entries
        """
        # Calculate timestamp range
        now = datetime.now()
        min_timestamp = now - timedelta(hours=hours)
        
        return self.search(
            level=level,
            min_timestamp=min_timestamp,
            limit=limit,
            order="desc"
        )
    
    def get_errors(self, 
                   days: int = 7, 
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent error logs.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results to return
            
        Returns:
            List of error log entries
        """
        # Calculate timestamp range
        now = datetime.now()
        min_timestamp = now - timedelta(days=days)
        
        return self.search(
            level="ERROR",
            min_timestamp=min_timestamp,
            limit=limit,
            order="desc"
        )
    
    def get_logs_by_trace_id(self, trace_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get logs with the specified trace ID.
        
        Args:
            trace_id: Trace ID to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching log entries
        """
        context_filters = {'trace_id': trace_id}
        
        return self.search(
            context_filters=context_filters,
            limit=limit,
            order="asc"  # Chronological order for trace analysis
        )
    
    def get_logs_by_operation(self, 
                             operation: str, 
                             hours: int = 24,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get logs for a specific operation.
        
        Args:
            operation: Operation name to search for
            hours: Number of hours to look back
            limit: Maximum number of results to return
            
        Returns:
            List of matching log entries
        """
        # Calculate timestamp range
        now = datetime.now()
        min_timestamp = now - timedelta(hours=hours)
        
        context_filters = {'operation': operation}
        
        return self.search(
            min_timestamp=min_timestamp,
            context_filters=context_filters,
            limit=limit,
            order="desc"
        ) 