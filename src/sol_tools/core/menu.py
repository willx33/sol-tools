"""Menu system for the Sol Tools CLI."""

import curses
import inquirer
from typing import Dict, List, Optional, Callable, Any, Union
from .config import edit_env_variables

class MenuOption:
    """Represents a single menu option."""
    def __init__(
        self,
        name: str,
        handler: Optional[Callable] = None,
        children: Optional[List['MenuOption']] = None,
        parent: Optional['MenuOption'] = None,
        description: str = "",
        missing_env_vars: bool = False
    ):
        self.name = name
        self.handler = handler
        self.children = children or []
        # Check for circular references in children
        for child in self.children:
            if child is self:
                print(f"ERROR: Circular reference detected in MenuOption {name}")
        self.parent = parent
        self.description = description
        self.missing_env_vars = missing_env_vars


class MenuManager:
    """Manages menu state and navigation in the CLI."""
    def __init__(self):
        # The current list of MenuOption items
        self.current_menu: List[MenuOption] = []
        # The index of whichever option is selected in the current menu
        self.selected_idx = 0
        # A history stack: each entry is (previous_menu, previous_selected_idx)
        self.history: List[tuple[List[MenuOption], int]] = []

    def execute_handler(self, handler: Callable) -> None:
        """Execute a handler function."""
        try:
            handler()
        except Exception as e:
            print(f"Handler error: {e}")

    def push_menu(self, options: List[MenuOption]):
        """Push new menu options onto the stack, saving current state to history."""
        # Debug logging to track recursion
        print(f"Pushing menu with {len(options)} options")
        if self.current_menu:
            print(f"Current menu has {len(self.current_menu)} options")
            # Check for circular reference
            if self.current_menu is options:
                print("ERROR: Circular reference detected - trying to push the same menu")
                return
            self.history.append((self.current_menu, self.selected_idx))
        self.current_menu = options
        self.selected_idx = 0

    def pop_menu(self) -> bool:
        """
        Pop the previous menu from the stack, restoring old selections.
        Returns False if we're already at the root (no history).
        """
        if not self.history:
            return False
        self.current_menu, self.selected_idx = self.history.pop()
        return True

    def get_current_option(self) -> Optional[MenuOption]:
        """Return the currently selected MenuOption, or None if there's no current menu."""
        if not self.current_menu:
            return None
        return self.current_menu[self.selected_idx]

    def move_selection(self, delta: int):
        """Move the selection cursor up/down by `delta` steps."""
        new_idx = self.selected_idx + delta
        if 0 <= new_idx < len(self.current_menu):
            self.selected_idx = new_idx


def check_module_env_vars(module_name: str) -> bool:
    """
    Check if required environment variables are set for a module.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        True if all required variables are set, False if any are missing
    """
    from .config import check_env_vars
    
    env_vars = check_env_vars(module_name)
    return all(env_vars.values()) if env_vars else True

