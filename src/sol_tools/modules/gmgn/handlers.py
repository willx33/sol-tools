"""
CLI command handlers for the GMGN module
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from inquirer import Text, List, prompt

from .gmgn_adapter import fetch_token_mcaps_async

logger = logging.getLogger(__name__)

async def fetch_mcap_data_handler():
    """Handler for fetching market cap data from GMGN"""
    
    print("\n==== GMGN Market Cap Data Fetcher ====\n")
    
    # Import utility functions
    from sol_tools.utils.common import ensure_data_dir
    
    # Set up input and output directories
    input_dir = ensure_data_dir("gmgn", data_type="input")
    output_dir = ensure_data_dir("gmgn", data_type="output")
    
    # First, allow the user to choose whether to use saved input or enter new data
    input_selection = [
        List('input_method',
             message="How would you like to provide token details?",
             choices=[
                 ('Enter new token details', 'new'),
                 ('Use saved token details', 'saved'),
                 ('Use default (BONK token - 1 day)', 'default')
             ],
             default='new')
    ]
    
    input_method = prompt(input_selection)['input_method']
    
    if input_method == 'saved':
        # Look for saved input files
        saved_inputs = list(Path(input_dir).glob("*.json"))
        
        if not saved_inputs:
            print("No saved inputs found. You'll need to enter new token details.")
            input_method = 'new'
        else:
            # Sort by modification time (newest first)
            saved_inputs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            input_choices = [f.stem for f in saved_inputs]
            input_select = [
                List('saved_input',
                     message="Select a saved input configuration:",
                     choices=input_choices)
            ]
            
            selected_input = prompt(input_select)['saved_input']
            
            # Load the selected input file
            selected_file = next((f for f in saved_inputs if f.stem == selected_input), None)
            if selected_file:
                with open(selected_file, 'r') as f:
                    input_data = json.load(f)
                    token_address = input_data.get('token_address')
                    days = input_data.get('days', 1)
                    
                print(f"Loaded configuration: {token_address} for {days} day(s)")
            else:
                # Fallback to new input if something went wrong
                input_method = 'new'
    
    if input_method == 'default':
        # Use BONK token with 1 day as default
        token_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK token on Solana
        days = 1
        print(f"Using default: BONK token ({token_address}) for 1 day")
    
    if input_method == 'new':
        # Get token address input
        default_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK token on Solana
        token_questions = [
            Text('token_address', 
                 message=f"Enter token address (leave empty for default BONK token - {default_token})",
                 default="")
        ]
        token_answer = prompt(token_questions)
        
        token_address = token_answer['token_address'].strip() or default_token
        print(f"Using token address: {token_address}")
        
        # Get time period input
        time_questions = [
            List('time_period',
                 message="Select time period to fetch data for:",
                 choices=[
                     ('1 day', '1'),
                     ('3 days', '3'),
                     ('7 days', '7'),
                     ('14 days', '14'),
                     ('30 days', '30'),
                     ('Custom period', 'custom')
                 ],
                 default='1')
        ]
        time_answer = prompt(time_questions)
        
        days = time_answer['time_period']
        if days == 'custom':
            custom_days = [
                Text('custom_days', message="Enter number of days:", default="1")
            ]
            custom_answer = prompt(custom_days)
            try:
                days = int(custom_answer['custom_days'])
            except ValueError:
                print("Invalid input. Using default value of 1 day.")
                days = 1
        else:
            days = int(days)
            
        # Ask if the user wants to save this input for future use
        save_input = [
            List('save',
                 message="Would you like to save these token details for future use?",
                 choices=[('Yes', 'yes'), ('No', 'no')],
                 default='yes')
        ]
        
        if prompt(save_input)['save'] == 'yes':
            # Create a readable name for the file
            token_short = token_address[:8] if len(token_address) > 8 else token_address
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            input_filename = f"{token_short}_{days}days_{timestamp}.json"
            input_path = os.path.join(input_dir, input_filename)
            
            # Save the input configuration
            with open(input_path, 'w') as f:
                json.dump({
                    'token_address': token_address,
                    'days': days,
                    'timestamp': timestamp
                }, f, indent=2)
                
            print(f"Input configuration saved to: {input_path}")
    
    print(f"\nFetching market cap data for the past {days} day(s)...")
    
    start_timestamp = datetime.now() - timedelta(days=days)
    
    # Fetch data
    try:
        candles = await fetch_token_mcaps_async(token_address, start_timestamp)
        
        # Save results to JSON file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        token_short = token_address[:8] if len(token_address) > 8 else token_address
        output_filename = f"{token_short}_{days}days_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(candles, f, indent=2)
        
        print(f"\nSuccessfully fetched {len(candles)} candles")
        print(f"Data saved to: {output_path}")
        
        # Ask if user wants to see the data
        view_questions = [
            List('view_data',
                 message="Do you want to see a sample of the data?",
                 choices=[
                     ('No', 'no'),
                     ('Yes (first 5 records)', 'sample'),
                     ('Yes (all records)', 'all')
                 ],
                 default='no')
        ]
        view_answer = prompt(view_questions)
        
        if view_answer['view_data'] == 'sample':
            print("\nSample of fetched data (first 5 records):")
            for candle in candles[:5]:
                print(json.dumps(candle, indent=2))
        elif view_answer['view_data'] == 'all':
            print("\nAll fetched data:")
            for candle in candles:
                print(json.dumps(candle, indent=2))
    
    except Exception as e:
        logger.error(f"Error fetching market cap data: {e}")
        print(f"Error: {e}")
    
    input("\nPress Enter to return to menu...")

# We don't need menu functions since the menu is already defined in core/menu.py