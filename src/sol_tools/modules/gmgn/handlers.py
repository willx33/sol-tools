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
    
    # Import our custom prompt function for better paste handling
    from ...utils.common import prompt_user
    
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
    
    input_method = prompt_user(input_selection)['input_method']
    
    if input_method == 'saved':
        # Use our new list_saved_data function to get a nice display of saved configurations
        from ...utils.common import list_saved_data, load_unified_data
        
        saved_configs = list_saved_data(
            module="gmgn", 
            data_type="input",
            pattern="token_configs_*.json"
        )
        
        if not saved_configs:
            print("No saved inputs found. You'll need to enter new token details.")
            input_method = 'new'
        else:
            # Create formatted choices for display
            choices = []
            for config in saved_configs:
                # Format the display string with item count and date
                item_count = config.get("item_count", 0)
                modified = datetime.fromisoformat(config.get("modified", "")).strftime("%Y-%m-%d %H:%M")
                name = config.get("name", "").replace(".json", "")
                
                # Add item count and date to the display
                display = f"{name} ({item_count} tokens, {modified})"
                choices.append((display, config.get("path")))
            
            # Prompt for selection
            input_select = [
                List('saved_input',
                     message="Select a saved input configuration:",
                     choices=choices)
            ]
            
            # Get the selected file path
            selected_file = prompt_user(input_select)['saved_input']
            
            # Load the selected file
            config_data = load_unified_data(selected_file)
            
            if config_data.get("success", False):
                # Get token addresses from the items
                config_items = config_data.get("items", [])
                token_addresses = [item.get('token_address') for item in config_items if item.get('token_address')]
                
                # Get days from the first item
                days = config_items[0].get('days', 1) if config_items else 1
                
                # Format output for display
                plural = 's' if len(token_addresses) > 1 else ''
                token_list = ', '.join(token_addresses[:3])
                if len(token_addresses) > 3:
                    token_list += f" and {len(token_addresses) - 3} more"
                    
                print(f"Loaded configuration: {len(token_addresses)} token{plural} ({token_list}) for {days} day(s)")
            else:
                print(f"Error loading configuration: {config_data.get('error', 'Unknown error')}")
                # Fallback to new input if something went wrong
                input_method = 'new'
    
    if input_method == 'default':
        # Use BONK token with 1 day as default
        token_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK token on Solana
        token_addresses = [token_address]
        days = 1
        print(f"Using default: BONK token ({token_address}) for 1 day")
    
    if input_method == 'new':
        # Get token address input
        default_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK token on Solana
        # Import centralized NoTruncationText for better display
        from sol_tools.utils.common import NoTruncationText
        
        token_questions = [
            NoTruncationText(
                'token_address', 
                message=f"Enter token address (space-separated for multiple, leave empty for default BONK token)",
                default="")
        ]
        token_answer = prompt_user(token_questions)
        
        # Parse token addresses
        from sol_tools.utils.common import parse_input_addresses
        token_addresses = parse_input_addresses(token_answer['token_address'])
        
        if not token_addresses:
            token_addresses = [default_token]
            print(f"Using default token address: {default_token}")
        else:
            print(f"Using {len(token_addresses)} token addresses")
        
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
        time_answer = prompt_user(time_questions)
        
        days = time_answer['time_period']
        if days == 'custom':
            custom_days = [
                Text('custom_days', message="Enter number of days:", default="1")
            ]
            custom_answer = prompt_user(custom_days)
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
        
        if prompt_user(save_input)['save'] == 'yes':
            # Import the unified data saving function
            from ...utils.common import save_unified_data
            
            # Create a list of input configurations
            input_configs = [
                {
                    'token_address': token,
                    'days': days
                } for token in token_addresses
            ]
            
            # Save all token configurations in a single file
            input_path = save_unified_data(
                module="gmgn",
                data_items=input_configs,
                filename_prefix=f"token_configs_{days}days",
                data_type="input"
            )
            
            print(f"Input configuration saved to: {input_path}")
    
    print(f"\nFetching market cap data for the past {days} day(s) for {len(token_addresses)} tokens...")
    
    start_timestamp = datetime.now() - timedelta(days=days)
    results = {}
    
    # Fetch data for each token
    all_results = []
    for idx, token_address in enumerate(token_addresses):
        print(f"\nProcessing token {idx+1}/{len(token_addresses)}: {token_address}")
        
        try:
            # Fetch data for this token
            candles = await fetch_token_mcaps_async(token_address, start_timestamp)
            results[token_address] = candles
            
            # Create a structured result object
            result_item = {
                "token_address": token_address,
                "days": days,
                "timestamp": datetime.now().isoformat(),
                "candle_count": len(candles),
                "data": candles
            }
            all_results.append(result_item)
            
            print(f"✅ Successfully fetched {len(candles)} candles")
            
        except Exception as e:
            logger.error(f"Error fetching market cap data for {token_address}: {e}")
            print(f"❌ Error processing {token_address}: {e}")
    
    # Save unified output data if we have results
    if all_results:
        from ...utils.common import save_unified_data
        
        # Save all the results in a single file
        output_path = save_unified_data(
            module="gmgn",
            data_items=all_results,
            filename_prefix=f"mcap_data_{days}days",
            data_type="output"
        )
        
        print(f"\nData for all tokens saved to: {output_path}")
    
    # Overall summary
    print(f"\n✨ Finished processing {len(results)}/{len(token_addresses)} tokens successfully.")
    
    # Only show sample data if at least one token was processed successfully
    if results:
        # Ask if user wants to see the data
        view_questions = [
            List('view_data',
                 message="Do you want to see a sample of the data?",
                 choices=[
                     ('No', 'no'),
                     ('Yes (for each token)', 'sample'),
                     ('Yes (all records)', 'all')
                 ],
                 default='no')
        ]
        view_answer = prompt_user(view_questions)
        
        if view_answer['view_data'] in ['sample', 'all']:
            for token, candles in results.items():
                print(f"\n📊 Data for token: {token}")
                if view_answer['view_data'] == 'sample':
                    sample_size = min(5, len(candles))
                    print(f"Sample of fetched data (first {sample_size} records):")
                    for candle in candles[:sample_size]:
                        print(json.dumps(candle, indent=2))
                else:  # 'all'
                    print("All fetched data:")
                    for candle in candles:
                        print(json.dumps(candle, indent=2))
    else:
        print("No data was successfully fetched for any token.")
    
    # Note: No input() prompt needed here - the menu system will handle it

# We don't need menu functions since the menu is already defined in core/menu.py