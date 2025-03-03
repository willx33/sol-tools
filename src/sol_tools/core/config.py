"""Configuration management for Sol Tools."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import inquirer
from dotenv import load_dotenv, set_key
from rich.console import Console

# Base paths
ROOT_DIR = Path(__file__).parents[3]
DATA_DIR = ROOT_DIR / "data"
INPUT_DATA_DIR = DATA_DIR / "input-data"
OUTPUT_DATA_DIR = DATA_DIR / "output-data"
CONFIG_DIR = ROOT_DIR / "config"
CACHE_DIR = DATA_DIR / "cache"

# Environment variables
ENV_FILE = ROOT_DIR / ".env"

# Config files
MAIN_CONFIG = CONFIG_DIR / "config.json"

# Required environment variables by module
REQUIRED_ENV_VARS = {
    "dragon": [
    ],
    "dune": [
        "DUNE_API_KEY"
    ],
    "solana": [
        "HELIUS_API_KEY"
    ],
    "ethereum": [
    ],
    "gmgn": [
    ],
    "telegram": [
        "TELEGRAM_BOT_TOKEN", 
        "TELEGRAM_CHAT_ID"
    ],
    "bullx": [
    ],
    "sharp": []
}

# Default configuration
DEFAULT_CONFIG = {
    "proxy_enabled": False,
    "proxy_file": "data/input-data/proxies/proxies.txt",
    "data_dir": "data",
    "input_data_dir": "data/input-data",
    "output_data_dir": "data/output-data",
    "cache_dir": "data/cache",
    "theme": "dark"
}

# Create a simple safer prompt function
def safe_prompt(questions):
    """A wrapper around inquirer.prompt that handles validation safely."""
    # Use direct input() for Text questions to avoid validation errors
    if len(questions) == 1 and isinstance(questions[0], inquirer.Text):
        q = questions[0]
        console = Console()
        console.print(f"{q.message}: ", end="")
        if q.default:
            console.print(f"[dim]{q.default}[/dim] ", end="")
        
        result = input()
        if not result and q.default:
            result = q.default
            
        return {q.name: result}
    else:
        # Use regular inquirer.prompt for other question types
        return inquirer.prompt(questions)


def load_config() -> Dict[str, Any]:
    """Load configuration from files and environment variables."""
    # Create directories if they don't exist
    for directory in [DATA_DIR, CONFIG_DIR, CACHE_DIR, INPUT_DATA_DIR, OUTPUT_DATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # List of all modules that need base directories
    modules = ["solana", "ethereum"]
    
    # Create base output directories for these modules only
    for module in modules:
        (OUTPUT_DATA_DIR / module).mkdir(parents=True, exist_ok=True)
    
    # Create new organized input directory structure by blockchain/API
    
    # Solana
    (INPUT_DATA_DIR / "solana").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "solana" / "token-lists").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "solana" / "wallets").mkdir(parents=True, exist_ok=True)
    
    # Ethereum
    (INPUT_DATA_DIR / "ethereum").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "ethereum" / "token-lists").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "ethereum" / "wallets").mkdir(parents=True, exist_ok=True)
    
    # Sharp
    (INPUT_DATA_DIR / "sharp").mkdir(parents=True, exist_ok=True)
    
    # API
    (INPUT_DATA_DIR / "api").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "api" / "dune").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "api" / "dune" / "query-configs").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "api" / "gmgn").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "api" / "gmgn" / "token-lists").mkdir(parents=True, exist_ok=True)
    
    # Proxies
    (INPUT_DATA_DIR / "proxies").mkdir(parents=True, exist_ok=True)
    
    # Solana modules
    (OUTPUT_DATA_DIR / "solana").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "transaction-data").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "wallet-data").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "telegram").mkdir(parents=True, exist_ok=True)
    
    # Dragon module for Solana
    (OUTPUT_DATA_DIR / "solana" / "dragon").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "dragon" / "wallet-analysis").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "dragon" / "top-traders").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "dragon" / "top-holders").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "dragon" / "early-buyers").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "solana" / "dragon" / "token-info").mkdir(parents=True, exist_ok=True)
    
    # Ethereum modules
    (OUTPUT_DATA_DIR / "ethereum").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "ethereum" / "transaction-data").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "ethereum" / "wallet-data").mkdir(parents=True, exist_ok=True)
    
    # Dragon module for Ethereum
    (OUTPUT_DATA_DIR / "ethereum" / "dragon").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "ethereum" / "dragon" / "wallet-analysis").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "ethereum" / "dragon" / "top-traders").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "ethereum" / "dragon" / "top-holders").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "ethereum" / "dragon" / "early-buyers").mkdir(parents=True, exist_ok=True)
    
    # Sharp Tools modules
    (OUTPUT_DATA_DIR / "sharp-tools").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "sharp-tools" / "wallets").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "sharp-tools" / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "sharp-tools" / "csv" / "merged").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "sharp-tools" / "csv" / "unmerged").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "sharp-tools" / "csv" / "filtered").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "sharp-tools" / "csv" / "unfiltered").mkdir(parents=True, exist_ok=True)
    
    # API modules
    (OUTPUT_DATA_DIR / "api").mkdir(parents=True, exist_ok=True)
    
    # API - Dune Analytics
    (OUTPUT_DATA_DIR / "api" / "dune").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "api" / "dune" / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "api" / "dune" / "parsed").mkdir(parents=True, exist_ok=True)
    
    # API - GMGN
    (OUTPUT_DATA_DIR / "api" / "gmgn").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "api" / "gmgn" / "token-listings").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "api" / "gmgn" / "market-cap-data").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATA_DIR / "api" / "gmgn" / "token-info").mkdir(parents=True, exist_ok=True)
    
    # Check if dragon directory exists in output-data and remove it
    import shutil
    if (OUTPUT_DATA_DIR / "dragon").exists():
        shutil.rmtree(OUTPUT_DATA_DIR / "dragon")
    
    # Import ensure_file_dir from utils
    from ..utils.common import ensure_file_dir
    
    # Ensure placeholder files exist
    placeholder_files = [
        (INPUT_DATA_DIR / "ethereum" / "wallets" / "wallets.txt"),
        (INPUT_DATA_DIR / "solana" / "wallets" / "wallets.txt"),
        (INPUT_DATA_DIR / "proxies" / "proxies.txt"),
        (INPUT_DATA_DIR / "api" / "gmgn" / "token-lists" / "token_addresses.txt"),
        (INPUT_DATA_DIR / "solana" / "token-lists" / "tokens.txt")
    ]
    
    # Remove old dragon directory if it exists
    import shutil
    if (INPUT_DATA_DIR / "dragon").exists():
        shutil.rmtree(INPUT_DATA_DIR / "dragon")
    
    for file_path in placeholder_files:
        if not file_path.exists():
            # Ensure parent directory exists before creating file
            ensure_file_dir(file_path)
            file_path.touch()
    
    # Load environment variables
    env_file = os.environ.get('SOL_TOOLS_ENV_FILE', str(ENV_FILE))
    if Path(env_file).exists():
        # Use override=True to ensure .env variables override existing environment variables
        load_dotenv(env_file, override=True)
    else:
        print(f"Warning: Environment file not found at {env_file}")
    
    # Load or create main config file
    if MAIN_CONFIG.exists():
        with open(MAIN_CONFIG, "r") as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Ensure parent directory exists
        MAIN_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        with open(MAIN_CONFIG, "w") as f:
            json.dump(config, indent=2, fp=f)
    
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to main config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure parent directory exists
    MAIN_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(MAIN_CONFIG, "w") as f:
        json.dump(config, indent=2, fp=f)


def get_env_var(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default value."""
    return os.getenv(var_name, default)


