"""
Log handlers for different output destinations.

This module provides handlers for console, file, and remote log destinations,
with support for log rotation, filtering, and queuing.
"""

import os
import sys
import gzip
import queue
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, TextIO, Type, Union
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor

from .formatters import LogFormatter, TextFormatter
from .logger import LogLevel


class LogHandler(ABC):
    """Base abstract class for all log handlers."""
    
    def __init__(self, 
                 level: Union[str, int], 
                 formatter: LogFormatter):
        """
        Initialize the handler.
        
        Args:
            level: Minimum log level to process
            formatter: Formatter to use for log entries
        """
        if isinstance(level, str):
            from .logger import LogLevel
            self.level = LogLevel.from_string(level)
        else:
            self.level = level
        
        self.formatter = formatter
    
    def should_emit(self, log_entry: Dict[str, Any]) -> bool:
        """
        Determine if a log entry should be emitted based on level.
        
        Args:
            log_entry: The log entry to check
            
        Returns:
            True if the entry should be emitted, False otherwise
        """
        if 'level' not in log_entry:
            return False
            
        from .logger import LogLevel
        entry_level = LogLevel.from_string(log_entry['level'])
        return entry_level <= self.level
    
    def emit(self, log_entry: Dict[str, Any]) -> None:
        """
        Process and emit a log entry.
        
        Args:
            log_entry: The log entry to emit
        """
        if not self.should_emit(log_entry):
            return
        
        formatted_entry = self.formatter.format(log_entry)
        self._emit_formatted(formatted_entry, log_entry)
    
    @abstractmethod
    def _emit_formatted(self, formatted_entry: str, original_entry: Dict[str, Any]) -> None:
        """
        Emit a formatted log entry to the destination.
        
        Args:
            formatted_entry: The formatted log entry string
            original_entry: The original log entry dictionary
        """
        pass
    
    def flush(self) -> None:
        """Flush any buffered log entries."""
        pass
    
    def close(self) -> None:
        """Close the handler and release resources."""
        self.flush()


class ConsoleHandler(LogHandler):
    """Handler for emitting logs to the console."""
    
    def __init__(self, 
                 level: Union[str, int] = "INFO",
                 formatter: Optional[LogFormatter] = None,
                 use_stderr_for_error: bool = True,
                 colorize: bool = True):
        """
        Initialize the console handler.
        
        Args:
            level: Minimum log level to process
            formatter: Formatter to use for log entries (defaults to TextFormatter)
            use_stderr_for_error: Whether to output ERROR logs to stderr
            colorize: Whether to colorize the output based on log level
        """
        super().__init__(level, formatter or TextFormatter())
        self.use_stderr_for_error = use_stderr_for_error
        self.colorize = colorize
        
        # ANSI color codes
        self.colors = {
            "ERROR": "\033[31m",    # Red
            "WARNING": "\033[33m",  # Yellow
            "INFO": "\033[32m",     # Green
            "DEBUG": "\033[36m",    # Cyan
            "TRACE": "\033[35m",    # Magenta
            "RESET": "\033[0m",     # Reset
        }
    
    def _emit_formatted(self, formatted_entry: str, original_entry: Dict[str, Any]) -> None:
        """
        Emit a formatted log entry to the console.
        
        Args:
            formatted_entry: The formatted log entry string
            original_entry: The original log entry dictionary
        """
        # Determine output stream
        output_stream = sys.stderr if (
            self.use_stderr_for_error and 
            original_entry.get('level') == 'ERROR'
        ) else sys.stdout
        
        # Apply color if enabled
        if self.colorize and 'level' in original_entry:
            level = original_entry['level']
            if level in self.colors:
                formatted_entry = f"{self.colors[level]}{formatted_entry}{self.colors['RESET']}"
        
        # Write to the console
        print(formatted_entry, file=output_stream)


