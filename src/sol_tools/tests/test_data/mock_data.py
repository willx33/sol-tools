"""
Mock data utilities for testing Sol Tools.

This module provides functions to generate mock data for various blockchain protocols,
APIs, and other services used in Sol Tools.
"""

import json
import random
import string
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

def random_string(length: int = 10) -> str:
    """Generate a random string of characters."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_address(eth: bool = False) -> str:
    """
    Generate a random blockchain address.
    
    Args:
        eth: If True, generate an Ethereum address, otherwise Solana
        
    Returns:
        A random address string
    """
    if eth:
        # Ethereum address format: 0x + 40 hex chars
        return "0x" + ''.join(random.choices(string.hexdigits.lower(), k=40))
    else:
        # Solana address format: Base58 string, typically 32-44 chars
        base58_chars = string.ascii_letters + string.digits
        base58_chars = base58_chars.replace('0', '').replace('O', '').replace('I', '').replace('l', '')
        return ''.join(random.choices(base58_chars, k=random.randint(32, 44)))

def random_token_amount(min_value: float = 0.0001, max_value: float = 1000.0) -> float:
    """Generate a random token amount."""
    return round(random.uniform(min_value, max_value), random.randint(2, 8))

def random_timestamp(
    start_date: datetime.datetime = datetime.datetime(2020, 1, 1),
    end_date: datetime.datetime = datetime.datetime.now()
) -> int:
    """Generate a random Unix timestamp within the given range."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 24 * 60 * 60)
    random_date = start_date + datetime.timedelta(days=random_days, seconds=random_seconds)
    return int(random_date.timestamp())

def random_transaction_hash(eth: bool = False) -> str:
    """Generate a random transaction hash."""
    if eth:
        # Ethereum transaction hash: 0x + 64 hex chars
        return "0x" + ''.join(random.choices(string.hexdigits.lower(), k=64))
    else:
        # Solana transaction signature: Base58 string, 88 chars
        base58_chars = string.ascii_letters + string.digits
        base58_chars = base58_chars.replace('0', '').replace('O', '').replace('I', '').replace('l', '')
        return ''.join(random.choices(base58_chars, k=88))

def random_wallet_with_tokens(eth: bool = False, token_count: int = 3) -> Dict[str, Any]:
    """
    Generate a random wallet with token balances.
    
    Args:
        eth: If True, generate Ethereum data, otherwise Solana
        token_count: Number of tokens to include
        
    Returns:
        A dictionary representing a wallet
    """
    wallet = {
        "address": random_address(eth),
        "last_updated": random_timestamp(),
        "tokens": []
    }
    
    for _ in range(token_count):
        token = {
            "symbol": random_string(3).upper(),
            "name": f"{random_string(6).capitalize()} Token",
            "balance": random_token_amount(),
            "price_usd": random_token_amount(0.01, 2000.0),
            "value_usd": 0,  # Will be calculated
        }
        token["value_usd"] = round(token["balance"] * token["price_usd"], 2)
        wallet["tokens"].append(token)
    
    # Add total value
    wallet["total_value_usd"] = sum(token["value_usd"] for token in wallet["tokens"])
    
    return wallet

def random_transaction(eth: bool = False) -> Dict[str, Any]:
    """
    Generate a random transaction.
    
    Args:
        eth: If True, generate Ethereum data, otherwise Solana
        
    Returns:
        A dictionary representing a transaction
    """
    tx_types = ["transfer", "swap", "stake", "unstake", "liquidity", "mint", "burn"]
    tx_type = random.choice(tx_types)
    
    if eth:
        # Ethereum transaction
        transaction = {
            "hash": random_transaction_hash(True),
            "blockNumber": random.randint(10000000, 20000000),
            "from": random_address(True),
            "to": random_address(True),
            "value": str(random.randint(0, 10**18)),  # in wei
            "gasPrice": str(random.randint(1, 200) * 10**9),  # in wei
            "gas": str(random.randint(21000, 300000)),
            "timestamp": random_timestamp(),
            "type": tx_type
        }
    else:
        # Solana transaction
        transaction = {
            "signature": random_transaction_hash(False),
            "slot": random.randint(100000000, 200000000),
            "fee": random.randint(5000, 10000),
            "timestamp": random_timestamp(),
            "type": tx_type,
            "source": random_address(False),
            "destination": random_address(False),
            "amount": random_token_amount()
        }
    
    return transaction

