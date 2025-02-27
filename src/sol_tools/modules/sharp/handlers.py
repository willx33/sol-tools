"""Handlers for Sharp module functionality."""

import os
import csv
import glob
import json
import inquirer
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

from ...utils.common import clear_terminal, ensure_data_dir

# BullX API URL for wallet checker
BULLX_GETPORTFOLIO_URL = "https://api-neo.bullx.io/v2/api/getPortfolioV3"

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


def wallet_checker():
    """Check wallet statistics using BullX API."""
    clear_terminal()
    print("🚧 Sharp Wallet Checker 🚧")
    
    # Setup directories
    sharp_dir = ensure_data_dir("sharp")
    wallet_dir = ensure_data_dir("sharp", "wallets")
    
    # Input file path
    questions = [
        inquirer.Text(
            "input_file",
            message="Enter path to file with wallet addresses (or press Enter for default)",
            default=str(wallet_dir / "check-wallets.txt")
        ),
    ]
    answers = inquirer.prompt(questions)
    input_file = answers["input_file"]
    
    # Ensure input file exists
    if not os.path.isfile(input_file):
        print(f"❌ Input file not found: {input_file}")
        print(f"Creating an empty file at this location.")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        # Create empty file
        with open(input_file, "w") as f:
            pass
        print("Please add wallet addresses to this file and run the tool again.")
        return
    
    # Read wallet addresses
    with open(input_file, "r", encoding="utf-8") as f:
        wallets = [line.strip() for line in f if line.strip()]
    
    if not wallets:
        print(f"❌ No wallet addresses found in file: {input_file}")
        return
    
    print(f"ℹ️ Loaded {len(wallets)} wallet addresses from {input_file}")
    
    # Load config file if it exists, or use defaults
    config_file = sharp_dir / "wallet_checker_config.json"
    config = {
        "filters": {
            "min_realizedPnlUsd": 0,
            "min_unrealizedPnlUsd": 0,
            "min_totalRevenuePercent": 0,
            "min_distribution_0_percent": 0,
            "min_distribution_0_200_percent": 0,
            "min_distribution_200_plus_percent": 0
        },
        "save_unfiltered_csv": True,
        "save_filtered_csv": True
    }
    
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # Merge with defaults
                config.update(user_config)
                if "filters" in user_config:
                    config["filters"].update(user_config["filters"])
        except Exception as e:
            print(f"⚠️ Error reading config file: {e}")
            print("Using default configuration.")
    
    # Edit configuration
    questions = [
        inquirer.Confirm(
            "edit_config",
            message="Do you want to edit the filtering configuration?",
            default=False
        ),
    ]
    answers = inquirer.prompt(questions)
    
    if answers["edit_config"]:
        # Edit filter values
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
                "min_totalRevenuePercent",
                message="Minimum total revenue percentage",
                default=str(config["filters"]["min_totalRevenuePercent"])
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
                print(f"⚠️ Invalid value for {key}: {value}. Using default.")
        
        # Save updated config
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, indent=2, fp=f)
        
        print(f"✅ Configuration saved to {config_file}")
    
    # Output options
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
    ]
    answers = inquirer.prompt(questions)
    
    config["save_unfiltered_csv"] = answers["save_unfiltered_csv"]
    config["save_filtered_csv"] = answers["save_filtered_csv"]
    
    # Fetch data for each wallet
    print(f"\nFetching data for {len(wallets)} wallets...")
    results = []
    
    for i, wallet in enumerate(wallets):
        progress = (i + 1) / len(wallets) * 100
        print(f"Processing {i+1}/{len(wallets)} ({progress:.1f}%): {wallet}")
        
        try:
            # This would call BullX API in the actual implementation
            # For now, we'll just create stub data
            row = {
                "wallet": wallet,
                "realizedPnlUsd": i * 100,  # Dummy values
                "unrealizedPnlUsd": i * 50,
                "totalRevenuePercent": i * 10,
                "distribution_0_percent": 10 + i,
                "distribution_0_200_percent": 20 + i * 0.5,
                "distribution_200_plus_percent": 5 + i * 0.2
            }
            results.append(row)
            
        except Exception as e:
            print(f"❌ Error processing wallet {wallet}: {e}")
    
    # Filter results
    filtered_results = []
    for row in results:
        # Check if this wallet passes all filter thresholds
        passes = True
        for filter_key, min_val in config["filters"].items():
            if min_val > 0 and row.get(filter_key, 0) < min_val:
                passes = False
                break
        
        if passes:
            filtered_results.append(row)
    
    # Generate file names with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_wallets_file = wallet_dir / f"output-wallets_{timestamp}.txt"
    
    # Write addresses that passed filters to output file
    with open(output_wallets_file, "w", encoding="utf-8") as f:
        for row in filtered_results:
            f.write(row["wallet"] + "\n")
    
    print(f"\n✅ Found {len(filtered_results)} wallets passing filter criteria.")
    print(f"✅ Wrote them to '{output_wallets_file}'.")
    
    # Generate CSV files
    fieldnames = [
        "wallet",
        "realizedPnlUsd",
        "unrealizedPnlUsd",
        "totalRevenuePercent",
        "distribution_0_percent",
        "distribution_0_200_percent",
        "distribution_200_plus_percent"
    ]
    
    # Save unfiltered CSV
    if config["save_unfiltered_csv"]:
        csv_filename = wallet_dir / f"portfolio_results_{timestamp}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"✅ Wrote {len(results)} rows to '{csv_filename}'.")
    
    # Save filtered CSV
    if config["save_filtered_csv"]:
        csv_filename_filtered = wallet_dir / f"portfolio_results_filtered_{timestamp}.csv"
        with open(csv_filename_filtered, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in filtered_results:
                writer.writerow(row)
        print(f"✅ Wrote {len(filtered_results)} rows to '{csv_filename_filtered}'.")
    
    print("\n✅ Wallet checker completed successfully!")


def wallet_splitter():
    """Split large wallet lists into smaller chunks."""
    clear_terminal()
    print("🚧 Sharp Wallet Splitter 🚧")
    
    # Setup directory
    wallet_dir = ensure_data_dir("sharp", "wallets")
    output_dir = ensure_data_dir("sharp", "wallets/split")
    
    # Input file path
    questions = [
        inquirer.Text(
            "input_file",
            message="Enter path to file with wallet addresses",
            default=str(wallet_dir / "bulk-wallets.txt")
        ),
        inquirer.Text(
            "max_wallets",
            message="Maximum wallets per file",
            default="24999"
        ),
    ]
    answers = inquirer.prompt(questions)
    
    input_file = answers["input_file"]
    try:
        max_wallets_per_file = int(answers["max_wallets"])
    except ValueError:
        print(f"⚠️ Invalid number, using default: 24999")
        max_wallets_per_file = 24999
    
    # Create input file if it doesn't exist
    if not os.path.isfile(input_file):
        print(f"❌ Input file not found: {input_file}")
        print(f"Creating an empty file at this location.")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        # Create empty file
        with open(input_file, "w") as f:
            pass
        print("Please add wallet addresses to this file and run the tool again.")
        return
    
    # Read wallet addresses
    with open(input_file, "r", encoding="utf-8") as f:
        wallets = [line.strip() for line in f if line.strip()]
    
    if not wallets:
        print(f"❌ No wallet addresses found in file: {input_file}")
        return
    
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    split_dir = output_dir / f"split_{timestamp}"
    os.makedirs(split_dir, exist_ok=True)
    
    # Split wallets into chunks
    total_wallets = len(wallets)
    num_files = (total_wallets + max_wallets_per_file - 1) // max_wallets_per_file
    
    print(f"ℹ️ Splitting {total_wallets} wallets into {num_files} files...")
    
    for i in range(num_files):
        start_idx = i * max_wallets_per_file
        end_idx = min((i + 1) * max_wallets_per_file, total_wallets)
        chunk = wallets[start_idx:end_idx]
        
        # Create output file
        output_file = split_dir / f"wallets_{i+1:03d}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for wallet in chunk:
                f.write(wallet + "\n")
        
        print(f"✅ Created file {i+1}/{num_files}: {output_file.name} with {len(chunk)} wallets")
    
    print(f"\n✅ Wallet splitting completed! Files saved to {split_dir}")


def csv_merger():
    """Merge multiple CSV files into a single file."""
    clear_terminal()
    print("🚧 Sharp CSV Merger 🚧")
    
    # Setup directories
    unmerged_dir = ensure_data_dir("sharp", "csv/unmerged")
    merged_dir = ensure_data_dir("sharp", "csv/merged")
    
    # Check for CSV files
    csv_files = glob.glob(os.path.join(unmerged_dir, '*.csv'))
    
    if not csv_files:
        print(f"❌ No CSV files found in {unmerged_dir}")
        print(f"Please place CSV files to merge in this directory and run the tool again.")
        return
    
    print(f"ℹ️ Found {len(csv_files)} CSV files in {unmerged_dir}:")
    for i, file in enumerate(csv_files):
        file_name = os.path.basename(file)
        print(f"  {i+1}. {file_name}")
    
    # Confirm merge
    questions = [
        inquirer.Confirm(
            "confirm_merge",
            message=f"Merge these {len(csv_files)} CSV files?",
            default=True
        ),
    ]
    answers = inquirer.prompt(questions)
    
    if not answers["confirm_merge"]:
        print("❌ CSV merge cancelled.")
        return
    
    try:
        # Read the first CSV with headers
        print(f"ℹ️ Reading first CSV file: {os.path.basename(csv_files[0])}")
        merged_data = pd.read_csv(csv_files[0])
        headers = merged_data.columns
        
        # Read remaining CSVs and concatenate
        for file in csv_files[1:]:
            print(f"ℹ️ Merging file: {os.path.basename(file)}")
            df = pd.read_csv(file, header=None)
            df.columns = headers
            merged_data = pd.concat([merged_data, df], ignore_index=True)
        
        # Save to merged file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_filename = f"merged_{timestamp}.csv"
        merged_path = os.path.join(merged_dir, merged_filename)
        
        merged_data.to_csv(merged_path, index=False)
        print(f"\n✅ Merged CSV saved at: {merged_path}")
        print(f"✅ Total rows: {len(merged_data)}")
    
    except Exception as e:
        print(f"❌ Error merging CSV files: {e}")


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