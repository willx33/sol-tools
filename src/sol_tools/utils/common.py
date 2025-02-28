"""Common utility functions used across modules."""

import os
import time
import json
import shutil
import requests
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

from ..core.config import get_env_var, ROOT_DIR, DATA_DIR, CACHE_DIR

console = Console()


class ProgressManager:
    """Enhanced progress tracking system with ETA support."""
    
    def __init__(self, total_steps: int = 0, description: str = "Process Progress"):
        """Initialize the progress manager.
        
        Args:
            total_steps: Total number of steps in the process
            description: Description of the process
        """
        self.total_steps = total_steps
        self.completed_steps = 0
        self.current_description = description
        self.step_descriptions = {}
        self.step_progress = {}
        self.start_time = time.time()
        self.progress = None
        self.live = None
        self._task_id = None
        self.current_step = None
        self.step_start_time = None
    
    def initialize(self):
        """Initialize the progress display and start live tracking."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )
        self._task_id = self.progress.add_task(
            self.current_description, 
            total=self.total_steps,
            completed=self.completed_steps
        )
        self.live = Live(self.progress, refresh_per_second=4)
        self.live.start()
        return self
    
    def start_step(self, step_name: str, description: str = None):
        """Start tracking a new step."""
        if description is None:
            description = f"Processing {step_name}..."
        
        self.current_step = step_name
        self.step_descriptions[step_name] = description
        self.step_start_time = time.time()
        
        if self.progress:
            self.progress.update(self._task_id, description=description)
    
    def update_step(self, completed: float, total: float, description: str = None):
        """Update progress of the current step."""
        if self.current_step:
            self.step_progress[self.current_step] = (completed, total)
            
            if description:
                self.step_descriptions[self.current_step] = description
                if self.progress:
                    self.progress.update(self._task_id, description=description)
    
    def complete_step(self, description: str = None):
        """Mark the current step as completed."""
        if self.current_step:
            self.step_progress[self.current_step] = (1, 1)  # 100% completion
            
            if description:
                self.step_descriptions[self.current_step] = description
            
            self.completed_steps += 1
            if self.progress:
                self.progress.update(
                    self._task_id, 
                    completed=self.completed_steps,
                    description=f"[green]✓[/green] {self.step_descriptions.get(self.current_step, 'Step completed')}"
                )
    
    def complete(self, success: bool = True, message: str = None):
        """Finish the progress tracking."""
        if self.live:
            if success:
                final_msg = message or "Process completed successfully!"
                self.progress.update(self._task_id, description=f"[bold green]✓ {final_msg}[/bold green]")
            else:
                final_msg = message or "Process failed!"
                self.progress.update(self._task_id, description=f"[bold red]✗ {final_msg}[/bold red]")
            
            self.live.stop()
    
    def get_elapsed_time(self) -> float:
        """Get the total elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_step_elapsed_time(self) -> float:
        """Get the elapsed time for the current step in seconds."""
        if self.step_start_time:
            return time.time() - self.step_start_time
        return 0
    
    def get_eta(self) -> float:
        """Estimate time remaining in seconds."""
        if self.completed_steps == 0:
            return 0
        
        elapsed = self.get_elapsed_time()
        avg_time_per_step = elapsed / self.completed_steps
        remaining_steps = self.total_steps - self.completed_steps
        return avg_time_per_step * remaining_steps


