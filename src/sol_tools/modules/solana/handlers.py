"""Handlers for Solana monitoring and utilities."""

import os
import sys
import time
import glob
import json
import inquirer
import asyncio
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

from ...utils.common import clear_terminal, ensure_data_dir, check_proxy_file
from ...core.config import check_env_vars, get_env_var
from .solana_adapter import SolanaAdapter

# We'll check for Dragon availability through the SolanaAdapter, not directly


def token_monitor():
    """Monitor new transactions for specific tokens."""
    clear_terminal()
    print("🚧 Solana Token Monitor 🚧")
    
    # Check for required environment variables
    env_vars = check_env_vars("solana")
    if not all(env_vars.values()):
        missing = [var for var, present in env_vars.items() if not present]
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please set them in the .env file before using this feature.")
        return
    
    # Import custom NoTruncationText and prompt function for better paste handling
    from ...utils.common import NoTruncationText, prompt_user
    
    # Input for token address
    questions = [
        NoTruncationText(
            "token_address",
            message="Enter Solana token address to monitor (space-separated for multiple)",
            validate=lambda _, x: all(len(addr.strip()) == 44 for addr in x.split()) if x else False
        ),
        NoTruncationText(
            "min_amount",
            message="Minimum transaction amount to alert (in USD)",
            default="1000"
        ),
    ]
    answers = prompt_user(questions)
    
    # Parse token addresses
    from ...utils.common import parse_input_addresses
    token_addresses = parse_input_addresses(answers["token_address"])
        
    try:
        min_amount = float(answers["min_amount"])
    except ValueError:
        print(f"⚠️ Invalid minimum amount, using default: 1000 USD")
        min_amount = 1000
    
    # Initialize Solana adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Start monitoring
    print(f"\n🔎 Monitoring transactions for {len(token_addresses)} tokens")
    print(f"🔔 Will alert for transactions >= ${min_amount:.2f}")
    print("\nPress Ctrl+C to stop monitoring...\n")
    
    try:
        # Use the new process_multiple_inputs utility
        from ...utils.common import process_multiple_inputs
        
        # Define a processor function that will be called for each token
        def process_token(token_address):
            return adapter.token_monitor(token_address, min_amount)
        
        # Process all tokens
        results = process_multiple_inputs(
            token_addresses,
            process_token,
            description="token",
            show_progress=True
        )
        
        # Display summary and transaction details
        all_results = results.get("all_results", [])
        total_events = 0
        processed_results = []
        
        # Count and display all events above threshold
        for result in all_results:
            if result.get("success", False):
                events = result.get("events", [])
                total_events += len(events)
                
                token = result.get("token_address", "Unknown token")
                for event in events:
                    print(f"⚡ Token {token}: ${event['amount']:.2f} at {event['timestamp']}")
                
                # Add this result to our list for saving
                processed_results.append({
                    "token_address": token,
                    "threshold": min_amount,
                    "timestamp": datetime.now().isoformat(),
                    "events": events
                })
        
        # Save all results to a unified file
        if processed_results:
            from ...utils.common import save_unified_data
            
            output_path = save_unified_data(
                module="solana",
                data_items=processed_results,
                filename_prefix="token_monitoring",
                data_type="output"
            )
            
            print(f"\nAll monitoring results saved to: {output_path}")
        
        # Summary
        print(f"\n✅ Monitoring complete. Successfully processed {results['success_count']}/{results['total_processed']} tokens.")
        print(f"Detected {total_events} transactions above threshold.")
        
        # Show any errors
        if results.get("errors"):
            print("\n⚠️ Errors encountered:")
            for error in results["errors"]:
                print(f"  - {error}")
            
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped by user")


