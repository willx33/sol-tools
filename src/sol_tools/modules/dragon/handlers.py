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
from pathlib import Path

from ...utils.common import clear_terminal, ensure_data_dir, check_proxy_file
from ...core.config import check_env_vars
from .dragon_adapter import DragonAdapter

# Setup logging with a NullHandler to prevent "No handlers could be found" warnings
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Check if we're in test mode
IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

# If in test mode, silence all logging from this module
if IN_TEST_MODE:
    # Create a do-nothing handler
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    
    # Set critical+1 level (higher than any standard level)
    logger.setLevel(logging.CRITICAL + 1)
    
    # Remove any existing handlers and add our null handler
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.addHandler(NullHandler())

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
        # Initialize the adapter directly - it's not an async method
        adapter.initialize()
        
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
            validate=lambda x: all(len(addr.strip()) in [43, 44] for addr in x.split()) if x else False
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
    
    # Set up directories
    wallet_dir = ensure_data_dir("api", "solana", "wallets")
    output_dir = ensure_data_dir("api", "solana", "wallet-analysis")
    
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
            default="10"
        ),
        inquirer.Confirm(
            "use_proxies",
            message="Use proxies?",
            default=False
        ),
        inquirer.Confirm(
            "skip_wallets",
            message="Skip wallet importing? (Use if already imported)",
            default=False
        )
    ]
    answers = inquirer.prompt(option_questions)
    
    if answers:
        threads = int(answers.get("threads", "10"))
        use_proxies = answers.get("use_proxies", False)
        skip_wallets = answers.get("skip_wallets", False)
        
        # Check proxy file if using proxies
        if use_proxies:
            if not check_proxy_file():
                print("❌ Proxy file check failed. Continuing without proxies.")
                use_proxies = False
        
        try:
            # Import the adapter
            adapter = _get_dragon_adapter()
            
            # Import wallets if not skipping
            if not skip_wallets:
                if not adapter.import_ethereum_wallets(str(wallets_path)):
                    print("❌ Failed to import wallets from file. Please check the file format.")
                    input("\nPress Enter to continue...")
                    return
            
            # Run the wallet checker
            print(f"\n🔍 Analyzing Ethereum wallets with {threads} threads...")
            
            # Create instance with the appropriate parameters
            wallet_checker = adapter.eth_bulk_wallet_checker(
                wallets=adapter.ethereum_wallets,
                skip_wallets=skip_wallets,
                threads=threads,
                proxies=use_proxies
            )
            
            # Call the run method as per the reference implementation
            if wallet_checker is None:
                print("\n❌ Failed to initialize wallet checker")
                return False
            result = wallet_checker.run()
            
            if result:
                print("\n✅ Ethereum wallet checking completed successfully!")
                print(f"📁 Results saved to output directory")
            else:
                print("\n❌ Failed to check Ethereum wallets.")
        
        except Exception as e:
            print(f"\n❌ Error during Ethereum wallet check: {str(e)}")
    
    input("\nPress Enter to continue...")


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
    """Check Ethereum wallet performance metrics."""
    clear_terminal()
    print("🐲 Dragon Ethereum Wallet Checker")
    
    try:
        # Check for required environment variables
        from ...utils.common import validate_credentials
        if not validate_credentials("ethereum"):
            return
        
        # Setup wallet directory paths
        project_root = Path(__file__).parent.parent.parent.parent.parent  # Navigate up to project root
        default_input_dir = project_root / "data" / "input-data" / "ethereum" / "wallets"
        general_input_dir = project_root / "data" / "input-data"
        
        # Ensure default directory exists
        os.makedirs(default_input_dir, exist_ok=True)
        
        # Create example file if it doesn't exist
        default_wallets_file = default_input_dir / "wallets.txt"
        if not os.path.exists(default_wallets_file):
            with open(default_wallets_file, 'w') as f:
                f.write("# Add wallet addresses here (one per line)")
        
        # Find all .txt files in both default and general input directories
        default_files = list(default_input_dir.glob("*.txt"))
        
        # Search for .txt files in all subdirectories of general_input_dir
        all_input_files = []
        for file_path in general_input_dir.glob("**/*.txt"):
            # Skip files that are already in default_files or are from default directory
            rel_path = file_path.relative_to(general_input_dir)
            if str(rel_path).startswith("ethereum/wallets/"):
                continue
            all_input_files.append(file_path)
        
        # Combine lists, with default files first
        input_files = default_files + all_input_files
        
        if not input_files:
            print("❌ No wallet files found in any input directory.")
            print(f"📁 Please place your wallet list files in: {default_input_dir}")
            print("💡 Use the --wallet/-w option to specify a wallet list file.")
            input("\nPress Enter to continue...")
            return
        
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
            print("\nSelect a file by number:")
            for i, file_path in enumerate(input_files, 1):
                # Use relative path from project root for display
                rel_path = file_path.relative_to(project_root)
                
                # Only mark this specific file as default
                specific_default_path = "data/input-data/ethereum/wallets/wallets.txt"
                is_default = str(rel_path) == specific_default_path
                
                display_name = f"{rel_path} {'🔹 (default)' if is_default else ''}"
                print(f"  {i}. {display_name}")
            
            while True:
                file_choice = input("\n➤ Select option (or press Enter for default file): ").strip()
                
                # Handle empty input - use default file
                if not file_choice:
                    wallets_path = str(default_wallets_file)
                    print(f"\n✅ Using default file: data/input-data/ethereum/wallets/wallets.txt")
                    break
                
                try:
                    choice_num = int(file_choice)
                    if 1 <= choice_num <= len(input_files):
                        wallets_path = str(input_files[choice_num - 1])
                        break
                    else:
                        print(f"\n❌ Please enter a number between 1 and {len(input_files)}")
                except ValueError:
                    print("\n❌ Please enter a valid number")
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
                default="10"
            ),
            inquirer.Confirm(
                "use_proxies",
                message="Use proxies?",
                default=False
            ),
            inquirer.Confirm(
                "skip_wallets",
                message="Skip wallet importing? (Use if already imported)",
                default=False
            )
        ]
        answers = inquirer.prompt(option_questions)
        
        if answers:
            threads = int(answers.get("threads", "10"))
            use_proxies = answers.get("use_proxies", False)
            skip_wallets = answers.get("skip_wallets", False)
            
            # Check proxy file if using proxies
            if use_proxies:
                if not check_proxy_file():
                    print("❌ Proxy file check failed. Continuing without proxies.")
                    use_proxies = False
            
            try:
                # Import the adapter
                adapter = _get_dragon_adapter()
                
                # Import wallets if not skipping
                if not skip_wallets:
                    if not adapter.import_ethereum_wallets(str(wallets_path)):
                        print("❌ Failed to import wallets from file. Please check the file format.")
                        input("\nPress Enter to continue...")
                        return
                
                # Run the wallet checker
                print(f"\n🔍 Analyzing Ethereum wallets with {threads} threads...")
                
                # Create output directory
                output_dir = project_root / "data" / "output-data" / "ethereum" / "wallet-analysis"
                os.makedirs(output_dir, exist_ok=True)
                
                try:
                    # Create instance with the appropriate parameters
                    wallet_checker = adapter.eth_bulk_wallet_checker(
                        wallets=adapter.ethereum_wallets,
                        skip_wallets=skip_wallets,
                        threads=threads,
                        proxies=use_proxies,
                        output_dir=output_dir
                    )
                    
                    # Check if the wallet_checker is None (e.g., due to initialization failure)
                    if wallet_checker is None:
                        print("\n❌ Error: Ethereum wallet checker could not be initialized.")
                        print("This could be due to missing dependencies or configuration issues.")
                        input("\nPress Enter to continue...")
                        return
                    
                    # Call the run method as per the reference implementation
                    if wallet_checker is None:
                        print("\n❌ Failed to initialize wallet checker")
                        return False
                    result = wallet_checker.run()
                    
                    if result:
                        print("\n✅ Ethereum wallet checking completed successfully!")
                        print(f"📁 Results saved to: {output_dir}")
                    else:
                        print("\n❌ Failed to check Ethereum wallets.")
                        
                except AttributeError as ae:
                    if "NoneType" in str(ae) and "handlers" in str(ae).lower():
                        print("\n❌ Handler error: The logging system is not properly configured.")
                    else:
                        print(f"\n❌ Error initializing wallet checker: {str(ae)}")
                except Exception as e:
                    print(f"\n❌ Error during Ethereum wallet check: {str(e)}")
            
            except Exception as e:
                print(f"\n❌ Error during Ethereum wallet setup: {str(e)}")
        
    except Exception as outer_e:
        print(f"\n❌ Unexpected error: {str(outer_e)}")
    
    input("\nPress Enter to continue...")


