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

# Import inquirer classes
try:
    from inquirer import Text as InquirerText
    from inquirer.render.console import ConsoleRender
    import inquirer
    import readchar
    import time
    import sys
    from blessed import Terminal
    
    # Create a simple but effective direct input implementation
    class NoTruncationText(InquirerText):
        """
        A simplified Text input that properly handles paste operations.
        
        This implementation bypasses the inquirer rendering engine completely
        and directly manages terminal input to prevent duplicate prompts during paste.
        """
        def __init__(self, *args, **kwargs):
            # Initialize parent class
            super().__init__(*args, **kwargs)
            
            # Set up validation
            self._validate_func = kwargs.get('validate')

        def execute(self):
            """
            Simple direct input method that completely avoids the paste issue
            by handling input directly without using the inquirer rendering engine.
            """
            # Get the prompt message (no truncation)
            message = self.message
            
            # Get the default value
            default = self.default or ""
            default_display = f" [{default}]" if default else ""
            
            # Display the prompt once and directly capture input
            user_input = input(f"{message}{default_display}: ")
            
            # Apply default if user didn't enter anything
            if not user_input and default:
                user_input = default
                
            # Run validation if provided
            if self._validate_func and callable(self._validate_func):
                # Only attempt validation if we have a value
                if user_input:
                    try:
                        is_valid = self._validate_func(None, user_input)
                        if not is_valid:
                            print(f"Invalid input. Please try again.")
                            return self.execute()  # Recursive call to retry
                    except Exception as e:
                        print(f"Validation error: {e}")
                        return self.execute()  # Recursive call to retry
                
            # Store the value and return
            self.current_value = user_input
            return user_input
            
        def get_message(self):
            """Get the prompt message without truncation"""
            return self.message

    # Create a function to prompt the user, bypassing inquirer's rendering
    def prompt_user(questions):
        """
        Alternative to inquirer.prompt that prevents the paste issues.
        Use this instead of inquirer.prompt when working with text inputs.
        """
        result = {}
        
        for question in questions:
            if isinstance(question, NoTruncationText):
                # Handle our custom text input directly
                result[question.name] = question.execute()
            else:
                # Pass other question types to inquirer
                temp_result = inquirer.prompt([question])
                if temp_result:
                    result.update(temp_result)
        
        return result
        
except ImportError:
    # Fallback if inquirer isn't available
    class NoTruncationText:
        """Fallback if inquirer isn't available."""
        pass
        
    def prompt_user(questions):
        """Fallback prompt function if inquirer isn't available."""
        result = {}
        for question in questions:
            result[question.name] = input(f"{question.message}: ")
        return result


def parse_input_addresses(input_value: str) -> List[str]:
    """
    Parse space-separated or line-separated addresses into a list.
    
    Args:
        input_value: String containing addresses separated by spaces or newlines
        
    Returns:
        List of individual addresses
    """
    if not input_value:
        return []
    
    # Handle both space-separated and newline-separated inputs
    # First split by newlines, then by spaces, and flatten the result
    addresses = []
    for line in input_value.strip().split('\n'):
        addresses.extend(line.strip().split())
    
    return [addr.strip() for addr in addresses if addr.strip()]


def validate_addresses(addresses: List[str], validator_func: Callable[[str], bool]) -> Tuple[List[str], List[str]]:
    """
    Validate a list of addresses using the provided validator function.
    
    Args:
        addresses: List of addresses to validate
        validator_func: Function that validates a single address
        
    Returns:
        Tuple of (valid_addresses, invalid_addresses)
    """
    valid = []
    invalid = []
    
    for addr in addresses:
        if validator_func(addr):
            valid.append(addr)
        else:
            invalid.append(addr)
            
    return valid, invalid


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
        
        # Ensure parent directory exists before writing
        ensure_file_dir(output_path)
        
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


