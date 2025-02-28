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
CACHE_DIR = ROOT_DIR / "cache"
LOG_DIR = ROOT_DIR / "logs"

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
    "proxy_file": str(DATA_DIR / "proxies.txt"),
    "data_dir": str(DATA_DIR),
    "input_data_dir": str(INPUT_DATA_DIR),
    "output_data_dir": str(OUTPUT_DATA_DIR),
    "log_dir": str(LOG_DIR),
    "cache_dir": str(CACHE_DIR),
    "theme": "dark"
}


def load_config() -> Dict[str, Any]:
    """Load configuration from files and environment variables."""
    # Create directories if they don't exist
    for directory in [DATA_DIR, CONFIG_DIR, CACHE_DIR, LOG_DIR, INPUT_DATA_DIR, OUTPUT_DATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # List of all modules
    modules = ["dragon", "dune", "sharp", "solana", "gmgn", "ethereum"]
    
    # Create data module directories with new organized structure
    for module in modules:
        (INPUT_DATA_DIR / module).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DATA_DIR / module).mkdir(parents=True, exist_ok=True)
        
    # Remove any leftover legacy directories
    for module in modules:
        legacy_dir = DATA_DIR / module
        if legacy_dir.exists():
            import shutil
            try:
                # Just in case there's any data left, move it to output
                output_dir = OUTPUT_DATA_DIR / module
                
                # This is commented out because we don't need it anymore
                # for item in legacy_dir.glob("*"):
                #     if item.is_file():
                #         shutil.copy2(item, output_dir / item.name) 
                #     elif item.is_dir():
                #         shutil.copytree(item, output_dir / item.name, dirs_exist_ok=True)
                
                # Remove the legacy directory
                shutil.rmtree(legacy_dir)
            except Exception as e:
                print(f"Warning: Could not remove legacy directory {legacy_dir}: {e}")
    
    # Load environment variables
    load_dotenv(ENV_FILE)
    
    # Load or create main config file
    if MAIN_CONFIG.exists():
        with open(MAIN_CONFIG, "r") as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(MAIN_CONFIG, "w") as f:
            json.dump(config, indent=2, fp=f)
    
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to main config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
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
    with open(ENV_FILE, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    # Reload environment variables
    load_dotenv(ENV_FILE)