def wallet_monitor():
    """Monitor transactions for specific wallets."""
    clear_terminal()
    print("🚧 Solana Wallet Monitor 🚧")
    
    # Check for required environment variables
    env_vars = check_env_vars("solana")
    if not all(env_vars.values()):
        missing = [var for var, present in env_vars.items() if not present]
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please set them in the .env file before using this feature.")
        return
    
    # Setup directory for wallets
    wallet_dir = ensure_data_dir("solana", "wallets")
    
    # Import the universal file selection utility
    from ...utils.common import select_input_file
    
    # First, allow the user to choose wallets source
    questions = [
        inquirer.List(
            "wallet_source",
            message="How would you like to provide wallet addresses?",
            choices=[
                ('Use the default wallets file', 'default'),
                ('Select a wallets file from any module', 'select'),
                ('Enter wallet addresses manually', 'manual')
            ],
            default='default'
        )
    ]
    wallet_source = inquirer.prompt(questions)["wallet_source"]
    
    # Handle based on selection
    if wallet_source == 'default':
        # Default wallet file
        wallet_file = wallet_dir / "monitor-wallets.txt"
        if os.path.exists(wallet_file):
            with open(wallet_file, "r") as f:
                existing_wallets = [line.strip() for line in f if line.strip()]
                
            if existing_wallets:
                print(f"ℹ️ Found {len(existing_wallets)} wallets in default file:")
                for i, wallet in enumerate(existing_wallets[:5], 1):
                    print(f"  {i}. {wallet}")
                if len(existing_wallets) > 5:
                    print(f"  ... and {len(existing_wallets) - 5} more")
                wallets = existing_wallets
            else:
                print("ℹ️ Default wallet file exists but is empty.")
                wallets = []
        else:
            print("ℹ️ No default wallet file found.")
            wallets = []
            
    elif wallet_source == 'select':
        # Use universal file selector to find any wallets.txt file
        selected_file = select_input_file(
            pattern="wallets.txt", 
            message="Select a wallets file from any module:",
            show_module=True
        )
        
        if selected_file:
            try:
                with open(selected_file, "r") as f:
                    wallets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                print(f"ℹ️ Loaded {len(wallets)} wallets from {selected_file}")
            except Exception as e:
                print(f"❌ Error reading selected file: {e}")
                wallets = []
        else:
            print("ℹ️ No file selected.")
            wallets = []
    else:
        # Manual entry
        wallets = []
    
    # If no wallets from file or user chose not to use them
    if not wallets:
        from ...utils.common import parse_input_addresses, validate_addresses
        
        # Ask for wallet addresses
        print("\nEnter wallet addresses to monitor (space-separated or one per line, empty line to finish):")
        wallet_input = ""
        while True:
            line = input("> ").strip()
            if not line:
                break
            wallet_input += line + "\n"
        
        # Parse and validate addresses
        raw_wallets = parse_input_addresses(wallet_input)
        valid_wallets, invalid_wallets = validate_addresses(
            raw_wallets, 
            lambda x: len(x) == 44
        )
        
        if invalid_wallets:
            print(f"❌ Ignored {len(invalid_wallets)} invalid wallet addresses")
        
        wallets = valid_wallets
        
        # Save wallets to file
        with open(wallet_dir / "monitor-wallets.txt", "w") as f:
            for wallet in wallets:
                f.write(f"{wallet}\n")
    
    if not wallets:
        print("❌ No wallets to monitor. Exiting.")
        return
    
    # Initialize Solana adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Start monitoring
    print(f"\n🔎 Monitoring transactions for {len(wallets)} wallets")
    print("\nPress Ctrl+C to stop monitoring...\n")
    
    try:
        # Use the adapter to monitor wallets
        result = adapter.wallet_monitor(wallets)
        
        if result.get("success", False):
            events = result.get("events", [])
            for event in events:
                wallet = event["wallet"]
                truncated = wallet[:6] + "..." + wallet[-6:]
                print(f"⚡ New transaction for wallet {truncated}: ${event['amount']:.2f} at {event['timestamp']}")
            
            print(f"\n✅ Monitoring complete. Detected {len(events)} transactions.")
        else:
            print(f"\n❌ Monitoring failed: {result.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped by user")


def telegram_scraper():
    """Scrape token data from Telegram channels."""
    clear_terminal()
    print("🚧 Solana Telegram Scraper 🚧")
    
    # Check for Telegram API credentials
    if not get_env_var("TELEGRAM_BOT_TOKEN") or not get_env_var("TELEGRAM_CHAT_ID"):
        print("❌ Missing Telegram API credentials")
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file.")
        return
    
    # Setup directory
    telegram_dir = ensure_data_dir("solana", "telegram")
    
    # Input for channel to scrape
    questions = [
        inquirer.Text(
            "channel",
            message="Enter Telegram channel username to scrape (without @)",
            default="SolanaNews"  # Example default
        ),
        inquirer.Text(
            "limit",
            message="Maximum number of messages to scrape",
            default="100"
        ),
    ]
    answers = inquirer.prompt(questions)
    
    channel = answers["channel"]
    try:
        limit = int(answers["limit"])
    except ValueError:
        print(f"⚠️ Invalid limit, using default: 100 messages")
        limit = 100
    
    # Scrape options
    questions = [
        inquirer.List(
            "filter_type",
            message="Filter messages for:",
            choices=["All messages", "Only messages with token addresses", "Only messages with links"]
        ),
        inquirer.Confirm(
            "export_csv",
            message="Export results to CSV?",
            default=True
        ),
    ]
    answers = inquirer.prompt(questions)
    
    filter_type = answers["filter_type"]
    export_csv = answers["export_csv"]
    
    # Initialize Solana adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Start scraping
    print(f"\n🔎 Scraping Telegram channel: @{channel}")
    print(f"ℹ️ Filter: {filter_type}")
    print(f"ℹ️ Maximum messages: {limit}")
    
    print("\nScraping messages...")
    
    # Use the adapter to scrape Telegram
    result = adapter.telegram_scraper(channel, limit, filter_type, export_csv)
    
    if result.get("success", False):
        token_count = result.get("tokens_found", 0)
        link_count = result.get("links_found", 0)
        output_file = result.get("output_file")
        
        print(f"\n✅ Scraping completed. Found {token_count} token addresses and {link_count} links.")
        if output_file:
            print(f"📄 Results saved to: {output_file}")
    else:
        print(f"\n❌ Scraping failed: {result.get('error', 'Unknown error')}")