def ensure_data_dir(module: str, subdir: Optional[str] = None, data_type: str = "output") -> Path:
    """
    Ensure that a data directory exists for a module and return its path.
    
    Args:
        module: The module name (dragon, dune, sharp, solana, gmgn)
        subdir: Optional subdirectory within the module
        data_type: Type of data directory ("input" or "output")
        
    Returns:
        Path object to the directory
    """
    from ..core.config import INPUT_DATA_DIR, OUTPUT_DATA_DIR
    
    if data_type.lower() == "input":
        base_dir = INPUT_DATA_DIR
    else:  # Default to output for any other value
        base_dir = OUTPUT_DATA_DIR
    
    # Handle a case where module might begin with "input-data/" or "output-data/" prefix
    if module.startswith("input-data/"):
        module = module.replace("input-data/", "")
        base_dir = INPUT_DATA_DIR
    elif module.startswith("output-data/"):
        module = module.replace("output-data/", "")
        base_dir = OUTPUT_DATA_DIR
    
    if subdir:
        directory = base_dir / module / subdir
    else:
        directory = base_dir / module
        
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_file_dir(file_path: Union[str, Path]) -> Path:
    """
    Ensure that the parent directory of a file exists.
    Creates all parent directories if they don't exist.
    
    Args:
        file_path: Path to the file (can be either a string or Path object)
        
    Returns:
        Path object to the file's parent directory
    """
    path = Path(file_path)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_unified_data(module: str, 
                    data_items: List[Dict[str, Any]], 
                    filename_prefix: str,
                    data_type: str = "output",
                    subdir: Optional[str] = None,
                    include_timestamp: bool = True,
                    pretty_print: bool = True) -> str:
    """
    Save multiple data items into a single unified JSON file.
    
    Args:
        module: The module name (dragon, dune, sharp, solana, gmgn)
        data_items: List of data items to save
        filename_prefix: Prefix for the output filename
        data_type: Type of data ("input" or "output")
        subdir: Optional subdirectory within the module
        include_timestamp: Whether to include timestamp in the filename
        pretty_print: Whether to format the JSON with indentation
        
    Returns:
        Path to the saved file
    """
    # Get the directory
    directory = ensure_data_dir(module, subdir, data_type)
    
    # Create a filename with timestamp if requested
    if include_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.json"
    else:
        filename = f"{filename_prefix}.json"
    
    # Full path to the output file
    output_path = directory / filename
    
    # The structure to save
    data_bundle = {
        "metadata": {
            "module": module,
            "created_at": datetime.now().isoformat(),
            "item_count": len(data_items),
            "type": data_type
        },
        "items": data_items
    }
    
    # Ensure parent directory exists before writing
    ensure_file_dir(output_path)
    
    # Save the data
    with open(output_path, 'w') as f:
        indent = 2 if pretty_print else None
        json.dump(data_bundle, f, indent=indent)
    
    return str(output_path)


