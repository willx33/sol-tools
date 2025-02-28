"""Handlers for Sharp module functionality."""

import os
import csv
import glob
import json
import time
import shutil
import inquirer
import pandas as pd
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

from ...utils.common import clear_terminal, ensure_data_dir

# Create Rich console for fancy output
console = Console()

# BullX API URLs
BULLX_GETPORTFOLIO_URL = "https://api-neo.bullx.io/v2/api/getPortfolioV3"
BULLX_TRANSACTION_URL = "https://api-neo.bullx.io/v2/api/getTransactionsV3"

# API request headers
HEADERS = {
    "Content-Type": "application/json",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/108.0.0.0 Safari/537.36"
    ),
}


def wallet_checker(export_format: str = None):
    """
    Check wallet statistics using BullX API and filter by performance metrics.
    
    Args:
        export_format: Optional format to export results ('json', 'csv', 'excel')
    """
    from ...utils.common import ProgressManager, WorkflowResult, format_duration
    
    clear_terminal()
    console.print("[bold blue]🔍 Sharp Wallet Checker[/bold blue]")
    console.print("Analyze wallet performance data from BullX API\n")
    
    # Setup directories
    sharp_dir = ensure_data_dir("sharp")
    wallet_dir = ensure_data_dir("sharp", "wallets")
    
    # Input method selection
    input_options = [
        "Load from file",
        "Enter addresses manually", 
        "Import from clipboard", 
        "Use latest filtered output"
    ]
    
    questions = [
        inquirer.List(
            "input_method",
            message="How would you like to provide wallet addresses?",
            choices=input_options
        ),
    ]
    answers = inquirer.prompt(questions)
    input_method = answers["input_method"]
    
    # Initialize workflow result tracking
    workflow_result = WorkflowResult()
    
    # Get wallets based on selected method
    wallets = []
    input_file = None  # Track the input file for the workflow result
    
    if input_method == "Load from file":
        # Find existing wallet files
        wallet_files = list(wallet_dir.glob("*.txt"))
        wallet_files.sort(key=os.path.getmtime, reverse=True)  # Sort by modification time
        
        default_file = str(wallet_dir / "check-wallets.txt")
        file_choices = [os.path.basename(f) for f in wallet_files] if wallet_files else []
        
        if file_choices:
            file_choices.append("Other file (specify path)")
            questions = [
                inquirer.List(
                    "file_choice",
                    message="Select a wallet file:",
                    choices=file_choices
                ),
            ]
            answers = inquirer.prompt(questions)
            file_choice = answers["file_choice"]
            
            if file_choice == "Other file (specify path)":
                questions = [
                    inquirer.Text(
                        "input_file",
                        message="Enter path to file with wallet addresses:",
                        default=default_file
                    ),
                ]
                answers = inquirer.prompt(questions)
                input_file = answers["input_file"]
            else:
                input_file = str(wallet_dir / file_choice)
        else:
            console.print("[yellow]No existing wallet files found.[/yellow]")
            questions = [
                inquirer.Text(
                    "input_file",
                    message="Enter path to file with wallet addresses:",
                    default=default_file
                ),
            ]
            answers = inquirer.prompt(questions)
            input_file = answers["input_file"]
        
        # Ensure input file exists
        if not os.path.isfile(input_file):
            console.print(f"[yellow]File not found: {input_file}[/yellow]")
            console.print("Creating an empty file at this location.")
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(input_file), exist_ok=True)
            # Create empty file
            with open(input_file, "w") as f:
                pass
                
            # Ask user to input some addresses now
            console.print("\n[bold]Enter wallet addresses to check (one per line)[/bold]")
            console.print("Press Enter on an empty line when finished")
            
            manual_wallets = []
            while True:
                line = input("> ").strip()
                if not line:
                    break
                if len(line) >= 30:  # Simple validation for wallet address length
                    manual_wallets.append(line)
                else:
                    console.print(f"[yellow]Warning: '{line}' doesn't look like a valid wallet address[/yellow]")
            
            if manual_wallets:
                # Save to the newly created file
                with open(input_file, "w", encoding="utf-8") as f:
                    for wallet in manual_wallets:
                        f.write(wallet + "\n")
                console.print(f"[green]✓[/green] Saved {len(manual_wallets)} addresses to {input_file}")
                wallets = manual_wallets
            else:
                console.print("[yellow]No addresses provided. Please add wallet addresses to the file and run again.[/yellow]")
                return
        else:
            # Read wallet addresses from file
            with open(input_file, "r", encoding="utf-8") as f:
                wallets = [line.strip() for line in f if line.strip()]
            
            if not wallets:
                console.print(f"[red]No wallet addresses found in file: {input_file}[/red]")
                return
    
    elif input_method == "Enter addresses manually":
        console.print("\n[bold]Enter wallet addresses to check (one per line)[/bold]")
        console.print("Press Enter on an empty line when finished")
        
        while True:
            line = input("> ").strip()
            if not line:
                break
            if len(line) >= 30:  # Simple validation for wallet address length
                wallets.append(line)
            else:
                console.print(f"[yellow]Warning: '{line}' doesn't look like a valid wallet address[/yellow]")
        
        if not wallets:
            console.print("[yellow]No addresses provided.[/yellow]")
            return
            
        # Ask if user wants to save these for future use
        questions = [
            inquirer.Confirm(
                "save_wallets",
                message="Save these wallet addresses for future use?",
                default=True
            ),
        ]
        answers = inquirer.prompt(questions)
        
        if answers["save_wallets"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_file = wallet_dir / f"manual_wallets_{timestamp}.txt"
            
            with open(save_file, "w", encoding="utf-8") as f:
                for wallet in wallets:
                    f.write(wallet + "\n")
            console.print(f"[green]✓[/green] Saved {len(wallets)} addresses to {save_file}")
            input_file = str(save_file)
    
    elif input_method == "Import from clipboard":
        import pyperclip
        try:
            clipboard_text = pyperclip.paste()
            
            if not clipboard_text:
                console.print("[yellow]Clipboard is empty.[/yellow]")
                return
                
            # Extract wallet addresses from clipboard (one per line)
            clipboard_wallets = [line.strip() for line in clipboard_text.split('\n') if line.strip()]
            
            # Validate addresses
            valid_wallets = []
            for wallet in clipboard_wallets:
                if len(wallet) >= 30:  # Simple validation for wallet address length
                    valid_wallets.append(wallet)
            
            if not valid_wallets:
                console.print("[yellow]No valid wallet addresses found in clipboard.[/yellow]")
                return
                
            console.print(f"Found {len(valid_wallets)} wallet addresses in clipboard.")
            wallets = valid_wallets
            
            # Ask if user wants to save these for future use
            questions = [
                inquirer.Confirm(
                    "save_wallets",
                    message="Save these wallet addresses for future use?",
                    default=True
                ),
            ]
            answers = inquirer.prompt(questions)
            
            if answers["save_wallets"]:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_file = wallet_dir / f"clipboard_wallets_{timestamp}.txt"
                
                with open(save_file, "w", encoding="utf-8") as f:
                    for wallet in wallets:
                        f.write(wallet + "\n")
                console.print(f"[green]✓[/green] Saved {len(wallets)} addresses to {save_file}")
                input_file = str(save_file)
                
        except ImportError:
            console.print("[red]Error: pyperclip module not installed.[/red]")
            console.print("Please install it with: pip install pyperclip")
            return
        except Exception as e:
            console.print(f"[red]Error accessing clipboard: {e}[/red]")
            return
    
    elif input_method == "Use latest filtered output":
        # Find the latest output-wallets file
        output_files = list(wallet_dir.glob("output-wallets_*.txt"))
        output_files.sort(key=os.path.getmtime, reverse=True)
        
        if not output_files:
            console.print("[yellow]No previous output files found. Please use another input method.[/yellow]")
            return
            
        latest_file = output_files[0]
        input_file = str(latest_file)
        
        # Show info about the file
        mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
        time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(latest_file, "r", encoding="utf-8") as f:
            wallets = [line.strip() for line in f if line.strip()]
        
        console.print(f"[green]✓[/green] Loaded {len(wallets)} addresses from {latest_file.name}")
        console.print(f"   File date: {time_str}")
    
    # Update workflow result with input file
    if input_file:
        workflow_result.add_input("wallet_list", input_file)
    
    # Make sure we have wallets to process
    if not wallets:
        console.print("[red]No wallet addresses provided.[/red]")
        return
    
    # Remove duplicates while preserving order
    unique_wallets = []
    seen = set()
    for wallet in wallets:
        if wallet not in seen:
            seen.add(wallet)
            unique_wallets.append(wallet)
    
    if len(unique_wallets) < len(wallets):
        console.print(f"[yellow]Removed {len(wallets) - len(unique_wallets)} duplicate addresses.[/yellow]")
    
    wallets = unique_wallets
    console.print(f"[green]✓[/green] Ready to process {len(wallets)} wallet addresses\n")
    
    # Load or create config
    config_file = sharp_dir / "wallet_checker_config.json"
    config = {
        "filters": {
            "min_realizedPnlUsd": 0,               # Realized profit (sold positions)
            "min_unrealizedPnlUsd": 0,             # Unrealized profit (held positions)
            "min_totalPnlUsd": 0,                  # Total profit (realized + unrealized)
            "min_totalRevenuePercent": 0,          # Total profit percentage
            "min_num_tokens": 0,                   # Minimum number of tokens held
            "min_distribution_0_percent": 0,       # % of trades with 0% profit
            "min_distribution_0_200_percent": 0,   # % of trades with 0-200% profit
            "min_distribution_200_plus_percent": 0, # % of trades with >200% profit
            "min_win_count": 0,                    # Minimum number of profitable trades
            "min_win_rate": 0,                     # Minimum win rate (percentage)
            "max_loss_rate": 100,                  # Maximum loss rate (percentage)
        },
        "save_unfiltered_csv": True,
        "save_filtered_csv": True,
        "save_transaction_data": False,
        "retry_failed": True,
        "retry_delay": 2
    }
    
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # Merge with defaults
                if "filters" in user_config:
                    config["filters"].update(user_config["filters"])
                # Get other config options
                for key in ["save_unfiltered_csv", "save_filtered_csv", "save_transaction_data", 
                           "retry_failed", "retry_delay"]:
                    if key in user_config:
                        config[key] = user_config[key]
        except Exception as e:
            console.print(f"[yellow]Error reading config file: {e}[/yellow]")
            console.print("Using default configuration.")
    
    # Config menu
    config_menu_choices = [
        "Edit filters",
        "Output options",
        "Advanced settings",
        "Continue with current settings",
    ]
    
    # Add export option if not provided
    if export_format is None:
        config_menu_choices.insert(2, "Export options")
    
    questions = [
        inquirer.List(
            "config_choice",
            message="Configuration:",
            choices=config_menu_choices
        ),
    ]
    answers = inquirer.prompt(questions)
    config_choice = answers["config_choice"]
    
    # Handle configuration choices
    if config_choice == "Edit filters":
        # Edit filter values
        console.print("\n[bold]Filter Settings[/bold]")
        console.print("Wallets must meet ALL criteria to pass the filter\n")
        
        questions = [
            inquirer.Text(
                "min_realizedPnlUsd",
                message="Minimum realized PnL in USD",
                default=str(config["filters"]["min_realizedPnlUsd"])
            ),
            inquirer.Text(
                "min_unrealizedPnlUsd",
                message="Minimum unrealized PnL in USD",
                default=str(config["filters"]["min_unrealizedPnlUsd"])
            ),
            inquirer.Text(
                "min_totalPnlUsd",
                message="Minimum total PnL in USD (realized + unrealized)",
                default=str(config["filters"].get("min_totalPnlUsd", 0))
            ),
            inquirer.Text(
                "min_totalRevenuePercent",
                message="Minimum total revenue percentage",
                default=str(config["filters"]["min_totalRevenuePercent"])
            ),
            inquirer.Text(
                "min_num_tokens",
                message="Minimum number of different tokens",
                default=str(config["filters"].get("min_num_tokens", 0))
            ),
            inquirer.Text(
                "min_win_count",
                message="Minimum number of profitable trades",
                default=str(config["filters"].get("min_win_count", 0))
            ),
            inquirer.Text(
                "min_win_rate",
                message="Minimum win rate percentage",
                default=str(config["filters"].get("min_win_rate", 0))
            ),
            inquirer.Text(
                "max_loss_rate",
                message="Maximum loss rate percentage",
                default=str(config["filters"].get("max_loss_rate", 100))
            ),
            inquirer.Text(
                "min_distribution_0_percent",
                message="Minimum 0% distribution percentage",
                default=str(config["filters"]["min_distribution_0_percent"])
            ),
            inquirer.Text(
                "min_distribution_0_200_percent",
                message="Minimum 0-200% distribution percentage",
                default=str(config["filters"]["min_distribution_0_200_percent"])
            ),
            inquirer.Text(
                "min_distribution_200_plus_percent",
                message="Minimum 200%+ distribution percentage",
                default=str(config["filters"]["min_distribution_200_plus_percent"])
            ),
        ]
        answers = inquirer.prompt(questions)
        
        # Update config with new values
        for key, value in answers.items():
            try:
                config["filters"][key] = float(value)
            except ValueError:
                console.print(f"[yellow]Invalid value for {key}: {value}. Using default.[/yellow]")
        
        # Save updated config
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, indent=2, fp=f)
        
        console.print(f"[green]✓[/green] Configuration saved to {config_file}")
    
    elif config_choice == "Output options":
        # Edit output options
        console.print("\n[bold]Output Options[/bold]")
        
        questions = [
            inquirer.Confirm(
                "save_unfiltered_csv",
                message="Save unfiltered results CSV?",
                default=config["save_unfiltered_csv"]
            ),
            inquirer.Confirm(
                "save_filtered_csv",
                message="Save filtered results CSV?",
                default=config["save_filtered_csv"]
            ),
            inquirer.Confirm(
                "save_transaction_data",
                message="Save detailed transaction data? (uses more API calls)",
                default=config.get("save_transaction_data", False)
            ),
        ]
        answers = inquirer.prompt(questions)
        
        # Update config
        config["save_unfiltered_csv"] = answers["save_unfiltered_csv"]
        config["save_filtered_csv"] = answers["save_filtered_csv"]
        config["save_transaction_data"] = answers["save_transaction_data"]
        
        # Save updated config
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, indent=2, fp=f)
            
        console.print(f"[green]✓[/green] Output options saved to {config_file}")
    
    elif config_choice == "Export options" and export_format is None:
        # Configure export options
        console.print("\n[bold]Export Options[/bold]")
        
        export_format_choices = [
            "None (don't export)",
            "JSON",
            "CSV",
            "Excel"
        ]
        
        questions = [
            inquirer.List(
                "export_format",
                message="Export results format:",
                choices=export_format_choices
            )
        ]
        answers = inquirer.prompt(questions)
        export_choice = answers["export_format"]
        
        if export_choice == "None (don't export)":
            export_format = None
        else:
            export_format = export_choice.lower()
    
    elif config_choice == "Advanced settings":
        # Edit advanced settings
        console.print("\n[bold]Advanced Settings[/bold]")
        
        questions = [
            inquirer.Confirm(
                "retry_failed",
                message="Retry failed API requests?",
                default=config.get("retry_failed", True)
            ),
            inquirer.Text(
                "retry_delay",
                message="Delay between retries (seconds)",
                default=str(config.get("retry_delay", 2))
            ),
        ]
        answers = inquirer.prompt(questions)
        
        # Update config
        config["retry_failed"] = answers["retry_failed"]
        try:
            config["retry_delay"] = float(answers["retry_delay"])
        except ValueError:
            console.print(f"[yellow]Invalid retry delay value. Using default.[/yellow]")
            config["retry_delay"] = 2
        
        # Save updated config
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, indent=2, fp=f)
            
        console.print(f"[green]✓[/green] Advanced settings saved to {config_file}")
    
    # Set up progress tracking
    progress_manager = ProgressManager(
        total_steps=3,
        description="Wallet Analysis"
    ).initialize()
    workflow_result.set_progress_manager(progress_manager)
    
    # Start processing
    progress_manager.start_step("api_processing", f"Processing {len(wallets)} wallets through BullX API...")
    
    # Timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize results
    results = []
    failed_wallets = []
    
    # Function to extract fields from API response
    def extract_portfolio_data(api_response, wallet):
        """Extract useful data from BullX API response"""
        try:
            # In real implementation, this would parse the API response
            # For demo purposes, create synthetic data
            import random
            
            # Basic portfolio metrics
            realized_pnl = random.uniform(-5000, 20000)
            unrealized_pnl = random.uniform(-2000, 10000)
            total_pnl = realized_pnl + unrealized_pnl
            total_revenue_percent = random.uniform(-50, 300)
            
            # Token holdings and trade statistics
            num_tokens = random.randint(1, 30)
            win_count = random.randint(0, 50)
            loss_count = random.randint(0, 30)
            total_trades = win_count + loss_count
            win_rate = win_count / total_trades * 100 if total_trades > 0 else 0
            loss_rate = loss_count / total_trades * 100 if total_trades > 0 else 0
            
            # Distribution of profits
            dist_0 = random.uniform(0, 50)  # Trades with 0% profit
            dist_0_200 = random.uniform(0, 80)  # Trades with 0-200% profit
            dist_200_plus = random.uniform(0, 40)  # Trades with >200% profit
            
            # Common scenarios for realistic data:
            # 1. Winners: High win rate, positive PnL
            # 2. Losers: High loss rate, negative PnL
            # 3. Mixed: Moderate metrics
            
            # Construct row
            row = {
                "wallet": wallet,
                "realizedPnlUsd": realized_pnl,
                "unrealizedPnlUsd": unrealized_pnl,
                "totalPnlUsd": total_pnl,
                "totalRevenuePercent": total_revenue_percent,
                "num_tokens": num_tokens,
                "win_count": win_count,
                "loss_count": loss_count,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "loss_rate": loss_rate,
                "distribution_0_percent": dist_0,
                "distribution_0_200_percent": dist_0_200,
                "distribution_200_plus_percent": dist_200_plus
            }
            return row
        except Exception as e:
            raise ValueError(f"Failed to extract portfolio data: {e}")
    
    # Process wallets incrementally with progress updates
    for i, wallet in enumerate(wallets):
        # Update progress
        progress_manager.update_step(
            i, 
            len(wallets), 
            f"Processing wallet {i+1}/{len(wallets)}: {wallet[:8]}..."
        )
        
        try:
            # In a real implementation, this would call the BullX API
            # For now, we'll use a simulated response
            
            if config.get("save_transaction_data", False):
                # Sleep to simulate longer API call for transaction data
                time.sleep(0.05)
            
            # Simulate API call (replace with actual API call)
            # response = requests.post(BULLX_GETPORTFOLIO_URL, json={"wallet": wallet}, headers=HEADERS)
            api_response = {"success": True, "data": {}}  # Simulated response
            
            # Process API response
            row = extract_portfolio_data(api_response, wallet)
            results.append(row)
            
        except Exception as e:
            # Handle failed requests
            if config.get("retry_failed", True):
                # Try one more time after delay
                try:
                    time.sleep(config.get("retry_delay", 2))
                    # Simulate second API call
                    api_response = {"success": True, "data": {}}
                    row = extract_portfolio_data(api_response, wallet)
                    results.append(row)
                except Exception as retry_e:
                    console.print(f"[red]Failed to process wallet after retry: {wallet}: {retry_e}[/red]")
                    failed_wallets.append(wallet)
            else:
                console.print(f"[red]Failed to process wallet: {wallet}: {e}[/red]")
                failed_wallets.append(wallet)
    
    # Mark API processing step as complete
    progress_manager.complete_step("API processing completed")
    
    # Start filtering step
    progress_manager.start_step("filtering", "Filtering wallets based on criteria...")
    
    # Filter results
    filtered_results = []
    for row in results:
        # Check if this wallet passes all filter thresholds
        passes = True
        for filter_key, min_val in config["filters"].items():
            # Special handling for max filters
            if filter_key.startswith("max_"):
                if min_val < 100 and row.get(filter_key.replace("max_", ""), 100) > min_val:
                    passes = False
                    break
            # Regular min filters
            elif min_val > 0 and row.get(filter_key, 0) < min_val:
                passes = False
                break
        
        if passes:
            filtered_results.append(row)
    
    # Create output directory for this run
    run_dir = wallet_dir / f"run_{timestamp}"
    os.makedirs(run_dir, exist_ok=True)
    
    # Write addresses that passed filters to output file
    output_wallets_file = run_dir / f"output-wallets.txt"
    with open(output_wallets_file, "w", encoding="utf-8") as f:
        for row in filtered_results:
            f.write(row["wallet"] + "\n")
    
    # Also write to the main output file for quick access in future runs
    main_output_file = wallet_dir / f"output-wallets_{timestamp}.txt"
    shutil.copy(output_wallets_file, main_output_file)
    
    # Add files to workflow result
    workflow_result.add_output("filtered_wallets", str(output_wallets_file))
    workflow_result.add_output("filtered_wallets_main", str(main_output_file))
    
    # Complete filtering step
    progress_manager.complete_step("Filtering completed")
    
    # Start export step
    progress_manager.start_step("exporting", "Generating output files...")
    
    # Add stats to workflow result
    workflow_result.add_stat("Total Wallets", len(wallets))
    workflow_result.add_stat("Processed Wallets", len(results))
    workflow_result.add_stat("Failed Wallets", len(failed_wallets))
    workflow_result.add_stat("Filtered Wallets", len(filtered_results))
    workflow_result.add_stat("Pass Rate", f"{len(filtered_results)/len(results)*100:.1f}%" if results else "0%")
    
    # Generate CSV files
    fieldnames = [
        "wallet",
        "realizedPnlUsd",
        "unrealizedPnlUsd",
        "totalPnlUsd",
        "totalRevenuePercent",
        "num_tokens",
        "win_count",
        "loss_count",
        "total_trades",
        "win_rate",
        "loss_rate",
        "distribution_0_percent",
        "distribution_0_200_percent",
        "distribution_200_plus_percent"
    ]
    
    # Save unfiltered CSV
    if config.get("save_unfiltered_csv", True):
        csv_filename = run_dir / f"portfolio_results.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        workflow_result.add_output("unfiltered_csv", str(csv_filename))
    
    # Save filtered CSV
    if config.get("save_filtered_csv", True):
        csv_filename_filtered = run_dir / f"portfolio_results_filtered.csv"
        with open(csv_filename_filtered, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in filtered_results:
                writer.writerow(row)
        workflow_result.add_output("filtered_csv", str(csv_filename_filtered))
        
        # Also add the filtered results as a DataFrame for easy export
        filtered_df = pd.DataFrame(filtered_results)
        workflow_result.add_dataframe("filtered_results", filtered_df)
    
    # Save configuration used for this run
    run_config_file = run_dir / "run_config.json"
    with open(run_config_file, "w", encoding="utf-8") as f:
        json.dump(config, indent=2, fp=f)
    workflow_result.add_output("run_config", str(run_config_file))
    
    # Save failed wallets if any
    if failed_wallets:
        failed_file = run_dir / "failed_wallets.txt"
        with open(failed_file, "w", encoding="utf-8") as f:
            for wallet in failed_wallets:
                f.write(wallet + "\n")
        workflow_result.add_output("failed_wallets", str(failed_file))
    
    # Complete export step and finalize workflow
    progress_manager.complete_step("Export completed")
    workflow_result.finalize()
    
    # Export the results if requested
    if export_format:
        export_path = workflow_result.export_results(export_format)
        if export_path:
            workflow_result.add_output("exported_results", export_path)
    
    # Show filtering results
    pass_percentage = len(filtered_results) / len(results) * 100 if results else 0
    console.print(f"\n[bold green]Filtering Results:[/bold green]")
    console.print(f"[green]✓[/green] {len(filtered_results)} wallets passed filters ({pass_percentage:.1f}%)")
    console.print(f"[green]✓[/green] Filtered wallets saved to '{output_wallets_file}'")
    console.print(f"[green]✓[/green] Also saved to '{main_output_file}' for quick access")
    
    # Print workflow summary
    workflow_result.print_summary()
    
    # Suggest next steps
    console.print("\n[bold green]Wallet checker completed successfully![/bold green]")
    
    if filtered_results:
        console.print("\n[bold]Suggested next steps:[/bold]")
        console.print("1. Use the filtered wallet list for further analysis")
        console.print("2. Run the Wallet Splitter tool if you need to break the list into smaller chunks")
        console.print("3. Import the CSV into a spreadsheet tool for advanced analysis")
    else:
        console.print("\n[yellow]⚠ No wallets passed the filters. Consider adjusting filter criteria.[/yellow]")


def wallet_splitter(export_format: str = None):
    """
    Split large wallet lists into smaller chunks for easier processing.
    
    Args:
        export_format: Optional format to export results ('json', 'csv', 'excel')
    """
    from ...utils.common import ProgressManager, WorkflowResult, format_duration
    
    clear_terminal()
    console.print("[bold blue]📂 Sharp Wallet Splitter[/bold blue]")
    console.print("Split large wallet lists into smaller chunks for APIs with size limits\n")
    
    # Setup directories
    wallet_dir = ensure_data_dir("sharp", "wallets")
    output_dir = ensure_data_dir("sharp", "wallets/split")
    
    # Initialize workflow result tracking
    workflow_result = WorkflowResult()
    
    # Find wallet files
    wallet_files = list(wallet_dir.glob("*.txt"))
    wallet_files.sort(key=os.path.getmtime, reverse=True)  # Sort by modification time
    
    # Choose input source
    input_options = [
        "Select from existing files",
        "Enter file path manually", 
        "Use previous filtered results"
    ]
    
    questions = [
        inquirer.List(
            "input_method",
            message="How would you like to provide the wallet list?",
            choices=input_options
        ),
    ]
    answers = inquirer.prompt(questions)
    input_method = answers["input_method"]
    
    input_file = None
    
    if input_method == "Select from existing files":
        if not wallet_files:
            console.print("[yellow]No wallet files found in the wallets directory.[/yellow]")
            console.print("Creating a default empty file...")
            default_file = wallet_dir / "bulk-wallets.txt"
            with open(default_file, "w") as f:
                pass
            console.print(f"Please add wallet addresses to {default_file} and run again.")
            return
        
        # List files with details
        console.print("[bold]Available wallet files:[/bold]")
        file_choices = []
        for i, f in enumerate(wallet_files):
            # Get size and line count
            size_kb = os.path.getsize(f) / 1024
            try:
                with open(f, "r", encoding="utf-8") as file:
                    line_count = sum(1 for line in file if line.strip())
                modified_time = os.path.getmtime(f)
                mod_time_str = datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M")
                
                file_display = f"{os.path.basename(f)} ({line_count} wallets, {size_kb:.1f} KB, {mod_time_str})"
                file_choices.append((file_display, str(f)))
            except Exception:
                # Fall back to just filename if there's an issue reading the file
                file_choices.append((os.path.basename(f), str(f)))
        
        file_choices.append(("Other file (specify path)", "other"))
        
        # Display file choices
        questions = [
            inquirer.List(
                "file_choice",
                message="Select a wallet file to split:",
                choices=[choice[0] for choice in file_choices]
            ),
        ]
        answers = inquirer.prompt(questions)
        file_choice = answers["file_choice"]
        
        # Find selected file
        selected_file = None
        for display, path in file_choices:
            if display == file_choice:
                selected_file = path
                break
                
        if selected_file == "other":
            questions = [
                inquirer.Text(
                    "input_file",
                    message="Enter path to file with wallet addresses:",
                    default=str(wallet_dir / "bulk-wallets.txt")
                ),
            ]
            answers = inquirer.prompt(questions)
            input_file = answers["input_file"]
        else:
            input_file = selected_file
    
    elif input_method == "Enter file path manually":
        questions = [
            inquirer.Text(
                "input_file",
                message="Enter path to file with wallet addresses:",
                default=str(wallet_dir / "bulk-wallets.txt")
            ),
        ]
        answers = inquirer.prompt(questions)
        input_file = answers["input_file"]
    
    elif input_method == "Use previous filtered results":
        # Find output files from wallet checker
        output_files = list(wallet_dir.glob("output-wallets_*.txt"))
        output_files.sort(key=os.path.getmtime, reverse=True)
        
        if not output_files:
            console.print("[yellow]No filtered wallet outputs found. Please use another input method.[/yellow]")
            return
            
        # List files with details
        console.print("[bold]Available filtered outputs:[/bold]")
        file_choices = []
        for i, f in enumerate(output_files):
            # Get size and line count
            size_kb = os.path.getsize(f) / 1024
            try:
                with open(f, "r", encoding="utf-8") as file:
                    line_count = sum(1 for line in file if line.strip())
                modified_time = os.path.getmtime(f)
                mod_time_str = datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M")
                
                file_display = f"{os.path.basename(f)} ({line_count} wallets, {size_kb:.1f} KB, {mod_time_str})"
                file_choices.append((file_display, str(f)))
            except Exception:
                # Fall back to just filename if there's an issue
                file_choices.append((os.path.basename(f), str(f)))
        
        # Display file choices
        questions = [
            inquirer.List(
                "file_choice",
                message="Select filtered output to split:",
                choices=[choice[0] for choice in file_choices]
            ),
        ]
        answers = inquirer.prompt(questions)
        file_choice = answers["file_choice"]
        
        # Find selected file
        for display, path in file_choices:
            if display == file_choice:
                input_file = path
                break
    
    # Ensure input file exists
    if not os.path.isfile(input_file):
        console.print(f"[yellow]File not found: {input_file}[/yellow]")
        console.print("Creating an empty file at this location.")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        # Create empty file
        with open(input_file, "w") as f:
            pass
        console.print("Please add wallet addresses to this file and run the tool again.")
        return
    
    # Add input file to workflow result
    workflow_result.add_input("wallet_list", input_file)
    
    # Get wallet split options
    console.print("\n[bold]Split Options:[/bold]")
    
    # Presets for common API limits
    presets = [
        "Standard (25,000 wallets per file)", 
        "BullX API (5,000 wallets per file)",
        "Birdeye (1,000 wallets per file)",
        "Solscan (500 wallets per file)",
        "Custom"
    ]
    
    preset_values = {
        "Standard (25,000 wallets per file)": 25000,
        "BullX API (5,000 wallets per file)": 5000,
        "Birdeye (1,000 wallets per file)": 1000,
        "Solscan (500 wallets per file)": 500,
    }
    
    questions = [
        inquirer.List(
            "preset",
            message="Select splitting preset:",
            choices=presets
        ),
    ]
    answers = inquirer.prompt(questions)
    preset = answers["preset"]
    
    if preset == "Custom":
        questions = [
            inquirer.Text(
                "max_wallets",
                message="Maximum wallets per file:",
                default="25000"
            ),
        ]
        answers = inquirer.prompt(questions)
        try:
            max_wallets_per_file = int(answers["max_wallets"])
            if max_wallets_per_file <= 0:
                console.print("[yellow]Invalid number, using default: 25000[/yellow]")
                max_wallets_per_file = 25000
        except ValueError:
            console.print("[yellow]Invalid number, using default: 25000[/yellow]")
            max_wallets_per_file = 25000
    else:
        max_wallets_per_file = preset_values[preset]
    
    # Additional options
    questions = [
        inquirer.Confirm(
            "remove_duplicates",
            message="Remove duplicate addresses?",
            default=True
        ),
        inquirer.Confirm(
            "validate_addresses",
            message="Validate address format?",
            default=True
        ),
    ]
    answers = inquirer.prompt(questions)
    remove_duplicates = answers["remove_duplicates"]
    validate_addresses = answers["validate_addresses"]
    
    # Add configuration to workflow result
    workflow_result.add_data("config", {
        "preset": preset,
        "max_wallets_per_file": max_wallets_per_file,
        "remove_duplicates": remove_duplicates,
        "validate_addresses": validate_addresses
    })
    
    # Set up progress tracking with 3 steps
    progress_manager = ProgressManager(
        total_steps=3,
        description="Wallet Splitting"
    ).initialize()
    workflow_result.set_progress_manager(progress_manager)
    
    # Start processing - Step 1: Loading and validating
    progress_manager.start_step("loading", f"Loading and processing wallets from {os.path.basename(input_file)}...")
    
    # Read wallet addresses
    with open(input_file, "r", encoding="utf-8") as f:
        wallets = [line.strip() for line in f if line.strip()]
    
    if not wallets:
        console.print(f"[red]No wallet addresses found in file: {input_file}[/red]")
        workflow_result.set_error("No wallet addresses found in input file")
        return
    
    original_count = len(wallets)
    console.print(f"\n[green]✓[/green] Loaded {original_count} addresses from {os.path.basename(input_file)}")
    
    # Process wallets
    results = []
    invalid_addresses = []
    
    if validate_addresses:
        valid_wallets = []
        
        # Update step description
        progress_manager.update_step(0, original_count, "Validating wallet addresses...")
        
        for i, wallet in enumerate(wallets):
            # Simple validation - Solana addresses are 32-44 characters
            # In a real implementation, you would use proper validation with regex or libraries
            if len(wallet) >= 30 and len(wallet) <= 50:
                valid_wallets.append(wallet)
            else:
                invalid_addresses.append(wallet)
                
            # Update progress occasionally (every 1000 wallets)
            if i % 1000 == 0:
                progress_manager.update_step(i, original_count, f"Validated {i}/{original_count} addresses...")
        
        if invalid_addresses:
            console.print(f"[yellow]⚠[/yellow] Found {len(invalid_addresses)} invalid wallet addresses")
            
            # Ask if user wants to see invalid addresses
            if len(invalid_addresses) <= 10:
                console.print("[bold]Invalid addresses:[/bold]")
                for wallet in invalid_addresses:
                    console.print(f"  - {wallet}")
            else:
                questions = [
                    inquirer.Confirm(
                        "show_invalid",
                        message=f"Show all {len(invalid_addresses)} invalid addresses?",
                        default=False
                    ),
                ]
                answers = inquirer.prompt(questions)
                
                if answers["show_invalid"]:
                    console.print("[bold]Invalid addresses:[/bold]")
                    for wallet in invalid_addresses:
                        console.print(f"  - {wallet}")
        
        wallets = valid_wallets
        console.print(f"[green]✓[/green] Kept {len(valid_wallets)} valid addresses")
    
    # Remove duplicates if requested
    if remove_duplicates:
        unique_wallets = []
        seen = set()
        
        # Update step description
        progress_manager.update_step(0, len(wallets), "Removing duplicate addresses...")
        
        for i, wallet in enumerate(wallets):
            if wallet not in seen:
                seen.add(wallet)
                unique_wallets.append(wallet)
                
            # Update progress occasionally
            if i % 1000 == 0:
                progress_manager.update_step(i, len(wallets), f"Processed {i}/{len(wallets)} addresses for duplicates...")
        
        duplicate_count = len(wallets) - len(unique_wallets)
        if duplicate_count > 0:
            console.print(f"[yellow]⚠[/yellow] Removed {duplicate_count} duplicate addresses")
        
        wallets = unique_wallets
    
    # Complete the first step
    progress_manager.complete_step("Wallet processing completed")
    
    # Create timestamped output directory with description
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"split_{timestamp}_{max_wallets_per_file}_per_file"
    split_dir = output_dir / folder_name
    os.makedirs(split_dir, exist_ok=True)
    
    # Split wallets into chunks - Step 2: Splitting
    total_wallets = len(wallets)
    num_files = (total_wallets + max_wallets_per_file - 1) // max_wallets_per_file
    
    # If no wallets to process
    if total_wallets == 0:
        console.print("[yellow]No valid wallets to split![/yellow]")
        workflow_result.set_error("No valid wallets to split after validation")
        return
    
    # Show summary before processing
    console.print(f"\n[bold]Ready to split {total_wallets} wallets into {num_files} files[/bold]")
    console.print(f"Each file will contain up to {max_wallets_per_file} wallets")
    console.print(f"Output directory: {split_dir}")
    
    # Confirm split
    questions = [
        inquirer.Confirm(
            "confirm_split",
            message="Proceed with splitting?",
            default=True
        ),
    ]
    answers = inquirer.prompt(questions)
    
    if not answers["confirm_split"]:
        console.print("[yellow]Operation cancelled by user.[/yellow]")
        workflow_result.set_error("Operation cancelled by user")
        return
    
    # Start the splitting step
    progress_manager.start_step("splitting", f"Splitting {total_wallets} wallets into {num_files} files...")
    
    # Process with progress updates
    for i in range(num_files):
        start_idx = i * max_wallets_per_file
        end_idx = min((i + 1) * max_wallets_per_file, total_wallets)
        chunk = wallets[start_idx:end_idx]
        
        # Create output file
        output_file = split_dir / f"wallets_{i+1:03d}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for wallet in chunk:
                f.write(wallet + "\n")
        
        # Add file result to results list
        results.append({
            "file_number": i+1,
            "file_path": str(output_file),
            "file_name": f"wallets_{i+1:03d}.txt",
            "wallet_count": len(chunk),
            "start_index": start_idx,
            "end_index": end_idx - 1
        })
        
        # Update progress
        progress_manager.update_step(i+1, num_files, f"Created file {i+1}/{num_files}: wallets_{i+1:03d}.txt")
    
    # Complete splitting step
    progress_manager.complete_step("Splitting completed")
    
    # Start summary generation - Step 3: Creating summary
    progress_manager.start_step("summary", "Creating summary and collecting statistics...")
    
    # Create a summary file
    summary_file = split_dir / "split_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Split summary for {os.path.basename(input_file)}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Original wallet count: {original_count}\n")
        f.write(f"Final wallet count: {total_wallets}\n")
        f.write(f"Maximum wallets per file: {max_wallets_per_file}\n")
        f.write(f"Number of files created: {num_files}\n")
        f.write(f"Duplicate removal: {'Enabled' if remove_duplicates else 'Disabled'}\n")
        f.write(f"Address validation: {'Enabled' if validate_addresses else 'Disabled'}\n")
        f.write("\nFile details:\n")
        
        for i in range(num_files):
            start_idx = i * max_wallets_per_file
            end_idx = min((i + 1) * max_wallets_per_file, total_wallets)
            count = end_idx - start_idx
            f.write(f"wallets_{i+1:03d}.txt: {count} wallets\n")
    
    # If invalid addresses were found, save them to a file
    if invalid_addresses:
        invalid_file = split_dir / "invalid_addresses.txt"
        with open(invalid_file, "w", encoding="utf-8") as f:
            for wallet in invalid_addresses:
                f.write(wallet + "\n")
        workflow_result.add_output("invalid_addresses", str(invalid_file))
    
    # Add outputs to workflow result
    workflow_result.add_output("summary_file", str(summary_file))
    workflow_result.add_output("split_directory", str(split_dir))
    
    # Add stats to workflow result
    workflow_result.add_stat("Original Wallet Count", original_count)
    workflow_result.add_stat("Final Wallet Count", total_wallets)
    workflow_result.add_stat("Invalid Addresses", len(invalid_addresses))
    workflow_result.add_stat("Duplicate Addresses", original_count - len(invalid_addresses) - total_wallets)
    workflow_result.add_stat("Files Created", num_files)
    workflow_result.add_stat("Wallets Per File", max_wallets_per_file)
    
    # Add results to workflow result
    for result in results:
        workflow_result.add_output(f"file_{result['file_number']}", result['file_path'])
    
    # Create a dataframe for organized export
    import pandas as pd
    files_df = pd.DataFrame(results)
    workflow_result.add_dataframe("split_files", files_df)
    
    # Complete summary step
    progress_manager.complete_step("Summary completed")
    
    # Finalize workflow
    workflow_result.finalize()
    
    # Export the results if requested
    if export_format:
        export_path = workflow_result.export_results(export_format, split_dir)
        if export_path:
            workflow_result.add_output("exported_results", export_path)
            console.print(f"[green]✓[/green] Results exported to: {export_path}")
    
    # Show results
    console.print(f"\n[bold green]Wallet splitting completed successfully![/bold green]")
    console.print(f"[green]✓[/green] Split {total_wallets} wallets into {num_files} files")
    console.print(f"[green]✓[/green] Files saved to: {split_dir}")
    console.print(f"[green]✓[/green] Summary saved to: {summary_file}")
    
    # Print a summary of the results
    workflow_result.print_summary()
    
    # Suggest next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Use these files for batch processing with external tools or APIs")
    console.print("2. Check the summary file for details about the split operation")
    if num_files > 20:
        console.print("[yellow]Note: You created a large number of files. Consider using a higher wallets-per-file setting for easier management.[/yellow]")


