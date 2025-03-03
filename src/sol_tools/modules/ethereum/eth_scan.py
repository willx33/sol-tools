"""
Standalone implementation of Ethereum Scanner functionality.
This module can be imported directly without dependencies on other modules.
"""

import random
import tls_client
import cloudscraper
from fake_useragent import UserAgent
import concurrent.futures
import time
import os
import sys
from pathlib import Path
import json
from typing import List, Union

ua = UserAgent(os='linux', browsers=['firefox'])

class Config:
    """Configuration for Ethereum API calls."""
    # API settings
    ETH_API_KEY = os.environ.get("ETHEREUM_API_KEY", "")
    ETH_ENDPOINT = "https://api.etherscan.io/api"
    
    # Request settings
    REQUEST_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY_MIN = 1.0  # seconds
    RETRY_DELAY_MAX = 3.0  # seconds
    
    # Thread settings
    DEFAULT_THREADS = 10
    
    # Rate limiting
    RATE_LIMIT_DELAY = 0.2  # seconds between API calls
    
    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory."""
        if 'sol_tools' in sys.modules:
            from ...core.config import ROOT_DIR
            return ROOT_DIR
        else:
            current_dir = Path(__file__).resolve().parent
            for _ in range(10):
                if (current_dir / ".git").exists() or (current_dir / "pyproject.toml").exists():
                    return current_dir
                if current_dir.parent == current_dir:
                    break
                current_dir = current_dir.parent
            return Path.home() / "sol-tools"
    
    @staticmethod
    def get_output_dir() -> Path:
        """Get the output directory for Ethereum scans."""
        if 'sol_tools' in sys.modules:
            from ...core.config import OUTPUT_DATA_DIR
            return OUTPUT_DATA_DIR / "ethereum" / "scan-txns"
        else:
            root = Config.get_project_root()
            return root / "data" / "output-data" / "ethereum" / "scan-txns"
    
    @staticmethod
    def ensure_dir_exists(directory: Path) -> Path:
        """Ensure a directory exists and return its path."""
        directory.mkdir(parents=True, exist_ok=True)
        return directory

def import_addresses_from_file(file_path: Union[str, Path]) -> List[str]:
    """Import Ethereum addresses from a file."""
    addresses = []
    path = Path(file_path)
    
    if not path.exists():
        print(f"Address file not found: {path}")
        return addresses
    
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                addresses.append(line)
        return addresses
    except Exception as e:
        print(f"Error reading address file {path}: {e}")
        return []

class EthScanAllTx:
    """Ethereum Transaction Scanner class."""
    
    def __init__(self, addresses=None, output_dir=None, test_mode=False):
        """Initialize the scanner with addresses and output directory."""
        self.addresses = addresses or []
        self.output_dir = Path(output_dir) if output_dir else Config.get_output_dir()
        self.test_mode = test_mode
        self.scanner = EthScan()
    
    def run(self) -> bool:
        """Run the transaction scanner and save results."""
        if not self.addresses:
            if not self.test_mode:
                print("No addresses provided!")
            return False
        
        Config.ensure_dir_exists(self.output_dir)
        
        for address in self.addresses:
            result = self.scanner.run(address)
            if not result:
                return False
        
        return True

class EthScan:
    def __init__(self):
        self.sendRequest = tls_client.Session(client_identifier='chrome_103')
        self.cloudScraper = cloudscraper.create_scraper()
        self.shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else s

    def fetch_url(self, url, headers):
        retries = 3
        for attempt in range(retries):
            try:
                response = self.sendRequest.get(url, headers=headers).json()
                return response
            except Exception:
                print(f"[🐲] Error fetching data, trying backup...")
            finally:
                try:
                    response = self.cloudScraper.get(url, headers=headers).json()
                    return response
                except Exception:
                    print(f"[🐲] Backup scraper failed, retrying...")
            
            time.sleep(1)
        
        print(f"[🐲] Failed to fetch data after {retries} attempts.")
        return {}

    def scanAllTx(self, contractAddress, threads=10):
        base_url = f"https://gmgn.ai/defi/quotation/v1/trades/eth/{contractAddress}?limit=100"
        paginator = None
        urls = []
        all_trades = []

        headers = {
            "User-Agent": ua.random
        }
        
        print(f"[🐲] Starting... please wait.")

        while True:
            url = f"{base_url}&cursor={paginator}" if paginator else base_url
            urls.append(url)
            
            response = self.fetch_url(url, headers)
            trades = response.get('data', {}).get('history', [])
            
            if not trades:
                break

            paginator = response['data'].get('next')
            if not paginator:
                break
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.fetch_url, url, headers): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                response = future.result()
                trades = response.get('data', {}).get('history', [])
                all_trades.extend(trades)

        wallets = []
        
        # Use our project's data structure
        output_dir = Path(os.getcwd()) / "data" / "output-data" / "ethereum" / "scan-txns"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = output_dir / f"txns_{self.shorten(contractAddress)}__{random.randint(1111, 9999)}.txt"
        json_filename = output_dir / f"txns_{self.shorten(contractAddress)}__{random.randint(1111, 9999)}.json"

        for trade in all_trades:
            wallets.append(trade.get("maker"))

        with open(filename, 'a') as f:
            for wallet in wallets:
                f.write(f"{wallet}\n")
                
        with open(json_filename, 'w') as f:
            json.dump(all_trades, f, indent=2)
        
        print(f"[🐲] {len(wallets)} trades successfully saved to {filename}")
        print(f"[🐲] Full trade data saved to {json_filename}")
        return True

    def run(self, contract_address: str, threads: int = 10) -> bool:
        """Run the transaction scanner."""
        if not contract_address:
            print("No contract address provided!")
            return False
            
        return self.scanAllTx(contract_address, threads) 