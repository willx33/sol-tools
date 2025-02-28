"""Adapter for Sharp wallet utilities and CSV processing."""

import os
import csv
import json
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

class SharpAdapter:
    """Adapter for Sharp wallet utilities."""
    
    def __init__(self, data_dir: Union[str, Path]):
        """
        Initialize the Sharp adapter.
        
        Args:
            data_dir: Path to the data directory
        """
        self.data_dir = Path(data_dir)
        self.sharp_dir = self.data_dir / "sharp"
        
        # Create necessary directories
        # Wallet directories
        (self.sharp_dir / "wallets").mkdir(parents=True, exist_ok=True)
        (self.sharp_dir / "wallets/split").mkdir(parents=True, exist_ok=True)
        
        # CSV directories
        (self.sharp_dir / "csv/unmerged").mkdir(parents=True, exist_ok=True)
        (self.sharp_dir / "csv/merged").mkdir(parents=True, exist_ok=True)
        (self.sharp_dir / "csv/unfiltered").mkdir(parents=True, exist_ok=True)
        (self.sharp_dir / "csv/filtered").mkdir(parents=True, exist_ok=True)
        
        # Configuration directory
        (self.sharp_dir / "config").mkdir(parents=True, exist_ok=True)
        
        # BullX API URL
        self.bullx_api_url = "https://api-neo.bullx.io/v2/api/getPortfolioV3"
        
        # Default headers for API requests
        self.headers = {
            "Content-Type": "application/json",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/108.0.0.0 Safari/537.36"
            )
        }
    
    def wallet_checker(self, wallets: List[str], config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Check wallet statistics using BullX API.
        
        Args:
            wallets: List of wallet addresses to check
            config: Configuration for filtering (optional)
            
        Returns:
            Dictionary with results information
        """
        if not wallets:
            return {
                "success": False,
                "error": "No wallet addresses provided"
            }
            
        # Load default configuration if none provided
        if config is None:
            config_path = self.sharp_dir / "config/wallet_checker_config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception as e:
                    print(f"Error reading config file: {e}")
                    config = self._get_default_wallet_config()
            else:
                config = self._get_default_wallet_config()
                # Save default config for future reference
                from ...utils.common import ensure_file_dir
                ensure_file_dir(config_path)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, indent=2, fp=f)
        
        # Process each wallet
        results = []
        filtered_results = []
        
        for wallet in wallets:
            try:
                # Call BullX API - this is a stub for real functionality
                # In a real implementation, we would make an actual API call
                # but we'll simulate it for now
                row = self._fetch_portfolio_data(wallet)
                results.append(row)
                
                # Apply filters from config
                if self._passes_filters(row, config["filters"]):
                    filtered_results.append(row)
                    
            except Exception as e:
                print(f"Error processing wallet {wallet}: {e}")
        
        # Generate output files with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save filtered wallet addresses
        from ...utils.common import ensure_file_dir
        wallet_dir = self.sharp_dir / "wallets"
        output_wallets_file = wallet_dir / f"output-wallets_{timestamp}.txt"
        
        ensure_file_dir(output_wallets_file)
        with open(output_wallets_file, "w", encoding="utf-8") as f:
            for row in filtered_results:
                f.write(row["wallet"] + "\n")
        
        # Generate CSV outputs if requested
        if config.get("save_unfiltered_csv", True):
            self._save_wallet_csv(results, timestamp, filtered=False)
            
        if config.get("save_filtered_csv", True):
            self._save_wallet_csv(filtered_results, timestamp, filtered=True)
        
        return {
            "success": True,
            "total_wallets": len(wallets),
            "processed_wallets": len(results),
            "filtered_wallets": len(filtered_results),
            "output_file": str(output_wallets_file)
        }
    
    def wallet_splitter(self, wallets: List[str], max_wallets_per_file: int = 24999) -> Dict[str, Any]:
        """
        Split large wallet lists into smaller chunks.
        
        Args:
            wallets: List of wallet addresses to split
            max_wallets_per_file: Maximum wallets per output file
            
        Returns:
            Dictionary with results information
        """
        if not wallets:
            return {
                "success": False,
                "error": "No wallet addresses provided"
            }
            
        # Create timestamped output directory
        from ...utils.common import ensure_file_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        split_dir = self.sharp_dir / f"wallets/split/split_{timestamp}"
        split_dir.mkdir(parents=True, exist_ok=True)
        
        # Split wallets into chunks
        total_wallets = len(wallets)
        num_files = (total_wallets + max_wallets_per_file - 1) // max_wallets_per_file
        
        output_files = []
        
        for i in range(num_files):
            start_idx = i * max_wallets_per_file
            end_idx = min((i + 1) * max_wallets_per_file, total_wallets)
            chunk = wallets[start_idx:end_idx]
            
            # Create output file
            output_file = split_dir / f"wallets_{i+1:03d}.txt"
            ensure_file_dir(output_file)
            with open(output_file, "w", encoding="utf-8") as f:
                for wallet in chunk:
                    f.write(wallet + "\n")
            
            output_files.append(str(output_file))
        
        return {
            "success": True,
            "total_wallets": total_wallets,
            "files_created": num_files,
            "output_directory": str(split_dir),
            "output_files": output_files
        }
    
    def csv_merger(self, csv_files: List[str]) -> Dict[str, Any]:
        """
        Merge multiple CSV files into a single file.
        
        Args:
            csv_files: List of CSV file paths to merge
            
        Returns:
            Dictionary with results information
        """
        if not csv_files:
            return {
                "success": False,
                "error": "No CSV files provided"
            }
        
        unmerged_dir = self.sharp_dir / "csv/unmerged"
        merged_dir = self.sharp_dir / "csv/merged"
        
        try:
            # Validate files exist
            for file in csv_files:
                file_path = unmerged_dir / file
                if not file_path.exists():
                    return {
                        "success": False,
                        "error": f"File not found: {file}"
                    }
            
            # Read the first CSV with headers
            first_file = unmerged_dir / csv_files[0]
            merged_data = pd.read_csv(first_file)
            headers = merged_data.columns
            
            # Read and merge remaining CSVs
            for file in csv_files[1:]:
                file_path = unmerged_dir / file
                df = pd.read_csv(file_path, header=None)
                df.columns = headers
                merged_data = pd.concat([merged_data, df], ignore_index=True)
            
            # Save to merged file
            from ...utils.common import ensure_file_dir
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            merged_filename = f"merged_{timestamp}.csv"
            merged_path = merged_dir / merged_filename
            
            # Ensure parent directory exists
            ensure_file_dir(merged_path)
            
            merged_data.to_csv(merged_path, index=False)
            
            return {
                "success": True,
                "input_files": len(csv_files),
                "total_rows": len(merged_data),
                "output_file": str(merged_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error merging CSV files: {e}"
            }
    
    def pnl_checker(self, csv_file: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Filter wallet CSVs based on performance metrics.
        
        Args:
            csv_file: Path to the CSV file to filter
            config: Configuration for filtering (optional)
            
        Returns:
            Dictionary with results information
        """
        unfiltered_dir = self.sharp_dir / "csv/unfiltered"
        filtered_dir = self.sharp_dir / "csv/filtered"
        
        csv_path = unfiltered_dir / csv_file
        if not csv_path.exists():
            return {
                "success": False,
                "error": f"CSV file not found: {csv_file}"
            }
        
        # Load default configuration if none provided
        if config is None:
            config_path = self.sharp_dir / "config/pnl_filter_config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception as e:
                    print(f"Error reading config file: {e}")
                    config = self._get_default_pnl_config()
            else:
                config = self._get_default_pnl_config()
                # Save default config for future reference
                from ...utils.common import ensure_file_dir
                ensure_file_dir(config_path)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, indent=2, fp=f)
        
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Apply filters (stub implementation)
            # In a real implementation, we would apply the actual filters from config
            # but we'll simulate filtering for now
            filtered_count = len(df) // 2
            filtered_df = df.iloc[:filtered_count]
            
            # Save filtered results
            from ...utils.common import ensure_file_dir
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = os.path.splitext(csv_file)[0]
            filtered_filename = f"{base_name}_filtered_{timestamp}.csv"
            filtered_path = filtered_dir / filtered_filename
            
            # Ensure parent directory exists
            ensure_file_dir(filtered_path)
            
            filtered_df.to_csv(filtered_path, index=False)
            
            return {
                "success": True,
                "input_rows": len(df),
                "filtered_rows": len(filtered_df),
                "output_file": str(filtered_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing CSV file: {e}"
            }
    
    def _fetch_portfolio_data(self, wallet_address: str) -> Dict[str, Any]:
        """
        Fetch portfolio data for a wallet from BullX API.
        This is a stub implementation that would be replaced with actual API calls.
        
        Args:
            wallet_address: Wallet address to fetch data for
            
        Returns:
            Dictionary with wallet data
        """
        # In a real implementation, we would call the BullX API
        # For now, return dummy data
        import random
        
        return {
            "wallet": wallet_address,
            "realizedPnlUsd": int(random.random() * 10000),
            "unrealizedPnlUsd": int(random.random() * 5000),
            "totalRevenuePercent": int(random.random() * 1000),
            "distribution_0_percent": int(random.random() * 100),
            "distribution_0_200_percent": round(random.random() * 100, 1),
            "distribution_200_plus_percent": round(random.random() * 100, 1)
        }
    
    def _passes_filters(self, row: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if a wallet passes all filter thresholds.
        
        Args:
            row: Wallet data row
            filters: Dictionary of filter thresholds
            
        Returns:
            True if the wallet passes all filters, False otherwise
        """
        for filter_key, min_val in filters.items():
            if min_val > 0 and row.get(filter_key, 0) < min_val:
                return False
        return True
    
    def _save_wallet_csv(self, rows: List[Dict[str, Any]], timestamp: str, filtered: bool = False) -> str:
        """
        Save wallet data as CSV.
        
        Args:
            rows: List of wallet data rows
            timestamp: Timestamp string for filename
            filtered: Whether this is filtered data
            
        Returns:
            Path to the saved CSV file
        """
        from ...utils.common import ensure_file_dir
        wallet_dir = self.sharp_dir / "wallets"
        file_prefix = "portfolio_results_filtered" if filtered else "portfolio_results"
        csv_filename = wallet_dir / f"{file_prefix}_{timestamp}.csv"
        
        # Ensure parent directory exists
        ensure_file_dir(csv_filename)
        
        fieldnames = [
            "wallet",
            "realizedPnlUsd",
            "unrealizedPnlUsd",
            "totalRevenuePercent",
            "distribution_0_percent",
            "distribution_0_200_percent",
            "distribution_200_plus_percent"
        ]
        
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
                
        return str(csv_filename)
    
    def _get_default_wallet_config(self) -> Dict[str, Any]:
        """
        Get default configuration for wallet checker.
        
        Returns:
            Dictionary with default configuration
        """
        return {
            "filters": {
                "min_realizedPnlUsd": 0,
                "min_unrealizedPnlUsd": 0,
                "min_totalRevenuePercent": 0,
                "min_distribution_0_percent": 0,
                "min_distribution_0_200_percent": 0,
                "min_distribution_200_plus_percent": 0
            },
            "save_unfiltered_csv": True,
            "save_filtered_csv": True
        }
    
    def _get_default_pnl_config(self) -> Dict[str, Any]:
        """
        Get default configuration for PnL checker.
        
        Returns:
            Dictionary with default configuration
        """
        return {
            "min_pnl": 0,
            "min_win_rate": 0,
            "max_loss_rate": 100,
            "min_trades": 0,
            "missed_data_allowed": True
        }