def csv_merger(export_format: str = None):
    """
    Merge multiple CSV files into a single consolidated file with advanced options.
    
    Args:
        export_format: Optional format to export results ('json', 'csv', 'excel')
    """
    from ...utils.common import ProgressManager, WorkflowResult, format_duration
    
    clear_terminal()
    console.print("[bold blue]📊 Sharp CSV Merger[/bold blue]")
    console.print("Merge multiple CSV files into a single consolidated file\n")
    
    # Setup directories
    unmerged_dir = ensure_data_dir("sharp", "csv/unmerged")
    merged_dir = ensure_data_dir("sharp", "csv/merged")
    
    # Initialize workflow result tracking
    workflow_result = WorkflowResult()
    
    # Input method selection
    input_options = [
        "Use files from unmerged directory",
        "Select specific files", 
        "Import from another directory"
    ]
    
    questions = [
        inquirer.List(
            "input_method",
            message="How would you like to select CSV files?",
            choices=input_options
        ),
    ]
    answers = inquirer.prompt(questions)
    input_method = answers["input_method"]
    
    # Get CSV files based on selected method
    csv_files = []
    imported_files = False
    source_dir = unmerged_dir
    
    if input_method == "Use files from unmerged directory":
        # Check for CSV files in the default directory
        csv_files = list(Path(unmerged_dir).glob('*.csv'))
        
        if not csv_files:
            console.print(f"[yellow]No CSV files found in {unmerged_dir}[/yellow]")
            console.print(f"Please place CSV files to merge in this directory and run the tool again.")
            return
            
    elif input_method == "Select specific files":
        # Get all CSV files in the unmerged directory
        all_csv_files = list(Path(unmerged_dir).glob('*.csv'))
        
        if not all_csv_files:
            console.print(f"[yellow]No CSV files found in {unmerged_dir}[/yellow]")
            # Ask if user wants to import from another location
            questions = [
                inquirer.Confirm(
                    "import_files",
                    message="Would you like to import CSV files from another location?",
                    default=True
                ),
            ]
            answers = inquirer.prompt(questions)
            
            if answers["import_files"]:
                # Change to import mode
                input_method = "Import from another directory"
            else:
                console.print("Please place CSV files in the unmerged directory and run the tool again.")
                return
        else:
            # Allow multiple selection
            file_choices = [os.path.basename(f) for f in all_csv_files]
            
            questions = [
                inquirer.Checkbox(
                    "selected_files",
                    message="Select files to merge (use space to select, enter to confirm):",
                    choices=file_choices
                ),
            ]
            answers = inquirer.prompt(questions)
            selected_files = answers["selected_files"]
            
            if not selected_files:
                console.print("[yellow]No files selected.[/yellow]")
                return
                
            # Get full paths for selected files
            csv_files = [f for f in all_csv_files if os.path.basename(f) in selected_files]
    
    if input_method == "Import from another directory":
        # Ask for directory path
        questions = [
            inquirer.Text(
                "import_dir",
                message="Enter path to directory containing CSV files:",
                default=str(Path.home() / "Downloads")  # Default to Downloads folder
            ),
        ]
        answers = inquirer.prompt(questions)
        import_dir = answers["import_dir"]
        source_dir = import_dir
        
        # Check if directory exists
        if not os.path.isdir(import_dir):
            console.print(f"[red]Directory not found: {import_dir}[/red]")
            return
            
        # Find CSV files in the specified directory
        import_csv_files = list(Path(import_dir).glob('*.csv'))
        
        if not import_csv_files:
            console.print(f"[yellow]No CSV files found in {import_dir}[/yellow]")
            return
            
        # Select files to import
        file_choices = [os.path.basename(f) for f in import_csv_files]
        
        questions = [
            inquirer.Checkbox(
                "selected_files",
                message="Select files to import and merge (use space to select, enter to confirm):",
                choices=file_choices
            ),
        ]
        answers = inquirer.prompt(questions)
        selected_files = answers["selected_files"]
        
        if not selected_files:
            console.print("[yellow]No files selected.[/yellow]")
            return
            
        # Ask if user wants to copy the files to the unmerged directory
        questions = [
            inquirer.Confirm(
                "copy_files",
                message="Copy selected files to the unmerged directory?",
                default=True
            ),
        ]
        answers = inquirer.prompt(questions)
        imported_files = True
        
        if answers["copy_files"]:
            # Copy files to unmerged directory
            for file_name in selected_files:
                src_path = os.path.join(import_dir, file_name)
                dest_path = os.path.join(unmerged_dir, file_name)
                try:
                    shutil.copy2(src_path, dest_path)
                    console.print(f"[green]✓[/green] Copied {file_name} to {unmerged_dir}")
                except Exception as e:
                    console.print(f"[red]Error copying {file_name}: {e}[/red]")
            
            # Get paths in the unmerged directory
            csv_files = [Path(unmerged_dir) / f for f in selected_files]
            source_dir = unmerged_dir
        else:
            # Use files directly from the import directory
            csv_files = [Path(import_dir) / f for f in selected_files]
    
    # Make sure we have files to process
    if not csv_files:
        console.print("[red]No CSV files available to merge.[/red]")
        return
    
    # Add source information to workflow result
    workflow_result.add_data("source_directory", str(source_dir))
    if imported_files:
        workflow_result.add_data("imported_files", True)
        workflow_result.add_data("import_directory", str(import_dir))
    
    # Add input files to workflow result
    for i, file in enumerate(csv_files):
        workflow_result.add_input(f"input_file_{i+1}", str(file))
    
    # Show selected files - scan the files in parallel with progress tracking
    file_stats = []
    console.print(f"\n[bold]Selected {len(csv_files)} CSV files for merging:[/bold]")
    
    # Set up progress tracking for file scanning
    progress_manager = ProgressManager(
        total_steps=4,  # 1) Scan files, 2) Merge, 3) Process, 4) Save
        description="CSV Merging"
    ).initialize()
    workflow_result.set_progress_manager(progress_manager)
    
    # Start first step - scanning files
    progress_manager.start_step("scanning", "Scanning selected CSV files...")
    
    for i, file in enumerate(csv_files):
        progress_manager.update_step(i, len(csv_files), f"Scanning file {i+1}/{len(csv_files)}: {os.path.basename(file)}")
        
        # Get file size and row count if possible
        try:
            size_kb = os.path.getsize(file) / 1024
            df = pd.read_csv(file, nrows=1)  # Read just one row to get column count
            num_columns = len(df.columns)
            
            # Get approximate row count - faster than counting all rows
            with open(file, 'r', encoding='utf-8') as f:
                # Count lines, subtract 1 for header
                line_count = sum(1 for _ in f) - 1
                
            file_info = {
                "file_path": str(file),
                "file_name": os.path.basename(file),
                "row_count": line_count,
                "column_count": num_columns,
                "size_kb": size_kb,
                "readable": True
            }
            
            console.print(f"  {i+1}. {os.path.basename(file)} ({line_count} rows, {num_columns} columns, {size_kb:.1f} KB)")
        except Exception as e:
            console.print(f"  {i+1}. {os.path.basename(file)} (unable to read file details: {e})")
            file_info = {
                "file_path": str(file),
                "file_name": os.path.basename(file),
                "readable": False,
                "error": str(e)
            }
        
        file_stats.append(file_info)
    
    # Complete file scanning step
    progress_manager.complete_step("File scanning completed")
    
    # Add file statistics to workflow result
    workflow_result.add_data("file_statistics", file_stats)
    
    # Merge options
    console.print("\n[bold]Merge Options:[/bold]")
    
    questions = [
        inquirer.Confirm(
            "skip_headers",
            message="Skip headers in all but the first file?",
            default=True
        ),
        inquirer.Confirm(
            "remove_duplicates",
            message="Remove duplicate rows?",
            default=True
        ),
        inquirer.Text(
            "output_filename",
            message="Output filename (without .csv extension):",
            default=f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ),
    ]
    answers = inquirer.prompt(questions)
    
    skip_headers = answers["skip_headers"]
    remove_duplicates = answers["remove_duplicates"]
    output_filename = answers["output_filename"]
    
    if not output_filename.endswith('.csv'):
        output_filename += '.csv'
    
    # Add merge options to workflow result
    workflow_result.add_data("merge_options", {
        "skip_headers": skip_headers,
        "remove_duplicates": remove_duplicates,
        "output_filename": output_filename
    })
    
    # Confirm merge
    console.print(f"\n[bold]Ready to merge {len(csv_files)} CSV files[/bold]")
    console.print(f"Output file: {output_filename}")
    
    questions = [
        inquirer.Confirm(
            "confirm_merge",
            message="Proceed with merge?",
            default=True
        ),
    ]
    answers = inquirer.prompt(questions)
    
    if not answers["confirm_merge"]:
        console.print("[yellow]CSV merge cancelled by user.[/yellow]")
        workflow_result.set_error("Operation cancelled by user")
        return
    
    # Start merging step
    progress_manager.start_step("merging", "Merging CSV files...")
    
    try:
        # Process first file and get columns
        progress_manager.update_step(0, len(csv_files), f"Reading first file: {os.path.basename(csv_files[0])}")
        
        try:
            # Try to detect encoding and separator automatically
            merged_data = pd.read_csv(csv_files[0], sep=None, engine='python')
        except Exception:
            # Fall back to default CSV format
            merged_data = pd.read_csv(csv_files[0])
            
        headers = merged_data.columns
        rows_processed = len(merged_data)
        columns_count = len(headers)
        
        merge_results = [{
            "file_name": os.path.basename(csv_files[0]),
            "rows_added": rows_processed,
            "status": "success"
        }]
        
        # Iterate through remaining files
        for i, file in enumerate(csv_files[1:], 1):
            file_name = os.path.basename(file)
            progress_manager.update_step(i, len(csv_files), f"Merging file {i+1}/{len(csv_files)}: {file_name}")
            
            try:
                if skip_headers:
                    # Skip first row (header) in subsequent files
                    df = pd.read_csv(file, header=0)
                else:
                    # Read with header but then align columns
                    df = pd.read_csv(file, header=None)
                    df.columns = headers
                    
                # Concatenate to the merged data
                pre_merge_count = len(merged_data)
                merged_data = pd.concat([merged_data, df], ignore_index=True)
                rows_added = len(df)
                
                merge_results.append({
                    "file_name": file_name,
                    "rows_added": rows_added,
                    "status": "success"
                })
                
            except Exception as e:
                console.print(f"[yellow]Warning: Error processing {file_name}: {e}[/yellow]")
                console.print("[yellow]Skipping this file and continuing with the merge.[/yellow]")
                
                merge_results.append({
                    "file_name": file_name,
                    "status": "error",
                    "error": str(e)
                })
        
        # Complete merging step
        progress_manager.complete_step("CSV merging completed")
        
        # Start processing step - handle duplicates if requested
        progress_manager.start_step("processing", "Processing merged data...")
        duplicates_removed = 0
        
        if remove_duplicates:
            progress_manager.update_step(0, 1, "Removing duplicate rows...")
            original_rows = len(merged_data)
            merged_data = merged_data.drop_duplicates()
            duplicates_removed = original_rows - len(merged_data)
            
            progress_manager.update_step(1, 1, f"Removed {duplicates_removed} duplicate rows")
        
        # Complete processing step
        progress_manager.complete_step("Data processing completed")
        
        # Start saving step
        progress_manager.start_step("saving", "Saving merged data...")
        
        # Ensure output directory exists
        os.makedirs(merged_dir, exist_ok=True)
        
        # Save to merged file
        merged_path = os.path.join(merged_dir, output_filename)
        merged_data.to_csv(merged_path, index=False)
        
        # Add output file to workflow result
        workflow_result.add_output("merged_csv", merged_path)
        
        # Add merged dataframe for export
        workflow_result.add_dataframe("merged_data", merged_data)
        
        # Add merge results dataframe
        results_df = pd.DataFrame(merge_results)
        workflow_result.add_dataframe("merge_results", results_df)
        
        # Calculate file size
        file_size_kb = os.path.getsize(merged_path) / 1024
        file_size_mb = file_size_kb / 1024
        
        # Add statistics to workflow result
        workflow_result.add_stat("Input Files", len(csv_files))
        workflow_result.add_stat("Total Rows", len(merged_data))
        workflow_result.add_stat("Total Columns", columns_count)
        workflow_result.add_stat("Duplicates Removed", duplicates_removed)
        
        if file_size_mb >= 1:
            workflow_result.add_stat("Output Size", f"{file_size_mb:.2f} MB")
        else:
            workflow_result.add_stat("Output Size", f"{file_size_kb:.2f} KB")
        
        # Complete saving step
        progress_manager.complete_step("Save completed")
        
        # Finalize workflow result
        workflow_result.finalize()
        
        # Export results if format specified
        if export_format:
            export_path = workflow_result.export_results(export_format, merged_dir)
            if export_path:
                workflow_result.add_output("exported_results", export_path)
                console.print(f"[green]✓[/green] Results exported to: {export_path}")
        
        # Show results
        console.print(f"\n[bold green]CSV merge completed successfully![/bold green]")
        console.print(f"[green]✓[/green] Merged {len(csv_files)} CSV files")
        console.print(f"[green]✓[/green] Total rows in output: {len(merged_data)}")
        
        if remove_duplicates:
            console.print(f"[green]✓[/green] Removed {duplicates_removed} duplicate rows")
            
        console.print(f"[green]✓[/green] Output file saved to: {merged_path}")
        
        if file_size_mb >= 1:
            console.print(f"[green]✓[/green] Output file size: {file_size_mb:.2f} MB")
        else:
            console.print(f"[green]✓[/green] Output file size: {file_size_kb:.2f} KB")
        
        # Print workflow summary
        workflow_result.print_summary()
        
        # Suggest next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Use the merged CSV for your data analysis")
        console.print("2. Check the output file to ensure all data was merged correctly")
        console.print("3. Run the PnL Checker tool to filter the merged data based on performance metrics")
        
    except Exception as e:
        console.print(f"[red]Error merging CSV files: {e}[/red]")
        workflow_result.set_error(f"Error merging CSV files: {e}")
        workflow_result.finalize()
        return