def eth_top_traders():
    """Find top Ethereum traders for specific tokens."""
    clear_terminal()
    print("🐲 Dragon Ethereum Top Traders")
    
    try:
        # Import the adapter first to catch initialization errors
        adapter = _get_dragon_adapter()
        
        # Check for required environment variables
        from ...utils.common import validate_credentials
        if not validate_credentials("ethereum"):
            return
        
        # Ask for token address
        token_questions = [
            inquirer.Text(
                "token_address",
                message="Enter token contract address:",
                validate=lambda _, x: x.startswith('0x') and len(x) == 42
            ),
            inquirer.Text(
                "days",
                message="Number of days to analyze:",
                default="30",
                validate=lambda _, x: x.isdigit() and int(x) > 0
            )
        ]
        
        token_answers = inquirer.prompt(token_questions)
        
        if not token_answers:
            return
        
        token_address = token_answers.get("token_address")
        days = int(token_answers.get("days", "30"))
        
        print(f"\n🔍 Finding top traders for {token_address} over the last {days} days...")
        
        # Create output directory
        output_dir = ensure_data_dir("ethereum", "top-traders", data_type="output")
        
        try:
            # Create instance with the appropriate parameters
            kwargs = {
                'token_address': token_address,
                'days': days,
                'output_dir': output_dir,
                'test_mode': False
            }
            top_traders = adapter.eth_top_traders(**kwargs)
            
            if top_traders is None:
                print("\n❌ Failed to initialize top traders analyzer")
                return False
                
            # Run the analysis
            result = top_traders.run(token_address=kwargs['token_address'])
            
            if result:
                print("\n✅ Top traders analysis completed successfully!")
                print(f"📁 Results saved to: {output_dir}")
            else:
                print("\n❌ Failed to find top traders.")
        
        except ImportError as e:
            print(f"\n❌ Ethereum module initialization error: {str(e)}")
            print("Please ensure all Ethereum dependencies are installed correctly.")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("Please check your inputs and try again.")
        
    input("\nPress Enter to continue...")


