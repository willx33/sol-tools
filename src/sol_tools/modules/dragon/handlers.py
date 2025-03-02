"""Handlers for Dragon module functionality."""

import os
import sys
import json
import asyncio
import inquirer
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
import time

from ...utils.common import clear_terminal, ensure_data_dir, check_proxy_file
from ...core.config import check_env_vars
from .dragon_adapter import DragonAdapter

logger = logging.getLogger(__name__)

class DragonHandlers:
    """Handlers for Dragon module functionality."""
    
    @staticmethod
    def handle_bundle_check(contract_address: str) -> Dict[str, Any]:
        """
        Handle checking bundles for a contract address.
        
        Args:
            contract_address: Contract address to check
            
        Returns:
            Response data
        """
        logger.info(f"Handling bundle check for {contract_address}")
        
        # Import the adapter
        try:
            adapter = DragonAdapter()
            return adapter.solana_bundle_checker(contract_address)
        except Exception as e:
            logger.error(f"Error in handle_bundle_check: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def handle_wallet_check(wallets: Union[str, List[str]], **kwargs) -> Dict[str, Any]:
        """
        Handle checking wallets.
        
        Args:
            wallets: Wallet address or list of addresses
            **kwargs: Additional parameters
            
        Returns:
            Response data
        """
        logger.info(f"Handling wallet check for {len(wallets) if isinstance(wallets, list) else 1} wallets")
        
        # Import the adapter
        try:
            adapter = DragonAdapter()
            return adapter.solana_wallet_checker(wallets, **kwargs)
        except Exception as e:
            logger.error(f"Error in handle_wallet_check: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def handle_token_info(contract_address: str) -> Dict[str, Any]:
        """
        Handle getting token information.
        
        Args:
            contract_address: Contract address to get information for
            
        Returns:
            Token information
        """
        logger.info(f"Handling token info request for {contract_address}")
        
        # Import the adapter
        try:
            adapter = DragonAdapter()
            return adapter.get_token_info_sync(contract_address)
        except Exception as e:
            logger.error(f"Error in handle_token_info: {e}")
            return {"success": False, "error": str(e)}

# Expose handlers for direct import
bundle_check_handler = DragonHandlers.handle_bundle_check
wallet_check_handler = DragonHandlers.handle_wallet_check
token_info_handler = DragonHandlers.handle_token_info

# Initialize the dragon adapter for all handlers
def _get_dragon_adapter():
    """Get initialized Dragon adapter."""
    try:
        adapter = DragonAdapter()
        # Initialize the adapter asynchronously
        async def _initialize():
            return await adapter.initialize()
            
        # Run the async initialization in a proper coroutine
        asyncio.run(_initialize())
        
        if not hasattr(adapter, 'get_token_data_handler') or adapter.get_token_data_handler() is None:
            logger = logging.getLogger(__name__)
            logger.warning("Token data handler is None after initialization")
        return adapter
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error initializing Dragon adapter: {e}")
        # Still return the adapter so caller can handle the error gracefully
        return DragonAdapter()


def solana_bundle_checker():
    """Check for bundled transactions (multiple buys in one tx)."""
    clear_terminal()
    print("🐲 Dragon Solana Bundle Checker")
    
    # Check for required environment variables
    from ...utils.common import validate_credentials
    if not validate_credentials("solana"):
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
    adapter = _get_dragon_adapter()
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
                module="solana/dragon",
                data_items=formatted_data,
                filename_prefix="bundle_check",
                data_type="output",
                subdir="transaction-data"
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


def solana_wallet_checker():
    """Analyze PnL and win rates for multiple wallets."""
    clear_terminal()
    print("🐲 Dragon Solana Wallet Checker")
    
    # Check for required environment variables
    from ...utils.common import validate_multiple_credentials
    if not validate_multiple_credentials(["solana", "telegram"]):
        return
    
    # Setup wallet directory
    wallet_dir = ensure_data_dir("solana", "wallet-lists", data_type="input")
    
    # Choose wallets file
    default_wallets_file = wallet_dir / "wallets.txt"
    if not os.path.exists(default_wallets_file):
        # Create example file if it doesn't exist
        with open(default_wallets_file, 'w') as f:
            f.write("# Add wallet addresses here (one per line)")
    
    # Import the universal file selection utility
    from ...utils.common import select_input_file
    
    # First, allow the user to choose whether to use the default file or select a file
    questions = [
        inquirer.List(
            "file_option",
            message="How would you like to provide wallet addresses?",
            choices=[
                ('Use the default wallets file', 'default'),
                ('Select a wallets file from all available files', 'select'),
                ('Enter a specific file path manually', 'manual')
            ],
            default='default'
        )
    ]
    answers = inquirer.prompt(questions)
    file_option = answers.get("file_option", "default") if answers else "default"
    
    # Handle file selection based on user choice
    if file_option == 'default':
        wallets_path = str(default_wallets_file)
        print(f"Using default wallets file: {wallets_path}")
    elif file_option == 'select':
        # Use our new universal file selector
        wallets_path = select_input_file(
            pattern="wallets.txt", 
            message="Select a wallets file from any module:",
            show_module=True
        )
        
        if not wallets_path:
            print("❌ No file selected. Using default file.")
            wallets_path = str(default_wallets_file)
    else:  # manual option
        manual_questions = [
            inquirer.Text(
                "wallets_file",
                message="Enter the path to wallets file",
                default=str(default_wallets_file)
            )
        ]
        answers = inquirer.prompt(manual_questions)
        wallets_path = answers.get("wallets_file", str(default_wallets_file)) if answers else str(default_wallets_file)
    
    # Get other options
    option_questions = [
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
    answers = inquirer.prompt(option_questions) or {}
    
    # Load wallets from file
    try:
        with open(wallets_path, 'r') as f:
            wallets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        print(f"❌ Error reading wallets file: {e}")
        return
    
    if not wallets:
        print("❌ No wallet addresses found in file.")
        return
    
    print(f"ℹ️ Loaded {len(wallets)} wallet addresses")
    
    # Parse thread count
    try:
        threads = int(answers.get("threads", "40"))
    except ValueError:
        print("⚠️ Invalid thread count, using default 40")
        threads = 40
    
    # Check proxies if requested
    use_proxies = answers.get("use_proxies", False)
    if use_proxies:
        proxies = check_proxy_file()
        if not proxies:
            print("⚠️ No proxies found. Continuing without proxies.")
            use_proxies = False
    
    # Use the adapter
    adapter = _get_dragon_adapter()
    result = adapter.solana_wallet_checker(
        wallets, 
        threads=threads,
        skip_wallets=answers.get("skip_wallets", False),
        use_proxies=use_proxies
    )
    
    if result.get("success", False):
        print(f"\n✅ Wallet analysis completed")
        if "data" in result:
            # Save the wallet analysis data to a file
            wallet_data = result["data"]
            from ...utils.common import save_unified_data
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = save_unified_data(
                module="solana/dragon",
                data_items=wallet_data if isinstance(wallet_data, list) else [wallet_data],
                filename_prefix=f"wallet_analysis_{timestamp}",
                data_type="output",
                subdir="wallet-analysis"
            )
            
            # Display summary stats
            print(f"Processed {len(wallets)} wallets")
            print(f"Results saved to: {output_file}")
    else:
        print(f"\n❌ Wallet analysis failed: {result.get('error', 'Unknown error')}")


def solana_top_traders():
    """Find top performing traders for specific tokens."""
    clear_terminal()
    print("🐲 Dragon Solana Top Traders")
    
    # Similar implementation to other handlers, but focused on traders
    # This is a stub implementation that would be replaced with actual functionality
    print("This feature will analyze top traders for Solana tokens")


def solana_scan_tx():
    """Retrieve all transactions for a specific token."""
    clear_terminal()
    print("🐲 Dragon Solana Scan Transactions")
    
    # Stub implementation for scanning transactions
    print("This feature will scan all transactions for a Solana token")


def solana_copy_wallet_finder():
    """Find wallets that copy other traders."""
    clear_terminal()
    print("🐲 Dragon Solana Copy Wallet Finder")
    
    # Stub implementation for copy wallet finder
    print("This feature will find wallets that copy specific traders")


def solana_top_holders():
    """Analyze top token holders' performance."""
    clear_terminal()
    print("🐲 Dragon Solana Top Holders")
    
    # Stub implementation for top holders
    print("This feature will analyze top token holders' performance")


def solana_early_buyers():
    """Find early token buyers and their performance."""
    clear_terminal()
    print("🐲 Dragon Solana Early Buyers")
    
    # Stub implementation for early buyers
    print("This feature will find early token buyers and analyze their performance")


def eth_wallet_checker():
    """Analyze Ethereum wallet performance metrics."""
    clear_terminal()
    print("🐲 Dragon Ethereum Wallet Checker")
    
    # Stub implementation for Ethereum wallet checker
    print("This feature will analyze Ethereum wallet performance metrics")


def eth_top_traders():
    """Find top Ethereum traders for specific tokens."""
    clear_terminal()
    print("🐲 Dragon Ethereum Top Traders")
    
    # Stub implementation for Ethereum top traders
    print("This feature will find top Ethereum traders for specific tokens")


def eth_scan_tx():
    """Retrieve all transactions for a specific Ethereum token."""
    clear_terminal()
    print("🐲 Dragon Ethereum Scan Transactions")
    
    # Stub implementation for Ethereum transaction scanning
    print("This feature will scan all transactions for an Ethereum token")


def eth_timestamp():
    """Find transactions between specific timestamps."""
    clear_terminal()
    print("🐲 Dragon Ethereum Timestamp Finder")
    
    # Stub implementation for Ethereum timestamp finder
    print("This feature will find Ethereum transactions between specific timestamps")


def gmgn_new_tokens():
    """Scrape new token contracts from GMGN."""
    clear_terminal()
    print("🐲 Dragon GMGN New Tokens")
    
    # Set up data directories
    output_dir = ensure_data_dir("api/gmgn", "token-listings", data_type="output")
    
    print("Fetching new tokens from GMGN...")
    
    # Use the adapter to get new tokens
    try:
        adapter = _get_dragon_adapter()
        
        if adapter.gmgn_client is None:
            print("\n❌ Error: GMGN client not properly initialized")
            input("\nPress Enter to continue...")
            return
            
        tokens = adapter.get_new_tokens()
        
        # Process and save the results
        if tokens:
            output_file = output_dir / f"new_tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Display results
            print(f"\n✅ Successfully fetched {len(tokens)} new tokens")
            print(f"Results saved to {output_file}")
            
            # Show sample of the data
            print("\nSample token data:")
            for token in tokens[:3]:
                print(f"- {token.get('name', 'Unknown')} ({token.get('symbol', 'Unknown')}): {token.get('address', 'Unknown')}")
            if len(tokens) > 3:
                print(f"...and {len(tokens) - 3} more tokens")
        else:
            print("⚠️ No new tokens found")
    except Exception as e:
        print(f"\n❌ Handler error: {e}")
    
    input("\nPress Enter to continue...")


def gmgn_completing_tokens():
    """Scrape completing token contracts from GMGN."""
    clear_terminal()
    print("🐲 Dragon GMGN Completing Tokens")
    
    # Set up data directories
    output_dir = ensure_data_dir("api/gmgn", "token-listings", data_type="output")
    
    print("Fetching completing tokens from GMGN...")
    
    # Use the adapter to get completing tokens
    try:
        adapter = _get_dragon_adapter()
        
        if adapter.gmgn_client is None:
            print("\n❌ Error: GMGN client not properly initialized")
            input("\nPress Enter to continue...")
            return
            
        tokens = adapter.get_completing_tokens()
        
        # Process and save the results
        if tokens:
            output_file = output_dir / f"completing_tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Display results
            print(f"\n✅ Successfully fetched {len(tokens)} completing tokens")
            print(f"Results saved to {output_file}")
            
            # Show sample of the data
            print("\nSample token data:")
            for token in tokens[:3]:
                print(f"- {token.get('name', 'Unknown')} ({token.get('symbol', 'Unknown')}): {token.get('address', 'Unknown')}")
            if len(tokens) > 3:
                print(f"...and {len(tokens) - 3} more tokens")
        else:
            print("⚠️ No completing tokens found")
    except Exception as e:
        print(f"\n❌ Handler error: {e}")
    
    input("\nPress Enter to continue...")


def gmgn_soaring_tokens():
    """Scrape soaring token contracts from GMGN."""
    clear_terminal()
    print("🐲 Dragon GMGN Soaring Tokens")
    
    # Set up data directories
    output_dir = ensure_data_dir("api/gmgn", "token-listings", data_type="output")
    
    print("Fetching soaring tokens from GMGN...")
    
    # Use the adapter to get soaring tokens
    try:
        adapter = _get_dragon_adapter()
        
        if adapter.gmgn_client is None:
            print("\n❌ Error: GMGN client not properly initialized")
            input("\nPress Enter to continue...")
            return
            
        tokens = adapter.get_soaring_tokens()
        
        # Process and save the results
        if tokens:
            output_file = output_dir / f"soaring_tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Display results
            print(f"\n✅ Successfully fetched {len(tokens)} soaring tokens")
            print(f"Results saved to {output_file}")
            
            # Show sample of the data
            print("\nSample token data:")
            for token in tokens[:3]:
                print(f"- {token.get('name', 'Unknown')} ({token.get('symbol', 'Unknown')}): {token.get('address', 'Unknown')}")
            if len(tokens) > 3:
                print(f"...and {len(tokens) - 3} more tokens")
        else:
            print("⚠️ No soaring tokens found")
    except Exception as e:
        print(f"\n❌ Handler error: {e}")
    
    input("\nPress Enter to continue...")


def gmgn_bonded_tokens():
    """Scrape bonded token contracts from GMGN."""
    clear_terminal()
    print("🐲 Dragon GMGN Bonded Tokens")
    
    # Set up data directories
    output_dir = ensure_data_dir("api/gmgn", "token-listings", data_type="output")
    
    print("Fetching bonded tokens from GMGN...")
    
    # Use the adapter to get bonded tokens
    try:
        adapter = _get_dragon_adapter()
        
        if adapter.gmgn_client is None:
            print("\n❌ Error: GMGN client not properly initialized")
            input("\nPress Enter to continue...")
            return
            
        tokens = adapter.get_bonded_tokens()
        
        # Process and save the results
        if tokens:
            output_file = output_dir / f"bonded_tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Display results
            print(f"\n✅ Successfully fetched {len(tokens)} bonded tokens")
            print(f"Results saved to {output_file}")
            
            # Show sample of the data
            print("\nSample token data:")
            for token in tokens[:3]:
                print(f"- {token.get('name', 'Unknown')} ({token.get('symbol', 'Unknown')}): {token.get('address', 'Unknown')}")
            if len(tokens) > 3:
                print(f"...and {len(tokens) - 3} more tokens")
        else:
            print("⚠️ No bonded tokens found")
    except Exception as e:
        print(f"\n❌ Handler error: {e}")
    
    input("\nPress Enter to continue...")


def gmgn_token_data():
    """Get token data from GMGN."""
    clear_terminal()
    print("🐲 Dragon GMGN Token Data")
    
    # Set up data directories
    output_dir = ensure_data_dir("api/gmgn", "token-data", data_type="output")
    
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
    if not answers:
        print("\n❌ No input provided")
        input("\nPress Enter to continue...")
        return
        
    contract_addresses_input = answers["contract_address"]
    contract_addresses = [addr.strip() for addr in contract_addresses_input.split() if addr.strip()]
    
    # Check if we have valid addresses
    if not contract_addresses:
        print("\n❌ No valid addresses provided")
        input("\nPress Enter to continue...")
        return
    
    # Use the adapter to get token information
    try:
        adapter = _get_dragon_adapter()
        
        if not hasattr(adapter, 'get_token_data_handler') or adapter.get_token_data_handler() is None:
            print("\n❌ Error: Token data handler not properly initialized")
            input("\nPress Enter to continue...")
            return
        
        # Display loading message based on number of tokens
        token_count = len(contract_addresses)
        if token_count == 1:
            print(f"\n🔍 Fetching token data for {contract_addresses[0]}...")
        else:
            print(f"\n🔍 Fetching token data for {token_count} tokens...")
        
        # Get the current time for timestamp in filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Fetch token data - handle both single and multiple tokens
        if token_count == 1:
            # Single token
            token_address = contract_addresses[0]
            token_info = adapter.get_token_info_sync(token_address)
            
            if token_info and "error" not in token_info:
                # Save token info to file
                output_file = output_dir / f"token_data_{token_address}_{timestamp}.json"
                with open(output_file, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                # Display results
                print("\n✅ Successfully fetched token data")
                print(f"Results saved to {output_file}")
                
                # Format and display token info
                print("\n📊 Token Information:")
                print(f"Name:             {token_info.get('name', 'Unknown')}")
                print(f"Symbol:           {token_info.get('symbol', 'Unknown')}")
                print(f"Price:            ${token_info.get('priceUsd', 0):.8f}")
                print(f"Market Cap:       ${token_info.get('marketCap', 0):,.2f}")
                print(f"Liquidity:        ${token_info.get('liquidityUsd', 0):,.2f}")
                print(f"24h Volume:       ${token_info.get('volume24h', 0):,.2f}")
                print(f"24h Change:       {token_info.get('priceChange24h', 0):.2f}%")
                print(f"Holders:          {token_info.get('holders', 0):,}")
            else:
                error_msg = token_info.get('error', 'Unknown error') if token_info else "No data returned"
                print(f"\n❌ Failed to get token data: {error_msg}")
        else:
            # Multiple tokens
            start_time = time.time()
            all_results = {}
            success_count = 0
            error_count = 0
            
            # Fetch data for each token
            for token_address in contract_addresses:
                print(f"  ⏳ Fetching data for {token_address}...")
                token_info = adapter.get_token_info_sync(token_address)
                
                if token_info and "error" not in token_info:
                    all_results[token_address] = token_info
                    print(f"  ✅ Successfully fetched data for {token_info.get('name', 'Unknown')} ({token_info.get('symbol', 'Unknown')})")
                    success_count += 1
                else:
                    error_msg = token_info.get('error', 'Unknown error') if token_info else "No data returned"
                    all_results[token_address] = {"error": error_msg, "address": token_address}
                    print(f"  ❌ Failed to fetch data for {token_address}: {error_msg}")
                    error_count += 1
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Save all results to a single file
            output_file = output_dir / f"token_data_multiple_{len(contract_addresses)}tokens_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "token_count": len(contract_addresses),
                    "success_count": success_count,
                    "error_count": error_count,
                    "data": all_results
                }, f, indent=2)
            
            # Display summary
            print(f"\n📊 Summary: {success_count} successful, {error_count} failed, completed in {elapsed:.2f} seconds")
            print(f"Results saved to {output_file}")
            
            # Display some details for successful tokens if there are any
            if success_count > 0:
                print("\nToken Details (successful tokens):")
                for token_address, data in all_results.items():
                    if "error" not in data:
                        print(f"\n--- {data.get('name', 'Unknown')} ({data.get('symbol', 'Unknown')}) ---")
                        print(f"Address:          {token_address}")
                        print(f"Price:            ${data.get('priceUsd', 0):.8f}")
                        print(f"Market Cap:       ${data.get('marketCap', 0):,.2f}")
                        print(f"Liquidity:        ${data.get('liquidityUsd', 0):,.2f}")
                        print(f"24h Volume:       ${data.get('volume24h', 0):,.2f}")
                        print(f"24h Change:       {data.get('priceChange24h', 0):.2f}%")
                        print(f"Holders:          {data.get('holders', 0):,}")
                        print(f"Network:          {data.get('network', 'Unknown')}")
                        if data.get('ath', 0) > 0:
                            print(f"All-time High:   ${data.get('ath', 0):.8f}")
                        if data.get('atl', 0) > 0:
                            print(f"All-time Low:    ${data.get('atl', 0):.8f}")
        
    except Exception as e:
        print(f"\n❌ Handler error: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to continue...")