def create_main_menu(handlers: Dict[str, Callable]) -> List[MenuOption]:
    """
    Build the top-level menu structure.
    """
    print("Creating main menu...")
    # Check environment variables for each module
    solana_env_vars_missing = not check_module_env_vars("solana")
    dragon_env_vars_missing = not check_module_env_vars("dragon")
    dune_env_vars_missing = not check_module_env_vars("dune")
    ethereum_env_vars_missing = not check_module_env_vars("ethereum")
    gmgn_env_vars_missing = not check_module_env_vars("gmgn")
    telegram_env_vars_missing = not check_module_env_vars("telegram")
    bullx_env_vars_missing = not check_module_env_vars("bullx")
    sharp_env_vars_missing = not check_module_env_vars("sharp")
    
    # Solana Tools (including Dragon Solana tools)
    solana_menu = [
        # Core Solana tools
        MenuOption("Token Watcher", handlers.get('solana_token_monitor'), 
                  description="Monitors token transactions. Saves to data/output-data/solana/transaction-data/.",
                  missing_env_vars=solana_env_vars_missing),
        MenuOption("Wallet Watcher", handlers.get('solana_wallet_monitor'),
                  description="Tracks wallet activity. Uses data/input-data/solana/wallet-lists/monitor-wallets.txt.",
                  missing_env_vars=solana_env_vars_missing),
        MenuOption("TG Data Extractor", handlers.get('solana_telegram_scraper'),
                  description="Extracts data from Telegram. Saves to data/output-data/solana/telegram/.",
                  missing_env_vars=telegram_env_vars_missing),
        
        # Dragon Solana tools
        MenuOption("Bundle Tracker - Dragon", handlers.get('solana_dragon_bundle'),
                  description="Finds bundled buys. Input: contract address.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Wallet Profiler - Dragon", handlers.get('solana_dragon_wallet'),
                  description="PnL analysis from wallet list. Uses data/input-data/solana/wallet-lists/.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Top Trader Finder - Dragon", handlers.get('solana_dragon_traders'),
                  description="Finds best traders by token. Output: data/output-data/solana/dragon/top-traders/.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        MenuOption("TX Scanner - Dragon", handlers.get('solana_dragon_scan'),
                  description="Gets all token transactions. Output: data/output-data/solana/dragon/transaction-data/.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Copycat Finder - Dragon", handlers.get('solana_dragon_copy'),
                  description="Finds copycat wallets. Input: wallet address to analyze.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Whale Tracker - Dragon", handlers.get('solana_dragon_holders'),
                  description="Lists major token holders. Output: data/output-data/solana/dragon/top-holders/.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Early Investor Finder - Dragon", handlers.get('solana_dragon_buyers'),
                  description="Finds first buyers for token. Input: contract address.",
                  missing_env_vars=solana_env_vars_missing or dragon_env_vars_missing),
        
        MenuOption("Back", None)
    ]
    
    # Sharp wallet and CSV tools
    wallet_analyzer_submenu = [
        MenuOption("Standard (No Export)", handlers.get('sharp_wallet_checker'),
                  description="Basic wallet analysis with no export file.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as JSON", handlers.get('sharp_wallet_checker_json'),
                  description="Wallet analysis with JSON export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as CSV", handlers.get('sharp_wallet_checker_csv'),
                  description="Wallet analysis with CSV export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as Excel", handlers.get('sharp_wallet_checker_excel'),
                  description="Wallet analysis with Excel workbook export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    address_splitter_submenu = [
        MenuOption("Standard (No Export)", handlers.get('sharp_wallet_splitter'),
                  description="Standard address splitting with no export.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as JSON", handlers.get('sharp_wallet_splitter_json'),
                  description="Address splitting with JSON export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as CSV", handlers.get('sharp_wallet_splitter_csv'),
                  description="Address splitting with CSV export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as Excel", handlers.get('sharp_wallet_splitter_excel'),
                  description="Address splitting with Excel workbook export.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    csv_combiner_submenu = [
        MenuOption("Standard (No Export)", handlers.get('sharp_csv_merger'),
                  description="Standard CSV combining with no export.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as JSON", handlers.get('sharp_csv_merger_json'),
                  description="CSV combining with JSON export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as CSV", handlers.get('sharp_csv_merger_csv'),
                  description="CSV combining with CSV export of results.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Export as Excel", handlers.get('sharp_csv_merger_excel'),
                  description="CSV combining with Excel workbook export.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    sharp_menu = [
        MenuOption("Wallet Analyzer", children=wallet_analyzer_submenu,
                  description="Analyzes wallet data via BullX API with enhanced progress tracking.",
                  missing_env_vars=False),
        MenuOption("Address Splitter", children=address_splitter_submenu,
                  description="Splits address lists to 25k chunks with validation and tracking.",
                  missing_env_vars=False),
        MenuOption("CSV Combiner", children=csv_combiner_submenu,
                  description="Combines CSV files with advanced options and detailed reporting.",
                  missing_env_vars=False),
        MenuOption("Profit Filter", handlers.get('sharp_pnl_checker'),
                  description="Filters CSV data by profit metrics. Uses data/input-data/sharp/pnl/.",
                  missing_env_vars=sharp_env_vars_missing or bullx_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    # API Tools (with Dune API and GMGN subsections)
    # Dune Analytics tools
    dune_menu = [
        MenuOption("Query Runner", handlers.get('dune_query'),
                  description="Runs Dune queries by ID. Output: data/output-data/api/dune/csv/.",
                  missing_env_vars=dune_env_vars_missing),
        MenuOption("Address Extractor", handlers.get('dune_parse'),
                  description="Extracts addresses from CSV. Input: data/input-data/api/dune/query-configs/, output: data/output-data/api/dune/parsed/.",
                  missing_env_vars=dune_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    # GMGN tools
    gmgn_menu = [
        MenuOption("Token Data", handlers.get('dragon_gmgn_token_data'),
                  description="Gets detailed information for Solana tokens. Output: data/output-data/api/gmgn/token-data/.",
                  missing_env_vars=gmgn_env_vars_missing or dragon_env_vars_missing),
        MenuOption("New Tokens", handlers.get('dragon_gmgn_new'),
                  description="Gets new listings from GMGN. Output: data/output-data/api/gmgn/token-listings/.",
                  missing_env_vars=gmgn_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Completing Tokens", handlers.get('dragon_gmgn_completing'),
                  description="Gets completing tokens from GMGN. Output: data/output-data/api/gmgn/token-listings/.",
                  missing_env_vars=gmgn_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Soaring Tokens", handlers.get('dragon_gmgn_soaring'),
                  description="Gets trending tokens from GMGN. Output: data/output-data/api/gmgn/token-listings/.",
                  missing_env_vars=gmgn_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Bonded Tokens", handlers.get('dragon_gmgn_bonded'),
                  description="Gets bonded tokens from GMGN. Output: data/output-data/api/gmgn/token-listings/.",
                  missing_env_vars=gmgn_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Market Cap Data", handlers.get('gmgn_mcap_data'),
                  description="Fetches market cap data for Solana tokens. Output: data/output-data/api/gmgn/market-cap-data/.",
                  missing_env_vars=gmgn_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    api_menu = [
        MenuOption("Dune API Tools", children=dune_menu,
                  description="Fetches and processes data from Dune Analytics API.",
                  missing_env_vars=False),
        MenuOption("GMGN Tools", children=gmgn_menu,
                  description="Tools for GMGN.ai data collection and processing.",
                  missing_env_vars=False),
        MenuOption("Back", None)
    ]
    
    # Ethereum Tools
    eth_menu = [
        MenuOption("Wallet Profiler - Dragon", handlers.get('dragon_eth_wallet'),
                  description="Analyzes ETH wallet performance. Uses data/input-data/ethereum/wallet-lists/.",
                  missing_env_vars=ethereum_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Top Trader Finder - Dragon", handlers.get('dragon_eth_traders'),
                  description="Finds ETH top traders. Output: data/output-data/ethereum/dragon/top-traders/.",
                  missing_env_vars=ethereum_env_vars_missing or dragon_env_vars_missing),
        MenuOption("TX Scanner - Dragon", handlers.get('dragon_eth_scan'),
                  description="Gets ETH token transactions. Output: data/output-data/ethereum/dragon/wallet-analysis/.",
                  missing_env_vars=ethereum_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Time-Based TX Finder - Dragon", handlers.get('dragon_eth_timestamp'),
                  description="Finds ETH txs by time range. Output: data/output-data/ethereum/dragon/early-buyers/.",
                  missing_env_vars=ethereum_env_vars_missing or dragon_env_vars_missing),
        MenuOption("Back", None)
    ]
    
    # Tron Tools (placeholder for future expansion)
    tron_menu = [
        MenuOption("Coming Soon", None,
                  description="Tron blockchain tools - currently in development."),
        MenuOption("Back", None)
    ]
    
    # Utilities and settings
    utils_menu = [
        MenuOption("Edit Environment Variables", edit_env_variables,
                  description="Sets API keys in .env file at project root."),
        MenuOption("Clear Cache", handlers.get('utils_clear_cache'),
                  description="Cleans cache directory."),
        MenuOption("Test Telegram", handlers.get('utils_test_telegram'),
                  description="Verifies Telegram API connection with test message."),
        MenuOption("Back", None)
    ]

    # Main menu with updated structure for missing environment variables
    return [
        MenuOption("Solana Tools", children=solana_menu,
                  description="Sol blockchain monitoring, analytics, and tracking.",
                  missing_env_vars=False),
        MenuOption("Sharp Tools", children=sharp_menu,
                  description="Wallet analysis, CSV processing, and BullX integration.",
                  missing_env_vars=False),
        MenuOption("API Tools", children=api_menu,
                  description="External API integrations (Dune, GMGN) for blockchain data.",
                  missing_env_vars=False),
        MenuOption("Eth Tools", children=eth_menu,
                  description="Ethereum blockchain analysis and wallet tracking.",
                  missing_env_vars=False),
        MenuOption("Tron Tools", children=tron_menu,
                  description="Tron blockchain tools (coming soon)."),
        MenuOption("Settings", children=utils_menu,
                  description="Configuration, cache, and API settings."),
        MenuOption("Exit", handlers.get('exit_app'),
                  description="Exit the application.")
    ]


class CursesMenu:
    """
    A curses-based menu interface with keyboard navigation.
    """
    def __init__(self, handlers: Dict[str, Callable]):
        self.manager = MenuManager()
        # Create the top-level menu from the handlers
        self.main_menu = create_main_menu(handlers)
        # Push the main menu as our starting point
        self.manager.push_menu(self.main_menu)
        self.running = True

    def _draw_menu(self, stdscr, title: str):
        """Render the current menu items on the terminal screen with scrolling."""
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Centered title with fancy border
        title_border = "╔" + "═" * (len(title) + 6) + "╗"
        title_text = "║   " + title + "   ║"
        title_footer = "╚" + "═" * (len(title) + 6) + "╝"
        
        # Calculate position for centered title block
        title_x = max((width - len(title_border)) // 2, 0)
        
        # Draw the title box
        stdscr.addstr(0, title_x, title_border)
        stdscr.addstr(1, title_x, title_text)
        stdscr.addstr(2, title_x, title_footer)
        
        # Draw description box right below the title box
        description_box_y = 4  # Position right below title box
        
        selected = self.manager.current_menu[self.manager.selected_idx]
        desc_text = ""
        if selected.description:
            desc_text = selected.description
        
        # Create description box - potentially with two lines of content
        desc_box_border_top = "╔" + "═" * (width - 2) + "╗"
        desc_box_footer = "╚" + "═" * (width - 2) + "╝"
        
        # Calculate if description needs two lines
        desc_max_width = width - 6  # Account for borders and padding
        needs_two_lines = len(desc_text) > desc_max_width
        
        if needs_two_lines and len(desc_text) > 0:
            # Split text between two lines, no truncation needed
            first_line = desc_text[:desc_max_width]
            second_line = desc_text[desc_max_width:]
            
            # Ensure second line isn't too long either
            if len(second_line) > desc_max_width:
                second_line = second_line[:desc_max_width - 3] + "..."
                
            # Format box with two content lines
            desc_box_line1 = "║ " + first_line + " " * (width - len(first_line) - 4) + " ║"
            desc_box_line2 = "║ " + second_line + " " * (width - len(second_line) - 4) + " ║"
            
            # Draw the 4-line description box
            stdscr.addstr(description_box_y, 0, desc_box_border_top)
            stdscr.addstr(description_box_y + 1, 0, desc_box_line1)
            stdscr.addstr(description_box_y + 2, 0, desc_box_line2)
            stdscr.addstr(description_box_y + 3, 0, desc_box_footer)
            
            # Menu starts after the taller box (with a 1-line gap)
            menu_start_y = description_box_y + 5
        else:
            # Single line is enough
            desc_box_middle = "║ " + desc_text + " " * (width - len(desc_text) - 4) + " ║"
            
            # Draw the 3-line description box
            stdscr.addstr(description_box_y, 0, desc_box_border_top)
            stdscr.addstr(description_box_y + 1, 0, desc_box_middle)
            stdscr.addstr(description_box_y + 2, 0, desc_box_footer)
            
            # Menu starts after the standard box (with a 1-line gap)
            menu_start_y = description_box_y + 4  
        
        # Dynamically calculate how many menu items can fit on screen
        # Based on header + actual description box size + gap + margin
        menu_height = height - menu_start_y - 1
        
        # Calculate scrolling window
        total_items = len(self.manager.current_menu)
        start_idx = 0
        
        # If we need to scroll to keep selection visible
        if self.manager.selected_idx >= menu_height:
            # Start showing items so selected is visible
            start_idx = max(0, self.manager.selected_idx - menu_height + 1)
            
        # Calculate how many items we can show with available space
        visible_items = min(menu_height, total_items - start_idx)
        
        # First pass: draw all non-selected items
        for i in range(visible_items):
            idx = i + start_idx
            option = self.manager.current_menu[idx]
            y = i + menu_start_y
            
            # Skip the selected item for now, we'll draw it last
            if idx == self.manager.selected_idx:
                continue
                
            # Normal display for non-selected items
            # Add red dot indicator for missing env vars but no arrow for non-selected items
            if option.missing_env_vars:
                option_text = f"{option.name} 🔴"
            else:
                option_text = f"{option.name}"
            
            x = max((width - len(option_text)) // 2, 0)
            
            # Only draw if it fits on screen
            if y < height - 1:
                stdscr.addstr(y, x, option_text)
        
        # Second pass: draw only the selected item with highlighting
        # This ensures it's drawn on top with proper attributes
        if self.manager.selected_idx >= start_idx and self.manager.selected_idx < start_idx + visible_items:
            # Calculate position for the selected item
            selected_y = menu_start_y + (self.manager.selected_idx - start_idx)
            option = self.manager.current_menu[self.manager.selected_idx]
            
            # Create highlighted text with padding
            # Add red dot indicator for missing env vars and arrow ONLY for selected item
            if option.missing_env_vars:
                option_text = f"▶ {option.name} 🔴"
            else:
                option_text = f"▶ {option.name}"
            
            padded_text = f" {option_text} "
            padded_x = max((width - len(padded_text)) // 2, 0)
            
            # Draw with highlighting only if it fits on screen
            if selected_y < height - 1:
                try:
                    # Use only A_REVERSE for better compatibility
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addstr(selected_y, padded_x, padded_text)
                    stdscr.attroff(curses.A_REVERSE)
                except curses.error:
                    # Fallback if we encounter any curses errors
                    pass

        stdscr.refresh()

    def run(self, stdscr):
        """
        Main event loop for curses-based menu. Blocks until
        user chooses 'Exit' or we hit an error.
        """
        curses.curs_set(0)     # Hide the cursor
        stdscr.keypad(True)    # Enable keypad mode for arrow keys

        while self.running:
            # Decide what to show in the title bar based on current section
            if self.manager.current_menu == self.main_menu:
                title = "Sol Tools - Main Menu"
            else:
                # Try to find the name of the current section from history
                current_section = "Sol Tools"
                for option in self.main_menu:
                    if option.children and option.children == self.manager.current_menu:
                        current_section = f"Sol Tools - {option.name}"
                        break
                title = current_section

            try:
                # Draw everything
                self._draw_menu(stdscr, title)

                # Get user input
                key = stdscr.getch()

                if key == curses.KEY_UP:
                    self.manager.move_selection(-1)
                elif key == curses.KEY_DOWN:
                    self.manager.move_selection(1)
                elif key == ord('\n'):  # Enter / Return
                    option = self.manager.get_current_option()
                    if not option:
                        continue

                    # If user selected "Back"...
                    if option.name == "Back":
                        # ...pop from history. If we can't, it means we're at root, so end.
                        if not self.manager.pop_menu():
                            break
                        continue

                    # If user selected "Exit"...
                    if option.name == "Exit":
                        if option.handler:
                            self.manager.execute_handler(option.handler)
                        break

                    # If the item has sub-items, push them as a new menu
                    if option.children:
                        self.manager.push_menu(option.children)

                    # If the item has a handler, run it
                    elif option.handler:
                        # Temporarily leave curses mode to run the handler
                        curses.endwin()
                        self.manager.execute_handler(option.handler)

                        # Wait so user can see output in normal terminal
                        print("\nPress Enter to continue...")
                        input()

                        # Return to curses display
                        stdscr.refresh()

            except KeyboardInterrupt:
                # If user hits Ctrl+C
                break
            except Exception as e:
                # For any other error, exit the loop
                self.running = False
                raise e


class InquirerMenu:
    """
    An inquirer-based menu interface with arrow key navigation.
    """
    def __init__(self, handlers: Dict[str, Callable]):
        self.manager = MenuManager()
        self.main_menu = create_main_menu(handlers)
        self.manager.push_menu(self.main_menu)
        self.running = True
    
    def run(self):
        """Run the inquirer-based menu system."""
        while self.running:
            try:
                # Create choices list from current menu
                choices = []
                for option in self.manager.current_menu:
                    choice_text = option.name
                    # Add red dot indicator for missing env vars
                    if option.missing_env_vars:
                        choice_text = f"{choice_text} 🔴"
                    choices.append((choice_text, option))
                
                # If not at the main menu, add "Back" choice
                is_main_menu = self.manager.current_menu == self.main_menu
                title = "Sol Tools - Main Menu" if is_main_menu else "Sol Tools"
                
                # Use inquirer to create an interactive menu with arrow key navigation
                questions = [
                    inquirer.List('choice',
                                message=title,
                                choices=[choice[0] for choice in choices],
                                carousel=True)
                ]
                
                # Get user selection
                try:
                    answers = inquirer.prompt(questions, raise_keyboard_interrupt=True)
                    if not answers:  # User pressed Ctrl+C
                        break
                        
                    # Find the selected option
                    selected_text = answers['choice']
                    selected_option = None
                    for choice_text, option in choices:
                        if choice_text == selected_text:
                            selected_option = option
                            break
                            
                    if not selected_option:
                        continue
                    
                    # Handle the selection
                    if selected_option.name == "Back" or selected_text.startswith("Back"):
                        if not self.manager.pop_menu():
                            break
                        continue
                    
                    if selected_option.name == "Exit" or selected_text.startswith("Exit"):
                        if selected_option.handler:
                            selected_option.handler()
                        break
                    
                    if selected_option.children:
                        self.manager.push_menu(selected_option.children)
                    elif selected_option.handler:
                        selected_option.handler()
                        
                        # Wait for user acknowledgment
                        input("\nPress Enter to continue...")
                    
                except KeyboardInterrupt:
                    break
                
            except Exception as e:
                print(f"Menu error: {e}")
                input("\nPress Enter to continue...")