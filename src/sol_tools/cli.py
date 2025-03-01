"""Command-line interface entry point for Sol Tools."""

import os
import sys
import curses
import argparse
import asyncio
from typing import Dict, Callable, Any
from pathlib import Path

from . import __version__
from .core.config import load_config, check_env_vars, get_env_var
from .core.menu import CursesMenu, InquirerMenu

# Import handlers for each module
from .modules.dragon import handlers as dragon_handlers
from .modules.dune import handlers as dune_handlers
from .modules.sharp import handlers as sharp_handlers
from .modules.solana import handlers as solana_handlers
from .modules.gmgn import handlers as gmgn_handlers
from .utils import common as utils_handlers

# Set up centralized __pycache__ location if not already set
if 'PYTHONPYCACHEPREFIX' not in os.environ:
    root_dir = Path(__file__).parents[2]  # Get project root
    pycache_dir = root_dir / "data" / "__pycache__"
    pycache_dir.mkdir(parents=True, exist_ok=True)
    os.environ['PYTHONPYCACHEPREFIX'] = str(pycache_dir)


def exit_app() -> None:
    """Handler for the Exit menu option."""
    print("Exiting Sol Tools. Goodbye!")
    sys.exit(0)


def create_handlers() -> Dict[str, Callable[[], Any]]:
    """
    Create a dictionary of all available handlers mapped to their menu identifiers.
    This is what connects menu options to actual functionality.
    """
    handlers = {
        # Exit function
        'exit_app': exit_app,
        
        # Dragon module handlers - from dragon/handlers.py
        'dragon_solana_bundle': dragon_handlers.solana_bundle_checker,
        'dragon_solana_wallet': dragon_handlers.solana_wallet_checker, 
        'dragon_solana_traders': dragon_handlers.solana_top_traders,
        'dragon_solana_scan': dragon_handlers.solana_scan_tx,
        'dragon_solana_copy': dragon_handlers.solana_copy_wallet_finder,
        'dragon_solana_holders': dragon_handlers.solana_top_holders,
        'dragon_solana_buyers': dragon_handlers.solana_early_buyers,
        
        # Alternative Dragon handlers from solana/handlers.py - these will be used by the menu
        'solana_dragon_bundle': solana_handlers.dragon_solana_bundle,
        'solana_dragon_wallet': solana_handlers.dragon_solana_wallet,
        'solana_dragon_traders': solana_handlers.dragon_solana_traders,
        'solana_dragon_scan': solana_handlers.dragon_solana_scan,
        'solana_dragon_copy': solana_handlers.dragon_solana_copy,
        'solana_dragon_holders': solana_handlers.dragon_solana_holders,
        'solana_dragon_buyers': solana_handlers.dragon_solana_buyers,
        
        'dragon_eth_wallet': dragon_handlers.eth_wallet_checker,
        'dragon_eth_traders': dragon_handlers.eth_top_traders,
        'dragon_eth_scan': dragon_handlers.eth_scan_tx,
        'dragon_eth_timestamp': dragon_handlers.eth_timestamp,
        
        'dragon_gmgn_info': dragon_handlers.gmgn_token_info,
        'dragon_gmgn_new': dragon_handlers.gmgn_new_tokens,
        'dragon_gmgn_completing': dragon_handlers.gmgn_completing_tokens,
        'dragon_gmgn_soaring': dragon_handlers.gmgn_soaring_tokens,
        'dragon_gmgn_bonded': dragon_handlers.gmgn_bonded_tokens,
        
        # Dune module handlers
        'dune_query': dune_handlers.run_query,
        'dune_parse': dune_handlers.parse_csv,
        
        # GMGN module handler
        'gmgn_mcap_data': lambda: asyncio.run(gmgn_handlers.fetch_mcap_data_handler()),
        
        # Sharp module handlers
        'sharp_wallet_checker': lambda: sharp_handlers.wallet_checker(),
        'sharp_wallet_checker_json': lambda: sharp_handlers.wallet_checker(export_format='json'),
        'sharp_wallet_checker_csv': lambda: sharp_handlers.wallet_checker(export_format='csv'),
        'sharp_wallet_checker_excel': lambda: sharp_handlers.wallet_checker(export_format='excel'),
        
        # Sharp wallet splitter with export options
        'sharp_wallet_splitter': lambda: sharp_handlers.wallet_splitter(),
        'sharp_wallet_splitter_json': lambda: sharp_handlers.wallet_splitter(export_format='json'),
        'sharp_wallet_splitter_csv': lambda: sharp_handlers.wallet_splitter(export_format='csv'),
        'sharp_wallet_splitter_excel': lambda: sharp_handlers.wallet_splitter(export_format='excel'),
        
        # Sharp CSV merger with export options
        'sharp_csv_merger': lambda: sharp_handlers.csv_merger(),
        'sharp_csv_merger_json': lambda: sharp_handlers.csv_merger(export_format='json'),
        'sharp_csv_merger_csv': lambda: sharp_handlers.csv_merger(export_format='csv'),
        'sharp_csv_merger_excel': lambda: sharp_handlers.csv_merger(export_format='excel'),
        
        'sharp_pnl_checker': sharp_handlers.pnl_checker,
        
        # Solana module handlers
        'solana_token_monitor': solana_handlers.token_monitor,
        'solana_wallet_monitor': solana_handlers.wallet_monitor,
        'solana_telegram_scraper': solana_handlers.telegram_scraper,
        
        # Utility handlers
        'utils_clear_cache': utils_handlers.clear_cache,
        'utils_test_telegram': utils_handlers.test_telegram,
    }
    
    return handlers


def check_requirements():
    """
    Check if all required files and directories exist.
    Create any missing directories needed for operation.
    """
    # Load config to create default directories including input/output data dirs
    config = load_config()
    
    # All directory creation is now handled in the load_config function


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Sol Tools - Ultimate blockchain and crypto analysis toolkit")
    parser.add_argument('--version', action='version', version=f'Sol Tools {__version__}')
    parser.add_argument('--text-menu', action='store_true', help='Use text-based menu (inquirer) instead of curses')
    parser.add_argument('--test', action='store_true', help='Run file system tests')
    parser.add_argument('--clean', action='store_true', help='Clean cache and __pycache__ directories before starting')
    # No need to add --help as argparse adds it automatically
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Check if the test flag is set
    if args.test:
        try:
            from .tests.test_runner import run_all_tests
            sys.exit(0 if run_all_tests() else 1)
        except ImportError:
            # Fall back to legacy test if new framework is not available
            from .utils.test_file_ops import run_all_tests
            sys.exit(0 if run_all_tests() else 1)
    
    # Check if the clean flag is set
    if args.clean:
        print("Cleaning cache and __pycache__ directories...")
        try:
            from .utils.cleanup import clean_caches
            success = clean_caches()
            if not success:
                print("Warning: Some errors occurred during cleanup")
            if len(sys.argv) == 2:  # Only --clean was specified, exit after cleaning
                sys.exit(0)
        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Continue with execution even if cleanup fails
    
    # Check if required directories exist
    check_requirements()
    
    # Create all function handlers
    handlers = create_handlers()
    
    # Run appropriate menu based on args
    if args.text_menu:
        menu = InquirerMenu(handlers)
        menu.run()
    else:
        try:
            menu = CursesMenu(handlers)
            curses.wrapper(menu.run)
        except Exception as e:
            print(f"Error with curses menu: {e}")
            print("Falling back to text-based menu...")
            menu = InquirerMenu(handlers)
            menu.run()


if __name__ == "__main__":
    main()