def generate_solana_wallet_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of Solana wallets."""
    return [random_wallet_with_tokens(False) for _ in range(count)]

def generate_ethereum_wallet_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of Ethereum wallets."""
    return [random_wallet_with_tokens(True) for _ in range(count)]

def generate_solana_transaction_list(count: int = 10) -> List[Dict[str, Any]]:
    """Generate a list of Solana transactions."""
    return [random_transaction(False) for _ in range(count)]

def generate_ethereum_transaction_list(count: int = 10) -> List[Dict[str, Any]]:
    """Generate a list of Ethereum transactions."""
    return [random_transaction(True) for _ in range(count)]

def generate_mock_dune_query_result() -> Dict[str, Any]:
    """Generate a mock Dune Analytics query result."""
    # Generate random column names
    columns = [f"column_{i}" for i in range(random.randint(3, 6))]
    
    # Generate random data
    data = []
    for _ in range(random.randint(5, 15)):
        row = {}
        for column in columns:
            # Mix of different data types
            data_type = random.choice(["number", "string", "address"])
            if data_type == "number":
                row[column] = random.uniform(0, 10000)
            elif data_type == "string":
                row[column] = random_string(random.randint(5, 10))
            else:
                row[column] = random_address(True)
        data.append(row)
    
    return {
        "execution_id": random.randint(1000000, 9999999),
        "query_id": random.randint(100000, 999999),
        "columns": columns,
        "data": data,
        "error": None,
        "status": "success"
    }

def generate_mock_sharp_portfolio() -> Dict[str, Any]:
    """Generate mock Sharp portfolio data."""
    coins = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "UNI", "AAVE", "COMP", "MKR", "SNX"]
    protocols = ["Uniswap", "Aave", "Compound", "MakerDAO", "Lido", "Curve", "Balancer"]
    
    # Generate random allocation
    allocation = []
    total_allocation = 100.0
    remaining = total_allocation
    
    for i in range(len(coins) - 1):
        if remaining <= 0:
            break
        value = round(random.uniform(0, remaining), 2)
        allocation.append({
            "coin": coins[i],
            "percentage": value
        })
        remaining -= value
    
    # Add the remaining to the last coin
    if remaining > 0:
        allocation.append({
            "coin": coins[-1],
            "percentage": round(remaining, 2)
        })
    
    # Generate protocol allocation
    protocol_allocation = []
    remaining = total_allocation
    
    for i in range(len(protocols) - 1):
        if remaining <= 0:
            break
        value = round(random.uniform(0, remaining), 2)
        protocol_allocation.append({
            "protocol": protocols[i],
            "percentage": value
        })
        remaining -= value
    
    # Add the remaining to the last protocol
    if remaining > 0:
        protocol_allocation.append({
            "protocol": protocols[-1],
            "percentage": round(remaining, 2)
        })
    
    return {
        "walletId": random_string(10),
        "totalValueUsd": round(random.uniform(10000, 1000000), 2),
        "realizedPnlUsd": round(random.uniform(-10000, 50000), 2),
        "unrealizedPnlUsd": round(random.uniform(-10000, 50000), 2),
        "allocation": allocation,
        "protocolAllocation": protocol_allocation,
        "lastUpdated": random_timestamp()
    }

