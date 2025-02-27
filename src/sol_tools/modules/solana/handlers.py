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

from ...utils.common import clear_terminal, ensure_data_dir
from ...core.config import check_env_vars, get_env_var
from .solana_adapter import SolanaAdapter


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
    
    # Input for token address
    questions = [
        inquirer.Text(
            "token_address",
            message="Enter Solana token address to monitor",
            validate=lambda _, x: len(x) == 44 if x else False
        ),
        inquirer.Text(
            "min_amount",
            message="Minimum transaction amount to alert (in USD)",
            default="1000"
        ),
    ]
    answers = inquirer.prompt(questions)
    
    token_address = answers["token_address"]
    try:
        min_amount = float(answers["min_amount"])
    except ValueError:
        print(f"⚠️ Invalid minimum amount, using default: 1000 USD")
        min_amount = 1000
    
    # Initialize Solana adapter
    data_dir = ensure_data_dir("").parent
    adapter = SolanaAdapter(data_dir)
    
    # Start monitoring
    print(f"\n🔎 Monitoring transactions for token: {token_address}")
    print(f"🔔 Will alert for transactions >= ${min_amount:.2f}")
    print("\nPress Ctrl+C to stop monitoring...\n")
    
    try:
        # Use the adapter to monitor the token
        result = adapter.token_monitor(token_address, min_amount)
        
        if result.get("success", False):
            events = result.get("events", [])
            for event in events:
                print(f"⚡ New transaction detected: ${event['amount']:.2f} at {event['timestamp']}")
            
            print(f"\n✅ Monitoring complete. Detected {len(events)} transactions above threshold.")
        else:
            print(f"\n❌ Monitoring failed: {result.get('error', 'Unknown error')}")
        
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
    
    # Choose wallets to monitor
    wallet_file = wallet_dir / "monitor-wallets.txt"
    
    if os.path.exists(wallet_file):
        with open(wallet_file, "r") as f:
            existing_wallets = [line.strip() for line in f if line.strip()]
        
        if existing_wallets:
            print(f"ℹ️ Found {len(existing_wallets)} wallets in existing file:")
            for i, wallet in enumerate(existing_wallets[:5], 1):
                print(f"  {i}. {wallet}")
            if len(existing_wallets) > 5:
                print(f"  ... and {len(existing_wallets) - 5} more")
            
            questions = [
                inquirer.Confirm(
                    "use_existing",
                    message="Use these existing wallets?",
                    default=True
                ),
            ]
            answers = inquirer.prompt(questions)
            
            if answers["use_existing"]:
                wallets = existing_wallets
            else:
                wallets = []
        else:
            wallets = []
    else:
        wallets = []
    
    # If no wallets from file or user chose not to use them
    if not wallets:
        wallets = []
        print("\nEnter wallet addresses to monitor (one per line, empty line to finish):")
        while True:
            wallet = input("> ").strip()
            if not wallet:
                break
            if len(wallet) == 44:
                wallets.append(wallet)
            else:
                print("❌ Invalid Solana wallet address (should be 44 characters)")
        
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