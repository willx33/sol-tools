# Sol Tools Data Directory Structure

This directory contains input and output data for all Sol Tools modules. The directory structure is organized by module and data type (input/output).

## Directory Structure

```
data/
├── input-data/             # Input data for all modules
│   ├── dragon/             # Dragon module input data
│   │   ├── ethereum/       # Ethereum-specific input data
│   │   │   └── wallet_lists/  # Ethereum wallet lists
│   │   ├── solana/         # Solana-specific input data
│   │   │   └── wallet_lists/  # Solana wallet lists
│   │   └── proxies/        # Proxy configurations
│   ├── dune/               # Dune module input data
│   │   └── query_configs/  # Dune query configurations
│   ├── ethereum/           # Ethereum module input data
│   ├── gmgn/               # GMGN module input data  
│   │   └── token_lists/    # Token list configurations
│   ├── sharp/              # Sharp module input data
│   └── solana/             # Solana module input data
│       └── wallet_lists/   # Solana wallet lists
│
├── output-data/            # Output data for all modules
│   ├── dragon/             # Dragon module output data
│   │   ├── ethereum/       # Ethereum-specific output data
│   │   │   ├── wallet_analysis/  # Wallet analysis results
│   │   │   ├── top_traders/      # Top traders analysis
│   │   │   ├── top_holders/      # Top holders analysis
│   │   │   └── early_buyers/     # Early buyers analysis
│   │   ├── solana/         # Solana-specific output data
│   │   │   ├── wallet_analysis/  # Wallet analysis results
│   │   │   ├── top_traders/      # Top traders analysis
│   │   │   ├── top_holders/      # Top holders analysis
│   │   │   └── early_buyers/     # Early buyers analysis
│   │   └── token_info/     # Token information
│   ├── dune/               # Dune module output data
│   │   ├── csv/            # Raw CSV query results
│   │   └── parsed/         # Parsed query results
│   ├── ethereum/           # Ethereum module output data
│   ├── gmgn/               # GMGN module output data
│   │   ├── token_listings/ # Token listings (new, completing, soaring, etc.)
│   │   ├── market_cap_data/ # Market cap data
│   │   └── token_info/     # Token information
│   ├── sharp/              # Sharp module output data
│   └── solana/             # Solana module output data
│       ├── transaction_data/ # Transaction data
│       └── wallet_data/    # Wallet data
└── README.md               # This file
```

## Module Data Usage

### Dragon Module

- **Input Data**:
  - `ethereum/wallet_lists/wallets.txt`: List of Ethereum wallet addresses for analysis
  - `solana/wallet_lists/wallets.txt`: List of Solana wallet addresses for analysis
  - `proxies/proxies.txt`: Proxy server configuration for API requests

- **Output Data**:
  - `ethereum/wallet_analysis/`: Analysis of Ethereum wallets
  - `ethereum/top_traders/`: Top traders on Ethereum
  - `ethereum/top_holders/`: Top token holders on Ethereum
  - `ethereum/early_buyers/`: Early token buyers on Ethereum
  - `solana/wallet_analysis/`: Analysis of Solana wallets
  - `solana/top_traders/`: Top traders on Solana
  - `solana/top_holders/`: Top token holders on Solana
  - `solana/early_buyers/`: Early token buyers on Solana
  - `token_info/`: Token information from various sources

### GMGN Module

- **Input Data**:
  - `token_lists/token_addresses.txt`: List of token addresses to query

- **Output Data**:
  - `token_listings/`: Token listings (new, completing, soaring, bonded)
  - `market_cap_data/`: Market cap data for tokens
  - `token_info/`: Token information from GMGN

### Dune Module

- **Input Data**:
  - `query_configs/`: Configuration for Dune queries

- **Output Data**:
  - `csv/`: Raw CSV query results from Dune
  - `parsed/`: Parsed query results

### Solana Module

- **Input Data**:
  - `wallet_lists/wallets.txt`: List of Solana wallet addresses

- **Output Data**:
  - `transaction_data/`: Transaction data from Solana blockchain
  - `wallet_data/`: Wallet data from Solana blockchain

## Notes

- Each module reads from its specific input directory and writes to its specific output directory
- File paths are defined in the `config.py` and respective module adapter files
- Input data files are generally expected to be text files with one item per line
- Output data files are generally JSON files with timestamp-based filenames