def test_telegram():
    """Test Telegram connection."""
    clear_terminal()
    print("🧪 Testing Telegram Connection...")
    
    # Initialize Solana adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Run test
    result = adapter.test_telegram()
    
    if result.get("success", False):
        print(f"✅ {result.get('message', 'Test successful')}")
    else:
        print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
        print("Please check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file.")


# Dragon integration handlers

def dragon_solana_bundle():
    """Check for bundled transactions (multiple buys in one tx)."""
    clear_terminal()
    print("🐲 Dragon Solana Bundle Checker")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Import NoTruncationText and prompt_user for better display and paste handling
    from ...utils.common import NoTruncationText, prompt_user
    
    # Prompt for contract address(es)
    questions = [
        NoTruncationText(
            "contract_address",
            message="Enter Solana contract address(es) (space-separated for multiple)",
            validate=lambda _, x: all(len(addr.strip()) in [43, 44] for addr in x.split()) if x else False
        )
    ]
    answers = prompt_user(questions)
    contract_address = answers["contract_address"]
    
    # Use the adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    result = adapter.solana_bundle_checker(contract_address)
    
    if result.get("success", False):
        # Get formatted data for multiple tokens
        formatted_data = result.get("data", [])
        success_count = result.get("success_count", 0)
        error_count = result.get("error_count", 0)
        
        print(f"\n✅ Bundle checking completed for {success_count} contract(s)")
        if error_count > 0:
            print(f"⚠️ {error_count} contract(s) had errors")
            
        # Show formatted data for each successful address
        for item in formatted_data:
            address = item.get("address", "Unknown")
            formatted = item.get("formatted", "No data returned")
            
            print(f"\n📊 Results for {address}:")
            print(formatted)
            print("-" * 40)
        
        # Save all bundle check results to a unified file
        if formatted_data:
            from ...utils.common import save_unified_data
            
            output_path = save_unified_data(
                module="dragon",
                data_items=formatted_data,
                filename_prefix="bundle_check",
                data_type="output"
            )
            
            print(f"\nAll bundle check results saved to: {output_path}")
        
        # Show errors, if any
        errors = result.get("errors", [])
        if errors:
            print("\n⚠️ Errors encountered:")
            for error in errors:
                print(f"  - {error}")
    else:
        print(f"\n❌ Bundle checking failed: {result.get('error', 'Unknown error')}")
    
    input("\nPress Enter to continue...")