class FileHandler(LogHandler):
    """
    Handler for emitting logs to a file with rotation support.
    
    Features:
    - File rotation based on size
    - Compression of rotated logs
    - Multiple backup files
    """
    
    def __init__(self, 
                 level: Union[str, int] = "INFO",
                 formatter: Optional[LogFormatter] = None,
                 file_path: Union[str, Path] = "sol_tools.log",
                 max_size: int = 10 * 1024 * 1024,  # 10 MB
                 max_files: int = 5,
                 compress: bool = True,
                 immediate_flush: bool = True):
        """
        Initialize the file handler.
        
        Args:
            level: Minimum log level to process
            formatter: Formatter to use for log entries
            file_path: Path to the log file
            max_size: Maximum file size in bytes before rotation
            max_files: Maximum number of backup files to keep
            compress: Whether to compress rotated files
            immediate_flush: Whether to flush after each write
        """
        from .formatters import JsonFormatter
        super().__init__(level, formatter or JsonFormatter())
        
        self.file_path = Path(file_path)
        self.max_size = max_size
        self.max_files = max_files
        self.compress = compress
        self.immediate_flush = immediate_flush
        
        # Create parent directory if it doesn't exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open the file for writing
        self.file: Optional[TextIO] = None
        self._open_file()
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    def _open_file(self) -> None:
        """Open the log file for writing."""
        if self.file is not None:
            return
            
        try:
            self.file = open(self.file_path, 'a', encoding='utf-8')
        except Exception as e:
            sys.stderr.write(f"Failed to open log file {self.file_path}: {e}\n")
            self.file = None
    
    def _rotate_if_needed(self) -> None:
        """Rotate the log file if it exceeds the maximum size."""
        if self.file is None or not self.file_path.exists():
            return
            
        # Check if rotation is needed
        if self.file_path.stat().st_size < self.max_size:
            return
            
        # Close current file
        self.file.close()
        self.file = None
        
        # Shift existing backup files
        for i in range(self.max_files - 1, 0, -1):
            src = self.file_path.parent / f"{self.file_path.name}.{i}"
            if self.compress:
                src = src.with_suffix('.gz')
                
            dst = self.file_path.parent / f"{self.file_path.name}.{i+1}"
            if self.compress:
                dst = dst.with_suffix('.gz')
                
            if src.exists():
                try:
                    shutil.move(src, dst)
                except Exception:
                    pass
        
        # Rotate current file to backup
        backup_path = self.file_path.parent / f"{self.file_path.name}.1"
        if self.compress:
            try:
                with gzip.open(backup_path.with_suffix('.gz'), 'wb') as f_out:
                    with open(self.file_path, 'rb') as f_in:
                        shutil.copyfileobj(f_in, f_out)
            except Exception as e:
                sys.stderr.write(f"Failed to compress log file {self.file_path}: {e}\n")
                try:
                    shutil.copy2(self.file_path, backup_path)
                except Exception:
                    pass
        else:
            try:
                shutil.copy2(self.file_path, backup_path)
            except Exception:
                pass
        
        # Truncate the current file
        try:
            open(self.file_path, 'w').close()
        except Exception as e:
            sys.stderr.write(f"Failed to truncate log file {self.file_path}: {e}\n")
        
        # Reopen file
        self._open_file()
    
    def _emit_formatted(self, formatted_entry: str, original_entry: Dict[str, Any]) -> None:
        """
        Emit a formatted log entry to the file.
        
        Args:
            formatted_entry: The formatted log entry string
            original_entry: The original log entry dictionary
        """
        if self.file is None:
            self._open_file()
            if self.file is None:
                return  # Still couldn't open file
        
        with self.lock:
            # Check for rotation
            self._rotate_if_needed()
            
            # Write the log entry
            if self.file is not None:
                try:
                    self.file.write(formatted_entry + '\n')
                    if self.immediate_flush:
                        self.file.flush()
                except Exception as e:
                    sys.stderr.write(f"Failed to write to log file: {e}\n")
    
    def flush(self) -> None:
        """Flush the file buffer."""
        with self.lock:
            if self.file is not None:
                try:
                    self.file.flush()
                except Exception:
                    pass
    
    def close(self) -> None:
        """Close the file handler."""
        with self.lock:
            if self.file is not None:
                try:
                    self.file.close()
                except Exception:
                    pass
                self.file = None