def eth_scan_all_tx():
    """Scan all transactions for Ethereum addresses."""
    clear_terminal()
    print("🐲 Dragon Ethereum Transaction Scanner")
    
    # Check for required environment variables
    from ...utils.common import validate_credentials
    if not validate_credentials("ethereum"):
        return
    
    # Ask for addresses
    address_questions = [
        inquirer.Text(
            "addresses",
            message="Enter Ethereum addresses (comma separated):",
            validate=lambda _, x: all(addr.strip().startswith('0x') and len(addr.strip()) == 42 for addr in x.split(','))
        ),
        inquirer.Text(
            "start_block",
            message="Starting block (optional, leave empty for default):",
            default=""
        ),
        inquirer.Text(
            "end_block",
            message="Ending block (optional, leave empty for latest):",
            default=""
        )
    ]
    
    address_answers = inquirer.prompt(address_questions)
    
    if not address_answers:
        return
    
    addresses = [addr.strip() for addr in address_answers.get("addresses", "").split(',')]
    start_block_str = address_answers.get("start_block", "").strip()
    end_block_str = address_answers.get("end_block", "").strip()
    
    start_block = int(start_block_str) if start_block_str else None
    end_block = int(end_block_str) if end_block_str else None
    
    try:
        # Import the adapter
        adapter = _get_dragon_adapter()
        
        print(f"\n🔍 Scanning transactions for {len(addresses)} addresses...")
        
        # Create output directory
        output_dir = ensure_data_dir("ethereum", "transaction-scans", data_type="output")
        
        # Create instance with the appropriate parameters
        scanner = adapter.eth_scan_all_tx(
            addresses=addresses,
            start_block=start_block,
            end_block=end_block,
            output_dir=output_dir
        )
        
        # Call the run method
        if scanner is None:
            print("\n❌ Failed to initialize transaction scanner")
            return False
        result = scanner.run()
        
        if result:
            print("\n✅ Transaction scanning completed successfully!")
            print(f"📁 Results saved to: {output_dir}")
        else:
            print("\n❌ Failed to scan transactions.")
    
    except Exception as e:
        print(f"\n❌ Error during transaction scanning: {str(e)}")
    
    input("\nPress Enter to continue...")


