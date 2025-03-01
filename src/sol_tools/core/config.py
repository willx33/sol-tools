"""Configuration management for Sol Tools."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import inquirer
from dotenv import load_dotenv, set_key

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
        "SOLSCAN_API_KEY", 
        "ETHERSCAN_API_KEY"
    ],
    "dune": [
        "DUNE_API_KEY"
    ],
    "solana": [
        "HELIUS_API_KEY", 
        "SOLANA_RPC_URL", 
        "SOLANA_WEBSOCKET_URL"
    ],
    "ethereum": [
        "ETHEREUM_RPC_URL", 
        "ETHERSCAN_API_KEY"
    ],
    "gmgn": [
        "PUMPFUN_API_KEY", 
        "MOONSHOT_API_KEY"
    ],
    "telegram": [
        "TELEGRAM_BOT_TOKEN", 
        "TELEGRAM_CHAT_ID"
    ],
    "bullx": [
        "BULLX_API_KEY"
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
    (INPUT_DATA_DIR / "solana" / "wallet-lists").mkdir(parents=True, exist_ok=True)
    
    # Ethereum
    (INPUT_DATA_DIR / "ethereum").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "ethereum" / "token-lists").mkdir(parents=True, exist_ok=True)
    (INPUT_DATA_DIR / "ethereum" / "wallet-lists").mkdir(parents=True, exist_ok=True)
    
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
        (INPUT_DATA_DIR / "ethereum" / "wallet-lists" / "wallets.txt"),
        (INPUT_DATA_DIR / "solana" / "wallet-lists" / "wallets.txt"),
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
    load_dotenv(ENV_FILE)
    
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
        results[var] = bool(os.getenv(var))
    return results


def edit_env_variables() -> None:
    """Interactive menu to edit environment variables."""
    # Load existing .env file if it exists
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    if "=" in line:
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
        selected_category = answers["category"]
        
        if selected_category == "⬅️ Back":
            break
        
        # Then choose a variable within that category
        while True:
            var_choices = organized_vars[selected_category] + ["⬅️ Back"]
            questions = [
                inquirer.List(
                    "variable",
                    message=f"Select {selected_category} environment variable to edit",
                    choices=var_choices,
                ),
            ]
            
            answers = inquirer.prompt(questions)
            selected = answers["variable"]
            
            if selected == "⬅️ Back":
                break
            
            # Get current value and prompt for new value
            current_value = env_vars.get(selected, "")
            masked_value = "********" if current_value and ("KEY" in selected or "TOKEN" in selected) else current_value
            
            questions2 = [
                inquirer.Text(
                    "value",
                    message=f"Enter value for {selected}",
                    default=masked_value
                ),
            ]
            value_answer = inquirer.prompt(questions2)
            
            # Only update if user changed the value
            if value_answer["value"] != masked_value:
                env_vars[selected] = value_answer["value"]
    
    # Save .env file
    # Ensure parent directory exists
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_FILE, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    # Reload environment variables
    load_dotenv(ENV_FILE)