def dragon_solana_wallet():
    """Analyze PnL and win rates for multiple wallets."""
    clear_terminal()
    print("🐲 Dragon Solana Wallet Checker")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Setup wallet directory
    wallet_dir = ensure_data_dir("input-data/dragon", "solana/wallet_lists")
    
    # Default wallets file
    default_wallets_file = wallet_dir / "wallets.txt"
    if not os.path.exists(default_wallets_file):
        # Create example file if it doesn't exist
        os.makedirs(os.path.dirname(default_wallets_file), exist_ok=True)
        with open(default_wallets_file, 'w') as f:
            f.write("# Add wallet addresses here (one per line)")
    
    # Import the universal file selection utility
    from ...utils.common import select_input_file
    
    # First, allow the user to choose wallets source
    questions = [
        inquirer.List(
            "file_option",
            message="How would you like to provide wallet addresses?",
            choices=[
                ('Use the default wallets file', 'default'),
                ('Select a wallets file from any module', 'select'),
                ('Enter a specific file path manually', 'manual')
            ],
            default='default'
        )
    ]
    file_option = inquirer.prompt(questions)["file_option"]
    
    # Handle file selection based on user choice
    if file_option == 'default':
        wallets_path = str(default_wallets_file)
        print(f"Using default wallets file: {wallets_path}")
    elif file_option == 'select':
        # Use universal file selector
        selected_file = select_input_file(
            pattern="wallets.txt", 
            message="Select a wallets file from any module:",
            show_module=True
        )
        
        if selected_file:
            wallets_path = selected_file
        else:
            print("❌ No file selected. Using default file.")
            wallets_path = str(default_wallets_file)
    else:
        # Manual option - prompt for file path
        questions = [
            inquirer.Text(
                "wallets_file",
                message="Enter the path to wallets file",
                default=str(default_wallets_file)
            ),
        ]
        wallets_path = inquirer.prompt(questions)["wallets_file"]
        
    # Other questions for the Dragon wallet checker
    questions = [
        inquirer.Text(
            "threads",
            message="Number of threads",
            default="40"
        ),
        inquirer.Confirm(
            "skip_wallets",
            message="Skip wallets with no buys in 30d?",
            default=False
        ),
        inquirer.Confirm(
            "use_proxies",
            message="Use proxies for API requests?",
            default=False
        )
    ]
    answers = inquirer.prompt(questions)
    
    # Load wallets from chosen file
    try:
        with open(wallets_path, 'r') as f:
            wallets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        print(f"❌ Error reading wallets file: {e}")
        input("\nPress Enter to continue...")
        return
    
    if not wallets:
        print("❌ No wallet addresses found in file.")
        input("\nPress Enter to continue...")
        return
    
    print(f"ℹ️ Loaded {len(wallets)} wallet addresses")
    
    # Parse thread count
    try:
        threads = int(answers["threads"])
    except ValueError:
        print("⚠️ Invalid thread count, using default 40")
        threads = 40
    
    # Check proxies if requested
    if answers["use_proxies"]:
        proxies = check_proxy_file()
        if not proxies:
            print("⚠️ No proxies found. Continuing without proxies.")
            answers["use_proxies"] = False
    
    # Use the adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    result = adapter.solana_wallet_checker(
        wallets, 
        threads=threads,
        skip_wallets=answers["skip_wallets"],
        use_proxies=answers["use_proxies"]
    )
    
    if result.get("success", False):
        print(f"\n✅ Wallet analysis completed")
        if "data" in result:
            # Handle success response with data summary
            # In a real implementation we would display summary stats
            print(f"Processed {len(wallets)} wallets")
    else:
        print(f"\n❌ Wallet analysis failed: {result.get('error', 'Unknown error')}")
    
    input("\nPress Enter to continue...")


def dragon_solana_traders():
    """Find top performing traders for specific tokens."""
    clear_terminal()
    print("🐲 Dragon Solana Top Traders")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Similar implementation to other handlers, but focused on traders
    print("This feature will analyze top traders for Solana tokens")
    input("\nPress Enter to continue...")


def dragon_solana_scan():
    """Retrieve all transactions for a specific token."""
    clear_terminal()
    print("🐲 Dragon Solana Scan Transactions")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Stub implementation for scanning transactions
    print("This feature will scan all transactions for a Solana token")
    input("\nPress Enter to continue...")


def dragon_solana_copy():
    """Find wallets that copy other traders."""
    clear_terminal()
    print("🐲 Dragon Solana Copy Wallet Finder")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Stub implementation for copy wallet finder
    print("This feature will find wallets that copy specific traders")
    input("\nPress Enter to continue...")


def dragon_solana_holders():
    """Analyze top token holders' performance."""
    clear_terminal()
    print("🐲 Dragon Solana Top Holders")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Stub implementation for top holders
    print("This feature will analyze top token holders' performance")
    input("\nPress Enter to continue...")


def dragon_solana_buyers():
    """Find early token buyers and their performance."""
    clear_terminal()
    print("🐲 Dragon Solana Early Buyers")
    
    # Initialize Solana adapter (which will also try to initialize Dragon)
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Check for Dragon modules via adapter
    if not adapter.check_dragon_availability():
        print("❌ Dragon modules not available")
        print("This functionality requires the Dragon library.")
        print("Please check that all dependencies are installed correctly.")
        print("Contact the administrator for installation instructions.")
        input("\nPress Enter to continue...")
        return
    
    # Stub implementation for early buyers
    print("This feature will find early token buyers and analyze their performance")
    input("\nPress Enter to continue...")