def generate_mock_gmgn_data() -> Dict[str, Any]:
    """Generate mock GMGN token data."""
    return {
        "token": {
            "name": "GMGN",
            "symbol": "GMGN",
            "address": "4e8rF4Q5s8AmTacxvfVMKJtQKMjM2ZfbCGnzAEjRGKTZ",
            "decimals": 9,
            "coingecko_id": "magiceden"
        },
        "price": {
            "usd": round(random.uniform(0.5, 5.0), 6),
            "usd_24h_change": round(random.uniform(-15.0, 15.0), 2),
            "usd_market_cap": round(random.uniform(10000000, 100000000), 2)
        },
        "supply": {
            "circulating": round(random.uniform(10000000, 50000000), 0),
            "total": 100000000
        },
        "history": [
            {
                "date": (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d"),
                "price_usd": round(random.uniform(0.5, 5.0), 6),
                "volume_usd": round(random.uniform(100000, 10000000), 2)
            }
            for i in range(30)
        ]
    }

def create_mock_data_files(base_path: Path) -> Dict[str, Path]:
    """
    Create mock data files in the specified directory.
    
    Args:
        base_path: Base path to create mock data files
        
    Returns:
        Dictionary mapping file descriptions to their paths
    """
    # Ensure directories exist
    (base_path / "solana").mkdir(parents=True, exist_ok=True)
    (base_path / "ethereum").mkdir(parents=True, exist_ok=True)
    (base_path / "dune").mkdir(parents=True, exist_ok=True)
    (base_path / "sharp").mkdir(parents=True, exist_ok=True)
    (base_path / "dragon").mkdir(parents=True, exist_ok=True)
    (base_path / "gmgn").mkdir(parents=True, exist_ok=True)
    
    # Create mock data files
    files = {}
    
    # Solana mock data
    solana_wallets = generate_solana_wallet_list(10)
    solana_txs = generate_solana_transaction_list(20)
    
    files["solana_wallets"] = base_path / "solana" / "wallets.json"
    files["solana_transactions"] = base_path / "solana" / "transactions.json"
    
    with open(files["solana_wallets"], "w") as f:
        json.dump(solana_wallets, f, indent=2)
    
    with open(files["solana_transactions"], "w") as f:
        json.dump(solana_txs, f, indent=2)
    
    # Ethereum mock data
    eth_wallets = generate_ethereum_wallet_list(10)
    eth_txs = generate_ethereum_transaction_list(20)
    
    files["ethereum_wallets"] = base_path / "ethereum" / "wallets.json"
    files["ethereum_transactions"] = base_path / "ethereum" / "transactions.json"
    
    with open(files["ethereum_wallets"], "w") as f:
        json.dump(eth_wallets, f, indent=2)
    
    with open(files["ethereum_transactions"], "w") as f:
        json.dump(eth_txs, f, indent=2)
    
    # Dune mock data
    dune_results = generate_mock_dune_query_result()
    files["dune_query_result"] = base_path / "dune" / "query_result.json"
    
    with open(files["dune_query_result"], "w") as f:
        json.dump(dune_results, f, indent=2)
    
    # Sharp mock data
    sharp_portfolio = generate_mock_sharp_portfolio()
    files["sharp_portfolio"] = base_path / "sharp" / "portfolio.json"
    
    with open(files["sharp_portfolio"], "w") as f:
        json.dump(sharp_portfolio, f, indent=2)
    
    # GMGN mock data
    gmgn_data = generate_mock_gmgn_data()
    files["gmgn_data"] = base_path / "gmgn" / "token_data.json"
    
    with open(files["gmgn_data"], "w") as f:
        json.dump(gmgn_data, f, indent=2)
    
    # Bundle data for Dragon module
    files["dragon_data_dir"] = base_path / "dragon"
    
    # Copy some wallet data to the dragon directory
    dragon_solana_wallets = base_path / "dragon" / "solana_wallets.json"
    dragon_ethereum_wallets = base_path / "dragon" / "ethereum_wallets.json"
    
    with open(dragon_solana_wallets, "w") as f:
        json.dump(solana_wallets[:5], f, indent=2)
    
    with open(dragon_ethereum_wallets, "w") as f:
        json.dump(eth_wallets[:5], f, indent=2)
    
    return files 