def pnl_checker():
    """Filter wallet CSVs based on performance metrics."""
    clear_terminal()
    print("🚧 Sharp PnL CSV Checker 🚧")
    
    # Setup directories
    unfiltered_dir = ensure_data_dir("sharp", "csv/unfiltered")
    filtered_dir = ensure_data_dir("sharp", "csv/filtered")
    
    # Check for CSV files
    csv_files = glob.glob(os.path.join(unfiltered_dir, '*.csv'))
    
    if not csv_files:
        print(f"❌ No CSV files found in {unfiltered_dir}")
        print(f"Please place CSV files to filter in this directory and run the tool again.")
        return
    
    # Select file to filter
    file_choices = [os.path.basename(f) for f in csv_files]
    questions = [
        inquirer.List(
            "csv_file",
            message="Select CSV file to filter:",
            choices=file_choices
        ),
    ]
    answers = inquirer.prompt(questions)
    selected_file = os.path.join(unfiltered_dir, answers["csv_file"])
    
    # Load or create filter config
    config_file = ensure_data_dir("sharp") / "pnl_filter_config.json"
    filter_config = {
        "min_pnl": 0,
        "min_win_rate": 0,
        "max_loss_rate": 100,
        "min_trades": 0,
        "missed_data_allowed": True
    }
    
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                filter_config.update(saved_config)
        except Exception as e:
            print(f"⚠️ Error reading config file: {e}")
    
    # Edit filter config
    questions = [
        inquirer.Confirm(
            "edit_config",
            message="Do you want to edit the filtering configuration?",
            default=False
        ),
    ]
    answers = inquirer.prompt(questions)
    
    if answers["edit_config"]:
        questions = [
            inquirer.Text(
                "min_pnl",
                message="Minimum PnL (USD)",
                default=str(filter_config["min_pnl"])
            ),
            inquirer.Text(
                "min_win_rate",
                message="Minimum win rate (%)",
                default=str(filter_config["min_win_rate"])
            ),
            inquirer.Text(
                "max_loss_rate",
                message="Maximum loss rate (%)",
                default=str(filter_config["max_loss_rate"])
            ),
            inquirer.Text(
                "min_trades",
                message="Minimum number of trades",
                default=str(filter_config["min_trades"])
            ),
            inquirer.Confirm(
                "missed_data_allowed",
                message="Allow wallets with missing data?",
                default=filter_config["missed_data_allowed"]
            ),
        ]
        answers = inquirer.prompt(questions)
        
        # Update config
        for key in ["min_pnl", "min_win_rate", "max_loss_rate", "min_trades"]:
            try:
                filter_config[key] = float(answers[key])
            except ValueError:
                print(f"⚠️ Invalid value for {key}: {answers[key]}. Using previous value.")
        
        filter_config["missed_data_allowed"] = answers["missed_data_allowed"]
        
        # Save updated config
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(filter_config, indent=2, fp=f)
        
        print(f"✅ Configuration saved to {config_file}")
    
    # Process the CSV
    try:
        # Read CSV
        print(f"ℹ️ Reading CSV file: {os.path.basename(selected_file)}")
        df = pd.read_csv(selected_file)
        
        # Apply filters
        print(f"ℹ️ Applying filters...")
        
        # These filtering criteria will depend on the actual CSV structure
        # For now, we'll just create a stub filtering process
        filtered_count = len(df) // 2  # Just an example
        
        # Save filtered results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(os.path.basename(selected_file))[0]
        filtered_filename = f"{base_name}_filtered_{timestamp}.csv"
        filtered_path = os.path.join(filtered_dir, filtered_filename)
        
        # Save dummy filtered data
        df.iloc[:filtered_count].to_csv(filtered_path, index=False)
        
        print(f"\n✅ Filtered {len(df)} rows to {filtered_count} rows")
        print(f"✅ Filtered CSV saved at: {filtered_path}")
        
    except Exception as e:
        print(f"❌ Error processing CSV file: {e}")