class RemoteHandler(LogHandler):
    """
    Handler for sending logs to a remote HTTP endpoint.
    
    Features:
    - Batched sending to reduce API calls
    - Background processing thread
    - Retry logic for failed sends
    """
    
    def __init__(self, 
                 level: Union[str, int] = "INFO",
                 formatter: Optional[LogFormatter] = None,
                 url: str = "http://localhost:8000/logs",
                 auth_token: Optional[str] = None,
                 batch_size: int = 100,
                 flush_interval: float = 5.0,  # seconds
                 timeout: int = 30,  # seconds
                 max_retries: int = 3,
                 retry_backoff: float = 2.0):
        """
        Initialize the remote handler.
        
        Args:
            level: Minimum log level to process
            formatter: Formatter to use for log entries
            url: URL of the remote endpoint
            auth_token: Optional authentication token
            batch_size: Maximum number of logs to send in one request
            flush_interval: Maximum time between sends (seconds)
            timeout: HTTP request timeout (seconds)
            max_retries: Maximum number of retries for failed sends
            retry_backoff: Multiplier for increasing backoff time between retries
        """
        from .formatters import JsonFormatter
        super().__init__(level, formatter or JsonFormatter())
        
        self.url = url
        self.auth_token = auth_token
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # Queue for log entries
        self.queue: queue.Queue = queue.Queue()
        
        # Shutdown flag
        self.shutdown_flag = threading.Event()
        
        # Start the background thread
        self.thread = threading.Thread(target=self._background_sender, daemon=True)
        self.thread.start()
        
        # Thread pool for async sends
        self.thread_pool = ThreadPoolExecutor(max_workers=1)
    
    def _background_sender(self) -> None:
        """
        Background thread for sending batched logs.
        
        This method runs in a separate thread and periodically flushes the queue.
        """
        last_flush_time = time.time()
        
        while not self.shutdown_flag.is_set():
            current_time = time.time()
            
            # Flush if we have a full batch or it's time for a periodic flush
            if (self.queue.qsize() >= self.batch_size or 
                current_time - last_flush_time >= self.flush_interval):
                self._flush_queue()
                last_flush_time = current_time
            
            # Sleep a bit to avoid consuming too much CPU
            time.sleep(0.1)
    
    def _send_logs(self, logs: List[str]) -> bool:
        """
        Send logs to the remote endpoint.
        
        Args:
            logs: List of formatted log entries to send
            
        Returns:
            True if successful, False otherwise
        """
        headers = {
            'Content-Type': 'application/json',
        }
        
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        payload = {
            'logs': logs,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'sol_tools',
            'count': len(logs)
        }
        
        # Try to send with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code < 400:
                    return True
                    
                if response.status_code >= 500:  # Server error, retry
                    if attempt < self.max_retries:
                        time.sleep(attempt * self.retry_backoff)
                        continue
                
                # Client error or out of retries for server error
                sys.stderr.write(f"Failed to send logs to {self.url}: {response.status_code} {response.text}\n")
                return False
                
            except requests.RequestException as e:
                if attempt < self.max_retries:
                    time.sleep(attempt * self.retry_backoff)
                    continue
                
                sys.stderr.write(f"Error sending logs to {self.url}: {e}\n")
                return False
        
        return False
    
    def _flush_queue(self) -> None:
        """Flush the log queue by sending all entries."""
        if self.queue.empty():
            return
            
        # Collect logs from the queue
        logs = []
        while not self.queue.empty() and len(logs) < self.batch_size:
            try:
                log = self.queue.get_nowait()
                logs.append(log)
            except queue.Empty:
                break
        
        if not logs:
            return
            
        # Send the logs
        success = self._send_logs(logs)
        
        # If failed, put the logs back in the queue
        if not success:
            for log in logs:
                try:
                    self.queue.put(log)
                except queue.Full:
                    # If queue is full, we have to drop logs
                    sys.stderr.write(f"Remote log queue full, dropping log entry\n")
                    break
        else:
            # Mark tasks as done
            for _ in range(len(logs)):
                self.queue.task_done()
    
    def _emit_formatted(self, formatted_entry: str, original_entry: Dict[str, Any]) -> None:
        """
        Add a formatted log entry to the send queue.
        
        Args:
            formatted_entry: The formatted log entry string
            original_entry: The original log entry dictionary
        """
        try:
            # Try to add to the queue, but don't block if it's full
            self.queue.put_nowait(formatted_entry)
        except queue.Full:
            sys.stderr.write(f"Remote log queue full, dropping log entry\n")
    
    def flush(self) -> None:
        """
        Flush the log queue by sending all entries.
        
        This method blocks until all entries are sent.
        """
        future = self.thread_pool.submit(self._flush_queue)
        try:
            # Wait for the flush to complete, but with a timeout
            future.result(timeout=self.timeout + 1)
        except Exception:
            pass
    
    def close(self) -> None:
        """Close the remote handler."""
        self.shutdown_flag.set()
        self.flush()
        
        # Wait for the background thread to exit, but with a timeout
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        # Shutdown the thread pool
        self.thread_pool.shutdown(wait=False) 