def eth_timestamp_transactions():
    """Find transactions within a specific time range."""
    clear_terminal()
    print("🐲 Dragon Ethereum Timestamp Transactions")
    
    try:
        # Import the adapter first to catch initialization errors
        adapter = _get_dragon_adapter()
        
        # Check for required environment variables
        from ...utils.common import validate_credentials
        if not validate_credentials("ethereum"):
            return
            
        # Ask for contract address and time range
        from datetime import datetime, timedelta
        
        # Default time range (last 24 hours)
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        # Format for display and input
        date_format = "%Y-%m-%d %H:%M:%S"
        
        questions = [
            inquirer.Text(
                "contract_address",
                message="Enter contract address:",
                validate=lambda _, x: x.startswith('0x') and len(x) == 42
            ),
            inquirer.Text(
                "start_time",
                message=f"Start time ({date_format}):",
                default=yesterday.strftime(date_format)
            ),
            inquirer.Text(
                "end_time",
                message=f"End time ({date_format}):",
                default=now.strftime(date_format)
            )
        ]
        
        answers = inquirer.prompt(questions)
        
        if not answers:
            return
            
        contract_address = answers.get("contract_address")
        
        try:
            start_time_str = answers.get("start_time", "")
            end_time_str = answers.get("end_time", "")
            
            if not start_time_str or not end_time_str:
                print("\n❌ Invalid date format: Start time or end time is missing")
                return
                
            start_time = int(datetime.strptime(start_time_str, date_format).timestamp())
            end_time = int(datetime.strptime(end_time_str, date_format).timestamp())
            
        except ValueError as e:
            print(f"\n❌ Invalid date format: {str(e)}")
            return
            
        # Create output directory
        output_dir = ensure_data_dir("ethereum", "timestamp-tx", data_type="output")
        
        try:
            # Create instance with the appropriate parameters
            kwargs = {
                'contract_address': contract_address,
                'start_time': start_time,
                'end_time': end_time,
                'output_dir': output_dir
            }
            timestamp_tx = adapter.eth_timestamp_transactions(**kwargs)
            
            if timestamp_tx is None:
                print("\n❌ Failed to initialize timestamp transactions analyzer")
                return False
                
            # Run the analysis
            result = timestamp_tx.run(
                contract_address=kwargs['contract_address'],
                start_time=kwargs['start_time'],
                end_time=kwargs['end_time']
            )
            
            if result:
                print("\n✅ Timestamp transactions analysis completed successfully!")
                print(f"📁 Results saved to: {output_dir}")
            else:
                print("\n❌ Failed to find transactions in the specified time range.")
        
        except ImportError as e:
            print(f"\n❌ Ethereum module initialization error: {str(e)}")
            print("Please ensure all Ethereum dependencies are installed correctly.")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("Please check your inputs and try again.")
        
    input("\nPress Enter to continue...")


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
            validate=lambda x: all(len(addr.strip()) in [43, 44] for addr in x.split()) if x else False
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