"""Common utility functions used across modules."""

import os
import time
import json
import shutil
import requests
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple, Union, Callable, cast, Type, TypeVar
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text

from ..core.config import get_env_var, ROOT_DIR, DATA_DIR, CACHE_DIR

console = Console()

# Import inquirer classes
try:
    import inquirer
    from inquirer.questions import Text as InquirerText
    from inquirer.render.console import ConsoleRender
    import readchar
    import sys
    from blessed import Terminal
    
    # Type variables for class compatibility
    T = TypeVar('T')
    
    # Create a simple but effective direct input implementation - use a unique name to avoid conflicts
    class EnhancedTextInput(InquirerText):
        """
        A simplified Text input that properly handles paste operations.
        
        This overrides the default inquirer Text input to fix an issue where
        pasting text with newlines or large amounts of text causes rendering glitches.
        """
        def __init__(self, name, message="", default="", validate=None, **kwargs):
            # Initialize parent class
            super().__init__(
                name, 
                message=message,
                default=default,
                validate=validate, 
                **kwargs
            )
        
        def execute(self):
            """
            Execute text input in a simplified way that properly handles paste operations.
            """
            console = Console()
            console.print(f"{self.message}: ", end="")
            if self.default:
                console.print(f"[dim]{self.default}[/dim] ", end="")
            
            # Get input
            result = input() or self.default
            
            # Validate
            if self.validate:
                validation_result = self.validate(result)
                if validation_result is not True:
                    console.print(f"[red]{validation_result}[/red]")
                    # Try again recursively
                    return self.execute()
            
            return result
        
        def get_message(self):
            """Custom message rendering to keep things simple."""
            return f"{self.message}: "

    # Create a function to prompt the user, bypassing inquirer's rendering
    def prompt_user(questions):
        """
        Alternative to inquirer.prompt that prevents the paste issues.
        Use this instead of inquirer.prompt when working with text inputs.
        """
        result = {}
        
        for question in questions:
            if isinstance(question, EnhancedTextInput):
                # Handle our custom text input directly
                result[question.name] = question.execute()
            else:
                # Pass other question types to inquirer
                temp_result = inquirer.prompt([question])
                if temp_result:
                    result.update(temp_result)
        
        return result
    
    # ======= MONKEY PATCHING FOR SYSTEM-WIDE FIX ========
    # Save original inquirer Text class for reference
    _original_inquirer_text = inquirer.Text
    
    # This function will replace the standard inquirer.prompt for our enhanced version
    _original_inquirer_prompt = inquirer.prompt
    
    def _paste_safe_prompt(questions, *args, **kwargs):
        """
        Replacement for inquirer.prompt that automatically handles Text inputs
        in a paste-safe manner, without requiring manual changes throughout the codebase.
        """
        # Convert standard Text questions to EnhancedTextInput
        for i, question in enumerate(questions):
            if isinstance(question, _original_inquirer_text):
                # Create a EnhancedTextInput with the same attributes
                new_question = EnhancedTextInput(
                    question.name,
                    message=question.message,
                    default=question.default,
                    validate=question.validate
                )
                questions[i] = new_question
        
        # Use our prompt_user function which handles the mix of question types
        # but make sure we don't call ourselves recursively
        result = {}
        
        for question in questions:
            if isinstance(question, EnhancedTextInput):
                # Handle our custom text input directly
                result[question.name] = question.execute()
            else:
                # Pass other question types to the original inquirer prompt
                temp_result = _original_inquirer_prompt([question], *args, **kwargs)
                if temp_result:
                    result.update(temp_result)
        
        return result

    # Replace the prompt method system-wide
    inquirer.prompt = _paste_safe_prompt
    
    # Define public names - these are the only ones that should be imported
    # by other modules to avoid name conflicts
    NoTruncationText = EnhancedTextInput
    PasteAwareTextInput = EnhancedTextInput
    
