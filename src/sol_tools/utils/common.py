"""Common utility functions used across modules."""

import os
import shutil
import requests
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..core.config import get_env_var, ROOT_DIR, DATA_DIR, CACHE_DIR


def clear_terminal():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def clear_cache():
    """Clear all cached data files."""
    try:
        # Clear cache directory
        if os.path.exists(CACHE_DIR):
            for file in os.listdir(CACHE_DIR):
                file_path = os.path.join(CACHE_DIR, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            print(f"✅ Successfully cleared cache directory: {CACHE_DIR}")
        else:
            print(f"ℹ️ Cache directory does not exist: {CACHE_DIR}")
            
        # Create cache directory if it doesn't exist
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")


def test_telegram():
    """Send a test message to the Telegram bot."""
    telegram_bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = get_env_var("TELEGRAM_CHAT_ID")
    
    if not telegram_bot_token or not telegram_chat_id:
        print("❌ Telegram is not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file.")
        return
    
    try:
        message = "🤖 Sol Tools - Test message from CLI"
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        
        response = requests.post(url, json={
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "HTML"
        })
        
        if response.status_code == 200:
            print(f"✅ Test message sent successfully to Telegram chat ID: {telegram_chat_id}")
        else:
            print(f"❌ Failed to send message to Telegram: {response.text}")
            
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")


def ensure_data_dir(module: str, subdir: Optional[str] = None) -> Path:
    """
    Ensure that a data directory exists for a module and return its path.
    
    Args:
        module: The module name (dragon, dune, sharp, solana)
        subdir: Optional subdirectory within the module
        
    Returns:
        Path object to the directory
    """
    if subdir:
        directory = DATA_DIR / module / subdir
    else:
        directory = DATA_DIR / module
        
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def check_proxy_file(proxy_path: Optional[str] = None) -> List[str]:
    """
    Check if proxy file exists and get proxies.
    
    Args:
        proxy_path: Optional path to proxy file, defaults to data/proxies.txt
        
    Returns:
        List of proxy strings or empty list if no proxies
    """
    if proxy_path is None:
        proxy_path = DATA_DIR / "proxies.txt"
        
    try:
        if os.path.exists(proxy_path):
            with open(proxy_path, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            return proxies
        else:
            print(f"⚠️ Proxy file not found at {proxy_path}")
            return []
    except Exception as e:
        print(f"❌ Error reading proxy file: {e}")
        return []