"""Handlers for Dune Analytics functionality."""

import os
import time
import glob
import inquirer
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from requests import HTTPError

from ...utils.common import clear_terminal, ensure_data_dir
from ...core.config import check_env_vars, get_env_var
from .dune_adapter import DuneAdapter


def _get_dune_adapter():
    """Get initialized Dune adapter."""
    data_dir = ensure_data_dir("").parent
    api_key = get_env_var("DUNE_API_KEY")
    return DuneAdapter(data_dir, api_key)


def run_query():
    """Execute Dune queries and save results to CSV."""
    clear_terminal()
    print("📊 Dune Analytics Query Runner")
    
    # Check for required environment variables
    from ...utils.common import validate_credentials
    if not validate_credentials("dune"):
        return
    
    # Get Dune adapter
    adapter = _get_dune_adapter()
    
    # Get query IDs from user
    print("Enter query IDs (space-separated or one per line, leave empty to stop)")
    
    query_input = ""
    while True:
        user_input = input("> ").strip()
        if user_input == "":
            break
        query_input += user_input + "\n"
    
    # Parse and validate query IDs
    query_ids = []
    if query_input.strip():
        # Split by spaces and newlines
        parts = []
        for line in query_input.strip().split('\n'):
            parts.extend(line.strip().split())
            
        # Convert to integers and validate
        for part in parts:
            if part.isdigit():
                query_ids.append(int(part))
            else:
                print(f"Invalid query ID skipped: {part} (must be a number)")
    
    if not query_ids:
        print("No valid query IDs entered. Exiting.")
        return
    
    # Import NoTruncationText for better display
    from ...utils.common import NoTruncationText
    
    # Get batch parameters
    questions = [
        NoTruncationText(
            "batch_size",
            message="Number of queries to run in each batch",
            default="3"
        ),
        NoTruncationText(
            "batch_delay",
            message="Delay between batches (seconds)",
            default="30"
        )
    ]
    answers = inquirer.prompt(questions)
    
    try:
        batch_size = int(answers["batch_size"])
        batch_delay = int(answers["batch_delay"])
    except ValueError:
        print("⚠️ Invalid parameters, using defaults: batch size 3, delay 30 seconds")
        batch_size = 3
        batch_delay = 30
    
    # Run the queries using the adapter
    print("\nRunning Dune queries...\n")
    result = adapter.run_query(query_ids, batch_size, batch_delay)
    
    if result.get("success", False):
        print(f"\n✅ Dune queries completed successfully")
        print(f"✅ Ran {result.get('queries_run', 0)} queries")
        if result.get("failures", 0) > 0:
            print(f"⚠️ Failed queries: {result.get('failures', 0)}")
        if result.get("csv_files"):
            print(f"📄 CSV files saved:")
            for file in result.get("csv_files", []):
                print(f"   {os.path.basename(file)}")
    else:
        print(f"\n❌ Dune query failed: {result.get('error', 'Unknown error')}")


def parse_csv():
    """Parse token addresses from Dune query CSV results."""
    clear_terminal()
    print("📊 Dune CSV Parser")
    
    # Check for required environment variables
    from ...utils.common import validate_credentials
    if not validate_credentials("dune"):
        return
    
    # Get Dune adapter
    adapter = _get_dune_adapter()
    
    # Get available CSV files
    csv_files = adapter.get_available_csvs()
    
    if not csv_files:
        print("❌ No CSV files found in data/dune/csv folder.")
        return
    
    # Loop until user is done selecting files
    while True:
        # Create menu choices
        menu_choices = csv_files + ["⬅️ Done selecting files"]
        
        questions = [
            inquirer.List(
                "csv_choice",
                message="Select a CSV file to parse:",
                choices=menu_choices
            )
        ]
        answers = inquirer.prompt(questions)
        chosen_file = answers.get("csv_choice")
        
        if chosen_file == "⬅️ Done selecting files":
            print("✅ Done selecting CSV files.")
            break
        
        # Choose column for token addresses
        from ...utils.common import NoTruncationText
        
        column_question = [
            NoTruncationText(
                "column_index",
                message="Column index to extract (default 2 for token_address)",
                default="2"
            )
        ]
        column_answer = inquirer.prompt(column_question)
        
        try:
            column_index = int(column_answer["column_index"])
        except ValueError:
            print("⚠️ Invalid column index, using default 2")
            column_index = 2
        
        # Parse the CSV
        result = adapter.parse_csv(chosen_file, column_index)
        
        if result.get("success", False):
            addresses_count = result.get("addresses_extracted", 0)
            output_file = result.get("output_file", "Unknown file")
            print(f"✅ Parsed {addresses_count} addresses to {os.path.basename(output_file)}")
            
            # Option to delete original CSV
            delete_q = [
                inquirer.List(
                    "delete_csv",
                    message=f"Delete original CSV file?",
                    choices=["Yes", "No"]
                )
            ]
            delete_ans = inquirer.prompt(delete_q)
            if delete_ans.get("delete_csv") == "Yes":
                if adapter.delete_csv(chosen_file):
                    print(f"✅ Original CSV file deleted")
                    # Remove from list
                    csv_files.remove(chosen_file)
                else:
                    print(f"❌ Failed to delete CSV file")
        else:
            print(f"❌ Error parsing file: {result.get('error', 'Unknown error')}")
    
    print("\n✅ Done parsing CSV files.")