class WorkflowResult:
    """Class to store workflow results and pass between steps."""
    
    def __init__(self):
        """Initialize the workflow result."""
        self.input_files = {}
        self.output_files = {}
        self.stats = {}
        self.success = True
        self.error_message = ""
        self.start_time = datetime.now()
        self.end_time = None
        self.raw_data = {}
        self.data_frames = {}
        self.progress_manager = None
    
    def add_input(self, key: str, file_path: str):
        """Add an input file to the workflow result."""
        self.input_files[key] = file_path
    
    def add_output(self, key: str, file_path: str):
        """Add an output file to the workflow result."""
        self.output_files[key] = file_path
    
    def add_stat(self, key: str, value: Any):
        """Add a statistic to the workflow result."""
        self.stats[key] = value
    
    def add_data(self, key: str, data: Any):
        """Add raw data to the result."""
        self.raw_data[key] = data
    
    def add_dataframe(self, key: str, df: pd.DataFrame):
        """Add a pandas DataFrame to the result."""
        self.data_frames[key] = df
    
    def set_error(self, message: str):
        """Set an error message and mark the workflow as failed."""
        self.success = False
        self.error_message = message
        if self.progress_manager:
            self.progress_manager.complete(success=False, message=message)
    
    def finalize(self):
        """Mark the workflow as finished and record end time."""
        self.end_time = datetime.now()
        if self.progress_manager:
            self.progress_manager.complete(
                success=self.success, 
                message="Workflow completed successfully!" if self.success else self.error_message
            )
    
    def duration(self) -> float:
        """Get workflow duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def set_progress_manager(self, manager: ProgressManager):
        """Set the progress manager for this workflow."""
        self.progress_manager = manager
    
    def print_summary(self):
        """Print a summary of the workflow results."""
        console.print("\n[bold cyan]Workflow Summary[/bold cyan]")
        
        if not self.success:
            console.print(f"[bold red]Workflow failed: {self.error_message}[/bold red]")
            return
        
        # Print completion time and duration
        duration_str = format_duration(self.duration())
        console.print(f"[green]Completed in: {duration_str}[/green]")
        
        # Print stats
        if self.stats:
            table = Table(title="Statistics", show_header=True)
            table.add_column("Metric")
            table.add_column("Value")
            
            for key, value in self.stats.items():
                table.add_row(key, str(value))
            
            console.print(table)
        
        # Print output files
        if self.output_files:
            console.print("[green]Output Files:[/green]")
            for key, file_path in self.output_files.items():
                console.print(f"  - {key}: [cyan]{file_path}[/cyan]")
    
    def export_results(self, export_format: str = 'json', output_path: str = None) -> str:
        """
        Export workflow results to a file.
        
        Args:
            export_format: 'json', 'csv', or 'excel'
            output_path: Path to save the file (optional)
            
        Returns:
            Path to the exported file
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Create exports directory in data
            exports_dir = Path(DATA_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(exports_dir / f"workflow_results_{timestamp}.{export_format}")
        
        # Create a summary dictionary
        summary = {
            "workflow": {
                "success": self.success,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": self.duration(),
                "error_message": self.error_message if not self.success else None
            },
            "statistics": self.stats,
            "input_files": self.input_files,
            "output_files": self.output_files
        }
        
        try:
            if export_format.lower() == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2)
            
            elif export_format.lower() == 'csv':
                # For CSV, we need to flatten the data structure
                rows = []
                
                # Add workflow info
                for key, value in summary["workflow"].items():
                    if value is not None:  # Skip None values
                        rows.append({"Category": "Workflow", "Key": key, "Value": str(value)})
                
                # Add statistics
                for key, value in summary["statistics"].items():
                    rows.append({"Category": "Statistics", "Key": key, "Value": str(value)})
                
                # Add input files
                for key, value in summary["input_files"].items():
                    rows.append({"Category": "Input Files", "Key": key, "Value": value})
                
                # Add output files
                for key, value in summary["output_files"].items():
                    rows.append({"Category": "Output Files", "Key": key, "Value": value})
                
                # Convert to DataFrame and save
                df = pd.DataFrame(rows)
                df.to_csv(output_path, index=False)
                
            elif export_format.lower() == 'excel':
                # Create a new Excel writer
                try:
                    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                        # Get the primary data frame if available
                        main_df = None
                        if self.data_frames:
                            # Use the first dataframe as the primary one
                            main_key = list(self.data_frames.keys())[0]
                            main_df = self.data_frames[main_key].copy()
                        
                        # If no dataframes, create an empty one
                        if main_df is None:
                            main_df = pd.DataFrame()
                        
                        # Add metadata as columns at the end
                        if not main_df.empty:
                            # Add workflow info
                            for key, value in summary["workflow"].items():
                                if value is not None:  # Skip None values
                                    main_df[f"meta_{key}"] = str(value)
                            
                            # Add statistics 
                            for key, value in summary["statistics"].items():
                                main_df[f"stat_{key}"] = str(value)
                                
                            # Add file info (in a compact format)
                            input_files_str = ", ".join([f"{k}: {v}" for k, v in summary["input_files"].items()])
                            output_files_str = ", ".join([f"{k}: {v}" for k, v in summary["output_files"].items()])
                            
                            if input_files_str:
                                main_df["meta_input_files"] = input_files_str
                            if output_files_str:
                                main_df["meta_output_files"] = output_files_str
                        else:
                            # If dataframe is empty, create rows with metadata
                            metadata_dict = {
                                **{f"workflow_{k}": str(v) for k, v in summary["workflow"].items() if v is not None},
                                **{f"stat_{k}": str(v) for k, v in summary["statistics"].items()},
                                "input_files": ", ".join([f"{k}: {v}" for k, v in summary["input_files"].items()]),
                                "output_files": ", ".join([f"{k}: {v}" for k, v in summary["output_files"].items()])
                            }
                            main_df = pd.DataFrame([metadata_dict])
                        
                        # Write to a single sheet
                        main_df.to_excel(writer, sheet_name='Results', index=False)
                except ImportError:
                    console.print("[yellow]Warning: Excel export requires openpyxl. Falling back to CSV export.[/yellow]")
                    # Fall back to CSV if openpyxl is not available
                    output_path = output_path.replace('.excel', '.csv')
                    return self.export_results('csv', output_path)
            
            else:
                console.print(f"[red]Unsupported export format: {export_format}[/red]")
                return None
            
            console.print(f"[green]Results exported to: {output_path}[/green]")
            return output_path
            
        except Exception as e:
            console.print(f"[red]Error exporting results: {str(e)}[/red]")
            return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{int(minutes)} minutes {int(seconds % 60)} seconds"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{int(hours)} hours {int(minutes)} minutes"