except ImportError:
    # ===== FALLBACK IMPLEMENTATION FOR WHEN INQUIRER IS NOT AVAILABLE =====
    class BasicTextInput:
        """Fallback if inquirer isn't available."""
        def __init__(self, name, message="", default="", validate=None, **kwargs):
            self.name = name
            self.message = message
            self.default = default
            self.validate = validate
            
        def execute(self):
            """Simple input handler for when inquirer isn't available."""
            print(f"{self.message}: ", end="")
            if self.default:
                print(f"{self.default} ", end="")
            
            result = input() or self.default
            
            if self.validate:
                validation_result = self.validate(result)
                if validation_result is not True:
                    print(f"Error: {validation_result}")
                    return self.execute()
                    
            return result
        
    def prompt_user(questions):
        """Fallback prompt function if inquirer isn't available."""
        result = {}
        for question in questions:
            result[question.name] = input(f"{question.message}: ")
        return result
    
    # Define public names - consistent with the above try block
    NoTruncationText = BasicTextInput
    PasteAwareTextInput = BasicTextInput


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
    """Manages progress bars and spinners for long-running tasks."""
    
    def __init__(self, total=None, description="Processing", transient=True):
        """Initialize a new progress manager."""
        self.total = total
        self.description = description
        self.transient = transient
        self.task_id = None
        self.progress = None
        self.live = None
        self.start_time = time.time()
        
        # Default settings for progress display
        self.show_sparklines = True
        self.enable_animations = True
        
        # Default colors
        self.primary_color = '#6C5CE7'
        self.secondary_color = '#00CEC9'
        
        # Create progress columns with theme colors
        self.progress_columns = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None, complete_style=f"bold {self.primary_color}", 
                     finished_style=f"bold {self.secondary_color}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]
    
    def start(self):
        """Start the progress tracking."""
        # Create a new progress instance
        refresh_rate = 10 if self.enable_animations else 4
        self.progress = Progress(*self.progress_columns, refresh_per_second=refresh_rate, 
                               transient=self.transient)
        
        # Start the live display
        self.live = Live(self.progress, refresh_per_second=refresh_rate, transient=self.transient)
        self.live.start()
        
        # Add the task
        self.task_id = self.progress.add_task(self.description, total=self.total)
        return self
    
    def update(self, completed: float, total: Optional[float] = None, description: Optional[str] = None):
        """Update progress of the current step."""
        if self.task_id is not None and self.progress is not None:
            # Create a clean kwargs dict with only the valid arguments
            update_kwargs = {}
            update_kwargs["completed"] = completed
            
            if total is not None:
                update_kwargs["total"] = total
            if description is not None:
                update_kwargs["description"] = description
            
            # Use type-safe update call
            self.progress.update(self.task_id, **update_kwargs)
    
    def complete(self, success: bool = True, message: Optional[str] = None):
        """Finish the progress tracking."""
        if self.live and self.progress is not None and self.task_id is not None:
            if success:
                final_msg = message or "Process completed successfully!"
                success_color = 'bright_green'
                # Use type-safe update call with only valid arguments
                self.progress.update(
                    self.task_id, 
                    description=f"[bold {success_color}]✓ {final_msg}[/bold {success_color}]", 
                    completed=self.total
                )
            else:
                final_msg = message or "Process failed!"
                warning_color = 'bright_red'
                # Use type-safe update call with only valid arguments
                self.progress.update(
                    self.task_id, 
                    description=f"[bold {warning_color}]✗ {final_msg}[/bold {warning_color}]"
                )
            
            # Add a slight delay to ensure final state is visible
            time.sleep(0.5)
            self.live.stop()
    
    def get_elapsed_time(self) -> float:
        """Get the total elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_eta(self) -> float:
        """Estimate time remaining in seconds."""
        if not self.progress or self.task_id is None:
            return 0
            
        task = self.progress.tasks[self.task_id]
        if task.completed == 0:
            return 0
            
        elapsed = self.get_elapsed_time()
        progress_ratio = task.completed / task.total if task.total else 0
        if progress_ratio == 0:
            return 0
            
        return elapsed * (1 - progress_ratio) / progress_ratio


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
        """Print a rich summary of the workflow results."""
        from rich.console import Console
        from rich.table import Table
        from rich import box
        from rich.text import Text
        
        console = Console()
        table = Table(show_header=False, box=box.SIMPLE)
        
        # Add columns
        table.add_column("label", style="bold")
        table.add_column("value")
        
        # Add title
        title = Text("Workflow Results", style="bold cyan underline")
        table.add_row("", title)
        
        # Add input files
        if self.input_files:
            table.add_row("\nInput Files:", "")
            for key, path in self.input_files.items():
                table.add_row(f"  {key}", path)
        
        # Add output files
        if self.output_files:
            table.add_row("\nOutput Files:", "")
            for key, path in self.output_files.items():
                table.add_row(f"  {key}", path)
        
        # Add stats
        if self.stats:
            table.add_row("\nStatistics:", "")
            for key, value in self.stats.items():
                table.add_row(f"  {key}", str(value))
        
        # Add processed timestamp
        completed_label = Text("Completed at: ", style="bold")
        completed_value = Text(self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else "N/A", style="cyan")
        table.add_row("\n", "")
        table.add_row(completed_label, completed_value)
        
        # Add status
        if self.error_message:
            error_label = Text("Error: ", style="bold red")
            error_value = Text(self.error_message, style="red")
            table.add_row("\n", "")
            table.add_row(error_label, error_value)
        else:
            status_label = Text("Status: ", style="bold")
            status_value = Text("Success", style="green")
            table.add_row("\n", "")
            table.add_row(status_label, status_value)
            
        # Add duration
        duration_str = format_duration(self.duration()) if self.start_time and self.end_time else "Unknown"
        duration_label = Text("Duration: ", style="bold")
        duration_value = Text(duration_str, style="cyan")
        table.add_row(duration_label, duration_value)
            
        console.print(table)
        console.print("\n[bright_green]✓[/bright_green] [bold]Workflow completed[/bold]\n")
    
    def export_results(self, export_format: str = 'json', output_path: Optional[str] = None) -> Optional[str]:
        """
        Export workflow results to a file.
        
        Args:
            export_format: Format to export (json, csv, xlsx)
            output_path: Path to save the exported file
            
        Returns:
            The path to the exported file if successful, None otherwise
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