def load_unified_data(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load data from a unified JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary with the loaded data
    """
    file_path = Path(file_path)
    
    try:
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Check if this is a unified format file
        if 'metadata' in data and 'items' in data:
            return {
                "success": True,
                "metadata": data['metadata'],
                "items": data['items'],
                "item_count": len(data['items'])
            }
        else:
            # Handle older format files
            return {
                "success": True,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "item_count": 1,
                    "type": "legacy"
                },
                "items": [data],  # Wrap the data in a list
                "item_count": 1
            }
            
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": f"Invalid JSON in file: {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error loading file: {e}"
        }


def list_saved_data(module: str, 
                    data_type: str = "output", 
                    subdir: Optional[str] = None, 
                    pattern: str = "*.json") -> List[Dict[str, Any]]:
    """
    List all saved data files for a module.
    
    Args:
        module: The module name (dragon, dune, sharp, solana, gmgn)
        data_type: Type of data directory ("input" or "output")
        subdir: Optional subdirectory within the module
        pattern: File pattern to match
        
    Returns:
        List of dictionaries with file information
    """
    # Get the directory
    directory = ensure_data_dir(module, subdir, data_type)
    
    # Find all matching files
    files = list(directory.glob(pattern))
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Create file information
    file_info = []
    for file in files:
        # Try to load metadata
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                
            if 'metadata' in data:
                metadata = data['metadata']
                item_count = metadata.get('item_count', 0)
            else:
                metadata = {"type": "legacy"}
                item_count = 1
                
            file_info.append({
                "path": str(file),
                "name": file.name,
                "stem": file.stem,
                "size": file.stat().st_size,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                "metadata": metadata,
                "item_count": item_count
            })
        except Exception:
            # If we can't load metadata, just include basic file info
            file_info.append({
                "path": str(file),
                "name": file.name,
                "stem": file.stem,
                "size": file.stat().st_size,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                "metadata": {"type": "unknown"}
            })
    
    return file_info


def find_all_matching_files(pattern: str, recursive: bool = True) -> List[Dict[str, Any]]:
    """
    Find all matching files in the entire input-data directory, regardless of module.
    
    Args:
        pattern: File pattern to match (e.g., "*.json", "wallets.txt")
        recursive: Whether to search recursively (default True)
        
    Returns:
        List of dictionaries with file information
    """
    from ..core.config import INPUT_DATA_DIR
    
    # Set up search pattern
    search_pattern = "**/" + pattern if recursive else pattern
    
    # Find all matching files in the input-data directory - convert to set to eliminate duplicates
    # This is important because the glob search might find the same file through different paths
    file_paths = set()
    for file in INPUT_DATA_DIR.glob(search_pattern):
        file_paths.add(str(file.resolve()))
    
    # Create file objects from resolved paths and sort
    files = [Path(path) for path in file_paths]
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Create file information
    file_info = []
    for file in files:
        # Determine relative module path
        try:
            rel_path = file.relative_to(INPUT_DATA_DIR)
            module_path = str(rel_path.parts[0] if len(rel_path.parts) > 0 else "")
        except ValueError:
            # If the file doesn't have a relative path to INPUT_DATA_DIR, use the full path
            rel_path = file.name
            module_path = ""
        
        # Try to load metadata if it's a JSON file
        metadata = {"type": "unknown"}
        item_count = 1
        
        if file.suffix.lower() == ".json":
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    
                if 'metadata' in data:
                    metadata = data['metadata']
                    item_count = metadata.get('item_count', 0)
            except Exception:
                pass  # Use default metadata for invalid JSON files
        
        file_info.append({
            "path": str(file),
            "name": file.name,
            "stem": file.stem,
            "size": file.stat().st_size,
            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
            "module": module_path,
            "metadata": metadata,
            "item_count": item_count,
            "rel_path": str(rel_path)
        })
    
    return file_info


def select_input_file(pattern: str, 
                     message: str = "Select an input file:", 
                     show_module: bool = True) -> Optional[str]:
    """
    Universal file selection utility that presents a list of all matching files 
    from the entire input-data directory.
    
    Args:
        pattern: File pattern to match (e.g., "*.json", "wallets.txt")
        message: Prompt message to display
        show_module: Whether to show the module path in the selection
        
    Returns:
        Path to the selected file or None if no selection was made
    """
    # Import inquirer for the UI
    import inquirer
    from blessed import Terminal
    
    # Find all matching files
    files = find_all_matching_files(pattern)
    
    if not files:
        console.print(f"[yellow]No files matching '{pattern}' found in the input-data directory.[/yellow]")
        return None
    
    # Create a list of choices for the user - deduplicate by path
    seen_paths = set()
    choice_items = []
    
    for file in files:
        path = file.get("path", "")
        # Skip duplicates - this prevents the same file appearing multiple times
        if path in seen_paths:
            continue
        
        seen_paths.add(path)
        
        # Format each file nicely for display
        modified_date = datetime.fromisoformat(file.get("modified", "")).strftime("%Y-%m-%d %H:%M")
        module_name = file.get("module", "")
        name = file.get("name", "")
        rel_path = file.get("rel_path", "")
        
        # Show module info if requested
        if show_module:
            display = f"{rel_path} ({modified_date})"
        else:
            display = f"{name} ({modified_date})"
        
        # Add to choices
        choice_items.append((display, path))
    
    # Add a cancel option
    choice_items.append(("Cancel", None))
    
    # Manual selection to avoid repeated prompts
    term = Terminal()
    
    print(f"\n{message}")
    
    selected_index = 0
    choice_count = len(choice_items)
    
    # Handle key presses and navigation
    with term.cbreak(), term.hidden_cursor():
        while True:
            # Clear the screen and display the current options
            print(term.clear)
            print(f"{message}")
            
            for i, (display, _) in enumerate(choice_items):
                if i == selected_index:
                    print(f"{term.bold}{term.blue}> {display}{term.normal}")
                else:
                    print(f"  {display}")
            
            # Get key press
            key = term.inkey()
            
            if key.name == 'KEY_UP':
                selected_index = (selected_index - 1) % choice_count
            elif key.name == 'KEY_DOWN':
                selected_index = (selected_index + 1) % choice_count
            elif key.name == 'KEY_ENTER':
                break
            elif key.name == 'KEY_ESCAPE':
                selected_index = choice_count - 1  # Select Cancel
                break
    
    # Return the selected choice
    _, selected_value = choice_items[selected_index]
    print(f"\nSelected: {choice_items[selected_index][0]}\n")
    
    return selected_value


def select_multiple_input_files(pattern: str, 
                               message: str = "Select input files (space to select, enter when done):", 
                               show_module: bool = True) -> List[str]:
    """
    Universal file multi-selection utility that allows selecting multiple files
    from the entire input-data directory.
    
    Args:
        pattern: File pattern to match (e.g., "*.json", "wallets.txt")
        message: Prompt message to display
        show_module: Whether to show the module path in the selection
        
    Returns:
        List of paths to the selected files (empty list if no selection was made)
    """
    # Import terminal UI components
    from blessed import Terminal
    
    # Find all matching files
    files = find_all_matching_files(pattern)
    
    if not files:
        console.print(f"[yellow]No files matching '{pattern}' found in the input-data directory.[/yellow]")
        return []
    
    # Create a list of choices for the user - deduplicate by path
    seen_paths = set()
    choice_items = []
    
    for file in files:
        path = file.get("path", "")
        # Skip duplicates
        if path in seen_paths:
            continue
        
        seen_paths.add(path)
        
        # Format each file nicely for display
        modified_date = datetime.fromisoformat(file.get("modified", "")).strftime("%Y-%m-%d %H:%M")
        module_name = file.get("module", "")
        name = file.get("name", "")
        rel_path = file.get("rel_path", "")
        
        # Show module info if requested
        if show_module:
            display = f"{rel_path} ({modified_date})"
        else:
            display = f"{name} ({modified_date})"
        
        # Add to choices with selection status
        choice_items.append((display, path, False))  # False means not selected
    
    # Add a done option
    choice_items.append(("Done", None, False))
    
    # Manual selection to avoid repeated prompts
    term = Terminal()
    
    print(f"\n{message}")
    print("Press Space to select/deselect, Enter when done, Esc to cancel")
    
    cursor_index = 0
    choice_count = len(choice_items)
    
    # Handle key presses and navigation
    with term.cbreak(), term.hidden_cursor():
        while True:
            # Clear the screen and display the current options
            print(term.clear)
            print(f"{message}")
            print("Press Space to select/deselect, Enter when done, Esc to cancel\n")
            
            for i, (display, _, selected) in enumerate(choice_items):
                # Different display for Done option
                if i == choice_count - 1:  # Done option
                    if i == cursor_index:
                        print(f"{term.bold}{term.blue}> {display}{term.normal}")
                    else:
                        print(f"  {display}")
                else:
                    prefix = "[x]" if selected else "[ ]"
                    if i == cursor_index:
                        print(f"{term.bold}{term.blue}> {prefix} {display}{term.normal}")
                    else:
                        print(f"  {prefix} {display}")
            
            # Count selected items
            selected_count = sum(1 for _, _, selected in choice_items[:-1] if selected)
            print(f"\n{selected_count} item(s) selected")
            
            # Get key press
            key = term.inkey()
            
            if key.name == 'KEY_UP':
                cursor_index = (cursor_index - 1) % choice_count
            elif key.name == 'KEY_DOWN':
                cursor_index = (cursor_index + 1) % choice_count
            elif key == ' ':  # Space
                # Toggle selection for current item (except Done option)
                if cursor_index < choice_count - 1:
                    display, path, selected = choice_items[cursor_index]
                    choice_items[cursor_index] = (display, path, not selected)
            elif key.name == 'KEY_ENTER':
                if cursor_index == choice_count - 1:  # Done selected
                    break
                # Otherwise toggle current item
                if cursor_index < choice_count - 1:
                    display, path, selected = choice_items[cursor_index]
                    choice_items[cursor_index] = (display, path, not selected)
            elif key.name == 'KEY_ESCAPE':
                # Clear all selections and exit
                for i in range(len(choice_items) - 1):
                    display, path, _ = choice_items[i]
                    choice_items[i] = (display, path, False)
                break
    
    # Return the selected file paths
    selected_paths = [path for _, path, selected in choice_items[:-1] if selected]
    
    if selected_paths:
        print(f"\nSelected {len(selected_paths)} file(s)")
    else:
        print("\nNo files selected")
    
    return selected_paths



def process_multiple_inputs(inputs: List[str], 
                        processor_func: Callable[[str], Dict[str, Any]], 
                        description: str = "item",
                        show_progress: bool = True) -> Dict[str, Any]:
    """
    Process multiple inputs using the provided processor function.
    This function handles iterating over inputs, tracking progress, and aggregating results.
    
    Args:
        inputs: List of input strings to process
        processor_func: Function that processes a single input and returns a dict
        description: Description of the items being processed (for progress display)
        show_progress: Whether to show progress information
        
    Returns:
        Dictionary with aggregated results and statistics
    """
    if not inputs:
        return {
            "success": False,
            "error": f"No {description} inputs provided"
        }
    
    all_results = []
    errors = []
    success_count = 0
    
    if show_progress:
        console.print(f"\nProcessing {len(inputs)} {description}(s)...\n")
    
    for idx, input_value in enumerate(inputs):
        if show_progress:
            console.print(f"[bold cyan]Processing {description} {idx+1}/{len(inputs)}: {input_value}[/bold cyan]")
        
        try:
            result = processor_func(input_value)
            all_results.append(result)
            
            if result.get("success", False):
                success_count += 1
                if show_progress:
                    console.print(f"[green]✓ Successfully processed {description}[/green]")
            else:
                error_msg = result.get("error", f"Unknown error processing {description}")
                errors.append(f"Error processing {input_value}: {error_msg}")
                if show_progress:
                    console.print(f"[red]✗ Failed to process {description}: {error_msg}[/red]")
        
        except Exception as e:
            errors.append(f"Exception processing {input_value}: {str(e)}")
            if show_progress:
                console.print(f"[red]✗ Exception during processing: {str(e)}[/red]")
    
    # Compile final results
    return {
        "success": success_count > 0,
        "all_results": all_results,
        "success_count": success_count,
        "error_count": len(inputs) - success_count,
        "errors": errors if errors else None,
        "total_processed": len(inputs)
    }


def check_proxy_file(proxy_path: Optional[str] = None) -> List[str]:
    """
    Check if proxy file exists and get proxies.
    
    Args:
        proxy_path: Optional path to proxy file, defaults to input-data/dragon/proxies/proxies.txt
        
    Returns:
        List of proxy strings or empty list if no proxies
    """
    if proxy_path is None:
        from ..core.config import INPUT_DATA_DIR
        proxy_path = INPUT_DATA_DIR / "dragon" / "proxies" / "proxies.txt"
        
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


def validate_credentials(module_name: str) -> bool:
    """
    Check if all required environment variables for a module are present.
    Shows error message and returns False if any are missing.
    
    Args:
        module_name: Module name to check credentials for (e.g., 'solana', 'dragon')
        
    Returns:
        True if all required credentials are present, False otherwise
    """
    # Import here to avoid circular imports
    from ..core.config import check_env_vars
    
    # Check for required environment variables
    env_vars = check_env_vars(module_name)
    
    # If no vars required (like some Sharp tools), return True
    if not env_vars:
        return True
        
    if not all(env_vars.values()):
        missing = [var for var, present in env_vars.items() if not present]
        clear_terminal()
        console.print(f"[bold red]❌ Missing required credentials for this module[/bold red]")
        console.print(f"The following environment variables are not set: {', '.join(missing)}")
        console.print("\nPlease set them in Settings > Edit Environment Variables")
        console.print("\nPress Enter to return to main menu...")
        input()
        return False
        
    return True


def validate_multiple_credentials(modules: List[str]) -> bool:
    """
    Check if all required environment variables for multiple modules are present.
    Shows error message and returns False if any are missing.
    
    Args:
        modules: List of module names to check credentials for
        
    Returns:
        True if all required credentials are present, False otherwise
    """
    # Import here to avoid circular imports
    from ..core.config import check_env_vars
    
    all_missing = []
    
    # Check each module's credentials
    for module in modules:
        env_vars = check_env_vars(module)
        missing = [var for var, present in env_vars.items() if not present]
        all_missing.extend(missing)
    
    # If any credentials are missing, show error and return False
    if all_missing:
        clear_terminal()
        console.print(f"[bold red]❌ Missing required credentials for this module[/bold red]")
        console.print(f"The following environment variables are not set: {', '.join(set(all_missing))}")
        console.print("\nPlease set them in Settings > Edit Environment Variables")
        console.print("\nPress Enter to return to main menu...")
        input()
        return False
        
    return True