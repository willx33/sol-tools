"""Command-line interface entry point for Sol Tools."""

import os
import sys
import curses
import argparse
import asyncio
from typing import Dict, Callable, Any, List
from pathlib import Path
import logging

from . import __version__
from .core.config import load_config
from .core.config_registry import ConfigRegistry
from .core.di_container import DIContainer
from .core.base_adapter import BaseAdapter
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
        
        'dragon_gmgn_token_data': dragon_handlers.gmgn_token_data,
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


def register_module_dependencies(container: DIContainer, test_mode: bool) -> None:
    """
    Register all module dependencies with the dependency injection container.
    
    Args:
        container: The dependency injection container
        test_mode: Whether to operate in test mode
    """
    # Import adapter classes
    from .modules.solana.solana_adapter import SolanaAdapter
    from .modules.dragon.dragon_adapter import DragonAdapter
    from .modules.dune.dune_adapter import DuneAdapter
    from .modules.gmgn.gmgn_adapter import GMGNAdapter
    from .modules.sharp.sharp_adapter import SharpAdapter
    
    # Register adapters with the container
    container.register_type(SolanaAdapter)
    container.register_type(DragonAdapter)
    container.register_type(DuneAdapter)
    container.register_type(GMGNAdapter)
    container.register_type(SharpAdapter)
    
    # Register any interfaces or other dependencies
    # ...


def register_module_schemas(registry: ConfigRegistry) -> None:
    """
    Register all module configuration schemas with the registry.
    
    Args:
        registry: The configuration registry
    """
    # Solana schema
    solana_schema = {
        "type": "object",
        "properties": {
            "default_channel": {"type": "string"},
            "require_dragon": {"type": "boolean"},
            "max_connections": {"type": "integer", "minimum": 1},
            "default_token_filter": {"type": "array", "items": {"type": "string"}}
        }
    }
    registry.register_schema(
        "solana", 
        solana_schema, 
        version="1.0.0", 
        required_env_vars=["HELIUS_API_KEY"]
    )
    
    # Dragon schema
    dragon_schema = {
        "type": "object",
        "properties": {
            "default_threads": {"type": "integer", "minimum": 1},
            "use_proxies": {"type": "boolean"}
        }
    }
    registry.register_schema("dragon", dragon_schema, version="1.0.0")
    
    # Dune schema
    dune_schema = {
        "type": "object",
        "properties": {
            "cache_results": {"type": "boolean"},
            "cache_timeout": {"type": "integer", "minimum": 60}
        }
    }
    registry.register_schema(
        "dune", 
        dune_schema, 
        version="1.0.0", 
        required_env_vars=["DUNE_API_KEY"]
    )
    
    # GMGN schema
    gmgn_schema = {
        "type": "object",
        "properties": {
            "default_output_format": {"type": "string", "enum": ["json", "csv", "table"]}
        }
    }
    registry.register_schema("gmgn", gmgn_schema, version="1.0.0")
    
    # Sharp schema
    sharp_schema = {
        "type": "object",
        "properties": {
            "default_prompt": {"type": "string"}
        }
    }
    registry.register_schema("sharp", sharp_schema, version="1.0.0")


def setup_application(args) -> tuple:
    """
    Set up the application components based on command-line arguments.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Tuple of (ConfigRegistry, DIContainer)
    """
    # Create configuration registry
    registry = ConfigRegistry(test_mode=args.test_mode)
    
    # Register module schemas
    register_module_schemas(registry)
    
    # Create dependency injection container
    container = DIContainer(test_mode=args.test_mode)
    
    # Register module dependencies
    register_module_dependencies(container, args.test_mode)
    
    return registry, container


def check_requirements():
    """
    Check if all required files and directories exist.
    Create any missing directories needed for operation.
    """
    # Load config to create default directories including input/output data dirs
    config = load_config()
    
    # All directory creation is now handled in the load_config function


def run_tests(args):
    """
    Run tests based on command-line arguments.
    
    Args:
        args: Command-line arguments with properties:
            - test_module: Optional name of a specific module to test
            - verbose: Whether to enable verbose output
    
    Returns:
        bool: True if all tests passed (including skipped tests), False if any test failed
    """
    try:
        # Import the test runner
        from .tests.test_runner import run_all_tests
        
        # Set debug environment variable if requested
        if args.verbose:
            os.environ["DEBUG_TESTS"] = "1"
        
        # Run the tests with asyncio
        exit_code = asyncio.run(run_all_tests(args.test_module))
        
        # Return True if exit_code is 0 (success), False otherwise
        # Note: exit_code 0 means all tests passed or skipped, 1 means some tests failed
        return exit_code == 0
    except ImportError as e:
        print(f"⚠️ Failed to import test runner: {str(e)}")
        print("❌ Could not find test framework")
        return False


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Sol Tools - Ultimate blockchain and crypto analysis toolkit")
    parser.add_argument('--version', action='version', version=f'Sol Tools {__version__}')
    parser.add_argument('--text-menu', action='store_true', help='Use text-based menu (inquirer) instead of curses')
    parser.add_argument('--test', action='store_true', help='Run all tests')
    parser.add_argument('--test-module', type=str, help='Run tests for a specific module (e.g., dragon, solana, file)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose test output')
    parser.add_argument('--report', '-r', action='store_true', help='Generate a test report')
    parser.add_argument('--clean', action='store_true', help='Clean cache and __pycache__ directories before starting')
    parser.add_argument('--use-curses', action='store_true', help='Use curses-based menu')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode')
    # No need to add --help as argparse adds it automatically
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    args = parse_args()
    
    # Set up logging
    logging_level = "DEBUG" if args.verbose else "INFO"
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if --no-mock is specified
    no_mock = "--no-mock" in sys.argv
    if no_mock:
        # Override test_mode to False when --no-mock is specified
        args.test_mode = False
        logging.info("Running with --no-mock flag: Mock implementations will be disabled")
    
    # Run tests if requested
    if args.test:
        run_tests(args)
        return
    
    # Check for required environment variables and files
    check_requirements()
    
    # Set up application components
    registry, container = setup_application(args)
    
    # If --no-mock is specified, make sure we're not using mock implementations
    if no_mock:
        from .modules.dragon.dragon_adapter import DRAGON_IMPORTS_SUCCESS
        if not DRAGON_IMPORTS_SUCCESS:
            logging.error("Cannot run with --no-mock flag because real Dragon implementation is not available")
            return 1
    
    # Create the handlers
    handlers = create_handlers()
    
    # Create and run the appropriate menu
    if args.text_menu:
        # Use inquirer menu if explicitly requested
        print("Using text-based menu as requested")
        menu = InquirerMenu(handlers)
        menu.run()
    else:
        try:
            # Set up curses menu by default
            menu = CursesMenu(handlers)
            curses.wrapper(menu.run)
        except Exception as e:
            print(f"Error in curses menu: {e}")
            print("Falling back to inquirer menu")
            # Reuse the same handlers to avoid rebuilding the main menu
            menu = InquirerMenu(handlers)
            menu.run()


if __name__ == "__main__":
    main()