def clear_terminal():
    """Clear the terminal screen."""
    # Check if the OS is Windows or Unix-like
    os.system('cls' if os.name == 'nt' else 'clear')


def clear_cache():
    """Clear all cached data files."""
    try:
        # Clear cache directory
        if os.path.exists(CACHE_DIR):
            for file in os.listdir(CACHE_DIR):
                file_path = os.path.join(CACHE_DIR, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            console.print(f"[green]✓ Successfully cleared cache directory: {CACHE_DIR}[/green]")
        else:
            console.print(f"[yellow]Cache directory does not exist: {CACHE_DIR}[/yellow]")
            
        # Create cache directory if it doesn't exist
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")


def test_telegram():
    """Send a test message to the Telegram bot."""
    telegram_bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = get_env_var("TELEGRAM_CHAT_ID")
    
    if not telegram_bot_token or not telegram_chat_id:
        console.print("[red]❌ Telegram is not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file.[/red]")
        return
    
    try:
        message = "🤖 Sol Tools - Test message from CLI"
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        
        response = requests.post(url, json={
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "HTML"
        })
        
        if response.status_code == 200:
            console.print(f"[green]✅ Test message sent successfully to Telegram chat ID: {telegram_chat_id}[/green]")
        else:
            console.print(f"[red]❌ Failed to send message to Telegram: {response.text}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Error sending Telegram message: {e}[/red]")


def ensure_data_dir(module: str, subdir: Optional[str] = None) -> Path:
    """
    Ensure that a data directory exists for a module and return its path.
    
    Args:
        module: The module name (dragon, dune, sharp, solana)
        subdir: Optional subdirectory within the module
        
    Returns:
        Path object to the directory
    """
    if subdir:
        directory = DATA_DIR / module / subdir
    else:
        directory = DATA_DIR / module
        
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def check_proxy_file(proxy_path: Optional[str] = None) -> List[str]:
    """
    Check if proxy file exists and get proxies.
    
    Args:
        proxy_path: Optional path to proxy file, defaults to data/proxies.txt
        
    Returns:
        List of proxy strings or empty list if no proxies
    """
    if proxy_path is None:
        proxy_path = DATA_DIR / "proxies.txt"
        
    try:
        if os.path.exists(proxy_path):
            with open(proxy_path, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            return proxies
        else:
            console.print(f"[yellow]⚠️ Proxy file not found at {proxy_path}[/yellow]")
            return []
    except Exception as e:
        console.print(f"[red]❌ Error reading proxy file: {e}[/red]")
        return []