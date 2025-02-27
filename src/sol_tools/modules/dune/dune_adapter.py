"""Adapter for Dune Analytics API integration."""

import os
import time
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

class DuneAdapter:
    """Adapter for Dune Analytics functionality."""
    
    def __init__(self, data_dir: Union[str, Path], api_key: Optional[str] = None):
        """
        Initialize the Dune Analytics adapter.
        
        Args:
            data_dir: Path to the data directory
            api_key: Dune Analytics API key (optional, can be set later)
        """
        self.data_dir = Path(data_dir)
        self.dune_data_dir = self.data_dir / "dune"
        self.api_key = api_key
        self.client = None
        
        # Create necessary directories
        (self.dune_data_dir / "csv").mkdir(parents=True, exist_ok=True)
        (self.dune_data_dir / "parsed").mkdir(parents=True, exist_ok=True)
        
    def _initialize_client(self) -> bool:
        """
        Initialize the Dune client with the API key.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if self.client is not None:
            return True
            
        if not self.api_key:
            return False
            
        try:
            from dune_client.client import DuneClient
            self.client = DuneClient(api_key=self.api_key)
            return True
        except ImportError:
            print("Error: dune-client package not installed")
            return False
        except Exception as e:
            print(f"Error initializing Dune client: {e}")
            return False
    
    def set_api_key(self, api_key: str) -> bool:
        """
        Set the Dune Analytics API key.
        
        Args:
            api_key: Dune Analytics API key
            
        Returns:
            True if the key was set and client initialized, False otherwise
        """
        self.api_key = api_key
        self.client = None  # Reset client so it will be reinitialized
        return self._initialize_client()
    
    def run_query(self, query_ids: List[int], batch_size: int = 3, batch_delay: int = 30) -> Dict[str, Any]:
        """
        Execute Dune queries and save results as CSV files.
        
        Args:
            query_ids: List of Dune query IDs to execute
            batch_size: Number of queries to run in each batch (default 3)
            batch_delay: Delay in seconds between batches (default 30)
            
        Returns:
            Dictionary with results information
        """
        if not self._initialize_client():
            return {
                "success": False, 
                "error": "Dune client not initialized. Please set API key."
            }
            
        if not query_ids:
            return {
                "success": False,
                "error": "No query IDs provided"
            }
            
        csv_dir = self.dune_data_dir / "csv"
        results = {
            "success": True,
            "queries_run": 0,
            "failures": 0,
            "csv_files": []
        }
        
        # Process queries in batches
        for i in range(0, len(query_ids), batch_size):
            batch = query_ids[i:i + batch_size]
            
            for qid in batch:
                try:
                    print(f"Fetching Query ID {qid}...")
                    df = self.client.get_latest_result_dataframe(qid)
                    
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    csv_filename = f"dune_output_{qid}_{timestamp}.csv"
                    csv_path = csv_dir / csv_filename
                    
                    df.to_csv(csv_path, index=False)
                    
                    row_count = len(df)
                    file_size = os.path.getsize(csv_path)
                    print(f"Saved {row_count} rows to '{csv_filename}' ({file_size} bytes)")
                    
                    results["queries_run"] += 1
                    results["csv_files"].append(str(csv_path))
                    
                except Exception as e:
                    print(f"Error fetching Query {qid}: {e}")
                    results["failures"] += 1
            
            # Add delay between batches if there are more queries to process
            if i + batch_size < len(query_ids):
                print(f"Batch done. Waiting {batch_delay} seconds to respect rate limits...")
                time.sleep(batch_delay)
        
        return results
    
    def parse_csv(self, csv_filename: str, column_index: int = 2) -> Dict[str, Any]:
        """
        Parse a CSV file from Dune to extract token addresses.
        
        Args:
            csv_filename: Name of the CSV file to parse
            column_index: Index of the column to extract (default 2 for token_address)
            
        Returns:
            Dictionary with parsing results
        """
        csv_dir = self.dune_data_dir / "csv"
        parsed_dir = self.dune_data_dir / "parsed"
        
        csv_path = csv_dir / csv_filename
        if not csv_path.exists():
            return {
                "success": False,
                "error": f"CSV file not found: {csv_filename}"
            }
            
        try:
            # Read the CSV
            df = pd.read_csv(csv_path, header=None)
            
            # Extract values from the specified column
            addresses = []
            for _, row in df.iterrows():
                if len(row) > column_index:
                    val = str(row[column_index]).strip()
                    if val.lower() == "token_address":
                        continue
                    addresses.append(val)
            
            # Create output filename
            base_name = os.path.splitext(csv_filename)[0]
            out_filename = f"{base_name}_parsed.txt"
            out_path = parsed_dir / out_filename
            
            # Write extracted addresses to file
            with open(out_path, "w", encoding="utf-8") as f:
                for addr in addresses:
                    f.write(addr + "\n")
            
            return {
                "success": True,
                "addresses_extracted": len(addresses),
                "output_file": str(out_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error parsing CSV: {e}"
            }
    
    def get_available_csvs(self) -> List[str]:
        """
        Get a list of available CSV files in the Dune data directory.
        
        Returns:
            List of CSV filenames
        """
        csv_dir = self.dune_data_dir / "csv"
        return [f.name for f in csv_dir.glob("*.csv")]
    
    def delete_csv(self, csv_filename: str) -> bool:
        """
        Delete a CSV file.
        
        Args:
            csv_filename: Name of the CSV file to delete
            
        Returns:
            True if the file was deleted, False otherwise
        """
        csv_path = self.dune_data_dir / "csv" / csv_filename
        if csv_path.exists():
            try:
                os.remove(csv_path)
                return True
            except Exception:
                return False
        return False