def clear_cache(clear_pycache: bool = False):
    """
    Clear all cached data files.
    
    Args:
        clear_pycache: Whether to also clear the __pycache__ directory
    """
    success = True
    
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
        
        # Also clear __pycache__ if requested
        if clear_pycache:
            pycache_dir = DATA_DIR / "__pycache__"
            if os.path.exists(pycache_dir):
                shutil.rmtree(pycache_dir)
                os.makedirs(pycache_dir, exist_ok=True)
                console.print(f"[green]✓ Successfully cleared __pycache__ directory: {pycache_dir}[/green]")
            else:
                console.print(f"[yellow]__pycache__ directory does not exist: {pycache_dir}[/yellow]")
                os.makedirs(pycache_dir, exist_ok=True)
        
    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")
        success = False
        
    return success


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


def check_proxy_file(proxy_path: Optional[Union[str, Path]] = None) -> List[str]:
    """
    Check if proxies file exists and load proxies.
    
    Args:
        proxy_path: Path to the proxies file, will use default if None
        
    Returns:
        List of proxy strings
    """
    if proxy_path is None:
        from ..core.config import INPUT_DATA_DIR
        proxy_path = str(INPUT_DATA_DIR / "proxies" / "proxies.txt")
        
    try:
        if proxy_path and os.path.exists(proxy_path):
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
    Check if all required credentials are set for a module.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        True if all required credentials are set, False otherwise
    """
    from ..core.config import check_env_vars
    
    console = Console()
    env_vars = check_env_vars(module_name)
    
    if not all(env_vars.values()):
        # Fix: Create the missing list here
        missing_vars = [var for var, present in env_vars.items() if not present]
        clear_terminal()
        console.print(f"[bold red]❌ Missing required credentials for this module[/bold red]")
        console.print("\nThe following environment variables are required but not set:")
        for var in missing_vars:
            console.print(f"  - [yellow]{var}[/yellow]")
        
        console.print("\nPlease set them in Settings > Edit Environment Variables")
        input("\nPress Enter to continue...")
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


def print_success(message):
    """Print a success message."""
    success_color = 'bright_green'
    console.print(f"[bold {success_color}]✓[/bold {success_color}] {message}")


def print_result(message, success=True):
    """Print an operation result with appropriate styling."""
    success_color = 'bright_green'
    icon = "✓" if success else "✗"
    style = f"bold {success_color}" if success else "bold bright_red"
    console.print(f"[{style}]{icon}[/{style}] {message}")


def print_warning(message):
    """Print a warning message."""
    warning_color = 'bright_red'
    console.print(f"[bold {warning_color}]![/bold {warning_color}] {message}")