def check_env_vars(module: str) -> Dict[str, bool]:
    """Check if required environment variables are set for a module."""
    results = {}
    for var in REQUIRED_ENV_VARS.get(module, []):
        # Improved check: ensure variable exists AND is not empty
        value = os.environ.get(var, '')
        results[var] = bool(value and value.strip() != '')
    return results


def edit_env_variables() -> None:
    """Interactive menu to edit environment variables."""
    console = Console()
    
    # Load existing .env file if it exists
    env_vars = {}
    env_comments = []
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip():
                    if line.startswith("#"):
                        env_comments.append(line.strip())
                    elif "=" in line:
                        key, value = line.strip().split("=", 1)
                        env_vars[key] = value
    
    # Sort environment variables by module
    organized_vars = {
        "Dragon": [],
        "Dune": [],
        "Solana": [],
        "Ethereum": [],
        "GMGN": [],
        "Telegram": [],
        "BullX": [],
        "Sharp": [],
        "Other": []
    }
    
    # Add any vars that aren't in our organized categories to "Other"
    for var in env_vars:
        if var in REQUIRED_ENV_VARS.get("dragon", []):
            organized_vars["Dragon"].append(var)
        elif var in REQUIRED_ENV_VARS.get("dune", []):
            organized_vars["Dune"].append(var)
        elif var in REQUIRED_ENV_VARS.get("solana", []):
            organized_vars["Solana"].append(var)
        elif var in REQUIRED_ENV_VARS.get("ethereum", []):
            organized_vars["Ethereum"].append(var)
        elif var in REQUIRED_ENV_VARS.get("gmgn", []):
            organized_vars["GMGN"].append(var)
        elif var in REQUIRED_ENV_VARS.get("telegram", []):
            organized_vars["Telegram"].append(var)
        elif var in REQUIRED_ENV_VARS.get("bullx", []):
            organized_vars["BullX"].append(var)
        elif var in REQUIRED_ENV_VARS.get("sharp", []):
            organized_vars["Sharp"].append(var)
        else:
            organized_vars["Other"].append(var)
    
    # Add missing required vars to their categories
    for module, vars_list in REQUIRED_ENV_VARS.items():
        for var in vars_list:
            if var not in env_vars:
                env_vars[var] = ""
                if module == "dragon":
                    organized_vars["Dragon"].append(var)
                elif module == "dune":
                    organized_vars["Dune"].append(var)
                elif module == "solana":
                    organized_vars["Solana"].append(var)
                elif module == "ethereum":
                    organized_vars["Ethereum"].append(var)
                elif module == "gmgn":
                    organized_vars["GMGN"].append(var)
                elif module == "telegram":
                    organized_vars["Telegram"].append(var)
                elif module == "bullx":
                    organized_vars["BullX"].append(var)
                elif module == "sharp":
                    organized_vars["Sharp"].append(var)
    
    # Function to get a censored view of a value
    def get_censored_value(value, length=20):
        if not value:
            return ""
        if len(value) <= 8:
            return "********"
        
        # For longer values, show first 4 and last 4 characters
        return f"{value[:4]}{'*' * min(12, len(value) - 8)}{value[-4:]}"
    
    # Track if any changes were made
    changes_made = False
    
    # First, choose a category
    while True:
        category_choices = []
        for category, vars_list in organized_vars.items():
            if vars_list:  # Only show categories with variables
                category_choices.append(category)
        category_choices.append("⬅️ Back")
        
        questions = [
            inquirer.List(
                "category",
                message="Select environment variable category",
                choices=category_choices,
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            # User cancelled with Ctrl+C
            break
            
        selected_category = answers["category"]
        
        if selected_category == "⬅️ Back":
            break
        
        # Then choose a variable within that category
        while True:
            var_choices = []
            for var in organized_vars[selected_category]:
                # Add a check mark for variables that already have values
                if env_vars.get(var, ""):
                    var_choices.append(f"{var} ✅")
                else:
                    var_choices.append(var)
            var_choices.append("⬅️ Back")
            
            questions = [
                inquirer.List(
                    "variable",
                    message=f"Select {selected_category} environment variable to edit",
                    choices=var_choices,
                ),
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                # User cancelled with Ctrl+C
                break
                
            selected = answers["variable"]
            
            if selected == "⬅️ Back":
                break
            
            # Remove the emoji if present
            if " ✅" in selected:
                selected = selected.replace(" ✅", "")
                
            # Get current value and prompt for new value
            current_value = env_vars.get(selected, "")
            is_sensitive = "KEY" in selected or "TOKEN" in selected or "SECRET" in selected
            
            # If there's an existing value, show a censored version
            if current_value:
                censored_value = get_censored_value(current_value) if is_sensitive else current_value
                console.print(f"[yellow]Current value: {censored_value}[/yellow]")
            
            # For sensitive values like API keys, don't show as default
            if is_sensitive:
                default_value = ""
                placeholder = "(Enter new value)"
            else:
                default_value = current_value
                placeholder = "(Enter new value)"
            
            questions2 = [
                inquirer.Text(
                    "value",
                    message=f"Enter value for {selected}",
                    default=placeholder if not default_value else default_value
                ),
            ]
            value_answer = safe_prompt(questions2)
            if not value_answer:
                # User cancelled with Ctrl+C
                break
                
            new_value = value_answer["value"]
            
            # Check if they entered the placeholder text by mistake
            if new_value == placeholder:
                new_value = ""
            
            # If clearing an existing value, confirm this explicitly
            if current_value and not new_value:
                clear_confirm = [
                    inquirer.Confirm(
                        "confirm_clear",
                        message=f"Are you sure you want to CLEAR the value for {selected}?",
                        default=False  # Default to No for safety
                    ),
                ]
                clear_answer = inquirer.prompt(clear_confirm)
                if not clear_answer or not clear_answer["confirm_clear"]:
                    console.print("[yellow]No changes made.[/yellow]")
                    continue
            # If current value exists and new value is different, confirm overwrite
            elif current_value and new_value and new_value != current_value:
                confirm_questions = [
                    inquirer.Confirm(
                        "confirm",
                        message=f"Overwrite existing value for {selected}?",
                        default=True
                    ),
                ]
                confirm = inquirer.prompt(confirm_questions)
                if not confirm:
                    # User cancelled with Ctrl+C
                    break
                    
                if not confirm["confirm"]:
                    console.print("[yellow]No changes made.[/yellow]")
                    continue
            
            # Update the value if changed
            if new_value != current_value:
                env_vars[selected] = new_value
                changes_made = True
                
                # Show success message
                if new_value:
                    censored_new = get_censored_value(new_value) if is_sensitive else new_value
                    console.print(f"[green]✓ Set {selected} to {censored_new}[/green]")
                else:
                    console.print(f"[yellow]⚠ Cleared {selected}[/yellow]")
                
                # Save immediately after each change
                try:
                    save_env_file(env_vars, env_comments)
                except Exception as e:
                    console.print(f"[red]Error saving environment variables: {e}[/red]")
    
    # Only show final success message if changes were made
    if changes_made:
        console.print("\n[green]✓ Environment variables saved successfully![/green]")
        
        try:
            # Reload dotenv with override=True to ensure changes take effect immediately
            from dotenv import load_dotenv as reload_dotenv
            reload_dotenv(ENV_FILE, override=True)
            
            # Also update the current process environment variables
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
                        
            console.print("[green]✓ Configuration has been reloaded.[/green]")
        except Exception as e:
            console.print(f"[red]Error reloading environment variables: {e}[/red]")


def save_env_file(env_vars, comments=None):
    """
    Save environment variables to .env file.
    
    Args:
        env_vars: Dictionary of environment variables
        comments: List of comment lines to preserve
    """
    # Ensure parent directory exists
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ENV_FILE, "w") as f:
        # Write comments first if provided
        if comments:
            for comment in comments:
                f.write(f"{comment}\n")
            
            # Add a blank line after comments
            if comments and env_vars:
                f.write("\n")
        
        # Write environment variables
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")